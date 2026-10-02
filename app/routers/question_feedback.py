from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..admin_operations import audit, require_admin
from ..auth import require_candidate
from ..question_bank import candidate_was_served_question
from ..question_feedback import (
    QuestionFeedbackError,
    candidate_question_feedback,
    editorial_question_feedback,
    submit_question_feedback,
    update_question_feedback,
)


router = APIRouter(tags=["question-feedback"])


class QuestionFeedbackSubmission(BaseModel):
    category: str = Field(pattern="^(ambiguous|incorrect_answer|outdated|explanation|typo|other)$")
    description: str = Field(min_length=3, max_length=3000)


class QuestionFeedbackResolution(BaseModel):
    status: str = Field(pattern="^(triaged|resolved|rejected)$")
    resolution_notes: str = Field(default="", max_length=3000)


def _admin(candidate: dict = Depends(require_candidate)) -> dict:
    return require_admin(candidate)


@router.post("/questions/{question_id}/feedback")
def create_question_feedback(
    question_id: str,
    payload: QuestionFeedbackSubmission,
    candidate: dict = Depends(require_candidate),
) -> dict:
    if not candidate_was_served_question(candidate["id"], question_id):
        raise HTTPException(status_code=404, detail="Question not found")
    try:
        report = submit_question_feedback(
            question_id,
            int(candidate["id"]),
            payload.category,
            payload.description,
        )
    except QuestionFeedbackError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "feedback": report}


@router.get("/question-feedback")
def my_question_feedback(
    limit: int = Query(100, ge=1, le=200),
    candidate: dict = Depends(require_candidate),
) -> dict:
    return {"feedback": candidate_question_feedback(int(candidate["id"]), limit=limit)}


@router.get("/admin/question-feedback")
def get_editorial_question_feedback(
    status: str = Query("open", pattern="^(open|triaged|resolved|rejected)?$"),
    limit: int = Query(200, ge=1, le=500),
    candidate: dict = Depends(_admin),
) -> dict:
    audit(candidate["id"], "admin.question_feedback.viewed")
    try:
        return {"feedback": editorial_question_feedback(status=status, limit=limit)}
    except QuestionFeedbackError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/admin/question-feedback/{feedback_id}")
def resolve_editorial_question_feedback(
    feedback_id: int,
    payload: QuestionFeedbackResolution,
    candidate: dict = Depends(_admin),
) -> dict:
    try:
        report = update_question_feedback(
            feedback_id,
            status=payload.status,
            actor=str(candidate.get("email") or candidate.get("id")),
            resolution_notes=payload.resolution_notes,
        )
    except QuestionFeedbackError as exc:
        raise HTTPException(status_code=404 if "not found" in str(exc).lower() else 400, detail=str(exc)) from exc
    audit(candidate["id"], "admin.question_feedback.updated", metadata={"feedback_id": feedback_id, "status": payload.status})
    return {"ok": True, "feedback": report}
