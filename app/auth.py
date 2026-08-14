from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException, Request

from .database import connect
from .entitlements import entitlement_usage, plan_details


COOKIE_NAME = "snowflake_candidate_session"
SESSION_DAYS = 30
PASSWORD_ITERATIONS = 260_000
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1


def normalize_email(value: str) -> str:
    return value.strip().lower()


def password_digest(password: str, salt_hex: str, algorithm: str = "scrypt") -> str:
    if algorithm == "pbkdf2_sha256":
        return hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), PASSWORD_ITERATIONS
        ).hex()
    return hashlib.scrypt(
        password.encode("utf-8"),
        salt=bytes.fromhex(salt_hex),
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=32,
    ).hex()


def public_candidate(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "email": row["email"],
        "display_name": row["display_name"],
    }


def membership_for_candidate(candidate_id: int) -> dict[str, Any]:
    with connect() as conn:
        conn.execute(
            "UPDATE candidate_memberships SET status = 'expired', updated_at = datetime('now') "
            "WHERE candidate_id = ? AND status = 'active' AND expires_at IS NOT NULL "
            "AND datetime(expires_at) <= datetime('now')",
            (candidate_id,),
        )
        row = conn.execute(
            """
            SELECT tier, status, plan_code, starts_at, expires_at, source
            FROM candidate_memberships
            WHERE candidate_id = ? AND status = 'active'
              AND datetime(starts_at) <= datetime('now')
              AND (expires_at IS NULL OR datetime(expires_at) > datetime('now'))
            ORDER BY CASE tier WHEN 'premium' THEN 0 ELSE 1 END, datetime(starts_at) DESC, id DESC
            LIMIT 1
            """,
            (candidate_id,),
        ).fetchone()
    if not row:
        membership = {"tier": "free", "status": "active", "plan_code": "free", "starts_at": None, "expires_at": None, "source": "fallback"}
    else:
        membership = dict(row)
    membership["plan"] = plan_details(membership.get("plan_code"), membership["tier"])
    membership["plan_code"] = membership["plan"]["code"]
    membership["usage"] = entitlement_usage(candidate_id, membership)
    return membership


def candidate_context(row: dict[str, Any]) -> dict[str, Any]:
    context = public_candidate(row)
    context["membership"] = membership_for_candidate(context["id"])
    context["is_premium"] = context["membership"]["tier"] == "premium" and context["membership"]["status"] == "active"
    return context


def create_candidate(display_name: str, email: str, password: str) -> dict[str, Any]:
    normalized = normalize_email(email)
    salt = secrets.token_hex(16)
    digest = password_digest(password, salt)
    try:
        with connect() as conn:
            cursor = conn.execute(
                "INSERT INTO candidate_accounts(email, display_name, password_hash, password_salt, password_algorithm, plan, status) "
                "VALUES (?, ?, ?, ?, 'scrypt', 'free', 'active')",
                (normalized, display_name.strip(), digest, salt),
            )
            conn.execute(
                "INSERT INTO candidate_memberships(candidate_id, tier, plan_code, status, source) VALUES (?, 'free', 'free', 'active', 'registration')",
                (cursor.lastrowid,),
            )
            row = conn.execute("SELECT * FROM candidate_accounts WHERE id = ?", (cursor.lastrowid,)).fetchone()
    except Exception as error:
        if "UNIQUE constraint failed" in str(error):
            raise HTTPException(status_code=409, detail="An account already exists for this email") from error
        raise
    return candidate_context(dict(row))


def authenticate_candidate(email: str, password: str) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM candidate_accounts WHERE email = ? COLLATE NOCASE",
            (normalize_email(email),),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    value = dict(row)
    algorithm = value.get("password_algorithm") or "pbkdf2_sha256"
    actual = password_digest(password, value["password_salt"], algorithm)
    if not hmac.compare_digest(actual, value["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    with connect() as conn:
        conn.execute("UPDATE candidate_accounts SET last_login_at = datetime('now') WHERE id = ?", (value["id"],))
    return candidate_context(value)


def create_session(candidate_id: int) -> str:
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expires = datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)
    with connect() as conn:
        conn.execute("DELETE FROM candidate_sessions WHERE datetime(expires_at) <= datetime('now')")
        conn.execute(
            "INSERT INTO candidate_sessions(candidate_id, token_hash, expires_at) VALUES (?, ?, ?)",
            (candidate_id, token_hash, expires.isoformat()),
        )
    return token


def delete_session(token: str | None) -> None:
    if not token:
        return
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with connect() as conn:
        conn.execute("UPDATE candidate_sessions SET revoked_at = datetime('now') WHERE token_hash = ?", (token_hash,))


def candidate_for_token(token: str | None) -> dict[str, Any] | None:
    if not token:
        return None
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with connect() as conn:
        row = conn.execute(
            "SELECT a.* FROM candidate_sessions s "
            "JOIN candidate_accounts a ON a.id = s.candidate_id "
            "WHERE s.token_hash = ? AND s.revoked_at IS NULL AND a.status = 'active' "
            "AND datetime(s.expires_at) > datetime('now')",
            (token_hash,),
        ).fetchone()
        if row:
            conn.execute(
                "UPDATE candidate_sessions SET last_seen_at = datetime('now') WHERE token_hash = ?",
                (token_hash,),
            )
    return candidate_context(dict(row)) if row else None


def optional_candidate(request: Request) -> dict[str, Any] | None:
    return candidate_for_token(request.cookies.get(COOKIE_NAME))


def require_candidate(candidate: dict[str, Any] | None = Depends(optional_candidate)) -> dict[str, Any]:
    if not candidate:
        raise HTTPException(
            status_code=401,
            detail={"code": "authentication_required", "message": "Create a free account or sign in to continue."},
        )
    return candidate


def require_premium_candidate(candidate: dict[str, Any] = Depends(require_candidate)) -> dict[str, Any]:
    if not candidate["is_premium"]:
        raise HTTPException(
            status_code=403,
            detail={"code": "premium_required", "message": "Premium membership is required for mock exams."},
        )
    return candidate


def require_owned_mock_session(session_id: int, candidate_id: int) -> None:
    with connect() as conn:
        row = conn.execute("SELECT candidate_id FROM exam_sessions WHERE id = ?", (session_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Exam session not found")
    if row["candidate_id"] != candidate_id:
        raise HTTPException(status_code=404, detail="Exam session not found")
