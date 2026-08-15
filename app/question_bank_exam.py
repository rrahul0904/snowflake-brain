from __future__ import annotations

import json
import random
from typing import Any

from fastapi import HTTPException

from .database import connect
from .entitlements import plan_details
from .mock_exam import _setting, certification, exam_config, session_payload
from .question_bank import (
    attach_recent_serves_to_session,
    exam_pack_set_question_ids,
    record_questions_served,
    store_exam_pack_set,
)
from .question_bank_selection import select_certification_questions
from .routers.certification_practice import CertificationQuizStart
from .serializers import json_list
from .tier_exam_policy import (
    FREE_FULL_CONTENT_MOCK_MINUTES,
    FREE_FULL_CONTENT_MOCK_QUESTIONS,
    mock_question_ids_to_avoid,
    mock_reset_context,
)


def _existing_ids(question_ids: list[str], track_id: str) -> list[str]:
    if not question_ids:
        return []
    placeholders = ",".join("?" for _ in question_ids)
    with connect() as conn:
        rows = {
            row["id"]
            for row in conn.execute(
                f"SELECT id FROM questions WHERE track_id=? AND id IN ({placeholders})",
                [track_id, *question_ids],
            )
        }
    return [qid for qid in question_ids if qid in rows]


def create_tier_mock_session(
    candidate: dict[str, Any],
    track_id: str,
    mode: str,
    *,
    practice_test_id: str | None = None,
    randomize_options: bool | None = None,
) -> dict[str, Any]:
    normalized, setting = _setting(mode)
    config = exam_config()
    certification(track_id)
    test = None
    if normalized == "source-exam":
        if not practice_test_id:
            raise HTTPException(status_code=400, detail="A source practice test is required")
        with connect() as conn:
            row = conn.execute(
                "SELECT * FROM practice_tests WHERE id=? AND track_id=?",
                (practice_test_id, track_id),
            ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Practice test not found")
        test = dict(row)
        if test.get("source_kind") not in {"source", "legacy"}:
            raise HTTPException(status_code=400, detail="Only imported source practice tests can create a source sitting")
        question_count = int(test.get("question_count") or 0)
        duration_minutes = max(1, question_count * 2)
    else:
        if practice_test_id:
            raise HTTPException(status_code=400, detail="Generated mocks cannot pin a source practice test")
        if normalized == "weekly-mock":
            question_count = FREE_FULL_CONTENT_MOCK_QUESTIONS
            duration_minutes = FREE_FULL_CONTENT_MOCK_MINUTES
        else:
            question_count = int(setting["question_count"])
            duration_minutes = int(setting["time_limit_minutes"])

    plan = plan_details(candidate["membership"].get("plan_code"), candidate["membership"].get("tier") or "free")
    reset = mock_reset_context(candidate, normalized)
    fixed_ids: list[str] = []
    set_kind: str | None = None
    if plan["code"] == "exam_pack_35" and normalized == "lifetime-practice":
        set_kind = "lifetime_practice"
        fixed_ids = _existing_ids(
            exam_pack_set_question_ids(candidate["id"], track_id, set_kind),
            track_id,
        )
    elif plan["code"] == "exam_pack_35" and normalized == "full-mock":
        set_kind = "full_exam"
        fixed_ids = _existing_ids(
            exam_pack_set_question_ids(candidate["id"], track_id, set_kind),
            track_id,
        )

    avoid_ids: set[str] = set()
    if not set_kind:
        avoid_ids = mock_question_ids_to_avoid(candidate["id"], track_id, normalized, reset)

    reset_exclusion_applied = False
    if fixed_ids:
        if len(fixed_ids) != question_count:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "exam_pack_set_incomplete",
                    "message": "The stored Exam Pack question set is incomplete and requires administrative repair.",
                },
            )
        questions = [{"id": qid} for qid in fixed_ids]
        selection_strategy = "candidate_exam_pack_fixed_set"
        record_questions_served(candidate["id"], questions, mode=normalized)
    else:
        selected = select_certification_questions(
            CertificationQuizStart(
                track_id=track_id,
                count=max(1, min(question_count, 500)),
                mode=normalized,
                test_id=practice_test_id,
            ),
            candidate,
            trusted_exam_session=True,
            exclude_question_ids=avoid_ids,
        )
        questions = list(selected.get("questions") or [])
        selection_strategy = str(selected.get("selection_strategy") or "blueprint_weighted_private_bank")
        reset_exclusion_applied = bool(selected.get("reset_exclusion_applied"))
        if len(questions) != question_count:
            raise HTTPException(
                status_code=409,
                detail=f"This sitting needs {question_count} eligible questions; {len(questions)} are available",
            )
        if set_kind:
            store_exam_pack_set(candidate["id"], track_id, set_kind, [row["id"] for row in questions])

    if normalized != "source-exam" and config.get("randomize_questions", True):
        random.shuffle(questions)
    should_shuffle_options = config.get("randomize_options", True) if randomize_options is None else randomize_options

    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO exam_sessions(
              track_id, practice_test_id, mode, started_at, score, total_questions,
              status, duration_seconds, configuration_json, candidate_id
            ) VALUES (?, ?, ?, datetime('now'), 0, ?, 'in_progress', ?, ?, ?)
            """,
            (
                track_id,
                practice_test_id,
                "exam_source" if normalized == "source-exam" else f"exam_{normalized.replace('-', '_')}",
                question_count,
                duration_minutes * 60,
                json.dumps(
                    {
                        "selection_strategy": selection_strategy,
                        "randomize_options": bool(should_shuffle_options),
                        "source_kind": test.get("source_kind") if test else "private_bank_or_fallback",
                        "exam_code": test.get("exam_code") if test else config.get("exam_code"),
                        "candidate_specific_set": bool(set_kind),
                        "set_kind": set_kind,
                        "reset_cadence": reset.get("cadence"),
                        "reset_window_key": reset.get("window_key"),
                        "resets_at": reset.get("resets_at"),
                        "rotates_questions": bool(reset.get("rotates_questions")),
                        "prior_questions_avoided": len(avoid_ids),
                        "reset_exclusion_applied": reset_exclusion_applied,
                    }
                ),
                candidate["id"],
            ),
        )
        session_id = int(cursor.lastrowid)
        for position, public in enumerate(questions, start=1):
            stored = conn.execute(
                "SELECT options_json, correct_json FROM questions WHERE id=? AND track_id=?",
                (public["id"], track_id),
            ).fetchone()
            if not stored:
                raise HTTPException(status_code=409, detail="A selected question disappeared before the sitting was saved")
            options = json_list(stored["options_json"])
            correct_original = {int(item) for item in json_list(stored["correct_json"])}
            order = list(range(len(options)))
            if should_shuffle_options:
                random.shuffle(order)
            displayed_options = [options[index] for index in order]
            displayed_correct = sorted(index for index, original in enumerate(order) if original in correct_original)
            conn.execute(
                """
                INSERT INTO exam_session_questions(
                  session_id, question_id, position, options_json, correct_positions_json, flagged
                ) VALUES (?, ?, ?, ?, ?, 0)
                """,
                (session_id, public["id"], position, json.dumps(displayed_options), json.dumps(displayed_correct)),
            )
        conn.execute(
            """
            INSERT INTO learning_events(event_type, track_id, practice_test_id, metadata_json, candidate_id)
            VALUES ('mock_session_started', ?, ?, ?, ?)
            """,
            (
                track_id,
                practice_test_id,
                json.dumps(
                    {
                        "session_id": session_id,
                        "mode": normalized,
                        "question_count": question_count,
                        "selection_strategy": selection_strategy,
                        "candidate_specific_set": bool(set_kind),
                        "reset_cadence": reset.get("cadence"),
                        "reset_window_key": reset.get("window_key"),
                        "resets_at": reset.get("resets_at"),
                        "reset_exclusion_applied": reset_exclusion_applied,
                    }
                ),
                candidate["id"],
            ),
        )
    attach_recent_serves_to_session(
        candidate["id"],
        [row["id"] for row in questions],
        normalized,
        session_id,
    )
    return session_payload(session_id)
