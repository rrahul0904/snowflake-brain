#!/usr/bin/env python3
"""Verify the configured Snowflake Certification Guide Stripe catalog safely.

This script reads Stripe credentials and price IDs only from environment variables.
It never prints secret keys or webhook secrets. The generated artifact contains only
non-secret catalog IDs, amounts, modes, and validation findings.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts" / "stripe-catalog-verification.json"
STRIPE_API_BASE = os.environ.get("STRIPE_API_BASE", "https://api.stripe.com").rstrip("/")
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "").strip()
EXPECTED_LIVEMODE_RAW = os.environ.get("EXPECTED_STRIPE_LIVEMODE", "").strip().lower()

CATALOG: dict[str, dict[str, Any]] = {
    "premium_20": {
        "env": "STRIPE_PRICE_PREMIUM_100",
        "amount": 2000,
        "currency": "usd",
        "recurring_interval": "month",
    },
    "premium_40": {
        "env": "STRIPE_PRICE_PREMIUM_250",
        "amount": 4000,
        "currency": "usd",
        "recurring_interval": "month",
    },
    "premium_100": {
        "env": "STRIPE_PRICE_PREMIUM_500",
        "amount": 10000,
        "currency": "usd",
        "recurring_interval": "month",
    },
    "exam_pack_35": {
        "env": "STRIPE_PRICE_EXAM_PACK",
        "amount": 3500,
        "currency": "usd",
        "recurring_interval": None,
    },
}


def require(value: object, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def expected_livemode() -> bool | None:
    if not EXPECTED_LIVEMODE_RAW:
        return None
    if EXPECTED_LIVEMODE_RAW in {"1", "true", "yes", "on"}:
        return True
    if EXPECTED_LIVEMODE_RAW in {"0", "false", "no", "off"}:
        return False
    raise RuntimeError("EXPECTED_STRIPE_LIVEMODE must be true/false when provided")


def retrieve_price(client: httpx.Client, price_id: str) -> dict[str, Any]:
    response = client.get(
        f"{STRIPE_API_BASE}/v1/prices/{price_id}",
        headers={"Authorization": f"Bearer {STRIPE_SECRET_KEY}"},
        params={"expand[]": "product"},
    )
    if response.status_code != 200:
        raise RuntimeError(f"Stripe price lookup failed for {price_id} with HTTP {response.status_code}")
    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError(f"Stripe returned an invalid price payload for {price_id}")
    return payload


def main() -> int:
    require(bool(STRIPE_SECRET_KEY), "STRIPE_SECRET_KEY is required")
    expected_mode = expected_livemode()
    findings: list[str] = []
    results: dict[str, Any] = {}

    with httpx.Client(timeout=15.0) as client:
        for plan_code, expected in CATALOG.items():
            env_name = str(expected["env"])
            price_id = os.environ.get(env_name, "").strip()
            if not price_id:
                findings.append(f"missing_{env_name.lower()}")
                results[plan_code] = {"status": "missing", "env": env_name}
                continue

            try:
                price = retrieve_price(client, price_id)
            except Exception as exc:
                findings.append(f"lookup_failed_{plan_code}")
                results[plan_code] = {
                    "status": "fail",
                    "price_id": price_id,
                    "error_type": type(exc).__name__,
                }
                continue

            plan_findings: list[str] = []
            if not bool(price.get("active")):
                plan_findings.append("price_inactive")
            if str(price.get("currency") or "").lower() != expected["currency"]:
                plan_findings.append("currency_mismatch")
            if int(price.get("unit_amount") or -1) != int(expected["amount"]):
                plan_findings.append("amount_mismatch")
            if expected_mode is not None and bool(price.get("livemode")) != expected_mode:
                plan_findings.append("livemode_mismatch")

            recurring = price.get("recurring")
            expected_interval = expected["recurring_interval"]
            if expected_interval is None:
                if recurring is not None:
                    plan_findings.append("unexpected_recurring_price")
            elif not isinstance(recurring, dict) or recurring.get("interval") != expected_interval:
                plan_findings.append("recurring_interval_mismatch")

            product = price.get("product")
            product_id = ""
            if isinstance(product, dict):
                product_id = str(product.get("id") or "")
                metadata = product.get("metadata") or {}
                if metadata.get("app") != "snowflake-brain":
                    plan_findings.append("product_app_metadata_mismatch")
                if metadata.get("plan") != plan_code:
                    plan_findings.append("product_plan_metadata_mismatch")
                if not bool(product.get("active")):
                    plan_findings.append("product_inactive")
            else:
                product_id = str(product or "")

            findings.extend(f"{plan_code}:{finding}" for finding in plan_findings)
            results[plan_code] = {
                "status": "pass" if not plan_findings else "fail",
                "price_id": price_id,
                "product_id": product_id,
                "livemode": bool(price.get("livemode")),
                "currency": price.get("currency"),
                "unit_amount": price.get("unit_amount"),
                "recurring_interval": recurring.get("interval") if isinstance(recurring, dict) else None,
                "findings": plan_findings,
            }

    payload = {
        "status": "pass" if not findings else "fail",
        "expected_livemode": expected_mode,
        "catalog": results,
        "finding_count": len(findings),
        "findings": findings,
    }
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if not findings else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Stripe catalog verification failed: {type(exc).__name__}", file=sys.stderr)
        raise
