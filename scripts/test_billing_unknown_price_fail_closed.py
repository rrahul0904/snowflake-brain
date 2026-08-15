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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory(prefix="snowflake-billing-unknown-price-")
os.environ["BRAIN_DB"] = str(Path(TEMP.name) / "billing-unknown-price.sqlite")
os.environ["SECURITY_RATE_LIMIT_ENABLED"] = "false"
os.environ["BILLING_ENABLED"] = "true"
os.environ["STRIPE_SECRET_KEY"] = "sk_test_not_real"
os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_unknown_price_test"
os.environ["STRIPE_PRICE_PREMIUM_100"] = "price_100"
os.environ["STRIPE_PRICE_PREMIUM_250"] = "price_250"
os.environ["STRIPE_PRICE_PREMIUM_500"] = "price_500"
os.environ["STRIPE_PRICE_EXAM_PACK"] = "price_pack"

from fastapi.testclient import TestClient  # noqa: E402
from app.database import connect, run_migrations  # noqa: E402
from app.identity_billing_schema import ensure_identity_billing_schema  # noqa: E402
from app.main import app  # noqa: E402


def check(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


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


def subscription_event(event_id: str, created: int, price_id: str | None, *, include_items: bool = True) -> dict:
    obj = {
        "id": "sub_unknown_price_test",
        "customer": "cus_unknown_price_test",
        "status": "active",
        "current_period_start": created - 100,
        "current_period_end": int(time.time()) + 30 * 86400,
        "cancel_at_period_end": False,
    }
    if include_items:
        obj["items"] = {"data": [{"price": {"id": price_id}}]}
    return {
        "id": event_id,
        "created": created,
        "type": "customer.subscription.updated",
        "data": {"object": obj},
    }


def main() -> None:
    run_migrations()
    ensure_identity_billing_schema()
    client = TestClient(app)
    registered = client.post(
        "/api/auth/register",
        json={"display_name": "Unknown Price", "email": "unknown-price@example.com", "password": "candidate-password"},
    )
    check(registered.status_code == 201, registered.text)
    candidate_id = int(registered.json()["candidate"]["id"])
    with connect() as conn:
        conn.execute(
            "INSERT INTO billing_customers(candidate_id,provider,provider_customer_id) VALUES (?,'stripe','cus_unknown_price_test')",
            (candidate_id,),
        )

    known = send(client, subscription_event("evt_known_price", 1000, "price_100"))
    check(known.status_code == 200, known.text)
    membership = client.get("/api/auth/me").json()["membership"]
    check(membership["plan_code"] == "premium_20", "known Stripe price activates Premium 100")
    entitlement_version = int(membership["entitlement_version"])

    unknown = send(client, subscription_event("evt_unknown_price", 1100, "price_future_not_configured"))
    check(unknown.status_code == 400, "unknown price must fail closed")
    after_unknown = client.get("/api/auth/me").json()["membership"]
    check(after_unknown["plan_code"] == "premium_20", "failed unknown price cannot alter or re-grant another tier")
    check(int(after_unknown["entitlement_version"]) == entitlement_version, "failed unknown price does not mutate entitlement version")

    with connect() as conn:
        stored = conn.execute(
            "SELECT provider_price_id,internal_plan,last_provider_event_created FROM billing_subscriptions WHERE provider_subscription_id='sub_unknown_price_test'"
        ).fetchone()
        failed_event = conn.execute(
            "SELECT processing_status,error_message FROM billing_events WHERE provider_event_id='evt_unknown_price'"
        ).fetchone()
    check(stored["provider_price_id"] == "price_100", "unknown event cannot replace stored known provider price")
    check(stored["internal_plan"] == "premium_20", "unknown event cannot replace stored internal plan")
    check(int(stored["last_provider_event_created"]) == 1000, "unknown event cannot advance subscription event authority")
    check(failed_event["processing_status"] == "failed", "unknown price event is retained as a failed audit event")

    omitted = send(client, subscription_event("evt_items_omitted", 1200, None, include_items=False))
    check(omitted.status_code == 200, omitted.text)
    after_omitted = client.get("/api/auth/me").json()["membership"]
    check(after_omitted["plan_code"] == "premium_20", "genuinely omitted item data may reuse the already stored known plan")
    with connect() as conn:
        stored_after = conn.execute(
            "SELECT provider_price_id,internal_plan,last_provider_event_created FROM billing_subscriptions WHERE provider_subscription_id='sub_unknown_price_test'"
        ).fetchone()
    check(stored_after["provider_price_id"] == "price_100", "omitted item data preserves the stored provider price")
    check(int(stored_after["last_provider_event_created"]) == 1200, "safe omitted-item lifecycle event can advance event ordering")

    print("Stripe unknown-price fail-closed checks passed.")


if __name__ == "__main__":
    main()
