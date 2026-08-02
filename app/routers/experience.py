from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter

from ..database import connect
from ..intelligence import command_brief, diagnostic_plan, mistake_queue, portfolio, readiness_model, skill_mastery
from ..lab_challenges import labs as configured_labs
from ..skill_brain import certifications

router = APIRouter()
_CACHE_TTL_SECONDS = 60
_CACHE: dict[tuple[str, str], tuple[float, dict[str, Any]]] = {}


def _cached(kind: str, track_id: str) -> dict[str, Any] | None:
    item = _CACHE.get((kind, track_id))
    if not item:
        return None
    created_at, payload = item
    if time.monotonic() - created_at > _CACHE_TTL_SECONDS:
        _CACHE.pop((kind, track_id), None)
        return None
    return payload


def _store_cache(kind: str, track_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    _CACHE[(kind, track_id)] = (time.monotonic(), payload)
    return payload


def _normalize_track(track_id: str) -> tuple[str, list[dict[str, Any]]]:
    certs = certifications()
    cert_ids = {cert.get("id") for cert in certs}
    if track_id not in cert_ids:
        track_id = "snowpro-core" if "snowpro-core" in cert_ids else (certs[0].get("id") if certs else track_id)
    return track_id, certs


def _summary(conn) -> dict[str, Any]:
    def one(sql: str, default: int = 0) -> int:
        try:
            row = conn.execute(sql).fetchone()
            if not row:
                return default
            return int(row[0] or 0)
        except Exception:
            return default

    return {
        "courses": one("SELECT COUNT(*) FROM courses"),
        "lessons": one("SELECT COUNT(*) FROM lessons"),
        "questions": one("SELECT COUNT(*) FROM questions"),
        "practice_tests": one("SELECT COUNT(*) FROM practice_tests"),
        "attempts": one("SELECT COUNT(*) FROM question_attempts"),
        "flashcards": one("SELECT COUNT(*) FROM flashcards"),
        "lab_events": one("SELECT COUNT(*) FROM learning_events WHERE event_type LIKE 'lab_%'"),
    }


def _content_trust(conn) -> dict[str, Any]:
    def one(sql: str, default: int = 0) -> int:
        try:
            row = conn.execute(sql).fetchone()
            return int((row or [default])[0] or 0)
        except Exception:
            return default

    return {
        "generated_notes": one("SELECT COUNT(*) FROM lessons WHERE COALESCE(transcript_text, '') LIKE '%English study notes%'"),
        "missing_duration": one("SELECT COUNT(*) FROM lessons WHERE COALESCE(duration_s, 0) = 0"),
        "empty_practice_shells": one("SELECT COUNT(*) FROM practice_tests WHERE COALESCE(question_count, 0) = 0"),
        "questions_without_explanation": one("SELECT COUNT(*) FROM questions WHERE LENGTH(COALESCE(explanation, '')) < 20"),
    }


def _lab_preview(track_id: str) -> list[dict[str, Any]]:
    rows = []
    for lab in configured_labs():
        if track_id and lab.get("certification") != track_id:
            continue
        rows.append(
            {
                "id": lab.get("id"),
                "title": lab.get("title"),
                "domain": lab.get("domain"),
                "difficulty": lab.get("difficulty"),
                "estimated_minutes": lab.get("estimated_minutes") or lab.get("minutes"),
                "skill_id": lab.get("skill_id"),
            }
        )
    return rows[:8]


def _readiness_snapshot(conn, track_id: str) -> dict[str, Any]:
    def row(sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any]:
        try:
            result = conn.execute(sql, params).fetchone()
            return dict(result) if result else {}
        except Exception:
            return {}

    attempts_row = row(
        """
        SELECT
          COUNT(a.id) AS attempts,
          SUM(CASE WHEN COALESCE(a.correct, 0) = 1 THEN 1 ELSE 0 END) AS correct,
          SUM(CASE WHEN COALESCE(a.correct, 0) = 0 THEN 1 ELSE 0 END) AS misses
        FROM question_attempts a
        JOIN questions q ON q.id = a.question_id
        LEFT JOIN courses c ON c.id = q.course_id
        LEFT JOIN practice_tests pt ON pt.id = q.test_id
        WHERE (? = '' OR COALESCE(c.track_id, pt.track_id, '') = ?)
        """,
        (track_id or "", track_id or ""),
    )
    attempts = int(attempts_row.get("attempts") or 0)
    correct = int(attempts_row.get("correct") or 0)
    misses = int(attempts_row.get("misses") or 0)
    accuracy = round((correct / attempts) * 100) if attempts else 0

    exam_row = row(
        """
        SELECT COUNT(*) AS mock_exam_attempts, MAX(score) AS best_mock_score
        FROM exam_sessions
        WHERE (? = '' OR track_id = ?) AND mode LIKE '%exam%' AND status = 'finished'
        """,
        (track_id or "", track_id or ""),
    )
    mock_attempts = int(exam_row.get("mock_exam_attempts") or 0)
    best_mock = int(exam_row.get("best_mock_score") or 0)

    lesson_row = row(
        """
        SELECT
          COUNT(lp.lesson_id) AS completed_lessons
        FROM lesson_progress lp
        JOIN lessons l ON l.id = lp.lesson_id
        LEFT JOIN courses c ON c.id = l.course_id
        WHERE COALESCE(lp.completed, 0) = 1 AND (? = '' OR COALESCE(c.track_id, '') = ?)
        """,
        (track_id or "", track_id or ""),
    )
    completed_lessons = int(lesson_row.get("completed_lessons") or 0)

    total_lesson_row = row(
        """
        SELECT COUNT(l.id) AS total_lessons
        FROM lessons l
        LEFT JOIN courses c ON c.id = l.course_id
        WHERE (? = '' OR COALESCE(c.track_id, '') = ?)
        """,
        (track_id or "", track_id or ""),
    )
    total_lessons = int(total_lesson_row.get("total_lessons") or 0)

    lab_passed_row = row(
        """
        SELECT COUNT(*) AS lab_passed
        FROM learning_events
        WHERE event_type = 'lab_passed' AND (? = '' OR track_id = ? OR json_extract(metadata_json, '$.track_id') = ?)
        """,
        (track_id or "", track_id or "", track_id or ""),
    )
    lab_passed = int(lab_passed_row.get("lab_passed") or 0)
    lab_available = sum(1 for lab in configured_labs() if not track_id or lab.get("certification") == track_id)

    score = 0
    score += min(25, attempts / 4)
    score += (accuracy / 100) * 30 if attempts else 0
    score += min(15, mock_attempts * 7)
    score += 10 if best_mock >= 80 else 0
    score += min(10, lab_passed * 2) if lab_available else 4
    score += min(10, (completed_lessons / max(1, total_lessons)) * 10)
    score = int(max(0, min(100, score)))

    blockers = []
    if attempts < 100:
        blockers.append(f"Question evidence is thin: {attempts} attempts recorded; target at least 100 before trusting readiness.")
    if mock_attempts < 2:
        blockers.append("No evidence of two finished timed readiness/mock exams.")
    if best_mock and best_mock < 80:
        blockers.append(f"Best timed exam score is {best_mock}%; target 80%+.")
    if lab_available and lab_passed < min(3, lab_available):
        blockers.append(f"Only {lab_passed}/{lab_available} available labs are proven.")

    if score >= 82 and not blockers:
        status = "exam_ready"
    elif score >= 70:
        status = "near_ready"
    elif score >= 45:
        status = "needs_repair"
    elif attempts or completed_lessons:
        status = "learning"
    else:
        status = "not_started"

    return {
        "track_id": track_id,
        "status": status,
        "readiness_score": score,
        "pass_probability_range": [max(0, score - 8), min(99, score + 6)],
        "attempts": attempts,
        "accuracy_pct": accuracy,
        "misses": misses,
        "mock_exam_attempts": mock_attempts,
        "best_mock_score": best_mock,
        "lab_passed": lab_passed,
        "lab_available": lab_available,
        "completed_lessons": completed_lessons,
        "total_lessons": total_lessons,
        "avg_mastery_level": 0,
        "blockers": blockers,
        "next_actions": [],
        "domains": [],
        "weak_skills": [],
    }


def _portfolio_snapshot(conn, certs: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for cert in certs:
        track_id = cert.get("id") or ""
        readiness = _readiness_snapshot(conn, track_id)
        rows.append(
            {
                "track_id": track_id,
                "title": cert.get("title"),
                "status": readiness.get("status"),
                "readiness_score": readiness.get("readiness_score"),
                "pass_probability_range": readiness.get("pass_probability_range"),
                "blocker_count": len(readiness.get("blockers") or []),
                "primary_blocker": (readiness.get("blockers") or ["No blocker detected"])[0],
                "attempts": readiness.get("attempts"),
                "avg_mastery_level": readiness.get("avg_mastery_level"),
            }
        )
    return {"certifications": rows, "recommended_order": sorted(rows, key=lambda item: item.get("readiness_score") or 0, reverse=True)}


def _command_brief_snapshot(track_id: str, readiness: dict[str, Any]) -> dict[str, Any]:
    mission = []
    if readiness.get("attempts", 0) < 30:
        mission.append({"type": "diagnostic", "title": "Run baseline diagnostic", "detail": "Answer a balanced diagnostic set before trusting the plan.", "href": f"#/practice?track_id={track_id}&mode=diagnostic"})
    if readiness.get("mock_exam_attempts", 0) < 2:
        mission.append({"type": "readiness_exam", "title": "Take a timed readiness exam", "detail": "Create exam-condition evidence for the readiness gate.", "href": f"#/practice?track_id={track_id}&mode=exam"})
    if readiness.get("lab_available", 0) and readiness.get("lab_passed", 0) < min(3, readiness.get("lab_available", 0)):
        mission.append({"type": "lab", "title": "Prove one lab skill", "detail": "Complete a lab so the gate has practical evidence.", "href": f"#/labs?certification={track_id}"})
    return {"track_id": track_id, "readiness": readiness, "mistake_count": 0, "mission": mission[:5]}


@router.get("/experience/shell")
def experience_shell(track_id: str = "snowpro-core") -> dict[str, Any]:
    """Fast payload for navigation, topbar, and non-graph page startup."""
    track_id, certs = _normalize_track(track_id)
    cached = _cached("shell", track_id)
    if cached:
        return cached
    with connect() as conn:
        readiness = _readiness_snapshot(conn, track_id)
        payload = {
            "selected_track_id": track_id,
            "summary": _summary(conn),
            "content_trust": _content_trust(conn),
            "certifications": certs,
            "portfolio": _portfolio_snapshot(conn, certs),
            "command_brief": _command_brief_snapshot(track_id, readiness),
            "readiness": readiness,
            "mastery": {"track_id": track_id, "skills": [], "domains": []},
            "mistakes": {"track_id": track_id, "items": [], "total_unresolved": 0},
            "diagnostic": {"track_id": track_id, "question_ids": [], "domains": []},
            "labs": _lab_preview(track_id),
        }
        return _store_cache("shell", track_id, payload)


@router.get("/experience/command-center")
def command_center(track_id: str = "snowpro-core") -> dict[str, Any]:
    """Single payload for the product command center UI.

    Track selection is normalized here so every page and the topbar read from the same source of truth.
    """
    track_id, certs = _normalize_track(track_id)
    cached = _cached("command", track_id)
    if cached:
        return cached
    with connect() as conn:
        mastery = skill_mastery(conn, track_id)
        readiness = readiness_model(conn, track_id, mastery=mastery)
        mistakes = mistake_queue(conn, track_id, limit=8)
        payload = {
            "selected_track_id": track_id,
            "summary": _summary(conn),
            "content_trust": _content_trust(conn),
            "certifications": certs,
            "portfolio": _portfolio_snapshot(conn, certs),
            "command_brief": command_brief(conn, track_id, readiness=readiness, mistakes=mistakes),
            "readiness": readiness,
            "mastery": mastery,
            "mistakes": mistakes,
            "diagnostic": {"track_id": track_id, "question_ids": [], "domains": []},
            "labs": _lab_preview(track_id),
        }
        return _store_cache("command", track_id, payload)
