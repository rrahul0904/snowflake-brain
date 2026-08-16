from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from ..adaptive_readiness import (
    AdaptiveReadinessError,
    adaptive_question_ids,
    build_readiness,
    latest_readiness,
)
from ..auth import require_candidate


router = APIRouter(prefix="/intelligence/adaptive", tags=["adaptive-intelligence"])


def _candidate_id(candidate: dict[str, Any]) -> int:
    return int(candidate["id"])


@router.get("/readiness")
def readiness(
    track_id: str = Query(default="snowpro-core"),
    refresh: bool = Query(default=True),
    candidate: dict[str, Any] = Depends(require_candidate),
) -> dict[str, Any]:
    try:
        if not refresh:
            existing = latest_readiness(_candidate_id(candidate), track_id)
            if existing:
                return existing
        return build_readiness(_candidate_id(candidate), track_id, persist=True)
    except AdaptiveReadinessError as exc:
        raise HTTPException(status_code=400, detail={"code": "adaptive_readiness_error", "message": str(exc)}) from exc


@router.get("/recommendations")
def recommendations(
    track_id: str = Query(default="snowpro-core"),
    candidate: dict[str, Any] = Depends(require_candidate),
) -> list[dict[str, Any]]:
    try:
        return build_readiness(_candidate_id(candidate), track_id, persist=True)["recommendations"]
    except AdaptiveReadinessError as exc:
        raise HTTPException(status_code=400, detail={"code": "adaptive_readiness_error", "message": str(exc)}) from exc


@router.get("/question-ids")
def question_ids(
    track_id: str = Query(default="snowpro-core"),
    limit: int = Query(default=20, ge=1, le=100),
    candidate: dict[str, Any] = Depends(require_candidate),
) -> dict[str, Any]:
    """Backend recommendation IDs only; no question answer material is exposed."""
    try:
        return {
            "track_id": track_id,
            "question_ids": adaptive_question_ids(_candidate_id(candidate), track_id, limit=limit),
        }
    except AdaptiveReadinessError as exc:
        raise HTTPException(status_code=400, detail={"code": "adaptive_readiness_error", "message": str(exc)}) from exc
