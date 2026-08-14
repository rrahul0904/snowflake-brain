#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory(prefix="snowflake-google-browser-state-")
os.environ["BRAIN_DB"] = str(Path(TEMP.name) / "browser-state.sqlite")
os.environ["SECURITY_RATE_LIMIT_ENABLED"] = "false"
os.environ["GOOGLE_AUTH_ENABLED"] = "true"
os.environ["GOOGLE_OIDC_CLIENT_ID"] = "google-browser-test.apps.googleusercontent.com"
os.environ["GOOGLE_OIDC_CLIENT_SECRET"] = "google-browser-secret"
os.environ["GOOGLE_OIDC_REDIRECT_URI"] = "http://localhost:8010/api/auth/google/callback"

from fastapi.testclient import TestClient  # noqa: E402
from app.database import run_migrations  # noqa: E402
from app.identity_billing_schema import ensure_identity_billing_schema  # noqa: E402
from app.main import app  # noqa: E402
from app.routers.google_auth import GOOGLE_OAUTH_STATE_COOKIE  # noqa: E402


def check(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    run_migrations()
    ensure_identity_billing_schema()

    origin = TestClient(app)
    started = origin.get("/api/auth/google/start", follow_redirects=False)
    check(started.status_code == 302, started.text)
    location = started.headers.get("location") or ""
    state = (parse_qs(urlparse(location).query).get("state") or [""])[0]
    check(state, "Google start includes state")
    check(origin.cookies.get(GOOGLE_OAUTH_STATE_COOKIE) == state, "state is bound to initiating browser with HttpOnly cookie")
    set_cookie = started.headers.get("set-cookie") or ""
    check("HttpOnly" in set_cookie, "Google state cookie is HttpOnly")
    check("SameSite=lax" in set_cookie or "SameSite=Lax" in set_cookie, "Google state cookie is SameSite=Lax")

    # A different browser can know/copy a valid state value but cannot use the
    # callback because it lacks the initiating browser's transaction cookie.
    other_browser = TestClient(app)
    rejected = other_browser.get(
        "/api/auth/google/callback",
        params={"state": state, "code": "copied-code"},
        follow_redirects=False,
    )
    check(rejected.status_code == 400, "valid-looking callback is rejected in a different browser")
    check("does not match this browser" in rejected.text, "browser-binding rejection is explicit")

    # A mismatched state is rejected even in the originating browser before any
    # token exchange is attempted.
    mismatch = origin.get(
        "/api/auth/google/callback",
        params={"state": "attacker-state", "code": "copied-code"},
        follow_redirects=False,
    )
    check(mismatch.status_code == 400, "mismatched browser state rejected")

    # User-cancel/error returns still require the matching transaction and clear
    # the short-lived state cookie.
    cancelled = origin.get(
        "/api/auth/google/callback",
        params={"state": state, "error": "access_denied"},
        follow_redirects=False,
    )
    check(cancelled.status_code == 302, cancelled.text)
    check("google_auth=cancelled" in (cancelled.headers.get("location") or ""), "matching cancelled transaction returns to app")
    check(origin.cookies.get(GOOGLE_OAUTH_STATE_COOKIE) is None, "OAuth state cookie cleared after completed transaction")

    print("Google OAuth browser-state binding checks passed.")


if __name__ == "__main__":
    main()
