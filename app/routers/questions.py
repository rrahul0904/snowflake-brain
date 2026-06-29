import json
from datetime import date
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..database import connect
from ..serializers import json_list, question_public

router = APIRouter()


class QuizStartRequest(BaseModel):
    track_id: str | None = None
    course_id: str | None = None
    test_id: str | None = None
    count: int = 10
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


class ExamSessionStart(BaseModel):
    track_id: str | None = None
    course_id: str | None = None
    practice_test_id: str | None = None
    mode: str = "practice"


class ExamSessionAnswerRequest(BaseModel):
    question_id: str
    selected: list[int]


@router.get("/questions")
def questions(
    track_id: str | None = None,
    course_id: str | None = None,
    test_id: str | None = None,
    q: str = "",
    tags: str = "",
    difficulty: str | None = None,
    unanswered: bool = False,
    bookmarked: bool = False,
    limit: int = Query(40, ge=1, le=500),
    offset: int = Query(0, ge=0),
    include_answers: bool = False,
) -> dict[str, Any]:
    where, params = _question_filters(track_id, course_id, test_id, q, tags, difficulty, unanswered, bookmarked)
    with connect() as conn:
        total = conn.execute(f"SELECT COUNT(*) AS count FROM questions q {where}", params).fetchone()["count"]
        rows = [
            question_public(dict(row), include_answer=include_answers)
            for row in conn.execute(
                f"""
                SELECT q.*
                FROM questions q
                {where}
                ORDER BY q.course_title, COALESCE(q.test_position, 0), q.test_title, COALESCE(q.question_position, 0), q.question
                LIMIT ? OFFSET ?
                """,
                [*params, limit, offset],
            )
        ]
    return {"questions": rows, "total": total}


@router.get("/practice-tests")
def practice_tests(
    track_id: str | None = None,
    course_id: str | None = None,
    q: str = "",
    min_questions: int = Query(1, ge=1, le=500),
) -> dict[str, Any]:
    filters = ["pt.question_count >= ?"]
    params: list[Any] = [min_questions]
    if track_id:
        filters.append("pt.track_id = ?")
        params.append(track_id)
    if course_id:
        filters.append("pt.course_id = ?")
        params.append(course_id)
    if q:
        filters.append("(pt.title LIKE ? OR pt.course_title LIKE ? OR pt.track_title LIKE ?)")
        like = f"%{q}%"
        params.extend([like, like, like])
    where = "WHERE " + " AND ".join(filters)
    with connect() as conn:
        rows = [
            dict(row)
            for row in conn.execute(
                f"""
                SELECT
                  pt.track_id,
                  pt.track_title,
                  pt.course_id,
                  pt.course_title,
                  pt.id AS test_id,
                  pt.title AS test_title,
                  pt.original_title,
                  pt.position AS test_position,
                  pt.question_count,
                  SUM(CASE WHEN q.difficulty = 'easy' THEN 1 ELSE 0 END) AS easy_count,
                  SUM(CASE WHEN q.difficulty = 'medium' THEN 1 ELSE 0 END) AS medium_count,
                  SUM(CASE WHEN q.difficulty = 'hard' THEN 1 ELSE 0 END) AS hard_count
                FROM practice_tests pt
                LEFT JOIN questions q ON q.test_id = pt.id
                {where}
                GROUP BY pt.id
                ORDER BY pt.track_title, pt.course_title, pt.position, pt.title
                """,
                params,
            )
        ]
    return {"tests": rows}


@router.post("/exam-sessions")
def create_exam_session(payload: ExamSessionStart) -> dict[str, Any]:
    mode = (payload.mode or "practice").strip().lower()
    if mode not in {"practice", "exam", "drill"}:
        raise HTTPException(status_code=400, detail="Unsupported exam session mode")

    track_id = payload.track_id or ""
    course_id = payload.course_id
    practice_test_id = payload.practice_test_id
    with connect() as conn:
        if practice_test_id:
            test = conn.execute("SELECT * FROM practice_tests WHERE id = ?", (practice_test_id,)).fetchone()
            if not test:
                raise HTTPException(status_code=404, detail="Practice test not found")
            track_id = track_id or test["track_id"] or ""
            course_id = course_id or test["course_id"]
        total_questions = _session_question_count(conn, track_id, course_id, practice_test_id)
        cursor = conn.execute(
            """
            INSERT INTO exam_sessions(track_id, course_id, practice_test_id, mode, total_questions)
            VALUES (?, ?, ?, ?, ?)
            """,
            (track_id, course_id, practice_test_id, mode, total_questions),
        )
        session_id = int(cursor.lastrowid)
        session = _fetch_session(conn, session_id)
        conn.execute(
            """
            INSERT INTO learning_events(event_type, track_id, course_id, practice_test_id, metadata_json)
            VALUES ('exam_session_started', ?, ?, ?, ?)
            """,
            (track_id, course_id, practice_test_id, json.dumps({"session_id": session_id, "mode": mode})),
        )
    return {"session": session}


@router.get("/exam-sessions/{session_id}")
def exam_session(session_id: int) -> dict[str, Any]:
    with connect() as conn:
        session = _fetch_session(conn, session_id)
        answers = [
            dict(row)
            for row in conn.execute(
                """
                SELECT esa.*, q.question, q.course_title, q.test_title
                FROM exam_session_answers esa
                JOIN questions q ON q.id = esa.question_id
                WHERE esa.session_id = ?
                ORDER BY esa.answered_at, esa.id
                """,
                (session_id,),
            )
        ]
    return {"session": session, "answers": answers}


@router.post("/exam-sessions/{session_id}/answers")
def save_exam_session_answer(session_id: int, payload: ExamSessionAnswerRequest) -> dict[str, Any]:
    selected = sorted(set(int(item) for item in payload.selected))
    with connect() as conn:
        session = _fetch_session(conn, session_id)
        if session["status"] == "finished":
            raise HTTPException(status_code=400, detail="Exam session is already finished")
        question = conn.execute("SELECT * FROM questions WHERE id = ?", (payload.question_id,)).fetchone()
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")
        correct = sorted(int(item) for item in json_list(question["correct_json"]) if isinstance(item, int) or str(item).isdigit())
        is_correct = selected == correct
        conn.execute(
            """
            INSERT INTO exam_session_answers(session_id, question_id, selected_json, correct)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(session_id, question_id) DO UPDATE SET
              selected_json = excluded.selected_json,
              correct = excluded.correct,
              answered_at = datetime('now')
            """,
            (session_id, payload.question_id, json.dumps(selected), 1 if is_correct else 0),
        )
        conn.execute(
            """
            INSERT INTO learning_events(event_type, track_id, course_id, practice_test_id, question_id, metadata_json)
            VALUES ('quiz_question_answered', ?, ?, ?, ?, ?)
            """,
            (
                session["track_id"],
                question["course_id"],
                session["practice_test_id"],
                payload.question_id,
                json.dumps({"session_id": session_id, "mode": session["mode"], "correct": is_correct}),
            ),
        )
    return {"ok": True, "correct": is_correct}


@router.post("/exam-sessions/{session_id}/finish")
def finish_exam_session(session_id: int) -> dict[str, Any]:
    with connect() as conn:
        session = _fetch_session(conn, session_id)
        rows = conn.execute(
            """
            SELECT COUNT(*) AS answered, COALESCE(SUM(correct), 0) AS score
            FROM exam_session_answers
            WHERE session_id = ?
            """,
            (session_id,),
        ).fetchone()
        answered = rows["answered"] or 0
        score = rows["score"] or 0
        total = session["total_questions"] or answered
        conn.execute(
            """
            UPDATE exam_sessions
            SET finished_at = datetime('now'),
                score = ?,
                total_questions = ?,
                status = 'finished'
            WHERE id = ?
            """,
            (score, total, session_id),
        )
        conn.execute(
            """
            INSERT INTO learning_events(event_type, track_id, course_id, practice_test_id, metadata_json)
            VALUES ('practice_test_finished', ?, ?, ?, ?)
            """,
            (
                session["track_id"],
                session["course_id"],
                session["practice_test_id"],
                json.dumps({"session_id": session_id, "score": score, "total": total, "answered": answered}),
            ),
        )
        session = _fetch_session(conn, session_id)
    return {"session": session, "score": score, "total": total, "answered": answered}


@router.get("/practice-tests/{test_id}/questions")
def practice_test_questions(test_id: str, include_answers: bool = False) -> dict[str, Any]:
    with connect() as conn:
        test = conn.execute("SELECT * FROM practice_tests WHERE id = ?", (test_id,)).fetchone()
        if not test:
            raise HTTPException(status_code=404, detail="Practice test not found")
        rows = [
            question_public(dict(row), include_answer=include_answers)
            for row in conn.execute(
                """
                SELECT *
                FROM questions
                WHERE test_id = ?
                ORDER BY COALESCE(question_position, 0), question
                """,
                (test_id,),
            )
        ]
    return {"test": dict(test), "questions": rows, "total": len(rows)}


@router.get("/practice-tests-legacy")
def practice_tests_legacy(
    course_id: str | None = None,
    q: str = "",
    min_questions: int = Query(1, ge=1, le=500),
) -> dict[str, Any]:
    filters = ["q.test_title <> ''"]
    params: list[Any] = []
    if course_id:
        filters.append("q.course_id = ?")
        params.append(course_id)
    if q:
        filters.append("(q.test_title LIKE ? OR q.course_title LIKE ?)")
        like = f"%{q}%"
        params.extend([like, like])
    where = "WHERE " + " AND ".join(filters)
    with connect() as conn:
        rows = [
            dict(row)
            for row in conn.execute(
                f"""
                SELECT
                  q.course_id,
                  q.course_title,
                  COALESCE(NULLIF(q.test_id, ''), q.course_id || '|' || q.test_title) AS test_id,
                  q.test_title,
                  MIN(COALESCE(q.test_position, 0)) AS test_position,
                  COUNT(*) AS question_count,
                  SUM(CASE WHEN q.difficulty = 'easy' THEN 1 ELSE 0 END) AS easy_count,
                  SUM(CASE WHEN q.difficulty = 'medium' THEN 1 ELSE 0 END) AS medium_count,
                  SUM(CASE WHEN q.difficulty = 'hard' THEN 1 ELSE 0 END) AS hard_count
                FROM questions q
                {where}
                GROUP BY q.course_id, q.course_title, COALESCE(NULLIF(q.test_id, ''), q.course_id || '|' || q.test_title), q.test_title
                HAVING COUNT(*) >= ?
                ORDER BY q.course_title, test_position, q.test_title
                """,
                [*params, min_questions],
            )
        ]
    return {"tests": rows}


@router.get("/questions/{question_id}")
def question_detail(question_id: str) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM questions WHERE id = ?", (question_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Question not found")
    return question_public(dict(row), include_answer=True)


@router.post("/quiz/start")
def quiz_start(payload: QuizStartRequest) -> dict[str, Any]:
    count = max(1, min(payload.count, 500))
    tags = ",".join(payload.tags or [])
    where, params = _question_filters(
        payload.track_id,
        payload.course_id,
        payload.test_id,
        "",
        tags,
        payload.difficulty,
        payload.unanswered_only,
        False,
    )
    if payload.test_id:
        order = "COALESCE(q.test_position, 0), COALESCE(q.question_position, 0), q.question"
    else:
        order = "RANDOM()" if payload.mode == "random" else "q.course_title, COALESCE(q.test_position, 0), q.test_title, COALESCE(q.question_position, 0)"
    with connect() as conn:
        rows = [
            question_public(dict(row), include_answer=False)
            for row in conn.execute(
                f"""
                SELECT q.*
                FROM questions q
                {where}
                ORDER BY {order}
                LIMIT ?
                """,
                [*params, count],
            )
        ]
    return {"questions": rows, "total": len(rows)}


@router.post("/quiz/grade")
def quiz_grade(payload: QuizGradeRequest) -> dict[str, Any]:
    ids = [answer.question_id for answer in payload.answers]
    if not ids:
        return {"score": 0, "total": 0, "results": []}
    placeholders = ",".join("?" for _ in ids)
    with connect() as conn:
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
        correct = [int(item) for item in json_list(row.get("correct_json"))]
        selected = sorted(set(answer.selected))
        is_correct = selected == sorted(correct)
        score += 1 if is_correct else 0
        result = question_public(row, include_answer=True)
        result["selected"] = selected
        result["is_correct"] = is_correct
        results.append(result)
    return {"score": score, "total": len(results), "results": results}


@router.post("/questions/{question_id}/attempt")
def record_attempt(question_id: str, payload: AttemptRequest) -> dict[str, bool]:
    with connect() as conn:
        row = conn.execute("SELECT id FROM questions WHERE id = ?", (question_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Question not found")
        conn.execute(
            """
            INSERT INTO question_attempts(question_id, selected, correct, mode)
            VALUES (?, ?, ?, ?)
            """,
            (question_id, json.dumps(payload.selected), 1 if payload.correct else 0, payload.mode),
        )
        question = conn.execute("SELECT course_id, test_id FROM questions WHERE id = ?", (question_id,)).fetchone()
        conn.execute(
            """
            INSERT INTO learning_events(event_type, course_id, practice_test_id, question_id, metadata_json)
            VALUES ('quiz_question_answered', ?, ?, ?, ?)
            """,
            (
                question["course_id"] if question else None,
                question["test_id"] if question else None,
                question_id,
                json.dumps({"mode": payload.mode, "correct": bool(payload.correct)}),
            ),
        )
        today = date.today().isoformat()
        conn.execute(
            """
            INSERT INTO daily_activity(date, questions_answered, correct_answers)
            VALUES (?, 1, ?)
            ON CONFLICT(date) DO UPDATE SET
              questions_answered = questions_answered + 1,
              correct_answers = correct_answers + excluded.correct_answers
            """,
            (today, 1 if payload.correct else 0),
        )
    return {"ok": True}


@router.get("/questions/{question_id}/bookmark")
def bookmark_state(question_id: str) -> dict[str, bool]:
    with connect() as conn:
        row = conn.execute("SELECT id FROM bookmarks WHERE question_id = ? LIMIT 1", (question_id,)).fetchone()
    return {"bookmarked": bool(row)}


@router.post("/questions/{question_id}/bookmark")
def toggle_bookmark(question_id: str) -> dict[str, bool]:
    with connect() as conn:
        existing = conn.execute("SELECT id FROM bookmarks WHERE question_id = ? LIMIT 1", (question_id,)).fetchone()
        if existing:
            conn.execute("DELETE FROM bookmarks WHERE id = ?", (existing["id"],))
            return {"bookmarked": False}
        if not conn.execute("SELECT id FROM questions WHERE id = ?", (question_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Question not found")
        conn.execute("INSERT INTO bookmarks(question_id) VALUES (?)", (question_id,))
    return {"bookmarked": True}


@router.get("/questions/{question_id}/notes")
def question_notes(question_id: str) -> dict[str, Any]:
    with connect() as conn:
        rows = [
            dict(row)
            for row in conn.execute(
                "SELECT id, body, created_at FROM notes WHERE question_id = ? ORDER BY created_at DESC",
                (question_id,),
            )
        ]
    return {"notes": rows}


@router.post("/questions/{question_id}/notes")
def add_question_note(question_id: str, payload: dict[str, str]) -> dict[str, Any]:
    body = (payload.get("body") or "").strip()
    if not body:
        raise HTTPException(status_code=400, detail="Note body is required")
    with connect() as conn:
        if not conn.execute("SELECT id FROM questions WHERE id = ?", (question_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Question not found")
        cursor = conn.execute("INSERT INTO notes(question_id, body) VALUES (?, ?)", (question_id, body))
    return {"ok": True, "id": cursor.lastrowid}


def _question_filters(
    track_id: str | None,
    course_id: str | None,
    test_id: str | None,
    q: str,
    tags: str,
    difficulty: str | None,
    unanswered: bool,
    bookmarked: bool,
) -> tuple[str, list[Any]]:
    filters = []
    params: list[Any] = []
    if track_id:
        filters.append("EXISTS (SELECT 1 FROM courses c WHERE c.id = q.course_id AND c.track_id = ?)")
        params.append(track_id)
    if course_id:
        filters.append("q.course_id = ?")
        params.append(course_id)
    if test_id:
        filters.append("COALESCE(NULLIF(q.test_id, ''), q.course_id || '|' || q.test_title) = ?")
        params.append(test_id)
    if q:
        filters.append("(q.question LIKE ? OR q.explanation LIKE ? OR q.test_title LIKE ? OR q.course_title LIKE ?)")
        like = f"%{q}%"
        params.extend([like, like, like, like])
    for tag in [item.strip() for item in tags.split(",") if item.strip()]:
        filters.append("q.tags LIKE ?")
        params.append(f"%{tag}%")
    if difficulty:
        filters.append("q.difficulty = ?")
        params.append(difficulty)
    if unanswered:
        filters.append("NOT EXISTS (SELECT 1 FROM question_attempts qa WHERE qa.question_id = q.id)")
    if bookmarked:
        filters.append("EXISTS (SELECT 1 FROM bookmarks b WHERE b.question_id = q.id)")
    return ("WHERE " + " AND ".join(filters) if filters else "", params)


def _session_question_count(
    conn: Any,
    track_id: str | None,
    course_id: str | None,
    practice_test_id: str | None,
) -> int:
    where, params = _question_filters(track_id, course_id, practice_test_id, "", "", None, False, False)
    return int(conn.execute(f"SELECT COUNT(*) AS count FROM questions q {where}", params).fetchone()["count"] or 0)


def _fetch_session(conn: Any, session_id: int) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM exam_sessions WHERE id = ?", (session_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Exam session not found")
    data = dict(row)
    answered = conn.execute(
        "SELECT COUNT(*) AS count FROM exam_session_answers WHERE session_id = ?",
        (session_id,),
    ).fetchone()["count"]
    data["answered_count"] = answered or 0
    return data
