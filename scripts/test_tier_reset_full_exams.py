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
TEMP = tempfile.TemporaryDirectory(prefix="snowflake-tier-reset-")
DB_PATH = Path(TEMP.name) / "tier-reset.sqlite"
os.environ["BRAIN_DB"] = str(DB_PATH)
os.environ["AFFILIATE_RESOURCES_ENABLED"] = "false"

from fastapi.testclient import TestClient  # noqa: E402
from app.database import connect, run_migrations  # noqa: E402
from app.entitlements import apply_membership_plan  # noqa: E402
from app.main import app  # noqa: E402
from app.question_bank import import_question_bank_payload  # noqa: E402
from app.skill_brain import flatten_skills  # noqa: E402


def check(value: object, message: str) -> None:
    if not value:
        raise AssertionError(message)


def bank() -> dict:
    questions = []
    pools = {"free": 6, "practice": 7, "diagnostic": 4, "mock_reserved": 12}
    for skill in flatten_skills("snowpro-core"):
        for pool, amount in pools.items():
            for index in range(1, amount + 1):
                qid = f"reset::{pool}::{skill['id']}::{index}"
                questions.append(
                    {
                        "id": qid,
                        "domain_id": skill["domain_id"],
                        "task_id": skill["id"],
                        "task_code": skill.get("task_code") or "",
                        "question_type": "scenario",
                        "cognitive_level": "apply",
                        "difficulty_band": ["foundation", "applied", "exam", "challenge"][(index - 1) % 4],
                        "bank_pool": pool,
                        "authoring_status": "active",
                        "authoring_version": "reset-test-v1",
                        "question": f"Reset test {pool} {skill['id']} #{index}: which Snowflake design best satisfies the stated requirement?",
                        "options": [f"A {qid}", f"B {qid}", f"C {qid}", f"D {qid}"],
                        "correct_options": [1],
                        "correct_rationale": f"Option B is correct for {qid} because it matches the tested Snowflake task boundary.",
                        "distractor_rationales": [
                            "A addresses a different constraint.",
                            "B matches the requirement.",
                            "C adds an unrelated behavior.",
                            "D does not satisfy the scenario.",
                        ],
                        "concepts": [skill["id"], pool],
                        "trap_tags": ["reset-test"],
                        "source_refs": [{"title": "Snowflake docs", "url": "https://docs.snowflake.com/en/user-guide/intro-key-concepts"}],
                        "source_verified_at": "2026-08-14",
                    }
                )
    return {
        "schema_version": "snowflake-question-bank-v1",
        "bank_version": "reset-test-v1",
        "track_id": "snowpro-core",
        "exam_code": "COF-C03",
        "source_verified_at": "2026-08-14",
        "questions": questions,
    }


def register(client: TestClient, email: str) -> int:
    response = client.post("/api/auth/register", json={"display_name": "Reset Candidate", "email": email, "password": "candidate-password"})
    check(response.status_code == 201, response.text)
    return int(response.json()["candidate"]["id"])


def ids(payload: dict) -> set[str]:
    return {str(row["id"]) for row in payload.get("questions") or []}


def internal_config(session_id: int) -> dict:
    with connect() as conn:
        row = conn.execute("SELECT configuration_json FROM exam_sessions WHERE id=?", (session_id,)).fetchone()
    return json.loads(row["configuration_json"] or "{}")


def domain_counts(session_id: int) -> Counter:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT m.domain_id
            FROM exam_session_questions sq
            JOIN question_bank_metadata m ON m.question_id=sq.question_id
            WHERE sq.session_id=?
            """,
            (session_id,),
        ).fetchall()
    return Counter(row["domain_id"] for row in rows)


def submit(client: TestClient, session_id: int) -> None:
    response = client.post(f"/api/mock/sessions/{session_id}/submit", json={"reason": "learner"})
    check(response.status_code == 200, response.text)


def simulate_reset_boundary(candidate_id: int, exam_type: str, *, session_mode: str, session_age_sql: str, prior_window_key: str) -> None:
    """Move both durable usage and its reservation ledger into a prior window.

    Production reset windows advance with wall-clock time. This test cannot
    change the process clock, so a synthetic reset must update both persisted
    pieces of the entitlement state; backdating only exam_sessions would leave
    the atomic reservation's current window key intentionally occupied.
    """
    with connect() as conn:
        conn.execute(
            f"UPDATE exam_sessions SET started_at={session_age_sql}, finished_at={session_age_sql} WHERE candidate_id=? AND mode=?",
            (candidate_id, session_mode),
        )
        conn.execute(
            """
            UPDATE exam_entitlement_reservations
               SET window_key=?
             WHERE candidate_id=? AND exam_type=? AND status='committed'
            """,
            (prior_window_key, candidate_id, exam_type),
        )


def main() -> None:
    run_migrations()
    imported = import_question_bank_payload(bank(), source_name="tier-reset-test.json")
    check(imported["tasks_covered"] == 19, "reset fixture covers all 19 tasks")

    # Daily practice allowance resets by UTC date.
    daily = TestClient(app)
    daily_id = register(daily, "daily-reset@example.com")
    first = daily.post("/api/certification-quiz/start", json={"track_id": "snowpro-core", "mode": "drill", "count": 20})
    check(first.status_code == 200 and len(first.json()["questions"]) == 20, "Free daily allowance serves 20 questions")
    blocked = daily.post("/api/certification-quiz/start", json={"track_id": "snowpro-core", "mode": "drill", "count": 1})
    check(blocked.status_code == 403, "Free daily practice blocks after 20")
    with connect() as conn:
        conn.execute("UPDATE candidate_daily_question_usage SET usage_date=date('now','-1 day') WHERE candidate_id=?", (daily_id,))
    reset_daily = daily.post("/api/certification-quiz/start", json={"track_id": "snowpro-core", "mode": "drill", "count": 1})
    check(reset_daily.status_code == 200, "daily question allowance reopens after UTC-day reset")

    # Free receives one 30-question, 45-minute, all-domain mock per week.
    free = TestClient(app)
    free_id = register(free, "weekly-reset@example.com")
    first_week = free.post("/api/mock/sessions", json={"track_id": "snowpro-core", "mode": "weekly-mock"})
    check(first_week.status_code == 200, first_week.text)
    first_payload = first_week.json()
    check(len(first_payload["questions"]) == 30, "Free weekly mock has 30 questions")
    check(int(first_payload["duration_seconds"]) == 2700, "Free weekly mock is timed for 45 minutes")
    check(domain_counts(int(first_payload["session_id"])) == Counter({"features-architecture": 9, "account-governance": 6, "loading-connectivity": 5, "performance-transformation": 7, "data-collaboration": 3}), "Free weekly mock covers full blueprint")
    first_ids = ids(first_payload)
    first_config = internal_config(int(first_payload["session_id"]))
    check(first_config.get("reset_cadence") == "weekly" and first_config.get("rotates_questions") is True, "weekly reset policy stored server-side")
    check(first_config.get("reset_window_key"), "weekly sitting has server window key")
    submit(free, int(first_payload["session_id"]))

    same_week = free.post("/api/mock/sessions", json={"track_id": "snowpro-core", "mode": "weekly-mock"})
    check(same_week.status_code == 403, "second Free mock is blocked in same weekly window")

    # Simulate crossing the weekly boundary. The allowance reopens and the
    # prior sitting's questions are hard-excluded when sufficient inventory exists.
    simulate_reset_boundary(
        free_id,
        "weekly_mock",
        session_mode="exam_weekly_mock",
        session_age_sql="datetime('now','-8 days')",
        prior_window_key="test-previous-week",
    )
    next_week = free.post("/api/mock/sessions", json={"track_id": "snowpro-core", "mode": "weekly-mock"})
    check(next_week.status_code == 200, next_week.text)
    next_payload = next_week.json()
    check(len(next_payload["questions"]) == 30, "weekly reset restores Free 30Q mock")
    check(first_ids.isdisjoint(ids(next_payload)), "weekly reset generates a fresh set without immediate repeats")
    next_config = internal_config(int(next_payload["session_id"]))
    check(next_config.get("reset_exclusion_applied") is True and int(next_config.get("prior_questions_avoided") or 0) >= 30, "fresh-set exclusion was actually invoked")
    submit(free, int(next_payload["session_id"]))

    # Premium 100 receives two Full Exams per month. Each same-window sitting
    # rotates away from already used Full Exam questions while inventory allows.
    premium = TestClient(app)
    premium_id = register(premium, "monthly-reset@example.com")
    apply_membership_plan(premium_id, "premium_20", source="test", reason="tier-reset-test")
    p1 = premium.post("/api/mock/sessions", json={"track_id": "snowpro-core", "mode": "full-mock"})
    check(p1.status_code == 200 and len(p1.json()["questions"]) == 100, "first Premium Full Exam starts")
    p1_ids = ids(p1.json())
    submit(premium, int(p1.json()["session_id"]))
    p2 = premium.post("/api/mock/sessions", json={"track_id": "snowpro-core", "mode": "full-mock"})
    check(p2.status_code == 200 and len(p2.json()["questions"]) == 100, "second Premium Full Exam starts")
    p2_ids = ids(p2.json())
    check(p1_ids.isdisjoint(p2_ids), "Premium same-month Full Exams rotate to a fresh set")
    p2_config = internal_config(int(p2.json()["session_id"]))
    check(p2_config.get("reset_cadence") == "monthly" and p2_config.get("reset_exclusion_applied") is True, "monthly fresh-set policy invoked")
    submit(premium, int(p2.json()["session_id"]))
    p3_blocked = premium.post("/api/mock/sessions", json={"track_id": "snowpro-core", "mode": "full-mock"})
    check(p3_blocked.status_code == 403, "Premium 100 blocks a third Full Exam in same month")

    simulate_reset_boundary(
        premium_id,
        "full_exam",
        session_mode="exam_full_mock",
        session_age_sql="datetime('now','start of month','-2 days')",
        prior_window_key="test-previous-month",
    )
    p3 = premium.post("/api/mock/sessions", json={"track_id": "snowpro-core", "mode": "full-mock"})
    check(p3.status_code == 200 and len(p3.json()["questions"]) == 100, "monthly reset restores Premium Full Exam allowance")
    check(p2_ids.isdisjoint(ids(p3.json())), "new monthly window avoids the immediately previous Full Exam set")
    submit(premium, int(p3.json()["session_id"]))

    # Premium 250 and 500 retain their configured monthly/full-exam contracts.
    simulate_reset_boundary(
        premium_id,
        "full_exam",
        session_mode="exam_full_mock",
        session_age_sql="datetime('now','start of month','-2 days')",
        prior_window_key="test-previous-month-after-p3",
    )
    apply_membership_plan(premium_id, "premium_40", source="test", reason="tier-reset-test")
    membership_250 = premium.get("/api/auth/me").json()["membership"]
    check(membership_250["usage"]["monthly_full_exams"]["limit"] == 4, "Premium 250 keeps four Full Exams per month")
    apply_membership_plan(premium_id, "premium_100", source="test", reason="tier-reset-test")
    membership_500 = premium.get("/api/auth/me").json()["membership"]
    check(membership_500["usage"]["monthly_full_exams"]["limit"] is None, "Premium 500 keeps unlimited Full Exams")

    # Exam Pack is intentionally fixed and is the exception to reset rotation.
    pack = TestClient(app)
    pack_id = register(pack, "fixed-pack@example.com")
    apply_membership_plan(pack_id, "exam_pack_35", source="test", reason="tier-reset-test")
    pack1 = pack.post("/api/mock/sessions", json={"track_id": "snowpro-core", "mode": "lifetime-practice"})
    check(pack1.status_code == 200, pack1.text)
    pack1_ids = ids(pack1.json())
    pack_config = internal_config(int(pack1.json()["session_id"]))
    check(pack_config.get("reset_cadence") == "fixed" and pack_config.get("rotates_questions") is False, "Exam Pack fixed set does not reset")
    submit(pack, int(pack1.json()["session_id"]))
    pack2 = pack.post("/api/mock/sessions", json={"track_id": "snowpro-core", "mode": "lifetime-practice"})
    check(pack2.status_code == 200 and ids(pack2.json()) == pack1_ids, "Exam Pack lifetime set remains identical")

    print("Daily, weekly, monthly, fresh-question rotation, and fixed Exam Pack reset checks passed.")


if __name__ == "__main__":
    main()
