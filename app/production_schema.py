"""Read-only hosted schema and runtime-role verification.

Schema mutation belongs to the controlled deployment migration job. Vercel
functions call this module only to prove that their runtime credential can read
and write the already-migrated application schema while remaining incapable of
DDL, role administration, database creation, or ownership escalation.
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


def _privilege_status(conn: Any, schema: str, tables: set[str]) -> dict[str, Any]:
    role_row = conn.execute(
        """
        SELECT current_user AS runtime_role,
               rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls
        FROM pg_roles
        WHERE rolname=current_user
        """
    ).fetchone()
    if not role_row:
        return {"status": "error", "reason": "runtime_role_not_found"}

    database_row = conn.execute(
        "SELECT pg_get_userbyid(datdba) AS owner FROM pg_database WHERE datname=current_database()"
    ).fetchone()
    schema_row = conn.execute(
        "SELECT pg_get_userbyid(nspowner) AS owner FROM pg_namespace WHERE nspname=current_schema()"
    ).fetchone()
    capability_row = conn.execute(
        """
        SELECT has_database_privilege(current_user, current_database(), 'CREATE') AS database_create,
               has_schema_privilege(current_user, current_schema(), 'CREATE') AS schema_create
        """
    ).fetchone()

    runtime_role = str(role_row["runtime_role"])
    database_owner = str((database_row or {}).get("owner") or "")
    schema_owner = str((schema_row or {}).get("owner") or "")
    unsafe: list[str] = []
    for key in ("rolsuper", "rolcreatedb", "rolcreaterole", "rolreplication", "rolbypassrls"):
        if bool(role_row.get(key)):
            unsafe.append(key)
    if runtime_role and runtime_role == database_owner:
        unsafe.append("database_owner")
    if runtime_role and runtime_role == schema_owner:
        unsafe.append("schema_owner")
    if bool((capability_row or {}).get("database_create")):
        unsafe.append("database_create")
    if bool((capability_row or {}).get("schema_create")):
        unsafe.append("schema_create")

    # The controlled migration job grants DML to every application table. Verify
    # that the runtime can perform that work without having to fall back to an
    # owner/DDL credential.
    missing_table_dml: list[str] = []
    for table in sorted(tables):
        row = conn.execute(
            "SELECT has_table_privilege(current_user, format('%I.%I', ?, ?), 'SELECT,INSERT,UPDATE,DELETE') AS ok",
            (schema, table),
        ).fetchone()
        if not row or not bool(row.get("ok")):
            missing_table_dml.append(table)

    sequence_rows = [
        str(row["sequence_name"])
        for row in conn.execute(
            "SELECT sequence_name FROM information_schema.sequences WHERE sequence_schema=current_schema()"
        )
    ]
    missing_sequence_dml: list[str] = []
    for sequence in sequence_rows:
        row = conn.execute(
            "SELECT has_sequence_privilege(current_user, format('%I.%I', ?, ?), 'USAGE,SELECT,UPDATE') AS ok",
            (schema, sequence),
        ).fetchone()
        if not row or not bool(row.get("ok")):
            missing_sequence_dml.append(sequence)

    return {
        "status": "ok" if not unsafe and not missing_table_dml and not missing_sequence_dml else "error",
        "runtime_role": runtime_role,
        "database_owner": database_owner,
        "schema_owner": schema_owner,
        "unsafe_capabilities": sorted(set(unsafe)),
        "missing_table_dml": missing_table_dml,
        "missing_sequence_dml": missing_sequence_dml,
    }


def production_schema_status() -> dict[str, Any]:
    """Return read-only migration/table/least-privilege evidence."""
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
            privilege = _privilege_status(conn, schema, tables)
    except Exception as exc:
        return {"status": "error", "reason": "schema_query_failed", "error_type": type(exc).__name__}

    missing_migrations = sorted(expected_migration_versions() - applied)
    missing_tables = sorted(REQUIRED_TABLES - tables)
    ready = not missing_migrations and not missing_tables and privilege.get("status") == "ok"
    return {
        "status": "ok" if ready else "error",
        "backend": "postgresql",
        "schema": schema,
        "migration_count": len(applied),
        "missing_migrations": missing_migrations,
        "missing_tables": missing_tables,
        "runtime_role": privilege.get("runtime_role"),
        "unsafe_runtime_capabilities": privilege.get("unsafe_capabilities") or [],
        "missing_runtime_table_dml": privilege.get("missing_table_dml") or [],
        "missing_runtime_sequence_dml": privilege.get("missing_sequence_dml") or [],
    }


def assert_production_schema_ready() -> dict[str, Any]:
    status = production_schema_status()
    if status.get("status") != "ok":
        details = (
            status.get("missing_migrations")
            or status.get("missing_tables")
            or status.get("unsafe_runtime_capabilities")
            or status.get("missing_runtime_table_dml")
            or status.get("missing_runtime_sequence_dml")
            or [str(status.get("reason", "unknown"))]
        )
        detail_text = ", ".join(str(item) for item in details)
        raise RuntimeError(
            "Production database/runtime role is not ready; run the controlled migration/privilege job "
            f"before deploying the application (details: {detail_text})."
        )
    return status
