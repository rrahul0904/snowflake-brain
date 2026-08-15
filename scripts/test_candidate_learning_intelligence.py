#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory(prefix="snowflake-learning-intelligence-")
DB_PATH = Path(TEMP.name) / "learning.sqlite"
os.environ["BRAIN_DB"] = str(DB_PATH)
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
        json={"display_name": "Learning Candidate", "email": email, "password": "candidate-password"},
    )
    check(response.status_code == 201, response.text)
    return int(response.json()["candidate"]["id"])


def seed_candidate_evidence(candidate_id: int) -> list[str]:
    skills = flatten_skills("snowpro-core")[:5]
    question_ids: list[str] = []
    with connect() as conn:
        for index, skill in enumerate(skills, start=1):
            qid = f"learning-intelligence::{index}"
            question_ids.append(qid)
            conn.execute(
                """
                INSERT INTO questions(
                  id,track_id,question,options_json,correct_json,explanation,
                  source_kind,assessment_type,tags,difficulty,multiple
                ) VALUES (?,?,?,?,?,?,?,?,?,?,0)
                """,
                (
                    qid,
                    "snowpro-core",
                    f"Learning intelligence question {index}: choose the best Snowflake design.",
                    json.dumps(["A", "B", "C", "D"]),
                    json.dumps([1]),
                    f"Option B is correct for learning intelligence question {index}.",
                    "canonical",
                    "practice",
                    json.dumps(["learning-intelligence"]),
                    "medium",
                ),
            )
            conn.execute(
                """
                INSERT INTO question_skill_map(
                  question_id,track_id,domain_id,skill_id,confidence,evidence_json,reviewed
                ) VALUES (?,?,?,?,0.99,'{}',1)
                """,
                (qid, "snowpro-core", skill["domain_id"], skill["id"]),
            )

        evidence = [
            (question_ids[0], 0, 5),
            (question_ids[1], 0, 4),
            (question_ids[2], 1, 1),
            (question_ids[3], 1, 2),
            (question_ids[4], 1, 4),
        ]
        for qid, correct, confidence in evidence:
            selected = [1] if correct else [0]
            conn.execute(
                """
                INSERT INTO question_attempts(question_id,selected,correct,mode,candidate_id)
                VALUES (?,?,?,?,?)
                """,
                (qid, json.dumps(selected), correct, "drill", candidate_id),
            )
            conn.execute(
                """
                INSERT INTO candidate_question_history(
                  candidate_id,question_id,mode,pool,served_at,answered_at,
                  selected_json,correct,response_time_ms,confidence,question_version
                ) VALUES (?,?, 'drill','fallback',datetime('now'),datetime('now'),?,?,?,?, '1')
                """,
                (candidate_id, qid, json.dumps(selected), correct, 1200 + confidence * 100, confidence),
            )
    return question_ids


def seed_finished_mock(candidate_id: int, question_ids: list[str]) -> int:
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO exam_sessions(
              track_id,mode,started_at,finished_at,score,total_questions,status,
              duration_seconds,raw_correct,raw_accuracy,weighted_accuracy,scaled_score,
              elapsed_seconds,submitted_reason,configuration_json,candidate_id
            ) VALUES (
              'snowpro-core','exam_full_mock',datetime('now','-1 hour'),datetime('now'),
              1,2,'finished',7200,1,50,50,650,1800,'learner','{}',?
            )
            """,
            (candidate_id,),
        )
        session_id = int(cursor.lastrowid)
        for position, qid in enumerate(question_ids[:2], start=1):
            conn.execute(
                """
                INSERT INTO exam_session_questions(
                  session_id,question_id,position,options_json,correct_positions_json,flagged
                ) VALUES (?,?,?,?,?,0)
                """,
                (session_id, qid, position, json.dumps(["A", "B", "C", "D"]), json.dumps([1])),
            )
        conn.execute(
            """
            INSERT INTO exam_session_answers(session_id,question_id,selected_json,correct,answered_at)
            VALUES (?,?,?,0,datetime('now'))
            """,
            (session_id, question_ids[0], json.dumps([0])),
        )
        conn.execute(
            """
            INSERT INTO exam_session_answers(session_id,question_id,selected_json,correct,answered_at)
            VALUES (?,?,?,1,datetime('now'))
            """,
            (session_id, question_ids[1], json.dumps([1])),
        )
    return session_id


def main() -> None:
    with TestClient(app) as candidate_client:
        candidate_id = register(candidate_client, "learning-a@example.com")
        question_ids = seed_candidate_evidence(candidate_id)

        due = candidate_client.get("/api/intelligence/due-today?track_id=snowpro-core&limit=20")
        check(due.status_code == 200, due.text)
        due_body = due.json()
        due_ids = {item["question_id"] for item in due_body["questions"]}
        check(due_body["due_count"] == 2, f"two incorrect attempts should be due immediately: {due_body}")
        check(due_ids == set(question_ids[:2]), "Due Today contains the two missed questions")

        mistakes = candidate_client.get("/api/intelligence/mistake-notebook?track_id=snowpro-core")
        check(mistakes.status_code == 200, mistakes.text)
        mistake_body = mistakes.json()
        check(mistake_body["counts"]["open"] == 2, "two missed questions enter the notebook")
        check({item["question_id"] for item in mistake_body["items"]} == set(question_ids[:2]), "notebook is candidate-specific")

        calibration = candidate_client.get("/api/intelligence/confidence-calibration?track_id=snowpro-core")
        check(calibration.status_code == 200, calibration.text)
        calibration_body = calibration.json()
        check(calibration_body["sample_size"] == 5, "five confidence-rated answers form the first calibration sample")
        check(calibration_body["overconfident_misses"] == 2, "high-confidence misses are identified")
        check(calibration_body["underconfident_correct"] == 2, "low-confidence correct answers are identified")

        preferences = candidate_client.put(
            "/api/intelligence/study-plan/preferences",
            json={
                "track_id": "snowpro-core",
                "exam_date": "2026-09-15",
                "daily_minutes": 60,
                "days_per_week": 5,
            },
        )
        check(preferences.status_code == 200, preferences.text)
        plan = candidate_client.get("/api/intelligence/study-plan?track_id=snowpro-core")
        check(plan.status_code == 200, plan.text)
        plan_body = plan.json()
        check(plan_body["preferences"]["daily_minutes"] == 60, "study minutes persist")
        check(plan_body["preferences"]["days_per_week"] == 5, "study-day preference persists")
        check(len(plan_body["days"]) == 7, "study plan generates a seven-day horizon")
        check(plan_body["due_today"] == 2 and plan_body["open_mistakes"] == 2, "plan is driven by due and mistake state")
        check(plan_body["priority_skills"], "plan produces prioritized blueprint skills")

        note = candidate_client.patch(
            f"/api/intelligence/mistake-notebook/{question_ids[0]}",
            json={"root_cause": "confused architecture layers", "note": "Storage is independent from virtual warehouse compute."},
        )
        check(note.status_code == 200, note.text)
        check(note.json()["root_cause"] == "confused architecture layers", "mistake root cause is editable")

        session_id = seed_finished_mock(candidate_id, question_ids)
        remediation = candidate_client.get(f"/api/intelligence/mock-remediation/{session_id}")
        check(remediation.status_code == 200, remediation.text)
        remediation_body = remediation.json()
        check(remediation_body["mistake_count"] == 1, "mock remediation finds the failed mock question")
        check(remediation_body["priority_tasks"], "mock remediation prioritizes the affected task")
        check(any(action["type"] == "srs" for action in remediation_body["actions"]), "mock remediation links back to spaced review")

        with TestClient(app) as other_client:
            other_id = register(other_client, "learning-b@example.com")
            check(other_id != candidate_id, "second candidate is distinct")
            other_due = other_client.get("/api/intelligence/due-today?track_id=snowpro-core")
            check(other_due.status_code == 200 and other_due.json()["due_count"] == 0, "Due Today does not leak between candidates")
            other_mistakes = other_client.get("/api/intelligence/mistake-notebook?track_id=snowpro-core")
            check(other_mistakes.status_code == 200 and not other_mistakes.json()["items"], "mistake notebook does not leak between candidates")
            other_remediation = other_client.get(f"/api/intelligence/mock-remediation/{session_id}")
            check(other_remediation.status_code == 404, "mock remediation enforces candidate ownership")

    print("Candidate Study Plan, SRS Due Today, Mistake Notebook, Confidence Calibration, remediation, and ownership checks passed.")


if __name__ == "__main__":
    main()
