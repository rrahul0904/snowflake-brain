#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory(prefix="snowflake-exam-entitlement-concurrency-")
DB_PATH = Path(TEMP.name) / "exam-entitlement-concurrency.sqlite"
os.environ["BRAIN_DB"] = str(DB_PATH)
os.environ["AFFILIATE_RESOURCES_ENABLED"] = "false"

from fastapi import HTTPException  # noqa: E402
from app.database import connect, run_migrations  # noqa: E402
from app.exam_entitlement_reservations import reserve_exam_attempt  # noqa: E402
from app.tier_exam_policy import mock_reset_context  # noqa: E402


def create_candidate(email: str, tier: str, plan_code: str) -> dict:
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO candidate_accounts(
              email, display_name, password_hash, password_salt, password_algorithm, plan
            ) VALUES (?, 'Concurrency Candidate', 'test', 'test', 'pbkdf2_sha256', ?)
            """,
            (email, tier),
        )
        candidate_id = int(cursor.lastrowid)
    return {
        "id": candidate_id,
        "membership": {
            "tier": tier,
            "plan_code": plan_code,
        },
    }


def race(candidate: dict, mode: str, expected_successes: int) -> None:
    reset = mock_reset_context(candidate, mode)

    def attempt(_: int) -> bool:
        try:
            reservation_id = reserve_exam_attempt(candidate, "snowpro-core", mode, reset)
            return reservation_id is not None
        except HTTPException as exc:
            if exc.status_code != 403:
                raise
            return False

    with ThreadPoolExecutor(max_workers=50) as pool:
        futures = [pool.submit(attempt, index) for index in range(50)]
        outcomes = [future.result() for future in as_completed(futures)]

    succeeded = sum(1 for outcome in outcomes if outcome)
    if succeeded != expected_successes:
        raise AssertionError(
            f"{candidate['membership']['plan_code']} {mode}: expected exactly "
            f"{expected_successes} reservations from 50 concurrent attempts, got {succeeded}"
        )

    with connect() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS count
              FROM exam_entitlement_reservations
             WHERE candidate_id=? AND status='reserved'
            """,
            (candidate["id"],),
        ).fetchone()
    stored = int(row["count"] if row else 0)
    if stored != expected_successes:
        raise AssertionError(
            f"{candidate['membership']['plan_code']} {mode}: reservation ledger contains {stored}, "
            f"expected {expected_successes}"
        )


def main() -> None:
    run_migrations()

    free = create_candidate("concurrency-free@example.com", "free", "free")
    race(free, "weekly-mock", 1)

    premium_100 = create_candidate("concurrency-premium100@example.com", "premium", "premium_20")
    race(premium_100, "full-mock", 2)

    premium_250 = create_candidate("concurrency-premium250@example.com", "premium", "premium_40")
    race(premium_250, "full-mock", 4)

    exam_pack = create_candidate("concurrency-pack@example.com", "premium", "exam_pack_35")
    race(exam_pack, "full-mock", 1)

    print("Atomic exam entitlement concurrency checks passed: 1 / 2 / 4 / 1 from 50 simultaneous attempts.")


if __name__ == "__main__":
    main()
