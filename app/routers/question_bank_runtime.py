from __future__ import annotations

import json
from datetime import date
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth import require_candidate, require_owned_mock_session
from ..database import connect
from ..entitlements import reserve_daily_questions, validate_mock_start
from ..mock_exam import (
    active_session,
    history,
    public_config,
    result_payload,
    save_answer,
    session_payload,
    set_flag,
    submit_session,
)
from ..question_bank import (
    candidate_was_served_question,
    question_review_metadata,
    record_question_answer,
)
from ..question_bank_exam import create_tier_mock_session
from ..question_bank_selection import select_certification_questions
from ..routers.certification_practice import CertificationQuizStart
from ..serializers import json_list, question_public

router = APIRouter()


class TierMockSessionStart(BaseModel):
    track_id: str = "snowpro-core"
    mode: Literal["weekly-mock", "lifetime-practice", "quick-mock", "full-mock"] = "quick-mock"
    randomize_options: bool | None = None


class SessionAnswer(BaseModel):
    selected: list[int] = Field(default_factory=list)


class SessionFlag(BaseModel):
    flagged: bool = True


class SessionSubmit(BaseModel):
    reason: Literal["learner", "timer"] = "learner"


class QuizAnswer(BaseModel):
    question_id: str
    selected: list[int] = Field(default_factory=list)


class QuizGradeRequest(BaseModel):
    answers: list[QuizAnswer]


class AttemptRequest(BaseModel):
    selected: list[int] = Field(default_factory=list)
    correct: bool | None = None  # legacy client field; ignored
    mode: str = "practice"
    response_time_ms: int | None = Field(default=None, ge=0, le=3_600_000)
    confidence: int | None = Field(default=None, ge=1, le=5)


def _must_have_been_served(candidate_id: int, question_id: str) -> None:
    # All question detail/grade/attempt lookups are bound to a previous server
    # selection. This avoids making even fallback questions enumerable.
    if not candidate_was_served_question(candidate_id, question_id):
        raise HTTPException(status_code=404, detail="Question not found")


def _candidate_question(row: dict[str, Any]) -> dict[str, Any]:
    allowed = {"id", "question", "options", "multiple", "difficulty", "position", "selected", "answered", "flagged"}
    return {key: value for key, value in row.items() if key in allowed}


def _candidate_mock(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not payload:
        return payload
    clean = {key: value for key, value in payload.items() if key not in {"configuration", "practice_test_id"}}
    if "questions" in clean:
        clean["questions"] = [_candidate_question(dict(item)) for item in clean.get("questions") or []]
    return clean


def _candidate_result(payload: dict[str, Any]) -> dict[str, Any]:
    clean = dict(payload)
    reviews = []
    for item in clean.get("reviews") or []:
        row = dict(item)
        row.pop("source_kind", None)
        row.pop("test_title", None)
        reviews.append(row)
    if "reviews" in clean:
        clean["reviews"] = reviews
    return clean


@router.get("/mock/config")
def candidate_mock_config(track_id: str = "snowpro-core", candidate: dict[str, Any] = Depends(require_candidate)) -> dict[str, Any]:
    del candidate
    payload = dict(public_config(track_id))
    payload.pop("question_bank", None)
    return payload


@router.post("/certification-quiz/start")
def start_candidate_practice(payload: CertificationQuizStart, candidate: dict[str, Any] = Depends(require_candidate)) -> dict[str, Any]:
    if payload.test_id:
        raise HTTPException(
            status_code=403,
            detail={"code": "session_required", "message": "Private source sets are not part of the candidate product. Start practice from the Free or Premium experience."},
        )
    selected = select_certification_questions(payload, candidate, trusted_exam_session=False)
    return {
        "questions": [_candidate_question(dict(item)) for item in selected.get("questions") or []],
        "total": int(selected.get("total") or 0),
        "quota": selected.get("quota"),
    }


@router.post("/mock/sessions")
def start_candidate_mock(payload: TierMockSessionStart, candidate: dict[str, Any] = Depends(require_candidate)) -> dict[str, Any]:
    if active_session(payload.track_id, candidate["id"]):
        raise HTTPException(status_code=409, detail={"code": "active_mock_must_be_completed", "message": "Resume and complete your active timed mock before starting another."})
    normalized_mode = validate_mock_start(candidate, payload.mode)
    if candidate.get("is_premium") and normalized_mode == "quick-mock":
        quick_count = int(public_config(payload.track_id).get("quick_mock", {}).get("question_count") or 30)
        reserve_daily_questions(candidate["id"], candidate["membership"], quick_count)
    return _candidate_mock(
        create_tier_mock_session(
            candidate,
            payload.track_id,
            normalized_mode,
            practice_test_id=None,
            randomize_options=payload.randomize_options,
        )
    ) or {}


@router.get("/mock/sessions/active")
def get_active_candidate_mock(track_id: str = "snowpro-core", candidate: dict[str, Any] = Depends(require_candidate)) -> dict[str, Any]:
    return {"session": _candidate_mock(active_session(track_id, candidate["id"]))}


@router.get("/mock/sessions/{session_id}")
def get_candidate_mock(session_id: int, candidate: dict[str, Any] = Depends(require_candidate)) -> dict[str, Any]:
    require_owned_mock_session(session_id, candidate["id"])
    return _candidate_mock(session_payload(session_id)) or {}


@router.put("/mock/sessions/{session_id}/answers/{question_id}")
def put_candidate_mock_answer(session_id: int, question_id: str, payload: SessionAnswer, candidate: dict[str, Any] = Depends(require_candidate)) -> dict[str, Any]:
    require_owned_mock_session(session_id, candidate["id"])
    return save_answer(session_id, question_id, payload.selected)


@router.put("/mock/sessions/{session_id}/questions/{question_id}/flag")
def put_candidate_mock_flag(session_id: int, question_id: str, payload: SessionFlag, candidate: dict[str, Any] = Depends(require_candidate)) -> dict[str, Any]:
    require_owned_mock_session(session_id, candidate["id"])
    return set_flag(session_id, question_id, payload.flagged)


@router.post("/mock/sessions/{session_id}/submit")
def submit_candidate_mock(session_id: int, payload: SessionSubmit | None = None, candidate: dict[str, Any] = Depends(require_candidate)) -> dict[str, Any]:
    require_owned_mock_session(session_id, candidate["id"])
    return _candidate_result(submit_session(session_id, (payload or SessionSubmit()).reason))


@router.get("/mock/sessions/{session_id}/result")
def get_candidate_mock_result(session_id: int, candidate: dict[str, Any] = Depends(require_candidate)) -> dict[str, Any]:
    require_owned_mock_session(session_id, candidate["id"])
    return _candidate_result(result_payload(session_id))


@router.get("/mock/history")
def get_candidate_mock_history(track_id: str = "snowpro-core", candidate: dict[str, Any] = Depends(require_candidate)) -> dict[str, Any]:
    return history(track_id, candidate["id"])


@router.get("/questions")
def block_question_inventory(candidate: dict[str, Any] = Depends(require_candidate)) -> dict[str, Any]:
    del candidate
    raise HTTPException(status_code=403, detail={"code": "session_required", "message": "Questions are delivered through your practice and mock sessions."})


@router.get("/practice-tests")
def hide_internal_test_inventory(candidate: dict[str, Any] = Depends(require_candidate)) -> dict[str, Any]:
    del candidate
    return {"tests": []}


@router.get("/practice-tests/{test_id}/questions")
def block_bulk_test_questions(test_id: str, candidate: dict[str, Any] = Depends(require_candidate)) -> dict[str, Any]:
    del test_id, candidate
    raise HTTPException(status_code=403, detail={"code": "session_required", "message": "Start an entitled exam session to receive questions."})


@router.get("/questions/{question_id}")
def get_served_candidate_question(question_id: str, candidate: dict[str, Any] = Depends(require_candidate)) -> dict[str, Any]:
    _must_have_been_served(candidate["id"], question_id)
    with connect() as conn:
        row = conn.execute("SELECT * FROM questions WHERE id=?", (question_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Question not found")
    return _candidate_question(question_public(dict(row), include_answer=False))


@router.post("/quiz/grade")
def grade_candidate_practice(payload: QuizGradeRequest, candidate: dict[str, Any] = Depends(require_candidate)) -> dict[str, Any]:
    ids = [answer.question_id for answer in payload.answers]
    if not ids:
        return {"score": 0, "total": 0, "results": []}
    if len(ids) > 500 or len(set(ids)) != len(ids):
        raise HTTPException(status_code=400, detail="Practice submission contains invalid question identifiers")
    for question_id in ids:
        _must_have_been_served(candidate["id"], question_id)
    placeholders = ",".join("?" for _ in ids)
    with connect() as conn:
        active = conn.execute(
            f"SELECT 1 FROM exam_session_questions sq JOIN exam_sessions s ON s.id=sq.session_id WHERE s.status='in_progress' AND s.candidate_id=? AND sq.question_id IN ({placeholders}) LIMIT 1",
            [candidate["id"], *ids],
        ).fetchone()
        if active:
            raise HTTPException(status_code=409, detail="Timed-exam questions can only be graded by submitting their session")
        rows = {row["id"]: dict(row) for row in conn.execute(f"SELECT * FROM questions WHERE id IN ({placeholders})", ids)}
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
        result = _candidate_question(question_public(row, include_answer=True))
        result["correct"] = correct
        result["explanation"] = row.get("explanation") or ""
        result["selected"] = selected
        result["is_correct"] = is_correct
        metadata = question_review_metadata(answer.question_id)
        if metadata.get("distractor_rationales"):
            result["option_rationales"] = metadata["distractor_rationales"]
        results.append(result)
    return {"score": score, "total": len(results), "results": results}


@router.post("/questions/{question_id}/attempt")
def record_candidate_attempt(question_id: str, payload: AttemptRequest, candidate: dict[str, Any] = Depends(require_candidate)) -> dict[str, bool]:
    _must_have_been_served(candidate["id"], question_id)
    selected = sorted(set(int(item) for item in payload.selected))
    with connect() as conn:
        question = conn.execute("SELECT id, track_id, test_id, correct_json FROM questions WHERE id=?", (question_id,)).fetchone()
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")
        correct_options = sorted(int(item) for item in json_list(question["correct_json"]) if isinstance(item, int) or str(item).isdigit())
        is_correct = selected == correct_options
        conn.execute("INSERT INTO question_attempts(question_id, selected, correct, mode, candidate_id) VALUES (?, ?, ?, ?, ?)", (question_id, json.dumps(selected), int(is_correct), payload.mode, candidate["id"]))
        conn.execute(
            "INSERT INTO learning_events(event_type, track_id, practice_test_id, question_id, metadata_json, candidate_id) VALUES ('question_answered', ?, ?, ?, ?, ?)",
            (question["track_id"], question["test_id"] or None, question_id, json.dumps({"mode": payload.mode, "correct": is_correct}), candidate["id"]),
        )
        today = date.today().isoformat()
        conn.execute(
            "INSERT INTO candidate_daily_activity(candidate_id,date,questions_answered,correct_answers) VALUES (?,?,1,?) ON CONFLICT(candidate_id,date) DO UPDATE SET questions_answered=questions_answered+1, correct_answers=correct_answers+excluded.correct_answers",
            (candidate["id"], today, int(is_correct)),
        )
    record_question_answer(candidate["id"], question_id, selected=selected, correct=is_correct, response_time_ms=payload.response_time_ms, confidence=payload.confidence)
    return {"ok": True}
