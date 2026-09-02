from __future__ import annotations

import json
import threading
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from .config import DATABASE_BACKEND

SCHEMA_VERSION = "20260902_002_mock_replay"
_SCHEMA_LOCK = threading.RLock()
_READY_DATABASES: set[str] = set()
_ALLOWED_EVENTS = {
    "question_viewed",
    "answer_selected",
    "answer_changed",
    "answer_cleared",
    "flag_added",
    "flag_removed",
    "question_navigated_from",
    "question_navigated_to",
    "session_resumed",
    "session_submitted",
    "timer_expired",
}
_CLIENT_EVENTS = {
    "question_viewed",
    "question_navigated_from",
    "question_navigated_to",
    "session_resumed",
}
_SAFE_METADATA_KEYS = {"position", "from_position", "to_position", "selected_count", "reason"}


def _database_key(conn: Any) -> str:
    row = conn.execute("PRAGMA database_list").fetchone()
    if not row:
        return "unknown"
    try:
        return str(row["file"] or row[2] or "memory")
    except (KeyError, TypeError, IndexError):
        return str(row[2] or "memory")


def _ensure_mock_replay_schema(conn: Any) -> None:
    """Bootstrap replay tables only for SQLite dev/test on the active connection.

    Hosted PostgreSQL is provisioned by migration 022 and the runtime role does
    not need DDL privileges. Reusing the active SQLite connection avoids nested
    writer locks while answer/flag events are being persisted.
    """
    if DATABASE_BACKEND != "sqlite":
        return
    with _SCHEMA_LOCK:
        key = _database_key(conn)
        if key in _READY_DATABASES:
            return
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS exam_session_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              session_id INTEGER NOT NULL REFERENCES exam_sessions(id) ON DELETE CASCADE,
              candidate_id INTEGER NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
              question_id TEXT REFERENCES questions(id) ON DELETE SET NULL,
              event_type TEXT NOT NULL,
              occurred_at TEXT NOT NULL DEFAULT (datetime('now')),
              metadata_json TEXT NOT NULL DEFAULT '{}'
            );
            CREATE INDEX IF NOT EXISTS idx_exam_session_events_session
              ON exam_session_events(session_id, occurred_at, id);
            CREATE INDEX IF NOT EXISTS idx_exam_session_events_candidate
              ON exam_session_events(candidate_id, session_id, occurred_at);
            """
        )
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations(version,name) VALUES (?,?)",
            (SCHEMA_VERSION, "Privacy-safe immutable mock exam replay events"),
        )
        _READY_DATABASES.add(key)


def _safe_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    source = metadata or {}
    result: dict[str, Any] = {}
    for key in _SAFE_METADATA_KEYS:
        if key not in source:
            continue
        value = source[key]
        if isinstance(value, (str, int, float, bool)) or value is None:
            result[key] = value
    return result


def append_event(
    conn: Any,
    *,
    session_id: int,
    candidate_id: int,
    event_type: str,
    question_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    client_event: bool = False,
) -> None:
    _ensure_mock_replay_schema(conn)
    if event_type not in _ALLOWED_EVENTS:
        raise ValueError("Unsupported mock replay event")
    if client_event and event_type not in _CLIENT_EVENTS:
        raise ValueError("This replay event is server-managed")
    if question_id:
        exists = conn.execute(
            "SELECT 1 FROM exam_session_questions WHERE session_id=? AND question_id=?",
            (session_id, question_id),
        ).fetchone()
        if not exists:
            raise ValueError("Question does not belong to this mock session")
    conn.execute(
        """
        INSERT INTO exam_session_events(session_id,candidate_id,question_id,event_type,metadata_json)
        VALUES (?,?,?,?,?)
        """,
        (
            session_id,
            candidate_id,
            question_id,
            event_type,
            json.dumps(_safe_metadata(metadata), separators=(",", ":")),
        ),
    )


def record_answer_event(
    conn: Any,
    *,
    session_id: int,
    candidate_id: int,
    question_id: str,
    previous: list[int],
    selected: list[int],
) -> None:
    if not selected:
        event_type = "answer_cleared"
    elif previous and sorted(previous) != sorted(selected):
        event_type = "answer_changed"
    else:
        event_type = "answer_selected"
    append_event(
        conn,
        session_id=session_id,
        candidate_id=candidate_id,
        question_id=question_id,
        event_type=event_type,
        metadata={"selected_count": len(selected)},
    )


def record_flag_event(
    conn: Any,
    *,
    session_id: int,
    candidate_id: int,
    question_id: str,
    flagged: bool,
) -> None:
    append_event(
        conn,
        session_id=session_id,
        candidate_id=candidate_id,
        question_id=question_id,
        event_type="flag_added" if flagged else "flag_removed",
    )


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    text = str(value).replace(" ", "T")
    if not text.endswith("Z") and "+" not in text[10:]:
        text += "+00:00"
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def replay_payload(conn: Any, session_id: int, candidate_id: int) -> dict[str, Any]:
    _ensure_mock_replay_schema(conn)
    session = conn.execute(
        "SELECT id,track_id,status,finished_at,started_at FROM exam_sessions WHERE id=? AND candidate_id=?",
        (session_id, candidate_id),
    ).fetchone()
    if not session:
        raise ValueError("Mock session not found")
    if str(session["status"]) == "in_progress":
        raise RuntimeError("Mock replay is available only after submission")

    questions = [
        dict(row)
        for row in conn.execute(
            """
            SELECT sq.question_id,sq.position,sq.flagged,
                   COALESCE(a.selected_json,'[]') AS selected_json,
                   COALESCE(a.correct,0) AS is_correct,
                   a.confidence,
                   COALESCE(m.domain_id,qsm.domain_id,'') AS domain_id,
                   COALESCE(m.task_id,qsm.skill_id,'') AS skill_id
            FROM exam_session_questions sq
            JOIN questions q ON q.id=sq.question_id
            LEFT JOIN exam_session_answers a
              ON a.session_id=sq.session_id AND a.question_id=sq.question_id
            LEFT JOIN question_bank_metadata m ON m.question_id=sq.question_id
            LEFT JOIN question_skill_map qsm
              ON qsm.question_id=sq.question_id AND qsm.track_id=q.track_id
            WHERE sq.session_id=?
            GROUP BY sq.question_id,sq.position,sq.flagged,a.selected_json,a.correct,a.confidence,
                     m.domain_id,m.task_id,qsm.domain_id,qsm.skill_id
            ORDER BY sq.position
            """,
            (session_id,),
        )
    ]
    events = [dict(row) for row in conn.execute(
        "SELECT id,question_id,event_type,occurred_at,metadata_json FROM exam_session_events WHERE session_id=? AND candidate_id=? ORDER BY occurred_at,id",
        (session_id, candidate_id),
    )]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        if event.get("question_id"):
            grouped[str(event["question_id"])].append(event)

    finished_at = _parse_time(session["finished_at"]) or datetime.now(timezone.utc)
    rows: list[dict[str, Any]] = []
    for question in questions:
        question_id = str(question["question_id"])
        qevents = grouped.get(question_id, [])
        visits = sum(1 for event in qevents if event["event_type"] in {"question_viewed", "question_navigated_to"})
        changes = sum(1 for event in qevents if event["event_type"] == "answer_changed")
        flag_added = sum(1 for event in qevents if event["event_type"] == "flag_added")
        flag_removed = sum(1 for event in qevents if event["event_type"] == "flag_removed")
        time_spent = 0.0
        open_at: datetime | None = None
        for event in qevents:
            at = _parse_time(event["occurred_at"])
            if not at:
                continue
            if event["event_type"] in {"question_viewed", "question_navigated_to"}:
                if open_at is None:
                    open_at = at
            elif event["event_type"] == "question_navigated_from" and open_at is not None:
                time_spent += max(0.0, min(1800.0, (at - open_at).total_seconds()))
                open_at = None
        if open_at is not None:
            time_spent += max(0.0, min(1800.0, (finished_at - open_at).total_seconds()))
        selected = json.loads(question["selected_json"] or "[]")
        rows.append({
            "position": int(question["position"]),
            "question_id": question_id,
            "domain_id": str(question["domain_id"] or ""),
            "skill_id": str(question["skill_id"] or ""),
            "status": "correct" if bool(question["is_correct"]) else "unanswered" if not selected else "incorrect",
            "time_spent_seconds": int(round(time_spent)),
            "visit_count": max(visits, 1 if qevents else 0),
            "answer_change_count": changes,
            "flag_added_count": flag_added,
            "flag_removed_count": flag_removed,
            "final_flagged": bool(question["flagged"]),
            "confidence": question["confidence"],
        })
    return {
        "session_id": session_id,
        "track_id": str(session["track_id"]),
        "event_count": len(events),
        "questions": rows,
        "integrity_note": "Replay telemetry contains interaction metadata only; answer keys, explanations, and question text are not stored in the event stream.",
    }
