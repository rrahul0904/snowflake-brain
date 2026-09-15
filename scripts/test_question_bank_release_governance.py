#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory(prefix="snowflake-bank-governance-")
os.environ["BRAIN_DB"] = str(Path(TEMP.name) / "bank-governance.sqlite")

from app.database import connect, run_migrations  # noqa: E402
from app.question_bank import import_question_bank_payload  # noqa: E402
from app.question_bank_release_governance import promote_release_governed  # noqa: E402
from app.question_bank_releases import create_release, get_release  # noqa: E402
from app.question_versions import ensure_question_version_schema  # noqa: E402
from app.skill_brain import flatten_skills  # noqa: E402


def check(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def expect_value_error(operation, expected: str) -> None:
    try:
        operation()
    except ValueError as exc:
        check(expected.lower() in str(exc).lower(), f"expected error containing {expected!r}, got {exc!r}")
        return
    raise AssertionError(f"expected ValueError containing {expected!r}")


def question() -> dict:
    skill = flatten_skills("snowpro-core")[0]
    return {
        "id": "governance::q1",
        "domain_id": skill["domain_id"],
        "task_id": skill["id"],
        "task_code": skill.get("task_code") or "",
        "question_type": "scenario",
        "cognitive_level": "apply",
        "difficulty_band": "applied",
        "bank_pool": "practice",
        "authoring_status": "active",
        "authoring_version": "governance-test",
        "question": "Which governed Snowflake release choice satisfies the certification scenario?",
        "options": ["Incorrect A", "Correct B", "Incorrect C", "Incorrect D"],
        "correct_options": [1],
        "correct_rationale": "Option B satisfies the controlled release scenario requirement.",
        "distractor_rationales": [
            "This does not satisfy the requirement.",
            "This is the correct choice.",
            "This addresses a different behavior.",
            "This introduces an unrelated constraint.",
        ],
        "concepts": ["release-governance"],
        "trap_tags": ["governance-test"],
        "source_refs": [
            {
                "title": "Snowflake documentation",
                "url": "https://docs.snowflake.com/en/user-guide/intro-key-concepts",
            }
        ],
        "source_verified_at": "2026-09-15",
    }


def main() -> None:
    run_migrations()
    ensure_question_version_schema()
    import_question_bank_payload(
        {
            "schema_version": "snowflake-question-bank-v1",
            "bank_version": "governance-test-v1",
            "track_id": "snowpro-core",
            "exam_code": "COF-C03",
            "source_verified_at": "2026-09-15",
            "questions": [question()],
        },
        source_name="governance-test-v1.json",
    )

    release_key = "governance-test-release"
    create_release(
        release_key,
        "snowpro-core",
        question_ids=["governance::q1"],
        actor="importer@example.com",
        notes="Test release for independent SME approval governance.",
    )
    promote_release_governed(release_key, "qa_passed", actor="qa-automation")

    evidence = "https://github.com/rrahul0904/snowflake-brain/issues/25#issuecomment-review-evidence"
    expect_value_error(
        lambda: promote_release_governed(
            release_key,
            "sme_approved",
            actor="importer@example.com",
            approval_evidence_ref=evidence,
        ),
        "independent",
    )
    expect_value_error(
        lambda: promote_release_governed(
            release_key,
            "sme_approved",
            actor="release-operator",
            approval_evidence_ref=evidence,
        ),
        "named independent reviewer",
    )
    expect_value_error(
        lambda: promote_release_governed(
            release_key,
            "sme_approved",
            actor="reviewer@example.com",
            approval_evidence_ref="",
        ),
        "evidence",
    )
    expect_value_error(
        lambda: promote_release_governed(
            release_key,
            "sme_approved",
            actor="reviewer@example.com",
            approval_evidence_ref="pending",
        ),
        "evidence",
    )

    approved = promote_release_governed(
        release_key,
        "sme_approved",
        actor="reviewer@example.com",
        approval_evidence_ref=evidence,
    )
    check(approved["status"] == "sme_approved", "independent reviewer may approve a QA-passed release")
    check(approved["approved_by"] == "reviewer@example.com", "approved_by records the named reviewer")
    check(approved["created_by"] == "importer@example.com", "release creator remains distinct from approver")

    evidence_events = [
        event
        for event in approved.get("events") or []
        if event.get("action") == "sme_approval_evidence_submitted"
    ]
    check(len(evidence_events) == 1, "SME evidence is recorded exactly once")
    metadata = evidence_events[0].get("metadata") or {}
    check(metadata.get("approval_evidence_ref") == evidence, "audit event retains the stable evidence reference")
    check(metadata.get("release_created_by") == "importer@example.com", "audit event records the creator identity")
    check(metadata.get("separation_of_duties") is True, "audit event records separation of duties")

    staged = promote_release_governed(release_key, "staging", actor="release-manager@example.com")
    check(staged["status"] == "staging", "approved release can continue to staging")

    with connect() as conn:
        approval_rows = conn.execute(
            "SELECT actor,metadata_json FROM question_bank_release_events WHERE action='sme_approval_evidence_submitted'"
        ).fetchall()
    check(len(approval_rows) == 1, "database audit trail contains one SME evidence event")
    stored = json.loads(approval_rows[0]["metadata_json"])
    check(approval_rows[0]["actor"] == "reviewer@example.com", "database audit actor is the reviewer")
    check(stored["approval_evidence_ref"] == evidence, "database audit metadata retains evidence")

    workflow = (ROOT / ".github" / "workflows" / "production-question-bank-release.yml").read_text(encoding="utf-8")
    admin_cli = (ROOT / "scripts" / "question_bank_admin.py").read_text(encoding="utf-8")
    check("approval_evidence_ref:" in workflow, "production workflow exposes explicit SME evidence input")
    check("--evidence-ref" in workflow, "production workflow passes SME evidence into the governed CLI")
    check("promote_release_governed" in admin_cli, "admin CLI cannot bypass governed SME promotion")
    check("--evidence-ref" in admin_cli, "admin CLI requires an auditable evidence channel")

    print("Question-bank independent SME approval governance checks passed.")


if __name__ == "__main__":
    main()
