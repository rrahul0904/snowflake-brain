#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory(prefix="snowflake-tier-transition-test-")
os.environ["BRAIN_DB"] = str(Path(TEMP.name) / "tier.sqlite")
os.environ["SECURITY_RATE_LIMIT_ENABLED"] = "false"
os.environ["BILLING_ENABLED"] = "true"
os.environ["STRIPE_SECRET_KEY"] = "sk_test_not_real"
os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_tier_test"
os.environ["STRIPE_PRICE_PREMIUM_100"] = "price_100"
os.environ["STRIPE_PRICE_PREMIUM_250"] = "price_250"
os.environ["STRIPE_PRICE_PREMIUM_500"] = "price_500"
os.environ["STRIPE_PRICE_EXAM_PACK"] = "price_pack"
os.environ["BILLING_PAST_DUE_GRACE_DAYS"] = "3"

from fastapi.testclient import TestClient  # noqa: E402
from app.database import connect, run_migrations  # noqa: E402
from app.identity_billing_schema import ensure_identity_billing_schema  # noqa: E402
from app.main import app  # noqa: E402


def check(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def register(email: str) -> tuple[TestClient, int]:
    client = TestClient(app)
    response = client.post(
        "/api/auth/register",
        json={"display_name": email.split("@", 1)[0], "email": email, "password": "candidate-password"},
    )
    check(response.status_code == 201, response.text)
    return client, int(response.json()["candidate"]["id"])


def bind_customer(candidate_id: int, customer_id: str) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO billing_customers(candidate_id,provider,provider_customer_id) VALUES (?,'stripe',?)",
            (candidate_id, customer_id),
        )


def signature(payload: bytes) -> str:
    timestamp = str(int(time.time()))
    digest = hmac.new(
        os.environ["STRIPE_WEBHOOK_SECRET"].encode(),
        timestamp.encode() + b"." + payload,
        hashlib.sha256,
    ).hexdigest()
    return f"t={timestamp},v1={digest}"


def send(client: TestClient, event: dict):
    payload = json.dumps(event, separators=(",", ":")).encode()
    return client.post(
        "/api/billing/webhook",
        content=payload,
        headers={"Stripe-Signature": signature(payload), "Content-Type": "application/json"},
    )


def subscription_event(
    event_id: str,
    created: int,
    customer_id: str,
    subscription_id: str,
    price_id: str,
    status: str,
    period_end: int,
) -> dict:
    return {
        "id": event_id,
        "created": created,
        "type": "customer.subscription.updated",
        "data": {"object": {
            "id": subscription_id,
            "customer": customer_id,
            "status": status,
            "current_period_start": created - 100,
            "current_period_end": period_end,
            "cancel_at_period_end": status == "canceled",
            "items": {"data": [{"price": {"id": price_id}}]},
        }},
    }


def plan(client: TestClient) -> dict:
    return client.get("/api/auth/me").json()["membership"]


def main() -> None:
    run_migrations()
    ensure_identity_billing_schema()
    now = int(time.time())

    # One account, one provider subscription: new provider price changes the
    # internal tier; an older webhook cannot later roll it backward.
    client, candidate_id = register("tiers@example.com")
    bind_customer(candidate_id, "cus_tiers")
    first = subscription_event(
        "evt_tier_100", 1000, "cus_tiers", "sub_tiers", "price_100", "active", now + 30 * 86400
    )
    check(send(client, first).status_code == 200, "initial Premium 100 event accepted")
    check(plan(client)["plan_code"] == "premium_20", "Premium 100 activated")
    first_version = int(plan(client)["entitlement_version"])

    # Existing subscribers cannot accidentally start a second hosted checkout;
    # tier changes are routed through hosted subscription management instead.
    duplicate_checkout = client.post("/api/billing/checkout", json={"plan_code": "premium_40"})
    check(duplicate_checkout.status_code == 409, "second subscription checkout blocked")
    check("Manage plan" in duplicate_checkout.text, "caller directed to subscription management")

    upgraded = subscription_event(
        "evt_tier_250", 1200, "cus_tiers", "sub_tiers", "price_250", "active", now + 30 * 86400
    )
    check(send(client, upgraded).status_code == 200, "Premium 250 upgrade event accepted")
    upgraded_membership = plan(client)
    check(upgraded_membership["plan_code"] == "premium_40", "tier moved to Premium 250")
    upgraded_version = int(upgraded_membership["entitlement_version"])
    check(upgraded_version > first_version, "upgrade increments entitlement version")

    stale_cancel = subscription_event(
        "evt_stale_cancel", 1100, "cus_tiers", "sub_tiers", "price_100", "canceled", now - 60
    )
    stale_response = send(client, stale_cancel)
    check(stale_response.status_code == 200, stale_response.text)
    check(plan(client)["plan_code"] == "premium_40", "older cancellation cannot roll back newer tier")
    check(int(plan(client)["entitlement_version"]) == upgraded_version, "stale event does not bump entitlement version")

    # The same provider event ID cannot be replayed with changed content.
    altered = dict(upgraded)
    altered["data"] = {"object": dict(upgraded["data"]["object"], status="unpaid")}
    changed_payload_replay = send(client, altered)
    check(changed_payload_replay.status_code == 400, "same event id with different payload rejected")

    # A current unpaid subscription removes subscription access. The account
    # remains intact and its learning data is not deleted.
    unpaid = subscription_event(
        "evt_unpaid", 1300, "cus_tiers", "sub_tiers", "price_250", "unpaid", now + 30 * 86400
    )
    check(send(client, unpaid).status_code == 200, "unpaid status event accepted")
    check(plan(client)["plan_code"] == "free", "unpaid subscription falls back to Free")

    # Multiple provider subscriptions cannot make one cancellation erase a
    # different still-active subscription. This is defensive against external
    # billing-dashboard mistakes even though the app blocks duplicate checkout.
    multi, multi_id = register("multi@example.com")
    bind_customer(multi_id, "cus_multi")
    check(send(multi, subscription_event("evt_multi_a", 2000, "cus_multi", "sub_a", "price_100", "active", now + 86400)).status_code == 200, "first subscription stored")
    check(send(multi, subscription_event("evt_multi_b", 2100, "cus_multi", "sub_b", "price_250", "active", now + 86400)).status_code == 200, "second subscription stored")
    check(plan(multi)["plan_code"] == "premium_40", "most recently updated active subscription is effective")
    check(send(multi, subscription_event("evt_multi_b_cancel", 2200, "cus_multi", "sub_b", "price_250", "canceled", now - 1)).status_code == 200, "second cancellation stored")
    check(plan(multi)["plan_code"] == "premium_20", "first active subscription remains effective")

    # Paid Exam Pack retains its original purchase window when it becomes the
    # fallback after a subscription ends; reactivation cannot reset 30 days.
    pack, pack_id = register("pack-fallback@example.com")
    bind_customer(pack_id, "cus_pack_fallback")
    with connect() as conn:
        conn.execute(
            "INSERT INTO billing_checkout_sessions(candidate_id,provider,provider_checkout_session_id,provider_customer_id,provider_price_id,internal_plan,checkout_mode,status) "
            "VALUES (?,'stripe','cs_pack_fallback','cus_pack_fallback','price_pack','exam_pack_35','payment','pending')",
            (pack_id,),
        )
    pack_event = {
        "id": "evt_pack_fallback",
        "created": 3000,
        "type": "checkout.session.completed",
        "data": {"object": {
            "id": "cs_pack_fallback",
            "customer": "cus_pack_fallback",
            "client_reference_id": str(pack_id),
            "payment_status": "paid",
            "payment_intent": "pi_pack_fallback",
        }},
    }
    check(send(pack, pack_event).status_code == 200, "Exam Pack purchase accepted")
    old_purchase = datetime.now(timezone.utc) - timedelta(days=20)
    with connect() as conn:
        conn.execute(
            "UPDATE billing_purchases SET purchased_at=? WHERE candidate_id=? AND product_type='exam_pack_35'",
            (old_purchase.isoformat(), pack_id),
        )
    original_deadline = plan(pack)["usage"]["monthly_full_exams"]["access_expires_at"]
    check(original_deadline, "Exam Pack deadline available")

    check(send(pack, subscription_event("evt_pack_sub", 3100, "cus_pack_fallback", "sub_pack", "price_100", "active", now + 86400)).status_code == 200, "subscription can supersede Exam Pack")
    check(plan(pack)["plan_code"] == "premium_20", "subscription becomes effective plan")
    check(send(pack, subscription_event("evt_pack_sub_end", 3200, "cus_pack_fallback", "sub_pack", "price_100", "canceled", now - 1)).status_code == 200, "subscription end accepted")
    fallback = plan(pack)
    check(fallback["plan_code"] == "exam_pack_35", "paid Exam Pack restored after subscription")
    check(fallback["usage"]["monthly_full_exams"]["access_expires_at"] == original_deadline, "Exam Pack deadline was not reset")

    print("Billing tier transition hardening checks passed.")


if __name__ == "__main__":
    main()
