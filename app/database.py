from __future__ import annotations

from typing import Any

from .config import DATABASE_BACKEND

# Keep the mature SQLite implementation intact for local development and the
# lightweight test path. Production PostgreSQL uses the compatibility adapter
# and versioned migrations in postgres_backend.py.
from .database_sqlite import SCHEMA_VERSION

if DATABASE_BACKEND == "postgresql":
    from .postgres_backend import (
        close_pool as close_database,
        connect,
        database_health,
        get_conn,
        run_postgres_migrations as run_migrations,
    )

    def row_to_dict(row: Any | None) -> dict[str, Any] | None:
        return dict(row) if row else None
else:
    from .database_sqlite import connect, get_conn, row_to_dict, run_migrations

    def database_health() -> dict[str, Any]:
        with connect() as conn:
            row = conn.execute("SELECT 1 AS ok").fetchone()
        return {
            "status": "ok" if row and int(row["ok"]) == 1 else "error",
            "backend": "sqlite",
        }

    def close_database() -> None:
        return None


__all__ = [
    "SCHEMA_VERSION",
    "close_database",
    "connect",
    "database_health",
    "get_conn",
    "row_to_dict",
    "run_migrations",
]
