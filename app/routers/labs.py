import json
from typing import Any

from fastapi import APIRouter, HTTPException

from ..database import connect
from ..labs import LABS

router = APIRouter()


@router.get("/labs")
def labs() -> dict[str, Any]:
    with connect() as conn:
        rows = [dict(row) for row in conn.execute("SELECT * FROM lab_exercises ORDER BY position, id")]
        completed = {
            row["exercise_id"]
            for row in conn.execute("SELECT DISTINCT exercise_id FROM lab_submissions WHERE passed = 1")
        }
    if rows:
        return {"labs": [_lab(row, row["id"] in completed) for row in rows]}
    return {"labs": LABS}


@router.get("/labs/{lab_id}")
def lab_detail(lab_id: str) -> dict[str, Any]:
    if lab_id.isdigit():
        with connect() as conn:
            row = conn.execute("SELECT * FROM lab_exercises WHERE id = ?", (int(lab_id),)).fetchone()
            if row:
                return _lab(dict(row), False)
    for lab in LABS:
        if lab["id"] == lab_id:
            return lab
    raise HTTPException(status_code=404, detail="Lab not found")


@router.post("/labs/{lab_id}/submit")
def submit_lab(lab_id: int, payload: dict[str, str]) -> dict[str, Any]:
    sql = payload.get("sql") or ""
    with connect() as conn:
        row = conn.execute("SELECT * FROM lab_exercises WHERE id = ?", (lab_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Lab not found")
        lab = dict(row)
        expected = json.loads(lab.get("expected_output") or "{}")
        keywords = expected.get("keywords") or []
        normalized = " ".join(sql.upper().split())
        missing = [keyword for keyword in keywords if keyword.upper() not in normalized]
        passed = not missing
        feedback = (
            "Correct. Your SQL includes the required Snowflake clauses."
            if passed
            else "Missing required clause(s): " + ", ".join(missing)
        )
        conn.execute(
            """
            INSERT INTO lab_submissions(exercise_id, submitted_sql, passed, feedback)
            VALUES (?, ?, ?, ?)
            """,
            (lab_id, sql, 1 if passed else 0, feedback),
        )
    return {"passed": passed, "feedback": feedback, "hint": None if passed else lab.get("hint")}


def _lab(row: dict[str, Any], completed: bool) -> dict[str, Any]:
    row["tags"] = json.loads(row.get("tags") or "[]")
    row["completed"] = completed
    return row
