from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth import require_candidate, require_owned_mock_session
from ..database import connect
from ..entitlements import reserve_daily_questions, validate_mock_start
from ..mock_exam import (
    active_session,
    create_session,
    history,
    public_config,
    result_payload,
    save_answer,
    session_payload,
    set_flag,
    submit_session,
)
from ..mock_replay import append_event, record_answer_event, record_flag_event, replay_payload
from ..serializers import json_list

router = APIRouter()


class MockSessionStart(BaseModel):
    track_id: str = "snowpro-core"
    mode: Literal["weekly-mock", "lifetime-practice", "quick-mock", "full-mock", "source-exam"] = "quick-mock"
    practice_test_id: str | None = None
    randomize_options: bool | None = None


class SessionAnswer(BaseModel):
    selected: list[int] = Field(default_factory=list)


class SessionFlag(BaseModel):
    flagged: bool = True


class SessionSubmit(BaseModel):
    reason: Literal["learner", "timer"] = "learner"


class SessionReplayEvent(BaseModel):
    event_type: Literal["question_viewed", "question_navigated_from", "question_navigated_to", "session_resumed"]
    question_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


@router.get("/mock/config")
def mock_config(track_id: str = "snowpro-core") -> dict:
    return public_config(track_id)


@router.post("/mock/sessions")
def start_mock_session(payload: MockSessionStart, candidate: dict = Depends(require_candidate)) -> dict:
    if active_session(payload.track_id, candidate["id"]):
        raise HTTPException(status_code=409, detail={"code": "active_mock_must_be_completed", "message": "Resume and complete your active timed mock before starting another."})
    normalized_mode = validate_mock_start(candidate, payload.mode)
    if candidate["is_premium"] and normalized_mode == "quick-mock":
        quick_count = int(public_config(payload.track_id).get("quick_mock", {}).get("question_count") or 30)
        reserve_daily_questions(candidate["id"], candidate["membership"], quick_count)
    return create_session(
        payload.track_id,
        normalized_mode,
        practice_test_id=payload.practice_test_id,
        randomize_options=payload.randomize_options,
        candidate_id=candidate["id"],
    )


@router.get("/mock/sessions/active")
def get_active_mock_session(track_id: str = "snowpro-core", candidate: dict = Depends(require_candidate)) -> dict:
    return {"session": active_session(track_id, candidate["id"])}


@router.get("/mock/sessions/{session_id}")
def get_mock_session(session_id: int, candidate: dict = Depends(require_candidate)) -> dict:
    require_owned_mock_session(session_id, candidate["id"])
    return session_payload(session_id)


@router.post("/mock/sessions/{session_id}/events")
def post_mock_replay_event(
    session_id: int,
    payload: SessionReplayEvent,
    candidate: dict = Depends(require_candidate),
) -> dict:
    require_owned_mock_session(session_id, candidate["id"])
    try:
        with connect() as conn:
            session = conn.execute("SELECT status FROM exam_sessions WHERE id=? AND candidate_id=?", (session_id, candidate["id"])).fetchone()
            if not session or str(session["status"]) != "in_progress":
                raise HTTPException(status_code=409, detail="Replay events are accepted only during an active mock")
            append_event(
                conn,
                session_id=session_id,
                candidate_id=candidate["id"],
                question_id=payload.question_id,
                event_type=payload.event_type,
                metadata=payload.metadata,
                client_event=True,
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}


@router.put("/mock/sessions/{session_id}/answers/{question_id}")
def put_mock_answer(session_id: int, question_id: str, payload: SessionAnswer, candidate: dict = Depends(require_candidate)) -> dict:
    require_owned_mock_session(session_id, candidate["id"])
    with connect() as conn:
        previous = conn.execute(
            "SELECT selected_json FROM exam_session_answers WHERE session_id=? AND question_id=?",
            (session_id, question_id),
        ).fetchone()
        previous_selected = [int(item) for item in json_list(previous["selected_json"])] if previous else []
    result = save_answer(session_id, question_id, payload.selected)
    with connect() as conn:
        record_answer_event(
            conn,
            session_id=session_id,
            candidate_id=candidate["id"],
            question_id=question_id,
            previous=previous_selected,
            selected=result.get("selected") or [],
        )
    return result


@router.put("/mock/sessions/{session_id}/questions/{question_id}/flag")
def put_mock_flag(session_id: int, question_id: str, payload: SessionFlag, candidate: dict = Depends(require_candidate)) -> dict:
    require_owned_mock_session(session_id, candidate["id"])
    with connect() as conn:
        previous = conn.execute(
            "SELECT flagged FROM exam_session_questions WHERE session_id=? AND question_id=?",
            (session_id, question_id),
        ).fetchone()
        previous_flagged = bool(previous["flagged"]) if previous else False
    result = set_flag(session_id, question_id, payload.flagged)
    if previous_flagged != bool(payload.flagged):
        with connect() as conn:
            record_flag_event(
                conn,
                session_id=session_id,
                candidate_id=candidate["id"],
                question_id=question_id,
                flagged=bool(payload.flagged),
            )
    return result


@router.post("/mock/sessions/{session_id}/submit")
def submit_mock(session_id: int, payload: SessionSubmit | None = None, candidate: dict = Depends(require_candidate)) -> dict:
    require_owned_mock_session(session_id, candidate["id"])
    reason = (payload or SessionSubmit()).reason
    result = submit_session(session_id, reason)
    with connect() as conn:
        append_event(
            conn,
            session_id=session_id,
            candidate_id=candidate["id"],
            event_type="timer_expired" if reason == "timer" else "session_submitted",
            metadata={"reason": reason},
        )
    return result


@router.get("/mock/sessions/{session_id}/result")
def get_mock_result(session_id: int, candidate: dict = Depends(require_candidate)) -> dict:
    require_owned_mock_session(session_id, candidate["id"])
    return result_payload(session_id)


@router.get("/mock/sessions/{session_id}/replay")
def get_mock_replay(session_id: int, candidate: dict = Depends(require_candidate)) -> dict:
    require_owned_mock_session(session_id, candidate["id"])
    try:
        with connect() as conn:
            return replay_payload(conn, session_id, candidate["id"])
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/mock/history")
def get_mock_history(track_id: str = "snowpro-core", candidate: dict = Depends(require_candidate)) -> dict:
    return history(track_id, candidate["id"])
