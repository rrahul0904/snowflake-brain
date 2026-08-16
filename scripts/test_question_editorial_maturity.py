#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory(prefix="snowflake-editorial-maturity-")
os.environ["BRAIN_DB"] = str(Path(TEMP.name) / "editorial.sqlite")

from app.config import DATABASE_BACKEND  # noqa: E402
from app.database import connect, run_migrations  # noqa: E402
from app.question_bank import import_question_bank_payload  # noqa: E402
from app.question_bank_releases import (  # noqa: E402
    activate_release,
    create_release,
    ensure_question_bank_release_schema,
    get_release,
    promote_release,
)
from app.question_editorial import (  # noqa: E402
    EditorialError,
    bank_health,
    ensure_question_editorial_schema,
    question_status,
    release_editorial_report,
    review_question,
    run_qa,
)
from app.question_editorial_policy import (  # noqa: E402
    ensure_question_editorial_policy_schema,
    set_editorial_policy,
)
from app.question_versions import ensure_question_version_schema  # noqa: E402
from app.skill_brain import flatten_skills  # noqa: E402


def seed_questions() -> None:
    skill = flatten_skills("snowpro-core")[0]
    fixtures = [
        (
            "editorial-q1",
            "A data engineering team needs independent compute capacity for concurrent analytical queries. Which Snowflake object should the team configure for that compute workload?",
            "A virtual warehouse supplies the compute resources used to execute Snowflake queries. Storage remains independently managed, so the warehouse is the relevant compute object for this requirement.",
            [0],
            "applied",
        ),
        (
            "editorial-q2",
            "A platform team wants to place credit-consumption controls around compute resources without changing the persisted database data. Which Snowflake object is designed for monitoring that consumption?",
            "A resource monitor tracks and controls credit usage for supported compute resources. It is separate from the database storage layer and from network access controls.",
            [3],
            "exam",
        ),
    ]
    questions = []
    for question_id, stem, rationale, correct, difficulty_band in fixtures:
        questions.append(
            {
                "id": question_id,
                "domain_id": skill["domain_id"],
                "task_id": skill["id"],
                "task_code": skill.get("task_code") or "",
                "question_type": "scenario",
                "cognitive_level": "apply",
                "difficulty_band": difficulty_band,
                "bank_pool": "practice",
                "authoring_status": "active",
                "authoring_version": "editorial-test",
                "question": stem,
                "options": ["Virtual warehouse", "Database storage layer", "Network policy", "Resource monitor"],
                "correct_options": correct,
                "correct_rationale": rationale,
                "distractor_rationales": [
                    "This choice does not satisfy the stated requirement.",
                    "This choice addresses persisted storage rather than the requested compute or monitoring behavior.",
                    "This choice controls network access rather than the requested compute or monitoring behavior.",
                    "This choice is relevant only when the requirement is credit monitoring or control.",
                ],
                "concepts": ["architecture", "compute"],
                "trap_tags": ["editorial-test"],
                "source_refs": [
                    {
                        "title": "Snowflake documentation",
                        "url": "https://docs.snowflake.com/en/user-guide/intro-key-concepts",
                    }
                ],
                "source_verified_at": "2026-08-15",
            }
        )
    import_question_bank_payload(
        {
            "schema_version": "snowflake-question-bank-v1",
            "bank_version": "editorial-test",
            "track_id": "snowpro-core",
            "exam_code": "COF-C03",
            "source_verified_at": "2026-08-15",
            "questions": questions,
        },
        source_name="editorial-regression.json",
    )


def main() -> None:
    try:
        run_migrations()
        ensure_question_version_schema()
        ensure_question_bank_release_schema()
        ensure_question_editorial_schema()
        ensure_question_editorial_policy_schema()
        seed_questions()

        create_release(
            "editorial-release-001",
            "snowpro-core",
            question_ids=["editorial-q1", "editorial-q2"],
            actor="editorial-test",
            notes="Editorial regression release",
        )

        qa = run_qa("snowpro-core")
        assert qa["questions"] == 2
        assert qa["failed"] == 0, qa
        assert qa["blockers"] == 0, qa
        for question_id in ("editorial-q1", "editorial-q2"):
            state = question_status(question_id)
            assert state["qa_status"] == "passed", state
            assert state["qa_current"] is True, state
            assert state["content_review_status"] == "pending"
            assert state["sme_review_status"] == "pending"

        report = release_editorial_report("editorial-release-001")
        assert report["qa_pct"] == 100.0
        assert report["content_approved_pct"] == 0.0
        assert report["sme_approved_pct"] == 0.0
        assert report["gate_pass"] is False

        try:
            review_question("editorial-q1", "content", "approved", "")
        except EditorialError as exc:
            assert "human" in str(exc).lower() or "actor" in str(exc).lower()
        else:
            raise AssertionError("Content review accepted an empty actor")
        try:
            review_question("editorial-q1", "sme", "approved", "sme-one")
        except EditorialError as exc:
            assert "content review" in str(exc).lower()
        else:
            raise AssertionError("SME approval bypassed content review")

        for question_id in ("editorial-q1", "editorial-q2"):
            review_question(
                question_id,
                "content",
                "approved",
                "content-reviewer-one",
                notes="Stem, options, rationale and distractors reviewed.",
            )
            review_question(
                question_id,
                "sme",
                "approved",
                "snowflake-sme-one",
                notes="Technical correctness approved for this immutable version.",
            )

        approved = release_editorial_report("editorial-release-001")
        assert approved["gate_pass"] is True, approved
        assert approved["content_approved_pct"] == 100.0
        assert approved["sme_approved_pct"] == 100.0

        promote_release("editorial-release-001", "qa_passed", actor="editorial-test")
        promote_release("editorial-release-001", "sme_approved", actor="editorial-test")
        promote_release("editorial-release-001", "staging", actor="editorial-test")

        policy = set_editorial_policy(
            "snowpro-core",
            enforcement_enabled=True,
            minimum_qa_score=70.0,
            require_content_review=True,
            require_sme_review=True,
            actor="editorial-admin",
            release_key="editorial-release-001",
        )
        assert int(policy["enforcement_enabled"]) == 1
        activate_release("editorial-release-001", actor="editorial-test")
        assert get_release("editorial-release-001")["status"] == "active"

        create_release(
            "editorial-release-002",
            "snowpro-core",
            question_ids=["editorial-q1", "editorial-q2"],
            actor="editorial-test",
            notes="Version-bound approval gate regression",
        )
        with connect() as conn:
            release_item = conn.execute(
                """
                SELECT item.question_version_id
                  FROM question_bank_release_questions item
                  JOIN question_bank_releases rel ON rel.id=item.release_id
                 WHERE rel.release_key='editorial-release-002' AND item.question_id='editorial-q1'
                """
            ).fetchone()
            assert release_item and int(release_item["question_version_id"]) > 0
            conn.execute(
                "UPDATE question_editorial_state SET sme_review_question_version_id=NULL WHERE question_id='editorial-q1'"
            )

        stale = release_editorial_report("editorial-release-002")
        assert stale["gate_pass"] is False
        assert any(item["question_id"] == "editorial-q1" and item["stage"] == "sme_review" for item in stale["violations"])
        try:
            promote_release("editorial-release-002", "qa_passed", actor="editorial-test")
        except Exception:
            pass
        else:
            try:
                promote_release("editorial-release-002", "sme_approved", actor="editorial-test")
            except Exception as exc:
                assert "editorial" in str(exc).lower() or "integrity" in type(exc).__name__.lower()
            else:
                raise AssertionError("Editorial release gate accepted stale SME approval")

        review_question("editorial-q1", "sme", "approved", "snowflake-sme-two", notes="Reconfirmed exact current version.")
        repaired = release_editorial_report("editorial-release-002")
        assert repaired["gate_pass"] is True, repaired

        health = bank_health("snowpro-core")
        assert health["questions"] == 2
        assert health["domains"]
        for domain in health["domains"].values():
            assert 0 <= domain["qa_pass_pct"] <= 100
            assert 0 <= domain["content_approved_pct"] <= 100
            assert 0 <= domain["sme_approved_pct"] <= 100

        with connect() as conn:
            events = int(conn.execute("SELECT COUNT(*) AS n FROM editorial_review_events").fetchone()["n"])
            assert events >= 5
            run = conn.execute("SELECT question_count,passed_count,failed_count FROM editorial_qa_runs ORDER BY id DESC LIMIT 1").fetchone()
            assert int(run["question_count"]) == 2 and int(run["passed_count"]) == 2 and int(run["failed_count"]) == 0

        print(
            f"Question editorial maturity: PASS (backend={DATABASE_BACKEND}, QA, human content/SME review, immutable-version gate, bank health)"
        )
    finally:
        TEMP.cleanup()


if __name__ == "__main__":
    main()
