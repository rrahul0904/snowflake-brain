from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from ..affiliate_resources import affiliate_resource_payload
from ..auth import require_candidate

router = APIRouter()


@router.get("/resources/affiliate")
def affiliate_resources(candidate: dict[str, Any] = Depends(require_candidate)) -> dict[str, Any]:
    del candidate
    return affiliate_resource_payload()
