from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..auth import require_candidate
from ..certification_content import study_lesson
from ..database import connect
from ..question_bank import candidate_was_served_question
from ..serializers import json_list
from .feedback import ensure_feedback_schema

router = APIRouter()


class QuestionReportRequest(BaseModel):
    reason: Literal["incorrect_answer", "ambiguous", "outdated", "typo", "other"]
    description: str = Field(default="", max_length=4000)


def _served(candidate_id: int, question_id: str) -> None:
    if not candidate_was_served_question(candidate_id, question_id):
        raise HTTPException(status_code=404, detail="Question not found")


@router.get("/question-explorer/history")
def question_explorer_history(
    track_id: str = "snowpro-core",
    domain_id: str = "",
    skill_id: str = "",
    difficulty: str = "",
    bookmarked_only: bool = False,
    unanswered_only: bool = False,
    limit: int = Query(default=40, ge=1, le=100),
    candidate: dict[str, Any] = Depends(require_candidate),
) -> dict[str, Any]:
    where = ["q.track_id = ?"]
    params: list[Any] = [candidate["id"], track_id]
    if difficulty:
        where.append("LOWER(COALESCE(q.difficulty,'')) = LOWER(?)")
        params.append(difficulty)
    if domain_id:
        where.append(
            "EXISTS (SELECT 1 FROM question_skill_map qsm WHERE qsm.question_id=q.id AND qsm.track_id=q.track_id AND qsm.domain_id=?)"
        )
        params.append(domain_id)
    if skill_id:
        where.append(
            "EXISTS (SELECT 1 FROM question_skill_map qsm WHERE qsm.question_id=q.id AND qsm.track_id=q.track_id AND qsm.skill_id=?)"
        )
        params.append(skill_id)
    if bookmarked_only:
        where.append(
            "EXISTS (SELECT 1 FROM candidate_bookmarks b WHERE b.candidate_id=? AND b.question_id=q.id)"
        )
        params.append(candidate["id"])
    if unanswered_only:
        where.append(
            "NOT EXISTS (SELECT 1 FROM question_attempts a WHERE a.candidate_id=? AND a.question_id=q.id)"
        )
        params.append(candidate["id"])
    params.append(limit)

    sql = f"""
        WITH seen AS (
            SELECT question_id, MAX(served_at) AS last_served_at, COUNT(*) AS served_count
            FROM candidate_question_history
            WHERE candidate_id=?
            GROUP BY question_id
        )
        SELECT q.id, q.question, q.options_json, q.multiple, q.difficulty, q.assessment_type,
               seen.last_served_at, seen.served_count,
               CASE WHEN EXISTS (
                   SELECT 1 FROM candidate_bookmarks b
                   WHERE b.candidate_id={int(candidate["id"])} AND b.question_id=q.id
               ) THEN 1 ELSE 0 END AS bookmarked,
               (SELECT COUNT(*) FROM question_attempts a
                 WHERE a.candidate_id={int(candidate["id"])} AND a.question_id=q.id) AS attempt_count,
               (SELECT qsm.domain_id FROM question_skill_map qsm
                 WHERE qsm.question_id=q.id AND qsm.track_id=q.track_id
                 ORDER BY qsm.reviewed DESC, qsm.confidence DESC LIMIT 1) AS domain_id,
               (SELECT qsm.skill_id FROM question_skill_map qsm
                 WHERE qsm.question_id=q.id AND qsm.track_id=q.track_id
                 ORDER BY qsm.reviewed DESC, qsm.confidence DESC LIMIT 1) AS skill_id
        FROM seen
        JOIN questions q ON q.id=seen.question_id
        WHERE {" AND ".join(where)}
        ORDER BY datetime(seen.last_served_at) DESC, q.id
        LIMIT ?
    """
    with connect() as conn:
        rows = [dict(row) for row in conn.execute(sql, params).fetchall()]

    items = []
    for row in rows:
        items.append(
            {
                "id": row["id"],
                "question": row.get("question") or "",
                "options": json_list(row.get("options_json")),
                "multiple": bool(row.get("multiple")),
                "difficulty": row.get("difficulty") or "medium",
                "domain_id": row.get("domain_id") or "",
                "skill_id": row.get("skill_id") or "",
                "bookmarked": bool(row.get("bookmarked")),
                "attempt_count": int(row.get("attempt_count") or 0),
                "served_count": int(row.get("served_count") or 0),
                "last_served_at": row.get("last_served_at"),
            }
        )
    return {
        "track_id": track_id,
        "items": items,
        "returned": len(items),
        "privacy_boundary": "previously_served_questions_only",
    }


@router.get("/question-explorer/{question_id}/coach")
def question_explorer_coach(
    question_id: str,
    track_id: str = "snowpro-core",
    candidate: dict[str, Any] = Depends(require_candidate),
) -> dict[str, Any]:
    _served(candidate["id"], question_id)
    with connect() as conn:
        edge = conn.execute(
            """
            SELECT skill_id, domain_id
            FROM question_skill_map
            WHERE question_id=? AND track_id=?
            ORDER BY reviewed DESC, confidence DESC
            LIMIT 1
            """,
            (question_id, track_id),
        ).fetchone()
    if not edge:
        return {
            "question_id": question_id,
            "track_id": track_id,
            "mode": "socratic",
            "concept": "Identify the exact Snowflake requirement before comparing options.",
            "prompt": "Which words in the scenario tell you whether the problem is about architecture, governance, ingestion, performance, or collaboration?",
            "decision_rule": "",
            "trap": "Do not pick an option just because it names a familiar Snowflake feature.",
            "answer_revealed": False,
        }

    skill_id = str(edge["skill_id"])
    lesson = study_lesson(track_id, skill_id) or {}
    content = lesson.get("content") or {}
    rules = content.get("decision_rules") or []
    traps = content.get("trap_explanations") or []
    anti = content.get("anti_patterns") or []
    rule = rules[0] if rules else {}
    trap = traps[0] if traps else {}
    return {
        "question_id": question_id,
        "track_id": track_id,
        "skill_id": skill_id,
        "domain_id": str(edge["domain_id"] or ""),
        "mode": "socratic",
        "concept": content.get("key_concept") or content.get("summary") or "Match the requirement to the Snowflake feature that owns it.",
        "prompt": f"Before choosing an option, state the requirement in one sentence and map it to task {skill_id}.",
        "decision_rule": rule.get("when") and f"When {rule.get('when')}, think about {rule.get('choose')} because {rule.get('why') or 'it matches the stated requirement.'}" or "",
        "trap": trap.get("trap") or (anti[0] if anti else "Avoid solving a neighboring problem instead of the one the scenario actually describes."),
        "next_action": f"#/skill?track_id={track_id}&skill_id={skill_id}",
        "answer_revealed": False,
    }


@router.post("/question-explorer/{question_id}/report")
def report_question_issue(
    question_id: str,
    payload: QuestionReportRequest,
    candidate: dict[str, Any] = Depends(require_candidate),
) -> dict[str, Any]:
    _served(candidate["id"], question_id)
    ensure_feedback_schema()
    description = payload.description.strip()
    body = f"question_id={question_id}\nreason={payload.reason}"
    if description:
        body += f"\n\n{description}"
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO feedback_submissions(
                title, category, description, contact, route, track_id, candidate_id
            ) VALUES (?, 'content', ?, '', ?, ?, ?)
            """,
            (
                f"Question review: {payload.reason.replace('_', ' ')}",
                body,
                f"#/question-explorer?track_id={track_id}",
                track_id,
                candidate["id"],
            ),
        )
    return {"ok": True, "feedback_id": int(cursor.lastrowid), "question_id": question_id}
