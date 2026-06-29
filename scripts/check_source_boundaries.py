#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "snowflake_brain.sqlite"


CHECKS = {
    "lessons_missing_course": """
        SELECT COUNT(*) AS count
        FROM lessons l
        LEFT JOIN courses c ON c.id = l.course_id
        WHERE c.id IS NULL
    """,
    "questions_missing_course": """
        SELECT COUNT(*) AS count
        FROM questions q
        LEFT JOIN courses c ON c.id = q.course_id
        WHERE q.course_id IS NOT NULL AND c.id IS NULL
    """,
    "questions_missing_practice_test": """
        SELECT COUNT(*) AS count
        FROM questions q
        LEFT JOIN practice_tests pt ON pt.id = q.test_id
        WHERE COALESCE(q.test_id, '') <> '' AND pt.id IS NULL
    """,
    "practice_tests_course_track_mismatch": """
        SELECT COUNT(*) AS count
        FROM practice_tests pt
        JOIN courses c ON c.id = pt.course_id
        WHERE COALESCE(pt.track_id, '') <> '' AND COALESCE(c.track_id, '') <> '' AND pt.track_id <> c.track_id
    """,
    "question_test_course_mismatch": """
        SELECT COUNT(*) AS count
        FROM questions q
        JOIN practice_tests pt ON pt.id = q.test_id
        WHERE COALESCE(q.course_id, '') <> '' AND COALESCE(pt.course_id, '') <> '' AND q.course_id <> pt.course_id
    """,
    "transcript_chunks_missing_lesson": """
        SELECT COUNT(*) AS count
        FROM transcript_chunks tc
        LEFT JOIN lessons l ON l.id = tc.lesson_id
        WHERE l.id IS NULL
    """,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Check source boundary integrity in the indexed DB.")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        raise SystemExit(f"Database not found: {db_path}")

    failures: list[str] = []
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        for label, sql in CHECKS.items():
            count = int(conn.execute(sql).fetchone()["count"] or 0)
            print(f"{label}: {count}")
            if count:
                failures.append(f"{label}={count}")

    if failures:
        print("Source boundary check failed:")
        for failure in failures:
            print(f"- {failure}")
        sys.exit(1)
    print("Source boundary check passed.")


if __name__ == "__main__":
    main()

