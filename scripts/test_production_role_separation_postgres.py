#!/usr/bin/env python3
"""Real PostgreSQL integration proof for the production runtime ACL.

Creates separate migration/runtime roles against the disposable CI database,
runs repository migrations, reconciles the production ACL, proves approved
candidate-state DML succeeds, and proves DDL, privilege escalation, server-side
program execution, plus question-bank/migration-ledger writes fail.
"""

from __future__ import annotations

import os
import secrets
import sys
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
from psycopg import errors, sql


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def require(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def role_dsn(admin_url: str, role: str, password: str) -> str:
    parsed = urlsplit(admin_url)
    host = parsed.hostname or "127.0.0.1"
    port = f":{parsed.port}" if parsed.port else ""
    netloc = f"{quote(role, safe='')}:{quote(password, safe='')}@{host}{port}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


def expect_denied(connection: psycopg.Connection, statement: object, label: str, params: tuple | None = None) -> None:
    try:
        connection.execute(statement, params or ())
    except (errors.InsufficientPrivilege, errors.NotOwner):
        return
    raise AssertionError(f"Runtime role unexpectedly performed privileged operation: {label}")


def main() -> None:
    admin_url = os.environ.get("ROLE_TEST_ADMIN_URL", "").strip()
    if not admin_url.lower().startswith(("postgresql://", "postgres://")):
        raise SystemExit("ROLE_TEST_ADMIN_URL must point to the disposable PostgreSQL CI database")

    suffix = secrets.token_hex(4)
    runtime_role = f"app_runtime_{suffix}"
    migration_role = f"app_migrator_{suffix}"
    schema = f"role_sep_{suffix}"
    runtime_password = secrets.token_urlsafe(18)
    migration_password = secrets.token_urlsafe(18)
    migration_function = f"migration_only_fn_{suffix}"

    parsed = urlsplit(admin_url)
    database_name = parsed.path.lstrip("/")
    require(bool(database_name), "ROLE_TEST_ADMIN_URL must include a database name")
    runtime_url = role_dsn(admin_url, runtime_role, runtime_password)
    migration_url = role_dsn(admin_url, migration_role, migration_password)

    with psycopg.connect(admin_url, autocommit=True) as admin:
        admin.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(runtime_role)))
        admin.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(migration_role)))
        # PostgreSQL utility statements such as CREATE ROLE do not accept a bind
        # placeholder for PASSWORD. sql.Literal performs Psycopg quoting/escaping
        # while keeping generated credentials out of logs and source text.
        admin.execute(
            sql.SQL(
                "CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS"
            ).format(sql.Identifier(runtime_role), sql.Literal(runtime_password))
        )
        admin.execute(
            sql.SQL(
                "CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS"
            ).format(sql.Identifier(migration_role), sql.Literal(migration_password))
        )
        admin.execute(
            sql.SQL("GRANT CONNECT ON DATABASE {} TO {}, {}").format(
                sql.Identifier(database_name),
                sql.Identifier(runtime_role),
                sql.Identifier(migration_role),
            )
        )
        admin.execute(
            sql.SQL("GRANT CREATE ON DATABASE {} TO {}").format(
                sql.Identifier(database_name), sql.Identifier(migration_role)
            )
        )

    os.environ["DATABASE_URL"] = runtime_url
    os.environ["DATABASE_MIGRATION_URL"] = migration_url
    os.environ["DATABASE_SCHEMA"] = schema
    os.environ["POSTGRES_TEST_ISOLATION"] = "false"
    os.environ.pop("VERCEL", None)
    os.environ.pop("VERCEL_ENV", None)

    from app.postgres_backend import close_pool, run_postgres_migrations  # noqa: E402
    from app.production_schema import assert_production_schema_ready  # noqa: E402
    from scripts.migrate_production import grant_runtime_privileges  # noqa: E402

    try:
        run_postgres_migrations(migration_url=migration_url)
        grant_runtime_privileges()
        status = assert_production_schema_ready()
        require(status.get("status") == "ok", f"runtime schema verifier rejected isolated role: {status}")
        require(not status.get("unsafe_runtime_capabilities"), f"unsafe runtime capabilities detected: {status}")
        require(not status.get("excessive_runtime_write"), f"governance table writes detected: {status}")

        with psycopg.connect(migration_url, autocommit=True) as migrator:
            migrator.execute(sql.SQL("SET search_path TO {}, public").format(sql.Identifier(schema)))
            migrator.execute(
                sql.SQL("CREATE FUNCTION {}.{}() RETURNS integer LANGUAGE SQL AS 'SELECT 1'").format(
                    sql.Identifier(schema), sql.Identifier(migration_function)
                )
            )

        with psycopg.connect(runtime_url, autocommit=True) as runtime:
            runtime.execute(sql.SQL("SET search_path TO {}, public").format(sql.Identifier(schema)))
            role_state = runtime.execute(
                """
                SELECT current_user,
                       rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls,
                       has_database_privilege(current_user, current_database(), 'CREATE') AS database_create,
                       has_schema_privilege(current_user, current_schema(), 'CREATE') AS schema_create
                FROM pg_roles WHERE rolname=current_user
                """
            ).fetchone()
            require(role_state is not None, "runtime role state unavailable")
            require(role_state[0] == runtime_role, "runtime connection authenticated as the wrong role")
            require(not any(bool(value) for value in role_state[1:]), f"runtime role retained privileged capabilities: {role_state}")

            owners = runtime.execute(
                """
                SELECT pg_get_userbyid(d.datdba), pg_get_userbyid(n.nspowner)
                FROM pg_database d, pg_namespace n
                WHERE d.datname=current_database() AND n.nspname=current_schema()
                """
            ).fetchone()
            require(owners is not None, "database/schema ownership evidence unavailable")
            require(runtime_role not in owners, f"runtime role owns database or schema: {owners}")

            member = runtime.execute("SELECT pg_has_role(current_user, %s, 'MEMBER')", (migration_role,)).fetchone()
            require(member is not None and not bool(member[0]), "runtime role can inherit/set the migration role")
            for dangerous_role in ("pg_execute_server_program", "pg_read_server_files", "pg_write_server_files"):
                dangerous_member = runtime.execute(
                    "SELECT pg_has_role(current_user, %s, 'MEMBER')",
                    (dangerous_role,),
                ).fetchone()
                require(
                    dangerous_member is not None and not bool(dangerous_member[0]),
                    f"runtime role inherits dangerous predefined role {dangerous_role}",
                )

            # Positive proof on an approved candidate/runtime state table.
            runtime.execute(
                "INSERT INTO feedback_submissions(title,category,description,route,track_id) VALUES ('role test','other','','#/home','snowpro-core')"
            )
            row = runtime.execute("SELECT COUNT(*) FROM feedback_submissions WHERE title='role test'").fetchone()
            require(row and int(row[0]) == 1, "approved runtime INSERT/SELECT failed")
            runtime.execute("UPDATE feedback_submissions SET description='ok' WHERE title='role test'")
            runtime.execute("DELETE FROM feedback_submissions WHERE title='role test'")

            # Question-bank definitions and migration/release governance are read-only.
            expect_denied(runtime, "UPDATE questions SET explanation='forbidden' WHERE 1=0", "question-bank UPDATE")
            expect_denied(
                runtime,
                "INSERT INTO schema_migrations(version,name) VALUES ('forbidden','forbidden')",
                "schema migration ledger INSERT",
            )
            expect_denied(
                runtime,
                "UPDATE question_bank_releases SET notes='forbidden' WHERE 1=0",
                "release governance UPDATE",
            )
            expect_denied(
                runtime,
                "UPDATE question_editorial_policies SET enforcement_enabled=0 WHERE 1=0",
                "editorial policy UPDATE",
            )

            # DDL and schema elevation are denied.
            expect_denied(
                runtime,
                sql.SQL("CREATE TABLE {}.runtime_must_not_create(id int)").format(sql.Identifier(schema)),
                "CREATE TABLE",
            )
            expect_denied(
                runtime,
                sql.SQL("ALTER TABLE {}.feedback_submissions ADD COLUMN forbidden int").format(sql.Identifier(schema)),
                "ALTER TABLE",
            )
            expect_denied(
                runtime,
                sql.SQL("DROP TABLE {}.feedback_submissions").format(sql.Identifier(schema)),
                "DROP TABLE",
            )
            expect_denied(
                runtime,
                sql.SQL("TRUNCATE TABLE {}.feedback_submissions").format(sql.Identifier(schema)),
                "TRUNCATE TABLE",
            )
            expect_denied(
                runtime,
                sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(f"runtime_schema_{suffix}")),
                "CREATE SCHEMA",
            )
            expect_denied(
                runtime,
                sql.SQL("CREATE FUNCTION {}.runtime_must_not_create_fn() RETURNS integer LANGUAGE SQL AS 'SELECT 1'").format(
                    sql.Identifier(schema)
                ),
                "CREATE FUNCTION",
            )
            expect_denied(
                runtime,
                sql.SQL("ALTER FUNCTION {}.{}() RENAME TO forbidden_rename").format(
                    sql.Identifier(schema), sql.Identifier(migration_function)
                ),
                "ALTER FUNCTION",
            )
            expect_denied(
                runtime,
                sql.SQL("DROP FUNCTION {}.{}()").format(
                    sql.Identifier(schema), sql.Identifier(migration_function)
                ),
                "DROP FUNCTION",
            )
            expect_denied(runtime, "CREATE ROLE runtime_forbidden_child", "CREATE ROLE")
            expect_denied(
                runtime,
                sql.SQL("SET ROLE {}").format(sql.Identifier(migration_role)),
                "SET ROLE migration role",
            )
            expect_denied(
                runtime,
                sql.SQL("GRANT SELECT ON {}.feedback_submissions TO PUBLIC").format(sql.Identifier(schema)),
                "GRANT table privilege",
            )
            expect_denied(
                runtime,
                sql.SQL("REVOKE SELECT ON {}.feedback_submissions FROM {}").format(
                    sql.Identifier(schema), sql.Identifier(runtime_role)
                ),
                "REVOKE table privilege",
            )
            expect_denied(runtime, "COPY (SELECT 1) TO PROGRAM 'true'", "COPY TO PROGRAM")

        # A future table is safe-by-default. After ACL reconciliation it is
        # readable but not writable until explicitly added to RUNTIME_WRITE_TABLES.
        with psycopg.connect(migration_url, autocommit=True) as migrator:
            migrator.execute(sql.SQL("SET search_path TO {}, public").format(sql.Identifier(schema)))
            migrator.execute(
                sql.SQL("CREATE TABLE {}.future_governance_probe (id bigint PRIMARY KEY, value text NOT NULL)").format(
                    sql.Identifier(schema)
                )
            )
        grant_runtime_privileges()
        status = assert_production_schema_ready()
        require(status.get("status") == "ok", f"future read-only table broke runtime verifier: {status}")
        with psycopg.connect(runtime_url, autocommit=True) as runtime:
            runtime.execute(sql.SQL("SET search_path TO {}, public").format(sql.Identifier(schema)))
            runtime.execute(sql.SQL("SELECT * FROM {}.future_governance_probe").format(sql.Identifier(schema)))
            expect_denied(
                runtime,
                sql.SQL("INSERT INTO {}.future_governance_probe(id,value) VALUES (1,'forbidden')").format(
                    sql.Identifier(schema)
                ),
                "future-table INSERT",
            )

        print(
            "Production role separation: PASS "
            "(candidate DML works; bank/governance writes, DDL, role escalation and server-program execution denied)"
        )
    finally:
        close_pool()
        with psycopg.connect(admin_url, autocommit=True) as admin:
            admin.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema)))
            admin.execute(sql.SQL("REVOKE CREATE ON DATABASE {} FROM {}").format(sql.Identifier(database_name), sql.Identifier(migration_role)))
            admin.execute(sql.SQL("DROP OWNED BY {} CASCADE").format(sql.Identifier(runtime_role)))
            admin.execute(sql.SQL("DROP OWNED BY {} CASCADE").format(sql.Identifier(migration_role)))
            admin.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(runtime_role)))
            admin.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(migration_role)))


if __name__ == "__main__":
    main()
