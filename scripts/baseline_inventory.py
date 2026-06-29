#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DEFAULT_DB = ROOT / "data" / "snowflake_brain.sqlite"
DOC_MD = ROOT / "docs" / "BASELINE_INVENTORY.md"
DOC_JSON = ROOT / "docs" / "BASELINE_INVENTORY.json"


TABLE_COUNTS = {
    "tracks": "certification_tracks",
    "courses": "courses",
    "sections": "course_sections",
    "lessons": "lessons",
    "transcript_chunks": "transcript_chunks",
    "practice_tests": "practice_tests",
    "questions": "questions",
    "labs": "lab_exercises",
    "flashcards": "flashcards",
    "study_goals": "study_goals",
    "study_plan_items": "study_plan_items",
}


SMOKE_PATHS = [
    "/api/summary",
    "/api/tracks",
    "/api/tracks/snowpro-core/courses",
    "/api/practice-tests?track_id=snowpro-core&min_questions=1",
    "/api/questions?track_id=snowpro-core&limit=1",
    "/api/lessons?track_id=snowpro-core&limit=1",
    "/api/search?q=warehouse&limit=1",
    "/api/labs",
    "/api/flashcards",
    "/api/study/goals",
    "/api/study/today",
    "/api/study/readiness?track_id=snowpro-core",
    "/api/study/content-audit",
]


def connect(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise SystemExit(f"Database not found: {db_path}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?", (table,)).fetchone()
    return bool(row)


def count_table(conn: sqlite3.Connection, table: str) -> int:
    if not table_exists(conn, table):
        return 0
    return int(conn.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()["count"] or 0)


def collect_db_counts(conn: sqlite3.Connection) -> dict[str, int]:
    counts = {label: count_table(conn, table) for label, table in TABLE_COUNTS.items()}
    if table_exists(conn, "practice_tests"):
        counts["empty_practice_tests"] = int(
            conn.execute("SELECT COUNT(*) AS count FROM practice_tests WHERE COALESCE(question_count, 0) = 0").fetchone()[
                "count"
            ]
            or 0
        )
        counts["non_empty_practice_tests"] = int(
            conn.execute("SELECT COUNT(*) AS count FROM practice_tests WHERE COALESCE(question_count, 0) > 0").fetchone()[
                "count"
            ]
            or 0
        )
    return counts


def collect_frontend_routes() -> list[str]:
    router = ROOT / "frontend" / "router.js"
    if not router.exists():
        return []
    routes: list[str] = []
    for line in router.read_text().splitlines():
        line = line.strip()
        if line.startswith('"#/') or line.startswith("'#/"):
            routes.append(line.split(":", 1)[0].strip(" \"'"))
    return sorted(set(routes))


def collect_backend_routes() -> list[dict[str, Any]]:
    os.environ.setdefault("AUTO_INGEST", "false")
    from app.main import app

    routes = []
    for route in app.routes:
        path = getattr(route, "path", "")
        methods = sorted(getattr(route, "methods", []) or [])
        if path.startswith("/api"):
            routes.append({"path": path, "methods": methods})
    return sorted(routes, key=lambda item: (item["path"], ",".join(item["methods"])))


def smoke_test_paths() -> list[dict[str, Any]]:
    os.environ.setdefault("AUTO_INGEST", "false")
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    results = []
    for path in SMOKE_PATHS:
        try:
            response = client.get(path)
            body = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
            summary = sorted(body.keys()) if isinstance(body, dict) else type(body).__name__
            results.append({"path": path, "status": response.status_code, "shape": summary})
        except Exception as exc:  # pragma: no cover - CLI diagnostic
            results.append({"path": path, "status": "error", "shape": str(exc)})
    return results


def markdown(snapshot: dict[str, Any]) -> str:
    lines = [
        "# Snowflake Brain - Baseline Inventory",
        "",
        f"Generated at: {snapshot['generated_at']}",
        "",
        "## Database Counts",
        "",
        "| Metric | Count |",
        "| --- | ---: |",
    ]
    for key, value in snapshot["counts"].items():
        lines.append(f"| {key} | {value} |")

    lines.extend(["", "## Frontend Routes", ""])
    for route in snapshot["frontend_routes"]:
        lines.append(f"- `{route}`")

    lines.extend(["", "## Backend API Routes", ""])
    for route in snapshot["backend_routes"]:
        lines.append(f"- `{','.join(route['methods'])}` `{route['path']}`")

    lines.extend(["", "## API Smoke Tests", "", "| Path | Status | Response Shape |", "| --- | ---: | --- |"])
    for result in snapshot["smoke_tests"]:
        lines.append(f"| `{result['path']}` | {result['status']} | `{result['shape']}` |")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a Snowflake Brain baseline inventory.")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="SQLite DB path.")
    parser.add_argument("--write", action="store_true", help="Write docs/BASELINE_INVENTORY.md and .json.")
    args = parser.parse_args()

    db_path = Path(args.db)
    with connect(db_path) as conn:
        snapshot = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "db_path": str(db_path),
            "counts": collect_db_counts(conn),
            "frontend_routes": collect_frontend_routes(),
            "backend_routes": collect_backend_routes(),
            "smoke_tests": smoke_test_paths(),
        }

    if args.write:
        DOC_JSON.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
        DOC_MD.write_text(markdown(snapshot), encoding="utf-8")
        print(DOC_MD)
        print(DOC_JSON)
    else:
        print(markdown(snapshot))


if __name__ == "__main__":
    main()
