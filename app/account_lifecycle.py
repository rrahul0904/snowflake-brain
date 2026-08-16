from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote, urlencode

import httpx

from .config import APP_BASE_URL, DATABASE_BACKEND
from .database import connect
from .observability import log_event, record_background_failure


SCHEMA_VERSION = "20260815_040_account_lifecycle_v1"
PASSWORD_N = 2**14
PASSWORD_R = 8
PASSWORD_P = 1
# Keep lifecycle credential writes byte-for-byte compatible with app.auth.
PASSWORD_DKLEN = 32
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
ACTIVE_SUBSCRIPTION_STATUSES = {"active", "trialing", "past_due", "unpaid", "incomplete"}

EMAIL_DELIVERY_MODE = os.getenv("ACCOUNT_EMAIL_DELIVERY_MODE", "outbox").strip().lower() or "outbox"
EMAIL_WEBHOOK_URL = os.getenv("ACCOUNT_EMAIL_WEBHOOK_URL", "").strip()
EMAIL_WEBHOOK_TOKEN = os.getenv("ACCOUNT_EMAIL_WEBHOOK_TOKEN", "").strip()
EMAIL_ACTION_BASE_URL = os.getenv("ACCOUNT_EMAIL_ACTION_BASE_URL", APP_BASE_URL).rstrip("/")
EMAIL_VERIFY_HOURS = max(1, int(os.getenv("ACCOUNT_EMAIL_VERIFY_HOURS", "24")))
PASSWORD_RESET_MINUTES = max(5, int(os.getenv("ACCOUNT_PASSWORD_RESET_MINUTES", "30")))
CHANGE_EMAIL_HOURS = max(1, int(os.getenv("ACCOUNT_CHANGE_EMAIL_HOURS", "2")))


class AccountLifecycleError(ValueError):
    pass


class AccountDeletionBlocked(AccountLifecycleError):
    def __init__(self, message: str, *, code: str = "active_subscription") -> None:
        super().__init__(message)
        self.code = code


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_email(email: str) -> str:
    normalized = str(email or "").strip().lower()
    if not EMAIL_RE.fullmatch(normalized) or len(normalized) > 320:
        raise AccountLifecycleError("Enter a valid email address.")
    return normalized


def _hash_password(password: str, salt_hex: str) -> str:
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=bytes.fromhex(salt_hex),
        n=PASSWORD_N,
        r=PASSWORD_R,
        p=PASSWORD_P,
        dklen=PASSWORD_DKLEN,
    )
    return digest.hex()


def _validate_new_password(password: str) -> None:
    if len(password or "") < 8:
        raise AccountLifecycleError("Password must be at least 8 characters.")
    if len(password) > 512:
        raise AccountLifecycleError("Password is too long.")


def _verify_current_password(row: Any, password: str) -> bool:
    if not row or not int(row["password_login_enabled"] or 0):
        return False
    expected = _hash_password(password or "", str(row["password_salt"]))
    return hmac.compare_digest(expected, str(row["password_hash"]))


def _action_token_hash(token: str) -> str:
    return hashlib.sha256(str(token).encode("utf-8")).hexdigest()


def _table_columns(conn: Any, table: str) -> set[str]:
    if DATABASE_BACKEND == "postgresql":
        rows = conn.execute(
            "SELECT column_name AS name FROM information_schema.columns WHERE table_schema=current_schema() AND table_name=?",
            (table,),
        ).fetchall()
    else:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {str(row["name"]) for row in rows}


def ensure_account_lifecycle_schema() -> None:
    with connect() as conn:
        existing = conn.execute(
            "SELECT 1 FROM schema_migrations WHERE version=?",
            (SCHEMA_VERSION,),
        ).fetchone()
        if existing:
            return
        if DATABASE_BACKEND == "postgresql":
            raise RuntimeError("PostgreSQL account lifecycle migration was not applied")

        account_columns = _table_columns(conn, "candidate_accounts")
        if "email_verified" not in account_columns:
            conn.execute("ALTER TABLE candidate_accounts ADD COLUMN email_verified INTEGER NOT NULL DEFAULT 1")
        if "email_verified_at" not in account_columns:
            conn.execute("ALTER TABLE candidate_accounts ADD COLUMN email_verified_at TEXT")
        if "password_changed_at" not in account_columns:
            conn.execute("ALTER TABLE candidate_accounts ADD COLUMN password_changed_at TEXT")
        conn.execute(
            "UPDATE candidate_accounts SET email_verified_at=COALESCE(email_verified_at,created_at) WHERE email_verified=1"
        )
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS account_action_tokens (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              candidate_id INTEGER NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
              purpose TEXT NOT NULL CHECK(purpose IN ('verify_email','password_reset','change_email')),
              token_hash TEXT NOT NULL UNIQUE,
              target_value TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL DEFAULT (datetime('now')),
              expires_at TEXT NOT NULL,
              consumed_at TEXT,
              metadata_json TEXT NOT NULL DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS account_audit_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              candidate_id INTEGER NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
              action TEXT NOT NULL,
              metadata_json TEXT NOT NULL DEFAULT '{}',
              created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS development_account_outbox (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              candidate_id INTEGER NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
              recipient TEXT NOT NULL,
              purpose TEXT NOT NULL,
              action_url TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'queued',
              created_at TEXT NOT NULL DEFAULT (datetime('now')),
              delivered_at TEXT
            );
            CREATE TABLE IF NOT EXISTS account_deletion_receipts (
              receipt_id TEXT PRIMARY KEY,
              reason TEXT NOT NULL DEFAULT 'candidate_request',
              created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_account_action_tokens_candidate
              ON account_action_tokens(candidate_id,purpose,expires_at,consumed_at);
            CREATE INDEX IF NOT EXISTS idx_account_audit_candidate
              ON account_audit_events(candidate_id,created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_account_outbox_candidate
              ON development_account_outbox(candidate_id,created_at DESC);
            """
        )
        conn.execute(
            "INSERT INTO schema_migrations(version,name) VALUES (?,?)",
            (SCHEMA_VERSION, "SQLite account lifecycle and recovery"),
        )


def _audit(conn: Any, candidate_id: int, action: str, metadata: dict[str, Any] | None = None) -> None:
    safe_metadata = metadata or {}
    conn.execute(
        "INSERT INTO account_audit_events(candidate_id,action,metadata_json) VALUES (?,?,?)",
        (candidate_id, action, json.dumps(safe_metadata, separators=(",", ":"), sort_keys=True)),
    )


def _issue_action_token(candidate_id: int, purpose: str, *, target_value: str = "", ttl: timedelta) -> str:
    ensure_account_lifecycle_schema()
    token = secrets.token_urlsafe(32)
    token_hash = _action_token_hash(token)
    now = _utc_now()
    expires = now + ttl
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            "UPDATE account_action_tokens SET consumed_at=datetime('now') WHERE candidate_id=? AND purpose=? AND consumed_at IS NULL",
            (candidate_id, purpose),
        )
        conn.execute(
            "INSERT INTO account_action_tokens(candidate_id,purpose,token_hash,target_value,created_at,expires_at) VALUES (?,?,?,?,?,?)",
            (candidate_id, purpose, token_hash, target_value, _iso(now), _iso(expires)),
        )
        _audit(conn, candidate_id, f"{purpose}_requested")
    return token


def _action_url(purpose: str, token: str) -> str:
    query = urlencode({"purpose": purpose, "token": token})
    return f"{EMAIL_ACTION_BASE_URL}/#/account-action?{query}"


def _deliver_action(candidate_id: int, recipient: str, purpose: str, token: str) -> str:
    action_url = _action_url(purpose, token)
    if EMAIL_DELIVERY_MODE == "outbox":
        with connect() as conn:
            conn.execute(
                "INSERT INTO development_account_outbox(candidate_id,recipient,purpose,action_url,status) VALUES (?,?,?,?,'queued')",
                (candidate_id, recipient, purpose, action_url),
            )
        return "queued"
    if EMAIL_DELIVERY_MODE == "disabled":
        return "disabled"
    if EMAIL_DELIVERY_MODE != "webhook" or not EMAIL_WEBHOOK_URL:
        record_background_failure("account_email_delivery", "invalid_delivery_configuration")
        return "failed"
    headers = {"Content-Type": "application/json"}
    if EMAIL_WEBHOOK_TOKEN:
        headers["Authorization"] = f"Bearer {EMAIL_WEBHOOK_TOKEN}"
    try:
        response = httpx.post(
            EMAIL_WEBHOOK_URL,
            json={"recipient": recipient, "purpose": purpose, "action_url": action_url},
            headers=headers,
            timeout=5.0,
        )
        response.raise_for_status()
    except Exception as exc:
        record_background_failure("account_email_delivery", exc)
        return "failed"
    return "sent"


def mark_registration_unverified(candidate_id: int) -> dict[str, Any]:
    ensure_account_lifecycle_schema()
    with connect() as conn:
        row = conn.execute("SELECT id,email FROM candidate_accounts WHERE id=?", (candidate_id,)).fetchone()
        if not row:
            raise AccountLifecycleError("Candidate account not found.")
        conn.execute(
            "UPDATE candidate_accounts SET email_verified=0,email_verified_at=NULL,updated_at=datetime('now') WHERE id=?",
            (candidate_id,),
        )
        _audit(conn, candidate_id, "registration_email_unverified")
        email = str(row["email"])
    token = _issue_action_token(candidate_id, "verify_email", ttl=timedelta(hours=EMAIL_VERIFY_HOURS))
    delivery = _deliver_action(candidate_id, email, "verify_email", token)
    return {"email_verified": False, "verification_delivery": delivery}


def resend_email_verification(candidate_id: int) -> dict[str, Any]:
    ensure_account_lifecycle_schema()
    with connect() as conn:
        row = conn.execute("SELECT email,email_verified FROM candidate_accounts WHERE id=?", (candidate_id,)).fetchone()
    if not row:
        raise AccountLifecycleError("Candidate account not found.")
    if int(row["email_verified"] or 0):
        return {"status": "already_verified"}
    token = _issue_action_token(candidate_id, "verify_email", ttl=timedelta(hours=EMAIL_VERIFY_HOURS))
    delivery = _deliver_action(candidate_id, str(row["email"]), "verify_email", token)
    return {"status": "verification_sent", "delivery": delivery}


def confirm_email_verification(token: str) -> dict[str, Any]:
    ensure_account_lifecycle_schema()
    token_hash = _action_token_hash(token)
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT id,candidate_id FROM account_action_tokens WHERE token_hash=? AND purpose='verify_email' AND consumed_at IS NULL AND datetime(expires_at)>datetime('now')",
            (token_hash,),
        ).fetchone()
        if not row:
            raise AccountLifecycleError("This verification link is invalid or has expired.")
        candidate_id = int(row["candidate_id"])
        conn.execute("UPDATE account_action_tokens SET consumed_at=datetime('now') WHERE id=?", (row["id"],))
        conn.execute(
            "UPDATE candidate_accounts SET email_verified=1,email_verified_at=datetime('now'),updated_at=datetime('now') WHERE id=?",
            (candidate_id,),
        )
        _audit(conn, candidate_id, "email_verified")
    return {"verified": True}


def request_password_reset(email: str) -> dict[str, Any]:
    ensure_account_lifecycle_schema()
    try:
        normalized = _normalize_email(email)
    except AccountLifecycleError:
        return {"accepted": True}
    with connect() as conn:
        row = conn.execute("SELECT id,email FROM candidate_accounts WHERE lower(email)=lower(?) AND status='active'", (normalized,)).fetchone()
    if row:
        candidate_id = int(row["id"])
        token = _issue_action_token(
            candidate_id,
            "password_reset",
            ttl=timedelta(minutes=PASSWORD_RESET_MINUTES),
        )
        _deliver_action(candidate_id, str(row["email"]), "password_reset", token)
    return {"accepted": True}


def confirm_password_reset(token: str, new_password: str) -> dict[str, Any]:
    ensure_account_lifecycle_schema()
    _validate_new_password(new_password)
    token_hash = _action_token_hash(token)
    salt = secrets.token_hex(16)
    password_hash = _hash_password(new_password, salt)
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT id,candidate_id FROM account_action_tokens WHERE token_hash=? AND purpose='password_reset' AND consumed_at IS NULL AND datetime(expires_at)>datetime('now')",
            (token_hash,),
        ).fetchone()
        if not row:
            raise AccountLifecycleError("This password reset link is invalid or has expired.")
        candidate_id = int(row["candidate_id"])
        conn.execute("UPDATE account_action_tokens SET consumed_at=datetime('now') WHERE id=?", (row["id"],))
        conn.execute(
            "UPDATE candidate_accounts SET password_hash=?,password_salt=?,password_algorithm='scrypt',password_login_enabled=1,password_changed_at=datetime('now'),updated_at=datetime('now') WHERE id=?",
            (password_hash, salt, candidate_id),
        )
        conn.execute(
            "UPDATE candidate_sessions SET revoked_at=COALESCE(revoked_at,datetime('now')) WHERE candidate_id=?",
            (candidate_id,),
        )
        _audit(conn, candidate_id, "password_reset_completed")
    return {"password_reset": True, "sessions_revoked": True}


def change_password(candidate_id: int, current_password: str | None, new_password: str) -> dict[str, Any]:
    ensure_account_lifecycle_schema()
    _validate_new_password(new_password)
    with connect() as conn:
        row = conn.execute(
            "SELECT password_hash,password_salt,password_login_enabled,email_verified FROM candidate_accounts WHERE id=?",
            (candidate_id,),
        ).fetchone()
    if not row:
        raise AccountLifecycleError("Candidate account not found.")
    if int(row["password_login_enabled"] or 0):
        if not _verify_current_password(row, current_password or ""):
            raise AccountLifecycleError("Current password is incorrect.")
    elif not int(row["email_verified"] or 0):
        raise AccountLifecycleError("Verify your email before adding a password.")

    salt = secrets.token_hex(16)
    password_hash = _hash_password(new_password, salt)
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            "UPDATE candidate_accounts SET password_hash=?,password_salt=?,password_algorithm='scrypt',password_login_enabled=1,password_changed_at=datetime('now'),updated_at=datetime('now') WHERE id=?",
            (password_hash, salt, candidate_id),
        )
        conn.execute(
            "UPDATE candidate_sessions SET revoked_at=COALESCE(revoked_at,datetime('now')) WHERE candidate_id=?",
            (candidate_id,),
        )
        _audit(conn, candidate_id, "password_changed")
    return {"password_changed": True, "sessions_revoked": True}


def request_email_change(candidate_id: int, new_email: str) -> dict[str, Any]:
    ensure_account_lifecycle_schema()
    normalized = _normalize_email(new_email)
    with connect() as conn:
        existing = conn.execute("SELECT id FROM candidate_accounts WHERE lower(email)=lower(?) AND id<>?", (normalized, candidate_id)).fetchone()
        current = conn.execute("SELECT email FROM candidate_accounts WHERE id=?", (candidate_id,)).fetchone()
    if not current:
        raise AccountLifecycleError("Candidate account not found.")
    if existing:
        raise AccountLifecycleError("That email address is already in use.")
    if str(current["email"]).lower() == normalized:
        raise AccountLifecycleError("That is already your account email.")
    token = _issue_action_token(
        candidate_id,
        "change_email",
        target_value=normalized,
        ttl=timedelta(hours=CHANGE_EMAIL_HOURS),
    )
    delivery = _deliver_action(candidate_id, normalized, "change_email", token)
    return {"status": "confirmation_sent", "delivery": delivery}


def confirm_email_change(token: str) -> dict[str, Any]:
    ensure_account_lifecycle_schema()
    token_hash = _action_token_hash(token)
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT id,candidate_id,target_value FROM account_action_tokens WHERE token_hash=? AND purpose='change_email' AND consumed_at IS NULL AND datetime(expires_at)>datetime('now')",
            (token_hash,),
        ).fetchone()
        if not row:
            raise AccountLifecycleError("This email-change link is invalid or has expired.")
        candidate_id = int(row["candidate_id"])
        target = _normalize_email(str(row["target_value"]))
        existing = conn.execute("SELECT id FROM candidate_accounts WHERE lower(email)=lower(?) AND id<>?", (target, candidate_id)).fetchone()
        if existing:
            raise AccountLifecycleError("That email address is already in use.")
        conn.execute("UPDATE account_action_tokens SET consumed_at=datetime('now') WHERE id=?", (row["id"],))
        conn.execute(
            "UPDATE candidate_accounts SET email=?,email_verified=1,email_verified_at=datetime('now'),updated_at=datetime('now') WHERE id=?",
            (target, candidate_id),
        )
        conn.execute(
            "UPDATE candidate_sessions SET revoked_at=COALESCE(revoked_at,datetime('now')) WHERE candidate_id=?",
            (candidate_id,),
        )
        _audit(conn, candidate_id, "email_changed")
    return {"email_changed": True, "sessions_revoked": True}


def list_identities(candidate_id: int) -> list[dict[str, Any]]:
    ensure_account_lifecycle_schema()
    with connect() as conn:
        rows = conn.execute(
            "SELECT id,provider,provider_email,provider_email_verified,created_at,last_login_at FROM candidate_identities WHERE candidate_id=? ORDER BY id",
            (candidate_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def unlink_identity(candidate_id: int, identity_id: int) -> dict[str, Any]:
    ensure_account_lifecycle_schema()
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        account = conn.execute("SELECT password_login_enabled FROM candidate_accounts WHERE id=?", (candidate_id,)).fetchone()
        identity = conn.execute(
            "SELECT id,provider FROM candidate_identities WHERE id=? AND candidate_id=?",
            (identity_id, candidate_id),
        ).fetchone()
        if not account or not identity:
            raise AccountLifecycleError("Linked identity not found.")
        count = int(conn.execute("SELECT COUNT(*) AS n FROM candidate_identities WHERE candidate_id=?", (candidate_id,)).fetchone()["n"])
        if not int(account["password_login_enabled"] or 0) and count <= 1:
            raise AccountLifecycleError("Add a password before unlinking your only sign-in method.")
        conn.execute("DELETE FROM candidate_identities WHERE id=? AND candidate_id=?", (identity_id, candidate_id))
        _audit(conn, candidate_id, "identity_unlinked", {"provider": str(identity["provider"])})
    return {"unlinked": True, "provider": str(identity["provider"])}


def _active_subscription(conn: Any, candidate_id: int) -> dict[str, Any] | None:
    rows = conn.execute(
        "SELECT internal_plan,status,cancel_at_period_end,current_period_end FROM billing_subscriptions WHERE candidate_id=? ORDER BY id DESC",
        (candidate_id,),
    ).fetchall()
    for row in rows:
        if str(row["status"] or "").lower() in ACTIVE_SUBSCRIPTION_STATUSES:
            return dict(row)
    return None


def account_status(candidate_id: int) -> dict[str, Any]:
    ensure_account_lifecycle_schema()
    with connect() as conn:
        account = conn.execute(
            "SELECT id,email,display_name,plan,status,password_login_enabled,email_verified,email_verified_at,password_changed_at,created_at,last_login_at FROM candidate_accounts WHERE id=?",
            (candidate_id,),
        ).fetchone()
        if not account:
            raise AccountLifecycleError("Candidate account not found.")
        active_sessions = int(
            conn.execute(
                "SELECT COUNT(*) AS n FROM candidate_sessions WHERE candidate_id=? AND revoked_at IS NULL AND datetime(expires_at)>datetime('now')",
                (candidate_id,),
            ).fetchone()["n"]
        )
        subscription = _active_subscription(conn, candidate_id)
        audit = conn.execute(
            "SELECT action,metadata_json,created_at FROM account_audit_events WHERE candidate_id=? ORDER BY id DESC LIMIT 20",
            (candidate_id,),
        ).fetchall()
    return {
        **dict(account),
        "email_verified": bool(account["email_verified"]),
        "password_login_enabled": bool(account["password_login_enabled"]),
        "active_sessions": active_sessions,
        "identities": list_identities(candidate_id),
        "can_delete": subscription is None,
        "deletion_blocker": subscription,
        "audit": [
            {
                "action": str(row["action"]),
                "metadata": json.loads(row["metadata_json"] or "{}"),
                "created_at": row["created_at"],
            }
            for row in audit
        ],
    }


def account_export_payload(candidate_id: int) -> dict[str, Any]:
    ensure_account_lifecycle_schema()
    with connect() as conn:
        account = conn.execute(
            "SELECT id,email,display_name,plan,status,password_login_enabled,email_verified,email_verified_at,password_changed_at,created_at,last_login_at FROM candidate_accounts WHERE id=?",
            (candidate_id,),
        ).fetchone()
        if not account:
            raise AccountLifecycleError("Candidate account not found.")

        def rows(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
            return [dict(row) for row in conn.execute(sql, params).fetchall()]

        payload = {
            "generated_at": _iso(_utc_now()),
            "profile": {**dict(account), "email_verified": bool(account["email_verified"]), "password_login_enabled": bool(account["password_login_enabled"])},
            "memberships": rows(
                "SELECT tier,plan_code,status,starts_at,expires_at,source,entitlement_version,created_at,updated_at FROM candidate_memberships WHERE candidate_id=? ORDER BY id",
                (candidate_id,),
            ),
            "exam_history": rows(
                "SELECT id,track_id,mode,started_at,finished_at,score,total_questions,status,duration_seconds,submitted_reason,raw_correct,raw_accuracy,weighted_accuracy,scaled_score,elapsed_seconds FROM exam_sessions WHERE candidate_id=? ORDER BY id",
                (candidate_id,),
            ),
            "practice_attempts": rows(
                "SELECT id,question_id,selected,correct,mode,response_time_ms,confidence,attempted_at FROM question_attempts WHERE candidate_id=? ORDER BY id",
                (candidate_id,),
            ),
            "task_progress": rows(
                "SELECT track_id,skill_id,completed,completed_at,updated_at FROM candidate_task_progress WHERE candidate_id=? ORDER BY track_id,skill_id",
                (candidate_id,),
            ),
            "srs_state": rows(
                "SELECT question_id,track_id,domain_id,skill_id,repetitions,interval_days,ease_factor,lapses,due_at,last_reviewed_at,last_correct,last_confidence,updated_at FROM candidate_srs_state WHERE candidate_id=? ORDER BY due_at,question_id",
                (candidate_id,),
            ),
            "mistake_notebook": rows(
                "SELECT question_id,track_id,domain_id,skill_id,miss_count,status,root_cause,note,first_missed_at,last_missed_at,last_reviewed_at,mastered_at,updated_at FROM candidate_mistake_notebook WHERE candidate_id=? ORDER BY last_missed_at DESC",
                (candidate_id,),
            ),
            "study_preferences": rows(
                "SELECT track_id,exam_date,daily_minutes,days_per_week,updated_at FROM candidate_study_preferences WHERE candidate_id=? ORDER BY track_id",
                (candidate_id,),
            ),
            "bookmarks": rows(
                "SELECT question_id,created_at FROM candidate_bookmarks WHERE candidate_id=? ORDER BY id",
                (candidate_id,),
            ),
            "notes": rows(
                "SELECT question_id,body,created_at FROM candidate_notes WHERE candidate_id=? ORDER BY id",
                (candidate_id,),
            ),
            "identities": rows(
                "SELECT provider,provider_email,provider_email_verified,created_at,last_login_at FROM candidate_identities WHERE candidate_id=? ORDER BY id",
                (candidate_id,),
            ),
            "sessions": rows(
                "SELECT expires_at,revoked_at,created_at,last_seen_at FROM candidate_sessions WHERE candidate_id=? ORDER BY id",
                (candidate_id,),
            ),
            "account_audit": rows(
                "SELECT action,metadata_json,created_at FROM account_audit_events WHERE candidate_id=? ORDER BY id",
                (candidate_id,),
            ),
            "billing_summary": rows(
                "SELECT internal_plan,status,current_period_start,current_period_end,cancel_at_period_end,created_at,updated_at FROM billing_subscriptions WHERE candidate_id=? ORDER BY id",
                (candidate_id,),
            )
            + rows(
                "SELECT product_type,status,purchased_at,expires_at FROM billing_purchases WHERE candidate_id=? ORDER BY id",
                (candidate_id,),
            ),
        }
        _audit(conn, candidate_id, "data_export_generated")
    log_event("account_data_export_generated")
    return payload


def delete_account(candidate_id: int, *, confirmation: str, password: str | None = None) -> dict[str, Any]:
    ensure_account_lifecycle_schema()
    if str(confirmation or "").strip().upper() != "DELETE":
        raise AccountLifecycleError("Type DELETE to confirm account deletion.")
    with connect() as conn:
        account = conn.execute(
            "SELECT password_hash,password_salt,password_login_enabled FROM candidate_accounts WHERE id=?",
            (candidate_id,),
        ).fetchone()
        if not account:
            raise AccountLifecycleError("Candidate account not found.")
        if int(account["password_login_enabled"] or 0) and not _verify_current_password(account, password or ""):
            raise AccountLifecycleError("Password confirmation is incorrect.")
        subscription = _active_subscription(conn, candidate_id)
        if subscription:
            raise AccountDeletionBlocked(
                "Account deletion is blocked while a recurring paid subscription is active. Cancel the subscription and wait for the paid period to end before deleting the account."
            )

    receipt_id = uuid.uuid4().hex
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("DELETE FROM question_attempts WHERE candidate_id=?", (candidate_id,))
        conn.execute("DELETE FROM exam_sessions WHERE candidate_id=?", (candidate_id,))
        conn.execute("DELETE FROM learning_events WHERE candidate_id=?", (candidate_id,))
        conn.execute("DELETE FROM feedback_submissions WHERE candidate_id=?", (candidate_id,))
        conn.execute(
            "INSERT INTO account_deletion_receipts(receipt_id,reason) VALUES (?,'candidate_request')",
            (receipt_id,),
        )
        deleted = conn.execute("DELETE FROM candidate_accounts WHERE id=?", (candidate_id,)).rowcount
        if int(deleted or 0) != 1:
            raise AccountLifecycleError("Candidate account could not be deleted.")
    log_event("account_deleted", receipt_id=receipt_id)
    return {"deleted": True, "receipt_id": receipt_id}


def development_outbox(candidate_id: int, purpose: str | None = None) -> list[dict[str, Any]]:
    """Backend/test helper only; no public API exposes action tokens."""
    ensure_account_lifecycle_schema()
    with connect() as conn:
        if purpose:
            rows = conn.execute(
                "SELECT id,recipient,purpose,action_url,status,created_at,delivered_at FROM development_account_outbox WHERE candidate_id=? AND purpose=? ORDER BY id DESC",
                (candidate_id, purpose),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id,recipient,purpose,action_url,status,created_at,delivered_at FROM development_account_outbox WHERE candidate_id=? ORDER BY id DESC",
                (candidate_id,),
            ).fetchall()
    return [dict(row) for row in rows]


def extract_token_from_action_url(action_url: str) -> str:
    """Test/admin helper for the private development outbox."""
    marker = "token="
    if marker not in action_url:
        raise AccountLifecycleError("Action URL does not contain a token.")
    return quote(action_url.split(marker, 1)[1].split("&", 1)[0], safe="%") and action_url.split(marker, 1)[1].split("&", 1)[0]
