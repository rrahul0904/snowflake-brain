#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Configure an isolated SQLite database before importing application modules.
_tmp = tempfile.TemporaryDirectory(prefix="snowflake-final-convergence-")
os.environ["BRAIN_DB"] = str(Path(_tmp.name) / "convergence.sqlite")
os.environ.pop("DATABASE_URL", None)
os.environ.pop("DATABASE_MIGRATION_URL", None)
os.environ.pop("VERCEL", None)
os.environ.pop("VERCEL_ENV", None)

from app.database import connect, run_migrations  # noqa: E402
from app.mock_replay import append_event, record_answer_event, replay_payload  # noqa: E402
from app.task_review import due_task_reviews, get_task_review, mark_task_reviewed, reset_task_review, schedule_task_review  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def must(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def seed() -> tuple[int, int, int]:
    run_migrations()
    with connect() as conn:
        def candidate(email: str) -> int:
            cursor = conn.execute(
                """
                INSERT INTO candidate_accounts(email,display_name,password_hash,password_salt,password_algorithm)
                VALUES (?,?,?,?,'scrypt')
                """,
                (email, email.split("@")[0], "test-hash", "test-salt"),
            )
            return int(cursor.lastrowid)

        c1 = candidate("convergence-1@example.com")
        c2 = candidate("convergence-2@example.com")
        conn.execute(
            "INSERT INTO certification_tracks(id,title,exam_code,description,position) VALUES ('snowpro-core','SnowPro Core','COF-C03','test',1)"
        )
        conn.execute(
            "INSERT INTO practice_tests(id,track_id,title,exam_code,source_kind,question_count,is_legacy) VALUES ('conv-test','snowpro-core','Convergence Test','COF-C03','canonical',1,0)"
        )
        conn.execute(
            """
            INSERT INTO questions(id,track_id,test_id,test_title,question,options_json,correct_json,explanation,source_kind,difficulty,multiple)
            VALUES ('conv-q1','snowpro-core','conv-test','Convergence Test','Synthetic CI question', '[\"A\",\"B\"]','[0]','Synthetic explanation','canonical','medium',0)
            """
        )
        conn.execute(
            "INSERT INTO question_skill_map(question_id,track_id,domain_id,skill_id,confidence,reviewed) VALUES ('conv-q1','snowpro-core','domain-1','skill-1',1.0,1)"
        )
        cursor = conn.execute(
            """
            INSERT INTO exam_sessions(track_id,practice_test_id,mode,started_at,score,total_questions,status,duration_seconds,configuration_json,candidate_id)
            VALUES ('snowpro-core','conv-test','exam_quick_mock',datetime('now'),0,1,'in_progress',2700,'{}',?)
            """,
            (c1,),
        )
        session_id = int(cursor.lastrowid)
        conn.execute(
            """
            INSERT INTO exam_session_questions(session_id,question_id,position,options_json,correct_positions_json,flagged)
            VALUES (?, 'conv-q1',1,'[\"A\",\"B\"]','[0]',0)
            """,
            (session_id,),
        )
        return c1, c2, session_id


def test_task_review(c1: int, c2: int) -> None:
    with connect() as conn:
        first = schedule_task_review(conn, c1, "snowpro-core", "skill-1")
        duplicate = schedule_task_review(conn, c1, "snowpro-core", "skill-1")
        must(first["skill_id"] == "skill-1", "task review was not scheduled")
        must(duplicate["created_at"] == first["created_at"], "duplicate task scheduling should be idempotent")
        must(get_task_review(conn, c2, "snowpro-core", "skill-1") is None, "task review leaked across candidates")
        must(get_task_review(conn, c1, "another-track", "skill-1") is None, "task review leaked across tracks")

        immediate = reset_task_review(conn, c1, "snowpro-core", "skill-1")
        must(int(immediate["interval_days"]) == 0, "manual reset should make a task due immediately")
        due = due_task_reviews(conn, c1, "snowpro-core", limit=10)
        must(int(due["task_due_count"]) == 1, "due task review was not returned")
        must(due["task_reviews"][0]["skill_id"] == "skill-1", "wrong task review returned")

        reviewed = mark_task_reviewed(conn, c1, "snowpro-core", "skill-1")
        must(int(reviewed["review_count"]) == 1, "task review count did not advance")
        must(int(reviewed["interval_days"]) == 3, "first completed manual review should schedule the next review in three days")
        reviewed_again = mark_task_reviewed(conn, c1, "snowpro-core", "skill-1")
        must(int(reviewed_again["interval_days"]) == 7, "task review interval progression is not deterministic")


def test_mock_replay(c1: int, c2: int, session_id: int) -> None:
    with connect() as conn:
        try:
            replay_payload(conn, session_id, c1)
        except RuntimeError:
            pass
        else:
            raise AssertionError("mock replay must be blocked before submission")

        append_event(conn, session_id=session_id, candidate_id=c1, question_id="conv-q1", event_type="question_viewed", metadata={"position": 1}, client_event=True)
        record_answer_event(conn, session_id=session_id, candidate_id=c1, question_id="conv-q1", previous=[], selected=[0])
        record_answer_event(conn, session_id=session_id, candidate_id=c1, question_id="conv-q1", previous=[0], selected=[1])

        # Deterministic elapsed-time fixture without weakening the production event API.
        base = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)
        conn.execute("DELETE FROM exam_session_events WHERE session_id=? AND event_type IN ('question_viewed','question_navigated_from')", (session_id,))
        conn.execute(
            "INSERT INTO exam_session_events(session_id,candidate_id,question_id,event_type,occurred_at,metadata_json) VALUES (?,?,?,?,?,?)",
            (session_id, c1, "conv-q1", "question_viewed", base.strftime("%Y-%m-%d %H:%M:%S"), "{\"position\":1}"),
        )
        conn.execute(
            "INSERT INTO exam_session_events(session_id,candidate_id,question_id,event_type,occurred_at,metadata_json) VALUES (?,?,?,?,?,?)",
            (session_id, c1, "conv-q1", "question_navigated_from", (base + timedelta(seconds=42)).strftime("%Y-%m-%d %H:%M:%S"), "{\"from_position\":1}"),
        )
        conn.execute(
            "INSERT INTO exam_session_answers(session_id,question_id,selected_json,correct,answered_at,confidence) VALUES (?,?,'[1]',0,datetime('now'),5)",
            (session_id, "conv-q1"),
        )
        conn.execute("UPDATE exam_sessions SET status='finished',finished_at=datetime('now') WHERE id=?", (session_id,))

        replay = replay_payload(conn, session_id, c1)
        must(replay["event_count"] >= 3, "mock replay event stream is empty")
        row = replay["questions"][0]
        must(int(row["answer_change_count"]) == 1, "answer-change count is incorrect")
        must(int(row["time_spent_seconds"]) == 42, "time-spent computation is incorrect")
        must(row["status"] == "incorrect", "post-submit replay result state is incorrect")
        serialized = json.dumps(replay).lower()
        must("synthetic ci question" not in serialized, "mock replay leaked question text")
        must("synthetic explanation" not in serialized, "mock replay leaked explanation text")
        must("correct_positions" not in serialized and "correct answer" not in serialized, "mock replay leaked an answer oracle")

        try:
            replay_payload(conn, session_id, c2)
        except ValueError:
            pass
        else:
            raise AssertionError("mock replay leaked across candidates")


def test_ui_contract() -> None:
    practice = (ROOT / "frontend/views/practice-v26.js").read_text(encoding="utf-8")
    lesson = (ROOT / "frontend/views/lesson-v26.js").read_text(encoding="utf-8")
    result = (ROOT / "frontend/views/exam-result-v26.js").read_text(encoding="utf-8")
    migration = (ROOT / "migrations/postgres/022_study_review_mock_replay.sql").read_text(encoding="utf-8").lower()

    for token in ("data-difficulty", "data-unanswered-only", "data-session-count", "difficulty: state.difficulty", "unanswered_only: state.unansweredOnly"):
        must(token in practice, f"real targeted-drill UI contract missing: {token}")
    must("Add to Review" in lesson and "scheduleTaskReview" in lesson, "lesson task review action is not persisted")
    for label in ("Mock Replay", "Changed Answer", "Slowest", "getMockReplay"):
        must(label in result, f"mock replay UI contract missing: {label}")
    for forbidden in ("correct_json", "correct_positions_json", "explanation", "question text"):
        must(forbidden not in migration, f"mock replay migration contains forbidden private payload field: {forbidden}")


def main() -> None:
    c1, c2, session_id = seed()
    test_task_review(c1, c2)
    test_mock_replay(c1, c2, session_id)
    test_ui_contract()
    print("Final UI convergence regression suite: PASS")


if __name__ == "__main__":
    main()
