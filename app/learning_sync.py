from __future__ import annotations

import json
from typing import Any

from .learning_intelligence import ensure_learning_intelligence_schema, record_learning_review

SCHEMA_VERSION = "20260815_031_candidate_learning_attempt_sync_v1"


def ensure_learning_sync_schema(conn: Any) -> None:
    ensure_learning_intelligence_schema()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS candidate_learning_attempt_sync (
          attempt_id INTEGER PRIMARY KEY REFERENCES question_attempts(id) ON DELETE CASCADE,
          candidate_id INTEGER NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
          processed_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_candidate_learning_attempt_sync_candidate
          ON candidate_learning_attempt_sync(candidate_id, processed_at);
        """
    )
    conn.execute(
        "INSERT OR IGNORE INTO schema_migrations(version,name) VALUES (?,?)",
        (SCHEMA_VERSION, "Idempotent candidate learning-state synchronization from question attempts"),
    )


def sync_candidate_learning_state(
    conn: Any,
    candidate_id: int,
    track_id: str = "snowpro-core",
    *,
    limit: int = 2000,
) -> dict[str, int]:
    """Project unsynchronized answer attempts into SRS and mistake state.

    `question_attempts` remains the authoritative answer ledger. Confidence and
    response time are read from the same attempt row, so multiple historical
    attempts for one question cannot inherit metadata from a later answer.
    This projection is idempotent and can safely run before intelligence reads.
    """
    ensure_learning_sync_schema(conn)
    safe_limit = max(1, min(int(limit), 10000))
    rows = [
        dict(row)
        for row in conn.execute(
            """
            SELECT a.id,a.question_id,a.selected,a.correct,a.mode,a.attempted_at,
                   a.confidence,a.response_time_ms
            FROM question_attempts a
            JOIN questions q ON q.id=a.question_id
            LEFT JOIN candidate_learning_attempt_sync s ON s.attempt_id=a.id
            WHERE a.candidate_id=? AND q.track_id=? AND s.attempt_id IS NULL
            ORDER BY a.id
            LIMIT ?
            """,
            (candidate_id, track_id, safe_limit),
        )
    ]
    processed = 0
    for row in rows:
        try:
            selected = [int(item) for item in json.loads(row["selected"] or "[]")]
        except (TypeError, ValueError, json.JSONDecodeError):
            selected = []
        record_learning_review(
            conn,
            candidate_id,
            row["question_id"],
            correct=bool(row["correct"]),
            confidence=int(row["confidence"]) if row["confidence"] is not None else None,
            mode=str(row["mode"] or "practice"),
            response_time_ms=int(row["response_time_ms"]) if row["response_time_ms"] is not None else None,
            selected=selected,
        )
        conn.execute(
            "INSERT INTO candidate_learning_attempt_sync(attempt_id,candidate_id) VALUES (?,?)",
            (int(row["id"]), candidate_id),
        )
        processed += 1
    return {"processed": processed, "remaining_unknown": int(len(rows) >= safe_limit)}
