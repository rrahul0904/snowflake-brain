from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from ..certification_content import configured_skill_map, content_coverage
from ..database import connect
from ..intelligence import command_brief, mistake_queue, portfolio, readiness_model, skill_mastery
from ..lab_challenges import labs as configured_labs

router = APIRouter()


def _certifications() -> list[dict[str, Any]]:
    return configured_skill_map().get("certifications") or []


def _normalize_track(track_id: str) -> tuple[str, list[dict[str, Any]]]:
    certs = _certifications()
    cert_ids = {cert.get("id") for cert in certs}
    if track_id not in cert_ids:
        track_id = "snowpro-core" if "snowpro-core" in cert_ids else (certs[0].get("id") if certs else track_id)
    return track_id, certs


def _summary(conn: Any, track_id: str) -> dict[str, Any]:
    def one(sql: str, params: tuple[Any, ...] = (), default: int = 0) -> int:
        try:
            row = conn.execute(sql, params).fetchone()
            return int((row or [default])[0] or 0)
        except Exception:
            return default

    configured_tasks = sum(len(domain.get("skills") or []) for cert in _certifications() if cert.get("id") == track_id for domain in cert.get("domains") or [])
    return {
        "configured_tasks": configured_tasks,
        "questions": one("SELECT COUNT(*) FROM questions q LEFT JOIN courses c ON c.id=q.course_id LEFT JOIN practice_tests pt ON pt.id=q.test_id WHERE COALESCE(c.track_id, pt.track_id, '') = ?", (track_id,)),
        "attempts": one("SELECT COUNT(*) FROM question_attempts a JOIN questions q ON q.id=a.question_id LEFT JOIN courses c ON c.id=q.course_id LEFT JOIN practice_tests pt ON pt.id=q.test_id WHERE COALESCE(c.track_id, pt.track_id, '') = ?", (track_id,)),
        "completed_tasks": one("SELECT COUNT(*) FROM certification_task_progress WHERE track_id = ? AND completed = 1", (track_id,)),
        "mock_exams": one("SELECT COUNT(*) FROM exam_sessions WHERE track_id = ? AND mode LIKE '%exam%' AND status='finished'", (track_id,)),
        "lab_events": one("SELECT COUNT(*) FROM learning_events WHERE track_id = ? AND event_type LIKE 'lab_%'", (track_id,)),
    }


def _content_trust(conn: Any, track_id: str) -> dict[str, Any]:
    coverage = next((row for row in content_coverage().get("tracks", []) if row.get("track_id") == track_id), {})
    try:
        question_total = int(conn.execute("SELECT COUNT(*) FROM question_skill_map WHERE track_id = ?", (track_id,)).fetchone()[0] or 0)
        reviewed = int(conn.execute("SELECT COUNT(*) FROM question_skill_map WHERE track_id = ? AND reviewed = 1", (track_id,)).fetchone()[0] or 0)
        strong = int(conn.execute("SELECT COUNT(*) FROM question_skill_map WHERE track_id = ? AND (reviewed=1 OR confidence >= 0.70)", (track_id,)).fetchone()[0] or 0)
        missing_explanation = int(conn.execute("SELECT COUNT(*) FROM questions q LEFT JOIN courses c ON c.id=q.course_id LEFT JOIN practice_tests pt ON pt.id=q.test_id WHERE COALESCE(c.track_id, pt.track_id, '') = ? AND LENGTH(COALESCE(q.explanation,'')) < 20", (track_id,)).fetchone()[0] or 0)
    except Exception:
        question_total = reviewed = strong = missing_explanation = 0
    return {
        "usable_task_lessons": coverage.get("usable_tasks", 0),
        "curated_task_lessons": coverage.get("curated_tasks", 0),
        "generated_task_lessons": coverage.get("generated_tasks", 0),
        "question_mapping_edges": question_total,
        "reviewed_mapping_edges": reviewed,
        "reliable_mapping_edges": strong,
        "questions_without_explanation": missing_explanation,
    }


def _lab_preview(track_id: str) -> list[dict[str, Any]]:
    rows = []
    for lab in configured_labs():
        if track_id and lab.get("certification") != track_id:
            continue
        rows.append({"id": lab.get("id"), "title": lab.get("title"), "domain": lab.get("domain"), "difficulty": lab.get("difficulty"), "estimated_minutes": lab.get("estimated_minutes") or lab.get("minutes"), "skill_id": lab.get("skill_id")})
    return rows[:8]


@router.get("/experience/shell")
def experience_shell(track_id: str = "snowpro-core") -> dict[str, Any]:
    """Fast certification-product payload. No course/video progress is part of this contract."""
    track_id, certs = _normalize_track(track_id)
    with connect() as conn:
        readiness = readiness_model(conn, track_id)
        return {
            "selected_track_id": track_id,
            "summary": _summary(conn, track_id),
            "content_trust": _content_trust(conn, track_id),
            "certifications": certs,
            "portfolio": {"certifications": []},
            "command_brief": command_brief(conn, track_id, readiness=readiness, mistakes={"track_id": track_id, "items": [], "total_unresolved": 0}),
            "readiness": readiness,
            "mastery": {"track_id": track_id, "skills": [], "domains": []},
            "mistakes": {"track_id": track_id, "items": [], "total_unresolved": 0},
            "diagnostic": {"track_id": track_id, "question_ids": [], "domains": []},
            "labs": _lab_preview(track_id),
        }


@router.get("/experience/command-center")
def command_center(track_id: str = "snowpro-core") -> dict[str, Any]:
    track_id, certs = _normalize_track(track_id)
    with connect() as conn:
        mastery = skill_mastery(conn, track_id)
        readiness = readiness_model(conn, track_id, mastery=mastery)
        mistakes = mistake_queue(conn, track_id, limit=8)
        return {
            "selected_track_id": track_id,
            "summary": _summary(conn, track_id),
            "content_trust": _content_trust(conn, track_id),
            "certifications": certs,
            "portfolio": portfolio(conn),
            "command_brief": command_brief(conn, track_id, readiness=readiness, mistakes=mistakes),
            "readiness": readiness,
            "mastery": mastery,
            "mistakes": mistakes,
            "diagnostic": {"track_id": track_id, "question_ids": [], "domains": []},
            "labs": _lab_preview(track_id),
        }
