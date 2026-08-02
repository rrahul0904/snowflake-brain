
from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from ..database import connect
from ..intelligence import (
    build_question_skill_map,
    command_brief,
    diagnostic_plan,
    mistake_queue,
    portfolio,
    readiness_model,
    skill_mastery,
)

router = APIRouter()


@router.get("/intelligence/portfolio")
def certification_portfolio() -> dict[str, Any]:
    with connect() as conn:
        return portfolio(conn)


@router.get("/intelligence/command-brief")
def certification_command_brief(track_id: str = "snowpro-core") -> dict[str, Any]:
    with connect() as conn:
        return command_brief(conn, track_id)


@router.get("/intelligence/skill-mastery")
def certification_skill_mastery(track_id: str = "snowpro-core") -> dict[str, Any]:
    with connect() as conn:
        return skill_mastery(conn, track_id)


@router.get("/intelligence/readiness")
def certification_readiness(track_id: str = "snowpro-core") -> dict[str, Any]:
    with connect() as conn:
        return readiness_model(conn, track_id)


@router.get("/intelligence/mistake-queue")
def certification_mistake_queue(track_id: str = "snowpro-core", limit: int = 25) -> dict[str, Any]:
    with connect() as conn:
        return mistake_queue(conn, track_id, limit=limit)


@router.get("/intelligence/diagnostic")
def certification_diagnostic(track_id: str = "snowpro-core", count: int = 30) -> dict[str, Any]:
    with connect() as conn:
        return diagnostic_plan(conn, track_id, count=count)


@router.post("/intelligence/reindex-skill-map")
def reindex_skill_map(track_id: str = "") -> dict[str, Any]:
    with connect() as conn:
        return build_question_skill_map(conn, track_id)
