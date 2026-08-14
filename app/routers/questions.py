import json
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..database import connect
from ..auth import optional_candidate, require_candidate
from ..entitlements import reserve_daily_questions
from ..serializers import json_list, question_public

router = APIRouter()


class QuizStartRequest(BaseModel):
    track_id: str = "snowpro-core"
    test_id: str | None = None
    count: int = Field(10, ge=1, le=500)
    mode: str = "random"
    tags: list[str] | None = None
    difficulty: str | None = None
    unanswered_only: bool = False


class QuizAnswer(BaseModel):
    question_id: str
    selected: list[int]


class QuizGradeRequest(BaseModel):
    answers: list[QuizAnswer]


class AttemptRequest(BaseModel):
    selected: list[int]
    correct: bool
    mode: str = "practice"


@router.get("/questions")
def questions(
    track_id: str = "snowpro-core",
    test_id: str | None = None,
    q: str = "",
    tags: str = "",
    difficulty: str | None = None,
    unanswered: bool = False,
    bookmarked: bool = False,
    source_kind: str | None = None,
    limit: int = Query(40, ge=1, le=500),
    offset: int = Query(0, ge=0),
    include_answers: bool = False,
    candidate: dict | None = Depends(optional_candidate),
) -> dict[str, Any]:
    if (unanswered or bookmarked) and not candidate:
        require_candidate(candidate)
    where, params = _question_filters(
        track_id,
        test_id,
        q,
        tags,
        difficulty,
        unanswered,
        bookmarked,
        source_kind,
        candidate["id"] if candidate else None,
    )
    with connect() as conn:
        total = conn.execute(f"SELECT COUNT(*) AS count FROM questions q {where}", params).fetchone()["count"]
        rows = [
            question_public(dict(row), include_answer=False)
            for row in conn.execute(
                f"""
                SELECT q.*
                FROM questions q
                {where}
                ORDER BY q.test_title, COALESCE(q.question_position, 0), q.question
                LIMIT ? OFFSET ?
                """,
                [*params, limit, offset],
            )
        ]
    return {"questions": rows, "total": int(total or 0)}


@router.get("/practice-tests")
def practice_tests(
    track_id: str = "snowpro-core",
    include_legacy: bool = False,
    source_kind: str | None = None,
) -> dict[str, Any]:
    filters = ["pt.track_id = ?"]
    params: list[Any] = [track_id]
    if not include_legacy:
        filters.append("pt.is_legacy = 0")
    if source_kind:
        filters.append("pt.source_kind = ?")
        params.append(source_kind)
    where = "WHERE " + " AND ".join(filters)
    with connect() as conn:
        rows = [
            dict(row)
            for row in conn.execute(
                f"""
                SELECT
                  pt.*,
                  COUNT(q.id) AS actual_question_count,
                  SUM(CASE WHEN q.multiple = 1 THEN 1 ELSE 0 END) AS multi_select_count
                FROM practice_tests pt
                LEFT JOIN questions q ON q.test_id = pt.id
                {where}
                GROUP BY pt.id
                ORDER BY pt.is_legacy, pt.position, pt.title
                """,
                params,
            )
        ]
    return {"tests": rows}


@router.get("/practice-tests/{test_id}/questions")
def practice_test_questions(test_id: str, include_answers: bool = False) -> dict[str, Any]:
    with connect() as conn:
        test = conn.execute("SELECT * FROM practice_tests WHERE id = ?", (test_id,)).fetchone()
        if not test:
            raise HTTPException(status_code=404, detail="Practice test not found")
        rows = [
            question_public(dict(row), include_answer=False)
            for row in conn.execute(
                """
                SELECT * FROM questions
                WHERE test_id = ?
                ORDER BY COALESCE(question_position, 0), question
                """,
                (test_id,),
            )
        ]
    return {"test": dict(test), "questions": rows, "total": len(rows)}


@router.get("/questions/{question_id}")
def question_detail(question_id: str) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM questions WHERE id = ?", (question_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Question not found")
    return question_public(dict(row), include_answer=False)


@router.post("/quiz/start")
def quiz_start(payload: QuizStartRequest, candidate: dict = Depends(require_candidate)) -> dict[str, Any]:
    tags = ",".join(payload.tags or [])
    where, params = _question_filters(
        payload.track_id,
        payload.test_id,
        "",
        tags,
        payload.difficulty,
        payload.unanswered_only,
        False,
        None,
        candidate["id"],
    )
    order = "COALESCE(q.question_position, 0), q.question" if payload.test_id else (
        "RANDOM()" if payload.mode == "random" else "q.test_title, COALESCE(q.question_position, 0), q.question"
    )
    with connect() as conn:
        rows = [
            question_public(dict(row), include_answer=False)
            for row in conn.execute(
                f"SELECT q.* FROM questions q {where} ORDER BY {order} LIMIT ?",
                [*params, payload.count],
            )
        ]
    quota = reserve_daily_questions(candidate["id"], candidate["membership"], len(rows))
    return {"questions": rows, "total": len(rows), "quota": quota}


@router.post("/quiz/grade")
def quiz_grade(payload: QuizGradeRequest, candidate: dict = Depends(require_candidate)) -> dict[str, Any]:
    ids = [answer.question_id for answer in payload.answers]
    if not ids:
        return {"score": 0, "total": 0, "results": []}
    placeholders = ",".join("?" for _ in ids)
    with connect() as conn:
        active = conn.execute(
            f"""
            SELECT 1
            FROM exam_session_questions sq
            JOIN exam_sessions s ON s.id = sq.session_id
            WHERE s.status = 'in_progress' AND sq.question_id IN ({placeholders})
            LIMIT 1
            """,
            ids,
        ).fetchone()
        if active:
            raise HTTPException(status_code=409, detail="Timed-exam questions can only be graded by submitting their session")
        rows = {
            row["id"]: dict(row)
            for row in conn.execute(f"SELECT * FROM questions WHERE id IN ({placeholders})", ids)
        }
    results = []
    score = 0
    for answer in payload.answers:
        row = rows.get(answer.question_id)
        if not row:
            continue
        correct = sorted(int(item) for item in json_list(row.get("correct_json")) if isinstance(item, int) or str(item).isdigit())
        selected = sorted(set(int(item) for item in answer.selected))
        is_correct = selected == correct
        score += int(is_correct)
        result = question_public(row, include_answer=True)
        result["selected"] = selected
        result["is_correct"] = is_correct
        results.append(result)
    return {"score": score, "total": len(results), "results": results}


@router.post("/questions/{question_id}/attempt")
def record_attempt(question_id: str, payload: AttemptRequest, candidate: dict = Depends(require_candidate)) -> dict[str, bool]:
    selected = sorted(set(int(item) for item in payload.selected))
    with connect() as conn:
        question = conn.execute(
            "SELECT id, track_id, test_id FROM questions WHERE id = ?",
            (question_id,),
        ).fetchone()
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")
        conn.execute(
            """
            INSERT INTO question_attempts(question_id, selected, correct, mode, candidate_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (question_id, json.dumps(selected), int(payload.correct), payload.mode, candidate["id"]),
        )
        conn.execute(
            """
            INSERT INTO learning_events(event_type, track_id, practice_test_id, question_id, metadata_json, candidate_id)
            VALUES ('question_answered', ?, ?, ?, ?, ?)
            """,
            (
                question["track_id"],
                question["test_id"] or None,
                question_id,
                json.dumps({"mode": payload.mode, "correct": bool(payload.correct)}),
                candidate["id"],
            ),
        )
        today = date.today().isoformat()
        conn.execute(
            """
            INSERT INTO candidate_daily_activity(candidate_id, date, questions_answered, correct_answers)
            VALUES (?, ?, 1, ?)
            ON CONFLICT(candidate_id, date) DO UPDATE SET
              questions_answered = questions_answered + 1,
              correct_answers = correct_answers + excluded.correct_answers
            """,
            (candidate["id"], today, int(payload.correct)),
        )
    return {"ok": True}


@router.get("/questions/{question_id}/bookmark")
def bookmark_state(question_id: str, candidate: dict = Depends(require_candidate)) -> dict[str, bool]:
    with connect() as conn:
        row = conn.execute("SELECT id FROM candidate_bookmarks WHERE candidate_id = ? AND question_id = ?", (candidate["id"], question_id)).fetchone()
    return {"bookmarked": bool(row)}


@router.post("/questions/{question_id}/bookmark")
def toggle_bookmark(question_id: str, candidate: dict = Depends(require_candidate)) -> dict[str, bool]:
    with connect() as conn:
        if not conn.execute("SELECT id FROM questions WHERE id = ?", (question_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Question not found")
        existing = conn.execute("SELECT id FROM candidate_bookmarks WHERE candidate_id = ? AND question_id = ?", (candidate["id"], question_id)).fetchone()
        if existing:
            conn.execute("DELETE FROM candidate_bookmarks WHERE id = ?", (existing["id"],))
            return {"bookmarked": False}
        conn.execute("INSERT INTO candidate_bookmarks(candidate_id, question_id) VALUES (?, ?)", (candidate["id"], question_id))
    return {"bookmarked": True}


@router.get("/questions/{question_id}/notes")
def question_notes(question_id: str, candidate: dict = Depends(require_candidate)) -> dict[str, Any]:
    with connect() as conn:
        rows = [
            dict(row)
            for row in conn.execute(
                "SELECT id, body, created_at FROM candidate_notes WHERE candidate_id = ? AND question_id = ? ORDER BY created_at DESC",
                (candidate["id"], question_id),
            )
        ]
    return {"notes": rows}


@router.post("/questions/{question_id}/notes")
def add_question_note(question_id: str, payload: dict[str, str], candidate: dict = Depends(require_candidate)) -> dict[str, Any]:
    body = (payload.get("body") or "").strip()
    if not body:
        raise HTTPException(status_code=400, detail="Note body is required")
    with connect() as conn:
        if not conn.execute("SELECT id FROM questions WHERE id = ?", (question_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Question not found")
        cursor = conn.execute("INSERT INTO candidate_notes(candidate_id, question_id, body) VALUES (?, ?, ?)", (candidate["id"], question_id, body))
    return {"ok": True, "id": cursor.lastrowid}


def _question_filters(
    track_id: str,
    test_id: str | None,
    q: str,
    tags: str,
    difficulty: str | None,
    unanswered: bool,
    bookmarked: bool,
    source_kind: str | None,
    candidate_id: int | None = None,
) -> tuple[str, list[Any]]:
    filters = ["q.track_id = ?"]
    params: list[Any] = [track_id]
    if test_id:
        filters.append("q.test_id = ?")
        params.append(test_id)
    if q:
        filters.append("(q.question LIKE ? OR q.explanation LIKE ? OR q.test_title LIKE ?)")
        like = f"%{q}%"
        params.extend([like, like, like])
    for tag in [item.strip() for item in tags.split(",") if item.strip()]:
        filters.append("q.tags LIKE ?")
        params.append(f"%{tag}%")
    if difficulty:
        filters.append("q.difficulty = ?")
        params.append(difficulty)
    if source_kind:
        filters.append("q.source_kind = ?")
        params.append(source_kind)
    if unanswered:
        filters.append("NOT EXISTS (SELECT 1 FROM question_attempts qa WHERE qa.question_id = q.id AND qa.candidate_id = ?)")
        params.append(candidate_id)
    if bookmarked:
        filters.append("EXISTS (SELECT 1 FROM candidate_bookmarks b WHERE b.question_id = q.id AND b.candidate_id = ?)")
        params.append(candidate_id)
    return "WHERE " + " AND ".join(filters), params
