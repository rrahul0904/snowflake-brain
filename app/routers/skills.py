from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..certification_content import certification_catalog, configured_skill_map, content_coverage, study_lesson
from ..database import connect
from ..skill_brain import certification, flatten_skills, skill_score

router = APIRouter()


class TaskProgressUpdate(BaseModel):
    track_id: str = "snowpro-core"
    skill_id: str
    completed: bool = True


def _ensure_task_progress(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS certification_task_progress (
          track_id TEXT NOT NULL,
          skill_id TEXT NOT NULL,
          completed INTEGER NOT NULL DEFAULT 0,
          completed_at TEXT,
          updated_at TEXT DEFAULT (datetime('now')),
          PRIMARY KEY(track_id, skill_id)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_cert_task_progress_track ON certification_task_progress(track_id, completed)"
    )


def _question_text(row: dict[str, Any]) -> str:
    return " ".join(
        [
            row.get("question") or "",
            row.get("explanation") or "",
            row.get("tags") or "",
            row.get("test_title") or "",
            row.get("course_title") or "",
        ]
    )


@router.get("/skills/map")
def skill_map() -> dict[str, Any]:
    return configured_skill_map()


@router.get("/skills/catalog")
def skill_catalog() -> dict[str, Any]:
    return certification_catalog()


@router.get("/skills/content-coverage")
def skill_content_coverage() -> dict[str, Any]:
    return content_coverage()


@router.get("/skills/task-progress")
def task_progress(track_id: str = "snowpro-core") -> dict[str, Any]:
    configured = {skill["id"]: skill for skill in flatten_skills(track_id)}
    with connect() as conn:
        _ensure_task_progress(conn)
        rows = [
            dict(row)
            for row in conn.execute(
                """
                SELECT track_id, skill_id, completed, completed_at, updated_at
                FROM certification_task_progress
                WHERE track_id = ?
                ORDER BY skill_id
                """,
                (track_id,),
            )
        ]
    completed_ids = {row["skill_id"] for row in rows if int(row.get("completed") or 0) == 1}
    return {
        "track_id": track_id,
        "total_tasks": len(configured),
        "completed_tasks": len(completed_ids & set(configured)),
        "completed_skill_ids": sorted(completed_ids & set(configured)),
        "items": rows,
    }


@router.post("/skills/task-progress")
def update_task_progress(payload: TaskProgressUpdate) -> dict[str, Any]:
    configured = {skill["id"]: skill for skill in flatten_skills(payload.track_id)}
    if payload.skill_id not in configured:
        raise HTTPException(status_code=404, detail="Skill is not configured for this certification")
    with connect() as conn:
        _ensure_task_progress(conn)
        conn.execute(
            """
            INSERT INTO certification_task_progress(track_id, skill_id, completed, completed_at, updated_at)
            VALUES (?, ?, ?, CASE WHEN ? = 1 THEN datetime('now') ELSE NULL END, datetime('now'))
            ON CONFLICT(track_id, skill_id) DO UPDATE SET
              completed = excluded.completed,
              completed_at = CASE WHEN excluded.completed = 1 THEN datetime('now') ELSE NULL END,
              updated_at = datetime('now')
            """,
            (payload.track_id, payload.skill_id, int(payload.completed), int(payload.completed)),
        )
    return {
        "track_id": payload.track_id,
        "skill_id": payload.skill_id,
        "completed": payload.completed,
    }


@router.get("/skills/summary")
def skill_summary(track_id: str = "snowpro-core") -> dict[str, Any]:
    cert = certification(track_id)
    # Overlay current public metadata without changing the underlying curriculum ids.
    cert = next((item for item in configured_skill_map().get("certifications", []) if item.get("id") == track_id), cert)
    skills = flatten_skills(track_id)
    with connect() as conn:
        _ensure_task_progress(conn)
        question_rows = [
            dict(row)
            for row in conn.execute(
                """
                SELECT q.id, q.question, q.explanation, q.tags, q.test_title, q.course_title,
                       COALESCE(c.track_id, pt.track_id, '') AS track_id,
                       COUNT(a.id) AS attempts,
                       SUM(CASE WHEN COALESCE(a.correct, 0) = 1 THEN 1 ELSE 0 END) AS correct_attempts
                FROM questions q
                LEFT JOIN question_attempts a ON a.question_id = q.id
                LEFT JOIN courses c ON c.id = q.course_id
                LEFT JOIN practice_tests pt ON pt.id = q.test_id
                WHERE (? = '' OR COALESCE(c.track_id, pt.track_id, '') = ? OR COALESCE(q.course_id, '') IN (SELECT id FROM courses WHERE track_id = ?))
                GROUP BY q.id
                LIMIT 8000
                """,
                (track_id or "", track_id or "", track_id or ""),
            )
        ]
        reliable_edges = [
            dict(row)
            for row in conn.execute(
                """
                SELECT question_id, skill_id, domain_id, confidence, reviewed
                FROM question_skill_map
                WHERE track_id = ? AND (reviewed = 1 OR confidence >= 0.70)
                ORDER BY reviewed DESC, confidence DESC
                """,
                (track_id,),
            )
        ]
        completed = {
            row["skill_id"]
            for row in conn.execute(
                "SELECT skill_id FROM certification_task_progress WHERE track_id = ? AND completed = 1",
                (track_id,),
            )
        }
        lab_events = [
            dict(row)
            for row in conn.execute(
                """
                SELECT lab_id, COUNT(*) AS attempts,
                       SUM(CASE WHEN event_type = 'lab_passed' THEN 1 ELSE 0 END) AS passed
                FROM learning_events
                WHERE lab_id IS NOT NULL
                GROUP BY lab_id
                """
            )
        ]

    best_edge_by_question: dict[str, dict[str, Any]] = {}
    for edge in reliable_edges:
        best_edge_by_question.setdefault(edge["question_id"], edge)

    output = []
    total_questions = len(question_rows)
    for skill in skills:
        q_matches = []
        for row in question_rows:
            reliable = best_edge_by_question.get(row["id"])
            if reliable:
                if reliable.get("skill_id") == skill.get("id"):
                    q_matches.append((float(reliable.get("confidence") or 1), row))
                continue
            score = skill_score(_question_text(row), skill)
            if score:
                q_matches.append((score, row))
        attempts = sum(int(row.get("attempts") or 0) for _, row in q_matches)
        correct = sum(int(row.get("correct_attempts") or 0) for _, row in q_matches)
        accuracy = round((correct / attempts) * 100) if attempts else 0
        coverage_pct = round((len(q_matches) / total_questions) * 100) if total_questions else 0
        completed_task = skill.get("id") in completed
        status = "completed" if completed_task else "available"
        if attempts:
            status = "strong" if accuracy >= 80 else "needs_review" if accuracy >= 60 else "weak"
        output.append(
            {
                "skill_id": skill.get("id"),
                "skill": skill.get("title"),
                "domain_id": skill.get("domain_id"),
                "domain": skill.get("domain"),
                "objective": skill.get("objective"),
                "question_count": len(q_matches),
                "attempts": attempts,
                "correct_attempts": correct,
                "accuracy_pct": accuracy,
                "coverage_pct": coverage_pct,
                "completed": completed_task,
                "status": status,
                "exam_traps": skill.get("exam_traps") or [],
            }
        )

    domain_summary: dict[str, dict[str, Any]] = {}
    for row in output:
        domain = row["domain"] or "Other"
        item = domain_summary.setdefault(
            domain,
            {
                "domain": domain,
                "domain_id": row.get("domain_id") or "",
                "skills": 0,
                "completed_tasks": 0,
                "question_count": 0,
                "attempts": 0,
                "correct_attempts": 0,
                "accuracy_pct": 0,
            },
        )
        item["skills"] += 1
        item["completed_tasks"] += int(bool(row["completed"]))
        item["question_count"] += row["question_count"]
        item["attempts"] += row["attempts"]
        item["correct_attempts"] += row["correct_attempts"]
    for item in domain_summary.values():
        item["accuracy_pct"] = round((item["correct_attempts"] / item["attempts"]) * 100) if item["attempts"] else 0

    return {
        "certification": cert,
        "skills": output,
        "domains": list(domain_summary.values()),
        "lab_activity": lab_events,
    }


@router.get("/skills/{skill_id}/lesson")
def skill_lesson(skill_id: str, track_id: str = "snowpro-core") -> dict[str, Any]:
    lesson = study_lesson(track_id, skill_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Study lesson is not configured for this certification task")
    return lesson


@router.get("/skills/{skill_id}/resources")
def skill_resources(skill_id: str, track_id: str = "snowpro-core", limit: int = 12) -> dict[str, Any]:
    skills = {skill["id"]: skill for skill in flatten_skills(track_id)}
    skill = skills.get(skill_id)
    if not skill:
        return {"skill": None, "questions": [], "mapping_strategy": "none"}
    limit = max(1, min(50, limit))
    with connect() as conn:
        persisted = [
            dict(row)
            for row in conn.execute(
                """
                SELECT q.id, q.question, q.options_json, q.correct_json, q.explanation,
                       q.tags, q.test_title, q.course_title, qsm.confidence, qsm.reviewed
                FROM question_skill_map qsm
                JOIN questions q ON q.id = qsm.question_id
                WHERE qsm.track_id = ? AND qsm.skill_id = ? AND (qsm.reviewed = 1 OR qsm.confidence >= 0.70)
                ORDER BY qsm.reviewed DESC, qsm.confidence DESC, q.id
                LIMIT ?
                """,
                (track_id, skill_id, limit),
            )
        ]
        if persisted:
            return {"skill": skill, "questions": persisted, "mapping_strategy": "persisted_reliable"}
        questions = [
            dict(row)
            for row in conn.execute(
                """
                SELECT q.id, q.question, q.options_json, q.correct_json, q.explanation,
                       q.tags, q.test_title, q.course_title
                FROM questions q
                LEFT JOIN courses c ON c.id = q.course_id
                LEFT JOIN practice_tests pt ON pt.id = q.test_id
                WHERE (? = '' OR COALESCE(c.track_id, pt.track_id, '') = ? OR COALESCE(q.course_id, '') IN (SELECT id FROM courses WHERE track_id = ?))
                LIMIT 2000
                """,
                (track_id or "", track_id or "", track_id or ""),
            )
        ]
    question_scored = sorted(
        [(skill_score(_question_text(row), skill), row) for row in questions],
        key=lambda item: item[0],
        reverse=True,
    )
    return {
        "skill": skill,
        "questions": [row for score, row in question_scored if score > 0][:limit],
        "mapping_strategy": "heuristic_fallback",
    }
