from __future__ import annotations

import os
from typing import Any

from .config import IS_VERCEL_RUNTIME


EMAIL_DELIVERY_MODE = os.getenv("ACCOUNT_EMAIL_DELIVERY_MODE", "outbox").strip().lower() or "outbox"
EMAIL_WEBHOOK_URL = os.getenv("ACCOUNT_EMAIL_WEBHOOK_URL", "").strip()


def email_delivery_status() -> dict[str, Any]:
    """Return non-secret account-email capability state.

    The development outbox is intentionally useful for local/CI verification,
    but it is not a transactional mail provider and must never be advertised as
    production-ready on hosted Vercel runtimes.
    """

    webhook_ready = EMAIL_DELIVERY_MODE == "webhook" and bool(EMAIL_WEBHOOK_URL)
    development_outbox = EMAIL_DELIVERY_MODE == "outbox" and not IS_VERCEL_RUNTIME
    ready = webhook_ready or development_outbox
    production_ready = webhook_ready

    if webhook_ready:
        reason = "configured"
    elif EMAIL_DELIVERY_MODE == "outbox" and IS_VERCEL_RUNTIME:
        reason = "development_outbox_not_allowed_in_hosted_runtime"
    elif EMAIL_DELIVERY_MODE == "webhook":
        reason = "webhook_url_missing"
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
