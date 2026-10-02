#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory(prefix="snowflake-public-discovery-")
os.environ["BRAIN_DB"] = str(Path(TEMP.name) / "public-discovery.sqlite")
os.environ["SECURITY_RATE_LIMIT_ENABLED"] = "false"
os.environ["ACCOUNT_EMAIL_DELIVERY_MODE"] = "outbox"
os.environ["BILLING_ENABLED"] = "false"
os.environ["GOOGLE_AUTH_ENABLED"] = "false"
os.environ["APP_BASE_URL"] = "https://snowflakecertificationguide.vercel.app"

from fastapi.testclient import TestClient  # noqa: E402
from app.database import run_migrations  # noqa: E402
from app.main import app  # noqa: E402


def check(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    run_migrations()
    client = TestClient(app)

    index = client.get("/discover")
    check(index.status_code == 200, index.text)
    check("SnowPro certification guides" in index.text, "discovery index title missing")
    check("/discover/snowpro-core" in index.text, "SnowPro Core discovery link missing")
    check("private practice questions" in index.text.lower(), "private-bank discovery boundary missing")
    check("index,follow" in index.text, "discovery index is not explicitly indexable")
    check("content-security-policy" in index.headers, "security headers missing on discovery HTML")

    core = client.get("/discover/snowpro-core")
    check(core.status_code == 200, core.text)
    for token in ("COF-C03", "Source verification:", "Official Snowflake page", "Weighted exam domains"):
        check(token in core.text, f"core discovery page missing verified fact surface: {token}")
    for forbidden in ("correct_json", "options_json", "answer_key", "bank_pool", "private_bank"):
        check(forbidden not in core.text.lower(), f"public discovery leaked private-bank field: {forbidden}")

    unknown = client.get("/discover/not-a-certification")
    check(unknown.status_code == 404, "unknown certification discovery route must return 404")

    sitemap = client.get("/sitemap.xml")
    check(sitemap.status_code == 200, sitemap.text)
    check("/discover/snowpro-core" in sitemap.text, "SnowPro Core missing from sitemap")
    for forbidden in ("#/practice", "/api/", "/questions/", "question-studio"):
        check(forbidden not in sitemap.text, f"sitemap exposed protected/private route: {forbidden}")

    robots = client.get("/robots.txt")
    check(robots.status_code == 200, robots.text)
    check("Disallow: /api/" in robots.text, "robots must keep API out of discovery")
    check("Sitemap: https://snowflakecertificationguide.vercel.app/sitemap.xml" in robots.text, "canonical sitemap declaration missing")

    print("Public certification SEO/discovery boundary: PASS")


if __name__ == "__main__":
    try:
        main()
    finally:
        TEMP.cleanup()
