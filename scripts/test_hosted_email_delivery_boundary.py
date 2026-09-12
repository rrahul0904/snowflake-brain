#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def probe(**overrides: str) -> dict:
    env = os.environ.copy()
    for key in (
        "VERCEL",
        "VERCEL_ENV",
        "VERCEL_GIT_COMMIT_SHA",
        "DATABASE_URL",
        "AUTH_COOKIE_SECURE",
        "FORCE_HTTPS",
        "SECURITY_RATE_LIMIT_ENABLED",
        "APP_BASE_URL",
        "ACCOUNT_EMAIL_DELIVERY_MODE",
        "ACCOUNT_EMAIL_WEBHOOK_URL",
        "ACCOUNT_EMAIL_WEBHOOK_TOKEN",
    ):
        env.pop(key, None)
    env.update(overrides)
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import json; from app.email_delivery import email_delivery_status; print(json.dumps(email_delivery_status()))",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return json.loads(result.stdout.strip().splitlines()[-1])


def hosted_env(**overrides: str) -> dict[str, str]:
    env = {
        "VERCEL": "1",
        "VERCEL_ENV": "production",
        "VERCEL_GIT_COMMIT_SHA": "a" * 40,
        "DATABASE_URL": "postgresql://runtime:secret@example.invalid/app",
        "AUTH_COOKIE_SECURE": "true",
        "FORCE_HTTPS": "true",
        "SECURITY_RATE_LIMIT_ENABLED": "true",
        "APP_BASE_URL": "https://snowflakecertificationguide.vercel.app",
    }
    env.update(overrides)
    return env


def main() -> None:
    local = probe(ACCOUNT_EMAIL_DELIVERY_MODE="outbox")
    assert local["ready"] is True
    assert local["production_ready"] is False
    assert local["registration_enabled"] is True
    assert local["recovery_enabled"] is True

    hosted_outbox = probe(**hosted_env(ACCOUNT_EMAIL_DELIVERY_MODE="outbox"))
    assert hosted_outbox["ready"] is False
    assert hosted_outbox["production_ready"] is False
    assert hosted_outbox["registration_enabled"] is False
    assert hosted_outbox["recovery_enabled"] is False
    assert hosted_outbox["change_email_enabled"] is False
    assert hosted_outbox["reason"] == "development_outbox_not_allowed_in_hosted_runtime"

    hosted_disabled = probe(**hosted_env(ACCOUNT_EMAIL_DELIVERY_MODE="disabled"))
    assert hosted_disabled["ready"] is False
    assert hosted_disabled["reason"] == "disabled"

    hosted_missing_webhook = probe(**hosted_env(ACCOUNT_EMAIL_DELIVERY_MODE="webhook"))
    assert hosted_missing_webhook["ready"] is False
    assert hosted_missing_webhook["reason"] == "webhook_url_missing"

    hosted_insecure_webhook = probe(
        **hosted_env(
            ACCOUNT_EMAIL_DELIVERY_MODE="webhook",
            ACCOUNT_EMAIL_WEBHOOK_URL="http://mailer.example.com/account-actions",
            ACCOUNT_EMAIL_WEBHOOK_TOKEN="secret-token",
        )
    )
    assert hosted_insecure_webhook["ready"] is False
    assert hosted_insecure_webhook["reason"] == "webhook_url_must_use_https"

    hosted_missing_token = probe(
        **hosted_env(
            ACCOUNT_EMAIL_DELIVERY_MODE="webhook",
            ACCOUNT_EMAIL_WEBHOOK_URL="https://mailer.example.com/account-actions",
        )
    )
    assert hosted_missing_token["ready"] is False
    assert hosted_missing_token["production_ready"] is False
    assert hosted_missing_token["registration_enabled"] is False
    assert hosted_missing_token["reason"] == "webhook_token_missing"

    hosted_webhook = probe(
        **hosted_env(
            ACCOUNT_EMAIL_DELIVERY_MODE="webhook",
            ACCOUNT_EMAIL_WEBHOOK_URL="https://mailer.example.com/account-actions",
            ACCOUNT_EMAIL_WEBHOOK_TOKEN="secret-token",
        )
    )
    assert hosted_webhook["ready"] is True
    assert hosted_webhook["production_ready"] is True
    assert hosted_webhook["registration_enabled"] is True
    assert hosted_webhook["recovery_enabled"] is True
    assert hosted_webhook["change_email_enabled"] is True
    assert hosted_webhook["reason"] == "configured"

    auth_router = (ROOT / "app/routers/auth.py").read_text(encoding="utf-8")
    account_router = (ROOT / "app/routers/account.py").read_text(encoding="utf-8")
    candidate_access = (ROOT / "frontend/components/candidate-access.js").read_text(encoding="utf-8")
    account_view = (ROOT / "frontend/views/account-v26.js").read_text(encoding="utf-8")
    account_management = (ROOT / "frontend/account-management.js").read_text(encoding="utf-8")

    assert '"password": _password_capabilities()' in auth_router
    assert "_require_email_registration()" in auth_router
    assert "_require_transactional_email(\"recovery_enabled\")" in account_router
    assert "config.password?.registration_enabled === false" in candidate_access
    assert "config.password?.recovery_enabled === false" in candidate_access
    assert "emailActionsAvailable" in account_view
    assert 'method: "DELETE"' in account_management
    assert "/api/auth/sessions/${encodeURIComponent(session.id)}" in account_management
    assert '/api/auth/sessions/revoke"' not in account_management

    print("Hosted transactional email boundary: PASS")


if __name__ == "__main__":
    main()
