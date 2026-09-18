#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory(prefix="snowflake-question-feedback-")
os.environ["BRAIN_DB"] = str(Path(TEMP.name) / "question-feedback.sqlite")
os.environ["SECURITY_RATE_LIMIT_ENABLED"] = "false"
os.environ["ACCOUNT_EMAIL_DELIVERY_MODE"] = "outbox"
os.environ["BILLING_ENABLED"] = "false"
os.environ["GOOGLE_AUTH_ENABLED"] = "false"

from fastapi.testclient import TestClient  # noqa: E402
from app.database import run_migrations  # noqa: E402
from app.main import app  # noqa: E402
from app.question_feedback import editorial_question_feedback, update_question_feedback  # noqa: E402


def check(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    run_migrations()
    client = TestClient(app)

    signup = client.post(
        "/api/auth/register",
        json={
            "display_name": "Question Feedback Candidate",
            "email": "question-feedback@example.com",
            "password": "QuestionFeedbackPassword!123",
        },
    )
    check(signup.status_code == 201, signup.text)

    unserved = client.post(
        "/api/questions/not-a-served-question/feedback",
        json={"category": "ambiguous", "description": "This should never be accepted."},
    )
    check(unserved.status_code == 404, f"unserved question report leaked authorization: {unserved.status_code}")

    quiz = client.post(
        "/api/certification-quiz/start",
        json={"track_id": "snowpro-core", "count": 1, "mode": "drill"},
    )
    check(quiz.status_code == 200, quiz.text)
    questions = quiz.json().get("questions") or []
    check(len(questions) == 1, f"expected one securely allocated question: {quiz.json()}")
    question_id = str(questions[0]["id"])

    report = client.post(
        f"/api/questions/{question_id}/feedback",
        json={
            "category": "ambiguous",
            "description": "Two choices appear close enough that the distinction should be reviewed.",
        },
    )
    check(report.status_code == 200, report.text)
    payload = report.json()
    feedback = payload.get("feedback") or {}
    check(feedback.get("question_id") == question_id, "feedback was not tied to the served question")
    check(feedback.get("status") == "open", "new question feedback must enter the open editorial queue")

    serialized = str(payload).lower()
    for forbidden in ("correct_json", "correct answer", "answer_key", "source_refs_json"):
        check(forbidden not in serialized, f"question report leaked protected answer/bank metadata: {forbidden}")

    duplicate = client.post(
        f"/api/questions/{question_id}/feedback",
        json={
            "category": "ambiguous",
            "description": "A duplicate open report should remain idempotent for this category.",
        },
    )
    check(duplicate.status_code == 200, duplicate.text)
    check(
        int((duplicate.json().get("feedback") or {}).get("id") or 0) == int(feedback.get("id") or -1),
        "duplicate open category report should reuse the active editorial item",
    )

    mine = client.get("/api/question-feedback")
    check(mine.status_code == 200, mine.text)
    rows = mine.json().get("feedback") or []
    check(len(rows) == 1 and rows[0].get("question_id") == question_id, "candidate report history is incorrect")
    for row in rows:
        for forbidden_key in ("correct_json", "options_json", "explanation", "bank_pool"):
            check(forbidden_key not in row, f"candidate report history leaked bank data: {forbidden_key}")

    unauthorized_admin = client.get("/api/admin/question-feedback")
    check(unauthorized_admin.status_code == 403, "ordinary candidate reached founder correction queue")

    queue = editorial_question_feedback(status="open")
    check(len(queue) == 1 and queue[0]["question_id"] == question_id, "editorial queue did not receive report")
    resolved = update_question_feedback(
        int(feedback["id"]),
        status="resolved",
        actor="editorial-reviewer@example.com",
        resolution_notes="Reviewed against current Snowflake documentation.",
    )
    check(resolved["status"] == "resolved", "editorial resolution did not persist")

    mine_after = client.get("/api/question-feedback").json().get("feedback") or []
    check(mine_after[0]["status"] == "resolved", "candidate cannot see editorial resolution state")
    check(
        mine_after[0]["resolution_notes"] == "Reviewed against current Snowflake documentation.",
        "candidate resolution note did not persist",
    )

    print("Question feedback authorization and editorial workflow: PASS")


if __name__ == "__main__":
    try:
        main()
    finally:
        TEMP.cleanup()
