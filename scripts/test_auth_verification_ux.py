#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory(prefix="snowflake-auth-verification-ux-")
os.environ["BRAIN_DB"] = str(Path(TEMP.name) / "auth-verification.sqlite")
os.environ["ACCOUNT_EMAIL_DELIVERY_MODE"] = "outbox"
os.environ["ACCOUNT_EMAIL_ACTION_BASE_URL"] = "http://testserver"
os.environ["AUTH_COOKIE_SECURE"] = "false"
os.environ["FORCE_HTTPS"] = "false"
os.environ["BILLING_ENABLED"] = "false"
os.environ["GOOGLE_AUTH_ENABLED"] = "false"

from fastapi.testclient import TestClient  # noqa: E402

from app.account_lifecycle import development_outbox  # noqa: E402
from app.main import app  # noqa: E402


def token_from_url(url: str) -> str:
    parsed = urlsplit(url)
    fragment_query = parsed.fragment.split("?", 1)[1] if "?" in parsed.fragment else ""
    return parse_qs(fragment_query).get("token", [""])[0]


def check_runtime_verification() -> None:
    client = TestClient(app)
    registered = client.post(
        "/api/auth/register",
        json={
            "display_name": "Verification UX Candidate",
            "email": "verification-ux@example.com",
            "password": "VerificationUX!123",
        },
    )
    assert registered.status_code == 201, registered.text
    payload = registered.json()
    candidate_id = int(payload["candidate"]["id"])
    assert payload["candidate"]["email_verified"] is False
    assert payload["verification_delivery"] == "queued"

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["candidate"]["email_verified"] is False

    outbox = development_outbox(candidate_id, "verify_email")
    assert outbox, "Registration did not create a verification action"
    action_url = str(outbox[0]["action_url"])
    assert action_url.startswith("http://testserver/#/account-action?"), action_url
    assert ".html/" not in action_url, action_url
    token = token_from_url(action_url)
    assert token

    confirmed = client.post("/api/auth/email-verification/confirm", json={"token": token})
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["verified"] is True

    me_after = client.get("/api/auth/me")
    assert me_after.status_code == 200
    assert me_after.json()["candidate"]["email_verified"] is True


def check_frontend_contract() -> None:
    router = (ROOT / "frontend/router-complete.js").read_text(encoding="utf-8")
    candidate_access = (ROOT / "frontend/components/candidate-access.js").read_text(encoding="utf-8")
    account = (ROOT / "frontend/views/account-v26.js").read_text(encoding="utf-8")
    account_action = (ROOT / "frontend/views/account-action-v26.js").read_text(encoding="utf-8")
    css = (ROOT / "frontend/styles/recording-parity-final.css").read_text(encoding="utf-8")
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    prod_env = (ROOT / "deploy/production.env.example").read_text(encoding="utf-8")
    dev = (ROOT / "scripts/dev.sh").read_text(encoding="utf-8")

    assert '"#/account-action":"account-action-v26.js"' in router
    assert '"#/account-action"' in router.split("publicRoutes", 1)[1]
    assert "Forgot password?" in candidate_access
    assert "/api/auth/password-reset/request" in candidate_access
    assert "One quick security step" in candidate_access
    assert 'window.location.assign("/api/auth/google/start")' in candidate_access
    assert "/api/account/email-verification/resend" in account
    assert "Link Google account" in account
    assert "/api/auth/email-verification/confirm" in account_action
    assert "/api/auth/password-reset/confirm" in account_action
    assert ".v26-adaptive-page .v26-learning-command" in css
    assert ".v26-membership-page .v26-plan-grid{grid-template-columns:repeat(3" in css
    assert "ACCOUNT_EMAIL_ACTION_BASE_URL: \"${ACCOUNT_EMAIL_ACTION_BASE_URL:-http://localhost:8010}\"" in compose
    assert "ACCOUNT_EMAIL_ACTION_BASE_URL=https://snowflake-certified.example.com\n" in prod_env
    assert 'source "$ROOT_DIR/.env"' in dev
    assert "Google OAuth is enabled but" in dev


def main() -> None:
    check_runtime_verification()
    check_frontend_contract()
    print("Auth verification and recording UX: PASS")


if __name__ == "__main__":
    main()
