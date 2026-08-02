from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter

from ..database import connect
from ..skill_brain import certification, flatten_skills, infer_skill, load_skill_map, matched_skills, skill_score

router = APIRouter()


@router.get("/skills/map")
def skill_map() -> dict[str, Any]:
    return load_skill_map()


@router.get("/skills/summary")
def skill_summary(track_id: str = "snowpro-core") -> dict[str, Any]:
    cert = certification(track_id)
    skills = flatten_skills(track_id)
    with connect() as conn:
        question_rows = [
            dict(row)
            for row in conn.execute(
                """
                SELECT q.id, q.question, q.explanation, q.tags, q.test_title, q.course_title,
                       COALESCE(c.track_id, pt.track_id, '') AS track_id,
                       MAX(COALESCE(a.correct, 0)) AS ever_correct,
                       COUNT(a.id) AS attempts,
                       SUM(CASE WHEN COALESCE(a.correct, 0) = 1 THEN 1 ELSE 0 END) AS correct_attempts
                FROM questions q
                LEFT JOIN question_attempts a ON a.question_id = q.id
                LEFT JOIN courses c ON c.id = q.course_id
                LEFT JOIN practice_tests pt ON pt.id = q.test_id
                WHERE (? = '' OR COALESCE(c.track_id, pt.track_id, '') = ? OR COALESCE(q.course_id, '') IN (SELECT id FROM courses WHERE track_id = ?))
                GROUP BY q.id
                LIMIT 5000
                """,
                (track_id or "", track_id or "", track_id or ""),
            )
        ]
        lesson_rows = [
            dict(row)
            for row in conn.execute(
                """
                SELECT l.id, l.title, l.section, l.course_title, l.transcript_text, l.excerpt, c.track_id
                FROM lessons l
                LEFT JOIN courses c ON c.id = l.course_id
                WHERE (? = '' OR COALESCE(c.track_id, '') = ?)
                LIMIT 2500
                """,
                (track_id or "", track_id or ""),
            )
        ]
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

    output = []
    total_questions = len(question_rows)
    for skill in skills:
        q_matches = []
        lesson_matches = []
        for row in question_rows:
            text = " ".join([row.get("question") or "", row.get("explanation") or "", row.get("tags") or "", row.get("test_title") or ""])
            score = skill_score(text, skill)
            if score:
                q_matches.append((score, row))
        for row in lesson_rows:
            text = " ".join([row.get("title") or "", row.get("section") or "", row.get("excerpt") or "", (row.get("transcript_text") or "")[:1200]])
            score = skill_score(text, skill)
            if score:
                lesson_matches.append((score, row))
        attempts = sum(int(row.get("attempts") or 0) for _, row in q_matches)
        correct = sum(int(row.get("correct_attempts") or 0) for _, row in q_matches)
        accuracy = round((correct / attempts) * 100) if attempts else 0
        coverage_pct = round((len(q_matches) / total_questions) * 100) if total_questions else 0
        status = "not_started"
        if attempts:
            status = "strong" if accuracy >= 80 else "needs_review" if accuracy >= 60 else "weak"
        elif q_matches or lesson_matches:
            status = "available"
        output.append(
            {
                "skill_id": skill.get("id"),
                "skill": skill.get("title"),
                "domain_id": skill.get("domain_id"),
                "domain": skill.get("domain"),
                "objective": skill.get("objective"),
                "question_count": len(q_matches),
                "lesson_count": len(lesson_matches),
                "attempts": attempts,
                "correct_attempts": correct,
                "accuracy_pct": accuracy,
                "coverage_pct": coverage_pct,
                "status": status,
                "exam_traps": skill.get("exam_traps") or [],
            }
        )
    domain_summary: dict[str, dict[str, Any]] = {}
    for row in output:
        domain = row["domain"] or "Other"
        item = domain_summary.setdefault(domain, {"domain": domain, "skills": 0, "question_count": 0, "attempts": 0, "correct_attempts": 0, "accuracy_pct": 0})
        item["skills"] += 1
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


@router.get("/skills/{skill_id}/resources")
def skill_resources(skill_id: str, track_id: str = "snowpro-core", limit: int = 12) -> dict[str, Any]:
    skills = {skill["id"]: skill for skill in flatten_skills(track_id)}
    skill = skills.get(skill_id)
    if not skill:
        return {"skill": None, "lessons": [], "questions": []}
    terms = list(dict.fromkeys((skill.get("aliases") or []) + (skill.get("question_tags") or []) + [skill.get("title") or ""]))[:8]
    pattern = "%" + "%".join([term.split()[0] for term in terms[:2] if term]) + "%" if terms else "%"
    with connect() as conn:
        lessons = [
            dict(row)
            for row in conn.execute(
                """
                SELECT l.id, l.title, l.course_title, l.section, l.excerpt
                FROM lessons l
                LEFT JOIN courses c ON c.id = l.course_id
                WHERE (? = '' OR c.track_id = ?)
                LIMIT 500
                """,
                (track_id or "", track_id or ""),
            )
        ]
        questions = [
            dict(row)
            for row in conn.execute(
                """
                SELECT q.id, q.question, q.explanation, q.tags, q.test_title, q.course_title
                FROM questions q
                LEFT JOIN courses c ON c.id = q.course_id
                LEFT JOIN practice_tests pt ON pt.id = q.test_id
                WHERE (? = '' OR COALESCE(c.track_id, pt.track_id, '') = ? OR COALESCE(q.course_id, '') IN (SELECT id FROM courses WHERE track_id = ?))
                LIMIT 1000
                """,
                (track_id or "", track_id or "", track_id or ""),
            )
        ]
    lesson_scored = sorted(
        [(skill_score(" ".join([row.get("title") or "", row.get("section") or "", row.get("excerpt") or ""]), skill), row) for row in lessons],
        key=lambda item: item[0],
        reverse=True,
    )
    question_scored = sorted(
        [(skill_score(" ".join([row.get("question") or "", row.get("explanation") or "", row.get("tags") or ""]), skill), row) for row in questions],
        key=lambda item: item[0],
        reverse=True,
    )
    return {
        "skill": skill,
        "lessons": [row for score, row in lesson_scored if score > 0][:limit],
        "questions": [row for score, row in question_scored if score > 0][:limit],
    }
