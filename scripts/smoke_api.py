#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("AUTO_INGEST", "false")

from fastapi.testclient import TestClient

from app.main import app
from app.database import run_migrations


CHECKS = [
    ("GET", "/api/summary"),
    ("GET", "/api/tracks"),
    ("GET", "/api/tracks/snowpro-core/courses"),
    ("GET", "/api/courses"),
    ("GET", "/api/practice-tests?track_id=snowpro-core&min_questions=1"),
    ("GET", "/api/questions?track_id=snowpro-core&limit=1"),
    ("GET", "/api/lessons?track_id=snowpro-core&limit=1"),
    ("GET", "/api/search?q=warehouse&limit=1"),
    ("GET", "/api/labs"),
    ("GET", "/api/flashcards"),
    ("GET", "/api/study/goals"),
    ("GET", "/api/study/today"),
    ("GET", "/api/study/content-audit"),
    ("GET", "/api/experience/command-center?track_id=snowpro-core"),
    ("GET", "/api/intelligence/portfolio"),
    ("GET", "/api/intelligence/readiness?track_id=snowpro-core"),
    ("GET", "/api/intelligence/diagnostic?track_id=snowpro-core&count=30"),
    ("GET", "/api/labs?certification=snowpro-core"),
    ("POST", "/api/brain/ask"),
]


def main() -> None:
    run_migrations()
    client = TestClient(app)
    failures: list[str] = []
    for method, path in CHECKS:
        kwargs = {}
        if path == "/api/brain/ask":
            kwargs["json"] = {"question": "Explain RBAC", "context_limit": 3}
        response = client.request(method, path, **kwargs)
        ok = 200 <= response.status_code < 400
        print(f"{method} {path} -> {response.status_code}")
        if not ok:
            failures.append(f"{method} {path} returned {response.status_code}: {response.text[:300]}")
    if failures:
        print("\nFailures:")
        for failure in failures:
            print(f"- {failure}")
        sys.exit(1)


if __name__ == "__main__":
    main()
