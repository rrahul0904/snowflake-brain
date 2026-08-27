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

from app.config import DATABASE_BACKEND, DATABASE_MIGRATION_URL, DATABASE_URL
from app.postgres_backend import run_postgres_migrations
from app.production_schema import assert_production_schema_ready


def is_postgres_url(value: str) -> bool:
    return value.lower().startswith(("postgresql://", "postgres://"))


def main() -> None:
    if DATABASE_BACKEND != "postgresql" or not is_postgres_url(DATABASE_URL):
        raise SystemExit("DATABASE_URL must be the PostgreSQL runtime connection for production migration verification")
    if not is_postgres_url(DATABASE_MIGRATION_URL):
        raise SystemExit("DATABASE_MIGRATION_URL must be a PostgreSQL deployment-only migration credential")

    run_postgres_migrations(migration_url=DATABASE_MIGRATION_URL)
    status = assert_production_schema_ready()
    print(json.dumps({"status": "ok", "backend": status["backend"], "schema": status["schema"], "migration_count": status["migration_count"]}))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Production migration failed: {type(exc).__name__}", file=sys.stderr)
        raise
