#!/usr/bin/env python3
"""Integration proof that the production runtime role is DML-only.

Unlike the lightweight GRANT-shape unit test, this test creates separate login
roles in a real PostgreSQL CI service, runs the repository migrations with the
migration role, grants runtime privileges through the production migration
helper, and proves the runtime role can perform application DML but cannot
perform DDL, own the database/schema, or inherit the migration role.
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


def expect_ddl_denied(connection: psycopg.Connection, statement: sql.Composed | sql.SQL, label: str) -> None:
    try:
        connection.execute(statement)
    except (errors.InsufficientPrivilege, errors.NotOwner):
        return
    raise AssertionError(f"Runtime role unexpectedly performed DDL: {label}")


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

    parsed = urlsplit(admin_url)
    database_name = parsed.path.lstrip("/")
    require(bool(database_name), "ROLE_TEST_ADMIN_URL must include a database name")
    runtime_url = role_dsn(admin_url, runtime_role, runtime_password)
    migration_url = role_dsn(admin_url, migration_role, migration_password)

    with psycopg.connect(admin_url, autocommit=True) as admin:
        admin.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(runtime_role)))
        admin.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(migration_role)))
        admin.execute(
            sql.SQL("CREATE ROLE {} LOGIN PASSWORD %s NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS").format(
                sql.Identifier(runtime_role)
            ),
            (runtime_password,),
        )
        admin.execute(
            sql.SQL("CREATE ROLE {} LOGIN PASSWORD %s NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS").format(
                sql.Identifier(migration_role)
            ),
            (migration_password,),
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

    # Configure the application modules only after the disposable roles exist.
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

        # Default privileges must cover future migration-created objects too.
        with psycopg.connect(migration_url, autocommit=True) as migrator:
            migrator.execute(sql.SQL("SET search_path TO {}, public").format(sql.Identifier(schema)))
            migrator.execute(
                sql.SQL("CREATE TABLE {}.role_default_probe (id bigint PRIMARY KEY, value text NOT NULL)").format(
                    sql.Identifier(schema)
                )
            )

        status = assert_production_schema_ready()
        require(status.get("status") == "ok", f"runtime schema verifier rejected isolated DML role: {status}")
        require(not status.get("unsafe_runtime_capabilities"), f"unsafe runtime capabilities detected: {status}")

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

            # Positive proof: required application DML works, including an object
            # created after ALTER DEFAULT PRIVILEGES was established.
            probe = sql.Identifier(schema, "role_default_probe")
            runtime.execute(sql.SQL("INSERT INTO {}(id,value) VALUES (1,'a')").format(probe))
            runtime.execute(sql.SQL("UPDATE {} SET value='b' WHERE id=1").format(probe))
            row = runtime.execute(sql.SQL("SELECT value FROM {} WHERE id=1").format(probe)).fetchone()
            require(row and row[0] == "b", "runtime SELECT/INSERT/UPDATE failed")
            runtime.execute(sql.SQL("DELETE FROM {} WHERE id=1").format(probe))

            # Negative proof: DDL and schema creation are denied to the exact role
            # the application would use at runtime.
            expect_ddl_denied(
                runtime,
                sql.SQL("CREATE TABLE {}.runtime_must_not_create(id int)").format(sql.Identifier(schema)),
                "CREATE TABLE",
            )
            expect_ddl_denied(
                runtime,
                sql.SQL("ALTER TABLE {}.role_default_probe ADD COLUMN forbidden int").format(sql.Identifier(schema)),
                "ALTER TABLE",
            )
            expect_ddl_denied(
                runtime,
                sql.SQL("DROP TABLE {}.role_default_probe").format(sql.Identifier(schema)),
                "DROP TABLE",
            )
            expect_ddl_denied(
                runtime,
                sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(f"runtime_schema_{suffix}")),
                "CREATE SCHEMA",
            )

        print("Production role separation: PASS (runtime DML works; DDL/ownership/escalation denied)")
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
