from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone
from typing import Any

from .certification_content import configured_skill_map
from .config import DATABASE_BACKEND

SCHEMA_VERSION = "20260902_001_task_review"
_SCHEMA_LOCK = threading.RLock()
_READY_DATABASES: set[str] = set()
_INTERVALS = (1, 3, 7, 14, 30, 60)


def _database_key(conn: Any) -> str:
    row = conn.execute("PRAGMA database_list").fetchone()
    if not row:
        return "unknown"
    try:
        return str(row["file"] or row[2] or "memory")
    except (KeyError, TypeError, IndexError):
        return str(row[2] or "memory")


def _validate_skill(track_id: str, skill_id: str) -> None:
    for cert in configured_skill_map().get("certifications") or []:
        if cert.get("id") != track_id:
            continue
        if any(skill.get("id") == skill_id for domain in cert.get("domains") or [] for skill in domain.get("skills") or []):
            return
        raise ValueError("Task not found for certification")
    raise ValueError("Certification track not found")


def _ensure_task_review_schema(conn: Any) -> None:
    """Bootstrap only SQLite dev/test databases on the caller's connection.

    PostgreSQL schema is provisioned by migrations/postgres/022_study_review_mock_replay.sql.
    Runtime PostgreSQL roles must never need DDL privileges. Using the caller's
    SQLite connection also avoids a nested writer connection and the resulting
    `database is locked` failure during Due Today requests.
    """
    if DATABASE_BACKEND != "sqlite":
        return
    with _SCHEMA_LOCK:
        key = _database_key(conn)
        if key in _READY_DATABASES:
            return
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS candidate_task_reviews (
              candidate_id INTEGER NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
              track_id TEXT NOT NULL,
              skill_id TEXT NOT NULL,
              source_type TEXT NOT NULL DEFAULT 'task' CHECK(source_type IN ('task')),
              created_at TEXT NOT NULL DEFAULT (datetime('now')),
              next_review_at TEXT NOT NULL DEFAULT (datetime('now','+1 day')),
              interval_days INTEGER NOT NULL DEFAULT 1 CHECK(interval_days >= 0),
              review_count INTEGER NOT NULL DEFAULT 0 CHECK(review_count >= 0),
              last_reviewed_at TEXT,
              status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','archived')),
              updated_at TEXT NOT NULL DEFAULT (datetime('now')),
              PRIMARY KEY(candidate_id, track_id, skill_id)
            );
            CREATE INDEX IF NOT EXISTS idx_candidate_task_reviews_due
              ON candidate_task_reviews(candidate_id, track_id, status, next_review_at);
            """
        )
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations(version,name) VALUES (?,?)",
            (SCHEMA_VERSION, "Persisted task-level spaced review scheduling"),
        )
        _READY_DATABASES.add(key)


def _sql_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _now_sql() -> str:
    return _sql_time(datetime.now(timezone.utc))


def _row(row: Any | None) -> dict[str, Any] | None:
    if not row:
        return None
    return {
        "track_id": str(row["track_id"]),
        "skill_id": str(row["skill_id"]),
        "source_type": str(row["source_type"] or "task"),
        "created_at": row["created_at"],
        "next_review_at": row["next_review_at"],
        "interval_days": int(row["interval_days"] or 0),
        "review_count": int(row["review_count"] or 0),
        "last_reviewed_at": row["last_reviewed_at"],
        "status": str(row["status"] or "active"),
    }


def get_task_review(conn: Any, candidate_id: int, track_id: str, skill_id: str) -> dict[str, Any] | None:
    _ensure_task_review_schema(conn)
    _validate_skill(track_id, skill_id)
    return _row(
        conn.execute(
            "SELECT * FROM candidate_task_reviews WHERE candidate_id=? AND track_id=? AND skill_id=?",
            (candidate_id, track_id, skill_id),
        ).fetchone()
    )


def schedule_task_review(conn: Any, candidate_id: int, track_id: str, skill_id: str) -> dict[str, Any]:
    _ensure_task_review_schema(conn)
    _validate_skill(track_id, skill_id)
    existing = conn.execute(
        "SELECT * FROM candidate_task_reviews WHERE candidate_id=? AND track_id=? AND skill_id=?",
        (candidate_id, track_id, skill_id),
    ).fetchone()
    if existing and str(existing["status"] or "active") == "active":
        return _row(existing) or {}
    now = datetime.now(timezone.utc)
    due = now + timedelta(days=1)
    conn.execute(
        """
        INSERT INTO candidate_task_reviews(
          candidate_id,track_id,skill_id,source_type,next_review_at,interval_days,review_count,status,updated_at
        ) VALUES (?,?,?,'task',?,1,0,'active',?)
        ON CONFLICT(candidate_id,track_id,skill_id) DO UPDATE SET
          status='active',next_review_at=excluded.next_review_at,interval_days=1,review_count=0,
          updated_at=excluded.updated_at
        """,
        (candidate_id, track_id, skill_id, _sql_time(due), _sql_time(now)),
    )
    return get_task_review(conn, candidate_id, track_id, skill_id) or {}


def mark_task_reviewed(conn: Any, candidate_id: int, track_id: str, skill_id: str) -> dict[str, Any]:
    _ensure_task_review_schema(conn)
    _validate_skill(track_id, skill_id)
    current = get_task_review(conn, candidate_id, track_id, skill_id)
    if not current or current["status"] != "active":
        raise ValueError("Task review is not scheduled")
    review_count = int(current["review_count"] or 0) + 1
    interval = _INTERVALS[min(review_count, len(_INTERVALS) - 1)]
    now = datetime.now(timezone.utc)
    due = now + timedelta(days=interval)
    now_sql = _sql_time(now)
    conn.execute(
        """
        UPDATE candidate_task_reviews
        SET review_count=?,interval_days=?,last_reviewed_at=?,
            next_review_at=?,status='active',updated_at=?
        WHERE candidate_id=? AND track_id=? AND skill_id=?
        """,
        (review_count, interval, now_sql, _sql_time(due), now_sql, candidate_id, track_id, skill_id),
    )
    return get_task_review(conn, candidate_id, track_id, skill_id) or {}


def reset_task_review(conn: Any, candidate_id: int, track_id: str, skill_id: str) -> dict[str, Any]:
    _ensure_task_review_schema(conn)
    _validate_skill(track_id, skill_id)
    current = get_task_review(conn, candidate_id, track_id, skill_id)
    if not current:
        schedule_task_review(conn, candidate_id, track_id, skill_id)
    now_sql = _now_sql()
    conn.execute(
        """
        UPDATE candidate_task_reviews
        SET next_review_at=?,interval_days=0,status='active',updated_at=?
        WHERE candidate_id=? AND track_id=? AND skill_id=?
        """,
        (now_sql, now_sql, candidate_id, track_id, skill_id),
    )
    return get_task_review(conn, candidate_id, track_id, skill_id) or {}


def due_task_reviews(conn: Any, candidate_id: int, track_id: str, limit: int = 50) -> dict[str, Any]:
    _ensure_task_review_schema(conn)
    safe_limit = max(1, min(int(limit), 100))
    now_sql = _now_sql()
    rows = [
        _row(row)
        for row in conn.execute(
            """
            SELECT * FROM candidate_task_reviews
            WHERE candidate_id=? AND track_id=? AND status='active'
              AND next_review_at <= ?
            ORDER BY next_review_at,review_count,skill_id
            LIMIT ?
            """,
            (candidate_id, track_id, now_sql, safe_limit),
        )
    ]
    rows = [row for row in rows if row]
    total = int(
        conn.execute(
            """
            SELECT COUNT(*) AS count FROM candidate_task_reviews
            WHERE candidate_id=? AND track_id=? AND status='active'
              AND next_review_at <= ?
            """,
            (candidate_id, track_id, now_sql),
        ).fetchone()["count"]
    )
    return {"task_due_count": total, "task_reviews": rows}
