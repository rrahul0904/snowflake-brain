#!/usr/bin/env python3
"""Read-only production question-bank inventory evidence.

The report contains counts only. It never selects question wording, options,
answers, explanations, source references, or private payload content.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import DATABASE_BACKEND  # noqa: E402
from app.database import connect  # noqa: E402


ARTIFACT = ROOT / "artifacts" / "production-bank-inventory.json"
TRACK_ID = os.environ.get("SECURITY_TRACK_ID", "snowpro-core")
REQUIRE_ACTIVE_BANK = os.environ.get("REQUIRE_ACTIVE_BANK", "false").strip().lower() in {"1", "true", "yes", "on"}
EXPECTED_ACTIVE_QUESTION_COUNT = max(0, int(os.environ.get("EXPECTED_ACTIVE_QUESTION_COUNT", "0")))
KNOWN_POOLS = ("free", "practice", "diagnostic", "mock_reserved")
EXPECTED_POOL_COUNTS = {
    "free": max(0, int(os.environ.get("EXPECTED_FREE_QUESTION_COUNT", "0"))),
    "practice": max(0, int(os.environ.get("EXPECTED_PRACTICE_QUESTION_COUNT", "0"))),
    "diagnostic": max(0, int(os.environ.get("EXPECTED_DIAGNOSTIC_QUESTION_COUNT", "0"))),
    "mock_reserved": max(0, int(os.environ.get("EXPECTED_MOCK_RESERVED_QUESTION_COUNT", "0"))),
}


def scalar(conn, statement: str, params: tuple = ()) -> int:
    row = conn.execute(statement, params).fetchone()
    if not row:
        return 0
    value = next(iter(dict(row).values()))
    return int(value or 0)


def main() -> None:
    if DATABASE_BACKEND != "postgresql":
        raise SystemExit("Production bank inventory must use the managed PostgreSQL database")

    with connect() as conn:
        total_questions = scalar(conn, "SELECT COUNT(*) AS n FROM questions WHERE track_id=?", (TRACK_ID,))
        active_release_row = conn.execute(
            """
            SELECT id, question_count
            FROM question_bank_releases
            WHERE track_id=? AND status='active'
            ORDER BY activated_at DESC, id DESC
            LIMIT 1
            """,
            (TRACK_ID,),
        ).fetchone()
        active_release_id = int(active_release_row["id"]) if active_release_row else None
        declared_release_count = int(active_release_row["question_count"] or 0) if active_release_row else 0
        active_release_questions = 0
        pool_counts = {pool: 0 for pool in KNOWN_POOLS}
        if active_release_id is not None:
            active_release_questions = scalar(
                conn,
                "SELECT COUNT(*) AS n FROM question_bank_release_questions WHERE release_id=?",
                (active_release_id,),
            )
            rows = conn.execute(
                """
                SELECT COALESCE(m.bank_pool,'unclassified') AS bank_pool, COUNT(*) AS n
                FROM question_bank_release_questions rq
                LEFT JOIN question_bank_metadata m ON m.question_id=rq.question_id
                WHERE rq.release_id=?
                GROUP BY COALESCE(m.bank_pool,'unclassified')
                ORDER BY bank_pool
                """,
                (active_release_id,),
            ).fetchall()
            for row in rows:
                pool_counts[str(row["bank_pool"])] = int(row["n"] or 0)

    findings: list[str] = []
    if REQUIRE_ACTIVE_BANK and active_release_id is None:
        findings.append("active_release_missing")
    if REQUIRE_ACTIVE_BANK and active_release_questions <= 0:
        findings.append("active_release_empty")
    if declared_release_count and active_release_questions != declared_release_count:
        findings.append("active_release_declared_count_mismatch")
    if EXPECTED_ACTIVE_QUESTION_COUNT and active_release_questions != EXPECTED_ACTIVE_QUESTION_COUNT:
        findings.append("active_release_expected_count_mismatch")

    unexpected_pools = sorted(set(pool_counts) - set(KNOWN_POOLS))
    if unexpected_pools:
        findings.append("active_release_unexpected_pool")
    for pool, expected_count in EXPECTED_POOL_COUNTS.items():
        if expected_count and int(pool_counts.get(pool, 0)) != expected_count:
            findings.append(f"active_release_{pool}_expected_count_mismatch")
    if EXPECTED_ACTIVE_QUESTION_COUNT and any(EXPECTED_POOL_COUNTS.values()):
        expected_pool_total = sum(EXPECTED_POOL_COUNTS.values())
        if expected_pool_total != EXPECTED_ACTIVE_QUESTION_COUNT:
            findings.append("configured_expected_pool_total_mismatch")
        if sum(int(pool_counts.get(pool, 0)) for pool in KNOWN_POOLS) != active_release_questions:
            findings.append("active_release_pool_total_mismatch")

    payload = {
        "status": "pass" if not findings else "fail",
        "track_id": TRACK_ID,
        "active_release_present": active_release_id is not None,
        "database_question_count": total_questions,
        "active_release_question_count": active_release_questions,
        "active_release_declared_question_count": declared_release_count,
        "pool_counts": pool_counts,
        "expected_active_question_count": EXPECTED_ACTIVE_QUESTION_COUNT,
        "expected_pool_counts": EXPECTED_POOL_COUNTS,
        "finding_count": len(findings),
        "findings": findings,
    }
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    if findings:
        raise SystemExit("Production question-bank inventory does not satisfy the release contract")


if __name__ == "__main__":
    main()
