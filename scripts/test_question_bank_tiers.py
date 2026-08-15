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
    pools = {"free": 4, "practice": 4, "diagnostic": 4, "mock_reserved": 6}
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
                        "options": [
                            f"Distractor A for {qid}",
                            f"Correct option for {qid}",
                            f"Distractor C for {qid}",
                            f"Distractor D for {qid}",
                        ],
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
                        "source_refs": [
                            {
                                "title": "Snowflake documentation",
                                "url": "https://docs.snowflake.com/en/user-guide/intro-key-concepts",
                            }
                        ],
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
    response = client.post(
        "/api/auth/register",
        json={"display_name": name, "email": email, "password": "candidate-password"},
    )
    check(response.status_code == 201, response.text)
    return response.json()


def metadata_for(ids: list[str]) -> list[dict]:
    placeholders = ",".join("?" for _ in ids)
    with connect() as conn:
        return [
            dict(row)
            for row in conn.execute(
                f"SELECT question_id,domain_id,task_id,bank_pool,difficulty_band FROM question_bank_metadata WHERE question_id IN ({placeholders})",
                ids,
            )
        ]


def session_metadata(session_id: int) -> list[dict]:
    with connect() as conn:
        return [
            dict(row)
            for row in conn.execute(
                """
                SELECT m.question_id,m.domain_id,m.task_id,m.bank_pool,m.difficulty_band
                FROM exam_session_questions sq
                JOIN question_bank_metadata m ON m.question_id=sq.question_id
                WHERE sq.session_id=? ORDER BY sq.position
                """,
                (session_id,),
            )
        ]


def candidate_id(email: str) -> int:
    with connect() as conn:
        row = conn.execute("SELECT id FROM candidate_accounts WHERE email=?", (email,)).fetchone()
    return int(row["id"])


def main() -> None:
    run_migrations()
    bank = synthetic_bank()
    validation = validate_question_bank_payload(bank, source_name="synthetic-test.json")
    check(validation["valid"], "synthetic private bank validates")
    check(validation["coverage"]["tasks_covered"] == 19, "all 19 COF-C03 task statements covered")
    imported = import_question_bank_payload(bank, source_name="synthetic-test.json")
    check(imported["imported"] == len(bank["questions"]), "all synthetic private questions imported")
    status = bank_status("snowpro-core")
    check(status["active_questions"] == len(bank["questions"]), "backend status counts private bank")
    check(status["tasks_covered"] == status["tasks_total"] == 19, "backend coverage complete")

    invalid = dict(bank)
    invalid["questions"] = [dict(bank["questions"][0], source_refs=[{"url": "https://example.com/not-official"}])]
    check(not validate_question_bank_payload(invalid, source_name="invalid.json")["valid"], "non-official source reference rejected")

    guest = TestClient(app)
    check(guest.get("/api/resources/affiliate").status_code == 401, "affiliate resources require candidate login")

    free = TestClient(app)
    free_state = register(free, "Free Candidate", "free-bank@example.com")
    free_id = int(free_state["candidate"]["id"])
    affiliate = free.get("/api/resources/affiliate")
    check(affiliate.status_code == 200 and affiliate.json()["enabled"] is False and affiliate.json()["books"] == [], "affiliate catalog fails closed until configured")

    config = free.get("/api/mock/config?track_id=snowpro-core")
    check(config.status_code == 200 and "question_bank" not in config.json(), "candidate mock config hides bank inventory")
    check(free.get("/api/questions").status_code == 403, "bulk question inventory blocked")
    check(free.get("/api/practice-tests").json() == {"tests": []}, "internal source-test inventory hidden")
    known = bank["questions"][0]["id"]
    check(free.get(f"/api/questions/{known}").status_code == 404, "unserved private question cannot be enumerated")
    check(free.post("/api/quiz/start", json={"count": 10}).status_code == 410, "legacy quiz endpoint cannot bypass selector")
    bypass = free.post("/api/certification-quiz/start", json={"track_id": "snowpro-core", "mode": "drill", "count": 1, "test_id": "anything"})
    check(bypass.status_code == 403, "candidate cannot pin an internal test_id")

    drill = free.post("/api/certification-quiz/start", json={"track_id": "snowpro-core", "mode": "drill", "count": 10})
    check(drill.status_code == 200 and len(drill.json()["questions"]) == 10, "Free drill works")
    check(set(drill.json()) == {"questions", "total", "quota"}, "candidate practice response exposes product surface only")
    allowed_question_keys = {"id", "question", "options", "multiple", "difficulty"}
    for question in drill.json()["questions"]:
        check(set(question).issubset(allowed_question_keys), "candidate question contains no backend authoring metadata")
        check("correct" not in question and "explanation" not in question, "practice start does not leak answer")
    drill_ids = [row["id"] for row in drill.json()["questions"]]
    check({row["bank_pool"] for row in metadata_for(drill_ids)} == {"free"}, "Free candidate receives only Free bank pool")

    served_id = drill_ids[0]
    served_detail = free.get(f"/api/questions/{served_id}")
    check(served_detail.status_code == 200 and "correct" not in served_detail.json(), "served question can be revisited without answer leak")
    check(free.get(f"/api/questions/{served_id}/bookmark").status_code == 200, "served question bookmark state allowed")
    check(free.post(f"/api/questions/{known}/bookmark", json={}).status_code == 404 if known not in drill_ids else True, "unserved bookmark lookup does not enumerate bank")

    # Grade one served item, then prove the legacy client-supplied correctness
    # flag cannot forge analytics.
    grade = free.post("/api/quiz/grade", json={"answers": [{"question_id": served_id, "selected": [1]}]})
    check(grade.status_code == 200 and grade.json()["results"][0]["is_correct"], "post-submit review reveals verified result")
    review = grade.json()["results"][0]
    check("correct" in review and "explanation" in review, "answer visible only after grading")
    check("source_refs" not in review and "bank_pool" not in review and "authoring_status" not in review, "review hides backend metadata")
    spoof = free.post(f"/api/questions/{served_id}/attempt", json={"selected": [0], "correct": True, "mode": "drill"})
    check(spoof.status_code == 200, "attempt accepted")
    with connect() as conn:
        last = conn.execute("SELECT correct FROM question_attempts WHERE candidate_id=? AND question_id=? ORDER BY id DESC LIMIT 1", (free_id, served_id)).fetchone()
    check(int(last["correct"]) == 0, "server recomputes correctness and ignores spoofed client flag")

    weekly = free.post("/api/mock/sessions", json={"track_id": "snowpro-core", "mode": "weekly-mock"})
    check(weekly.status_code == 200 and len(weekly.json()["questions"]) == 20, "Free weekly mock starts")
    check("configuration" not in weekly.json(), "mock selection internals hidden")
    for question in weekly.json()["questions"]:
        check("correct" not in question and "explanation" not in question and "source_kind" not in question, "mock pre-submit payload is minimum-data")
    weekly_meta = session_metadata(int(weekly.json()["session_id"]))
    check({row["bank_pool"] for row in weekly_meta} == {"free"}, "Free weekly mock uses Free pool only")
    check(Counter(row["domain_id"] for row in weekly_meta) == Counter({"features-architecture": 6, "account-governance": 4, "loading-connectivity": 4, "performance-transformation": 4, "data-collaboration": 2}), "Free 20Q mock follows exact domain allocation")
    free.post(f"/api/mock/sessions/{weekly.json()['session_id']}/submit", json={"reason": "learner"})

    apply_membership_plan(free_id, "premium_20", source="test", reason="question-bank-tier-test")
    quick = free.post("/api/mock/sessions", json={"track_id": "snowpro-core", "mode": "quick-mock"})
    check(quick.status_code == 200 and len(quick.json()["questions"]) == 30, "Premium Quick Mock starts")
    quick_meta = session_metadata(int(quick.json()["session_id"]))
    check({row["bank_pool"] for row in quick_meta}.issubset({"mock_reserved", "practice"}), "Premium mock uses Premium-eligible pools")
    check("free" not in {row["bank_pool"] for row in quick_meta}, "Premium mock does not consume Free-only pool when enough Premium bank exists")
    free.post(f"/api/mock/sessions/{quick.json()['session_id']}/submit", json={"reason": "learner"})

    full = free.post("/api/mock/sessions", json={"track_id": "snowpro-core", "mode": "full-mock"})
    check(full.status_code == 200 and len(full.json()["questions"]) == 100, "Premium Full Mock starts")
    full_meta = session_metadata(int(full.json()["session_id"]))
    check(Counter(row["domain_id"] for row in full_meta) == Counter({"features-architecture": 31, "account-governance": 20, "loading-connectivity": 18, "performance-transformation": 21, "data-collaboration": 10}), "100Q Full Mock follows exact COF-C03 app blueprint allocation")
    check(len({row["task_id"] for row in full_meta}) == 19, "Full Mock spans all 19 task statements when bank coverage exists")
    free.post(f"/api/mock/sessions/{full.json()['session_id']}/submit", json={"reason": "learner"})

    pack = TestClient(app)
    pack_state = register(pack, "Exam Pack Candidate", "pack-bank@example.com")
    pack_id = int(pack_state["candidate"]["id"])
    apply_membership_plan(pack_id, "exam_pack_35", source="test", reason="question-bank-exam-pack")
    first_pack = pack.post("/api/mock/sessions", json={"track_id": "snowpro-core", "mode": "lifetime-practice"})
    check(first_pack.status_code == 200 and len(first_pack.json()["questions"]) == 100, "Exam Pack lifetime Practice Mock starts")
    first_ids = {row["id"] for row in first_pack.json()["questions"]}
    pack.post(f"/api/mock/sessions/{first_pack.json()['session_id']}/submit", json={"reason": "learner"})
    second_pack = pack.post("/api/mock/sessions", json={"track_id": "snowpro-core", "mode": "lifetime-practice"})
    check(second_pack.status_code == 200, "Exam Pack lifetime Practice Mock repeats")
    second_ids = {row["id"] for row in second_pack.json()["questions"]}
    check(first_ids == second_ids, "Exam Pack lifetime Practice Mock keeps candidate-specific 100-question set")
    pack.post(f"/api/mock/sessions/{second_pack.json()['session_id']}/submit", json={"reason": "learner"})

    route_paths = {getattr(route, "path", "") for route in app.routes}
    check("/api/question-bank/status" not in route_paths and "/api/question-bank/import" not in route_paths, "bank authoring/status tooling is not exposed as candidate HTTP API")

    print("Question bank tier, privacy, blueprint, and Exam Pack checks passed.")


if __name__ == "__main__":
    main()
