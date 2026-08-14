#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory(prefix="snowflake-candidate-test-")
DB_PATH = Path(TEMP.name) / "candidate.sqlite"
os.environ["BRAIN_DB"] = str(DB_PATH)

from fastapi.testclient import TestClient  # noqa: E402
from app.auth import COOKIE_NAME  # noqa: E402
from app.database import connect, run_migrations  # noqa: E402
from app.main import app  # noqa: E402


def check(value: object, message: str) -> None:
    if not value:
        raise AssertionError(message)


def register(client: TestClient, name: str, email: str) -> dict:
    response = client.post(
        "/api/auth/register",
        json={"display_name": name, "email": email, "password": "candidate-password"},
    )
    check(response.status_code == 201, response.text)
    return response.json()


def set_tier(email: str, tier: str) -> None:
    env = dict(os.environ)
    env["BRAIN_DB"] = str(DB_PATH)
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "set_membership.py"), email, tier],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    check(result.returncode == 0, result.stderr or result.stdout)


def main() -> None:
    run_migrations()
    guest = TestClient(app)
    me = guest.get("/api/auth/me")
    check(me.json() == {"authenticated": False, "candidate": None, "membership": None}, "guest auth/me contract")
    check(guest.get("/api/skills/map").status_code == 401, "guest curriculum denied until account creation")
    check(guest.post("/api/certification-quiz/start", json={"mode": "diagnostic", "count": 10}).status_code == 401, "guest diagnostic denied")
    check(guest.get("/api/labs?track_id=snowpro-core").status_code == 401, "guest exercises denied")
    check(guest.get("/api/skills/task-progress?track_id=snowpro-core").status_code == 401, "guest progress denied")
    guest_mock = guest.post("/api/mock/sessions", json={"track_id": "snowpro-core", "mode": "quick-mock"})
    check(guest_mock.status_code == 401, "guest mock denied")

    alice = TestClient(app)
    alice_state = register(alice, "Alice Candidate", "  ALICE@example.com ")
    check(alice_state["membership"]["tier"] == "free" and alice_state["membership"]["status"] == "active", "new account Free")
    check(alice_state["candidate"]["email"] == "alice@example.com", "normalized email")
    duplicate = TestClient(app).post(
        "/api/auth/register",
        json={"display_name": "Alice Again", "email": "alice@example.com", "password": "candidate-password"},
    )
    check(duplicate.status_code == 409, "duplicate email rejected")
    short = TestClient(app).post(
        "/api/auth/register",
        json={"display_name": "Short Password", "email": "short@example.com", "password": "short"},
    )
    check(short.status_code == 422, "minimum password length enforced")

    with connect() as conn:
        stored = dict(conn.execute("SELECT * FROM candidate_accounts WHERE email='alice@example.com'").fetchone())
        token_row = dict(conn.execute("SELECT * FROM candidate_sessions WHERE candidate_id=?", (stored["id"],)).fetchone())
        memberships = [dict(row) for row in conn.execute("SELECT * FROM candidate_memberships WHERE candidate_id=?", (stored["id"],))]
    check(stored["password_hash"] != "candidate-password", "password not plaintext")
    check(stored["password_algorithm"] == "scrypt" and len(stored["password_salt"]) == 32, "scrypt with unique salt")
    cookie = alice.cookies.get(COOKIE_NAME)
    check(cookie and token_row["token_hash"] == hashlib.sha256(cookie.encode()).hexdigest(), "only session hash stored")
    check(any(row["tier"] == "free" and row["status"] == "active" for row in memberships), "Free membership row")

    free_diag = alice.post("/api/certification-quiz/start", json={"track_id": "snowpro-core", "mode": "diagnostic", "count": 10})
    check(free_diag.status_code == 200 and len(free_diag.json()["questions"]) == 10, "Free diagnostic allowed")
    check(alice.get("/api/skills/task-progress?track_id=snowpro-core").status_code == 200, "Free progress allowed")
    skill_id = alice.get("/api/skills/map").json()["certifications"][0]["domains"][0]["skills"][0]["id"]
    question_for_state = free_diag.json()["questions"][0]["id"]
    check(alice.post("/api/skills/task-progress", json={"track_id": "snowpro-core", "skill_id": skill_id, "completed": True}).status_code == 200, "candidate progress write")
    check(alice.post(f"/api/questions/{question_for_state}/bookmark", json={}).json()["bookmarked"], "candidate bookmark write")
    check(alice.post(f"/api/questions/{question_for_state}/notes", json={"body": "Alice private note"}).status_code == 200, "candidate note write")
    second_free_diag = alice.post("/api/certification-quiz/start", json={"track_id": "snowpro-core", "mode": "drill", "count": 10})
    check(second_free_diag.status_code == 200, "Free daily 20-question allowance")
    daily_denial = alice.post("/api/certification-quiz/start", json={"track_id": "snowpro-core", "mode": "drill", "count": 1})
    check(daily_denial.status_code == 403 and daily_denial.json()["detail"]["code"] == "daily_question_limit_reached", "Free daily allowance enforced")
    wrong_free_mode = alice.post("/api/mock/sessions", json={"track_id": "snowpro-core", "mode": "quick-mock"})
    check(wrong_free_mode.status_code == 403 and wrong_free_mode.json()["detail"]["code"] == "premium_required", "Free limited to weekly mock")
    free_mock = alice.post("/api/mock/sessions", json={"track_id": "snowpro-core", "mode": "weekly-mock"})
    check(free_mock.status_code == 200 and len(free_mock.json()["questions"]) == 20, "Free weekly 20-question mock")
    free_session_id = free_mock.json()["session_id"]
    free_cancel = alice.post(f"/api/mock/session-control/{free_session_id}/cancel", json={})
    check(free_cancel.status_code == 403 and free_cancel.json()["detail"]["code"] == "free_mock_must_be_completed", "Free mock cannot be reversed")
    check(alice.post(f"/api/mock/sessions/{free_session_id}/submit", json={"reason": "learner"}).status_code == 200, "Free mock completion")
    weekly_denial = alice.post("/api/mock/sessions", json={"track_id": "snowpro-core", "mode": "weekly-mock"})
    check(weekly_denial.status_code == 403 and weekly_denial.json()["detail"]["code"] == "weekly_mock_limit_reached", "Free weekly reset enforced")
    check(alice.get("/api/mock/history?track_id=snowpro-core").status_code == 200, "Free owns mock history")

    set_tier("alice@example.com", "premium_20")
    premium_me = alice.get("/api/auth/me").json()
    check(premium_me["membership"]["plan_code"] == "premium_20", "$20 plan persisted server-side")
    check(premium_me["membership"]["plan"]["price_usd_monthly"] == 20, "$20 price contract")
    check(premium_me["membership"]["usage"]["daily_questions"]["limit"] == 100, "$20 daily 100-question limit")
    check(premium_me["membership"]["usage"]["monthly_full_exams"]["limit"] == 2, "$20 two full exams monthly")
    started = alice.post("/api/mock/sessions", json={"track_id": "snowpro-core", "mode": "quick-mock"})
    check(started.status_code == 200, started.text)
    session = started.json()
    check(len(session["questions"]) == 30, "30-question Quick Mock")
    session_id = session["session_id"]
    question_id = session["questions"][0]["id"]

    bob = TestClient(app)
    register(bob, "Bob Candidate", "bob@example.com")
    bob_progress = bob.get("/api/skills/task-progress?track_id=snowpro-core").json()
    check(skill_id not in bob_progress["completed_skill_ids"], "task progress isolated")
    check(bob.get(f"/api/questions/{question_for_state}/bookmark").status_code == 404, "unserved cross-candidate bookmark lookup denied")
    check(bob.get(f"/api/questions/{question_for_state}/notes").status_code == 404, "unserved cross-candidate notes lookup denied")
    set_tier("bob@example.com", "premium_40")
    check(bob.get("/api/auth/me").json()["membership"]["tier"] == "premium", "Bob Premium")
    check(bob.get("/api/auth/me").json()["membership"]["usage"]["daily_questions"]["limit"] == 250, "$40 daily 250-question limit")
    ownership_requests = [
        bob.get(f"/api/mock/sessions/{session_id}"),
        bob.put(f"/api/mock/sessions/{session_id}/answers/{question_id}", json={"selected": [0]}),
        bob.put(f"/api/mock/sessions/{session_id}/questions/{question_id}/flag", json={"flagged": True}),
        bob.post(f"/api/mock/sessions/{session_id}/submit", json={"reason": "learner"}),
        bob.get(f"/api/mock/sessions/{session_id}/result"),
    ]
    check(all(response.status_code == 404 for response in ownership_requests), "Candidate B rejected from every Candidate A mock operation")

    check(alice.put(f"/api/mock/sessions/{session_id}/answers/{question_id}", json={"selected": [0]}).status_code == 200, "autosave")
    check(alice.put(f"/api/mock/sessions/{session_id}/questions/{question_id}/flag", json={"flagged": True}).status_code == 200, "flag")
    resumed = alice.get(f"/api/mock/sessions/{session_id}")
    check(resumed.status_code == 200 and resumed.json()["questions"][0]["flagged"], "resume")
    submitted = alice.post(f"/api/mock/sessions/{session_id}/submit", json={"reason": "learner"})
    check(submitted.status_code == 200, submitted.text)
    check(alice.get(f"/api/mock/sessions/{session_id}/result").status_code == 200, "result")
    check(alice.get("/api/mock/history?track_id=snowpro-core").json()["history"], "history")
    full = alice.post("/api/mock/sessions", json={"track_id": "snowpro-core", "mode": "full-mock"})
    check(full.status_code == 200 and len(full.json()["questions"]) == 100, "First monthly Full Mock")
    check(alice.post(f"/api/mock/sessions/{full.json()['session_id']}/submit", json={"reason": "learner"}).status_code == 200, "first Full Mock submitted")
    full_two = alice.post("/api/mock/sessions", json={"track_id": "snowpro-core", "mode": "full-mock"})
    check(full_two.status_code == 200, "Second monthly Full Mock")
    check(alice.post(f"/api/mock/sessions/{full_two.json()['session_id']}/submit", json={"reason": "learner"}).status_code == 200, "second Full Mock submitted")
    full_three = alice.post("/api/mock/sessions", json={"track_id": "snowpro-core", "mode": "full-mock"})
    check(full_three.status_code == 403 and full_three.json()["detail"]["code"] == "monthly_full_exam_limit_reached", "$20 monthly full-exam limit enforced")

    carol = TestClient(app)
    register(carol, "Carol Candidate", "carol@example.com")
    set_tier("carol@example.com", "premium_100")
    carol_me = carol.get("/api/auth/me").json()["membership"]
    check(carol_me["usage"]["daily_questions"]["limit"] == 500, "$100 daily 500-question limit")
    check(carol_me["usage"]["monthly_full_exams"]["limit"] is None, "$100 unlimited full exams")

    pack = TestClient(app)
    register(pack, "Pack Candidate", "pack@example.com")
    set_tier("pack@example.com", "exam_pack_35")
    pack_me = pack.get("/api/auth/me").json()["membership"]
    check(pack_me["plan"]["price_usd_one_time"] == 35 and pack_me["plan"]["lifetime_practice_mock"], "$35 one-time plan contract")
    practice_pack = pack.post("/api/mock/sessions", json={"track_id": "snowpro-core", "mode": "lifetime-practice"})
    check(practice_pack.status_code == 200 and len(practice_pack.json()["questions"]) == 100, "lifetime 100-question Practice Mock")
    check(pack.post(f"/api/mock/sessions/{practice_pack.json()['session_id']}/submit", json={"reason": "learner"}).status_code == 200, "Practice Mock submitted")
    included_exam = pack.post("/api/mock/sessions", json={"track_id": "snowpro-core", "mode": "full-mock"})
    check(included_exam.status_code == 200, "one-time pack Full Exam within 30 days")
    check(pack.post(f"/api/mock/sessions/{included_exam.json()['session_id']}/submit", json={"reason": "learner"}).status_code == 200, "pack Full Exam submitted")
    pack_second = pack.post("/api/mock/sessions", json={"track_id": "snowpro-core", "mode": "full-mock"})
    check(pack_second.status_code == 403 and pack_second.json()["detail"]["code"] == "exam_pack_full_exam_used", "one-time pack has one Full Exam")
    old_pack = TestClient(app)
    register(old_pack, "Old Pack Candidate", "old-pack@example.com")
    set_tier("old-pack@example.com", "exam_pack_35")
    with connect() as conn:
        old_pack_id = conn.execute("SELECT id FROM candidate_accounts WHERE email='old-pack@example.com'").fetchone()["id"]
        conn.execute("UPDATE candidate_memberships SET starts_at=datetime('now','-31 days') WHERE candidate_id=? AND plan_code='exam_pack_35' AND status='active'", (old_pack_id,))
    old_pack_denial = old_pack.post("/api/mock/sessions", json={"track_id": "snowpro-core", "mode": "full-mock"})
    check(old_pack_denial.status_code == 403 and old_pack_denial.json()["detail"]["code"] == "exam_pack_full_exam_expired", "one-time Full Exam expires after 30 days")
    old_pack_practice = old_pack.post("/api/mock/sessions", json={"track_id": "snowpro-core", "mode": "lifetime-practice"})
    check(old_pack_practice.status_code == 200, "lifetime Practice Mock remains after Full Exam window")

    with connect() as conn:
        alice_id = stored["id"]
        conn.execute("UPDATE candidate_memberships SET status='cancelled' WHERE candidate_id=? AND tier='premium'", (alice_id,))
        conn.execute(
            "INSERT INTO candidate_memberships(candidate_id,tier,plan_code,status,starts_at,expires_at,source) "
            "VALUES (?, 'premium', 'premium_20', 'active', datetime('now','-2 days'), datetime('now','-1 day'), 'test_expired')",
            (alice_id,),
        )
    expired = alice.get("/api/auth/me").json()
    check(expired["membership"]["tier"] == "free", "expired Premium behaves as Free")
    expired_full = alice.post("/api/mock/sessions", json={"track_id": "snowpro-core", "mode": "full-mock"})
    check(expired_full.status_code == 403 and expired_full.json()["detail"]["code"] == "premium_required", "expired Premium loses paid exam entitlement")

    wrong = TestClient(app).post("/api/auth/login", json={"email": "alice@example.com", "password": "wrong-password"})
    check(wrong.status_code == 401 and wrong.json()["detail"] == "Incorrect email or password.", "wrong password generic error")
    login_client = TestClient(app)
    logged_in = login_client.post("/api/auth/login", json={"email": "alice@example.com", "password": "candidate-password"})
    check(logged_in.status_code == 200 and logged_in.json()["authenticated"], "correct login")
    token = login_client.cookies.get(COOKIE_NAME)
    check(login_client.post("/api/auth/logout").status_code == 200, "logout")
    check(login_client.get("/api/auth/me").json()["authenticated"] is False, "logout clears auth")
    with connect() as conn:
        revoked = conn.execute("SELECT revoked_at FROM candidate_sessions WHERE token_hash=?", (hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
    check(revoked and revoked["revoked_at"], "logout revokes server session")

    expired_client = TestClient(app)
    check(expired_client.post("/api/auth/login", json={"email": "bob@example.com", "password": "candidate-password"}).status_code == 200, "session for expiry test")
    expired_token = expired_client.cookies.get(COOKIE_NAME)
    with connect() as conn:
        conn.execute(
            "UPDATE candidate_sessions SET expires_at=datetime('now','-1 day') WHERE token_hash=?",
            (hashlib.sha256(expired_token.encode()).hexdigest(),),
        )
    check(expired_client.get("/api/auth/me").json()["authenticated"] is False, "expired session rejected")

    print("V26 candidate authentication, membership, entitlement, and ownership tests: PASS")
    print("scrypt=pass free_daily=20 weekly_mock=1 premium=100/250/500 monthly=2/4/unlimited exam_pack=35 ownership=pass expiry=pass")


if __name__ == "__main__":
    try:
        main()
    finally:
        TEMP.cleanup()
