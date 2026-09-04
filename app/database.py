from __future__ import annotations

import atexit
import time
from contextlib import contextmanager
from typing import Any, Iterator

from .config import DATABASE_BACKEND
from .observability import instrument_connection, log_event, record_db_operation

# Keep the mature SQLite implementation intact for local development and the
# lightweight test path. Production PostgreSQL uses the compatibility adapter
# and versioned migrations in postgres_backend.py. Both are instrumented through
# the same public database boundary below.
from .database_sqlite import SCHEMA_VERSION

if DATABASE_BACKEND == "postgresql":
    from .postgres_backend import (
        close_pool as _raw_close_database,
        connect as _raw_connect,
        database_health as _raw_database_health,
        get_conn as _raw_get_conn,
        run_postgres_migrations as _raw_run_migrations,
    )

    def row_to_dict(row: Any | None) -> dict[str, Any] | None:
        return dict(row) if row else None

    atexit.register(_raw_close_database)
else:
    from .database_sqlite import (
        connect as _raw_connect,
        get_conn as _raw_get_conn,
        row_to_dict,
        run_migrations as _raw_run_migrations,
    )

    def _raw_database_health() -> dict[str, Any]:
        with _raw_connect() as conn:
            row = conn.execute("SELECT 1 AS ok").fetchone()
        return {
            "status": "ok" if row and int(row["ok"]) == 1 else "error",
            "backend": "sqlite",
        }

    def _raw_close_database() -> None:
        return None


def _converge_sqlite_runtime_schema() -> None:
    """Keep the lightweight SQLite compatibility schema aligned with runtime writes.

    Production schema changes are versioned PostgreSQL migrations. SQLite is only
    the local/CI compatibility path, but every runtime write exercised there must
    still have a converged schema so security regressions cannot be hidden by a
    stale test database.
    """
    if DATABASE_BACKEND != "sqlite":
        return
    required = {
        "response_time_ms": "INTEGER",
        "confidence": "INTEGER",
    }
    with _raw_connect() as conn:
        columns = {str(row["name"]) for row in conn.execute("PRAGMA table_info(question_attempts)")}
        for column, declaration in required.items():
            if column not in columns:
                conn.execute(f"ALTER TABLE question_attempts ADD COLUMN {column} {declaration}")
        conn.commit()

    # Credential/talent tables are part of the normal local application schema
    # and are required by the hostile-subscriber ownership suite. Import lazily
    # here to avoid a module cycle: talent_schema itself uses database.connect.
    from .talent_schema import ensure_talent_schema

    ensure_talent_schema()


@contextmanager
def connect() -> Iterator[Any]:
    with _raw_connect() as raw:
        yield instrument_connection(raw, DATABASE_BACKEND)


def get_conn() -> Any:
    return instrument_connection(_raw_get_conn(), DATABASE_BACKEND)


def run_migrations() -> None:
    started = time.perf_counter()
    try:
        _raw_run_migrations()
        _converge_sqlite_runtime_schema()
    except Exception as exc:
        duration = (time.perf_counter() - started) * 1000
        record_db_operation("MIGRATION", duration, ok=False, backend=DATABASE_BACKEND)
        log_event("database_migration_failed", level=40, backend=DATABASE_BACKEND, error_type=type(exc).__name__)
        raise
    record_db_operation("MIGRATION", (time.perf_counter() - started) * 1000, ok=True, backend=DATABASE_BACKEND)


def database_health() -> dict[str, Any]:
    started = time.perf_counter()
    try:
        result = _raw_database_health()
    except Exception:
        record_db_operation("HEALTH", (time.perf_counter() - started) * 1000, ok=False, backend=DATABASE_BACKEND)
        raise
    record_db_operation("HEALTH", (time.perf_counter() - started) * 1000, ok=result.get("status") == "ok", backend=DATABASE_BACKEND)
    return result


def close_database() -> None:
    _raw_close_database()


__all__ = [
    "SCHEMA_VERSION",
    "close_database",
    "connect",
    "database_health",
    "get_conn",
    "row_to_dict",
    "run_migrations",
]
