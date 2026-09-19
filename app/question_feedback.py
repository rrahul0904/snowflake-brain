from __future__ import annotations

from typing import Any

from .config import DATABASE_BACKEND
from .database import connect


SCHEMA_VERSION = "20260918_001_question_feedback_v1"
CATEGORIES = {"ambiguous", "incorrect_answer", "outdated", "explanation", "typo", "other"}
STATUSES = {"open", "triaged", "resolved", "rejected"}


class QuestionFeedbackError(ValueError):
    pass


def ensure_question_feedback_schema() -> None:
    if DATABASE_BACKEND == "postgresql":
        return
    with connect() as conn:
        existing = conn.execute(
            "SELECT 1 FROM schema_migrations WHERE version=?",
            (SCHEMA_VERSION,),
        ).fetchone()
        if existing:
            return
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS question_feedback (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
              candidate_id INTEGER NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
              category TEXT NOT NULL CHECK(category IN ('ambiguous','incorrect_answer','outdated','explanation','typo','other')),
              description TEXT NOT NULL DEFAULT '',
              status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','triaged','resolved','rejected')),
              resolution_notes TEXT NOT NULL DEFAULT '',
              resolved_by TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL DEFAULT (datetime('now')),
              updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_question_feedback_candidate
              ON question_feedback(candidate_id,created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_question_feedback_editorial
              ON question_feedback(status,question_id,created_at);
            """
        )
        conn.execute(
            "INSERT INTO schema_migrations(version,name) VALUES (?,?)",
            (SCHEMA_VERSION, "Candidate question correction reports and editorial triage"),
        )


def submit_question_feedback(
    question_id: str,
    candidate_id: int,
    category: str,
    description: str,
) -> dict[str, Any]:
    ensure_question_feedback_schema()
    category = str(category or "").strip().lower()
    description = str(description or "").strip()
    if category not in CATEGORIES:
        raise QuestionFeedbackError("Unsupported question-feedback category")
    if not description:
        raise QuestionFeedbackError("Tell the editorial team what should be reviewed")
    if len(description) > 3000:
        raise QuestionFeedbackError("Question feedback must be 3000 characters or fewer")

    with connect() as conn:
        duplicate = conn.execute(
            """
            SELECT * FROM question_feedback
             WHERE question_id=? AND candidate_id=? AND category=?
               AND status IN ('open','triaged')
             ORDER BY id DESC LIMIT 1
            """,
            (question_id, candidate_id, category),
        ).fetchone()
        if duplicate:
            return dict(duplicate)
        cursor = conn.execute(
            """
            INSERT INTO question_feedback(question_id,candidate_id,category,description)
            VALUES (?,?,?,?)
            """,
            (question_id, candidate_id, category, description),
        )
        row = conn.execute(
            "SELECT * FROM question_feedback WHERE id=?",
            (int(cursor.lastrowid),),
        ).fetchone()
    return dict(row)


def candidate_question_feedback(candidate_id: int, *, limit: int = 100) -> list[dict[str, Any]]:
    ensure_question_feedback_schema()
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id,question_id,category,description,status,resolution_notes,created_at,updated_at
              FROM question_feedback
             WHERE candidate_id=?
             ORDER BY id DESC LIMIT ?
            """,
            (candidate_id, max(1, min(int(limit), 200))),
        ).fetchall()
    return [dict(row) for row in rows]


def editorial_question_feedback(*, status: str = "open", limit: int = 200) -> list[dict[str, Any]]:
    ensure_question_feedback_schema()
    normalized = str(status or "").strip().lower()
    if normalized and normalized not in STATUSES:
        raise QuestionFeedbackError("Unsupported question-feedback status")
    with connect() as conn:
        if normalized:
            rows = conn.execute(
                """
                SELECT f.*,a.email AS candidate_email
                  FROM question_feedback f
                  JOIN candidate_accounts a ON a.id=f.candidate_id
                 WHERE f.status=?
                 ORDER BY f.id ASC LIMIT ?
                """,
                (normalized, max(1, min(int(limit), 500))),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT f.*,a.email AS candidate_email
                  FROM question_feedback f
                  JOIN candidate_accounts a ON a.id=f.candidate_id
                 ORDER BY f.id DESC LIMIT ?
                """,
                (max(1, min(int(limit), 500)),),
            ).fetchall()
    return [dict(row) for row in rows]


def update_question_feedback(
    feedback_id: int,
    *,
    status: str,
    actor: str,
    resolution_notes: str = "",
) -> dict[str, Any]:
    ensure_question_feedback_schema()
    normalized = str(status or "").strip().lower()
    actor = str(actor or "").strip()
    if normalized not in STATUSES - {"open"}:
        raise QuestionFeedbackError("Editorial status must be triaged, resolved, or rejected")
    if not actor:
        raise QuestionFeedbackError("Editorial actor is required")
    notes = str(resolution_notes or "").strip()
    if len(notes) > 3000:
        raise QuestionFeedbackError("Resolution notes must be 3000 characters or fewer")
    with connect() as conn:
        row = conn.execute("SELECT id FROM question_feedback WHERE id=?", (feedback_id,)).fetchone()
        if not row:
            raise QuestionFeedbackError("Question feedback was not found")
        conn.execute(
            """
            UPDATE question_feedback
               SET status=?,resolution_notes=?,resolved_by=?,updated_at=datetime('now')
             WHERE id=?
            """,
            (normalized, notes, actor, feedback_id),
        )
        updated = conn.execute("SELECT * FROM question_feedback WHERE id=?", (feedback_id,)).fetchone()
    return dict(updated)
