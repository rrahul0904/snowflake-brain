#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory(prefix="snowflake-bank-test-")
DB_PATH = Path(TEMP.name) / "question-bank.sqlite"
os.environ["BRAIN_DB"] = str(DB_PATH)
os.environ["AFFILIATE_RESOURCES_ENABLED"] = "false"

from fastapi.testclient import TestClient  # noqa: E402
from app.database import connect, run_migrations  # noqa: E402
from app.entitlements import apply_membership_plan  # noqa: E402
from app.main import app  # noqa: E402
from app.question_bank import bank_status, import_question_bank_payload, validate_question_bank_payload  # noqa: E402
from app.skill_brain import flatten_skills  # noqa: E402


def check(value: object, message: str) -> None:
    if not value:
        raise AssertionError(message)


def synthetic_bank() -> dict:
    questions = []
    pools = {"free": 5, "practice": 6, "diagnostic": 4, "mock_reserved": 10}
    for skill in flatten_skills("snowpro-core"):
        for pool, count in pools.items():
            for index in range(1, count + 1):
                qid = f"private::{pool}::{skill['id']}::{index}"
                questions.append(
                    {
                        "id": qid,
                        "domain_id": skill["domain_id"],
                        "task_id": skill["id"],
                        "task_code": skill.get("task_code") or "",
                        "question_type": "scenario" if index % 2 else "standard_mcq",
                        "cognitive_level": "apply",
                        "difficulty_band": ["foundation", "applied", "exam", "challenge"][(index - 1) % 4],
                        "bank_pool": pool,
                        "authoring_status": "active",
                        "authoring_version": "test-v1",
                        "question": f"For task {skill['id']} in pool {pool}, scenario {index}: which Snowflake choice best satisfies the stated requirement?",
                        "options": [f"Distractor A for {qid}", f"Correct option for {qid}", f"Distractor C for {qid}", f"Distractor D for {qid}"],
                        "correct_options": [1],
                        "correct_rationale": f"Option B is correct for {qid} because it directly matches the configured task boundary and the scenario requirement.",
                        "distractor_rationales": [
                            "This option solves a different requirement and is not the best answer.",
                            "This is the correct option for the stated task and requirement.",
                            "This option introduces an unnecessary or unrelated Snowflake behavior.",
                            "This option does not satisfy the key constraint in the scenario.",
                        ],
                        "concepts": [skill["id"], pool],
                        "trap_tags": ["scope-confusion"],
                        "source_refs": [{"title": "Snowflake documentation", "url": "https://docs.snowflake.com/en/user-guide/intro-key-concepts"}],
                        "source_verified_at": "2026-08-14",
                    }
                )
    return {
        "schema_version": "snowflake-question-bank-v1",
        "bank_version": "test-v1",
        "track_id": "snowpro-core",
        "exam_code": "COF-C03",
        "source_verified_at": "2026-08-14",
        "questions": questions,
    }


def register(client: TestClient, name: str, email: str) -> dict:
    response = client.post("/api/auth/register", json={"display_name": name, "email": email, "password": "candidate-password"})
    check(response.status_code == 201, response.text)
    return response.json()


def metadata_for_session(session_id: int) -> list[dict]:
    with connect() as conn:
        return [dict(row) for row in conn.execute(
            """
            SELECT m.question_id,m.domain_id,m.task_id,m.bank_pool,m.difficulty_band
            FROM exam_session_questions sq
            JOIN question_bank_metadata m ON m.question_id=sq.question_id
            WHERE sq.session_id=? ORDER BY sq.position
            """,
            (session_id,),
        )]


def main() -> None:
    run_migrations()
    bank = synthetic_bank()
    validation = validate_question_bank_payload(bank, source_name="synthetic-test.json")
    check(validation["valid"], "synthetic private bank validates")
    check(validation["coverage"]["tasks_covered"] == 19, "all 19 COF-C03 task statements covered")
    imported = import_question_bank_payload(bank, source_name="synthetic-test.json")
    check(imported["imported"] == len(bank["questions"]), "all synthetic private questions imported")
    status = bank_status("snowpro-core")
    check(status["tasks_covered"] == status["tasks_total"] == 19, "backend coverage complete")

    free = TestClient(app)
    state = register(free, "Free Candidate", "free-bank@example.com")
    free_id = int(state["candidate"]["id"])
    config = free.get("/api/mock/config?track_id=snowpro-core")
    check(config.status_code == 200 and "question_bank" not in config.json(), "candidate config hides bank inventory")
    check(free.get("/api/questions").status_code == 403, "bulk bank inventory blocked")

    drill = free.post("/api/certification-quiz/start", json={"track_id": "snowpro-core", "mode": "drill", "count": 10})
    check(drill.status_code == 200 and len(drill.json()["questions"]) == 10, "Free drill works")
    for question in drill.json()["questions"]:
        check("correct" not in question and "explanation" not in question, "practice start does not leak answers")

    weekly = free.post("/api/mock/sessions", json={"track_id": "snowpro-core", "mode": "weekly-mock"})
    check(weekly.status_code == 200 and len(weekly.json()["questions"]) == 30, "Free 30Q full-content mock starts")
    check(int(weekly.json()["duration_seconds"]) == 45 * 60, "Free mock is timed for 45 minutes")
    weekly_meta = metadata_for_session(int(weekly.json()["session_id"]))
    check({row["bank_pool"] for row in weekly_meta} == {"free"}, "Free mock uses only Free pool")
    check(Counter(row["domain_id"] for row in weekly_meta) == Counter({"features-architecture": 9, "account-governance": 6, "loading-connectivity": 5, "performance-transformation": 7, "data-collaboration": 3}), "Free 30Q mock spans the full blueprint")
    free.post(f"/api/mock/sessions/{weekly.json()['session_id']}/submit", json={"reason": "learner"})

    apply_membership_plan(free_id, "premium_20", source="test", reason="question-bank-tier-test")
    quick = free.post("/api/mock/sessions", json={"track_id": "snowpro-core", "mode": "quick-mock"})
    check(quick.status_code == 200 and len(quick.json()["questions"]) == 30, "Premium Quick Mock starts")
    free.post(f"/api/mock/sessions/{quick.json()['session_id']}/submit", json={"reason": "learner"})

    full = free.post("/api/mock/sessions", json={"track_id": "snowpro-core", "mode": "full-mock"})
    check(full.status_code == 200 and len(full.json()["questions"]) == 100, "Premium Full Mock starts")
    full_meta = metadata_for_session(int(full.json()["session_id"]))
    check(Counter(row["domain_id"] for row in full_meta) == Counter({"features-architecture": 31, "account-governance": 20, "loading-connectivity": 18, "performance-transformation": 21, "data-collaboration": 10}), "100Q Full Mock follows exact blueprint allocation")
    check(len({row["task_id"] for row in full_meta}) == 19, "Full Mock spans all 19 tasks")
    free.post(f"/api/mock/sessions/{full.json()['session_id']}/submit", json={"reason": "learner"})

    pack = TestClient(app)
    pack_state = register(pack, "Exam Pack Candidate", "pack-bank@example.com")
    pack_id = int(pack_state["candidate"]["id"])
    apply_membership_plan(pack_id, "exam_pack_35", source="test", reason="question-bank-exam-pack")
    first_pack = pack.post("/api/mock/sessions", json={"track_id": "snowpro-core", "mode": "lifetime-practice"})
    check(first_pack.status_code == 200 and len(first_pack.json()["questions"]) == 100, "Exam Pack lifetime mock starts")
    first_ids = {row["id"] for row in first_pack.json()["questions"]}
    pack.post(f"/api/mock/sessions/{first_pack.json()['session_id']}/submit", json={"reason": "learner"})
    second_pack = pack.post("/api/mock/sessions", json={"track_id": "snowpro-core", "mode": "lifetime-practice"})
    second_ids = {row["id"] for row in second_pack.json()["questions"]}
    check(first_ids == second_ids, "Exam Pack lifetime set remains fixed and does not reset")

    print("Question-bank tier, Free 30Q mock, blueprint, privacy, and Exam Pack checks passed.")


if __name__ == "__main__":
    main()
