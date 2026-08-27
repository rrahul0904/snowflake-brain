"""Read-only production schema verification.

Schema mutation belongs to the controlled deployment migration job.  Vercel
functions call this module only to prove that their least-privilege runtime
credential can read the complete, already-migrated application schema.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import DATABASE_BACKEND, ROOT_DIR
from .database import connect


REQUIRED_TABLES = frozenset(
    {
        "schema_migrations",
        "candidate_accounts",
        "candidate_sessions",
        "candidate_memberships",
        "questions",
        "question_versions",
        "question_bank_releases",
        "question_bank_release_questions",
        "question_attempts",
        "exam_sessions",
        "exam_session_answers",
        "candidate_srs_state",
        "candidate_mistake_notebook",
        "candidate_readiness_snapshots",
        "feedback_submissions",
        "candidate_credentials",
    }
)


def expected_migration_versions() -> set[str]:
    directory = Path(ROOT_DIR) / "migrations" / "postgres"
    return {path.stem for path in directory.glob("*.sql")}


def production_schema_status() -> dict[str, Any]:
    """Return read-only migration/table evidence for the active PostgreSQL schema."""
    if DATABASE_BACKEND != "postgresql":
        return {"status": "error", "reason": "postgresql_required", "backend": DATABASE_BACKEND}
    try:
        with connect() as conn:
            schema_row = conn.execute("SELECT current_schema() AS schema").fetchone()
            schema = str(schema_row["schema"] if schema_row else "")
            applied = {
                str(row["version"])
                for row in conn.execute("SELECT version FROM schema_migrations")
            }
            table_rows = conn.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema=current_schema() AND table_type='BASE TABLE'"
            )
            tables = {str(row["table_name"]) for row in table_rows}
    except Exception as exc:
        return {"status": "error", "reason": "schema_query_failed", "error_type": type(exc).__name__}

    missing_migrations = sorted(expected_migration_versions() - applied)
    missing_tables = sorted(REQUIRED_TABLES - tables)
    return {
        "status": "ok" if not missing_migrations and not missing_tables else "error",
        "backend": "postgresql",
        "schema": schema,
        "migration_count": len(applied),
        "missing_migrations": missing_migrations,
        "missing_tables": missing_tables,
    }


def assert_production_schema_ready() -> dict[str, Any]:
    status = production_schema_status()
    if status.get("status") != "ok":
        missing = ", ".join(status.get("missing_migrations") or status.get("missing_tables") or [str(status.get("reason", "unknown"))])
        raise RuntimeError(
            "Production database schema is not ready; run the controlled migration job before deploying "
            f"the application (details: {missing})."
        )
    return status
