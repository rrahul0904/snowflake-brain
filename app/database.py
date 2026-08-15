from __future__ import annotations

from typing import Any

from .config import DATABASE_BACKEND

# Keep the mature SQLite implementation intact for local development and the
# lightweight test path. Production PostgreSQL uses the compatibility adapter
# and versioned migrations in postgres_backend.py.
from .database_sqlite import SCHEMA_VERSION

if DATABASE_BACKEND == "postgresql":
    from .postgres_backend import connect, get_conn, run_postgres_migrations as run_migrations

    def row_to_dict(row: Any | None) -> dict[str, Any] | None:
        return dict(row) if row else None
else:
    from .database_sqlite import connect, get_conn, row_to_dict, run_migrations


__all__ = ["SCHEMA_VERSION", "connect", "get_conn", "row_to_dict", "run_migrations"]
