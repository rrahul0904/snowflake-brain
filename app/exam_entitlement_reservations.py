from __future__ import annotations

import threading
from typing import Any

from fastapi import HTTPException

from .database import connect
from .entitlements import plan_details


_SCHEMA_LOCK = threading.RLock()
_SCHEMA_READY = False


def ensure_exam_entitlement_reservation_schema() -> None:
    """Create the concurrency boundary for limited timed-exam starts.

    The reservation ledger is intentionally separate from exam_sessions. A
    request reserves scarce entitlement capacity before question selection and
    session creation, preventing concurrent requests from all observing the
    same remaining allowance. Existing session rows remain the durable usage
    source, while short-lived uncommitted reservations cover the in-flight gap.
    """
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    with _SCHEMA_LOCK:
        if _SCHEMA_READY:
            return
        with connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS exam_entitlement_reservations (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  candidate_id INTEGER NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
                  track_id TEXT NOT NULL,
                  plan_code TEXT NOT NULL,
                  exam_type TEXT NOT NULL CHECK(exam_type IN ('weekly_mock','full_exam')),
                  window_key TEXT NOT NULL,
                  attempt_number INTEGER NOT NULL,
                  session_id INTEGER REFERENCES exam_sessions(id) ON DELETE SET NULL,
                  status TEXT NOT NULL DEFAULT 'reserved'
                    CHECK(status IN ('reserved','committed','released')),
                  created_at TEXT NOT NULL DEFAULT (datetime('now')),
                  committed_at TEXT,
                  released_at TEXT,
                  UNIQUE(candidate_id, track_id, exam_type, window_key, attempt_number),
                  UNIQUE(session_id)
                );

                CREATE INDEX IF NOT EXISTS idx_exam_entitlement_reservation_window
                  ON exam_entitlement_reservations(candidate_id, track_id, exam_type, window_key, status, created_at);
                """
            )
        _SCHEMA_READY = True


def _reservation_contract(
    candidate: dict[str, Any],
    mode: str,
    reset: dict[str, Any],
) -> dict[str, Any] | None:
    membership = candidate.get("membership") or {}
    plan = plan_details(membership.get("plan_code"), membership.get("tier") or "free")
    normalized = str(mode or "").strip().lower().replace("_", "-")

    if normalized == "weekly-mock" and plan["tier"] == "free":
        return {
            "plan_code": plan["code"],
            "exam_type": "weekly_mock",
            "session_modes": ("exam_weekly_mock",),
            "limit": int(plan.get("weekly_mock_limit") or 0),
            "window_key": str(reset.get("window_key") or "weekly"),
            "starts_at": reset.get("starts_at"),
            "error_code": "weekly_mock_limit_reached",
            "error_message": "Your Free full-content mock has already been started for this weekly reset window.",
        }

    if normalized not in {"full-mock", "source-exam", "exam"}:
        return None

    if plan["code"] == "exam_pack_35":
        return {
            "plan_code": plan["code"],
            "exam_type": "full_exam",
            "session_modes": ("exam_full_mock", "exam_source"),
            "limit": 1,
            "window_key": "exam-pack-fixed",
            "starts_at": None,
            "error_code": "exam_pack_full_exam_used",
            "error_message": "The included Full Exam attempt has already been started. Lifetime Practice Mock access remains active.",
        }

    limit = plan.get("monthly_full_exam_limit")
    if limit is None:
        return None
    return {
        "plan_code": plan["code"],
        "exam_type": "full_exam",
        "session_modes": ("exam_full_mock", "exam_source"),
        "limit": int(limit),
        "window_key": str(reset.get("window_key") or "monthly"),
        "starts_at": reset.get("starts_at"),
        "error_code": "monthly_full_exam_limit_reached",
        "error_message": "Your monthly full-exam allowance has been used. It resets on the first day of next month at 00:00 UTC.",
    }


def reserve_exam_attempt(
    candidate: dict[str, Any],
    track_id: str,
    mode: str,
    reset: dict[str, Any],
) -> int | None:
    """Atomically reserve one scarce timed-exam entitlement slot.

    Counts durable exam sessions plus in-flight reservations. Reserved rows
    older than 15 minutes are released defensively so a process crash does not
    permanently consume a candidate allowance.
    """
    contract = _reservation_contract(candidate, mode, reset)
    if not contract:
        return None
    ensure_exam_entitlement_reservation_schema()

    candidate_id = int(candidate["id"])
    limit = int(contract["limit"])
    if limit < 1:
        raise HTTPException(
            status_code=403,
            detail={"code": contract["error_code"], "message": contract["error_message"], "limit": limit, "used": 0, "remaining": 0},
        )

    session_modes = tuple(str(item) for item in contract["session_modes"])
    placeholders = ",".join("?" for _ in session_modes)
    starts_at = contract.get("starts_at")

    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            """
            UPDATE exam_entitlement_reservations
               SET status='released', released_at=datetime('now')
             WHERE candidate_id=? AND track_id=? AND exam_type=? AND window_key=?
               AND status='reserved'
               AND datetime(created_at) < datetime('now','-15 minutes')
            """,
            (candidate_id, track_id, contract["exam_type"], contract["window_key"]),
        )

        if starts_at:
            session_row = conn.execute(
                f"SELECT COUNT(*) AS count FROM exam_sessions WHERE candidate_id=? AND track_id=? AND mode IN ({placeholders}) AND datetime(started_at)>=datetime(?)",
                [candidate_id, track_id, *session_modes, starts_at],
            ).fetchone()
        else:
            session_row = conn.execute(
                f"SELECT COUNT(*) AS count FROM exam_sessions WHERE candidate_id=? AND track_id=? AND mode IN ({placeholders})",
                [candidate_id, track_id, *session_modes],
            ).fetchone()
        durable_used = int(session_row["count"] if session_row else 0)

        inflight_row = conn.execute(
            """
            SELECT COUNT(*) AS count
              FROM exam_entitlement_reservations
             WHERE candidate_id=? AND track_id=? AND exam_type=? AND window_key=?
               AND status='reserved'
            """,
            (candidate_id, track_id, contract["exam_type"], contract["window_key"]),
        ).fetchone()
        in_flight = int(inflight_row["count"] if inflight_row else 0)
        used = durable_used + in_flight
        if used >= limit:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": contract["error_code"],
                    "message": contract["error_message"],
                    "limit": limit,
                    "used": used,
                    "remaining": 0,
                },
            )

        attempt_number = used + 1
        cursor = conn.execute(
            """
            INSERT INTO exam_entitlement_reservations(
              candidate_id, track_id, plan_code, exam_type, window_key, attempt_number, status
            ) VALUES (?, ?, ?, ?, ?, ?, 'reserved')
            """,
            (
                candidate_id,
                track_id,
                contract["plan_code"],
                contract["exam_type"],
                contract["window_key"],
                attempt_number,
            ),
        )
        return int(cursor.lastrowid)


def commit_exam_attempt_reservation(reservation_id: int | None, session_id: int) -> None:
    if reservation_id is None:
        return
    ensure_exam_entitlement_reservation_schema()
    with connect() as conn:
        cursor = conn.execute(
            """
            UPDATE exam_entitlement_reservations
               SET status='committed', session_id=?, committed_at=datetime('now')
             WHERE id=? AND status='reserved'
            """,
            (session_id, reservation_id),
        )
        if cursor.rowcount != 1:
            raise RuntimeError("Exam entitlement reservation was not available to commit")


def release_exam_attempt_reservation(reservation_id: int | None) -> None:
    if reservation_id is None:
        return
    ensure_exam_entitlement_reservation_schema()
    with connect() as conn:
        conn.execute(
            """
            UPDATE exam_entitlement_reservations
               SET status='released', released_at=datetime('now')
             WHERE id=? AND status='reserved'
            """,
            (reservation_id,),
        )
