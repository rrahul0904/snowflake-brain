#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory(prefix="snowflake-auth-content-boundary-")
os.environ["BRAIN_DB"] = str(Path(TEMP.name) / "content-boundary.sqlite")
os.environ["SECURITY_RATE_LIMIT_ENABLED"] = "false"

from fastapi.testclient import TestClient  # noqa: E402
from app.database import run_migrations  # noqa: E402
from app.identity_billing_schema import ensure_identity_billing_schema  # noqa: E402
from app.main import app  # noqa: E402


def check(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    run_migrations()
    ensure_identity_billing_schema()
    client = TestClient(app)

    # Only operational/auth/billing-marketing/activity surfaces are public.
    for path in (
        "/api/health",
        "/api/auth/me",
        "/api/auth/providers",
        "/api/billing/config",
        "/api/activity/globe",
    ):
        response = client.get(path)
        check(response.status_code == 200, f"public endpoint must remain available: {path} -> {response.status_code}")

    # Certification-prep APIs fail closed before a candidate account exists.
    protected = (
        "/api/skills/map",
        "/api/skills/catalog",
        "/api/skills/content-coverage",
        "/api/practice-tests?track_id=snowpro-core",
        "/api/mock/config?track_id=snowpro-core",
        "/api/labs/config",
        "/api/intelligence/readiness?track_id=snowpro-core",
    )
    for path in protected:
        response = client.get(path)
        check(response.status_code == 401, f"anonymous certification content leaked: {path} -> {response.status_code}")
        body = response.json()
        check(body.get("detail", {}).get("code") == "authentication_required", f"wrong denial contract for {path}")
        check(response.headers.get("cache-control") == "private, no-store", f"denied content must not be cached: {path}")

    # A forged/reused-looking cookie cannot bypass the boundary.
    client.cookies.set("snowflake_candidate_session", "forged-session-token")
    forged = client.get("/api/skills/map")
    check(forged.status_code == 401, "forged candidate cookie must not unlock content")
    client.cookies.clear()

    # Creating a real candidate account unlocks the Free-account content layer.
    signup = client.post(
        "/api/auth/register",
        json={
            "display_name": "Content Boundary Candidate",
            "email": "content-boundary@example.com",
            "password": "candidate-password",
        },
    )
    check(signup.status_code == 201, signup.text)
    check(signup.json().get("authenticated") is True, "candidate session created")

    for path in (
        "/api/skills/map",
        "/api/skills/catalog",
        "/api/mock/config?track_id=snowpro-core",
    ):
        response = client.get(path)
        check(response.status_code == 200, f"authenticated Free candidate should reach included content: {path} -> {response.status_code}")
        check(response.headers.get("cache-control") == "private, no-store", f"candidate content must not be shared-cacheable: {path}")

    # The SPA must gate protected routes before importing/rendering their views.
    router = (ROOT / "frontend" / "router-complete.js").read_text(encoding="utf-8")
    check('const publicRoutes=new Set(["#/home","#/membership","#/about","#/changelog","#/privacy"])' in router, "public SPA route allowlist is explicit")
    check("if(!publicRoutes.has(path))" in router and "if(!candidate())" in router, "protected SPA routes require candidate state")
    check("authentication-required" in router, "anonymous deep links render the access gate, not study content")

    home = (ROOT / "frontend" / "views" / "home-v26.js").read_text(encoding="utf-8")
    check("if (account)" in home and "getSkillMap()" in home, "public home does not fetch protected skill content for guests")

    extras = (ROOT / "frontend" / "components" / "home-extras.js").read_text(encoding="utf-8")
    check("No certification content is exposed before login" in extras, "public membership copy states the account boundary")

    print("Authenticated certification content boundary checks passed.")


if __name__ == "__main__":
    main()
