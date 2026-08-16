#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory(prefix="snowflake-adaptive-readiness-")
os.environ["BRAIN_DB"] = str(Path(TEMP.name) / "adaptive.sqlite")

from app.adaptive_readiness import (  # noqa: E402
    adaptive_question_ids,
    build_readiness,
    ensure_adaptive_readiness_schema,
    latest_readiness,
)
from app.auth import create_candidate  # noqa: E402
from app.config import DATABASE_BACKEND  # noqa: E402
from app.database import connect, run_migrations  # noqa: E402
from app.learning_intelligence import ensure_learning_intelligence_schema  # noqa: E402
from app.question_bank import import_question_bank_payload  # noqa: E402
from app.question_bank_releases import (  # noqa: E402
    activate_release,
    create_release,
    ensure_question_bank_release_schema,
    promote_release,
)
from app.question_versions import ensure_question_version_schema  # noqa: E402
from app.skill_brain import flatten_skills  # noqa: E402


def seed_questions() -> list[str]:
    skill = flatten_skills("snowpro-core")[0]
    ids: list[str] = []
    questions = []
    for index in range(1, 31):
        question_id = f"adaptive-q{index:02d}"
        ids.append(question_id)
        difficulty_band = "exam" if index % 5 == 0 else "foundation" if index % 4 == 0 else "applied"
        correct = index % 4
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
                "authoring_version": "adaptive-test",
                "question": f"Which Snowflake architecture choice best addresses adaptive regression requirement {index} with an independently managed compute decision?",
                "options": ["Choice A", "Choice B", "Choice C", "Choice D"],
                "correct_options": [correct],
                "correct_rationale": "The selected option is correct for this controlled adaptive regression scenario and represents the intended certification decision.",
                "distractor_rationales": [
                    "This option does not satisfy the controlled adaptive scenario.",
                    "This option represents a different Snowflake behavior.",
                    "This option introduces an unrelated constraint.",
                    "This option is not the best choice for the stated requirement.",
                ],
                "concepts": ["adaptive", "architecture"],
                "trap_tags": ["adaptive-test"],
                "source_refs": [
                    {
                        "title": "Snowflake key concepts",
                        "url": "https://docs.snowflake.com/en/user-guide/intro-key-concepts",
                    }
                ],
                "source_verified_at": "2026-08-15",
            }
        )
    import_question_bank_payload(
        {
            "schema_version": "snowflake-question-bank-v1",
            "bank_version": "adaptive-test",
            "track_id": "snowpro-core",
            "exam_code": "COF-C03",
            "source_verified_at": "2026-08-15",
            "questions": questions,
        },
        source_name="adaptive-regression.json",
    )
    return ids


def activate_bank(question_ids: list[str]) -> None:
    create_release(
        "adaptive-release-001",
        "snowpro-core",
        question_ids=question_ids,
        actor="adaptive-test",
        notes="Adaptive readiness regression bank",
    )
    promote_release("adaptive-release-001", "qa_passed", actor="adaptive-test")
    promote_release("adaptive-release-001", "sme_approved", actor="adaptive-test")
    promote_release("adaptive-release-001", "staging", actor="adaptive-test")
    activate_release("adaptive-release-001", actor="adaptive-test")


def seed_candidate_evidence(candidate_id: int, question_ids: list[str]) -> None:
    exam_date = (date.today() + timedelta(days=18)).isoformat()
    with connect() as conn:
        conn.execute(
            "INSERT INTO candidate_study_preferences(candidate_id,track_id,exam_date,daily_minutes,days_per_week) VALUES (?,?,?,?,?)",
            (candidate_id, "snowpro-core", exam_date, 35, 5),
        )
        for index, question_id in enumerate(question_ids[:12]):
            conn.execute(
                """
                INSERT INTO question_attempts(question_id,selected,correct,mode,candidate_id,response_time_ms,confidence,attempted_at)
                VALUES (?,?,?,?,?,?,?,datetime('now',?))
                """,
                (question_id, f"[{index % 4}]", 1, "drill", candidate_id, 42000 + index * 700, 5 if index % 3 == 0 else 4, f"-{index % 6} days"),
            )
        for index, question_id in enumerate(question_ids[12:16]):
            conn.execute(
                """
                INSERT INTO question_attempts(question_id,selected,correct,mode,candidate_id,response_time_ms,confidence,attempted_at)
                VALUES (?,?,?,?,?,?,?,datetime('now',?))
                """,
                (question_id, "[0]", 0, "drill", candidate_id, 50000 + index * 1000, 5, f"-{index + 1} days"),
            )
        for index, question_id in enumerate(question_ids[16:19]):
            conn.execute(
                """
                INSERT INTO question_attempts(question_id,selected,correct,mode,candidate_id,response_time_ms,confidence,attempted_at)
                VALUES (?,?,?,?,?,?,?,datetime('now'))
                """,
                (question_id, "[0]", 1, "drill", candidate_id, 650 + index * 40, 1),
            )
        conn.execute(
            """
            INSERT INTO question_attempts(question_id,selected,correct,mode,candidate_id,response_time_ms,confidence,attempted_at)
            VALUES (?,?,?,?,?,?,?,datetime('now','-90 days'))
            """,
            (question_ids[19], "[0]", 1, "drill", candidate_id, 46000, 5),
        )

        for index, question_id in enumerate(question_ids[:2]):
            modifier = "-1 days" if index == 0 else "-5 days"
            conn.execute(
                """
                INSERT INTO candidate_srs_state(
                  candidate_id,question_id,track_id,domain_id,skill_id,repetitions,interval_days,ease_factor,lapses,due_at,last_reviewed_at,last_correct,last_confidence
                ) VALUES (?,?,?,?,?,?,?,?,?,datetime('now',?),datetime('now','-10 days'),1,4)
                """,
                (candidate_id, question_id, "snowpro-core", skill_domain(question_id), skill_id(question_id), 3, 7, 2.4, 0, modifier),
            )

        conn.execute(
            """
            INSERT INTO exam_sessions(
              track_id,candidate_id,mode,status,total_questions,raw_accuracy,weighted_accuracy,scaled_score,finished_at
            ) VALUES (?,?,?,'submitted',100,?,?,?,datetime('now','-2 days'))
            """,
            ("snowpro-core", candidate_id, "exam_full_mock", 0.72, 0.72, 720),
        )


def skill_domain(question_id: str) -> str:
    with connect() as conn:
        row = conn.execute("SELECT domain_id FROM question_bank_metadata WHERE question_id=?", (question_id,)).fetchone()
    return str(row["domain_id"]) if row else "unmapped"


def skill_id(question_id: str) -> str:
    with connect() as conn:
        row = conn.execute("SELECT task_id FROM question_bank_metadata WHERE question_id=?", (question_id,)).fetchone()
    return str(row["task_id"]) if row else "unmapped"


def seed_sparse_candidate(candidate_id: int, question_id: str) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO question_attempts(question_id,selected,correct,mode,candidate_id,response_time_ms,confidence,attempted_at) VALUES (?,?,?,?,?,?,?,datetime('now'))",
            (question_id, "[0]", 1, "drill", candidate_id, 40000, 5),
        )


def main() -> None:
    try:
        run_migrations()
        ensure_question_version_schema()
        ensure_question_bank_release_schema()
        ensure_learning_intelligence_schema()
        ensure_adaptive_readiness_schema()
        question_ids = seed_questions()
        activate_bank(question_ids)

        primary = create_candidate("Adaptive Primary", "adaptive-primary@example.com", "AdaptivePrimary!123")
        sparse = create_candidate("Adaptive Sparse", "adaptive-sparse@example.com", "AdaptiveSparse!123")
        primary_id = int(primary["id"])
        sparse_id = int(sparse["id"])
        seed_candidate_evidence(primary_id, question_ids)
        seed_sparse_candidate(sparse_id, question_ids[-1])

        primary_result = build_readiness(primary_id, "snowpro-core", persist=True)
        assert 0 <= primary_result["readiness_score"] <= 100
        assert primary_result["evidence_confidence"] in {"low", "medium", "high"}
        assert primary_result["runway_days"] is not None and 15 <= primary_result["runway_days"] <= 19
        assert 15 <= primary_result["recommended_daily_minutes"] <= 180
        assert primary_result["evidence"]["probable_guess_count"] >= 3
        assert primary_result["evidence"]["srs_due"] == 2
        assert primary_result["evidence"]["srs_overdue"] >= 1
        assert primary_result["components"]["calibration"] < 100
        assert primary_result["recommendations"]
        assert any(item["recommendation_type"] == "retention" for item in primary_result["recommendations"])
        assert any(item["recommendation_type"] == "exam_runway" for item in primary_result["recommendations"])
        assert "not a probability" in primary_result["evidence"]["statement"].lower()

        sparse_result = build_readiness(sparse_id, "snowpro-core", persist=True)
        assert sparse_result["evidence_confidence"] == "low"
        assert sparse_result["readiness_band"] in {"building_evidence", "insufficient_evidence"}
        assert sparse_result["components"]["coverage"] < 10
        assert sparse_result["readiness_score"] < 75, sparse_result

        with connect() as conn:
            old_row = conn.execute(
                "SELECT question_id,attempted_at FROM question_attempts WHERE candidate_id=? AND datetime(attempted_at)<datetime('now','-80 days')",
                (primary_id,),
            ).fetchone()
            assert old_row is not None

        adaptive_ids = adaptive_question_ids(primary_id, "snowpro-core", limit=12)
        assert len(adaptive_ids) == 12
        assert len(set(adaptive_ids)) == 12
        assert set(adaptive_ids) <= set(question_ids)
        assert any(question_id in adaptive_ids[:6] for question_id in question_ids[:2])

        latest = latest_readiness(primary_id, "snowpro-core")
        assert latest is not None
        assert int(latest["id"]) == int(primary_result["snapshot_id"])
        assert latest["recommendations"]

        with connect() as conn:
            primary_snapshots = int(conn.execute("SELECT COUNT(*) AS n FROM candidate_readiness_snapshots WHERE candidate_id=?", (primary_id,)).fetchone()["n"])
            sparse_snapshots = int(conn.execute("SELECT COUNT(*) AS n FROM candidate_readiness_snapshots WHERE candidate_id=?", (sparse_id,)).fetchone()["n"])
            assert primary_snapshots == 1 and sparse_snapshots == 1
            cross = conn.execute(
                """
                SELECT COUNT(*) AS n
                  FROM candidate_adaptive_recommendations r
                  JOIN candidate_readiness_snapshots s ON s.id=r.source_snapshot_id
                 WHERE r.candidate_id<>s.candidate_id
                """
            ).fetchone()["n"]
            assert int(cross) == 0

        print(
            f"Adaptive readiness intelligence v2: PASS (backend={DATABASE_BACKEND}, decay, pace, confidence, guesses, runway, recommendations, isolation)"
        )
    finally:
        TEMP.cleanup()


if __name__ == "__main__":
    main()
