from __future__ import annotations

import hmac
from urllib.parse import parse_qs, urlparse

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from ..auth import (
    GOOGLE_LINK_COOKIE,
    candidate_by_email,
    candidate_by_google_subject,
    consume_pending_google_link,
    create_google_candidate,
    create_pending_google_link,
    pending_google_link,
    public_candidate,
    set_session_cookie,
)
from ..config import APP_BASE_URL, AUTH_COOKIE_SECURE, GOOGLE_OIDC_FLOW_MINUTES
from ..google_oidc import (
    consume_google_flow,
    create_google_authorization,
    exchange_google_code,
    verify_google_identity,
)


router = APIRouter()
GOOGLE_OAUTH_STATE_COOKIE = "snowflake_google_oauth_state"


class GoogleLinkRequest(BaseModel):
    password: str = Field(min_length=8, max_length=256)


def _browser_state_matches(request: Request, state: str) -> bool:
    browser_state = request.cookies.get(GOOGLE_OAUTH_STATE_COOKIE) or ""
    return bool(state and browser_state and hmac.compare_digest(browser_state, state))


def _clear_google_state(response: Response) -> None:
    response.delete_cookie(GOOGLE_OAUTH_STATE_COOKIE, path="/")


@router.get("/auth/google/start")
def google_start() -> RedirectResponse:
    authorization_url = create_google_authorization()
    state = (parse_qs(urlparse(authorization_url).query).get("state") or [""])[0]
    if not state:
        raise HTTPException(status_code=500, detail="Google sign-in could not initialize safely.")
    response = RedirectResponse(authorization_url, status_code=302)
    response.set_cookie(
        GOOGLE_OAUTH_STATE_COOKIE,
        state,
        max_age=GOOGLE_OIDC_FLOW_MINUTES * 60,
        httponly=True,
        secure=AUTH_COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    return response


@router.get("/auth/google/callback")
def google_callback(request: Request, code: str = "", state: str = "", error: str = "") -> RedirectResponse:
    # The server-side state record prevents forgery/replay; the short-lived
    # HttpOnly browser cookie additionally binds the transaction to the browser
    # that initiated it and blocks login-CSRF/session-confusion callbacks.
    if not _browser_state_matches(request, state):
        raise HTTPException(status_code=400, detail="Google sign-in request does not match this browser session.")
    if error:
        response = RedirectResponse(f"{APP_BASE_URL}/#/home?google_auth=cancelled", status_code=302)
        _clear_google_state(response)
        return response
    if not code:
        raise HTTPException(status_code=400, detail="Google authorization code is missing.")
    flow = consume_google_flow(state)
    token_payload = exchange_google_code(code, flow["code_verifier"])
    identity = verify_google_identity(str(token_payload["id_token"]), flow["nonce"])

    existing_identity = candidate_by_google_subject(str(identity["sub"]))
    if existing_identity:
        response = RedirectResponse(f"{APP_BASE_URL}/#/home?google_auth=success", status_code=302)
        _clear_google_state(response)
        set_session_cookie(response, existing_identity["id"])
        return response

    existing_account = candidate_by_email(str(identity["email"]))
    if existing_account:
        pending_token = create_pending_google_link(
            int(existing_account["id"]), str(identity["sub"]), str(identity["email"])
        )
        response = RedirectResponse(f"{APP_BASE_URL}/#/home?google_link=required", status_code=302)
        _clear_google_state(response)
        response.set_cookie(
            GOOGLE_LINK_COOKIE,
            pending_token,
            max_age=10 * 60,
            httponly=True,
            secure=AUTH_COOKIE_SECURE,
            samesite="lax",
            path="/",
        )
        return response

    candidate = create_google_candidate(
        str(identity.get("name") or "Candidate"), str(identity["email"]), str(identity["sub"])
    )
    response = RedirectResponse(f"{APP_BASE_URL}/#/home?google_auth=success", status_code=302)
    _clear_google_state(response)
    set_session_cookie(response, candidate["id"])
    return response


@router.get("/auth/google/pending-link")
def google_pending_link(request: Request) -> dict:
    pending = pending_google_link(request.cookies.get(GOOGLE_LINK_COOKIE))
    if not pending:
        return {"pending": False}
    email = str(pending["email"])
    local, _, domain = email.partition("@")
    masked = f"{local[:2]}***@{domain}" if domain else "existing account"
    return {
        "pending": True,
        "email": masked,
        "message": "Sign in once with your existing password to link Google to this account.",
    }


@router.post("/auth/google/link")
def google_link(payload: GoogleLinkRequest, request: Request, response: Response) -> dict:
    token = request.cookies.get(GOOGLE_LINK_COOKIE)
    if not token:
        raise HTTPException(status_code=400, detail="No Google account link is pending.")
    candidate = consume_pending_google_link(token, payload.password)
    set_session_cookie(response, candidate["id"])
    response.delete_cookie(GOOGLE_LINK_COOKIE, path="/")
    return {
        "authenticated": True,
        "candidate": public_candidate(candidate),
        "membership": candidate["membership"],
    }
