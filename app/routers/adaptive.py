from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from ..adaptive_readiness import AdaptiveReadinessError, build_readiness, latest_readiness
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
