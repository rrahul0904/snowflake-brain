#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory(prefix="snowflake-security-adversarial-")
os.environ["BRAIN_DB"] = str(Path(TEMP.name) / "security.sqlite")
os.environ["ACCOUNT_EMAIL_DELIVERY_MODE"] = "outbox"
os.environ["AUTH_COOKIE_SECURE"] = "false"
os.environ["FORCE_HTTPS"] = "false"
os.environ["SECURITY_RATE_LIMIT_ENABLED"] = "true"
os.environ["BILLING_ENABLED"] = "false"
os.environ["GOOGLE_AUTH_ENABLED"] = "false"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def check(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    try:
        client = TestClient(app)

        # Anonymous users must not reach candidate data or study-runtime modules.
        protected = [
            "/api/account/export",
            "/api/mock/config?track_id=snowpro-core",
            "/api/intelligence/adaptive/readiness?track_id=snowpro-core",
            "/static/views/practice-v26.js",
            "/static/views/credentials-v26.js",
        ]
        for path in protected:
            response = client.get(path)
            check(response.status_code in {401, 403}, f"anonymous access escaped boundary: {path} -> {response.status_code}")

        # Public shell must carry browser hardening headers.
        home = client.get("/")
        check(home.status_code == 200, "public shell failed")
        headers = {key.lower(): value for key, value in home.headers.items()}
        for name in (
            "content-security-policy",
            "x-content-type-options",
            "x-frame-options",
            "referrer-policy",
            "permissions-policy",
        ):
            check(name in headers, f"missing security header: {name}")
        check("frame-ancestors 'none'" in headers["content-security-policy"], "CSP permits framing")
        check(headers["x-frame-options"].upper() == "DENY", "clickjacking header is not DENY")

        # Registration should establish an HttpOnly same-site session.
        registration = client.post(
            "/api/auth/register",
            json={
                "display_name": "Security Candidate",
                "email": "security-candidate@example.com",
                "password": "LongCandidatePassword!123",
            },
        )
        check(registration.status_code == 201, f"registration failed: {registration.text}")
        cookie = registration.headers.get("set-cookie", "").lower()
        check("httponly" in cookie, "session cookie is not HttpOnly")
        check("samesite=lax" in cookie, "session cookie is missing SameSite=Lax")

        # A cookie-authenticated cross-site mutation must be rejected before the route executes.
        cross_site = client.post(
            "/api/account/change-email/request",
            headers={"Origin": "https://evil.example", "Sec-Fetch-Site": "cross-site"},
            json={"new_email": "attacker@example.com"},
        )
        check(cross_site.status_code == 403, f"cross-site mutation not blocked: {cross_site.status_code}")
        detail = cross_site.json().get("detail", {})
        check(detail.get("code") == "cross_site_request_blocked", "wrong cross-site rejection reason")

        # The same authenticated operation from the application origin remains usable.
        same_origin = client.post(
            "/api/account/change-email/request",
            headers={"Origin": "http://testserver", "Sec-Fetch-Site": "same-origin"},
            json={"new_email": "security-candidate-new@example.com"},
        )
        check(same_origin.status_code == 200, f"same-origin mutation unexpectedly blocked: {same_origin.text}")

        # Basic injection-shaped credentials must not bypass authentication or crash the server.
        attacker = TestClient(app)
        injection = attacker.post(
            "/api/auth/login",
            json={"email": "' OR 1=1--@example.com", "password": "not-the-password"},
        )
        check(injection.status_code in {401, 422}, f"injection-shaped login produced unsafe status: {injection.status_code}")

        # Encoded path traversal must never disclose server source code.
        traversal = attacker.get("/static/%2e%2e/app/auth.py")
        check(traversal.status_code != 200, "path traversal returned a source file")
        check("password_digest" not in traversal.text, "path traversal exposed authentication source")

        # Logout revokes the server-side session, not just the browser cookie.
        logout = client.post("/api/auth/logout")
        check(logout.status_code == 200, "logout failed")
        after_logout = client.get("/api/account/export")
        check(after_logout.status_code == 401, "revoked session still accesses account export")

        # Auth abuse must eventually hit the application safety-net limiter.
        limiter = TestClient(app)
        saw_429 = False
        for _ in range(40):
            response = limiter.post(
                "/api/auth/login",
                json={"email": "nobody@example.com", "password": "LongInvalidPassword!123"},
            )
            if response.status_code == 429:
                saw_429 = True
                check(response.headers.get("retry-after"), "rate limit response lacks Retry-After")
                break
        check(saw_429, "authentication rate limit did not trigger")

        print("Security adversarial HTTP checks passed.")
    finally:
        TEMP.cleanup()


if __name__ == "__main__":
    main()
