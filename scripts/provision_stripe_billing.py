#!/usr/bin/env python3
"""Provision Stripe billing infrastructure without exposing provider secrets.

This administrative script is intended for an approved GitHub Actions job. It:
- discovers the four Snowflake Certification Guide products by metadata;
- validates their exact price contract in the selected Stripe mode;
- creates one dedicated Stripe webhook when no matching endpoint exists;
- captures the one-time webhook signing secret only in process memory;
- immediately upserts Stripe credentials and resolved price IDs into the chosen
  Vercel environment as sensitive values; and
- never prints API keys, webhook signing secrets, or full provider responses.

An existing matching webhook cannot reveal its signing secret. In that case the
job fails closed unless EXISTING_STRIPE_WEBHOOK_SECRET is supplied by the
approved secret store. This prevents reruns from creating duplicate endpoints
or silently installing an unknown signing secret.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx


STRIPE_API_BASE = "https://api.stripe.com/v1"
STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY", "").strip()
STRIPE_MODE = os.environ.get("STRIPE_MODE", "test").strip().lower()
STRIPE_WEBHOOK_URL = os.environ.get("STRIPE_WEBHOOK_URL", "").strip()
EXISTING_WEBHOOK_SECRET = os.environ.get("EXISTING_STRIPE_WEBHOOK_SECRET", "").strip()
VERCEL_TOKEN = os.environ.get("VERCEL_TOKEN", "").strip()
VERCEL_PROJECT_ID = os.environ.get("VERCEL_PROJECT_ID", "prj_2SLKmOpeMM8ogNkXfNYHu7IyjYab").strip()
VERCEL_TEAM_ID = os.environ.get("VERCEL_TEAM_ID", "team_zmEezpOKGZy2sH5nqTfO44LD").strip()
VERCEL_TARGET = os.environ.get("VERCEL_TARGET", "preview").strip().lower()
ENABLE_BILLING = os.environ.get("ENABLE_BILLING", "false").strip().lower() in {"1", "true", "yes", "on"}

WEBHOOK_EVENTS = [
    "checkout.session.completed",
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "invoice.paid",
    "invoice.payment_failed",
]


@dataclass(frozen=True)
class PlanContract:
    plan: str
    env_key: str
    unit_amount: int
    recurring_interval: str | None


PLAN_CONTRACTS = (
    PlanContract("premium_20", "STRIPE_PRICE_PREMIUM_100", 2000, "month"),
    PlanContract("premium_40", "STRIPE_PRICE_PREMIUM_250", 4000, "month"),
    PlanContract("premium_100", "STRIPE_PRICE_PREMIUM_500", 10000, "month"),
    PlanContract("exam_pack_35", "STRIPE_PRICE_EXAM_PACK", 3500, None),
)


def require(condition: object, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def stripe_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {STRIPE_API_KEY}"}


def stripe_request(client: httpx.Client, method: str, path: str, *, data: Any = None, params: Any = None) -> dict[str, Any]:
    response = client.request(
        method,
        f"{STRIPE_API_BASE}{path}",
        headers=stripe_headers(),
        data=data,
        params=params,
    )
    if response.status_code < 200 or response.status_code >= 300:
        raise RuntimeError(f"Stripe API request failed for {path} with HTTP {response.status_code}")
    payload = response.json()
    require(isinstance(payload, dict), f"Stripe API returned an invalid payload for {path}")
    return payload


def account_state(client: httpx.Client) -> dict[str, bool]:
    payload = stripe_request(client, "GET", "/account")
    return {
        "charges_enabled": bool(payload.get("charges_enabled")),
        "payouts_enabled": bool(payload.get("payouts_enabled")),
    }


def discover_catalog(client: httpx.Client) -> dict[str, str]:
    payload = stripe_request(client, "GET", "/products", params={"active": "true", "limit": "100"})
    products = payload.get("data") or []
    require(isinstance(products, list), "Stripe products payload is invalid")
    resolved: dict[str, str] = {}
    expected_live = STRIPE_MODE == "live"

    for contract in PLAN_CONTRACTS:
        matches = []
        for product in products:
            if not isinstance(product, dict):
                continue
            metadata = product.get("metadata") or {}
            if metadata.get("app") == "snowflake-brain" and metadata.get("plan") == contract.plan:
                matches.append(product)
        require(len(matches) == 1, f"Expected exactly one active Stripe product for {contract.plan}; found {len(matches)}")
        require(bool(matches[0].get("livemode")) == expected_live, f"Stripe product mode mismatch for {contract.plan}")
        price_id = str(matches[0].get("default_price") or "").strip()
        require(bool(price_id), f"Stripe product for {contract.plan} has no default price")
        price = stripe_request(client, "GET", f"/prices/{price_id}")
        require(bool(price.get("livemode")) == expected_live, f"Stripe price mode mismatch for {contract.plan}")
        require(bool(price.get("active")), f"Stripe price for {contract.plan} is inactive")
        require(str(price.get("currency") or "").lower() == "usd", f"Stripe price currency mismatch for {contract.plan}")
        require(int(price.get("unit_amount") or -1) == contract.unit_amount, f"Stripe price amount mismatch for {contract.plan}")
        recurring = price.get("recurring")
        if contract.recurring_interval is None:
            require(not recurring, f"Stripe price for {contract.plan} must be one-time")
        else:
            require(isinstance(recurring, dict), f"Stripe price for {contract.plan} must be recurring")
            require(recurring.get("interval") == contract.recurring_interval, f"Stripe recurring interval mismatch for {contract.plan}")
        resolved[contract.env_key] = price_id

    return resolved


def reconcile_webhook(client: httpx.Client) -> tuple[str, bool]:
    payload = stripe_request(client, "GET", "/webhook_endpoints", params={"limit": "100"})
    endpoints = payload.get("data") or []
    require(isinstance(endpoints, list), "Stripe webhook endpoint payload is invalid")
    expected_live = STRIPE_MODE == "live"
    matching = [
        row for row in endpoints
        if isinstance(row, dict)
        and row.get("url") == STRIPE_WEBHOOK_URL
        and row.get("status") == "enabled"
        and bool(row.get("livemode")) == expected_live
    ]
    require(len(matching) <= 1, "Multiple enabled Stripe webhooks already target the Snowflake billing URL")

    if matching:
        require(
            bool(EXISTING_WEBHOOK_SECRET),
            "A matching Stripe webhook already exists, but its signing secret is not available in EXISTING_STRIPE_WEBHOOK_SECRET",
        )
        enabled = set(matching[0].get("enabled_events") or [])
        missing = sorted(set(WEBHOOK_EVENTS) - enabled)
        require(not missing, "Existing Stripe webhook is missing required billing events")
        return EXISTING_WEBHOOK_SECRET, False

    form: list[tuple[str, str]] = [("url", STRIPE_WEBHOOK_URL)]
    form.append(("description", f"Snowflake Certification Guide billing webhook ({STRIPE_MODE})"))
    form.extend(("enabled_events[]", event) for event in WEBHOOK_EVENTS)
    created = stripe_request(client, "POST", "/webhook_endpoints", data=form)
    require(bool(created.get("livemode")) == expected_live, "New Stripe webhook mode does not match requested mode")
    secret = str(created.get("secret") or "").strip()
    require(bool(secret), "Stripe did not return a webhook signing secret for the newly created endpoint")
    return secret, True


def upsert_vercel_env(client: httpx.Client, key: str, value: str) -> None:
    query = urlencode({"upsert": "true", "teamId": VERCEL_TEAM_ID})
    url = f"https://api.vercel.com/v10/projects/{VERCEL_PROJECT_ID}/env?{query}"
    body = {
        "key": key,
        "value": value,
        "type": "sensitive",
        "target": [VERCEL_TARGET],
        "comment": f"Snowflake Certification Guide Stripe {STRIPE_MODE} billing configuration",
    }
    response = client.post(
        url,
        headers={"Authorization": f"Bearer {VERCEL_TOKEN}", "Content-Type": "application/json"},
        json=body,
    )
    if response.status_code not in {200, 201}:
        raise RuntimeError(f"Vercel environment upsert failed for {key} with HTTP {response.status_code}")
    try:
        payload = response.json()
    except Exception:
        payload = {}
    if isinstance(payload, dict) and payload.get("failed"):
        raise RuntimeError(f"Vercel reported a failed environment upsert for {key}")


def main() -> None:
    require(STRIPE_MODE in {"test", "live"}, "STRIPE_MODE must be test or live")
    require(VERCEL_TARGET in {"preview", "production"}, "VERCEL_TARGET must be preview or production")
    require(bool(STRIPE_API_KEY), "STRIPE_API_KEY is required")
    require(bool(STRIPE_WEBHOOK_URL) and STRIPE_WEBHOOK_URL.startswith("https://"), "STRIPE_WEBHOOK_URL must be an HTTPS URL")
    require(bool(VERCEL_TOKEN), "VERCEL_TOKEN is required")
    require(bool(VERCEL_PROJECT_ID) and bool(VERCEL_TEAM_ID), "Vercel project/team identifiers are required")
    require(not (STRIPE_MODE == "test" and VERCEL_TARGET == "production"), "Test Stripe credentials must never be installed in Vercel Production")
    require(not (STRIPE_MODE == "live" and VERCEL_TARGET == "preview"), "Live Stripe credentials must never be installed in Vercel Preview")

    with httpx.Client(timeout=30.0) as stripe_client:
        account = account_state(stripe_client)
        if STRIPE_MODE == "live" and ENABLE_BILLING:
            require(account["charges_enabled"], "Live Stripe billing cannot be enabled until charges are enabled")
        catalog = discover_catalog(stripe_client)
        webhook_secret, webhook_created = reconcile_webhook(stripe_client)

    with httpx.Client(timeout=30.0) as vercel_client:
        upsert_vercel_env(vercel_client, "STRIPE_SECRET_KEY", STRIPE_API_KEY)
        upsert_vercel_env(vercel_client, "STRIPE_WEBHOOK_SECRET", webhook_secret)
        for key, value in sorted(catalog.items()):
            upsert_vercel_env(vercel_client, key, value)
        upsert_vercel_env(vercel_client, "BILLING_ENABLED", "true" if ENABLE_BILLING else "false")

    # Deliberately exclude API keys, webhook signing secrets, and Vercel tokens.
    print(
        json.dumps(
            {
                "status": "ok",
                "stripe_mode": STRIPE_MODE,
                "vercel_target": VERCEL_TARGET,
                "webhook_created": webhook_created,
                "required_events": WEBHOOK_EVENTS,
                "resolved_plan_keys": sorted(catalog),
                "billing_enabled": ENABLE_BILLING,
                "live_charges_enabled": account["charges_enabled"] if STRIPE_MODE == "live" else None,
                "live_payouts_enabled": account["payouts_enabled"] if STRIPE_MODE == "live" else None,
                "redeploy_required": True,
            }
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Stripe billing provisioning failed: {type(exc).__name__}", file=sys.stderr)
        raise
