#!/usr/bin/env python3
"""Apply PostgreSQL migrations through the deployment-only credential.

Run this from an approved administrative job with *both*
``DATABASE_MIGRATION_URL`` (DDL role) and ``DATABASE_URL`` (runtime role) in
its secret environment.  It intentionally has no default, no file fallback,
and never prints either credential.
"""

from __future__ import annotations

import json
import sys

from psycopg import connect, sql

from app.config import DATABASE_BACKEND, DATABASE_MIGRATION_URL, DATABASE_URL
from app.postgres_backend import current_schema_name, run_postgres_migrations
from app.production_schema import assert_production_schema_ready


def is_postgres_url(value: str) -> bool:
    return value.lower().startswith(("postgresql://", "postgres://"))


def grant_runtime_privileges() -> None:
    """Grant the DML-only runtime role access to migrated application objects."""
    with connect(DATABASE_URL) as runtime_connection:
        row = runtime_connection.execute("SELECT current_user AS role").fetchone()
    runtime_role = str(row[0] if row else "")
    if not runtime_role:
        raise RuntimeError("Unable to determine the PostgreSQL runtime role")

    schema = current_schema_name()
    with connect(DATABASE_MIGRATION_URL, autocommit=True) as migration_connection:
        schema_identifier = sql.Identifier(schema)
        role_identifier = sql.Identifier(runtime_role)
        migration_connection.execute(
            sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(schema_identifier, role_identifier)
        )
        migration_connection.execute(
            sql.SQL("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA {} TO {}").format(
                schema_identifier, role_identifier
            )
        )
        migration_connection.execute(
            sql.SQL("GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA {} TO {}").format(
                schema_identifier, role_identifier
            )
        )
        migration_connection.execute(
            sql.SQL("GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA {} TO {}").format(schema_identifier, role_identifier)
        )
        migration_connection.execute(
            sql.SQL("ALTER DEFAULT PRIVILEGES IN SCHEMA {} GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {}").format(
                schema_identifier, role_identifier
            )
        )
        migration_connection.execute(
            sql.SQL("ALTER DEFAULT PRIVILEGES IN SCHEMA {} GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO {}").format(
                schema_identifier, role_identifier
            )
        )
        migration_connection.execute(
            sql.SQL("ALTER DEFAULT PRIVILEGES IN SCHEMA {} GRANT EXECUTE ON FUNCTIONS TO {}").format(
                schema_identifier, role_identifier
            )
        )


def main() -> None:
    if DATABASE_BACKEND != "postgresql" or not is_postgres_url(DATABASE_URL):
        raise SystemExit("DATABASE_URL must be the PostgreSQL runtime connection for production migration verification")
    if not is_postgres_url(DATABASE_MIGRATION_URL):
        raise SystemExit("DATABASE_MIGRATION_URL must be a PostgreSQL deployment-only migration credential")

    run_postgres_migrations(migration_url=DATABASE_MIGRATION_URL)
    grant_runtime_privileges()
    status = assert_production_schema_ready()
    print(json.dumps({"status": "ok", "backend": status["backend"], "schema": status["schema"], "migration_count": status["migration_count"]}))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Production migration failed: {type(exc).__name__}", file=sys.stderr)
        raise
