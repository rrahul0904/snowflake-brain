"""Privacy-safe, server-side admin reporting and operations helpers.

The console never derives metrics in the browser and never returns question
text, credentials, tokens, or provider secrets.  Date windows are expressed as
UTC ISO strings so SQLite and PostgreSQL share deterministic grouping rules.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException

from .config import (
    ADMIN_REPORTING_TIMEZONE,
    BILLING_ENABLED,
    DATABASE_BACKEND,
    GOOGLE_AUTH_ENABLED,
    OBSERVABILITY_ENABLED,
)
from .database import connect, database_health


_LOCK = threading.RLock()
_READY: set[str] = set()


def _database_key(conn: Any) -> str:
    if DATABASE_BACKEND == "postgresql":
        return "postgresql"
    row = conn.execute("PRAGMA database_list").fetchone()
    return str((dict(row) if row else {}).get("file") or "sqlite")


def ensure_admin_operations_schema() -> None:
    """Create local/CI compatibility tables; production uses migration 023."""
    if DATABASE_BACKEND == "postgresql":
        return
    with _LOCK:
        with connect() as conn:
            key = _database_key(conn)
            if key in _READY:
                return
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS admin_audit_events (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  actor_candidate_id INTEGER REFERENCES candidate_accounts(id) ON DELETE SET NULL,
                  event TEXT NOT NULL, target_type TEXT NOT NULL DEFAULT '', target_id TEXT NOT NULL DEFAULT '',
                  result TEXT NOT NULL DEFAULT 'success', metadata_json TEXT NOT NULL DEFAULT '{}',
                  created_at TEXT NOT NULL DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_admin_audit_events_created ON admin_audit_events(created_at DESC, id DESC);
                CREATE TABLE IF NOT EXISTS finops_cost_snapshots (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  service_provider TEXT NOT NULL, service_name TEXT NOT NULL, cost_category TEXT NOT NULL,
                  period_start TEXT NOT NULL, period_end TEXT NOT NULL, amount REAL, currency TEXT NOT NULL DEFAULT 'USD',
                  measurement_source TEXT NOT NULL, evidence_classification TEXT NOT NULL,
                  usage_quantity REAL, usage_unit TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT '',
                  created_at TEXT NOT NULL DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_finops_period ON finops_cost_snapshots(period_start, service_provider, cost_category);
                CREATE TABLE IF NOT EXISTS operations_daily_snapshots (
                  snapshot_date TEXT PRIMARY KEY, registrations INTEGER NOT NULL DEFAULT 0,
                  active_users INTEGER NOT NULL DEFAULT 0, paid_users INTEGER NOT NULL DEFAULT 0,
                  new_subscribers INTEGER NOT NULL DEFAULT 0, mrr REAL, revenue REAL,
                  questions_answered INTEGER NOT NULL DEFAULT 0, mock_submissions INTEGER NOT NULL DEFAULT 0,
                  average_readiness REAL, api_errors INTEGER NOT NULL DEFAULT 0, estimated_cost REAL,
                  daily_active_users INTEGER NOT NULL DEFAULT 0, weekly_active_users INTEGER NOT NULL DEFAULT 0,
                  monthly_active_users INTEGER NOT NULL DEFAULT 0, practice_sessions INTEGER NOT NULL DEFAULT 0,
                  review_completions INTEGER NOT NULL DEFAULT 0,
                  generated_at TEXT NOT NULL DEFAULT (datetime('now'))
                );
                CREATE TABLE IF NOT EXISTS deployment_records (
                  id INTEGER PRIMARY KEY AUTOINCREMENT, deployment_sha TEXT NOT NULL, environment TEXT NOT NULL,
                  status TEXT NOT NULL, source_branch TEXT NOT NULL DEFAULT '', deployment_reason TEXT NOT NULL DEFAULT '',
                  release_candidate TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT (datetime('now')),
                  UNIQUE(deployment_sha, environment, created_at)
                );
                CREATE INDEX IF NOT EXISTS idx_deployment_records_created ON deployment_records(created_at DESC, environment);
                """
            )
            snapshot_columns = {str(row["name"]) for row in conn.execute("PRAGMA table_info(operations_daily_snapshots)").fetchall()}
            for name in ("daily_active_users", "weekly_active_users", "monthly_active_users", "practice_sessions", "review_completions"):
                if name not in snapshot_columns:
                    conn.execute(f"ALTER TABLE operations_daily_snapshots ADD COLUMN {name} INTEGER NOT NULL DEFAULT 0")
            _READY.add(key)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _cutoff(days: int) -> str:
    return (_utc_now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")


def _scalar(conn: Any, statement: str, params: tuple[Any, ...] = ()) -> int | float:
    row = conn.execute(statement, params).fetchone()
    return (dict(row) if row else {}).get("value") or 0


def require_admin(candidate: dict[str, Any]) -> dict[str, Any]:
    ensure_admin_operations_schema()
    with connect() as conn:
        row = conn.execute("SELECT role, status FROM candidate_accounts WHERE id=?", (candidate["id"],)).fetchone()
    value = dict(row) if row else {}
    if not row or value.get("status") != "active" or value.get("role") != "admin":
        raise HTTPException(status_code=403, detail={"code": "admin_required", "message": "Administrator access is required."})
    return candidate


def audit(actor_id: int, event: str, *, target_type: str = "", target_id: str = "", result: str = "success", metadata: dict[str, Any] | None = None) -> None:
    ensure_admin_operations_schema()
    safe_metadata = {str(k): v for k, v in (metadata or {}).items() if str(k).lower() not in {"secret", "token", "password", "dsn"}}
    with connect() as conn:
        conn.execute(
            "INSERT INTO admin_audit_events(actor_candidate_id,event,target_type,target_id,result,metadata_json) VALUES (?,?,?,?,?,?)",
            (actor_id, event, target_type, target_id, result, json.dumps(safe_metadata, separators=(",", ":"), sort_keys=True)),
        )


def _plan_mrr(plan: str) -> float:
    return {"premium_100": 20.0, "premium_250": 40.0, "premium_500": 100.0}.get(plan, 0.0)


def overview() -> dict[str, Any]:
    ensure_admin_operations_schema()
    today = _cutoff(1)
    week = _cutoff(7)
    month = _cutoff(30)
    with connect() as conn:
        users = {
            "total": int(_scalar(conn, "SELECT COUNT(*) AS value FROM candidate_accounts")),
            "today": int(_scalar(conn, "SELECT COUNT(*) AS value FROM candidate_accounts WHERE created_at>=?", (today,))),
            "seven_days": int(_scalar(conn, "SELECT COUNT(*) AS value FROM candidate_accounts WHERE created_at>=?", (week,))),
            "thirty_days": int(_scalar(conn, "SELECT COUNT(*) AS value FROM candidate_accounts WHERE created_at>=?", (month,))),
            "active_today": int(_scalar(conn, "SELECT COUNT(*) AS value FROM candidate_accounts WHERE last_login_at>=?", (today,))),
            "active_seven_days": int(_scalar(conn, "SELECT COUNT(*) AS value FROM candidate_accounts WHERE last_login_at>=?", (week,))),
            "active_thirty_days": int(_scalar(conn, "SELECT COUNT(*) AS value FROM candidate_accounts WHERE last_login_at>=?", (month,))),
            "verified": int(_scalar(conn, "SELECT COUNT(*) AS value FROM candidate_accounts WHERE email_verified=1")),
            "google": int(_scalar(conn, "SELECT COUNT(DISTINCT candidate_id) AS value FROM candidate_identities WHERE provider='google'")),
        }
        users["password"] = max(0, users["total"] - users["google"])
        learning = {
            "questions_today": int(_scalar(conn, "SELECT COUNT(*) AS value FROM question_attempts WHERE attempted_at>=?", (today,))),
            "sessions_today": int(_scalar(conn, "SELECT COUNT(DISTINCT candidate_id) AS value FROM question_attempts WHERE attempted_at>=?", (today,))),
            "mocks_started": int(_scalar(conn, "SELECT COUNT(*) AS value FROM exam_sessions WHERE started_at>=?", (today,))),
            "mocks_completed": int(_scalar(conn, "SELECT COUNT(*) AS value FROM exam_sessions WHERE finished_at>=? AND status='submitted'", (today,))),
        }
        subscription_rows = conn.execute("SELECT internal_plan,status FROM billing_subscriptions").fetchall()
        subscription_rows = [dict(row) for row in subscription_rows]
        active = [row for row in subscription_rows if row.get("status") in {"active", "trialing"}]
        subscriptions = {
            "free": int(_scalar(conn, "SELECT COUNT(*) AS value FROM candidate_accounts WHERE plan='free'")),
            "active": len(active),
            "canceled": sum(1 for row in subscription_rows if row.get("status") == "canceled"),
            "past_due": sum(1 for row in subscription_rows if row.get("status") == "past_due"),
            "mrr": round(sum(_plan_mrr(str(row.get("internal_plan") or "")) for row in active), 2),
        }
        subscriptions["arr"] = round(subscriptions["mrr"] * 12, 2)
        finops = _finops_summary(conn)
        releases = conn.execute("SELECT release_key,status,question_count,activated_at FROM question_bank_releases WHERE status='active' ORDER BY activated_at DESC LIMIT 1").fetchone()
    return {
        "reporting_timezone": ADMIN_REPORTING_TIMEZONE,
        "users": users, "learning": learning, "subscriptions": subscriptions,
        "finops": finops,
        "question_bank": dict(releases) if releases else {"status": "not_active", "question_count": 0},
        "system": system_status(),
    }


def registrations(period: str = "daily") -> dict[str, Any]:
    ensure_admin_operations_schema()
    days = {"daily": 30, "weekly": 84, "monthly": 365}.get(period, 30)
    with connect() as conn:
        rows = conn.execute(
            "SELECT substr(created_at,1,10) AS date, COUNT(*) AS registrations FROM candidate_accounts WHERE created_at>=? GROUP BY substr(created_at,1,10) ORDER BY date DESC LIMIT ?",
            (_cutoff(days), days),
        ).fetchall()
    return {"period": period, "reporting_timezone": ADMIN_REPORTING_TIMEZONE, "rows": [dict(row) for row in rows]}


def users(page: int, page_size: int, filters: dict[str, str]) -> dict[str, Any]:
    ensure_admin_operations_schema()
    page = max(1, page); page_size = min(max(1, page_size), 100)
    clauses: list[str] = ["1=1"]; params: list[Any] = []
    if filters.get("plan"):
        clauses.append("a.plan=?"); params.append(filters["plan"])
    if filters.get("provider"):
        clauses.append("EXISTS(SELECT 1 FROM candidate_identities i WHERE i.candidate_id=a.id AND i.provider=?)"); params.append(filters["provider"])
    if filters.get("active") == "true":
        clauses.append("a.last_login_at>=?"); params.append(_cutoff(30))
    where = " AND ".join(clauses)
    with connect() as conn:
        total = int(_scalar(conn, f"SELECT COUNT(*) AS value FROM candidate_accounts a WHERE {where}", tuple(params)))
        rows = conn.execute(
            f"""SELECT a.id,a.created_at,a.status,a.email,a.display_name,a.plan,a.last_login_at,
                 (SELECT provider FROM candidate_identities i WHERE i.candidate_id=a.id ORDER BY provider LIMIT 1) AS auth_provider,
                 (SELECT COUNT(*) FROM question_attempts q WHERE q.candidate_id=a.id) AS questions_used,
                 (SELECT COUNT(*) FROM exam_sessions e WHERE e.candidate_id=a.id) AS mock_count
                 FROM candidate_accounts a WHERE {where} ORDER BY a.created_at DESC LIMIT ? OFFSET ?""",
            tuple(params + [page_size, (page - 1) * page_size]),
        ).fetchall()
    safe = [{key: value for key, value in dict(row).items() if key not in {"password_hash", "password_salt"}} for row in rows]
    return {"page": page, "page_size": page_size, "total": total, "rows": safe}


def subscriptions(page: int = 1, page_size: int = 50) -> dict[str, Any]:
    ensure_admin_operations_schema()
    page = max(1, page); page_size = min(max(1, page_size), 100)
    with connect() as conn:
        total = int(_scalar(conn, "SELECT COUNT(*) AS value FROM billing_subscriptions"))
        kpi_rows = [dict(row) for row in conn.execute("SELECT internal_plan,status FROM billing_subscriptions").fetchall()]
        rows = conn.execute(
            "SELECT s.candidate_id,s.provider_customer_id,s.provider_subscription_id,s.internal_plan,s.status,s.current_period_end,s.cancel_at_period_end,s.created_at,a.email FROM billing_subscriptions s JOIN candidate_accounts a ON a.id=s.candidate_id ORDER BY s.created_at DESC LIMIT ? OFFSET ?",
            (page_size, (page - 1) * page_size),
        ).fetchall()
    safe_rows = []
    for row in rows:
        value = dict(row); value["mrr_contribution"] = _plan_mrr(str(value.get("internal_plan") or "")); safe_rows.append(value)
    active = [row for row in kpi_rows if row.get("status") in {"active", "trialing"}]
    mrr = round(sum(_plan_mrr(str(row.get("internal_plan") or "")) for row in active), 2)
    return {"page": page, "page_size": page_size, "total": total, "kpis": {"active_subscribers": len(active), "mrr": mrr, "arr": round(mrr * 12, 2), "churn_rate": None}, "rows": safe_rows}


def _finops_summary(conn: Any) -> dict[str, Any]:
    rows = conn.execute("SELECT service_provider,cost_category,amount,evidence_classification FROM finops_cost_snapshots WHERE period_start>=?", (_cutoff(31),)).fetchall()
    values = [dict(row) for row in rows]
    amount = sum(float(row.get("amount") or 0) for row in values)
    return {"monthly_cost": round(amount, 2) if values else None, "evidence": sorted(set(row.get("evidence_classification") for row in values)) or ["NOT_CONNECTED"], "providers_connected": sorted(set(row.get("service_provider") for row in values))}


def finops(page: int = 1, page_size: int = 50) -> dict[str, Any]:
    ensure_admin_operations_schema()
    page = max(1, page); page_size = min(max(1, page_size), 100)
    with connect() as conn:
        total = int(_scalar(conn, "SELECT COUNT(*) AS value FROM finops_cost_snapshots"))
        rows = conn.execute("SELECT service_provider,service_name,cost_category,period_start,period_end,amount,currency,measurement_source,evidence_classification,usage_quantity,usage_unit,notes FROM finops_cost_snapshots ORDER BY period_start DESC,id DESC LIMIT ? OFFSET ?", (page_size, (page - 1) * page_size)).fetchall()
        summary = _finops_summary(conn)
        user_count = int(_scalar(conn, "SELECT COUNT(*) AS value FROM candidate_accounts"))
        paid_count = int(_scalar(conn, "SELECT COUNT(*) AS value FROM billing_subscriptions WHERE status IN ('active','trialing')"))
    cost = summary["monthly_cost"]
    return {"page": page, "page_size": page_size, "total": total, "summary": summary, "unit_economics": {"cost_per_registered_user": round(cost / user_count, 2) if cost is not None and user_count else None, "cost_per_paid_user": round(cost / paid_count, 2) if cost is not None and paid_count else None}, "rows": [dict(row) for row in rows]}


def question_bank() -> dict[str, Any]:
    ensure_admin_operations_schema()
    with connect() as conn:
        release = conn.execute("SELECT release_key,track_id,status,question_count,source_fingerprint,created_at,activated_at FROM question_bank_releases ORDER BY created_at DESC LIMIT 1").fetchone()
        pools = conn.execute("SELECT bank_pool,COUNT(*) AS count FROM question_bank_metadata GROUP BY bank_pool").fetchall()
        quality = conn.execute("SELECT COUNT(*) AS total, SUM(CASE WHEN q.explanation='' THEN 1 ELSE 0 END) AS missing_explanations, SUM(CASE WHEN m.source_refs_json='[]' THEN 1 ELSE 0 END) AS missing_provenance FROM questions q JOIN question_bank_metadata m ON m.question_id=q.id").fetchone()
    return {"release": dict(release) if release else {"status": "not_active"}, "pools": [dict(row) for row in pools], "quality": dict(quality or {})}


def usage() -> dict[str, Any]:
    ensure_admin_operations_schema()
    with connect() as conn:
        rows = conn.execute("SELECT substr(attempted_at,1,10) AS date,COUNT(*) AS questions_answered,COUNT(DISTINCT candidate_id) AS active_learners FROM question_attempts WHERE attempted_at>=? GROUP BY substr(attempted_at,1,10) ORDER BY date DESC", (_cutoff(30),)).fetchall()
    return {"reporting_timezone": ADMIN_REPORTING_TIMEZONE, "rows": [dict(row) for row in rows]}


def system_status() -> dict[str, Any]:
    ensure_admin_operations_schema()
    try:
        db = database_health()
        database = "healthy" if db.get("status") == "ok" else "degraded"
    except Exception:
        database = "degraded"
    return {"database": database, "database_backend": DATABASE_BACKEND, "runtime_role": "snowflake_app_runtime" if DATABASE_BACKEND == "postgresql" else "local_ci", "billing": "enabled" if BILLING_ENABLED else "disabled", "google_auth": "enabled" if GOOGLE_AUTH_ENABLED else "disabled", "observability": "connected" if OBSERVABILITY_ENABLED else "disabled", "reporting_timezone": ADMIN_REPORTING_TIMEZONE}


def deployments(page: int = 1, page_size: int = 50) -> dict[str, Any]:
    ensure_admin_operations_schema()
    page = max(1, page); page_size = min(max(1, page_size), 100)
    with connect() as conn:
        total = int(_scalar(conn, "SELECT COUNT(*) AS value FROM deployment_records"))
        rows = conn.execute("SELECT deployment_sha,environment,status,source_branch,deployment_reason,release_candidate,created_at FROM deployment_records ORDER BY created_at DESC LIMIT ? OFFSET ?", (page_size, (page - 1) * page_size)).fetchall()
    return {"page": page, "page_size": page_size, "total": total, "cost_data": "NOT_CONNECTED", "rows": [dict(row) for row in rows]}


def audit_log(page: int = 1, page_size: int = 50) -> dict[str, Any]:
    ensure_admin_operations_schema()
    page = max(1, page); page_size = min(max(1, page_size), 100)
    with connect() as conn:
        total = int(_scalar(conn, "SELECT COUNT(*) AS value FROM admin_audit_events"))
        rows = conn.execute("SELECT event,target_type,target_id,result,metadata_json,created_at FROM admin_audit_events ORDER BY created_at DESC,id DESC LIMIT ? OFFSET ?", (page_size, (page - 1) * page_size)).fetchall()
    return {"page": page, "page_size": page_size, "total": total, "rows": [dict(row) for row in rows]}
