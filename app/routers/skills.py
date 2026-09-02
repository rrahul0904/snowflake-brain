from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth import require_candidate
from ..certification_content import certification_catalog, configured_skill_map, content_coverage, study_lesson
from ..database import connect
from ..skill_brain import certification, flatten_skills, skill_score

router = APIRouter()


class TaskProgressUpdate(BaseModel):
    track_id: str = "snowpro-core"
    skill_id: str
    completed: bool = True


def _question_text(row: dict[str, Any]) -> str:
    return " ".join(
        [
            row.get("question") or "",
            row.get("explanation") or "",
            row.get("tags") or "",
            row.get("test_title") or "",
        ]
    )


@router.get("/skills/map")
def skill_map(candidate: dict = Depends(require_candidate)) -> dict[str, Any]:
    del candidate
    return configured_skill_map()


@router.get("/skills/catalog")
def skill_catalog(candidate: dict = Depends(require_candidate)) -> dict[str, Any]:
    del candidate
    return certification_catalog()


@router.get("/skills/content-coverage")
def skill_content_coverage(candidate: dict = Depends(require_candidate)) -> dict[str, Any]:
    del candidate
    return content_coverage()


@router.get("/skills/task-progress")
def task_progress(track_id: str = "snowpro-core", candidate: dict = Depends(require_candidate)) -> dict[str, Any]:
    configured = {skill["id"]: skill for skill in flatten_skills(track_id)}
    with connect() as conn:
        rows = [
            dict(row)
            for row in conn.execute(
                """
                SELECT track_id, skill_id, completed, completed_at, updated_at
                FROM candidate_task_progress
                WHERE candidate_id = ? AND track_id = ?
                ORDER BY skill_id
                """,
                (candidate["id"], track_id),
            )
        ]
    completed_ids = {row["skill_id"] for row in rows if int(row.get("completed") or 0) == 1}
    current_ids = set(configured)
    return {
        "track_id": track_id,
        "total_tasks": len(configured),
        "completed_tasks": len(completed_ids & current_ids),
        "completed_skill_ids": sorted(completed_ids & current_ids),
        "items": [row for row in rows if row.get("skill_id") in current_ids],
    }


@router.post("/skills/task-progress")
def update_task_progress(payload: TaskProgressUpdate, candidate: dict = Depends(require_candidate)) -> dict[str, Any]:
    configured = {skill["id"]: skill for skill in flatten_skills(payload.track_id)}
    if payload.skill_id not in configured:
        raise HTTPException(status_code=404, detail="Task is not configured for this certification")
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO candidate_task_progress(candidate_id, track_id, skill_id, completed, completed_at, updated_at)
            VALUES (?, ?, ?, ?, CASE WHEN ? = 1 THEN datetime('now') ELSE NULL END, datetime('now'))
            ON CONFLICT(candidate_id, track_id, skill_id) DO UPDATE SET
              completed = excluded.completed,
              completed_at = CASE WHEN excluded.completed = 1 THEN datetime('now') ELSE NULL END,
              updated_at = datetime('now')
            """,
            (candidate["id"], payload.track_id, payload.skill_id, int(payload.completed), int(payload.completed)),
        )
    return {"track_id": payload.track_id, "skill_id": payload.skill_id, "completed": payload.completed}


@router.get("/skills/summary")
def skill_summary(track_id: str = "snowpro-core", candidate: dict = Depends(require_candidate)) -> dict[str, Any]:
    cert = certification(track_id)
    cert = next(
        (item for item in configured_skill_map().get("certifications", []) if item.get("id") == track_id),
        cert,
    )
    skills = flatten_skills(track_id)
    valid_ids = {skill["id"] for skill in skills}
    with connect() as conn:
        question_rows = [
            dict(row)
            for row in conn.execute(
                """
                SELECT q.id, q.question, q.explanation, q.tags, q.test_title, q.source_kind,
                       COUNT(a.id) AS attempts,
                       COALESCE(SUM(CASE WHEN a.correct = 1 THEN 1 ELSE 0 END), 0) AS correct_attempts
                FROM questions q
                LEFT JOIN question_attempts a ON a.question_id = q.id AND a.candidate_id = ?
                WHERE q.track_id = ? AND q.source_kind <> 'legacy'
                GROUP BY q.id
                LIMIT 8000
                """,
                (candidate["id"], track_id),
            )
        ]
        reliable_edges = [
            dict(row)
            for row in conn.execute(
                """
                SELECT question_id, skill_id, domain_id, confidence, reviewed
                FROM question_skill_map
                WHERE track_id = ? AND (reviewed = 1 OR confidence >= 0.70)
                ORDER BY question_id, reviewed DESC, confidence DESC, updated_at DESC
                """,
                (track_id,),
            )
            if row["skill_id"] in valid_ids
        ]
        completed = {
            row["skill_id"]
            for row in conn.execute(
                "SELECT skill_id FROM candidate_task_progress WHERE candidate_id = ? AND track_id = ? AND completed = 1",
                (candidate["id"], track_id),
            )
            if row["skill_id"] in valid_ids
        }
        lab_events = [
            dict(row)
            for row in conn.execute(
                """
                SELECT skill_id, COUNT(*) AS attempts,
                       SUM(CASE WHEN event_type = 'lab_passed' THEN 1 ELSE 0 END) AS passed
                FROM learning_events
                WHERE candidate_id = ? AND track_id = ? AND skill_id IS NOT NULL
                GROUP BY skill_id
                """,
                (candidate["id"], track_id),
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
                "task_code": skill.get("task_code"),
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
        key = row.get("domain_id") or row.get("domain") or "other"
        item = domain_summary.setdefault(
            key,
            {
                "domain": row.get("domain") or "Other",
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
def skill_lesson(
    skill_id: str,
    track_id: str = "snowpro-core",
    candidate: dict = Depends(require_candidate),
) -> dict[str, Any]:
    del candidate
    lesson = study_lesson(track_id, skill_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Written task lesson is not configured for this certification")
    return lesson


@router.get("/skills/{skill_id}/resources")
def skill_resources(
    skill_id: str,
    track_id: str = "snowpro-core",
    candidate: dict = Depends(require_candidate),
) -> dict[str, Any]:
    """Return only non-question resource metadata.

    This route previously returned arbitrary mapped question rows including
    ``correct_json`` and ``explanation`` to any authenticated candidate. That
    bypassed quota, served-history, active-release, and pre-submit answer-hiding
    controls. Candidate question delivery is intentionally singular now:
    practice/mock endpoints allocate questions and ``/api/questions/{id}``
    requires a candidate-served relationship.
    """
    del candidate
    skills = {skill["id"]: skill for skill in flatten_skills(track_id)}
    skill = skills.get(skill_id)
    if not skill:
        return {"skill": None, "questions": [], "mapping_strategy": "none"}
    return {
        "skill": skill,
        "questions": [],
        "mapping_strategy": "candidate_delivery_only",
    }
