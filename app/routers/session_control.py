from fastapi import APIRouter, HTTPException

from ..database import connect

router = APIRouter()


@router.post("/mock/session-control/{session_id}/cancel")
def cancel_session(session_id: int) -> dict:
    with connect() as conn:
        row = conn.execute("SELECT status FROM exam_sessions WHERE id = ?", (session_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Exam session not found")
        if row["status"] == "in_progress":
            conn.execute("UPDATE exam_sessions SET status='cancelled', finished_at=datetime('now') WHERE id=?", (session_id,))
    return {"ok": True, "session_id": session_id, "status": "cancelled"}
