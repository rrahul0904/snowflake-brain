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
    ("GET", "/api/study/readiness?track_id=snowpro-core"),
    ("GET", "/api/study/content-audit"),
]


def main() -> None:
    client = TestClient(app)
    failures: list[str] = []
    for method, path in CHECKS:
        response = client.request(method, path)
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
