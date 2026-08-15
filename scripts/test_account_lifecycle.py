#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory(prefix="snowflake-account-lifecycle-")
os.environ["BRAIN_DB"] = str(Path(TEMP.name) / "account.sqlite")
os.environ["ACCOUNT_EMAIL_DELIVERY_MODE"] = "outbox"
os.environ["AUTH_COOKIE_SECURE"] = "false"
os.environ["BILLING_ENABLED"] = "false"

from fastapi.testclient import TestClient  # noqa: E402

from app.account_lifecycle import (  # noqa: E402
    AccountLifecycleError,
    account_export_payload,
    change_password,
    development_outbox,
    ensure_account_lifecycle_schema,
    unlink_identity,
)
from app.auth import create_candidate  # noqa: E402
from app.config import DATABASE_BACKEND  # noqa: E402
from app.database import connect  # noqa: E402
from app.main import app  # noqa: E402


def token_from_action_url(url: str) -> str:
    parsed = urlsplit(url)
    fragment = parsed.fragment
    query = fragment.split("?", 1)[1] if "?" in fragment else parsed.query
    token = parse_qs(query).get("token", [""])[0]
    if not token:
        raise AssertionError(f"No action token in URL: {url}")
    return token


def latest_token(candidate_id: int, purpose: str) -> str:
    rows = development_outbox(candidate_id, purpose)
    if not rows:
        raise AssertionError(f"No development outbox row for {purpose}")
    return token_from_action_url(str(rows[0]["action_url"]))


def candidate_id_for_email(email: str) -> int:
    with connect() as conn:
        row = conn.execute("SELECT id FROM candidate_accounts WHERE lower(email)=lower(?)", (email,)).fetchone()
    if not row:
        raise AssertionError(f"Candidate not found: {email}")
    return int(row["id"])


def register(client: TestClient, email: str, password: str = "LifecycleStart!234") -> tuple[int, dict]:
    response = client.post(
        "/api/auth/register",
        json={"display_name": "Lifecycle Candidate", "email": email, "password": password},
    )
    if response.status_code != 200:
        raise AssertionError(f"Registration failed: {response.status_code} {response.text}")
    payload = response.json()
    candidate_id = int(payload["id"])
    if payload.get("email_verified") is not False:
        raise AssertionError("API registration must start with an unverified email")
    if payload.get("verification_delivery") != "queued":
        raise AssertionError(f"Expected development verification queue, got {payload}")
    return candidate_id, payload


def check_verification_and_resend() -> tuple[int, str]:
    client = TestClient(app)
    candidate_id, _ = register(client, "lifecycle-primary@example.com")
    first = latest_token(candidate_id, "verify_email")

    with connect() as conn:
        token_row = conn.execute(
            "SELECT token_hash FROM account_action_tokens WHERE candidate_id=? AND purpose='verify_email' AND consumed_at IS NULL ORDER BY id DESC LIMIT 1",
            (candidate_id,),
        ).fetchone()
        if not token_row:
            raise AssertionError("Verification token hash was not persisted")
        if str(token_row["token_hash"]) == first or first in str(token_row["token_hash"]):
            raise AssertionError("Raw verification token leaked into account_action_tokens")

    resend = client.post("/api/account/email-verification/resend")
    assert resend.status_code == 200, resend.text
    second = latest_token(candidate_id, "verify_email")
    assert second != first

    stale = TestClient(app).post("/api/auth/email-verification/confirm", json={"token": first})
    assert stale.status_code == 400, stale.text
    verified = TestClient(app).post("/api/auth/email-verification/confirm", json={"token": second})
    assert verified.status_code == 200 and verified.json()["verified"] is True
    replay = TestClient(app).post("/api/auth/email-verification/confirm", json={"token": second})
    assert replay.status_code == 400

    status = client.get("/api/account/status")
    assert status.status_code == 200
    assert status.json()["email_verified"] is True
    return candidate_id, "LifecycleStart!234"


def check_password_reset(candidate_id: int, old_password: str) -> str:
    # Create another active session before reset to prove global revocation.
    other = TestClient(app)
    login_other = other.post(
        "/api/auth/login",
        json={"email": "lifecycle-primary@example.com", "password": old_password},
    )
    assert login_other.status_code == 200

    known = TestClient(app).post(
        "/api/auth/password-reset/request",
        json={"email": "lifecycle-primary@example.com"},
    )
    unknown = TestClient(app).post(
        "/api/auth/password-reset/request",
        json={"email": "definitely-unknown@example.com"},
    )
    assert known.status_code == 202 and unknown.status_code == 202
    assert known.json() == unknown.json() == {"accepted": True}

    token = latest_token(candidate_id, "password_reset")
    new_password = "LifecycleReset!567"
    confirm = TestClient(app).post(
        "/api/auth/password-reset/confirm",
        json={"token": token, "new_password": new_password},
    )
    assert confirm.status_code == 200, confirm.text
    assert confirm.json()["sessions_revoked"] is True
    replay = TestClient(app).post(
        "/api/auth/password-reset/confirm",
        json={"token": token, "new_password": "AnotherPassword!9"},
    )
    assert replay.status_code == 400

    assert other.get("/api/auth/me").status_code == 401
    old_login = TestClient(app).post(
        "/api/auth/login",
        json={"email": "lifecycle-primary@example.com", "password": old_password},
    )
    assert old_login.status_code == 401
    new_login = TestClient(app).post(
        "/api/auth/login",
        json={"email": "lifecycle-primary@example.com", "password": new_password},
    )
    assert new_login.status_code == 200
    return new_password


def check_password_and_email_change(candidate_id: int, password: str) -> tuple[str, str]:
    client = TestClient(app)
    login = client.post(
        "/api/auth/login",
        json={"email": "lifecycle-primary@example.com", "password": password},
    )
    assert login.status_code == 200

    bad = client.post(
        "/api/account/change-password",
        json={"current_password": "wrong-password", "new_password": "LifecycleChanged!890"},
    )
    assert bad.status_code == 400
    changed_password = "LifecycleChanged!890"
    good = client.post(
        "/api/account/change-password",
        json={"current_password": password, "new_password": changed_password},
    )
    assert good.status_code == 200 and good.json()["sessions_revoked"] is True
    assert client.get("/api/auth/me").status_code == 401

    client = TestClient(app)
    assert client.post(
        "/api/auth/login",
        json={"email": "lifecycle-primary@example.com", "password": changed_password},
    ).status_code == 200

    new_email = "lifecycle-renamed@example.com"
    requested = client.post("/api/account/change-email/request", json={"new_email": new_email})
    assert requested.status_code == 200, requested.text
    token = latest_token(candidate_id, "change_email")
    confirmed = TestClient(app).post("/api/auth/change-email/confirm", json={"token": token})
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["sessions_revoked"] is True
    replay = TestClient(app).post("/api/auth/change-email/confirm", json={"token": token})
    assert replay.status_code == 400

    assert client.get("/api/auth/me").status_code == 401
    old_email = TestClient(app).post(
        "/api/auth/login",
        json={"email": "lifecycle-primary@example.com", "password": changed_password},
    )
    assert old_email.status_code == 401
    renamed = TestClient(app).post(
        "/api/auth/login",
        json={"email": new_email, "password": changed_password},
    )
    assert renamed.status_code == 200
    return new_email, changed_password


def check_google_unlink_safeguard() -> None:
    candidate, _ = create_candidate("Google Only", "google-only@example.com", "TemporaryPassword!4")
    candidate_id = int(candidate["id"])
    ensure_account_lifecycle_schema()
    with connect() as conn:
        conn.execute("UPDATE candidate_accounts SET password_login_enabled=0 WHERE id=?", (candidate_id,))
        conn.execute(
            "INSERT INTO candidate_identities(candidate_id,provider,provider_subject,provider_email,provider_email_verified) VALUES (?,?,?,?,1)",
            (candidate_id, "google", "google-subject-lifecycle", "google-only@example.com"),
        )
        identity_id = int(
            conn.execute("SELECT id FROM candidate_identities WHERE candidate_id=?", (candidate_id,)).fetchone()["id"]
        )
    try:
        unlink_identity(candidate_id, identity_id)
    except AccountLifecycleError as exc:
        assert "only sign-in method" in str(exc)
    else:
        raise AssertionError("Google-only candidate was allowed to unlink the only identity")

    change_password(candidate_id, None, "GoogleFallbackPassword!5")
    result = unlink_identity(candidate_id, identity_id)
    assert result["unlinked"] is True and result["provider"] == "google"


def seed_export_and_delete_data(candidate_id: int) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO questions(
              id,track_id,test_title,question,options_json,correct_json,explanation,
              source_path,source_kind,assessment_type,tags,difficulty,multiple,question_position
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                "account-lifecycle-q1",
                "snowpro-core",
                "Account lifecycle regression",
                "Which layer owns candidate account lifecycle controls?",
                '["Candidate account service","Snowflake warehouse","Browser cache"]',
                "[0]",
                "Candidate lifecycle is owned by the certification application account service.",
                "private://account-lifecycle",
                "curated",
                "practice",
                '["account-lifecycle"]',
                "medium",
                0,
                1,
            ),
        )
        conn.execute(
            "INSERT INTO question_attempts(question_id,selected,correct,mode,candidate_id,response_time_ms,confidence) VALUES (?,?,?,?,?,?,?)",
            ("account-lifecycle-q1", "[1]", 0, "drill", candidate_id, 1400, 4),
        )
        session = conn.execute(
            "INSERT INTO exam_sessions(track_id,candidate_id,mode,status,total_questions) VALUES (?,?,?,'submitted',1)",
            ("snowpro-core", candidate_id, "exam_full_mock"),
        )
        session_id = int(session.lastrowid)
        conn.execute(
            "INSERT INTO candidate_srs_state(candidate_id,question_id,track_id,domain_id,skill_id,lapses,due_at) VALUES (?,?,?,?,?,1,datetime('now'))",
            (candidate_id, "account-lifecycle-q1", "snowpro-core", "features-architecture", "snowflake-architecture"),
        )
        conn.execute(
            "INSERT INTO candidate_mistake_notebook(candidate_id,question_id,track_id,domain_id,skill_id,miss_count,status) VALUES (?,?,?,?,?,1,'open')",
            (candidate_id, "account-lifecycle-q1", "snowpro-core", "features-architecture", "snowflake-architecture"),
        )
        conn.execute(
            "INSERT INTO candidate_study_preferences(candidate_id,track_id,exam_date,daily_minutes,days_per_week) VALUES (?,?,?,?,?)",
            (candidate_id, "snowpro-core", "2026-10-01", 45, 5),
        )
        conn.execute(
            "INSERT INTO feedback_submissions(title,category,description,route,track_id,candidate_id) VALUES (?,?,?,?,?,?)",
            ("Lifecycle feedback", "account", "Regression row", "#/account", "snowpro-core", candidate_id),
        )
        assert session_id > 0


def check_export(candidate_id: int) -> None:
    payload = account_export_payload(candidate_id)
    required = {
        "profile",
        "memberships",
        "exam_history",
        "practice_attempts",
        "task_progress",
        "srs_state",
        "mistake_notebook",
        "study_preferences",
        "bookmarks",
        "notes",
        "identities",
        "sessions",
        "account_audit",
        "billing_summary",
    }
    assert required <= set(payload)
    serialized = json.dumps(payload, sort_keys=True)
    for forbidden in (
        "password_hash",
        "password_salt",
        "token_hash",
        "provider_customer_id",
        "provider_subscription_id",
        "provider_payment_id",
        "provider_event_id",
        "account_action_tokens",
    ):
        if forbidden in serialized:
            raise AssertionError(f"Sensitive/internal field leaked into export: {forbidden}")
    assert payload["practice_attempts"]
    assert payload["exam_history"]
    assert payload["srs_state"]
    assert payload["mistake_notebook"]
    assert payload["study_preferences"]


def check_subscription_aware_deletion(email: str, password: str, candidate_id: int) -> None:
    survivor, _ = create_candidate("Survivor", "lifecycle-survivor@example.com", "SurvivorPassword!6")
    survivor_id = int(survivor["id"])
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO billing_subscriptions(
              candidate_id,provider,provider_customer_id,provider_subscription_id,
              provider_price_id,internal_plan,status,cancel_at_period_end
            ) VALUES (?,?,?,?,?,?,?,0)
            """,
            (candidate_id, "stripe", "cus_lifecycle", "sub_lifecycle", "price_lifecycle", "premium_20", "active"),
        )

    client = TestClient(app)
    assert client.post("/api/auth/login", json={"email": email, "password": password}).status_code == 200
    blocked = client.request(
        "DELETE",
        "/api/account",
        json={"confirmation": "DELETE", "password": password},
    )
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["detail"]["code"] == "active_subscription"

    with connect() as conn:
        conn.execute("UPDATE billing_subscriptions SET status='canceled' WHERE candidate_id=?", (candidate_id,))
    deleted = client.request(
        "DELETE",
        "/api/account",
        json={"confirmation": "DELETE", "password": password},
    )
    assert deleted.status_code == 200, deleted.text
    receipt = deleted.json()["receipt_id"]
    assert deleted.json()["deleted"] is True and receipt

    with connect() as conn:
        assert not conn.execute("SELECT 1 FROM candidate_accounts WHERE id=?", (candidate_id,)).fetchone()
        assert not conn.execute("SELECT 1 FROM question_attempts WHERE candidate_id=?", (candidate_id,)).fetchone()
        assert not conn.execute("SELECT 1 FROM exam_sessions WHERE candidate_id=?", (candidate_id,)).fetchone()
        assert not conn.execute("SELECT 1 FROM candidate_srs_state WHERE candidate_id=?", (candidate_id,)).fetchone()
        assert not conn.execute("SELECT 1 FROM candidate_mistake_notebook WHERE candidate_id=?", (candidate_id,)).fetchone()
        assert not conn.execute("SELECT 1 FROM candidate_study_preferences WHERE candidate_id=?", (candidate_id,)).fetchone()
        receipt_row = conn.execute(
            "SELECT receipt_id,reason FROM account_deletion_receipts WHERE receipt_id=?",
            (receipt,),
        ).fetchone()
        assert receipt_row and receipt_row["reason"] == "candidate_request"
        assert conn.execute("SELECT 1 FROM candidate_accounts WHERE id=?", (survivor_id,)).fetchone()


def main() -> None:
    try:
        with TestClient(app):
            pass
        candidate_id, original_password = check_verification_and_resend()
        reset_password = check_password_reset(candidate_id, original_password)
        email, final_password = check_password_and_email_change(candidate_id, reset_password)
        check_google_unlink_safeguard()
        seed_export_and_delete_data(candidate_id)
        check_export(candidate_id)
        check_subscription_aware_deletion(email, final_password, candidate_id)
        print(
            f"Account lifecycle: PASS (backend={DATABASE_BACKEND}, verification, recovery, identities, export, subscription-aware purge)"
        )
    finally:
        TEMP.cleanup()


if __name__ == "__main__":
    main()
