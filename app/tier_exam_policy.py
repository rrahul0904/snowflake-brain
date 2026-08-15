from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException

from .database import connect
from .entitlements import entitlement_usage, plan_details, validate_mock_start


FREE_FULL_CONTENT_MOCK_QUESTIONS = 30
FREE_FULL_CONTENT_MOCK_MINUTES = 45
FREE_FULL_CONTENT_MOCK_DOMAIN_COUNTS = {
    "features-architecture": 9,
    "account-governance": 6,
    "loading-connectivity": 5,
    "performance-transformation": 7,
    "data-collaboration": 3,
}


def _utc_now(now: datetime | None = None) -> datetime:
    value = now or datetime.now(timezone.utc)
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _month_end(month: datetime) -> datetime:
    return month.replace(
        year=month.year + (1 if month.month == 12 else 0),
        month=1 if month.month == 12 else month.month + 1,
    )


def mock_reset_context(candidate: dict[str, Any], mode: str, *, now: datetime | None = None) -> dict[str, Any]:
    """Return the authoritative server reset window for a candidate mock mode.

    The window is stored with a sitting for audit/debugging but is never trusted
    from the browser. Exam Pack sets are deliberately fixed and do not rotate.
    """
    current = _utc_now(now)
    day = current.replace(hour=0, minute=0, second=0, microsecond=0)
    week = day - timedelta(days=day.weekday())
    month = day.replace(day=1)
    normalized = str(mode or "").strip().lower().replace("_", "-")
    membership = candidate.get("membership") or {}
    plan = plan_details(membership.get("plan_code"), membership.get("tier") or "free")

    if plan["code"] == "exam_pack_35":
        return {
            "cadence": "fixed",
            "window_key": "exam-pack-fixed",
            "starts_at": None,
            "resets_at": None,
            "rotates_questions": False,
        }
    if normalized == "weekly-mock":
        iso_year, iso_week, _ = week.isocalendar()
        return {
            "cadence": "weekly",
            "window_key": f"{iso_year}-W{iso_week:02d}",
            "starts_at": _iso(week),
            "resets_at": _iso(week + timedelta(days=7)),
            "rotates_questions": True,
        }
    if normalized == "quick-mock":
        return {
            "cadence": "daily",
            "window_key": day.date().isoformat(),
            "starts_at": _iso(day),
            "resets_at": _iso(day + timedelta(days=1)),
            "rotates_questions": True,
        }
    if normalized in {"full-mock", "exam", "source-exam"}:
        return {
            "cadence": "monthly",
            "window_key": f"{month.year:04d}-{month.month:02d}",
            "starts_at": _iso(month),
            "resets_at": _iso(_month_end(month)),
            "rotates_questions": True,
        }
    return {
        "cadence": "none",
        "window_key": "none",
        "starts_at": None,
        "resets_at": None,
        "rotates_questions": True,
    }


def validate_tier_mock_start(candidate: dict[str, Any], mode: str) -> str:
    """Candidate mock gate with the Free 30Q full-content weekly contract."""
    membership = candidate["membership"]
    plan = plan_details(membership.get("plan_code"), membership.get("tier") or "free")
    normalized = str(mode or "").strip().lower().replace("_", "-")
    if plan["tier"] != "free":
        return validate_mock_start(candidate, normalized)

    usage = entitlement_usage(candidate["id"], membership)
    if normalized != "weekly-mock":
        raise HTTPException(
            status_code=403,
            detail={
                "code": "premium_required",
                "message": "Free includes one 30-question full-content timed mock each week. Choose the Free Weekly Mock or upgrade for additional exam access.",
            },
        )
    weekly = usage["weekly_mocks"]
    if int(weekly.get("remaining") or 0) < 1:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "weekly_mock_limit_reached",
                "message": "Your Free full-content mock has already been started for this weekly reset window.",
                **weekly,
            },
        )
    return "weekly-mock"


def mock_question_ids_to_avoid(
    candidate_id: int,
    track_id: str,
    mode: str,
    reset: dict[str, Any],
) -> set[str]:
    """Questions that should not repeat in the next resettable mock when avoidable.

    We exclude all same-mode questions already used in the current reset window,
    plus the immediately preceding same-mode sitting. Selection falls back only
    if the eligible bank is too small to fill the requested sitting.
    """
    if not reset.get("rotates_questions") or reset.get("cadence") == "fixed":
        return set()
    normalized = str(mode or "").strip().lower().replace("_", "-")
    db_mode = f"exam_{normalized.replace('-', '_')}"
    current_start = reset.get("starts_at")
    session_ids: list[int] = []
    with connect() as conn:
        if current_start:
            session_ids.extend(
                int(row["id"])
                for row in conn.execute(
                    "SELECT id FROM exam_sessions WHERE candidate_id=? AND track_id=? AND mode=? AND datetime(started_at)>=datetime(?) ORDER BY id",
                    (candidate_id, track_id, db_mode, current_start),
                )
            )
            previous = conn.execute(
                "SELECT id FROM exam_sessions WHERE candidate_id=? AND track_id=? AND mode=? AND datetime(started_at)<datetime(?) ORDER BY datetime(started_at) DESC,id DESC LIMIT 1",
                (candidate_id, track_id, db_mode, current_start),
            ).fetchone()
        else:
            previous = conn.execute(
                "SELECT id FROM exam_sessions WHERE candidate_id=? AND track_id=? AND mode=? ORDER BY datetime(started_at) DESC,id DESC LIMIT 1",
                (candidate_id, track_id, db_mode),
            ).fetchone()
        if previous:
            session_ids.append(int(previous["id"]))
        if not session_ids:
            return set()
        placeholders = ",".join("?" for _ in session_ids)
        return {
            str(row["question_id"])
            for row in conn.execute(
                f"SELECT DISTINCT question_id FROM exam_session_questions WHERE session_id IN ({placeholders})",
                session_ids,
            )
        }
