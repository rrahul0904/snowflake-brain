from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from ..certification_content import configured_skill_map, content_coverage
from ..config import DATABASE_BACKEND
from ..database import connect
from ..intelligence import command_brief, mistake_queue, portfolio, readiness_model, skill_mastery
from ..lab_challenges import labs as configured_labs
from ..learning_intelligence import study_plan
from ..task_review import due_task_reviews
from ..auth import require_candidate, require_premium_candidate

router = APIRouter()


def _certifications() -> list[dict[str, Any]]:
    return configured_skill_map().get("certifications") or []


def _normalize_track(track_id: str) -> tuple[str, list[dict[str, Any]]]:
    certs = _certifications()
    cert_ids = {cert.get("id") for cert in certs}
    if track_id not in cert_ids:
        track_id = "snowpro-core" if "snowpro-core" in cert_ids else (certs[0].get("id") if certs else track_id)
    return track_id, certs


def _summary(conn: Any, track_id: str, candidate_id: int) -> dict[str, Any]:
    def one(sql: str, params: tuple[Any, ...] = (), default: int = 0) -> int:
        try:
            row = conn.execute(sql, params).fetchone()
            return int((row or [default])[0] or 0)
        except Exception:
            return default

    configured_tasks = sum(
        len(domain.get("skills") or [])
        for cert in _certifications()
        if cert.get("id") == track_id
        for domain in cert.get("domains") or []
    )
    return {
        "configured_tasks": configured_tasks,
        "questions": one("SELECT COUNT(*) FROM questions WHERE track_id = ? AND source_kind <> 'legacy'", (track_id,)),
        "source_questions": one("SELECT COUNT(*) FROM questions WHERE track_id = ? AND source_kind = 'source'", (track_id,)),
        "attempts": one(
            "SELECT COUNT(*) FROM question_attempts a JOIN questions q ON q.id=a.question_id WHERE a.candidate_id = ? AND q.track_id = ? AND q.source_kind <> 'legacy'",
            (candidate_id, track_id),
        ),
        "completed_tasks": one(
            "SELECT COUNT(*) FROM candidate_task_progress WHERE candidate_id = ? AND track_id = ? AND completed = 1",
            (candidate_id, track_id),
        ),
        "mock_exams": one(
            "SELECT COUNT(*) FROM exam_sessions WHERE candidate_id = ? AND track_id = ? AND mode LIKE '%exam%' AND status='finished'",
            (candidate_id, track_id),
        ),
        "source_exams": one(
            "SELECT COUNT(*) FROM practice_tests WHERE track_id = ? AND source_kind = 'source' AND is_legacy = 0",
            (track_id,),
        ),
        "lab_events": one(
            "SELECT COUNT(*) FROM learning_events WHERE candidate_id = ? AND track_id = ? AND event_type LIKE 'lab_%'",
            (candidate_id, track_id),
        ),
    }


def _content_trust(conn: Any, track_id: str) -> dict[str, Any]:
    coverage = next((row for row in content_coverage().get("tracks", []) if row.get("track_id") == track_id), {})
    try:
        question_total = int(conn.execute("SELECT COUNT(*) FROM question_skill_map WHERE track_id = ?", (track_id,)).fetchone()[0] or 0)
        reviewed = int(conn.execute("SELECT COUNT(*) FROM question_skill_map WHERE track_id = ? AND reviewed = 1", (track_id,)).fetchone()[0] or 0)
        strong = int(
            conn.execute(
                "SELECT COUNT(*) FROM question_skill_map WHERE track_id = ? AND (reviewed=1 OR confidence >= 0.70)",
                (track_id,),
            ).fetchone()[0]
            or 0
        )
        missing_explanation = int(
            conn.execute(
                "SELECT COUNT(*) FROM questions WHERE track_id = ? AND source_kind <> 'legacy' AND LENGTH(COALESCE(explanation,'')) < 20",
                (track_id,),
            ).fetchone()[0]
            or 0
        )
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


def _home_summary(conn: Any, track_id: str, candidate_id: int, certs: list[dict[str, Any]]) -> dict[str, Any]:
    """Bounded, read-only data contract for the Home command center.

    The client used to fan out into eight independently slow requests. This
    single endpoint intentionally returns counts and compact evidence only;
    it never syncs legacy attempts, creates schema, or returns question text.
    """
    def count(statement: str, params: tuple[Any, ...]) -> int:
        row = conn.execute(statement, params).fetchone()
        return int((dict(row) if row else {}).get("n") or 0)

    question_due = count(
        "SELECT COUNT(*) AS n FROM candidate_srs_state WHERE candidate_id=? AND track_id=? AND datetime(due_at)<=datetime('now')",
        (candidate_id, track_id),
    )
    if DATABASE_BACKEND == "sqlite":
        # Local SQLite keeps its isolated test fixture bootstrap. PostgreSQL
        # takes the strictly read-only query below because migration 022 owns
        # this table in every hosted environment.
        task_due = int(due_task_reviews(conn, candidate_id, track_id, limit=1).get("task_due_count") or 0)
    else:
        task_due = count(
            "SELECT COUNT(*) AS n FROM candidate_task_reviews WHERE candidate_id=? AND track_id=? AND status='active' AND datetime(next_review_at)<=datetime('now')",
            (candidate_id, track_id),
        )
    mistake_rows = conn.execute(
        "SELECT status,COUNT(*) AS n FROM candidate_mistake_notebook WHERE candidate_id=? AND track_id=? GROUP BY status",
        (candidate_id, track_id),
    ).fetchall()
    mistake_counts = {str(row["status"]): int(row["n"] or 0) for row in mistake_rows}
    progress_rows = conn.execute(
        "SELECT skill_id FROM candidate_task_progress WHERE candidate_id=? AND track_id=? AND completed=1 ORDER BY skill_id",
        (candidate_id, track_id),
    ).fetchall()
    history = [
        dict(row)
        for row in conn.execute(
            "SELECT mode,scaled_score,finished_at FROM exam_sessions WHERE candidate_id=? AND track_id=? AND status='finished' ORDER BY datetime(finished_at) DESC,id DESC LIMIT 1",
            (candidate_id, track_id),
        ).fetchall()
    ]
    attempt_rows = conn.execute(
        """
        SELECT qsm.skill_id,COUNT(*) AS attempts,
               ROUND(100.0 * AVG(CASE WHEN a.correct THEN 1 ELSE 0 END),1) AS accuracy_pct
          FROM question_attempts a JOIN questions q ON q.id=a.question_id
          JOIN question_skill_map qsm ON qsm.question_id=q.id AND qsm.track_id=q.track_id
         WHERE a.candidate_id=? AND q.track_id=? AND (qsm.reviewed=1 OR qsm.confidence>=0.70)
         GROUP BY qsm.skill_id ORDER BY attempts DESC LIMIT 24
        """,
        (candidate_id, track_id),
    ).fetchall()
    configured_skills = {
        str(skill.get("id")): str(skill.get("title") or skill.get("id"))
        for cert in certs if cert.get("id") == track_id
        for domain in cert.get("domains") or [] for skill in domain.get("skills") or []
    }
    skills = [
        {"skill_id": str(row["skill_id"]), "skill": configured_skills.get(str(row["skill_id"]), str(row["skill_id"])), "attempts": int(row["attempts"] or 0), "accuracy_pct": float(row["accuracy_pct"] or 0)}
        for row in attempt_rows
    ]
    latest_readiness = conn.execute(
        "SELECT readiness_score,evidence_confidence FROM candidate_readiness_snapshots WHERE candidate_id=? AND track_id=? ORDER BY created_at DESC,id DESC LIMIT 1",
        (candidate_id, track_id),
    ).fetchone()
    total_tasks = len(configured_skills)
    return {
        "track_id": track_id,
        "due": {"due_count": question_due + task_due, "question_due_count": question_due, "task_due_count": task_due, "questions": [], "task_reviews": []},
        "mistakes": {"counts": mistake_counts, "items": []},
        "plan": study_plan(conn, candidate_id, track_id),
        "summary": {"skills": skills, "domains": []},
        "history": {"history": history},
        "map": {"certifications": certs},
        "progress": {"completed_skill_ids": [str(row["skill_id"]) for row in progress_rows], "completed_tasks": len(progress_rows), "total_tasks": total_tasks},
        "readiness": dict(latest_readiness) if latest_readiness else {},
    }


@router.get("/candidate/home-summary")
def candidate_home_summary(track_id: str = "snowpro-core", candidate: dict = Depends(require_candidate)) -> dict[str, Any]:
    track_id, certs = _normalize_track(track_id)
    with connect() as conn:
        return _home_summary(conn, track_id, int(candidate["id"]), certs)


@router.get("/experience/shell")
def experience_shell(track_id: str = "snowpro-core", candidate: dict = Depends(require_candidate)) -> dict[str, Any]:
    """Fast certification-product payload. No course/video state exists in this contract."""
    track_id, certs = _normalize_track(track_id)
    with connect() as conn:
        readiness = readiness_model(conn, track_id, candidate_id=candidate["id"]) if candidate["is_premium"] else {"premium_required": True}
        return {
            "selected_track_id": track_id,
            "summary": _summary(conn, track_id, candidate["id"]),
            "content_trust": _content_trust(conn, track_id),
            "certifications": certs,
            "portfolio": {"certifications": []},
            "command_brief": command_brief(
                conn,
                track_id,
                readiness=readiness,
                mistakes={"track_id": track_id, "items": [], "total_unresolved": 0},
                candidate_id=candidate["id"],
            ) if candidate["is_premium"] else {"premium_required": True, "mission": []},
            "readiness": readiness,
            "mastery": {"track_id": track_id, "skills": [], "domains": []},
            "mistakes": {"track_id": track_id, "items": [], "total_unresolved": 0},
            "diagnostic": {"track_id": track_id, "question_ids": [], "domains": []},
            "labs": _lab_preview(track_id),
        }


@router.get("/experience/command-center")
def command_center(track_id: str = "snowpro-core", candidate: dict = Depends(require_premium_candidate)) -> dict[str, Any]:
    track_id, certs = _normalize_track(track_id)
    with connect() as conn:
        mastery = skill_mastery(conn, track_id, candidate_id=candidate["id"])
        readiness = readiness_model(conn, track_id, mastery=mastery, candidate_id=candidate["id"])
        mistakes = mistake_queue(conn, track_id, limit=8, candidate_id=candidate["id"])
        return {
            "selected_track_id": track_id,
            "summary": _summary(conn, track_id, candidate["id"]),
            "content_trust": _content_trust(conn, track_id),
            "certifications": certs,
            "portfolio": portfolio(conn, candidate_id=candidate["id"]),
            "command_brief": command_brief(conn, track_id, readiness=readiness, mistakes=mistakes, candidate_id=candidate["id"]),
            "readiness": readiness,
            "mastery": mastery,
            "mistakes": mistakes,
            "diagnostic": {"track_id": track_id, "question_ids": [], "domains": []},
            "labs": _lab_preview(track_id),
        }
