from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException, Request, Response

from .config import AUTH_COOKIE_SECURE
from .database import connect
from .entitlements import entitlement_usage, plan_details
from .identity_billing_schema import ensure_identity_billing_schema


COOKIE_NAME = "snowflake_candidate_session"
GOOGLE_LINK_COOKIE = "snowflake_google_link"
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


def _identity_methods(candidate_id: int, password_login_enabled: bool = True) -> list[str]:
    ensure_identity_billing_schema()
    methods = ["email"] if password_login_enabled else []
    with connect() as conn:
        rows = conn.execute(
            "SELECT DISTINCT provider FROM candidate_identities WHERE candidate_id=? ORDER BY provider",
            (candidate_id,),
        ).fetchall()
    methods.extend(str(row["provider"]) for row in rows if row["provider"] not in methods)
    return methods


def public_candidate(row: dict[str, Any]) -> dict[str, Any]:
    candidate_id = int(row["id"])
    methods = row.get("sign_in_methods") or _identity_methods(
        candidate_id, bool(row.get("password_login_enabled", 1))
    )
    return {
        "id": candidate_id,
        "email": row["email"],
        "display_name": row["display_name"],
        "sign_in_methods": methods,
    }


def membership_for_candidate(candidate_id: int) -> dict[str, Any]:
    ensure_identity_billing_schema()
    with connect() as conn:
        conn.execute(
            "UPDATE candidate_memberships SET status = 'expired', updated_at = datetime('now') "
            "WHERE candidate_id = ? AND status = 'active' AND expires_at IS NOT NULL "
            "AND datetime(expires_at) <= datetime('now')",
            (candidate_id,),
        )
        row = conn.execute(
            """
            SELECT tier, status, plan_code, starts_at, expires_at, source, entitlement_version
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
        membership = {
            "tier": "free",
            "status": "active",
            "plan_code": "free",
            "starts_at": None,
            "expires_at": None,
            "source": "fallback",
            "entitlement_version": 0,
        }
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
    ensure_identity_billing_schema()
    normalized = normalize_email(email)
    salt = secrets.token_hex(16)
    digest = password_digest(password, salt)
    try:
        with connect() as conn:
            cursor = conn.execute(
                "INSERT INTO candidate_accounts(email, display_name, password_hash, password_salt, password_algorithm, password_login_enabled, plan, status) "
                "VALUES (?, ?, ?, ?, 'scrypt', 1, 'free', 'active')",
                (normalized, display_name.strip(), digest, salt),
            )
            conn.execute(
                "INSERT INTO candidate_memberships(candidate_id, tier, plan_code, status, source, entitlement_version) VALUES (?, 'free', 'free', 'active', 'registration', 1)",
                (cursor.lastrowid,),
            )
            row = conn.execute("SELECT * FROM candidate_accounts WHERE id = ?", (cursor.lastrowid,)).fetchone()
    except Exception as error:
        if "UNIQUE constraint failed" in str(error):
            raise HTTPException(status_code=409, detail="An account already exists for this email") from error
        raise
    return candidate_context(dict(row))


def create_google_candidate(display_name: str, email: str, provider_subject: str) -> dict[str, Any]:
    """Create a Google-only candidate without creating a usable password credential."""
    ensure_identity_billing_schema()
    normalized = normalize_email(email)
    random_secret = secrets.token_urlsafe(48)
    salt = secrets.token_hex(16)
    digest = password_digest(random_secret, salt)
    try:
        with connect() as conn:
            cursor = conn.execute(
                "INSERT INTO candidate_accounts(email, display_name, password_hash, password_salt, password_algorithm, password_login_enabled, plan, status) "
                "VALUES (?, ?, ?, ?, 'scrypt', 0, 'free', 'active')",
                (normalized, (display_name or normalized.split('@')[0]).strip(), digest, salt),
            )
            candidate_id = int(cursor.lastrowid)
            conn.execute(
                "INSERT INTO candidate_memberships(candidate_id, tier, plan_code, status, source, entitlement_version) VALUES (?, 'free', 'free', 'active', 'google_registration', 1)",
                (candidate_id,),
            )
            conn.execute(
                "INSERT INTO candidate_identities(candidate_id,provider,provider_subject,provider_email,provider_email_verified) "
                "VALUES (?,'google',?,?,1)",
                (candidate_id, provider_subject, normalized),
            )
            row = conn.execute("SELECT * FROM candidate_accounts WHERE id=?", (candidate_id,)).fetchone()
    except Exception as error:
        if "UNIQUE constraint failed" in str(error):
            raise HTTPException(status_code=409, detail="An account already exists for this email") from error
        raise
    return candidate_context(dict(row))


def authenticate_candidate(email: str, password: str) -> dict[str, Any]:
    ensure_identity_billing_schema()
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM candidate_accounts WHERE email = ? COLLATE NOCASE",
            (normalize_email(email),),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    value = dict(row)
    if not bool(value.get("password_login_enabled", 1)):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    algorithm = value.get("password_algorithm") or "pbkdf2_sha256"
    actual = password_digest(password, value["password_salt"], algorithm)
    if not hmac.compare_digest(actual, value["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    with connect() as conn:
        conn.execute("UPDATE candidate_accounts SET last_login_at = datetime('now') WHERE id = ?", (value["id"],))
    return candidate_context(value)


def candidate_by_email(email: str) -> dict[str, Any] | None:
    ensure_identity_billing_schema()
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM candidate_accounts WHERE email=? COLLATE NOCASE AND status='active'",
            (normalize_email(email),),
        ).fetchone()
    return dict(row) if row else None


def candidate_by_google_subject(subject: str) -> dict[str, Any] | None:
    ensure_identity_billing_schema()
    with connect() as conn:
        row = conn.execute(
            "SELECT a.* FROM candidate_identities i JOIN candidate_accounts a ON a.id=i.candidate_id "
            "WHERE i.provider='google' AND i.provider_subject=? AND a.status='active'",
            (subject,),
        ).fetchone()
        if row:
            conn.execute(
                "UPDATE candidate_identities SET last_login_at=datetime('now') WHERE provider='google' AND provider_subject=?",
                (subject,),
            )
            conn.execute("UPDATE candidate_accounts SET last_login_at=datetime('now') WHERE id=?", (row["id"],))
    return candidate_context(dict(row)) if row else None


def link_google_identity(candidate_id: int, subject: str, email: str, email_verified: bool = True) -> dict[str, Any]:
    ensure_identity_billing_schema()
    with connect() as conn:
        existing = conn.execute(
            "SELECT candidate_id FROM candidate_identities WHERE provider='google' AND provider_subject=?",
            (subject,),
        ).fetchone()
        if existing and int(existing["candidate_id"]) != candidate_id:
            raise HTTPException(status_code=409, detail="This Google identity is already linked to another account.")
        conn.execute(
            "INSERT INTO candidate_identities(candidate_id,provider,provider_subject,provider_email,provider_email_verified,last_login_at) "
            "VALUES (?,'google',?,?,?,datetime('now')) "
            "ON CONFLICT(provider,provider_subject) DO UPDATE SET provider_email=excluded.provider_email, "
            "provider_email_verified=excluded.provider_email_verified,last_login_at=datetime('now')",
            (candidate_id, subject, normalize_email(email), 1 if email_verified else 0),
        )
        row = conn.execute("SELECT * FROM candidate_accounts WHERE id=?", (candidate_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Candidate account not found")
    return candidate_context(dict(row))


def create_pending_google_link(candidate_id: int, subject: str, email: str) -> str:
    ensure_identity_billing_schema()
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expires = datetime.now(timezone.utc) + timedelta(minutes=10)
    with connect() as conn:
        conn.execute("DELETE FROM pending_identity_links WHERE datetime(expires_at) <= datetime('now') OR consumed_at IS NOT NULL")
        conn.execute(
            "INSERT OR REPLACE INTO pending_identity_links(token_hash,candidate_id,provider,provider_subject,provider_email,provider_email_verified,expires_at) "
            "VALUES (?,?,'google',?,?,1,?)",
            (token_hash, candidate_id, subject, normalize_email(email), expires.isoformat()),
        )
    return token


def pending_google_link(token: str | None) -> dict[str, Any] | None:
    if not token:
        return None
    ensure_identity_billing_schema()
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with connect() as conn:
        row = conn.execute(
            "SELECT p.*, a.email, a.display_name, a.password_login_enabled FROM pending_identity_links p "
            "JOIN candidate_accounts a ON a.id=p.candidate_id "
            "WHERE p.token_hash=? AND p.consumed_at IS NULL AND datetime(p.expires_at)>datetime('now')",
            (token_hash,),
        ).fetchone()
    return dict(row) if row else None


def consume_pending_google_link(token: str, password: str) -> dict[str, Any]:
    pending = pending_google_link(token)
    if not pending or not bool(pending.get("password_login_enabled", 1)):
        raise HTTPException(status_code=401, detail="Google account linking request is no longer valid.")
    candidate = authenticate_candidate(pending["email"], password)
    if int(candidate["id"]) != int(pending["candidate_id"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    linked = link_google_identity(
        int(pending["candidate_id"]), pending["provider_subject"], pending["provider_email"], True
    )
    with connect() as conn:
        conn.execute(
            "UPDATE pending_identity_links SET consumed_at=datetime('now') WHERE token_hash=?",
            (hashlib.sha256(token.encode()).hexdigest(),),
        )
    return linked


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


def list_candidate_sessions(candidate_id: int, current_token: str | None) -> list[dict[str, Any]]:
    current_hash = hashlib.sha256(current_token.encode()).hexdigest() if current_token else ""
    with connect() as conn:
        rows = conn.execute(
            "SELECT id,token_hash,created_at,last_seen_at,expires_at FROM candidate_sessions "
            "WHERE candidate_id=? AND revoked_at IS NULL AND datetime(expires_at)>datetime('now') ORDER BY last_seen_at DESC",
            (candidate_id,),
        ).fetchall()
    return [
        {
            "id": int(row["id"]),
            "created_at": row["created_at"],
            "last_seen_at": row["last_seen_at"],
            "expires_at": row["expires_at"],
            "current": hmac.compare_digest(row["token_hash"], current_hash) if current_hash else False,
        }
        for row in rows
    ]


def revoke_candidate_session(candidate_id: int, session_id: int) -> bool:
    with connect() as conn:
        cursor = conn.execute(
            "UPDATE candidate_sessions SET revoked_at=datetime('now') WHERE id=? AND candidate_id=? AND revoked_at IS NULL",
            (session_id, candidate_id),
        )
    return cursor.rowcount > 0


def revoke_all_candidate_sessions(candidate_id: int) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE candidate_sessions SET revoked_at=datetime('now') WHERE candidate_id=? AND revoked_at IS NULL",
            (candidate_id,),
        )


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
