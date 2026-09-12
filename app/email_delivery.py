from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlparse

from .config import IS_VERCEL_RUNTIME


EMAIL_DELIVERY_MODE = os.getenv("ACCOUNT_EMAIL_DELIVERY_MODE", "outbox").strip().lower() or "outbox"
EMAIL_WEBHOOK_URL = os.getenv("ACCOUNT_EMAIL_WEBHOOK_URL", "").strip()
EMAIL_WEBHOOK_TOKEN = os.getenv("ACCOUNT_EMAIL_WEBHOOK_TOKEN", "").strip()


def _secure_webhook_url(value: str) -> bool:
    if not value:
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def email_delivery_status() -> dict[str, Any]:
    """Return non-secret account-email capability state.

    The development outbox is intentionally useful for local/CI verification,
    but it is not a transactional mail provider and must never be advertised as
    production-ready on hosted Vercel runtimes. The production webhook is also
    considered ready only when its HTTPS endpoint and bearer token are both
    configured, matching the delivery contract in ``account_lifecycle``.
    """

    webhook_url_ready = _secure_webhook_url(EMAIL_WEBHOOK_URL)
    webhook_token_ready = bool(EMAIL_WEBHOOK_TOKEN)
    webhook_ready = EMAIL_DELIVERY_MODE == "webhook" and webhook_url_ready and webhook_token_ready
    development_outbox = EMAIL_DELIVERY_MODE == "outbox" and not IS_VERCEL_RUNTIME
    ready = webhook_ready or development_outbox
    production_ready = webhook_ready

    if webhook_ready:
        reason = "configured"
    elif EMAIL_DELIVERY_MODE == "outbox" and IS_VERCEL_RUNTIME:
        reason = "development_outbox_not_allowed_in_hosted_runtime"
    elif EMAIL_DELIVERY_MODE == "webhook" and not EMAIL_WEBHOOK_URL:
        reason = "webhook_url_missing"
    elif EMAIL_DELIVERY_MODE == "webhook" and not webhook_url_ready:
        reason = "webhook_url_must_use_https"
    elif EMAIL_DELIVERY_MODE == "webhook" and not webhook_token_ready:
        reason = "webhook_token_missing"
    elif EMAIL_DELIVERY_MODE == "disabled":
        reason = "disabled"
    else:
        reason = "unsupported_delivery_mode"

    return {
        "mode": EMAIL_DELIVERY_MODE,
        "ready": ready,
        "production_ready": production_ready,
        "registration_enabled": ready,
        "recovery_enabled": ready,
        "change_email_enabled": ready,
        "reason": reason,
    }


def hosted_transactional_email_ready() -> bool:
    return bool(email_delivery_status()["production_ready"])
