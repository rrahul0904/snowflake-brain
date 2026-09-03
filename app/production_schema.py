"""Read-only hosted schema and runtime-role verification.

Schema mutation belongs to the controlled deployment migration job. Vercel
functions call this module only to prove that their runtime credential can read
the already-migrated application schema, write only candidate/runtime state,
and cannot mutate certification content, release governance, editorial state,
or the migration ledger.
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
        "exam_session_events",
        "candidate_srs_state",
        "candidate_task_reviews",
        "candidate_mistake_notebook",
        "candidate_readiness_snapshots",
        "feedback_submissions",
        "candidate_credentials",
    }
)

# Only these tables may be mutated by the request-serving application role.
# Certification/question definitions, release/editorial administration, source
# freshness, and schema migration state deliberately remain read-only even if
# the application credential is compromised.
RUNTIME_WRITE_TABLES = frozenset(
    {
        "candidate_accounts",
        "candidate_sessions",
        "membership_events",
        "candidate_memberships",
        "candidate_task_progress",
        "candidate_daily_activity",
        "candidate_daily_question_usage",
        "question_attempts",
        "exam_sessions",
        "exam_session_questions",
        "exam_session_answers",
        "exam_session_events",
        "question_exposure_stats",
        "candidate_question_history",
        "candidate_exam_pack_sets",
        "candidate_exam_pack_set_questions",
        "candidate_bookmarks",
        "candidate_notes",
        "learning_events",
        "candidate_identities",
        "oauth_login_flows",
        "pending_identity_links",
        "billing_customers",
        "billing_checkout_sessions",
        "billing_subscriptions",
        "billing_purchases",
        "billing_events",
        "membership_audit_log",
        "candidate_srs_state",
        "candidate_task_reviews",
        "candidate_mistake_notebook",
        "candidate_study_preferences",
        "candidate_learning_attempt_sync",
        "exam_entitlement_reservations",
        "feedback_submissions",
        "account_action_tokens",
        "account_audit_events",
        "account_deletion_receipts",
        "candidate_readiness_snapshots",
        "candidate_adaptive_recommendations",
        "candidate_talent_profiles",
        "candidate_credentials",
        "credential_verification_events",
    }
)


def expected_migration_versions() -> set[str]:
    directory = Path(ROOT_DIR) / "migrations" / "postgres"
    return {path.stem for path in directory.glob("*.sql")}


def _table_privileges(conn: Any, schema: str, table: str) -> dict[str, bool]:
    # PostgreSQL cannot infer the data type of parameters passed only through
    # format('%I', ...). Explicit text casts keep the query parameterized while
    # allowing has_table_privilege() to resolve the safely quoted relation name.
    row = conn.execute(
        """
        SELECT has_table_privilege(current_user, format('%I.%I', ?::text, ?::text), 'SELECT') AS can_select,
               has_table_privilege(current_user, format('%I.%I', ?::text, ?::text), 'INSERT') AS can_insert,
               has_table_privilege(current_user, format('%I.%I', ?::text, ?::text), 'UPDATE') AS can_update,
               has_table_privilege(current_user, format('%I.%I', ?::text, ?::text), 'DELETE') AS can_delete,
               has_table_privilege(current_user, format('%I.%I', ?::text, ?::text), 'TRUNCATE') AS can_truncate,
               has_table_privilege(current_user, format('%I.%I', ?::text, ?::text), 'REFERENCES') AS can_references,
               has_table_privilege(current_user, format('%I.%I', ?::text, ?::text), 'TRIGGER') AS can_trigger
        """,
        (schema, table, schema, table, schema, table, schema, table, schema, table, schema, table, schema, table),
    ).fetchone()
    return {
        "select": bool((row or {}).get("can_select")),
        "insert": bool((row or {}).get("can_insert")),
        "update": bool((row or {}).get("can_update")),
        "delete": bool((row or {}).get("can_delete")),
        "truncate": bool((row or {}).get("can_truncate")),
        "references": bool((row or {}).get("can_references")),
        "trigger": bool((row or {}).get("can_trigger")),
    }


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

    missing_select: list[str] = []
    missing_write: list[str] = []
    excessive_write: list[str] = []
    elevated_table_privileges: list[str] = []
    for table in sorted(tables):
        privilege = _table_privileges(conn, schema, table)
        if not privilege["select"]:
            missing_select.append(table)
        writable = privilege["insert"] and privilege["update"] and privilege["delete"]
        if table in RUNTIME_WRITE_TABLES:
            if not writable:
                missing_write.append(table)
        elif privilege["insert"] or privilege["update"] or privilege["delete"]:
            excessive_write.append(table)
        if privilege["truncate"] or privilege["references"] or privilege["trigger"]:
            elevated_table_privileges.append(table)

    sequence_rows = [
        str(row["sequence_name"])
        for row in conn.execute(
            "SELECT sequence_name FROM information_schema.sequences WHERE sequence_schema=current_schema()"
        )
    ]
    missing_sequence_usage: list[str] = []
    for sequence in sequence_rows:
        row = conn.execute(
            "SELECT has_sequence_privilege(current_user, format('%I.%I', ?::text, ?::text), 'USAGE') AS ok",
            (schema, sequence),
        ).fetchone()
        if not row or not bool(row.get("ok")):
            missing_sequence_usage.append(sequence)

    clean = not (
        unsafe
        or missing_select
        or missing_write
        or excessive_write
        or elevated_table_privileges
        or missing_sequence_usage
    )
    return {
        "status": "ok" if clean else "error",
        "runtime_role": runtime_role,
        "database_owner": database_owner,
        "schema_owner": schema_owner,
        "unsafe_capabilities": sorted(set(unsafe)),
        "missing_select": missing_select,
        "missing_write": missing_write,
        "excessive_write": excessive_write,
        "elevated_table_privileges": elevated_table_privileges,
        "missing_sequence_usage": missing_sequence_usage,
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
    unknown_write_tables = sorted(RUNTIME_WRITE_TABLES - tables)
    ready = (
        not missing_migrations
        and not missing_tables
        and not unknown_write_tables
        and privilege.get("status") == "ok"
    )
    return {
        "status": "ok" if ready else "error",
        "backend": "postgresql",
        "schema": schema,
        "migration_count": len(applied),
        "missing_migrations": missing_migrations,
        "missing_tables": missing_tables,
        "missing_runtime_write_tables": unknown_write_tables,
        "runtime_role": privilege.get("runtime_role"),
        "unsafe_runtime_capabilities": privilege.get("unsafe_capabilities") or [],
        "missing_runtime_select": privilege.get("missing_select") or [],
        "missing_runtime_write": privilege.get("missing_write") or [],
        "excessive_runtime_write": privilege.get("excessive_write") or [],
        "elevated_runtime_table_privileges": privilege.get("elevated_table_privileges") or [],
        "missing_runtime_sequence_usage": privilege.get("missing_sequence_usage") or [],
    }


def assert_production_schema_ready() -> dict[str, Any]:
    status = production_schema_status()
    if status.get("status") != "ok":
        details = (
            status.get("missing_migrations")
            or status.get("missing_tables")
            or status.get("missing_runtime_write_tables")
            or status.get("unsafe_runtime_capabilities")
            or status.get("missing_runtime_select")
            or status.get("missing_runtime_write")
            or status.get("excessive_runtime_write")
            or status.get("elevated_runtime_table_privileges")
            or status.get("missing_runtime_sequence_usage")
            or [str(status.get("reason", "unknown"))]
        )
        detail_text = ", ".join(str(item) for item in details)
        raise RuntimeError(
            "Production database/runtime role is not ready; run the controlled migration/privilege job "
            f"before deploying the application (details: {detail_text})."
        )
    return status
