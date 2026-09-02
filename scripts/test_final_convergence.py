#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Configure an isolated SQLite database before importing application modules.
_tmp = tempfile.TemporaryDirectory(prefix="snowflake-final-convergence-")
os.environ["BRAIN_DB"] = str(Path(_tmp.name) / "convergence.sqlite")
os.environ.pop("DATABASE_URL", None)
os.environ.pop("DATABASE_MIGRATION_URL", None)
os.environ.pop("VERCEL", None)
os.environ.pop("VERCEL_ENV", None)

from fastapi import HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from app.database import connect, run_migrations  # noqa: E402
from app.main import app  # noqa: E402
from app.mock_replay import append_event, record_answer_event, replay_payload  # noqa: E402
from app.routers.question_bank_runtime import (  # noqa: E402
    SessionReplayEvent,
    get_candidate_mock_replay,
    post_candidate_mock_replay_event,
)
from app.skill_brain import flatten_skills  # noqa: E402
from app.task_review import due_task_reviews, get_task_review, mark_task_reviewed, reset_task_review, schedule_task_review  # noqa: E402


def must(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def seed() -> tuple[int, int, int, dict[str, str]]:
    run_migrations()
    skill = flatten_skills("snowpro-core")[0]
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
            "INSERT OR IGNORE INTO certification_tracks(id,title,exam_code,description,position) VALUES ('snowpro-core','SnowPro Core','COF-C03','test',1)"
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
            "INSERT INTO question_skill_map(question_id,track_id,domain_id,skill_id,confidence,reviewed) VALUES (?,?,?,?,1.0,1)",
            ("conv-q1", "snowpro-core", skill["domain_id"], skill["id"]),
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
        return c1, c2, session_id, skill


def test_task_review(c1: int, c2: int, skill: dict[str, str]) -> None:
    skill_id = skill["id"]
    with connect() as conn:
        first = schedule_task_review(conn, c1, "snowpro-core", skill_id)
        duplicate = schedule_task_review(conn, c1, "snowpro-core", skill_id)
        must(first["skill_id"] == skill_id, "task review was not scheduled")
        must(duplicate["created_at"] == first["created_at"], "duplicate task scheduling should be idempotent")
        must(duplicate["next_review_at"] == first["next_review_at"], "duplicate task scheduling must not push the review date")
        must(get_task_review(conn, c2, "snowpro-core", skill_id) is None, "task review leaked across candidates")

        try:
            get_task_review(conn, c1, "advanced-data-engineer", skill_id)
        except ValueError:
            pass
        else:
            raise AssertionError("task review accepted a task under the wrong certification track")

        immediate = reset_task_review(conn, c1, "snowpro-core", skill_id)
        must(int(immediate["interval_days"]) == 0, "manual reset should make a task due immediately")
        due = due_task_reviews(conn, c1, "snowpro-core", limit=10)
        must(int(due["task_due_count"]) == 1, "due task review was not returned")
        must(due["task_reviews"][0]["skill_id"] == skill_id, "wrong task review returned")

        reviewed = mark_task_reviewed(conn, c1, "snowpro-core", skill_id)
        must(int(reviewed["review_count"]) == 1, "task review count did not advance")
        must(int(reviewed["interval_days"]) == 3, "first completed manual review should schedule the next review in three days")
        reviewed_again = mark_task_reviewed(conn, c1, "snowpro-core", skill_id)
        must(int(reviewed_again["interval_days"]) == 7, "task review interval progression is not deterministic")

        try:
            schedule_task_review(conn, c1, "snowpro-core", "not-a-real-task")
        except ValueError:
            pass
        else:
            raise AssertionError("task review accepted an unknown task")


def test_mounted_mock_replay_api_active(c1: int, c2: int, session_id: int) -> None:
    post_route = next(
        (
            route
            for route in app.routes
            if getattr(route, "path", None) == "/api/mock/sessions/{session_id}/events"
            and "POST" in (getattr(route, "methods", set()) or set())
        ),
        None,
    )
    replay_route = next(
        (
            route
            for route in app.routes
            if getattr(route, "path", None) == "/api/mock/sessions/{session_id}/replay"
            and "GET" in (getattr(route, "methods", set()) or set())
        ),
        None,
    )
    must(post_route is not None, "candidate Mock Replay event endpoint is not mounted under /api")
    must(replay_route is not None, "candidate Mock Replay read endpoint is not mounted under /api")

    # The application security middleware must reject anonymous access before the
    # route handler is allowed to mutate replay state.
    with TestClient(app) as client:
        anonymous = client.post(
            f"/api/mock/sessions/{session_id}/events",
            json={"event_type": "question_viewed", "question_id": "conv-q1", "metadata": {"position": 1}},
        )
    must(anonymous.status_code == 401, f"anonymous replay event write was not authentication-gated: {anonymous.status_code}")

    payload = SessionReplayEvent(
        event_type="question_viewed",
        question_id="conv-q1",
        metadata={
            "position": 1,
            "question": "must never persist",
            "correct_answer": [0],
            "explanation": "must never persist",
        },
    )
    result = post_candidate_mock_replay_event(session_id, payload, {"id": c1})
    must(result.get("ok") is True, "owned active-session replay event write failed")

    try:
        SessionReplayEvent(event_type="answer_changed", question_id="conv-q1", metadata={})
    except ValidationError:
        pass
    else:
        raise AssertionError("candidate replay event model accepted a server-managed answer event")

    try:
        post_candidate_mock_replay_event(session_id, payload, {"id": c2})
    except HTTPException as exc:
        must(exc.status_code in {403, 404}, f"cross-candidate replay event write returned unexpected status: {exc.status_code}")
    else:
        raise AssertionError("cross-candidate replay event write was not denied")

    with connect() as conn:
        persisted = [
            json.loads(row["metadata_json"] or "{}")
            for row in conn.execute(
                "SELECT metadata_json FROM exam_session_events WHERE session_id=? ORDER BY id",
                (session_id,),
            )
        ]
    forbidden = {"question", "correct_answer", "correct", "explanation", "answer_key"}
    must(all(not (forbidden & set(item)) for item in persisted), f"mounted replay API leaked private/oracle metadata: {persisted}")


def test_mock_replay(c1: int, c2: int, session_id: int) -> None:
    with connect() as conn:
        try:
            replay_payload(conn, session_id, c1)
        except RuntimeError:
            pass
        else:
            raise AssertionError("mock replay must be blocked before submission")

        append_event(
            conn,
            session_id=session_id,
            candidate_id=c1,
            question_id="conv-q1",
            event_type="question_viewed",
            metadata={
                "position": 1,
                "question": "must never persist",
                "correct_answer": [0],
                "explanation": "must never persist",
            },
            client_event=True,
        )
        record_answer_event(conn, session_id=session_id, candidate_id=c1, question_id="conv-q1", previous=[], selected=[0])
        record_answer_event(conn, session_id=session_id, candidate_id=c1, question_id="conv-q1", previous=[0], selected=[1])

        try:
            append_event(
                conn,
                session_id=session_id,
                candidate_id=c1,
                question_id="conv-q1",
                event_type="answer_changed",
                client_event=True,
            )
        except ValueError:
            pass
        else:
            raise AssertionError("client was allowed to forge a server-managed answer-change event")

        persisted = [
            json.loads(row["metadata_json"] or "{}")
            for row in conn.execute(
                "SELECT metadata_json FROM exam_session_events WHERE session_id=? ORDER BY id",
                (session_id,),
            )
        ]
        forbidden = {"question", "correct_answer", "correct", "explanation", "answer_key"}
        must(all(not (forbidden & set(item)) for item in persisted), f"replay metadata leaked private/oracle fields: {persisted}")

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
        must("interaction metadata only" in replay["integrity_note"].lower(), "mock replay integrity note is missing")

        try:
            replay_payload(conn, session_id, c2)
        except ValueError:
            pass
        else:
            raise AssertionError("mock replay leaked across candidates")


def test_mounted_mock_replay_api_submitted(c1: int, session_id: int) -> None:
    payload = SessionReplayEvent(event_type="session_resumed", metadata={})
    try:
        post_candidate_mock_replay_event(session_id, payload, {"id": c1})
    except HTTPException as exc:
        must(exc.status_code == 409, f"submitted mock replay event returned unexpected status: {exc.status_code}")
    else:
        raise AssertionError("submitted mock accepted a new replay event")

    replay = get_candidate_mock_replay(session_id, {"id": c1})
    serialized = json.dumps(replay).lower()
    must("synthetic ci question" not in serialized, "mounted replay endpoint leaked question text")
    must("synthetic explanation" not in serialized, "mounted replay endpoint leaked explanation text")
    must("correct_positions" not in serialized and "correct answer" not in serialized, "mounted replay endpoint leaked an answer oracle")


def test_ui_contract() -> None:
    practice = (ROOT / "frontend/views/practice-v26.js").read_text(encoding="utf-8")
    lesson = (ROOT / "frontend/views/lesson-v26.js").read_text(encoding="utf-8")
    due = (ROOT / "frontend/views/due-v26.js").read_text(encoding="utf-8")
    result = (ROOT / "frontend/views/exam-result-v26.js").read_text(encoding="utf-8")
    session = (ROOT / "frontend/views/exam-session-v26.js").read_text(encoding="utf-8")
    globe = (ROOT / "frontend/components/globe.js").read_text(encoding="utf-8")
    migration = (ROOT / "migrations/postgres/022_study_review_mock_replay.sql").read_text(encoding="utf-8").lower()

    for token in ("data-difficulty", "data-unanswered-only", "data-session-count", "difficulty: state.difficulty", "unanswered_only: state.unansweredOnly"):
        must(token in practice, f"real targeted-drill UI contract missing: {token}")
    for forbidden in ("confidence gap", "ai-selected difficulty"):
        must(forbidden not in practice.lower(), f"unsupported drill control leaked into UI: {forbidden}")
    must("Add to Review" in lesson and "scheduleTaskReview" in lesson, "lesson task review action is not persisted")
    must("Concept review" in due and "Question review" in due, "Due Today does not distinguish task and question reviews")
    for label in ("Mock Replay", "Changed Answer", "Slowest", "getMockReplay"):
        must(label in result, f"mock replay UI contract missing: {label}")
    must("recordMockReplayEvent" in session and "question_navigated_to" in session, "exam player does not capture replay navigation events")
    must("renderActivityGlobe" in globe and "WORLD_GEOMETRY_URL" in globe, "canonical interactive globe was removed")
    for forbidden in ("correct_json", "correct_positions_json", "explanation", "question text"):
        must(forbidden not in migration, f"mock replay migration contains forbidden private payload field: {forbidden}")


def main() -> None:
    c1, c2, session_id, skill = seed()
    test_task_review(c1, c2, skill)
    test_mounted_mock_replay_api_active(c1, c2, session_id)
    test_mock_replay(c1, c2, session_id)
    test_mounted_mock_replay_api_submitted(c1, session_id)
    test_ui_contract()
    print("Final UI convergence regression suite: PASS")


if __name__ == "__main__":
    main()
