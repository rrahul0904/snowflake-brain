from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field, field_validator

from ..auth import (
    COOKIE_NAME,
    SESSION_DAYS,
    authenticate_candidate,
    create_candidate,
    create_session,
    delete_session,
    optional_candidate,
    public_candidate,
    require_candidate,
)
from ..config import AUTH_COOKIE_SECURE

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


def set_session_cookie(response: Response, candidate_id: int) -> None:
    response.set_cookie(
        COOKIE_NAME,
        create_session(candidate_id),
        max_age=SESSION_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=AUTH_COOKIE_SECURE,
        samesite="lax",
        path="/",
    )


@router.get("/auth/me")
def auth_me(candidate: dict | None = Depends(optional_candidate)) -> dict:
    if not candidate:
        return {"authenticated": False, "candidate": None, "membership": None}
    return {
        "authenticated": True,
        "candidate": public_candidate(candidate),
        "membership": candidate["membership"],
    }


@router.post("/auth/register", status_code=201)
def auth_register(payload: SignupRequest, response: Response) -> dict:
    candidate = create_candidate(payload.display_name, payload.email, payload.password)
    set_session_cookie(response, candidate["id"])
    return {
        "authenticated": True,
        "candidate": public_candidate(candidate),
        "membership": candidate["membership"],
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
        "candidate": public_candidate(candidate),
        "membership": candidate["membership"],
    }


@router.post("/auth/logout")
def auth_logout(request: Request, response: Response) -> dict:
    delete_session(request.cookies.get(COOKIE_NAME))
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}
