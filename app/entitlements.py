from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException

from .database import connect
from .identity_billing_schema import ensure_identity_billing_schema


PLAN_CATALOG: dict[str, dict[str, Any]] = {
    "free": {"code": "free", "tier": "free", "name": "Free", "price_usd_monthly": 0, "daily_question_limit": 20, "weekly_mock_limit": 1, "monthly_full_exam_limit": 0},
    "premium_20": {"code": "premium_20", "tier": "premium", "name": "Premium 100", "price_usd_monthly": 20, "daily_question_limit": 100, "weekly_mock_limit": 0, "monthly_full_exam_limit": 2},
    "premium_40": {"code": "premium_40", "tier": "premium", "name": "Premium 250", "price_usd_monthly": 40, "daily_question_limit": 250, "weekly_mock_limit": 0, "monthly_full_exam_limit": 4},
    "premium_100": {"code": "premium_100", "tier": "premium", "name": "Premium 500", "price_usd_monthly": 100, "daily_question_limit": 500, "weekly_mock_limit": 0, "monthly_full_exam_limit": None},
    "exam_pack_35": {"code": "exam_pack_35", "tier": "premium", "name": "One-Time Exam Pack", "price_usd_one_time": 35, "daily_question_limit": None, "weekly_mock_limit": 0, "monthly_full_exam_limit": 1, "lifetime_practice_mock": True, "full_exam_access_days": 30},
}


def plan_details(plan_code: str | None, tier: str = "free") -> dict[str, Any]:
    fallback = "premium_20" if tier == "premium" else "free"
    selected = PLAN_CATALOG.get(plan_code or "")
    return dict(selected if selected and selected["tier"] == tier else PLAN_CATALOG[fallback])


def _periods(now: datetime | None = None) -> dict[str, datetime]:
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    day = current.replace(hour=0, minute=0, second=0, microsecond=0)
    week = day - timedelta(days=day.weekday())
    month = day.replace(day=1)
    next_month = month.replace(year=month.year + (month.month == 12), month=1 if month.month == 12 else month.month + 1)
    return {"day": day, "week": week, "month": month, "next_day": day + timedelta(days=1), "next_week": week + timedelta(days=7), "next_month": next_month}


def _iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def apply_membership_plan(
    candidate_id: int,
    plan_code: str,
    *,
    source: str,
    reason: str,
    provider_event_id: str | None = None,
    expires_at: str | None = None,
) -> dict[str, Any]:
    """Single trusted write path for plan changes.

    Browsers never call this directly. Billing webhooks and explicit local CLI
    tooling are the only intended callers. Actual changes increment an
    entitlement version so stale entitlement caches can be invalidated later.
    """
    ensure_identity_billing_schema()
    plan = PLAN_CATALOG.get(plan_code)
    if not plan:
        raise ValueError(f"Unknown plan: {plan_code}")
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        current = conn.execute(
            "SELECT plan_code, entitlement_version, expires_at FROM candidate_memberships "
            "WHERE candidate_id=? AND status='active' ORDER BY id DESC LIMIT 1",
            (candidate_id,),
        ).fetchone()
        old_plan = current["plan_code"] if current else "free"
        previous_version = int(current["entitlement_version"] if current else 0)
        current_expiry = str(current["expires_at"] or "") if current else ""
        requested_expiry = str(expires_at or "")
        if current and old_plan == plan_code and current_expiry == requested_expiry:
            conn.execute(
                "UPDATE candidate_accounts SET plan=?,updated_at=datetime('now') WHERE id=?",
                (plan["tier"], candidate_id),
            )
            return {"old_plan": old_plan, "new_plan": plan_code, "entitlement_version": previous_version, "changed": False}
        maximum = conn.execute(
            "SELECT COALESCE(MAX(entitlement_version), 0) AS v FROM candidate_memberships WHERE candidate_id=?",
            (candidate_id,),
        ).fetchone()
        next_version = max(previous_version, int(maximum["v"] if maximum else 0)) + 1
        conn.execute(
            "UPDATE candidate_memberships SET status='cancelled', updated_at=datetime('now') "
            "WHERE candidate_id=? AND status='active'",
            (candidate_id,),
        )
        conn.execute(
            "INSERT INTO candidate_memberships(candidate_id,tier,plan_code,status,starts_at,expires_at,source,entitlement_version) "
            "VALUES (?,?,?,'active',datetime('now'),?,?,?)",
            (candidate_id, plan["tier"], plan_code, expires_at, source, next_version),
        )
        conn.execute(
            "UPDATE candidate_accounts SET plan=?,updated_at=datetime('now') WHERE id=?",
            (plan["tier"], candidate_id),
        )
        conn.execute(
            "INSERT INTO membership_audit_log(candidate_id,old_plan,new_plan,reason,source,provider_event_id,entitlement_version) "
            "VALUES (?,?,?,?,?,?,?)",
            (candidate_id, old_plan, plan_code, reason, source, provider_event_id, next_version),
        )
        conn.execute(
            "INSERT INTO membership_events(candidate_id,previous_plan,next_plan,source) VALUES (?,?,?,?)",
            (candidate_id, old_plan, plan_code, source),
        )
    return {"old_plan": old_plan, "new_plan": plan_code, "entitlement_version": next_version, "changed": True}


def entitlement_usage(candidate_id: int, membership: dict[str, Any]) -> dict[str, Any]:
    periods = _periods()
    plan = plan_details(membership.get("plan_code"), membership.get("tier") or "free")
    with connect() as conn:
        daily = conn.execute("SELECT questions_consumed FROM candidate_daily_question_usage WHERE candidate_id = ? AND usage_date = ?", (candidate_id, periods["day"].date().isoformat())).fetchone()
        weekly = conn.execute("SELECT COUNT(*) AS count FROM exam_sessions WHERE candidate_id = ? AND mode = 'exam_weekly_mock' AND datetime(started_at) >= datetime(?)", (candidate_id, periods["week"].isoformat())).fetchone()
        monthly = conn.execute("SELECT COUNT(*) AS count FROM exam_sessions WHERE candidate_id = ? AND mode IN ('exam_full_mock', 'exam_source') AND datetime(started_at) >= datetime(?)", (candidate_id, periods["month"].isoformat())).fetchone()
    daily_used = int(daily["questions_consumed"] if daily else 0)
    weekly_used = int(weekly["count"] if weekly else 0)
    monthly_used = int(monthly["count"] if monthly else 0)
    daily_limit = plan["daily_question_limit"]
    weekly_limit = int(plan["weekly_mock_limit"])
    monthly_limit = plan["monthly_full_exam_limit"]
    exam_pack = plan["code"] == "exam_pack_35"
    deadline: datetime | None = None
    if exam_pack:
        # A paid Exam Pack keeps the original purchase timestamp even if a
        # subscription temporarily becomes the active membership and the pack
        # later becomes the fallback entitlement. Development CLI packs, which
        # have no billing purchase, continue to use the membership start time.
        with connect() as conn:
            purchase = conn.execute(
                "SELECT purchased_at FROM billing_purchases WHERE candidate_id=? AND product_type='exam_pack_35' AND status='paid' ORDER BY id DESC LIMIT 1",
                (candidate_id,),
            ).fetchone()
        anchor = purchase["purchased_at"] if purchase else membership.get("starts_at")
        started = datetime.fromisoformat(str(anchor or periods["day"].isoformat()).replace("Z", "+00:00"))
        started = started.replace(tzinfo=timezone.utc) if started.tzinfo is None else started.astimezone(timezone.utc)
        deadline = started + timedelta(days=int(plan["full_exam_access_days"]))
        with connect() as conn:
            packed = conn.execute("SELECT COUNT(*) AS count FROM exam_sessions WHERE candidate_id = ? AND mode IN ('exam_full_mock', 'exam_source') AND datetime(started_at) >= datetime(?)", (candidate_id, started.isoformat())).fetchone()
        monthly_used = int(packed["count"] if packed else 0)
    return {
        "daily_questions": {"used": daily_used, "limit": daily_limit, "remaining": None if daily_limit is None else max(0, int(daily_limit) - daily_used), "resets_at": None if daily_limit is None else _iso(periods["next_day"])},
        "weekly_mocks": {"used": weekly_used, "limit": weekly_limit, "remaining": max(0, weekly_limit - weekly_used), "resets_at": _iso(periods["next_week"])},
        "monthly_full_exams": {"used": monthly_used, "limit": monthly_limit, "remaining": None if monthly_limit is None else max(0, int(monthly_limit) - monthly_used), "resets_at": _iso(deadline) if deadline else _iso(periods["next_month"]), "access_expires_at": _iso(deadline) if deadline else None},
    }


def reserve_daily_questions(candidate_id: int, membership: dict[str, Any], requested: int) -> dict[str, Any]:
    requested = max(0, int(requested))
    plan = plan_details(membership.get("plan_code"), membership.get("tier") or "free")
    usage_date = _periods()["day"].date().isoformat()
    if plan["daily_question_limit"] is None:
        return {"used": 0, "limit": None, "remaining": None}
    limit = int(plan["daily_question_limit"])
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT questions_consumed FROM candidate_daily_question_usage WHERE candidate_id = ? AND usage_date = ?", (candidate_id, usage_date)).fetchone()
        used = int(row["questions_consumed"] if row else 0)
        if requested > max(0, limit - used):
            raise HTTPException(status_code=403, detail={"code": "daily_question_limit_reached", "message": f"Your {plan['name']} daily question allowance has been reached. It resets at 00:00 UTC.", "limit": limit, "used": used, "remaining": max(0, limit - used)})
        conn.execute(
            "INSERT INTO candidate_daily_question_usage(candidate_id, usage_date, questions_consumed) VALUES (?, ?, ?) "
            "ON CONFLICT(candidate_id, usage_date) DO UPDATE SET "
            "questions_consumed = candidate_daily_question_usage.questions_consumed + excluded.questions_consumed, "
            "updated_at = datetime('now')",
            (candidate_id, usage_date, requested),
        )
    return {"used": used + requested, "limit": limit, "remaining": max(0, limit - used - requested)}


def validate_mock_start(candidate: dict[str, Any], mode: str) -> str:
    membership = candidate["membership"]
    plan = plan_details(membership.get("plan_code"), membership.get("tier") or "free")
    normalized = mode.strip().lower().replace("_", "-")
    usage = entitlement_usage(candidate["id"], membership)
    if plan["code"] == "exam_pack_35":
        if normalized == "lifetime-practice":
            return normalized
        if normalized not in {"full-mock", "source-exam"}:
            raise HTTPException(status_code=403, detail={"code": "exam_pack_mode_required", "message": "The One-Time Exam Pack includes the lifetime 100-question Practice Mock and one Full Exam attempt."})
        deadline = usage["monthly_full_exams"].get("access_expires_at")
        if deadline and datetime.now(timezone.utc) >= datetime.fromisoformat(deadline.replace("Z", "+00:00")):
            raise HTTPException(status_code=403, detail={"code": "exam_pack_full_exam_expired", "message": "The 30-day window for the included Full Exam has expired. Lifetime Practice Mock access remains active.", "expired_at": deadline})
        if usage["monthly_full_exams"]["remaining"] < 1:
            raise HTTPException(status_code=403, detail={"code": "exam_pack_full_exam_used", "message": "The included Full Exam attempt has already been started. Lifetime Practice Mock access remains active."})
        return normalized
    if plan["tier"] == "free":
        if normalized != "weekly-mock":
            raise HTTPException(status_code=403, detail={"code": "premium_required", "message": "Free includes one 20-question timed mock per week. Choose Weekly Mock or upgrade for Quick and Full mocks."})
        if usage["weekly_mocks"]["remaining"] < 1:
            raise HTTPException(status_code=403, detail={"code": "weekly_mock_limit_reached", "message": "Your weekly Free mock has already been started. It resets Monday at 00:00 UTC.", **usage["weekly_mocks"]})
        return "weekly-mock"
    if normalized == "weekly-mock":
        normalized = "quick-mock"
    if normalized in {"full-mock", "source-exam"}:
        remaining = usage["monthly_full_exams"]["remaining"]
        if remaining is not None and remaining < 1:
            raise HTTPException(status_code=403, detail={"code": "monthly_full_exam_limit_reached", "message": "Your monthly full-exam allowance has been used. It resets on the first day of next month at 00:00 UTC.", **usage["monthly_full_exams"]})
    return normalized
