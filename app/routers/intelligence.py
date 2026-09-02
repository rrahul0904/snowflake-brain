from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth import require_candidate, require_premium_candidate
from ..database import connect
from ..intelligence import command_brief, diagnostic_plan, mistake_queue, portfolio, readiness_model, skill_mastery
from ..learning_intelligence import (
    confidence_calibration,
    due_today,
    mistake_notebook,
    mock_remediation,
    set_study_preferences,
    study_plan,
    update_mistake,
)
from ..learning_sync import sync_candidate_learning_state
from ..task_review import due_task_reviews, get_task_review, mark_task_reviewed, reset_task_review, schedule_task_review

router = APIRouter()


class StudyPreferencesRequest(BaseModel):
    track_id: str = "snowpro-core"
    exam_date: str | None = None
    daily_minutes: int = Field(default=45, ge=15, le=240)
    days_per_week: int = Field(default=6, ge=1, le=7)


class MistakeUpdateRequest(BaseModel):
    note: str | None = Field(default=None, max_length=4000)
    root_cause: str | None = Field(default=None, max_length=500)
    status: str | None = None


class TaskReviewRequest(BaseModel):
    track_id: str = "snowpro-core"
    skill_id: str = Field(min_length=1, max_length=200)


def _sync(conn: Any, candidate_id: int, track_id: str) -> None:
    sync_candidate_learning_state(conn, candidate_id, track_id)


@router.get("/intelligence/portfolio")
def certification_portfolio(candidate: dict = Depends(require_premium_candidate)) -> dict[str, Any]:
    with connect() as conn:
        return portfolio(conn, candidate_id=candidate["id"])


@router.get("/intelligence/command-brief")
def certification_command_brief(track_id: str = "snowpro-core", candidate: dict = Depends(require_premium_candidate)) -> dict[str, Any]:
    with connect() as conn:
        return command_brief(conn, track_id, candidate_id=candidate["id"])


@router.get("/intelligence/skill-mastery")
def certification_skill_mastery(track_id: str = "snowpro-core", candidate: dict = Depends(require_candidate)) -> dict[str, Any]:
    with connect() as conn:
        return skill_mastery(conn, track_id, candidate_id=candidate["id"])


@router.get("/intelligence/readiness")
def certification_readiness(track_id: str = "snowpro-core", candidate: dict = Depends(require_premium_candidate)) -> dict[str, Any]:
    with connect() as conn:
        return readiness_model(conn, track_id, candidate_id=candidate["id"])


@router.get("/intelligence/mistake-queue")
def certification_mistake_queue(track_id: str = "snowpro-core", limit: int = 25, candidate: dict = Depends(require_candidate)) -> dict[str, Any]:
    with connect() as conn:
        return mistake_queue(conn, track_id, limit=limit, candidate_id=candidate["id"])


@router.get("/intelligence/due-today")
def certification_due_today(
    track_id: str = "snowpro-core",
    limit: int = 20,
    candidate: dict = Depends(require_candidate),
) -> dict[str, Any]:
    with connect() as conn:
        _sync(conn, candidate["id"], track_id)
        question_due = due_today(conn, candidate["id"], track_id, limit=limit)
        task_due = due_task_reviews(conn, candidate["id"], track_id, limit=limit)
        return {
            **question_due,
            **task_due,
            "due_count": int(question_due.get("due_count") or 0) + int(task_due.get("task_due_count") or 0),
            "question_due_count": int(question_due.get("due_count") or 0),
        }


@router.get("/intelligence/task-review")
def certification_task_review_status(
    track_id: str = "snowpro-core",
    skill_id: str = "",
    candidate: dict = Depends(require_candidate),
) -> dict[str, Any]:
    if not skill_id:
        raise HTTPException(status_code=400, detail="skill_id is required")
    with connect() as conn:
        return {"review": get_task_review(conn, candidate["id"], track_id, skill_id)}


@router.post("/intelligence/task-review")
def certification_schedule_task_review(
    payload: TaskReviewRequest,
    candidate: dict = Depends(require_candidate),
) -> dict[str, Any]:
    with connect() as conn:
        return {"review": schedule_task_review(conn, candidate["id"], payload.track_id, payload.skill_id)}


@router.post("/intelligence/task-review/reviewed")
def certification_mark_task_reviewed(
    payload: TaskReviewRequest,
    candidate: dict = Depends(require_candidate),
) -> dict[str, Any]:
    try:
        with connect() as conn:
            return {"review": mark_task_reviewed(conn, candidate["id"], payload.track_id, payload.skill_id)}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/intelligence/task-review/reset")
def certification_reset_task_review(
    payload: TaskReviewRequest,
    candidate: dict = Depends(require_candidate),
) -> dict[str, Any]:
    with connect() as conn:
        return {"review": reset_task_review(conn, candidate["id"], payload.track_id, payload.skill_id)}


@router.get("/intelligence/mistake-notebook")
def certification_mistake_notebook(
    track_id: str = "snowpro-core",
    status: str = "active",
    limit: int = 50,
    candidate: dict = Depends(require_candidate),
) -> dict[str, Any]:
    with connect() as conn:
        _sync(conn, candidate["id"], track_id)
        return mistake_notebook(conn, candidate["id"], track_id, status=status, limit=limit)


@router.patch("/intelligence/mistake-notebook/{question_id}")
def certification_update_mistake(
    question_id: str,
    payload: MistakeUpdateRequest,
    candidate: dict = Depends(require_candidate),
) -> dict[str, Any]:
    try:
        with connect() as conn:
            return update_mistake(
                conn,
                candidate["id"],
                question_id,
                note=payload.note,
                root_cause=payload.root_cause,
                status=payload.status,
            )
    except ValueError as exc:
        raise HTTPException(status_code=404 if "not found" in str(exc).lower() else 400, detail=str(exc)) from exc


@router.get("/intelligence/confidence-calibration")
def certification_confidence_calibration(
    track_id: str = "snowpro-core",
    candidate: dict = Depends(require_candidate),
) -> dict[str, Any]:
    with connect() as conn:
        return confidence_calibration(conn, candidate["id"], track_id)


@router.get("/intelligence/study-plan")
def certification_study_plan(
    track_id: str = "snowpro-core",
    candidate: dict = Depends(require_candidate),
) -> dict[str, Any]:
    with connect() as conn:
        _sync(conn, candidate["id"], track_id)
        return study_plan(conn, candidate["id"], track_id)


@router.put("/intelligence/study-plan/preferences")
def certification_study_preferences(
    payload: StudyPreferencesRequest,
    candidate: dict = Depends(require_candidate),
) -> dict[str, Any]:
    try:
        with connect() as conn:
            return set_study_preferences(
                conn,
                candidate["id"],
                payload.track_id,
                exam_date=payload.exam_date,
                daily_minutes=payload.daily_minutes,
                days_per_week=payload.days_per_week,
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/intelligence/mock-remediation/{session_id}")
def certification_mock_remediation(
    session_id: int,
    candidate: dict = Depends(require_candidate),
) -> dict[str, Any]:
    try:
        with connect() as conn:
            session = conn.execute("SELECT track_id FROM exam_sessions WHERE id=? AND candidate_id=?", (session_id, candidate["id"])).fetchone()
            if not session:
                raise ValueError("Mock session not found")
            _sync(conn, candidate["id"], str(session["track_id"] or "snowpro-core"))
            return mock_remediation(conn, candidate["id"], session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404 if "not found" in str(exc).lower() else 409, detail=str(exc)) from exc


@router.get("/intelligence/diagnostic")
def certification_diagnostic(track_id: str = "snowpro-core", count: int = 30, candidate: dict = Depends(require_candidate)) -> dict[str, Any]:
    with connect() as conn:
        return diagnostic_plan(conn, track_id, count=count, candidate_id=candidate["id"])
