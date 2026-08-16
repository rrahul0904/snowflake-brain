#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory(prefix="snowflake-content-freshness-")
os.environ["BRAIN_DB"] = str(Path(TEMP.name) / "freshness.sqlite")
os.environ["CONTENT_FRESHNESS_ALLOWED_HOSTS"] = "docs.snowflake.com"

from app.content_freshness import (  # noqa: E402
    ContentFreshnessError,
    FetchResult,
    check_source,
    ensure_content_freshness_schema,
    fingerprint_html,
    link_artifact,
    provenance_status,
    record_source_content,
    register_source,
    release_freshness_report,
    review_queue,
    set_freshness_policy,
    verify_artifact_link,
    verify_source,
)
from app.database import connect, run_migrations  # noqa: E402
from app.question_bank import import_question_bank_payload  # noqa: E402
from app.question_bank_releases import (  # noqa: E402
    activate_release,
    create_release,
    ensure_question_bank_release_schema,
    get_release,
    promote_release,
)
from app.question_versions import ensure_question_version_schema  # noqa: E402
from app.skill_brain import flatten_skills  # noqa: E402


def seed_questions() -> None:
    skill = flatten_skills("snowpro-core")[0]
    questions = []
    for position, question_id in enumerate(("fresh-q1", "fresh-q2"), start=1):
        questions.append(
            {
                "id": question_id,
                "domain_id": skill["domain_id"],
                "task_id": skill["id"],
                "task_code": skill.get("task_code") or "",
                "question_type": "scenario",
                "cognitive_level": "apply",
                "difficulty_band": "applied",
                "bank_pool": "practice",
                "authoring_status": "active",
                "authoring_version": "freshness-test",
                "question": f"For freshness regression scenario {position}, which Snowflake choice best satisfies the stated requirement?",
                "options": [
                    f"Incorrect A for freshness {position}",
                    f"Correct B for freshness {position}",
                    f"Incorrect C for freshness {position}",
                    f"Incorrect D for freshness {position}",
                ],
                "correct_options": [1],
                "correct_rationale": f"Option B is correct for freshness regression {position} because it directly satisfies the controlled scenario requirement.",
                "distractor_rationales": [
                    "This option does not satisfy the scenario requirement.",
                    "This is the correct option for the stated requirement.",
                    "This option addresses a different Snowflake behavior.",
                    "This option introduces an unrelated constraint.",
                ],
                "concepts": ["freshness"],
                "trap_tags": ["freshness-test"],
                "source_refs": [
                    {
                        "title": "Snowflake virtual warehouses",
                        "url": "https://docs.snowflake.com/en/user-guide/warehouses",
                    }
                ],
                "source_verified_at": "2026-08-15",
            }
        )
    import_question_bank_payload(
        {
            "schema_version": "snowflake-question-bank-v1",
            "bank_version": "freshness-test",
            "track_id": "snowpro-core",
            "exam_code": "COF-C03",
            "source_verified_at": "2026-08-15",
            "questions": questions,
        },
        source_name="freshness-regression.json",
    )


def promote_to_staging(release_key: str) -> None:
    promote_release(release_key, "qa_passed", actor="freshness-test")
    promote_release(release_key, "sme_approved", actor="freshness-test")
    promote_release(release_key, "staging", actor="freshness-test")


def content_rows() -> dict[str, tuple[str, str, str]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT id,question,correct_json,explanation FROM questions WHERE id IN ('fresh-q1','fresh-q2') ORDER BY id"
        ).fetchall()
    return {str(row["id"]): (str(row["question"]), str(row["correct_json"]), str(row["explanation"])) for row in rows}


def check_fingerprint_normalization() -> None:
    one, _ = fingerprint_html(
        "<html><nav>Navigation version 1</nav><main><h1>Warehouses</h1><p>A warehouse provides compute resources.</p></main></html>"
    )
    two, _ = fingerprint_html(
        "<html><nav>Navigation version 999</nav><main><h1>Warehouses</h1><p>A warehouse provides compute resources.</p></main></html>"
    )
    changed, _ = fingerprint_html(
        "<html><nav>Navigation version 999</nav><main><h1>Warehouses</h1><p>A warehouse provides isolated compute resources.</p></main></html>"
    )
    assert one == two, "Navigation chrome should not create a false documentation change"
    assert one != changed, "Meaningful visible source content change was not detected"


def main() -> None:
    try:
        run_migrations()
        ensure_question_version_schema()
        ensure_question_bank_release_schema()
        ensure_content_freshness_schema()
        seed_questions()
        check_fingerprint_normalization()

        try:
            register_source("evil", "https://example.com/not-official")
        except ContentFreshnessError:
            pass
        else:
            raise AssertionError("Unapproved source host was accepted")

        register_source(
            "snowflake-warehouses",
            "https://docs.snowflake.com/en/user-guide/warehouses",
            source_title="Virtual warehouses",
            source_section="Overview",
        )
        initial_html = """
        <html><body><nav>Docs navigation</nav><main>
          <h1>Virtual warehouses</h1>
          <p>A virtual warehouse provides compute resources for queries and data loading.</p>
        </main></body></html>
        """
        initialized = record_source_content(
            "snowflake-warehouses",
            initial_html,
            etag='"freshness-v1"',
            last_modified="Sat, 15 Aug 2026 12:00:00 GMT",
        )
        assert initialized["result"] == "initialized"
        assert len(review_queue()) == 1

        link_artifact("snowflake-warehouses", "question", "fresh-q1", track_id="snowpro-core", source_section="Overview")
        link_artifact("snowflake-warehouses", "question", "fresh-q2", track_id="snowpro-core", source_section="Overview")
        link_artifact("snowflake-warehouses", "lesson", "warehouse-compute-basics", track_id="snowpro-core", source_section="Overview")

        verify_source(
            "snowflake-warehouses",
            "editor-one",
            confidence=98,
            document_date="2026-08-15",
            notes="Initial official-source verification for regression.",
        )
        for artifact_type, artifact_key in (
            ("question", "fresh-q1"),
            ("question", "fresh-q2"),
            ("lesson", "warehouse-compute-basics"),
        ):
            verify_artifact_link(
                "snowflake-warehouses",
                artifact_type,
                artifact_key,
                "editor-one",
                confidence=97,
                notes="Assertion checked against current official source fingerprint.",
            )
        assert review_queue() == []

        create_release(
            "freshness-release-001",
            "snowpro-core",
            question_ids=["fresh-q1", "fresh-q2"],
            actor="freshness-test",
            notes="Freshness gate regression release 1",
        )
        promote_to_staging("freshness-release-001")
        baseline = release_freshness_report("freshness-release-001")
        assert baseline["gate_pass"] is True and baseline["coverage_pct"] == 100.0
        set_freshness_policy(
            "snowpro-core",
            enforcement_enabled=True,
            require_all_questions=True,
            max_verification_age_days=120,
            actor="freshness-test",
            release_key="freshness-release-001",
        )
        activate_release("freshness-release-001", actor="freshness-test")
        assert get_release("freshness-release-001")["status"] == "active"

        before = content_rows()
        changed_html = """
        <html><body><nav>New docs navigation</nav><main>
          <h1>Virtual warehouses</h1>
          <p>A virtual warehouse provides compute resources for queries, loading, and supported DML workloads.</p>
        </main></body></html>
        """
        changed = record_source_content(
            "snowflake-warehouses",
            changed_html,
            etag='"freshness-v2"',
            last_modified="Sat, 15 Aug 2026 13:00:00 GMT",
        )
        assert changed["result"] == "changed"
        after = content_rows()
        assert before == after, "Freshness monitoring must never auto-rewrite certification questions/answers"

        queue = review_queue()
        queue_pairs = {(str(item["artifact_type"]), str(item["artifact_key"])) for item in queue}
        assert ("source", "snowflake-warehouses") in queue_pairs
        assert ("question", "fresh-q1") in queue_pairs
        assert ("question", "fresh-q2") in queue_pairs
        assert ("lesson", "warehouse-compute-basics") in queue_pairs

        create_release(
            "freshness-release-002",
            "snowpro-core",
            question_ids=["fresh-q1", "fresh-q2"],
            actor="freshness-test",
            notes="Freshness gate regression release 2",
        )
        promote_to_staging("freshness-release-002")
        report = release_freshness_report("freshness-release-002")
        assert report["gate_pass"] is False
        assert {item["question_id"] for item in report["violations"]} == {"fresh-q1", "fresh-q2"}
        try:
            activate_release("freshness-release-002", actor="freshness-test")
        except Exception as exc:
            assert "freshness" in str(exc).lower() or "integrity" in type(exc).__name__.lower()
        else:
            raise AssertionError("Freshness policy did not block activation of a stale/needs-review release")
        assert get_release("freshness-release-002")["status"] == "staging"

        verify_source("snowflake-warehouses", "editor-two", confidence=99, notes="Reviewed official source change.")
        for artifact_type, artifact_key in (
            ("question", "fresh-q1"),
            ("question", "fresh-q2"),
            ("lesson", "warehouse-compute-basics"),
        ):
            verify_artifact_link(
                "snowflake-warehouses",
                artifact_type,
                artifact_key,
                "editor-two",
                confidence=98,
                notes="Linked assertion remains valid after source change.",
            )
        assert release_freshness_report("freshness-release-002")["gate_pass"] is True
        activate_release("freshness-release-002", actor="freshness-test")
        assert get_release("freshness-release-002")["status"] == "active"

        with connect() as conn:
            conn.execute(
                "UPDATE content_source_links SET last_verified_at='2000-01-01T00:00:00Z' WHERE artifact_type='question' AND artifact_key='fresh-q1'"
            )
        stale = release_freshness_report("freshness-release-002", max_verification_age_days=120)
        assert stale["gate_pass"] is False
        verify_artifact_link("snowflake-warehouses", "question", "fresh-q1", "editor-three", confidence=98)

        not_modified = check_source(
            "snowflake-warehouses",
            fetcher=lambda source: FetchResult(
                304,
                "",
                etag=str(source.get("etag") or ""),
                last_modified=str(source.get("last_modified") or ""),
                final_url=str(source["source_url"]),
                elapsed_ms=3,
            ),
        )
        assert not_modified["result"] == "not_modified"

        status = provenance_status("snowpro-core")
        assert status["open_reviews"] == 0
        assert status["policy"] and int(status["policy"]["enforcement_enabled"]) == 1
        assert status["active_release"]["gate_pass"] is True

        print(
            "Content freshness pipeline: PASS (official-host guard, fingerprints, review fan-out, no auto-rewrite, hard release gate)"
        )
    finally:
        TEMP.cleanup()


if __name__ == "__main__":
    main()
