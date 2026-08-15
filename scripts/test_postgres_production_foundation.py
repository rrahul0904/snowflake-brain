#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

if not os.getenv("DATABASE_URL", "").lower().startswith(("postgresql://", "postgres://")):
    raise SystemExit("DATABASE_URL must point to PostgreSQL for this regression")

from fastapi import HTTPException  # noqa: E402
from app.auth import create_candidate  # noqa: E402
from app.config import DATABASE_BACKEND  # noqa: E402
from app.database import connect, database_health, run_migrations  # noqa: E402
from app.entitlements import reserve_daily_questions  # noqa: E402
from app.identity_billing_schema import ensure_identity_billing_schema  # noqa: E402
from app.learning_intelligence import ensure_learning_intelligence_schema, record_learning_review  # noqa: E402
from app.question_bank_releases import (  # noqa: E402
    activate_release,
    create_release,
    ensure_question_bank_release_schema,
    promote_release,
)
from app.question_versions import ensure_question_version_schema  # noqa: E402


def seed_question(candidate_id: int) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO questions(
              id,track_id,test_title,question,options_json,correct_json,explanation,
              source_path,source_kind,assessment_type,tags,difficulty,multiple,question_position
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                "pg-foundation-q1",
                "snowpro-core",
                "PostgreSQL foundation",
                "Which persistence backend is active for this production foundation regression?",
                '["SQLite","PostgreSQL","Browser storage"]',
                "[1]",
                "The production foundation regression is intentionally executing against PostgreSQL.",
                "private://postgres-foundation",
                "private_bank",
                "bank_standard_mcq",
                '["postgres-foundation"]',
                "medium",
                0,
                1,
            ),
        )
        conn.execute(
            """
            INSERT INTO question_bank_metadata(
              question_id,certification_id,exam_version,domain_id,task_id,task_code,
              question_type,cognitive_level,difficulty_band,bank_pool,authoring_status,
              authoring_version,concepts_json,trap_tags_json,distractor_rationales_json,
              source_refs_json,source_verified_at,content_hash
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                "pg-foundation-q1",
                "snowpro-core",
                "COF-C03",
                "features-architecture",
                "snowflake-architecture",
                "PG-FOUNDATION",
                "standard_mcq",
                "apply",
                "applied",
                "practice",
                "active",
                "pg-foundation-v1",
                '["production persistence"]',
                "[]",
                "[]",
                '[{"url":"https://docs.snowflake.com/","title":"Snowflake documentation"}]',
                "2026-08-15",
                "pg-foundation-hash",
            ),
        )
        version = conn.execute(
            "SELECT id,version_number FROM question_versions WHERE question_id=?",
            ("pg-foundation-q1",),
        ).fetchone()
        if not version or int(version["version_number"]) != 1:
            raise AssertionError("PostgreSQL question-version insert trigger did not create version 1")

        conn.execute(
            """
            INSERT INTO question_attempts(
              question_id,selected,correct,mode,candidate_id,response_time_ms,confidence
            ) VALUES (?,?,?,?,?,?,?)
            """,
            ("pg-foundation-q1", "[0]", 0, "drill", candidate_id, 1500, 4),
        )
        record_learning_review(
            conn,
            candidate_id,
            "pg-foundation-q1",
            correct=False,
            confidence=4,
            mode="drill",
            response_time_ms=1500,
            selected=[0],
        )


def check_release() -> None:
    release = create_release(
        "pg-foundation-release",
        "snowpro-core",
        question_ids=["pg-foundation-q1"],
        actor="postgres-regression",
    )
    if release["status"] != "draft":
        raise AssertionError("release did not begin in draft")
    promote_release("pg-foundation-release", "qa_passed", actor="postgres-regression")
    promote_release("pg-foundation-release", "sme_approved", actor="postgres-regression")
    promote_release("pg-foundation-release", "staging", actor="postgres-regression")
    active = activate_release("pg-foundation-release", actor="postgres-regression")
    if active["status"] != "active":
        raise AssertionError("PostgreSQL release activation failed")


def check_daily_quota_race(candidate: dict) -> None:
    membership = candidate["membership"]

    def reserve(_: int) -> bool:
        try:
            reserve_daily_questions(candidate["id"], membership, 1)
            return True
        except HTTPException as exc:
            if exc.status_code != 403:
                raise
            return False

    with ThreadPoolExecutor(max_workers=30) as pool:
        outcomes = [future.result() for future in as_completed([pool.submit(reserve, i) for i in range(30)])]
    if sum(outcomes) != 20:
        raise AssertionError(f"Free daily quota race admitted {sum(outcomes)} requests; expected exactly 20")
    with connect() as conn:
        row = conn.execute(
            "SELECT questions_consumed FROM candidate_daily_question_usage WHERE candidate_id=?",
            (candidate["id"],),
        ).fetchone()
    if not row or int(row["questions_consumed"]) != 20:
        raise AssertionError("PostgreSQL daily quota ledger drifted under concurrency")


def main() -> None:
    if DATABASE_BACKEND != "postgresql":
        raise AssertionError(f"Expected PostgreSQL backend, got {DATABASE_BACKEND}")

    # Migration runner must be idempotent and all additive compatibility
    # boundaries must accept the native PostgreSQL schema.
    run_migrations()
    run_migrations()
    ensure_identity_billing_schema()
    ensure_question_version_schema()
    ensure_question_bank_release_schema()
    ensure_learning_intelligence_schema()

    health = database_health()
    if health.get("status") != "ok" or health.get("backend") != "postgresql":
        raise AssertionError(f"Unexpected database health: {health}")

    candidate = create_candidate("PostgreSQL Candidate", "postgres-foundation@example.com", "StrongPassword!234")
    seed_question(int(candidate["id"]))
    check_release()
    check_daily_quota_race(candidate)

    with connect() as conn:
        migrations = int(conn.execute("SELECT COUNT(*) AS n FROM schema_migrations").fetchone()["n"])
        if migrations < 10:
            raise AssertionError(f"Expected versioned PostgreSQL migration history, found only {migrations} rows")
        srs = conn.execute(
            "SELECT lapses,due_at FROM candidate_srs_state WHERE candidate_id=? AND question_id=?",
            (candidate["id"], "pg-foundation-q1"),
        ).fetchone()
        if not srs or int(srs["lapses"]) < 1:
            raise AssertionError("Candidate learning state did not persist on PostgreSQL")

    print("PostgreSQL production foundation: PASS (migrations, pool health, versions, releases, learning state, quota concurrency)")


if __name__ == "__main__":
    main()
