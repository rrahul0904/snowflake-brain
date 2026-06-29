#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "snowflake_brain.sqlite"
BASELINE_JSON = ROOT / "docs" / "BASELINE_INVENTORY.json"


def count(conn: sqlite3.Connection, sql: str) -> int:
    return int(conn.execute(sql).fetchone()[0] or 0)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fail if question/test counts drop below baseline.")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--baseline", default=str(BASELINE_JSON))
    args = parser.parse_args()

    db_path = Path(args.db)
    baseline_path = Path(args.baseline)
    if not db_path.exists():
        raise SystemExit(f"Database not found: {db_path}")
    if not baseline_path.exists():
        raise SystemExit(f"Baseline not found: {baseline_path}. Run scripts/baseline_inventory.py --write first.")

    baseline = json.loads(baseline_path.read_text())
    expected = baseline.get("counts", {})

    with sqlite3.connect(db_path) as conn:
        actual = {
            "questions": count(conn, "SELECT COUNT(*) FROM questions"),
            "practice_tests": count(conn, "SELECT COUNT(*) FROM practice_tests"),
            "non_empty_practice_tests": count(
                conn,
                "SELECT COUNT(*) FROM practice_tests WHERE COALESCE(question_count, 0) > 0",
            ),
            "empty_practice_tests": count(
                conn,
                "SELECT COUNT(*) FROM practice_tests WHERE COALESCE(question_count, 0) = 0",
            ),
        }

    failures = []
    for key, value in actual.items():
        baseline_value = int(expected.get(key, 0) or 0)
        print(f"{key}: actual={value} baseline={baseline_value}")
        if value < baseline_value:
            failures.append(f"{key} dropped from {baseline_value} to {value}")

    if failures:
        print("Question count check failed:")
        for failure in failures:
            print(f"- {failure}")
        sys.exit(1)
    print("Question count check passed.")


if __name__ == "__main__":
    main()
