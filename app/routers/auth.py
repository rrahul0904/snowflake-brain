from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator

from ..account_lifecycle import account_status, mark_registration_unverified
from ..auth import (
    COOKIE_NAME,
    authenticate_candidate,
    create_candidate,
    delete_session,
    list_candidate_sessions,
    optional_candidate,
    public_candidate,
    require_candidate,
    revoke_all_candidate_sessions,
    revoke_candidate_session,
    set_session_cookie,
)
from ..billing.service import billing_public_config
from ..google_oidc import google_configured

router = APIRouter()


class SignupRequest(BaseModel):
    display_name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=8, max_length=256)

    @field_validator("email", mode="before")
    @classmethod
    def strip_email(cls, value: str) -> str:
        return str(value).strip().lower()


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=8, max_length=256)

    @field_validator("email", mode="before")
    @classmethod
    def strip_email(cls, value: str) -> str:
        return str(value).strip().lower()


def _public_candidate_with_lifecycle(candidate: dict) -> dict:
    payload = public_candidate(candidate)
    try:
        status = account_status(int(candidate["id"]))
        payload["email_verified"] = bool(status.get("email_verified"))
        payload["email_verified_at"] = status.get("email_verified_at")
        payload["password_login_enabled"] = bool(status.get("password_login_enabled"))
    except Exception:
        # Identity should still be usable if lifecycle status is temporarily unavailable;
        # protected lifecycle APIs remain the source of truth for security changes.
        pass
    return payload


@router.get("/auth/providers")
def auth_providers() -> dict:
    return {
        "google": {"enabled": google_configured()},
        "billing": billing_public_config(),
    }


@router.get("/auth/me")
def auth_me(candidate: dict | None = Depends(optional_candidate)) -> dict:
    if not candidate:
        return {"authenticated": False, "candidate": None, "membership": None}
    return {
        "authenticated": True,
        "candidate": _public_candidate_with_lifecycle(candidate),
        "membership": candidate["membership"],
    }


@router.post("/auth/register", status_code=201)
def auth_register(payload: SignupRequest, response: Response) -> dict:
    candidate = create_candidate(payload.display_name, payload.email, payload.password)
    lifecycle = mark_registration_unverified(candidate["id"])
    set_session_cookie(response, candidate["id"])
    public = public_candidate(candidate)
    public["email_verified"] = False
    public["email_verified_at"] = None
    public["password_login_enabled"] = True
    return {
        "authenticated": True,
        "candidate": public,
        "membership": candidate["membership"],
        **lifecycle,
    }


@router.post("/auth/signup", status_code=201, include_in_schema=False)
def auth_signup_compatibility(payload: SignupRequest, response: Response) -> dict:
    return auth_register(payload, response)


@router.post("/auth/login")
def auth_login(payload: LoginRequest, response: Response) -> dict:
    candidate = authenticate_candidate(payload.email, payload.password)
    set_session_cookie(response, candidate["id"])
    return {
        "authenticated": True,
        "candidate": _public_candidate_with_lifecycle(candidate),
        "membership": candidate["membership"],
    }


@router.post("/auth/logout")
def auth_logout(request: Request, response: Response) -> dict:
    delete_session(request.cookies.get(COOKIE_NAME))
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/auth/sessions")
def auth_sessions(request: Request, candidate: dict = Depends(require_candidate)) -> dict:
    return {
        "sessions": list_candidate_sessions(candidate["id"], request.cookies.get(COOKIE_NAME))
    }


@router.delete("/auth/sessions/{session_id}")
def auth_revoke_session(session_id: int, candidate: dict = Depends(require_candidate)) -> dict:
    if not revoke_candidate_session(candidate["id"], session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"ok": True}


@router.post("/auth/sessions/revoke-all")
def auth_revoke_all_sessions(response: Response, candidate: dict = Depends(require_candidate)) -> dict:
    revoke_all_candidate_sessions(candidate["id"])
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}
