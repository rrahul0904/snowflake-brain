from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

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

router = APIRouter()


class MockSessionStart(BaseModel):
    track_id: str = "snowpro-core"
    mode: Literal["quick-mock", "full-mock", "source-exam"] = "quick-mock"
    practice_test_id: str | None = None
    randomize_options: bool | None = None


class SessionAnswer(BaseModel):
    selected: list[int] = Field(default_factory=list)


class SessionFlag(BaseModel):
    flagged: bool = True


class SessionSubmit(BaseModel):
    reason: Literal["learner", "timer"] = "learner"


@router.get("/mock/config")
def mock_config(track_id: str = "snowpro-core") -> dict:
    return public_config(track_id)


@router.post("/mock/sessions")
def start_mock_session(payload: MockSessionStart) -> dict:
    return create_session(
        payload.track_id,
        payload.mode,
        practice_test_id=payload.practice_test_id,
        randomize_options=payload.randomize_options,
    )


@router.get("/mock/sessions/active")
def get_active_mock_session(track_id: str = "snowpro-core") -> dict:
    return {"session": active_session(track_id)}


@router.get("/mock/sessions/{session_id}")
def get_mock_session(session_id: int) -> dict:
    return session_payload(session_id)


@router.put("/mock/sessions/{session_id}/answers/{question_id}")
def put_mock_answer(session_id: int, question_id: str, payload: SessionAnswer) -> dict:
    return save_answer(session_id, question_id, payload.selected)


@router.put("/mock/sessions/{session_id}/questions/{question_id}/flag")
def put_mock_flag(session_id: int, question_id: str, payload: SessionFlag) -> dict:
    return set_flag(session_id, question_id, payload.flagged)


@router.post("/mock/sessions/{session_id}/submit")
def submit_mock(session_id: int, payload: SessionSubmit | None = None) -> dict:
    return submit_session(session_id, (payload or SessionSubmit()).reason)


@router.get("/mock/sessions/{session_id}/result")
def get_mock_result(session_id: int) -> dict:
    return result_payload(session_id)


@router.get("/mock/history")
def get_mock_history(track_id: str = "snowpro-core") -> dict:
    return history(track_id)
