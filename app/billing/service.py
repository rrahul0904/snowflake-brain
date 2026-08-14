from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException

from ..config import (
    APP_BASE_URL,
    BILLING_ENABLED,
    BILLING_PAST_DUE_GRACE_DAYS,
    STRIPE_PRICE_EXAM_PACK,
    STRIPE_PRICE_PREMIUM_100,
    STRIPE_PRICE_PREMIUM_250,
    STRIPE_PRICE_PREMIUM_500,
    STRIPE_SECRET_KEY,
    STRIPE_WEBHOOK_SECRET,
)
from ..database import connect
from ..entitlements import PLAN_CATALOG, apply_membership_plan
from ..identity_billing_schema import ensure_identity_billing_schema
from .stripe_provider import StripeProvider


SUBSCRIPTION_PLANS = {"premium_20", "premium_40", "premium_100"}
PURCHASE_PLANS = {"exam_pack_35"}
PAID_PLANS = SUBSCRIPTION_PLANS | PURCHASE_PLANS


def price_map() -> dict[str, str]:
    return {
        "premium_20": STRIPE_PRICE_PREMIUM_100,
        "premium_40": STRIPE_PRICE_PREMIUM_250,
        "premium_100": STRIPE_PRICE_PREMIUM_500,
        "exam_pack_35": STRIPE_PRICE_EXAM_PACK,
    }


def reverse_price_map() -> dict[str, str]:
    return {price: plan for plan, price in price_map().items() if price}


def billing_configured() -> bool:
    configured_prices = [value for value in price_map().values() if value]
    return bool(BILLING_ENABLED and STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET and configured_prices)


def billing_public_config() -> dict[str, Any]:
    return {
        "enabled": billing_configured(),
        "provider": "stripe" if billing_configured() else None,
        "available_plans": [plan for plan, price in price_map().items() if price] if billing_configured() else [],
    }


def _provider() -> StripeProvider:
    if not billing_configured():
        raise HTTPException(
            status_code=503,
            detail={
                "code": "billing_unavailable",
                "message": "Checkout is not enabled in this environment. No membership change or payment was made.",
            },
        )
    return StripeProvider()


def _candidate_for_customer(provider: str, customer_id: str) -> int | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT candidate_id FROM billing_customers WHERE provider=? AND provider_customer_id=?",
            (provider, customer_id),
        ).fetchone()
    return int(row["candidate_id"]) if row else None


def _get_or_create_customer(candidate: dict[str, Any], provider: StripeProvider) -> str:
    ensure_identity_billing_schema()
    with connect() as conn:
        row = conn.execute(
            "SELECT provider_customer_id FROM billing_customers WHERE provider='stripe' AND candidate_id=?",
            (candidate["id"],),
        ).fetchone()
    if row:
        return str(row["provider_customer_id"])
    provider_customer_id = provider.create_customer(email=candidate["email"], candidate_id=int(candidate["id"]))
    try:
        with connect() as conn:
            conn.execute(
                "INSERT INTO billing_customers(candidate_id,provider,provider_customer_id) VALUES (?,'stripe',?)",
                (candidate["id"], provider_customer_id),
            )
    except sqlite3.IntegrityError:
        with connect() as conn:
            row = conn.execute(
                "SELECT provider_customer_id FROM billing_customers WHERE provider='stripe' AND candidate_id=?",
                (candidate["id"],),
            ).fetchone()
        if row:
            return str(row["provider_customer_id"])
        raise
    return provider_customer_id


def create_checkout(candidate: dict[str, Any], plan_code: str) -> dict[str, Any]:
    if plan_code not in PAID_PLANS or plan_code not in PLAN_CATALOG:
        raise HTTPException(status_code=400, detail={"code": "invalid_plan", "message": "This plan cannot be purchased."})
    provider = _provider()
    price_id = price_map().get(plan_code) or ""
    if not price_id:
        raise HTTPException(status_code=503, detail={"code": "billing_plan_unavailable", "message": "This plan is not configured for checkout."})
    customer_id = _get_or_create_customer(candidate, provider)
    mode = "subscription" if plan_code in SUBSCRIPTION_PLANS else "payment"
    checkout = provider.create_checkout_session(
        customer_id=customer_id,
        candidate_id=int(candidate["id"]),
        plan_code=plan_code,
        price_id=price_id,
        mode=mode,
        success_url=f"{APP_BASE_URL}/#/membership?checkout=success",
        cancel_url=f"{APP_BASE_URL}/#/membership?checkout=cancelled",
    )
    if not checkout.get("url"):
        raise HTTPException(status_code=502, detail="Billing provider did not return a checkout URL.")
    return {"checkout_url": checkout["url"], "checkout_session_id": checkout.get("id"), "plan_code": plan_code}


def _stripe_time(value: Any) -> str | None:
    if value in {None, ""}:
        return None
    try:
        timestamp = int(value)
    except (TypeError, ValueError):
        return str(value)
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def subscription_allows_access(status: str, current_period_end: str | None) -> bool:
    normalized = (status or "").lower()
    if normalized in {"active", "trialing"}:
        return True
    period_end = _parse_iso(current_period_end)
    now = datetime.now(timezone.utc)
    if normalized in {"canceled", "cancelled"}:
        return bool(period_end and period_end > now)
    if normalized == "past_due":
        if not period_end:
            return False
        return now <= period_end + timedelta(days=BILLING_PAST_DUE_GRACE_DAYS)
    return False


def _fallback_paid_plan(candidate_id: int) -> str:
    with connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM billing_purchases WHERE candidate_id=? AND product_type='exam_pack_35' AND status='paid' LIMIT 1",
            (candidate_id,),
        ).fetchone()
    return "exam_pack_35" if row else "free"


def _subscription_plan_from_object(subscription: dict[str, Any]) -> str | None:
    for item in ((subscription.get("items") or {}).get("data") or []):
        price = item.get("price") or {}
        price_id = price.get("id") if isinstance(price, dict) else None
        if price_id and price_id in reverse_price_map():
            return reverse_price_map()[price_id]
    metadata_plan = str((subscription.get("metadata") or {}).get("plan_code") or "")
    if metadata_plan in SUBSCRIPTION_PLANS:
        return metadata_plan
    return None


def _store_subscription(candidate_id: int, event_id: str, subscription: dict[str, Any]) -> dict[str, Any]:
    customer_id = str(subscription.get("customer") or "")
    subscription_id = str(subscription.get("id") or "")
    plan_code = _subscription_plan_from_object(subscription)
    if not customer_id or not subscription_id:
        raise ValueError("Subscription event is missing customer or subscription ID")
    if not plan_code:
        existing = None
        with connect() as conn:
            existing = conn.execute(
                "SELECT internal_plan,provider_price_id FROM billing_subscriptions WHERE provider='stripe' AND provider_subscription_id=?",
                (subscription_id,),
            ).fetchone()
        if not existing:
            raise ValueError("Subscription price is not mapped to an internal plan")
        plan_code = str(existing["internal_plan"])
        price_id = str(existing["provider_price_id"])
    else:
        price_id = price_map()[plan_code]
    status = str(subscription.get("status") or "unknown")
    period_start = _stripe_time(subscription.get("current_period_start"))
    period_end = _stripe_time(subscription.get("current_period_end"))
    cancel_at_period_end = 1 if subscription.get("cancel_at_period_end") else 0
    with connect() as conn:
        conn.execute(
            "INSERT INTO billing_subscriptions(candidate_id,provider,provider_customer_id,provider_subscription_id,provider_price_id,internal_plan,status,current_period_start,current_period_end,cancel_at_period_end) "
            "VALUES (?,'stripe',?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(provider,provider_subscription_id) DO UPDATE SET provider_customer_id=excluded.provider_customer_id, "
            "provider_price_id=excluded.provider_price_id,internal_plan=excluded.internal_plan,status=excluded.status, "
            "current_period_start=excluded.current_period_start,current_period_end=excluded.current_period_end, "
            "cancel_at_period_end=excluded.cancel_at_period_end,updated_at=datetime('now')",
            (candidate_id, customer_id, subscription_id, price_id, plan_code, status, period_start, period_end, cancel_at_period_end),
        )
    if subscription_allows_access(status, period_end):
        apply_membership_plan(
            candidate_id,
            plan_code,
            source="stripe_webhook",
            reason=f"subscription_{status}",
            provider_event_id=event_id,
            expires_at=period_end if status in {"canceled", "cancelled"} else None,
        )
    else:
        apply_membership_plan(
            candidate_id,
            _fallback_paid_plan(candidate_id),
            source="stripe_webhook",
            reason=f"subscription_{status}",
            provider_event_id=event_id,
        )
    return {"candidate_id": candidate_id, "plan_code": plan_code, "status": status}


def _record_exam_pack(candidate_id: int, event_id: str, session: dict[str, Any]) -> dict[str, Any]:
    metadata = session.get("metadata") or {}
    plan_code = str(metadata.get("plan_code") or "")
    if plan_code != "exam_pack_35":
        return {"ignored": True, "reason": "not_exam_pack"}
    payment_status = str(session.get("payment_status") or "")
    if payment_status not in {"paid", "no_payment_required"}:
        return {"ignored": True, "reason": "payment_not_complete"}
    payment_id = str(session.get("payment_intent") or session.get("id") or "")
    if not payment_id:
        raise ValueError("Paid Exam Pack event is missing a payment identifier")
    try:
        with connect() as conn:
            conn.execute(
                "INSERT INTO billing_purchases(candidate_id,provider,provider_payment_id,product_type,status,metadata_json) VALUES (?,'stripe',?,'exam_pack_35','paid',?)",
                (candidate_id, payment_id, json.dumps({"checkout_session_id": session.get("id")})),
            )
    except sqlite3.IntegrityError:
        return {"duplicate_purchase": True}
    apply_membership_plan(
        candidate_id,
        "exam_pack_35",
        source="stripe_webhook",
        reason="exam_pack_purchased",
        provider_event_id=event_id,
    )
    return {"candidate_id": candidate_id, "plan_code": "exam_pack_35", "status": "paid"}


def _handle_event(event: dict[str, Any]) -> dict[str, Any]:
    event_id = str(event["id"])
    event_type = str(event["type"])
    obj = ((event.get("data") or {}).get("object") or {})
    if not isinstance(obj, dict):
        return {"ignored": True, "reason": "missing_object"}

    if event_type == "checkout.session.completed":
        customer_id = str(obj.get("customer") or "")
        candidate_id = _candidate_for_customer("stripe", customer_id)
        if candidate_id is None:
            raise ValueError("Checkout customer is not bound to a candidate")
        reference = str(obj.get("client_reference_id") or "")
        if reference and reference != str(candidate_id):
            raise ValueError("Checkout candidate reference does not match billing customer ownership")
        return _record_exam_pack(candidate_id, event_id, obj)

    if event_type in {"customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted"}:
        customer_id = str(obj.get("customer") or "")
        candidate_id = _candidate_for_customer("stripe", customer_id)
        if candidate_id is None:
            raise ValueError("Subscription customer is not bound to a candidate")
        return _store_subscription(candidate_id, event_id, obj)

    if event_type in {"invoice.paid", "invoice.payment_failed"}:
        subscription_id = str(obj.get("subscription") or "")
        if not subscription_id:
            return {"ignored": True, "reason": "invoice_without_subscription"}
        with connect() as conn:
            row = conn.execute(
                "SELECT * FROM billing_subscriptions WHERE provider='stripe' AND provider_subscription_id=?",
                (subscription_id,),
            ).fetchone()
            if not row:
                return {"ignored": True, "reason": "unknown_subscription"}
            status = "active" if event_type == "invoice.paid" else "past_due"
            conn.execute(
                "UPDATE billing_subscriptions SET status=?,updated_at=datetime('now') WHERE id=?",
                (status, row["id"]),
            )
        synthetic = {
            "id": subscription_id,
            "customer": row["provider_customer_id"],
            "status": status,
            "current_period_start": row["current_period_start"],
            "current_period_end": row["current_period_end"],
            "cancel_at_period_end": bool(row["cancel_at_period_end"]),
            "metadata": {"plan_code": row["internal_plan"]},
        }
        return _store_subscription(int(row["candidate_id"]), event_id, synthetic)

    return {"ignored": True, "reason": "unsupported_event"}


def process_stripe_webhook(payload: bytes, signature_header: str) -> dict[str, Any]:
    ensure_identity_billing_schema()
    event = StripeProvider().verify_webhook(payload, signature_header)
    event_id = str(event["id"])
    event_type = str(event["type"])
    payload_hash = hashlib.sha256(payload).hexdigest()
    try:
        with connect() as conn:
            conn.execute(
                "INSERT INTO billing_events(provider,provider_event_id,event_type,payload_hash,processing_status) VALUES ('stripe',?,?,?,'processing')",
                (event_id, event_type, payload_hash),
            )
    except sqlite3.IntegrityError:
        return {"received": True, "duplicate": True, "event_id": event_id}

    try:
        result = _handle_event(event)
    except Exception as error:
        with connect() as conn:
            conn.execute(
                "UPDATE billing_events SET processing_status='failed',processed_at=datetime('now'),error_message=? WHERE provider='stripe' AND provider_event_id=?",
                (str(error)[:500], event_id),
            )
        raise HTTPException(status_code=400, detail="Billing event could not be applied safely.") from error

    with connect() as conn:
        conn.execute(
            "UPDATE billing_events SET processing_status='processed',processed_at=datetime('now') WHERE provider='stripe' AND provider_event_id=?",
            (event_id,),
        )
    return {"received": True, "duplicate": False, "event_id": event_id, "result": result}
