#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory(prefix="snowflake-google-billing-test-")
DB_PATH = Path(TEMP.name) / "candidate.sqlite"
os.environ["BRAIN_DB"] = str(DB_PATH)
os.environ["SECURITY_RATE_LIMIT_ENABLED"] = "false"
os.environ["GOOGLE_AUTH_ENABLED"] = "true"
os.environ["GOOGLE_OIDC_CLIENT_ID"] = "google-client-test.apps.googleusercontent.com"
os.environ["GOOGLE_OIDC_CLIENT_SECRET"] = "google-client-secret-test"
os.environ["GOOGLE_OIDC_REDIRECT_URI"] = "http://localhost:8010/api/auth/google/callback"
os.environ["BILLING_ENABLED"] = "true"
os.environ["STRIPE_SECRET_KEY"] = "sk_test_not_real"
os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_test_secret"
os.environ["STRIPE_PRICE_PREMIUM_100"] = "price_premium_100"
os.environ["STRIPE_PRICE_PREMIUM_250"] = "price_premium_250"
os.environ["STRIPE_PRICE_PREMIUM_500"] = "price_premium_500"
os.environ["STRIPE_PRICE_EXAM_PACK"] = "price_exam_pack"

from fastapi import HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from app.auth import (  # noqa: E402
    GOOGLE_LINK_COOKIE,
    authenticate_candidate,
    create_google_candidate,
    create_pending_google_link,
)
from app.database import connect, run_migrations  # noqa: E402
from app.entitlements import apply_membership_plan  # noqa: E402
from app.google_oidc import create_google_authorization, consume_google_flow, verify_google_identity  # noqa: E402
from app.identity_billing_schema import ensure_identity_billing_schema  # noqa: E402
from app.main import app  # noqa: E402
import app.google_oidc as google_oidc  # noqa: E402


def check(value: object, message: str) -> None:
    if not value:
        raise AssertionError(message)


def register(client: TestClient, name: str, email: str) -> dict:
    response = client.post(
        "/api/auth/register",
        json={"display_name": name, "email": email, "password": "candidate-password"},
    )
    check(response.status_code == 201, response.text)
    return response.json()


def stripe_signature(payload: bytes) -> str:
    timestamp = str(int(time.time()))
    signature = hmac.new(
        os.environ["STRIPE_WEBHOOK_SECRET"].encode(),
        timestamp.encode() + b"." + payload,
        hashlib.sha256,
    ).hexdigest()
    return f"t={timestamp},v1={signature}"


def send_event(client: TestClient, event: dict, *, valid: bool = True):
    payload = json.dumps(event, separators=(",", ":")).encode()
    signature = stripe_signature(payload) if valid else "t=1,v1=bad"
    return client.post(
        "/api/billing/webhook",
        content=payload,
        headers={"Stripe-Signature": signature, "Content-Type": "application/json"},
    )


def subscription_event(event_id: str, customer: str, subscription: str, price: str, status: str, period_end: int) -> dict:
    return {
        "id": event_id,
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": subscription,
                "customer": customer,
                "status": status,
                "current_period_start": int(time.time()) - 60,
                "current_period_end": period_end,
                "cancel_at_period_end": status == "canceled",
                "metadata": {"candidate_id": "999999", "plan_code": "premium_100"},
                "items": {"data": [{"price": {"id": price}}]},
            }
        },
    }


def main() -> None:
    run_migrations()
    ensure_identity_billing_schema()

    # Google start uses state + nonce + PKCE and stores only a state hash.
    authorization_url = create_google_authorization()
    params = parse_qs(urlparse(authorization_url).query)
    state = params["state"][0]
    check(params.get("nonce"), "Google nonce present")
    check(params.get("code_challenge_method") == ["S256"], "PKCE S256 present")
    check(params.get("code_challenge"), "PKCE challenge present")
    with connect() as conn:
        flow = conn.execute("SELECT * FROM oauth_login_flows").fetchone()
    check(flow and flow["state_hash"] == hashlib.sha256(state.encode()).hexdigest(), "only OAuth state hash stored")
    check(flow["state_hash"] != state, "raw OAuth state not stored")
    consumed = consume_google_flow(state)
    check(consumed["nonce"] == params["nonce"][0], "state resolves original nonce")
    try:
        consume_google_flow(state)
        raise AssertionError("OAuth state replay should fail")
    except HTTPException as error:
        check(error.status_code == 400, "OAuth state replay rejected")

    # Token claim validation uses Google verifier output and still enforces nonce,
    # issuer, audience and verified email itself.
    original_verify = google_oidc.google_id_token.verify_oauth2_token
    google_oidc.google_id_token.verify_oauth2_token = lambda token, request, audience: {
        "iss": "https://accounts.google.com",
        "aud": os.environ["GOOGLE_OIDC_CLIENT_ID"],
        "sub": "google-subject-test",
        "nonce": "expected-nonce",
        "email": "google@example.com",
        "email_verified": True,
        "name": "Google Candidate",
    }
    try:
        identity = verify_google_identity("signed-google-id-token", "expected-nonce")
        check(identity["sub"] == "google-subject-test", "Google subject accepted")
        try:
            verify_google_identity("signed-google-id-token", "wrong-nonce")
            raise AssertionError("wrong nonce should fail")
        except HTTPException as error:
            check(error.status_code == 401, "wrong nonce rejected")
    finally:
        google_oidc.google_id_token.verify_oauth2_token = original_verify

    # Google-only signup creates one candidate, Free membership and no usable
    # password login while keeping Google as an external identity.
    google_candidate = create_google_candidate("Google Only", "google-only@example.com", "sub-google-only")
    check(google_candidate["membership"]["plan_code"] == "free", "Google signup starts Free")
    check(google_candidate["sign_in_methods"] == ["google"], "Google identity reported")
    try:
        authenticate_candidate("google-only@example.com", "candidate-password")
        raise AssertionError("Google-only account should not accept password login")
    except HTTPException as error:
        check(error.status_code == 401, "Google-only password login rejected")

    # Existing password account must prove ownership before Google is linked.
    alice = TestClient(app)
    alice_state = register(alice, "Alice Candidate", "alice@example.com")
    alice_id = int(alice_state["candidate"]["id"])
    apply_membership_plan(alice_id, "premium_40", source="test", reason="test_premium")
    with connect() as conn:
        conn.execute(
            "INSERT INTO candidate_task_progress(candidate_id,track_id,skill_id,completed) VALUES (?,?,?,1)",
            (alice_id, "snowpro-core", "1.1"),
        )
    pending = create_pending_google_link(alice_id, "sub-alice-google", "alice@example.com")
    alice.cookies.set(GOOGLE_LINK_COOKIE, pending)
    wrong_link = alice.post("/api/auth/google/link", json={"password": "wrong-password"})
    check(wrong_link.status_code == 401, "Google link requires existing password")
    linked = alice.post("/api/auth/google/link", json={"password": "candidate-password"})
    check(linked.status_code == 200, linked.text)
    linked_payload = linked.json()
    check(int(linked_payload["candidate"]["id"]) == alice_id, "Google linking preserves candidate id")
    check(linked_payload["membership"]["plan_code"] == "premium_40", "Google linking preserves Premium")
    check(set(linked_payload["candidate"]["sign_in_methods"]) == {"email", "google"}, "linked methods reported")
    with connect() as conn:
        progress = conn.execute(
            "SELECT completed FROM candidate_task_progress WHERE candidate_id=? AND skill_id='1.1'",
            (alice_id,),
        ).fetchone()
    check(progress and progress["completed"] == 1, "Google linking preserves progress")

    # Billing is account-bound. Browser-provided plan flags do not grant access.
    eve = TestClient(app)
    eve_state = register(eve, "Eve Free", "eve@example.com")
    spoof = eve.post(
        "/api/mock/sessions",
        json={"track_id": "snowpro-core", "mode": "quick-mock", "plan": "premium_100", "tier": "premium", "is_premium": True},
    )
    check(spoof.status_code == 403, "browser plan spoof cannot unlock Premium")
    before_return = eve.get("/api/auth/me").json()["membership"]["plan_code"]
    check(eve.get("/#/membership?checkout=success").status_code == 200, "checkout return page can render")
    after_return = eve.get("/api/auth/me").json()["membership"]["plan_code"]
    check(before_return == after_return == "free", "checkout success URL cannot grant Premium")

    bob = TestClient(app)
    bob_state = register(bob, "Bob Billing", "bob@example.com")
    bob_id = int(bob_state["candidate"]["id"])
    with connect() as conn:
        conn.execute(
            "INSERT INTO billing_customers(candidate_id,provider,provider_customer_id) VALUES (?,'stripe','cus_bob')",
            (bob_id,),
        )
    active = subscription_event(
        "evt_subscription_active",
        "cus_bob",
        "sub_bob",
        os.environ["STRIPE_PRICE_PREMIUM_100"],
        "active",
        int(time.time()) + 30 * 86400,
    )
    upgraded = send_event(bob, active)
    check(upgraded.status_code == 200, upgraded.text)
    bob_membership = bob.get("/api/auth/me").json()["membership"]
    check(bob_membership["plan_code"] == "premium_20", "signed provider event activates mapped Premium plan")
    version_after_upgrade = int(bob_membership["entitlement_version"])

    replay = send_event(bob, active)
    check(replay.status_code == 200 and replay.json()["duplicate"], "webhook replay is idempotent")
    check(int(bob.get("/api/auth/me").json()["membership"]["entitlement_version"]) == version_after_upgrade, "replay does not change entitlement version")

    invalid = send_event(bob, {"id": "evt_invalid", "type": "customer.subscription.updated", "data": {"object": {}}}, valid=False)
    check(invalid.status_code == 400, "invalid webhook signature rejected")

    # Signed metadata cannot redirect one customer's entitlement to another
    # candidate: customer ownership in the private DB is authoritative.
    check(alice.get("/api/auth/me").json()["membership"]["plan_code"] == "premium_40", "Alice membership unchanged by Bob event metadata")
    check(bob.get("/api/auth/me").json()["membership"]["plan_code"] == "premium_20", "Bob owns subscription through customer binding")

    cancelled = subscription_event(
        "evt_subscription_cancelled",
        "cus_bob",
        "sub_bob",
        os.environ["STRIPE_PRICE_PREMIUM_100"],
        "canceled",
        int(time.time()) - 10,
    )
    downgraded = send_event(bob, cancelled)
    check(downgraded.status_code == 200, downgraded.text)
    bob_free = bob.get("/api/auth/me").json()["membership"]
    check(bob_free["plan_code"] == "free", "expired cancellation removes Premium")
    check(int(bob_free["entitlement_version"]) > version_after_upgrade, "real plan change increments entitlement version")

    pack = TestClient(app)
    pack_state = register(pack, "Pack Billing", "pack-billing@example.com")
    pack_id = int(pack_state["candidate"]["id"])
    with connect() as conn:
        conn.execute(
            "INSERT INTO billing_customers(candidate_id,provider,provider_customer_id) VALUES (?,'stripe','cus_pack')",
            (pack_id,),
        )
    pack_event = {
        "id": "evt_exam_pack",
        "type": "checkout.session.completed",
        "data": {"object": {
            "id": "cs_pack",
            "customer": "cus_pack",
            "client_reference_id": str(pack_id),
            "payment_status": "paid",
            "payment_intent": "pi_pack",
            "metadata": {"plan_code": "exam_pack_35", "candidate_id": str(pack_id)},
        }},
    }
    pack_response = send_event(pack, pack_event)
    check(pack_response.status_code == 200, pack_response.text)
    check(pack.get("/api/auth/me").json()["membership"]["plan_code"] == "exam_pack_35", "verified one-time purchase activates Exam Pack")

    with connect() as conn:
        event_rows = conn.execute("SELECT provider_event_id,processing_status FROM billing_events").fetchall()
        audit_rows = conn.execute("SELECT reason,source FROM membership_audit_log ORDER BY id").fetchall()
    check(any(row["provider_event_id"] == "evt_subscription_active" and row["processing_status"] == "processed" for row in event_rows), "billing event audit persisted")
    check(any(row["source"] == "stripe_webhook" for row in audit_rows), "membership audit identifies trusted billing source")

    print("Google identity and trusted billing security checks passed.")


if __name__ == "__main__":
    main()
