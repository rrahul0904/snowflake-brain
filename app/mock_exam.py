from __future__ import annotations

import json
import random
from collections import defaultdict
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

from fastapi import HTTPException

from .certification_content import configured_skill_map
from .config import EXAM_SIMULATION_CONFIG
from .database import connect
from .routers.certification_practice import CertificationQuizStart, certification_quiz_start
from .serializers import json_list
from .skill_brain import flatten_skills


@lru_cache(maxsize=1)
def exam_config() -> dict[str, Any]:
    return json.loads(EXAM_SIMULATION_CONFIG.read_text(encoding="utf-8"))


def certification(track_id: str) -> dict[str, Any]:
    for item in configured_skill_map().get("certifications") or []:
        if item.get("id") == track_id:
            return item
    raise HTTPException(status_code=404, detail="Certification track is not configured")


def public_config(track_id: str = "snowpro-core") -> dict[str, Any]:
    config = exam_config()
    cert = certification(track_id)
    if config.get("track_id") != track_id:
        raise HTTPException(status_code=404, detail="Mock configuration is not available for this track")
    with connect() as conn:
        counts = {
            row["source_kind"]: int(row["count"] or 0)
            for row in conn.execute(
                "SELECT source_kind, COUNT(*) AS count FROM questions WHERE track_id = ? GROUP BY source_kind",
                (track_id,),
            )
        }
        current_tests = int(
            conn.execute(
                "SELECT COUNT(*) AS count FROM practice_tests WHERE track_id = ? AND source_kind = 'source' AND is_legacy = 0",
                (track_id,),
            ).fetchone()["count"]
            or 0
        )
        legacy_tests = int(
            conn.execute(
                "SELECT COUNT(*) AS count FROM practice_tests WHERE track_id = ? AND is_legacy = 1",
                (track_id,),
            ).fetchone()["count"]
            or 0
        )
    return {
        **config,
        "certification_title": cert.get("title"),
        "domains": [
            {
                "id": domain.get("id"),
                "title": domain.get("title"),
                "weight": int(domain.get("weight") or 0),
                "task_count": len(domain.get("skills") or []),
            }
            for domain in cert.get("domains") or []
        ],
        "task_count": len(flatten_skills(track_id)),
        "question_bank": {
            "source_questions": counts.get("source", 0),
            "curated_questions": counts.get("curated", 0),
            "canonical_questions": counts.get("canonical", 0),
            "legacy_questions": counts.get("legacy", 0),
            "current_source_tests": current_tests,
            "legacy_tests": legacy_tests,
        },
    }


def _setting(mode: str) -> tuple[str, dict[str, Any]]:
    normalized = mode.strip().lower().replace("_", "-")
    if normalized in {"quick", "quick-mock"}:
        return "quick-mock", exam_config()["quick_mock"]
    if normalized in {"full", "full-mock", "exam"}:
        return "full-mock", exam_config()["full_mock"]
    if normalized == "source-exam":
        return normalized, {}
    raise HTTPException(status_code=400, detail="Mode must be quick-mock, full-mock, or source-exam")


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def _remaining_seconds(session: dict[str, Any]) -> int:
    deadline = _parse_utc(session["started_at"]).timestamp() + int(session.get("duration_seconds") or 0)
    return max(0, int(deadline - datetime.now(timezone.utc).timestamp()))


def _question_edge(conn: Any, question_id: str, track_id: str) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT domain_id, skill_id, confidence, reviewed
        FROM question_skill_map
        WHERE question_id = ? AND track_id = ?
        ORDER BY reviewed DESC, confidence DESC, updated_at DESC
        LIMIT 1
        """,
        (question_id, track_id),
    ).fetchone()
    return dict(row) if row else {"domain_id": "", "skill_id": "", "confidence": 0, "reviewed": 0}


def create_session(
    track_id: str,
    mode: str,
    practice_test_id: str | None = None,
    randomize_options: bool | None = None,
) -> dict[str, Any]:
    normalized, setting = _setting(mode)
    config = exam_config()
    test = None
    if normalized == "source-exam":
        if not practice_test_id:
            raise HTTPException(status_code=400, detail="A source practice test is required")
        with connect() as conn:
            row = conn.execute("SELECT * FROM practice_tests WHERE id = ? AND track_id = ?", (practice_test_id, track_id)).fetchone()
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
        question_count = int(setting["question_count"])
        duration_minutes = int(setting["time_limit_minutes"])

    selected = certification_quiz_start(
        CertificationQuizStart(
            track_id=track_id,
            count=max(1, min(question_count, 500)),
            mode=normalized,
            test_id=practice_test_id,
        )
    )
    questions = list(selected.get("questions") or [])
    if len(questions) != question_count:
        raise HTTPException(
            status_code=409,
            detail=f"This sitting needs {question_count} eligible questions; {len(questions)} are available",
        )
    if normalized != "source-exam" and config.get("randomize_questions", True):
        random.shuffle(questions)

    should_shuffle_options = config.get("randomize_options", True) if randomize_options is None else randomize_options
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO exam_sessions(
              track_id, practice_test_id, mode, started_at, score, total_questions,
              status, duration_seconds, configuration_json
            ) VALUES (?, ?, ?, datetime('now'), 0, ?, 'in_progress', ?, ?)
            """,
            (
                track_id,
                practice_test_id,
                "exam_source" if normalized == "source-exam" else f"exam_{normalized.replace('-', '_')}",
                question_count,
                duration_minutes * 60,
                json.dumps(
                    {
                        "selection_strategy": selected.get("selection_strategy"),
                        "randomize_options": bool(should_shuffle_options),
                        "source_kind": test.get("source_kind") if test else None,
                        "exam_code": test.get("exam_code") if test else config.get("exam_code"),
                    }
                ),
            ),
        )
        session_id = int(cursor.lastrowid)
        for position, public in enumerate(questions, start=1):
            stored = conn.execute("SELECT options_json, correct_json FROM questions WHERE id = ?", (public["id"],)).fetchone()
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
            INSERT INTO learning_events(event_type, track_id, practice_test_id, metadata_json)
            VALUES ('mock_session_started', ?, ?, ?)
            """,
            (track_id, practice_test_id, json.dumps({"session_id": session_id, "mode": normalized, "question_count": question_count})),
        )
    return session_payload(session_id)


def _session_row(conn: Any, session_id: int) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM exam_sessions WHERE id = ?", (session_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Exam session not found")
    return dict(row)


def session_payload(session_id: int) -> dict[str, Any]:
    with connect() as conn:
        session = _session_row(conn, session_id)
    if session["status"] == "in_progress" and _remaining_seconds(session) <= 0:
        submit_session(session_id, "timer")
        with connect() as conn:
            session = _session_row(conn, session_id)
    if session["status"] != "in_progress":
        return {
            "session_id": session_id,
            "track_id": session["track_id"],
            "mode": session["mode"],
            "status": session["status"],
            "remaining_seconds": 0,
            "result_available": True,
        }

    with connect() as conn:
        rows = [
            dict(row)
            for row in conn.execute(
                """
                SELECT sq.position, sq.question_id, sq.options_json, sq.flagged,
                       q.question, q.multiple, q.assessment_type, q.difficulty,
                       q.test_title, q.source_kind,
                       a.selected_json, a.answered_at
                FROM exam_session_questions sq
                JOIN questions q ON q.id = sq.question_id
                LEFT JOIN exam_session_answers a
                  ON a.session_id = sq.session_id AND a.question_id = sq.question_id
                WHERE sq.session_id = ?
                ORDER BY sq.position
                """,
                (session_id,),
            )
        ]
        questions = []
        for row in rows:
            edge = _question_edge(conn, row["question_id"], session["track_id"])
            questions.append(
                {
                    "id": row["question_id"],
                    "position": int(row["position"]),
                    "question": row["question"],
                    "options": json_list(row["options_json"]),
                    "multiple": bool(row["multiple"] or len(json_list(row["selected_json"])) > 1 or "multi" in (row["assessment_type"] or "")),
                    "difficulty": row["difficulty"],
                    "test_title": row["test_title"],
                    "source_kind": row["source_kind"],
                    "domain_id": edge.get("domain_id") or "unmapped",
                    "skill_id": edge.get("skill_id") or "unmapped",
                    "selected": [int(item) for item in json_list(row["selected_json"])],
                    "answered": bool(json_list(row["selected_json"])),
                    "flagged": bool(row["flagged"]),
                }
            )
    configuration = json.loads(session.get("configuration_json") or "{}")
    return {
        "session_id": session_id,
        "track_id": session["track_id"],
        "mode": session["mode"],
        "practice_test_id": session.get("practice_test_id"),
        "status": session["status"],
        "started_at": session["started_at"],
        "duration_seconds": int(session.get("duration_seconds") or 0),
        "remaining_seconds": _remaining_seconds(session),
        "configuration": configuration,
        "questions": questions,
        "total_questions": len(questions),
    }


def active_session(track_id: str = "snowpro-core") -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT id FROM exam_sessions WHERE track_id = ? AND status = 'in_progress' ORDER BY id DESC LIMIT 1",
            (track_id,),
        ).fetchone()
    return session_payload(int(row["id"])) if row else None


def save_answer(session_id: int, question_id: str, selected: list[int]) -> dict[str, Any]:
    cleaned = sorted(set(int(item) for item in selected))
    with connect() as conn:
        session = _session_row(conn, session_id)
    if session["status"] != "in_progress":
        raise HTTPException(status_code=409, detail="This exam has already been submitted")
    if _remaining_seconds(session) <= 0:
        submit_session(session_id, "timer")
        raise HTTPException(status_code=409, detail="Time expired; the exam was submitted")
    with connect() as conn:
        row = conn.execute(
            "SELECT options_json FROM exam_session_questions WHERE session_id = ? AND question_id = ?",
            (session_id, question_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Question is not part of this session")
        option_count = len(json_list(row["options_json"]))
        if any(index < 0 or index >= option_count for index in cleaned):
            raise HTTPException(status_code=400, detail="An answer option is outside the available range")
        conn.execute(
            """
            INSERT INTO exam_session_answers(session_id, question_id, selected_json, correct, answered_at)
            VALUES (?, ?, ?, 0, datetime('now'))
            ON CONFLICT(session_id, question_id) DO UPDATE SET
              selected_json=excluded.selected_json,
              answered_at=excluded.answered_at
            """,
            (session_id, question_id, json.dumps(cleaned)),
        )
    return {"ok": True, "question_id": question_id, "selected": cleaned}


def set_flag(session_id: int, question_id: str, flagged: bool) -> dict[str, Any]:
    with connect() as conn:
        session = _session_row(conn, session_id)
        if session["status"] != "in_progress":
            raise HTTPException(status_code=409, detail="This exam has already been submitted")
        cursor = conn.execute(
            "UPDATE exam_session_questions SET flagged = ? WHERE session_id = ? AND question_id = ?",
            (int(flagged), session_id, question_id),
        )
        if not cursor.rowcount:
            raise HTTPException(status_code=404, detail="Question is not part of this session")
    return {"ok": True, "question_id": question_id, "flagged": bool(flagged)}


def _domain_and_skill_lookup(track_id: str) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    cert = certification(track_id)
    domains = {domain["id"]: domain for domain in cert.get("domains") or []}
    skills = {skill["id"]: skill for skill in flatten_skills(track_id)}
    return domains, skills


def submit_session(session_id: int, reason: str = "learner") -> dict[str, Any]:
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        session = _session_row(conn, session_id)
        if session["status"] != "in_progress":
            return result_payload(session_id)
        rows = [
            dict(row)
            for row in conn.execute(
                """
                SELECT sq.question_id, sq.correct_positions_json,
                       COALESCE(a.selected_json, '[]') AS selected_json
                FROM exam_session_questions sq
                LEFT JOIN exam_session_answers a
                  ON a.session_id = sq.session_id AND a.question_id = sq.question_id
                WHERE sq.session_id = ? ORDER BY sq.position
                """,
                (session_id,),
            )
        ]
        domains, _ = _domain_and_skill_lookup(session["track_id"])
        session_configuration = json.loads(session.get("configuration_json") or "{}")
        counts_for_readiness = session_configuration.get("source_kind") != "legacy"
        stats: dict[str, dict[str, int]] = defaultdict(lambda: {"correct": 0, "total": 0})
        raw_correct = 0
        for row in rows:
            selected = sorted(set(int(item) for item in json_list(row["selected_json"])))
            correct = sorted(set(int(item) for item in json_list(row["correct_positions_json"])))
            is_correct = selected == correct
            raw_correct += int(is_correct)
            edge = _question_edge(conn, row["question_id"], session["track_id"])
            domain_id = edge.get("domain_id") or "unmapped"
            stats[domain_id]["total"] += 1
            stats[domain_id]["correct"] += int(is_correct)
            conn.execute(
                """
                INSERT INTO exam_session_answers(session_id, question_id, selected_json, correct, answered_at)
                VALUES (?, ?, ?, ?, datetime('now'))
                ON CONFLICT(session_id, question_id) DO UPDATE SET correct=excluded.correct
                """,
                (session_id, row["question_id"], json.dumps(selected), int(is_correct)),
            )
            if counts_for_readiness:
                conn.execute(
                    "INSERT INTO question_attempts(question_id, selected, correct, mode) VALUES (?, ?, ?, ?)",
                    (row["question_id"], json.dumps(selected), int(is_correct), session["mode"]),
                )

        total = len(rows)
        raw_accuracy = (raw_correct / total * 100) if total else 0.0
        weighted_accuracy = 0.0
        domain_payload = []
        for domain_id, domain in domains.items():
            item = stats.get(domain_id, {"correct": 0, "total": 0})
            accuracy = (item["correct"] / item["total"] * 100) if item["total"] else 0.0
            weight = float(domain.get("weight") or 0)
            weighted_accuracy += accuracy * weight / 100
            domain_payload.append(
                {
                    "domain_id": domain_id,
                    "title": domain.get("title"),
                    "weight": int(weight),
                    "correct": item["correct"],
                    "total": item["total"],
                    "accuracy": round(accuracy, 1),
                }
            )
        scaled_score = max(0, min(int(exam_config()["score_scale"]), round(weighted_accuracy * 10)))
        started = _parse_utc(session["started_at"])
        elapsed = min(
            int(session.get("duration_seconds") or 0),
            max(0, int(datetime.now(timezone.utc).timestamp() - started.timestamp())),
        )
        conn.execute(
            """
            UPDATE exam_sessions SET
              finished_at=datetime('now'), score=?, raw_correct=?, raw_accuracy=?,
              weighted_accuracy=?, scaled_score=?, elapsed_seconds=?, status='finished',
              submitted_reason=?
            WHERE id=? AND status='in_progress'
            """,
            (raw_correct, raw_correct, raw_accuracy, weighted_accuracy, scaled_score, elapsed, reason, session_id),
        )
        conn.execute(
            """
            INSERT INTO learning_events(event_type, track_id, practice_test_id, metadata_json)
            VALUES (?, ?, ?, ?)
            """,
            (
                "practice_test_finished" if counts_for_readiness else "legacy_practice_finished",
                session["track_id"],
                session.get("practice_test_id"),
                json.dumps(
                    {
                        "session_id": session_id,
                        "mode": session["mode"],
                        "scaled_score": scaled_score,
                        "raw_correct": raw_correct,
                        "total": total,
                        "elapsed_seconds": elapsed,
                        "domains": domain_payload,
                        "submitted_reason": reason,
                    }
                ),
            ),
        )
    return result_payload(session_id)


def result_payload(session_id: int) -> dict[str, Any]:
    with connect() as conn:
        session = _session_row(conn, session_id)
        if session["status"] == "in_progress":
            raise HTTPException(status_code=409, detail="Results are available only after submission")
        domains, skills = _domain_and_skill_lookup(session["track_id"])
        rows = [
            dict(row)
            for row in conn.execute(
                """
                SELECT sq.position, sq.question_id, sq.options_json, sq.correct_positions_json, sq.flagged,
                       q.question, q.explanation, q.multiple, q.test_title, q.source_kind,
                       COALESCE(a.selected_json, '[]') AS selected_json, COALESCE(a.correct, 0) AS is_correct
                FROM exam_session_questions sq
                JOIN questions q ON q.id = sq.question_id
                LEFT JOIN exam_session_answers a
                  ON a.session_id = sq.session_id AND a.question_id = sq.question_id
                WHERE sq.session_id = ? ORDER BY sq.position
                """,
                (session_id,),
            )
        ]
        domain_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"correct": 0, "total": 0})
        task_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"correct": 0, "total": 0})
        reviews = []
        for row in rows:
            edge = _question_edge(conn, row["question_id"], session["track_id"])
            domain_id = edge.get("domain_id") or "unmapped"
            skill_id = edge.get("skill_id") or "unmapped"
            domain_stats[domain_id]["total"] += 1
            domain_stats[domain_id]["correct"] += int(row["is_correct"])
            task_stats[skill_id]["total"] += 1
            task_stats[skill_id]["correct"] += int(row["is_correct"])
            reviews.append(
                {
                    "position": int(row["position"]),
                    "question_id": row["question_id"],
                    "question": row["question"],
                    "options": json_list(row["options_json"]),
                    "selected": [int(item) for item in json_list(row["selected_json"])],
                    "correct": [int(item) for item in json_list(row["correct_positions_json"])],
                    "is_correct": bool(row["is_correct"]),
                    "flagged": bool(row["flagged"]),
                    "multiple": bool(row["multiple"]),
                    "explanation": row["explanation"],
                    "domain_id": domain_id,
                    "domain_title": (domains.get(domain_id) or {}).get("title") or "Unmapped",
                    "skill_id": skill_id,
                    "task_code": (skills.get(skill_id) or {}).get("task_code") or "",
                    "skill_title": (skills.get(skill_id) or {}).get("title") or "Unmapped task",
                    "source_kind": row["source_kind"],
                    "test_title": row["test_title"],
                    "lesson_url": f"#/skill?track_id={session['track_id']}&skill_id={skill_id}",
                    "drill_url": f"#/practice?track_id={session['track_id']}&mode=drill&skill_id={skill_id}",
                }
            )
    domain_performance = []
    for domain_id, domain in domains.items():
        item = domain_stats.get(domain_id, {"correct": 0, "total": 0})
        accuracy = (item["correct"] / item["total"] * 100) if item["total"] else 0.0
        domain_performance.append(
            {
                "domain_id": domain_id,
                "title": domain.get("title"),
                "weight": int(domain.get("weight") or 0),
                "correct": item["correct"],
                "total": item["total"],
                "accuracy": round(accuracy, 1),
            }
        )
    task_performance = []
    for skill_id, item in task_stats.items():
        skill = skills.get(skill_id) or {}
        task_performance.append(
            {
                "skill_id": skill_id,
                "task_code": skill.get("task_code") or "",
                "title": skill.get("title") or "Unmapped task",
                "correct": item["correct"],
                "total": item["total"],
                "accuracy": round(item["correct"] / item["total"] * 100, 1) if item["total"] else 0,
                "lesson_url": f"#/skill?track_id={session['track_id']}&skill_id={skill_id}",
                "drill_url": f"#/practice?track_id={session['track_id']}&mode=drill&skill_id={skill_id}",
            }
        )
    task_performance.sort(key=lambda item: (item["accuracy"], item["task_code"]))
    pass_score = int(exam_config()["pass_scaled_score"])
    return {
        "session_id": session_id,
        "track_id": session["track_id"],
        "practice_test_id": session.get("practice_test_id"),
        "mode": session["mode"],
        "status": session["status"],
        "scaled_score": int(session.get("scaled_score") or 0),
        "score_scale": int(exam_config()["score_scale"]),
        "pass_scaled_score": pass_score,
        "ready": int(session.get("scaled_score") or 0) >= pass_score,
        "raw_correct": int(session.get("raw_correct") or 0),
        "total_questions": int(session.get("total_questions") or 0),
        "raw_accuracy": round(float(session.get("raw_accuracy") or 0), 1),
        "weighted_accuracy": round(float(session.get("weighted_accuracy") or 0), 1),
        "elapsed_seconds": int(session.get("elapsed_seconds") or 0),
        "submitted_reason": session.get("submitted_reason") or "learner",
        "scoring_note": exam_config()["scoring_note"],
        "domain_performance": domain_performance,
        "task_performance": task_performance,
        "strongest_tasks": [
            item
            for item in sorted(task_performance, key=lambda item: (-item["accuracy"], item["task_code"]))
            if item["accuracy"] > 0
        ][:3],
        "weakest_tasks": task_performance[:3],
        "reviews": reviews,
        "counts": {
            "correct": sum(1 for item in reviews if item["is_correct"]),
            "incorrect": sum(1 for item in reviews if not item["is_correct"] and item["selected"]),
            "unanswered": sum(1 for item in reviews if not item["selected"]),
            "flagged": sum(1 for item in reviews if item["flagged"]),
        },
    }


def history(track_id: str = "snowpro-core") -> dict[str, Any]:
    with connect() as conn:
        sessions = [
            dict(row)
            for row in conn.execute(
                """
                SELECT * FROM exam_sessions
                WHERE track_id = ? AND status = 'finished' AND mode LIKE 'exam_%'
                ORDER BY finished_at DESC, id DESC
                """,
                (track_id,),
            )
        ]
    rows = []
    for session in sessions:
        result = result_payload(int(session["id"]))
        weakest = min(result["domain_performance"], key=lambda item: item["accuracy"], default=None)
        rows.append(
            {
                "session_id": session["id"],
                "finished_at": session["finished_at"],
                "mode": session["mode"],
                "practice_test_id": session.get("practice_test_id"),
                "scaled_score": result["scaled_score"],
                "ready": result["ready"],
                "elapsed_seconds": result["elapsed_seconds"],
                "weakest_domain": weakest,
            }
        )
    return {"history": rows}
