#!/usr/bin/env python3
"""Authenticated hostile-subscriber regression suite.

This is intentionally candidate-facing rather than an admin/unit-only test. Two
real application sessions are created and the attacker is assumed to know IDs
observed by the victim. The suite proves that legitimate authentication cannot
be escalated into question-bank enumeration, answer-key leakage, plan bypass,
or horizontal access to candidate state.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory(prefix="snowflake-authenticated-bank-isolation-")
os.environ["BRAIN_DB"] = str(Path(TEMP.name) / "bank-isolation.sqlite")
os.environ["SECURITY_RATE_LIMIT_ENABLED"] = "false"
os.environ["ACCOUNT_EMAIL_DELIVERY_MODE"] = "outbox"
os.environ.pop("VERCEL", None)
os.environ.pop("VERCEL_ENV", None)
os.environ.pop("DATABASE_URL", None)

from fastapi.testclient import TestClient  # noqa: E402

from app.database import connect, run_migrations  # noqa: E402
from app.main import app  # noqa: E402
from app.question_bank import import_question_bank_payload, validate_question_bank_payload  # noqa: E402
from app.skill_brain import flatten_skills  # noqa: E402
from app.talent_schema import ensure_talent_schema  # noqa: E402


PASSWORD = "candidate-password"
FORBIDDEN_PRE_SUBMIT_KEYS = {
    "correct",
    "correct_json",
    "correct_options",
    "correct_positions_json",
    "answer_key",
    "solution",
    "explanation",
    "rationale",
    "correct_rationale",
    "distractor_rationales",
    "distractor_rationales_json",
    "expected_answer",
    "grading",
    "score_key",
    "editorial_answer",
    "sme_notes",
    "review_notes",
}
FORBIDDEN_PRE_SUBMIT_FRAGMENTS = (
    "correct_answer",
    "correct_option",
    "answer_key",
    "solution",
    "explanation",
    "rationale",
    "expected_answer",
    "grading",
    "score_key",
    "editorial_answer",
    "sme_note",
    "review_note",
)


def check(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def register(client: TestClient, name: str, email: str) -> dict:
    response = client.post(
        "/api/auth/register",
        json={"display_name": name, "email": email, "password": PASSWORD},
    )
    check(response.status_code == 201, f"registration failed: {response.text}")
    return response.json()


def login(client: TestClient, email: str) -> dict:
    response = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    check(response.status_code == 200, f"login failed: {response.text}")
    return response.json()


def assert_private_no_store(response, label: str) -> None:
    value = response.headers.get("cache-control", "").lower()
    check("private" in value and "no-store" in value, f"{label} is shared-cacheable: {value!r}")


def assert_no_answer_material(value: object, label: str) -> None:
    def walk(node: object, path: str = "$") -> None:
        if isinstance(node, dict):
            for key, child in node.items():
                lowered = str(key).lower()
                if lowered in FORBIDDEN_PRE_SUBMIT_KEYS or any(fragment in lowered for fragment in FORBIDDEN_PRE_SUBMIT_FRAGMENTS):
                    raise AssertionError(f"{label} leaks answer-bearing key {path}.{key}")
                walk(child, f"{path}.{key}")
        elif isinstance(node, list):
            for index, child in enumerate(node):
                walk(child, f"{path}[{index}]")
    walk(value)


def synthetic_bank() -> dict:
    questions: list[dict] = []
    pools = {"free": 5, "practice": 4, "diagnostic": 3, "mock_reserved": 2}
    for skill in flatten_skills("snowpro-core"):
        for pool, count in pools.items():
            for index in range(1, count + 1):
                qid = f"isolation::{pool}::{skill['id']}::{index}"
                questions.append(
                    {
                        "id": qid,
                        "domain_id": skill["domain_id"],
                        "task_id": skill["id"],
                        "task_code": skill.get("task_code") or "",
                        "question_type": "scenario",
                        "cognitive_level": "apply",
                        "difficulty_band": "applied",
                        "bank_pool": pool,
                        "authoring_status": "active",
                        "authoring_version": "isolation-v1",
                        "question": f"Isolation scenario {index} for {skill['id']} in {pool}: choose the best option.",
                        "options": [f"Option {letter} {qid}" for letter in "ABCD"],
                        "correct_options": [1],
                        "correct_rationale": "The second option matches the isolated fixture rule.",
                        "distractor_rationales": ["Not best", "Best", "Not best", "Not best"],
                        "concepts": [skill["id"]],
                        "trap_tags": ["isolation"],
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
        "bank_version": "isolation-v1",
        "track_id": "snowpro-core",
        "exam_code": "COF-C03",
        "source_verified_at": "2026-08-14",
        "questions": questions,
    }


def main() -> None:
    run_migrations()
    ensure_talent_schema()
    bank = synthetic_bank()
    validation = validate_question_bank_payload(bank, source_name="authenticated-isolation.json")
    check(validation["valid"], f"synthetic bank invalid: {validation}")
    imported = import_question_bank_payload(bank, source_name="authenticated-isolation.json")
    check(int(imported["imported"]) == len(bank["questions"]), "synthetic isolation bank import incomplete")

    victim = TestClient(app)
    victim_email = "victim-isolation@example.com"
    victim_state = register(victim, "Victim Candidate", victim_email)
    victim_id = int(victim_state["candidate"]["id"])

    attacker = TestClient(app)
    attacker_state = register(attacker, "Hostile Candidate", "hostile-isolation@example.com")
    attacker_id = int(attacker_state["candidate"]["id"])
    check(attacker_id != victim_id, "attacker and victim identities collapsed")

    check(attacker.get("/api/questions").status_code == 403, "authenticated candidate can enumerate bulk questions")
    check(attacker.get("/api/practice-tests/arbitrary/questions").status_code == 403, "authenticated candidate can bulk-read a test")
    practice_inventory = attacker.get("/api/practice-tests")
    check(practice_inventory.status_code == 200 and practice_inventory.json() == {"tests": []}, "internal practice-test inventory leaked")
    assert_private_no_store(practice_inventory, "practice-test inventory boundary")

    drill = victim.post(
        "/api/certification-quiz/start",
        json={"track_id": "snowpro-core", "mode": "drill", "count": 10},
    )
    check(drill.status_code == 200 and len(drill.json().get("questions") or []) == 10, drill.text)
    assert_private_no_store(drill, "practice question delivery")
    assert_no_answer_material(drill.json(), "pre-submit practice payload")
    victim_question = str(drill.json()["questions"][0]["id"])
    victim_skill = str(flatten_skills("snowpro-core")[0]["id"])

    direct_victim_question = victim.get(f"/api/questions/{victim_question}")
    check(direct_victim_question.status_code == 200, "owner cannot retrieve legitimately served question")
    assert_private_no_store(direct_victim_question, "direct served question")
    assert_no_answer_material(direct_victim_question.json(), "direct served question")

    guessed = attacker.get(f"/api/questions/{victim_question}")
    check(guessed.status_code == 404, "known question ID grants another candidate access")
    assert_private_no_store(guessed, "denied guessed question")
    check("explanation" not in guessed.text.lower() and "correct_json" not in guessed.text.lower(), "denial leaks answer metadata")

    attacker_attempt = attacker.post(
        f"/api/questions/{victim_question}/attempt",
        json={"selected": [1], "mode": "drill", "confidence": 5, "response_time_ms": 500},
    )
    check(attacker_attempt.status_code == 404, "known question ID lets attacker write victim learning evidence")
    assert_private_no_store(attacker_attempt, "denied cross-candidate attempt")
    attacker_grade = attacker.post(
        "/api/quiz/grade",
        json={"answers": [{"question_id": victim_question, "selected": [1]}]},
    )
    check(attacker_grade.status_code == 404, "known question ID lets attacker use grade endpoint as answer oracle")
    assert_private_no_store(attacker_grade, "denied cross-candidate grade")
    check("explanation" not in attacker_grade.text.lower() and "correct" not in attacker_grade.text.lower(), "grade denial leaks answer metadata")

    resources = victim.get(f"/api/skills/{victim_skill}/resources?track_id=snowpro-core&limit=50")
    check(resources.status_code == 200, resources.text)
    assert_private_no_store(resources, "skill resources")
    check(resources.json().get("questions") == [], "skill resources expose raw mapped question inventory")
    check(resources.json().get("mapping_strategy") == "candidate_delivery_only", "skill resource boundary not explicit")
    assert_no_answer_material(resources.json(), "skill resources")

    check(attacker.get("/api/intelligence/adaptive/question-ids?limit=100").status_code == 404, "adaptive question IDs are enumerable")
    check(attacker.get("/api/intelligence/evidence-audit").status_code == 404, "candidate can reach evidence audit admin API")
    check(attacker.post("/api/intelligence/evidence-review", json={"question_id": victim_question, "skill_id": victim_skill, "reviewed": True}).status_code == 404, "candidate can mutate evidence review state")
    check(attacker.post("/api/intelligence/reindex-skill-map").status_code == 404, "candidate can reindex administrative question mapping")

    victim_bookmark = victim.post(f"/api/questions/{victim_question}/bookmark", json={})
    check(victim_bookmark.status_code == 200, victim_bookmark.text)
    victim_note = victim.post(f"/api/questions/{victim_question}/notes", json={"body": "victim-only-note"})
    check(victim_note.status_code == 200, victim_note.text)

    for method, path, body in (
        ("get", f"/api/questions/{victim_question}/bookmark", None),
        ("post", f"/api/questions/{victim_question}/bookmark", {}),
        ("get", f"/api/questions/{victim_question}/notes", None),
        ("post", f"/api/questions/{victim_question}/notes", {"body": "attacker-write"}),
    ):
        response = getattr(attacker, method)(path, **({"json": body} if body is not None else {}))
        check(response.status_code == 404, f"attacker crossed question state ownership via {method.upper()} {path}: {response.status_code}")

    attempt = victim.post(
        f"/api/questions/{victim_question}/attempt",
        json={"selected": [0], "mode": "drill", "confidence": 5, "response_time_ms": 900},
    )
    check(attempt.status_code == 200, attempt.text)
    victim_mistakes = victim.get("/api/intelligence/mistake-notebook?track_id=snowpro-core&status=active")
    check(victim_mistakes.status_code == 200, victim_mistakes.text)
    assert_private_no_store(victim_mistakes, "mistake notebook")
    attacker_patch = attacker.patch(
        f"/api/intelligence/mistake-notebook/{victim_question}",
        json={"status": "mastered", "note": "attacker"},
    )
    check(attacker_patch.status_code == 404, "attacker can mutate another candidate's mistake notebook")

    progress_update = victim.post(
        "/api/skills/task-progress",
        json={"track_id": "snowpro-core", "skill_id": victim_skill, "completed": True},
    )
    check(progress_update.status_code == 200, progress_update.text)
    attacker_progress = attacker.get(
        f"/api/skills/task-progress?track_id=snowpro-core&candidate_id={victim_id}"
    )
    check(attacker_progress.status_code == 200, attacker_progress.text)
    check(victim_skill not in set(attacker_progress.json().get("completed_skill_ids") or []), "candidate_id query injection exposed victim progress")

    victim_plan = victim.put(
        "/api/intelligence/study-plan/preferences",
        json={"track_id": "snowpro-core", "exam_date": "2026-12-31", "daily_minutes": 73, "days_per_week": 4},
    )
    check(victim_plan.status_code == 200, victim_plan.text)
    attacker_plan = attacker.get(
        f"/api/intelligence/study-plan?track_id=snowpro-core&candidate_id={victim_id}"
    )
    check(attacker_plan.status_code == 200, attacker_plan.text)
    check(attacker_plan.json().get("preferences", {}).get("daily_minutes") != 73, "candidate_id query injection exposed victim study plan")
    assert_private_no_store(attacker_plan, "study plan")

    credential_uid = f"cred-{uuid4()}"
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO candidate_credentials(
              credential_uid,candidate_id,provider,provider_badge_id,credential_name,
              issuer_name,issued_to_name,credential_url,verification_status
            ) VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (
                credential_uid,
                victim_id,
                "credly",
                f"badge-{uuid4()}",
                "SnowPro Core",
                "Snowflake",
                "Victim Candidate",
                "https://www.credly.com/badges/00000000-0000-0000-0000-000000000001/public_url",
                "verified",
            ),
        )
    attacker_credentials = attacker.get(f"/api/credentials?candidate_id={victim_id}")
    check(attacker_credentials.status_code == 200, attacker_credentials.text)
    check(credential_uid not in json.dumps(attacker_credentials.json()), "candidate_id query injection exposed victim credential")
    assert_private_no_store(attacker_credentials, "credentials")
    check(attacker.delete(f"/api/credentials/{credential_uid}").status_code == 404, "attacker can delete victim credential")
    check(attacker.post(f"/api/credentials/{credential_uid}/reverify", json={}).status_code == 404, "attacker can reverify victim credential")
    victim_credentials = victim.get("/api/credentials")
    check(credential_uid in json.dumps(victim_credentials.json()), "victim credential disappeared after attacker operations")

    too_many = attacker.post(
        "/api/certification-quiz/start",
        json={"track_id": "snowpro-core", "mode": "drill", "count": 21, "plan_code": "premium_500", "is_premium": True},
    )
    check(too_many.status_code == 403, f"Free account bypassed daily quota: {too_many.status_code} {too_many.text}")
    check(attacker.post("/api/certification-quiz/start", json={"track_id": "snowpro-core", "mode": "drill", "count": 0}).status_code == 422, "zero practice count accepted")
    check(attacker.post("/api/certification-quiz/start", json={"track_id": "snowpro-core", "mode": "drill", "count": 501}).status_code == 422, "oversized practice count accepted")
    premium_mock_forge = attacker.post(
        "/api/mock/sessions",
        json={"track_id": "snowpro-core", "mode": "full-mock", "plan_code": "premium_500", "is_premium": True, "membership": {"tier": "premium"}},
    )
    check(premium_mock_forge.status_code == 403, f"client-supplied premium state bypassed server entitlement: {premium_mock_forge.status_code}")
    check(attacker.post("/api/mock/sessions", json={"track_id": "snowpro-core", "mode": "admin-mock"}).status_code == 422, "unknown mock mode accepted")

    weekly = victim.post("/api/mock/sessions", json={"track_id": "snowpro-core", "mode": "weekly-mock"})
    check(weekly.status_code == 200 and len(weekly.json().get("questions") or []) == 30, weekly.text)
    assert_private_no_store(weekly, "weekly mock start")
    assert_no_answer_material(weekly.json().get("questions") or [], "pre-submit weekly mock questions")
    session_id = int(weekly.json()["session_id"])
    mock_question = str(weekly.json()["questions"][0]["id"])

    attack_calls = (
        attacker.get(f"/api/mock/sessions/{session_id}"),
        attacker.put(f"/api/mock/sessions/{session_id}/answers/{mock_question}", json={"selected": [1]}),
        attacker.put(f"/api/mock/sessions/{session_id}/questions/{mock_question}/flag", json={"flagged": True}),
        attacker.post(f"/api/mock/sessions/{session_id}/submit", json={"reason": "learner"}),
        attacker.get(f"/api/mock/sessions/{session_id}/result"),
        attacker.get(f"/api/intelligence/mock-remediation/{session_id}"),
    )
    for response in attack_calls:
        check(response.status_code in {403, 404}, f"cross-candidate mock operation succeeded: {response.status_code} {response.text}")

    own_session = victim.get(f"/api/mock/sessions/{session_id}")
    check(own_session.status_code == 200, own_session.text)
    assert_private_no_store(own_session, "mock resume")
    assert_no_answer_material(own_session.json().get("questions") or [], "pre-submit mock resume questions")

    secondary = TestClient(app)
    login(secondary, victim_email)
    sessions = victim.get("/api/auth/sessions")
    check(sessions.status_code == 200, sessions.text)
    assert_private_no_store(sessions, "session list")
    rows = sessions.json().get("sessions") or []
    other_rows = [row for row in rows if not row.get("current")]
    check(other_rows, f"second victim session not listed: {rows}")
    secondary_session_id = int(other_rows[0]["id"])
    check(attacker.delete(f"/api/auth/sessions/{secondary_session_id}").status_code == 404, "attacker can revoke victim session")
    check(secondary.get("/api/skills/map").status_code == 200, "attacker denial changed victim session")
    owner_revoke = victim.delete(f"/api/auth/sessions/{secondary_session_id}")
    check(owner_revoke.status_code == 204, owner_revoke.text)
    check(secondary.get("/api/skills/map").status_code == 401, "revoked session remains usable")

    print(
        "Authenticated bank isolation: PASS "
        "(answers hidden, no raw bank/admin ID inventory, grade/attempt oracles blocked, server entitlements, candidate ownership, session revocation)"
    )


if __name__ == "__main__":
    main()
