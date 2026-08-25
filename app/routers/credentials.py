from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field

from ..auth import require_candidate
from ..credential_verification import (
    CredentialAlreadyClaimedError,
    CredentialVerificationError,
    delete_candidate_credential,
    get_talent_profile,
    list_candidate_credentials,
    reverify_credential,
    update_talent_profile,
    verify_credly_credential,
)


router = APIRouter(tags=["verified-credentials"])


class CredlyCredentialRequest(BaseModel):
    credential_url: str = Field(min_length=20, max_length=500)


class TalentProfileUpdate(BaseModel):
    headline: str | None = Field(default=None, max_length=160)
    location: str | None = Field(default=None, max_length=160)
    availability: Literal["not_looking", "open_to_work", "open_to_contract", "available_now"] | None = None
    recruiter_discoverable: bool | None = None
    public_profile: bool | None = None


def _candidate_id(candidate: dict[str, Any]) -> int:
    return int(candidate["id"])


def _verification_error(exc: CredentialVerificationError, *, default_status: int = 422) -> HTTPException:
    code = 409 if isinstance(exc, CredentialAlreadyClaimedError) else default_status
    return HTTPException(status_code=code, detail={"code": "credential_verification_error", "message": str(exc)})


@router.get("/credentials")
def credentials(candidate: dict[str, Any] = Depends(require_candidate)) -> dict[str, Any]:
    rows = list_candidate_credentials(_candidate_id(candidate))
    return {
        "credentials": rows,
        "verified_count": sum(1 for row in rows if row.get("verification_status") == "verified"),
    }


@router.post("/credentials/credly/verify", status_code=status.HTTP_201_CREATED)
def verify_credly(
    payload: CredlyCredentialRequest,
    candidate: dict[str, Any] = Depends(require_candidate),
) -> dict[str, Any]:
    try:
        credential = verify_credly_credential(candidate, payload.credential_url)
    except CredentialVerificationError as exc:
        raise _verification_error(exc) from exc
    return {"credential": credential, "profile": get_talent_profile(_candidate_id(candidate))}


@router.post("/credentials/{credential_uid}/reverify")
def reverify(
    credential_uid: str,
    candidate: dict[str, Any] = Depends(require_candidate),
) -> dict[str, Any]:
    try:
        credential = reverify_credential(candidate, credential_uid)
    except CredentialVerificationError as exc:
        raise _verification_error(exc, default_status=404 if "not found" in str(exc).lower() else 422) from exc
    return {"credential": credential, "profile": get_talent_profile(_candidate_id(candidate))}


@router.delete("/credentials/{credential_uid}", status_code=status.HTTP_204_NO_CONTENT)
def remove_credential(
    credential_uid: str,
    candidate: dict[str, Any] = Depends(require_candidate),
) -> Response:
    try:
        delete_candidate_credential(_candidate_id(candidate), credential_uid)
    except CredentialVerificationError as exc:
        raise _verification_error(exc, default_status=404) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/talent/profile")
def talent_profile(candidate: dict[str, Any] = Depends(require_candidate)) -> dict[str, Any]:
    profile = get_talent_profile(_candidate_id(candidate))
    profile["credentials"] = list_candidate_credentials(_candidate_id(candidate))
    return profile


@router.patch("/talent/profile")
def talent_profile_update(
    payload: TalentProfileUpdate,
    candidate: dict[str, Any] = Depends(require_candidate),
) -> dict[str, Any]:
    try:
        return update_talent_profile(
            _candidate_id(candidate),
            headline=payload.headline,
            location=payload.location,
            availability=payload.availability,
            recruiter_discoverable=payload.recruiter_discoverable,
            public_profile=payload.public_profile,
        )
    except CredentialVerificationError as exc:
        raise _verification_error(exc) from exc
