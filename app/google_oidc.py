from __future__ import annotations

import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import id_token as google_id_token

from .config import (
    GOOGLE_AUTH_ENABLED,
    GOOGLE_OIDC_CLIENT_ID,
    GOOGLE_OIDC_CLIENT_SECRET,
    GOOGLE_OIDC_FLOW_MINUTES,
    GOOGLE_OIDC_REDIRECT_URI,
)
from .database import connect
from .identity_billing_schema import ensure_identity_billing_schema


AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
VALID_ISSUERS = {"https://accounts.google.com", "accounts.google.com"}


def google_configured() -> bool:
    return bool(
        GOOGLE_AUTH_ENABLED
        and GOOGLE_OIDC_CLIENT_ID
        and GOOGLE_OIDC_CLIENT_SECRET
        and GOOGLE_OIDC_REDIRECT_URI
    )


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _hash_token(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def create_google_authorization() -> str:
    if not google_configured():
        raise HTTPException(
            status_code=503,
            detail={"code": "google_auth_unavailable", "message": "Google sign-in is not configured in this environment."},
        )
    ensure_identity_billing_schema()
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    challenge = _b64url(hashlib.sha256(verifier.encode("ascii")).digest())
    expires = datetime.now(timezone.utc) + timedelta(minutes=GOOGLE_OIDC_FLOW_MINUTES)
    with connect() as conn:
        conn.execute("DELETE FROM oauth_login_flows WHERE datetime(expires_at)<=datetime('now') OR consumed_at IS NOT NULL")
        conn.execute(
            "INSERT INTO oauth_login_flows(state_hash,provider,nonce,code_verifier,expires_at) VALUES (?,'google',?,?,?)",
            (_hash_token(state), nonce, verifier, expires.isoformat()),
        )
    params = {
        "client_id": GOOGLE_OIDC_CLIENT_ID,
        "redirect_uri": GOOGLE_OIDC_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "nonce": nonce,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "prompt": "select_account",
    }
    return f"{AUTHORIZATION_ENDPOINT}?{urlencode(params)}"


def consume_google_flow(state: str) -> dict[str, str]:
    if not state:
        raise HTTPException(status_code=400, detail="Missing OAuth state")
    ensure_identity_billing_schema()
    state_hash = _hash_token(state)
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT nonce,code_verifier FROM oauth_login_flows "
            "WHERE state_hash=? AND provider='google' AND consumed_at IS NULL AND datetime(expires_at)>datetime('now')",
            (state_hash,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=400, detail="Google sign-in request is invalid or expired.")
        conn.execute(
            "UPDATE oauth_login_flows SET consumed_at=datetime('now') WHERE state_hash=?",
            (state_hash,),
        )
    return {"nonce": str(row["nonce"]), "code_verifier": str(row["code_verifier"])}


def exchange_google_code(code: str, code_verifier: str) -> dict:
    if not google_configured():
        raise HTTPException(status_code=503, detail="Google sign-in is not configured.")
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                TOKEN_ENDPOINT,
                data={
                    "code": code,
                    "client_id": GOOGLE_OIDC_CLIENT_ID,
                    "client_secret": GOOGLE_OIDC_CLIENT_SECRET,
                    "redirect_uri": GOOGLE_OIDC_REDIRECT_URI,
                    "grant_type": "authorization_code",
                    "code_verifier": code_verifier,
                },
            )
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as error:
        raise HTTPException(status_code=401, detail="Google sign-in could not be verified.") from error
    if not payload.get("id_token"):
        raise HTTPException(status_code=401, detail="Google sign-in did not return an identity token.")
    return payload


def verify_google_identity(raw_id_token: str, expected_nonce: str) -> dict[str, str | bool]:
    try:
        claims = google_id_token.verify_oauth2_token(
            raw_id_token,
            GoogleAuthRequest(),
            GOOGLE_OIDC_CLIENT_ID,
        )
    except Exception as error:
        raise HTTPException(status_code=401, detail="Google identity token is invalid.") from error
    if claims.get("iss") not in VALID_ISSUERS:
        raise HTTPException(status_code=401, detail="Google identity issuer is invalid.")
    if claims.get("aud") != GOOGLE_OIDC_CLIENT_ID:
        raise HTTPException(status_code=401, detail="Google identity audience is invalid.")
    if not claims.get("sub"):
        raise HTTPException(status_code=401, detail="Google identity is missing a subject.")
    if claims.get("nonce") != expected_nonce:
        raise HTTPException(status_code=401, detail="Google identity nonce is invalid.")
    if claims.get("email_verified") not in {True, "true"}:
        raise HTTPException(status_code=401, detail="A verified Google email is required.")
    email = str(claims.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=401, detail="Google identity is missing an email address.")
    return {
        "sub": str(claims["sub"]),
        "email": email,
        "email_verified": True,
        "name": str(claims.get("name") or email.split("@", 1)[0]),
    }
