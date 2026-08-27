#!/usr/bin/env python3
"""Apply PostgreSQL migrations through the deployment-only credential.

Run this from an approved administrative job with *both*
``DATABASE_MIGRATION_URL`` (DDL role) and ``DATABASE_URL`` (runtime role) in
its secret environment. It intentionally has no default, no file fallback, and
never prints either credential.
"""

from __future__ import annotations

import json
import sys

from psycopg import connect, sql

from app.config import DATABASE_BACKEND, DATABASE_MIGRATION_URL, DATABASE_URL
from app.postgres_backend import current_schema_name, run_postgres_migrations
from app.production_schema import RUNTIME_WRITE_TABLES, assert_production_schema_ready


def is_postgres_url(value: str) -> bool:
    return value.lower().startswith(("postgresql://", "postgres://"))


def _runtime_role() -> str:
    with connect(DATABASE_URL) as runtime_connection:
        row = runtime_connection.execute("SELECT current_user AS role").fetchone()
    runtime_role = str(row[0] if row else "")
    if not runtime_role:
        raise RuntimeError("Unable to determine the PostgreSQL runtime role")
    return runtime_role


def grant_runtime_privileges() -> None:
    """Reset and grant the request-serving role to least privilege.

    Runtime may read migrated application tables, but writes are limited to the
    explicit candidate/session/billing/runtime state allowlist. Certification
    content, answer keys, release/editorial governance, source freshness, and
    the migration ledger remain read-only to the request-serving role.
    """
    runtime_role = _runtime_role()
    schema = current_schema_name()

    with connect(DATABASE_MIGRATION_URL, autocommit=True) as migration_connection:
        schema_identifier = sql.Identifier(schema)
        role_identifier = sql.Identifier(runtime_role)
        database_row = migration_connection.execute("SELECT current_database()").fetchone()
        database_name = str(database_row[0] if database_row else "")
        if not database_name:
            raise RuntimeError("Unable to determine the PostgreSQL database name")

        existing_tables = {
            str(row[0])
            for row in migration_connection.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema=%s AND table_type='BASE TABLE'",
                (schema,),
            )
        }
        missing_write_tables = sorted(RUNTIME_WRITE_TABLES - existing_tables)
        if missing_write_tables:
            raise RuntimeError(
                "Runtime write allowlist references missing migrated tables: " + ", ".join(missing_write_tables)
            )

        # Reset any inherited/object-level grants from previous deployments, then
        # rebuild the runtime ACL from a narrow allowlist.
        migration_connection.execute(
            sql.SQL("REVOKE ALL PRIVILEGES ON SCHEMA {} FROM {}").format(schema_identifier, role_identifier)
        )
        migration_connection.execute(
            sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(schema_identifier, role_identifier)
        )
        migration_connection.execute(
            sql.SQL("REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA {} FROM {}").format(
                schema_identifier, role_identifier
            )
        )
        migration_connection.execute(
            sql.SQL("GRANT SELECT ON ALL TABLES IN SCHEMA {} TO {}").format(schema_identifier, role_identifier)
        )

        writable_tables = sql.SQL(", ").join(
            sql.Identifier(schema, table) for table in sorted(RUNTIME_WRITE_TABLES)
        )
        migration_connection.execute(
            sql.SQL("GRANT INSERT, UPDATE, DELETE ON {} TO {}").format(writable_tables, role_identifier)
        )

        # Sequence usage is limited to serial/identity sequences owned by tables
        # the runtime is explicitly allowed to mutate.
        migration_connection.execute(
            sql.SQL("REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA {} FROM {}").format(
                schema_identifier, role_identifier
            )
        )
        sequence_rows = migration_connection.execute(
            """
            SELECT DISTINCT seq.relname
            FROM pg_class seq
            JOIN pg_namespace ns ON ns.oid=seq.relnamespace
            JOIN pg_depend dep ON dep.objid=seq.oid AND dep.deptype IN ('a','i')
            JOIN pg_class tbl ON tbl.oid=dep.refobjid
            WHERE seq.relkind='S' AND ns.nspname=%s AND tbl.relname = ANY(%s)
            ORDER BY seq.relname
            """,
            (schema, list(sorted(RUNTIME_WRITE_TABLES))),
        ).fetchall()
        sequence_names = [str(row[0]) for row in sequence_rows]
        if sequence_names:
            writable_sequences = sql.SQL(", ").join(
                sql.Identifier(schema, sequence) for sequence in sequence_names
            )
            migration_connection.execute(
                sql.SQL("GRANT USAGE, SELECT, UPDATE ON {} TO {}").format(
                    writable_sequences, role_identifier
                )
            )

        # Explicitly remove database/schema DDL and table-elevation capabilities.
        migration_connection.execute(
            sql.SQL("REVOKE CREATE ON DATABASE {} FROM {}").format(
                sql.Identifier(database_name), role_identifier
            )
        )
        migration_connection.execute(
            sql.SQL("REVOKE CREATE ON SCHEMA {} FROM {}").format(schema_identifier, role_identifier)
        )
        migration_connection.execute(
            sql.SQL("REVOKE TRUNCATE, REFERENCES, TRIGGER ON ALL TABLES IN SCHEMA {} FROM {}").format(
                schema_identifier, role_identifier
            )
        )

        # No ALTER DEFAULT PRIVILEGES grant is used. Each migration job reruns
        # this reconciliation, so a new table receives no runtime write access
        # until it is explicitly added to RUNTIME_WRITE_TABLES and reviewed.


def main() -> None:
    if DATABASE_BACKEND != "postgresql" or not is_postgres_url(DATABASE_URL):
        raise SystemExit("DATABASE_URL must be the PostgreSQL runtime connection for production migration verification")
    if not is_postgres_url(DATABASE_MIGRATION_URL):
        raise SystemExit("DATABASE_MIGRATION_URL must be a PostgreSQL deployment-only migration credential")

    run_postgres_migrations(migration_url=DATABASE_MIGRATION_URL)
    grant_runtime_privileges()
    status = assert_production_schema_ready()
    print(
        json.dumps(
            {
                "status": "ok",
                "backend": status["backend"],
                "schema": status["schema"],
                "migration_count": status["migration_count"],
                "runtime_role_verified": True,
            }
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Production migration failed: {type(exc).__name__}", file=sys.stderr)
        raise
