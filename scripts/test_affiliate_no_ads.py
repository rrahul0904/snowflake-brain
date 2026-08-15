#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory(prefix="snowflake-affiliate-test-")
os.environ["BRAIN_DB"] = str(Path(TEMP.name) / "affiliate.sqlite")
os.environ["AFFILIATE_RESOURCES_ENABLED"] = "true"
os.environ["AMAZON_ASSOCIATE_TAG"] = "snowflake-test-20"

from fastapi.testclient import TestClient  # noqa: E402
from app.database import run_migrations  # noqa: E402
from app.main import app  # noqa: E402


def check(value: object, message: str) -> None:
    if not value:
        raise AssertionError(message)


def main() -> None:
    run_migrations()
    guest = TestClient(app)
    check(guest.get("/api/resources/affiliate").status_code == 401, "affiliate recommendations are authenticated candidate content")

    client = TestClient(app)
    registered = client.post(
        "/api/auth/register",
        json={"display_name": "Affiliate Candidate", "email": "affiliate@example.com", "password": "candidate-password"},
    )
    check(registered.status_code == 201, registered.text)
    response = client.get("/api/resources/affiliate")
    check(response.status_code == 200, response.text)
    payload = response.json()
    check(payload["enabled"] is True and len(payload["books"]) >= 3, "curated books enabled when Associates tag is configured")
    check(payload["disclosure"] == "As an Amazon Associate I earn from qualifying purchases.", "Amazon Associates site disclosure is present")
    check("commission" in payload["commission_disclosure"].lower(), "commission relationship is stated clearly")
    for book in payload["books"]:
        check(book["url"].startswith("https://www.amazon.com/dp/"), "affiliate link goes directly to Amazon product detail")
        check("tag=snowflake-test-20" in book["url"], "Amazon Associates tag is attached server-side")
        check(book["link_disclosure"] == "Paid link", "each monetized link has a nearby paid-link disclosure")
        check("price" not in book and "rating" not in book and "reviews" not in book, "no stale Amazon price/rating data is copied into product")

    forbidden = [
        "googlesyndication",
        "doubleclick.net",
        "googleadservices",
        "adsbygoogle",
        "prebid",
        "taboola",
        "outbrain",
        "adroll",
        "fbevents.js",
    ]
    frontend_text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore").lower()
        for path in (ROOT / "frontend").rglob("*")
        if path.is_file() and path.suffix.lower() in {".js", ".html", ".css"}
    )
    for token in forbidden:
        check(token not in frontend_text, f"no advertising network/SDK token allowed in frontend: {token}")
    check("rel=\"sponsored noopener noreferrer\"" in (ROOT / "frontend" / "affiliate-resources.js").read_text(encoding="utf-8"), "affiliate links use sponsored relationship semantics")

    print("Affiliate disclosure and no-ad-network checks passed.")


if __name__ == "__main__":
    main()
