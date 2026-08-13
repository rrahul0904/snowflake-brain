#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory(prefix="snowflake-mock-v25-")
os.environ["BRAIN_DB"] = str(Path(TEMP.name) / "mock.sqlite")

from app.database import connect, run_migrations  # noqa: E402
from app.mock_exam import (  # noqa: E402
    active_session,
    create_session,
    history,
    public_config,
    result_payload,
    save_answer,
    session_payload,
    set_flag,
    submit_session,
)
from app.routers.questions import QuizAnswer, QuizGradeRequest, quiz_grade  # noqa: E402


def seed_test(test_id: str, source_kind: str, legacy: bool, questions: list[dict]) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO practice_tests(id, track_id, title, exam_code, source_kind, source_path,
              position, question_count, version, is_legacy)
            VALUES (?, 'snowpro-core', ?, ?, ?, 'test://fixture', 1, ?, 'test', ?)
            """,
            (test_id, test_id, "COF-C02" if legacy else "COF-C03", source_kind, len(questions), int(legacy)),
        )
        for position, item in enumerate(questions, start=1):
            conn.execute(
                """
                INSERT INTO questions(id, track_id, test_id, test_title, question, options_json,
                  correct_json, explanation, source_path, source_kind, assessment_type, tags,
                  difficulty, multiple, question_position)
                VALUES (?, 'snowpro-core', ?, ?, ?, ?, ?, ?, 'test://fixture', ?, ?, '[]', 'medium', ?, ?)
                """,
                (
                    item["id"], test_id, test_id, item["question"], json.dumps(item["options"]),
                    json.dumps(item["correct"]), item.get("explanation", "Fixture explanation"), source_kind,
                    "multi-select" if len(item["correct"]) > 1 else "single-select", int(len(item["correct"]) > 1), position,
                ),
            )
            conn.execute(
                """
                INSERT INTO question_skill_map(question_id, track_id, domain_id, skill_id, confidence, reviewed)
                VALUES (?, 'snowpro-core', ?, ?, 1.0, 1)
                """,
                (item["id"], item["domain_id"], item["skill_id"]),
            )


def private_correct(session_id: int, question_id: str) -> list[int]:
    with connect() as conn:
        row = conn.execute(
            "SELECT correct_positions_json FROM exam_session_questions WHERE session_id=? AND question_id=?",
            (session_id, question_id),
        ).fetchone()
    return json.loads(row["correct_positions_json"])


def assert_no_private_answer(value: object) -> None:
    forbidden = {"correct", "correct_json", "correct_index", "correct_positions_json", "explanation"}
    if isinstance(value, dict):
        assert not (forbidden & set(value)), f"pre-submit payload leaked {forbidden & set(value)}"
        for item in value.values():
            assert_no_private_answer(item)
    elif isinstance(value, list):
        for item in value:
            assert_no_private_answer(item)


def main() -> None:
    run_migrations()
    domains = [
        ("features-architecture", "ai-data-cloud-features"),
        ("account-governance", "security-access-principles"),
        ("loading-connectivity", "bulk-load-unload"),
        ("performance-transformation", "warehouse-sizing-scaling"),
        ("data-collaboration", "time-travel-failsafe"),
    ]
    seed_test(
        "fixture-current",
        "source",
        False,
        [
            {"id": f"source-{index}", "question": f"Current source {index}", "options": ["A", "B", "C", "D"], "correct": [0], "domain_id": domain, "skill_id": skill}
            for index, (domain, skill) in enumerate(domains, start=1)
        ],
    )
    seed_test(
        "fixture-legacy",
        "legacy",
        True,
        [{"id": "legacy-1", "question": "Legacy question", "options": ["A", "B"], "correct": [1], "domain_id": domains[0][0], "skill_id": domains[0][1]}],
    )
    seed_test(
        "fixture-multi",
        "source",
        False,
        [{"id": "multi-1", "question": "Select two", "options": ["A", "B", "C", "D"], "correct": [0, 2], "domain_id": domains[0][0], "skill_id": domains[0][1]}],
    )

    config = public_config()
    assert config["track_id"] == "snowpro-core" and config["exam_code"] == "COF-C03"
    assert [domain["weight"] for domain in config["domains"]] == [31, 20, 18, 21, 10]

    quick = create_session("snowpro-core", "quick-mock", randomize_options=False)
    assert quick["total_questions"] == 30  # 1. mock starts; 2. requested count
    assert len({question["id"] for question in quick["questions"]}) == 30  # 6. no duplicates
    assert "legacy-1" not in {question["id"] for question in quick["questions"]}  # 4/20. isolation
    assert sum(question["source_kind"] == "source" for question in quick["questions"]) >= 5  # 5. source priority
    assert_no_private_answer(quick)  # 14. no leakage

    quick_domains = Counter(question["domain_id"] for question in quick["questions"])
    assert quick_domains == Counter({
        "features-architecture": 10,
        "performance-transformation": 6,
        "account-governance": 6,
        "loading-connectivity": 5,
        "data-collaboration": 3,
    })  # 3. weighted allocation

    first = quick["questions"][0]
    save_answer(quick["session_id"], first["id"], [0])
    set_flag(quick["session_id"], first["id"], True)
    resumed = session_payload(quick["session_id"])
    resumed_first = next(question for question in resumed["questions"] if question["id"] == first["id"])
    assert resumed_first["selected"] == [0]  # 8. answer persistence
    assert resumed_first["flagged"] is True  # 9. flag persistence
    assert active_session()["session_id"] == quick["session_id"]  # 10. refresh/resume

    # Active timed questions cannot use the legacy stateless grading endpoint.
    try:
        quiz_grade(QuizGradeRequest(answers=[QuizAnswer(question_id=first["id"], selected=[])]))
        raise AssertionError("active exam leaked through /quiz/grade")
    except Exception as error:
        assert getattr(error, "status_code", None) == 409

    early = submit_session(quick["session_id"], "learner")  # 12. early submit
    assert early["status"] == "finished"
    with connect() as conn:
        attempt_count = conn.execute("SELECT COUNT(*) AS count FROM question_attempts").fetchone()["count"]
    repeat = submit_session(quick["session_id"], "learner")
    with connect() as conn:
        repeat_count = conn.execute("SELECT COUNT(*) AS count FROM question_attempts").fetchone()["count"]
    assert repeat["session_id"] == early["session_id"] and repeat_count == attempt_count  # 13. idempotent
    assert attempt_count == 30  # 17. task/mastery evidence update

    full = create_session("snowpro-core", "full-mock", randomize_options=False)
    assert full["total_questions"] == 100
    full_domains = Counter(question["domain_id"] for question in full["questions"])
    assert full_domains == Counter({
        "features-architecture": 31,
        "performance-transformation": 21,
        "account-governance": 20,
        "loading-connectivity": 18,
        "data-collaboration": 10,
    })
    for question in full["questions"]:
        save_answer(full["session_id"], question["id"], private_correct(full["session_id"], question["id"]))
    perfect = submit_session(full["session_id"])
    assert perfect["raw_correct"] == 100
    assert perfect["scaled_score"] == 1000 and perfect["weighted_accuracy"] == 100.0  # 15/16. score/domain

    partial = create_session("snowpro-core", "source-exam", "fixture-multi", randomize_options=False)
    save_answer(partial["session_id"], "multi-1", [0])
    partial_result = submit_session(partial["session_id"])
    assert partial_result["raw_correct"] == 0  # 7. partial multi-select wrong
    exact = create_session("snowpro-core", "source-exam", "fixture-multi", randomize_options=False)
    save_answer(exact["session_id"], "multi-1", [0, 2])
    exact_result = submit_session(exact["session_id"])
    assert exact_result["raw_correct"] == 1  # 7. exact set correct

    source = create_session("snowpro-core", "source-exam", "fixture-current", randomize_options=False)
    assert [question["id"] for question in source["questions"]] == [f"source-{i}" for i in range(1, 6)]  # 19. fixed membership/order
    submit_session(source["session_id"])

    with connect() as conn:
        before_legacy = conn.execute("SELECT COUNT(*) AS count FROM question_attempts").fetchone()["count"]
    legacy = create_session("snowpro-core", "source-exam", "fixture-legacy", randomize_options=False)
    save_answer(legacy["session_id"], "legacy-1", [1])
    submit_session(legacy["session_id"])
    with connect() as conn:
        after_legacy = conn.execute("SELECT COUNT(*) AS count FROM question_attempts").fetchone()["count"]
        legacy_event = conn.execute("SELECT COUNT(*) AS count FROM learning_events WHERE event_type='legacy_practice_finished'").fetchone()["count"]
    assert after_legacy == before_legacy and legacy_event == 1  # 20. COF-C02 excluded from readiness

    expired = create_session("snowpro-core", "quick-mock")
    with connect() as conn:
        conn.execute("UPDATE exam_sessions SET started_at=datetime('now', '-2 hours'), duration_seconds=1 WHERE id=?", (expired["session_id"],))
    expired_payload = session_payload(expired["session_id"])
    assert expired_payload["status"] == "finished"
    assert result_payload(expired["session_id"])["submitted_reason"] == "timer"  # 11. timer expiration

    rows = history()["history"]
    assert any(row["session_id"] == full["session_id"] for row in rows)  # 18. history
    print("V25 production mock tests passed")
    print("checks=20 quick=30 full=100 multi_select=exact timer=persisted history=persisted")


if __name__ == "__main__":
    try:
        main()
    finally:
        TEMP.cleanup()
