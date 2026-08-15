from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth import require_candidate
from ..database import connect
from ..question_bank import candidate_was_served_question

router = APIRouter()


class NoteRequest(BaseModel):
    body: str = Field(min_length=1, max_length=10_000)


def _served(candidate_id: int, question_id: str) -> None:
    if not candidate_was_served_question(candidate_id, question_id):
        raise HTTPException(status_code=404, detail="Question not found")


@router.post("/quiz/start")
def block_legacy_quiz_start(candidate: dict[str, Any] = Depends(require_candidate)) -> dict[str, Any]:
    del candidate
    raise HTTPException(
        status_code=410,
        detail={"code": "use_certification_practice", "message": "Start practice from the Free or Premium practice experience."},
    )


@router.get("/questions/{question_id}/bookmark")
def bookmark_state(question_id: str, candidate: dict[str, Any] = Depends(require_candidate)) -> dict[str, bool]:
    _served(candidate["id"], question_id)
    with connect() as conn:
        row = conn.execute(
            "SELECT id FROM candidate_bookmarks WHERE candidate_id=? AND question_id=?",
            (candidate["id"], question_id),
        ).fetchone()
    return {"bookmarked": bool(row)}


@router.post("/questions/{question_id}/bookmark")
def toggle_bookmark(question_id: str, candidate: dict[str, Any] = Depends(require_candidate)) -> dict[str, bool]:
    _served(candidate["id"], question_id)
    with connect() as conn:
        existing = conn.execute(
            "SELECT id FROM candidate_bookmarks WHERE candidate_id=? AND question_id=?",
            (candidate["id"], question_id),
        ).fetchone()
        if existing:
            conn.execute("DELETE FROM candidate_bookmarks WHERE id=?", (existing["id"],))
            return {"bookmarked": False}
        conn.execute(
            "INSERT INTO candidate_bookmarks(candidate_id, question_id) VALUES (?, ?)",
            (candidate["id"], question_id),
        )
    return {"bookmarked": True}


@router.get("/questions/{question_id}/notes")
def question_notes(question_id: str, candidate: dict[str, Any] = Depends(require_candidate)) -> dict[str, Any]:
    _served(candidate["id"], question_id)
    with connect() as conn:
        rows = [
            dict(row)
            for row in conn.execute(
                "SELECT id, body, created_at FROM candidate_notes WHERE candidate_id=? AND question_id=? ORDER BY created_at DESC",
                (candidate["id"], question_id),
            )
        ]
    return {"notes": rows}


@router.post("/questions/{question_id}/notes")
def add_question_note(question_id: str, payload: NoteRequest, candidate: dict[str, Any] = Depends(require_candidate)) -> dict[str, Any]:
    _served(candidate["id"], question_id)
    with connect() as conn:
        cursor = conn.execute(
            "INSERT INTO candidate_notes(candidate_id, question_id, body) VALUES (?, ?, ?)",
            (candidate["id"], question_id, payload.body.strip()),
        )
    return {"ok": True, "id": cursor.lastrowid}
