from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..database import connect
from ..evidence import evidence_audit, review_mapping
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


class MappingReviewRequest(BaseModel):
    item_id: str
    skill_id: str
    decision: str
    track_id: str = "snowpro-core"
    replacement_skill_id: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


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


@router.get("/intelligence/evidence-audit")
def certification_evidence_audit(
    track_id: str = "snowpro-core",
    confidence_threshold: float = 0.65,
    limit: int = 50,
) -> dict[str, Any]:
    with connect() as conn:
        return evidence_audit(
            conn,
            track_id=track_id,
            confidence_threshold=confidence_threshold,
            limit=limit,
        )


@router.post("/intelligence/evidence-review")
def certification_evidence_review(payload: MappingReviewRequest) -> dict[str, Any]:
    try:
        with connect() as conn:
            return review_mapping(
                conn,
                mapping_type="question",
                item_id=payload.item_id,
                skill_id=payload.skill_id,
                decision=payload.decision,
                track_id=payload.track_id,
                replacement_skill_id=payload.replacement_skill_id,
                confidence=payload.confidence,
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/intelligence/reindex-skill-map")
def reindex_skill_map(track_id: str = "snowpro-core") -> dict[str, Any]:
    with connect() as conn:
        return build_question_skill_map(conn, track_id)
