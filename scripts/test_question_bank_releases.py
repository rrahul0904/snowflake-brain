#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory(prefix="snowflake-bank-release-")
os.environ["BRAIN_DB"] = str(Path(TEMP.name) / "bank-release.sqlite")

from app.database import connect, run_migrations  # noqa: E402
from app.question_bank import import_question_bank_payload  # noqa: E402
from app.question_bank_releases import (  # noqa: E402
    activate_release,
    compare_releases,
    create_release,
    ensure_active_release_baseline,
    filter_rows_to_active_release,
    get_release,
    list_releases,
    promote_release,
    rollback_release,
)
from app.question_versions import ensure_question_version_schema  # noqa: E402
from app.skill_brain import flatten_skills  # noqa: E402


def check(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def question(qid: str) -> dict:
    skill = flatten_skills("snowpro-core")[0]
    return {
        "id": qid,
        "domain_id": skill["domain_id"],
        "task_id": skill["id"],
        "task_code": skill.get("task_code") or "",
        "question_type": "scenario",
        "cognitive_level": "apply",
        "difficulty_band": "applied",
        "bank_pool": "practice",
        "authoring_status": "active",
        "authoring_version": "release-test",
        "question": f"For the controlled release scenario {qid}, which Snowflake choice best satisfies the stated certification requirement?",
        "options": [
            f"Incorrect A for {qid}",
            f"Correct B for {qid}",
            f"Incorrect C for {qid}",
            f"Incorrect D for {qid}",
        ],
        "correct_options": [1],
        "correct_rationale": f"Option B is correct for {qid} because it directly satisfies the controlled release scenario requirement.",
        "distractor_rationales": [
            "This option does not satisfy the scenario requirement.",
            "This is the correct option for the stated requirement.",
            "This option addresses a different Snowflake behavior.",
            "This option introduces an unrelated constraint.",
        ],
        "concepts": ["release-management"],
        "trap_tags": ["release-test"],
        "source_refs": [
            {
                "title": "Snowflake documentation",
                "url": "https://docs.snowflake.com/en/user-guide/intro-key-concepts",
            }
        ],
        "source_verified_at": "2026-08-14",
    }


def bank(ids: list[str], version: str) -> dict:
    return {
        "schema_version": "snowflake-question-bank-v1",
        "bank_version": version,
        "track_id": "snowpro-core",
        "exam_code": "COF-C03",
        "source_verified_at": "2026-08-14",
        "questions": [question(qid) for qid in ids],
    }


def visible_ids() -> set[str]:
    rows = [
        {"id": "release::q1", "bank_pool": "practice"},
        {"id": "release::q2", "bank_pool": "practice"},
        {"id": "release::q3", "bank_pool": "practice"},
        {"id": "canonical::fallback", "source_kind": "canonical"},
    ]
    return {row["id"] for row in filter_rows_to_active_release(rows, "snowpro-core")}


def main() -> None:
    run_migrations()
    ensure_question_version_schema()

    import_question_bank_payload(
        bank(["release::q1", "release::q2"], "release-v1"),
        source_name="release-v1.json",
    )
    baseline = ensure_active_release_baseline("snowpro-core")
    check(baseline and baseline["status"] == "active", "existing bank is bootstrapped once as the active release")
    baseline_key = str(baseline["release_key"])
    check(visible_ids() == {"release::q1", "release::q2", "canonical::fallback"}, "baseline exposes only its managed members plus fallback")

    # Importing a newer source does not alter candidate-visible release state.
    import_question_bank_payload(
        bank(["release::q1", "release::q3"], "release-v2"),
        source_name="release-v2.json",
    )
    check(visible_ids() == {"release::q1", "release::q2", "canonical::fallback"}, "fresh imports remain hidden until explicit activation")

    release_v2 = create_release(
        "2026.08.15-release-v2",
        "snowpro-core",
        question_ids=["release::q1", "release::q3"],
        actor="release-test",
        notes="New source intentionally omits q2 and adds q3.",
    )
    check(release_v2["status"] == "draft" and release_v2["question_count"] == 2, "new release starts as an exact draft snapshot")
    check(visible_ids() == {"release::q1", "release::q2", "canonical::fallback"}, "draft release is never candidate-visible")

    promote_release("2026.08.15-release-v2", "qa_passed", actor="qa-test")
    promote_release("2026.08.15-release-v2", "sme_approved", actor="sme-test")
    staged = promote_release("2026.08.15-release-v2", "staging", actor="release-test")
    check(staged["status"] == "staging", "release follows draft -> QA -> SME -> staging")
    activated = activate_release("2026.08.15-release-v2", actor="release-test")
    check(activated["status"] == "active", "staging release activates")
    check(visible_ids() == {"release::q1", "release::q3", "canonical::fallback"}, "activation adds q3 and retires omitted q2 from candidate selection")

    baseline_after = get_release(baseline_key)
    check(baseline_after["status"] == "retired", "previous active release is retained as retired")
    comparison = compare_releases(baseline_key, "2026.08.15-release-v2")
    check(comparison["added"] == ["release::q3"], "release compare reports added questions")
    check(comparison["removed"] == ["release::q2"], "release compare reports removed questions")
    check(comparison["changed"] == [], "unchanged logical question content is not spuriously versioned by a new source filename")

    restored = rollback_release(baseline_key, actor="release-test")
    check(restored["status"] == "active", "retired release can be rolled back atomically")
    check(visible_ids() == {"release::q1", "release::q2", "canonical::fallback"}, "rollback restores exact prior candidate membership")
    check(get_release("2026.08.15-release-v2")["status"] == "retired", "rollback retires the replaced release")

    releases = list_releases("snowpro-core")
    check(sum(1 for row in releases if row["status"] == "active") == 1, "database permits exactly one active release per track")
    with connect() as conn:
        audit_count = int(conn.execute("SELECT COUNT(*) AS count FROM question_bank_release_events").fetchone()["count"])
    check(audit_count >= 8, "release lifecycle writes an audit trail")

    print("Question-bank release create/promote/activate/compare/rollback gating checks passed.")


if __name__ == "__main__":
    main()
