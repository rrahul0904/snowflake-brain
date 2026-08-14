from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..database import connect
from ..auth import optional_candidate, require_candidate, require_owned_mock_session

router = APIRouter()


class FeedbackSubmission(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    category: str = Field(default="bug", pattern="^(bug|feature|content|other)$")
    description: str = Field(default="", max_length=5000)
    contact: str = Field(default="", max_length=320)
    route: str = Field(default="#/home", max_length=500)
    track_id: str = Field(default="snowpro-core", max_length=120)


@router.post("/feedback")
def submit_feedback(payload: FeedbackSubmission, candidate: dict | None = Depends(optional_candidate)) -> dict:
    with connect() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS feedback_submissions (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, category TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', contact TEXT DEFAULT '', route TEXT NOT NULL DEFAULT '#/home', track_id TEXT NOT NULL DEFAULT 'snowpro-core', candidate_id INTEGER REFERENCES candidate_accounts(id) ON DELETE SET NULL, created_at TEXT DEFAULT (datetime('now')))"
        )
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(feedback_submissions)")}
        if "candidate_id" not in columns:
            conn.execute("ALTER TABLE feedback_submissions ADD COLUMN candidate_id INTEGER REFERENCES candidate_accounts(id) ON DELETE SET NULL")
        cursor = conn.execute(
            "INSERT INTO feedback_submissions(title, category, description, contact, route, track_id, candidate_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (payload.title.strip(), payload.category, payload.description.strip(), payload.contact.strip(), payload.route, payload.track_id, candidate["id"] if candidate else None),
        )
        feedback_id = int(cursor.lastrowid)
    return {"ok": True, "feedback_id": feedback_id}


@router.post("/mock/session-control/{session_id}/cancel")
def cancel_mock_session(session_id: int, candidate: dict = Depends(require_candidate)) -> dict:
    require_owned_mock_session(session_id, candidate["id"])
    if not candidate["is_premium"]:
        raise HTTPException(status_code=403, detail={"code": "free_mock_must_be_completed", "message": "A Free weekly mock cannot be discarded. Resume it and submit, or let its timer expire."})
    with connect() as conn:
        row = conn.execute("SELECT status FROM exam_sessions WHERE id = ?", (session_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Exam session not found")
        if row["status"] == "in_progress":
            conn.execute("UPDATE exam_sessions SET status='cancelled', finished_at=datetime('now') WHERE id=?", (session_id,))
    return {"ok": True, "session_id": session_id, "status": "cancelled"}
