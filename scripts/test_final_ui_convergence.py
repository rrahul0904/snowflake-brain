#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory(prefix="snowflake-final-convergence-")
os.environ["BRAIN_DB"] = str(Path(TEMP.name) / "convergence.sqlite")
os.environ["AFFILIATE_RESOURCES_ENABLED"] = "false"

from fastapi.testclient import TestClient  # noqa: E402
from app.database import connect  # noqa: E402
from app.main import app  # noqa: E402
from app.skill_brain import flatten_skills  # noqa: E402


def check(value: object, message: str) -> None:
    if not value:
        raise AssertionError(message)


def register(client: TestClient, email: str) -> int:
    response = client.post(
        "/api/auth/register",
        json={"display_name": "Convergence Candidate", "email": email, "password": "candidate-password"},
    )
    check(response.status_code == 201, response.text)
    return int(response.json()["candidate"]["id"])


def seed_replay_session(candidate_id: int) -> tuple[int, str]:
    with connect() as conn:
        question = conn.execute(
            """
            SELECT q.id,q.options_json,q.correct_json
            FROM questions q
            WHERE q.track_id='snowpro-core'
            ORDER BY q.id
            LIMIT 1
            """
        ).fetchone()
        check(question is not None, "seeded certification question is required")
        cursor = conn.execute(
            """
            INSERT INTO exam_sessions(
              track_id,mode,started_at,score,total_questions,status,duration_seconds,
              configuration_json,candidate_id
            ) VALUES ('snowpro-core','exam_quick_mock',datetime('now'),0,1,'in_progress',2700,'{}',?)
            """,
            (candidate_id,),
        )
        session_id = int(cursor.lastrowid)
        conn.execute(
            """
            INSERT INTO exam_session_questions(
              session_id,question_id,position,options_json,correct_positions_json,flagged
            ) VALUES (?,?,?,?,?,0)
            """,
            (
                session_id,
                question["id"],
                1,
                question["options_json"],
                question["correct_json"],
            ),
        )
    return session_id, str(question["id"])


def task_review_contract(client: TestClient, other: TestClient) -> None:
    skill = flatten_skills("snowpro-core")[0]
    payload = {"track_id": "snowpro-core", "skill_id": skill["id"]}

    initial = client.get(f"/api/intelligence/task-review?track_id=snowpro-core&skill_id={skill['id']}")
    check(initial.status_code == 200 and initial.json()["review"] is None, initial.text)

    scheduled = client.post("/api/intelligence/task-review", json=payload)
    check(scheduled.status_code == 200, scheduled.text)
    first = scheduled.json()["review"]
    check(first["status"] == "active" and first["interval_days"] == 1, f"first review must be tomorrow: {first}")

    duplicate = client.post("/api/intelligence/task-review", json=payload)
    check(duplicate.status_code == 200, duplicate.text)
    second = duplicate.json()["review"]
    check(second["created_at"] == first["created_at"], "task scheduling must be idempotent")
    check(second["next_review_at"] == first["next_review_at"], "duplicate schedule must not push the review date")

    reset = client.post("/api/intelligence/task-review/reset", json=payload)
    check(reset.status_code == 200 and reset.json()["review"]["interval_days"] == 0, reset.text)
    due = client.get("/api/intelligence/due-today?track_id=snowpro-core&limit=20")
    check(due.status_code == 200, due.text)
    check(due.json()["task_due_count"] == 1, f"reset task review must enter Due Today: {due.json()}")
    check(due.json()["due_count"] >= due.json()["task_due_count"], "combined due count includes task reviews")

    reviewed = client.post("/api/intelligence/task-review/reviewed", json=payload)
    check(reviewed.status_code == 200, reviewed.text)
    review = reviewed.json()["review"]
    check(review["review_count"] == 1 and review["interval_days"] == 3, f"successful review advances interval: {review}")

    other_status = other.get(f"/api/intelligence/task-review?track_id=snowpro-core&skill_id={skill['id']}")
    check(other_status.status_code == 200 and other_status.json()["review"] is None, "task review state must be candidate isolated")

    invalid = client.post("/api/intelligence/task-review", json={"track_id": "snowpro-core", "skill_id": "not-a-real-task"})
    check(invalid.status_code == 404, f"invalid task must fail closed: {invalid.status_code} {invalid.text}")


def mock_replay_contract(client: TestClient, other: TestClient, candidate_id: int) -> None:
    session_id, question_id = seed_replay_session(candidate_id)

    before = client.get(f"/api/mock/sessions/{session_id}/replay")
    check(before.status_code == 409, f"replay must be unavailable before submission: {before.status_code}")

    observed = client.post(
        f"/api/mock/sessions/{session_id}/events",
        json={
            "event_type": "question_viewed",
            "question_id": question_id,
            "metadata": {
                "position": 1,
                "question": "must never persist",
                "correct_answer": [0],
                "explanation": "must never persist",
            },
        },
    )
    check(observed.status_code == 200, observed.text)

    answer1 = client.put(f"/api/mock/sessions/{session_id}/answers/{question_id}", json={"selected": [0]})
    check(answer1.status_code == 200, answer1.text)
    answer2 = client.put(f"/api/mock/sessions/{session_id}/answers/{question_id}", json={"selected": [1]})
    check(answer2.status_code == 200, answer2.text)
    flagged = client.put(f"/api/mock/sessions/{session_id}/questions/{question_id}/flag", json={"flagged": True})
    check(flagged.status_code == 200, flagged.text)

    nav_from = client.post(
        f"/api/mock/sessions/{session_id}/events",
        json={"event_type": "question_navigated_from", "question_id": question_id, "metadata": {"position": 1, "to_position": 1}},
    )
    check(nav_from.status_code == 200, nav_from.text)

    with connect() as conn:
        metadata_rows = [json.loads(row["metadata_json"] or "{}") for row in conn.execute(
            "SELECT metadata_json FROM exam_session_events WHERE session_id=? ORDER BY id",
            (session_id,),
        )]
    check(metadata_rows, "replay events must be persisted")
    forbidden = {"question", "correct_answer", "correct", "explanation", "answer_key"}
    check(all(not (forbidden & set(item)) for item in metadata_rows), f"replay metadata leaked answer/content fields: {metadata_rows}")

    other_replay = other.get(f"/api/mock/sessions/{session_id}/replay")
    check(other_replay.status_code == 404, "mock replay must enforce candidate ownership")

    submit = client.post(f"/api/mock/sessions/{session_id}/submit", json={"reason": "learner"})
    check(submit.status_code == 200, submit.text)
    replay = client.get(f"/api/mock/sessions/{session_id}/replay")
    check(replay.status_code == 200, replay.text)
    body = replay.json()
    check(body["event_count"] >= 5, f"expected replay event stream: {body}")
    check(len(body["questions"]) == 1, "replay has one seeded question")
    q = body["questions"][0]
    check(q["answer_change_count"] == 1, f"answer change count must come from persisted events: {q}")
    check(q["flag_added_count"] == 1 and q["final_flagged"] is True, f"flag history must be replayed: {q}")
    serialized = json.dumps(body).lower()
    check("explanation" not in serialized and "correct_positions" not in serialized, "replay payload must not expose answer-oracle content")
    check("interaction metadata only" in body["integrity_note"].lower(), "replay integrity note is explicit")


def drill_filter_contract(client: TestClient) -> None:
    skill = flatten_skills("snowpro-core")[0]
    response = client.post(
        "/api/certification-quiz/start",
        json={
            "track_id": "snowpro-core",
            "mode": "drill",
            "count": 1,
            "skill_id": skill["id"],
            "domain_id": skill["domain_id"],
            "difficulty": "medium",
            "unanswered_only": True,
        },
    )
    check(response.status_code == 200, response.text)
    body = response.json()
    check(len(body.get("questions") or []) == 1, f"filtered drill must honor requested count: {body}")
    question = body["questions"][0]
    check(str(question.get("difficulty") or "").lower() == "medium", f"difficulty filter must be honored: {question}")

    js = (ROOT / "frontend" / "views" / "practice-v26.js").read_text(encoding="utf-8")
    for token in ("data-difficulty", "data-unanswered", "data-session-count", "difficulty: state.difficulty", "unanswered_only: state.unansweredOnly"):
        check(token in js, f"Targeted Drill UI contract missing: {token}")
    for forbidden in ("confidence gap", "AI-selected difficulty"):
        check(forbidden.lower() not in js.lower(), f"unsupported drill control leaked into UI: {forbidden}")


def frontend_integrity_contract() -> None:
    session_js = (ROOT / "frontend" / "views" / "exam-session-v26.js").read_text(encoding="utf-8")
    result_js = (ROOT / "frontend" / "views" / "exam-result-v26.js").read_text(encoding="utf-8")
    lesson_js = (ROOT / "frontend" / "views" / "lesson-v26.js").read_text(encoding="utf-8")
    due_js = (ROOT / "frontend" / "views" / "due-v26.js").read_text(encoding="utf-8")
    globe_js = (ROOT / "frontend" / "components" / "globe.js").read_text(encoding="utf-8")

    check("recordMockReplayEvent" in session_js and "question_navigated_to" in session_js, "exam player records navigation replay events")
    for label in ("Changed Answer", "Slowest", "Mock Replay"):
        check(label in result_js, f"result replay UI missing {label}")
    check("Add to Review" in lesson_js and "In Review Queue" in lesson_js, "lesson exposes real task review state")
    check("Concept review" in due_js and "Question review" in due_js, "Due Today separates concept and question review")
    check("renderActivityGlobe" in globe_js and "WORLD_GEOMETRY_URL" in globe_js, "canonical globe must remain intact")


def main() -> None:
    with TestClient(app) as client, TestClient(app) as other:
        candidate_id = register(client, "convergence-a@example.com")
        register(other, "convergence-b@example.com")
        task_review_contract(client, other)
        mock_replay_contract(client, other, candidate_id)
        drill_filter_contract(client)
    frontend_integrity_contract()
    print("Final UI convergence contracts passed: task review, mock replay privacy/ownership, real drill filters, and globe preservation.")


if __name__ == "__main__":
    main()
