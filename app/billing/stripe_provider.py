from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any

import httpx
from fastapi import HTTPException

from ..config import STRIPE_API_BASE, STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET


class StripeProvider:
    name = "stripe"

    def _headers(self) -> dict[str, str]:
        if not STRIPE_SECRET_KEY:
            raise HTTPException(status_code=503, detail={"code": "billing_unavailable", "message": "Billing is not configured in this environment."})
        return {"Authorization": f"Bearer {STRIPE_SECRET_KEY}"}

    def _post(self, path: str, data: list[tuple[str, str]] | dict[str, str]) -> dict[str, Any]:
        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.post(f"{STRIPE_API_BASE}{path}", headers=self._headers(), data=data)
                response.raise_for_status()
                return response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise HTTPException(status_code=502, detail={"code": "billing_provider_error", "message": "The billing provider could not complete this request."}) from error

    def create_customer(self, *, email: str, candidate_id: int) -> str:
        payload = self._post(
            "/v1/customers",
            {
                "email": email,
                "metadata[candidate_id]": str(candidate_id),
                "metadata[product]": "snowflake-brain",
            },
        )
        customer_id = str(payload.get("id") or "")
        if not customer_id:
            raise HTTPException(status_code=502, detail="Billing provider did not return a customer ID.")
        return customer_id

    def create_checkout_session(
        self,
        *,
        customer_id: str,
        candidate_id: int,
        plan_code: str,
        price_id: str,
        mode: str,
        success_url: str,
        cancel_url: str,
    ) -> dict:
        data: list[tuple[str, str]] = [
            ("customer", customer_id),
            ("mode", mode),
            ("line_items[0][price]", price_id),
            ("line_items[0][quantity]", "1"),
            ("success_url", success_url),
            ("cancel_url", cancel_url),
            ("client_reference_id", str(candidate_id)),
            ("metadata[candidate_id]", str(candidate_id)),
            ("metadata[plan_code]", plan_code),
        ]
        if mode == "subscription":
            data.extend(
                [
                    ("subscription_data[metadata][candidate_id]", str(candidate_id)),
                    ("subscription_data[metadata][plan_code]", plan_code),
                ]
            )
        payload = self._post("/v1/checkout/sessions", data)
        return {"id": payload.get("id"), "url": payload.get("url")}

    def verify_webhook(self, payload: bytes, signature_header: str) -> dict:
        if not STRIPE_WEBHOOK_SECRET:
            raise HTTPException(status_code=503, detail="Stripe webhook verification is not configured.")
        timestamp = ""
        signatures: list[str] = []
        for part in (signature_header or "").split(","):
            key, sep, value = part.partition("=")
            if not sep:
                continue
            if key == "t":
                timestamp = value
            elif key == "v1":
                signatures.append(value)
        if not timestamp or not signatures:
            raise HTTPException(status_code=400, detail="Invalid Stripe webhook signature.")
        try:
            ts = int(timestamp)
        except ValueError as error:
            raise HTTPException(status_code=400, detail="Invalid Stripe webhook timestamp.") from error
        if abs(int(time.time()) - ts) > 300:
            raise HTTPException(status_code=400, detail="Stripe webhook timestamp is outside the allowed tolerance.")
        signed = timestamp.encode("ascii") + b"." + payload
        expected = hmac.new(STRIPE_WEBHOOK_SECRET.encode("utf-8"), signed, hashlib.sha256).hexdigest()
        if not any(hmac.compare_digest(expected, signature) for signature in signatures):
            raise HTTPException(status_code=400, detail="Invalid Stripe webhook signature.")
        try:
            event = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise HTTPException(status_code=400, detail="Invalid Stripe webhook payload.") from error
        if not isinstance(event, dict) or not event.get("id") or not event.get("type"):
            raise HTTPException(status_code=400, detail="Stripe webhook event is malformed.")
        return event
