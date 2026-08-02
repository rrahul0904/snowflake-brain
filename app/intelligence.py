
from __future__ import annotations

import json
import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from .lab_challenges import labs as configured_labs
from .skill_brain import certifications, flatten_skills, matched_skills, skill_score


def _json_load(value: str | None, default: Any) -> Any:
    try:
        return json.loads(value or "")
    except Exception:
        return default


def _question_text(row: dict[str, Any]) -> str:
    options = _json_load(row.get("options_json"), [])
    return " ".join(
        [
            row.get("question") or "",
            " ".join(map(str, options)) if isinstance(options, list) else str(options),
            row.get("explanation") or "",
            row.get("tags") or "",
            row.get("test_title") or "",
            row.get("course_title") or "",
        ]
    )


def _safe_pct(numerator: int | float, denominator: int | float) -> int:
    if not denominator:
        return 0
    return round((numerator / denominator) * 100)


def _clamp(value: float, low: float = 0, high: float = 100) -> float:
    return max(low, min(high, value))


def fetch_question_rows(conn, track_id: str = "", limit: int = 8000) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in conn.execute(
            """
            SELECT q.id, q.course_id, q.course_title, q.test_id, q.test_title,
                   q.question, q.options_json, q.correct_json, q.explanation, q.tags,
                   q.difficulty, q.assessment_type,
                   COALESCE(c.track_id, pt.track_id, '') AS track_id,
                   COUNT(a.id) AS attempts,
                   SUM(CASE WHEN COALESCE(a.correct, 0) = 1 THEN 1 ELSE 0 END) AS correct_attempts,
                   SUM(CASE WHEN COALESCE(a.correct, 0) = 0 THEN 1 ELSE 0 END) AS missed_attempts,
                   MAX(a.attempted_at) AS last_attempted,
                   SUM(CASE WHEN a.mode LIKE '%exam%' AND COALESCE(a.correct, 0) = 1 THEN 1 ELSE 0 END) AS timed_correct,
                   SUM(CASE WHEN a.mode LIKE '%exam%' THEN 1 ELSE 0 END) AS timed_attempts
            FROM questions q
            LEFT JOIN question_attempts a ON a.question_id = q.id
            LEFT JOIN courses c ON c.id = q.course_id
            LEFT JOIN practice_tests pt ON pt.id = q.test_id
            WHERE (? = '' OR COALESCE(c.track_id, pt.track_id, '') = ? OR COALESCE(q.course_id, '') IN (SELECT id FROM courses WHERE track_id = ?))
            GROUP BY q.id
            LIMIT ?
            """,
            (track_id or "", track_id or "", track_id or "", limit),
        )
    ]


def fetch_lesson_rows(conn, track_id: str = "", limit: int = 5000) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in conn.execute(
            """
            SELECT l.id, l.course_id, l.course_title, l.section, l.title, l.excerpt,
                   substr(COALESCE(l.transcript_text, ''), 1, 2500) AS transcript_sample,
                   COALESCE(c.track_id, '') AS track_id,
                   COALESCE(lp.completed, 0) AS completed
            FROM lessons l
            LEFT JOIN courses c ON c.id = l.course_id
            LEFT JOIN lesson_progress lp ON lp.lesson_id = l.id
            WHERE (? = '' OR COALESCE(c.track_id, '') = ?)
            LIMIT ?
            """,
            (track_id or "", track_id or "", limit),
        )
    ]


def build_question_skill_map(conn, track_id: str = "") -> dict[str, Any]:
    rows = fetch_question_rows(conn, track_id)
    inserted = 0
    low_confidence = 0
    for row in rows:
        skill_matches = matched_skills(_question_text(row), row.get("track_id") or track_id, limit=3)
        if not skill_matches:
            low_confidence += 1
            continue
        best = skill_matches[0]
        confidence = float(best.get("confidence") or 0)
        if confidence < 0.55:
            low_confidence += 1
        conn.execute(
            """
            INSERT INTO question_skill_map(question_id, track_id, domain_id, skill_id, confidence, evidence_json)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(question_id, skill_id) DO UPDATE SET
              track_id = excluded.track_id,
              domain_id = excluded.domain_id,
              confidence = excluded.confidence,
              evidence_json = excluded.evidence_json,
              updated_at = datetime('now')
            """,
            (
                row["id"],
                best.get("certification") or row.get("track_id") or track_id or "",
                best.get("domain_id") or "",
                best.get("id") or "",
                confidence,
                json.dumps({"matches": skill_matches[:3], "source": "heuristic_v6"}),
            ),
        )
        inserted += 1
    return {"questions_scanned": len(rows), "mapped": inserted, "low_confidence": low_confidence}


def _lab_skill_activity(track_id: str) -> dict[str, dict[str, int]]:
    # Config-level availability. Runtime pass/fail comes from learning_events where metadata_json stores skill_id.
    activity: dict[str, dict[str, int]] = defaultdict(lambda: {"available_labs": 0, "passed_labs": 0, "attempted_labs": 0})
    for lab in configured_labs():
        if track_id and lab.get("certification") != track_id:
            continue
        skill_id = lab.get("skill_id") or lab.get("skill")
        if skill_id:
            activity[skill_id]["available_labs"] += 1
    return activity


def skill_mastery(conn, track_id: str = "snowpro-core") -> dict[str, Any]:
    skills = flatten_skills(track_id)
    questions = fetch_question_rows(conn, track_id)
    lessons = fetch_lesson_rows(conn, track_id)
    lab_activity = _lab_skill_activity(track_id)
    events = [
        dict(row)
        for row in conn.execute(
            """
            SELECT event_type, metadata_json, COUNT(*) AS count
            FROM learning_events
            WHERE (? = '' OR track_id = ? OR json_extract(metadata_json, '$.track_id') = ?)
            GROUP BY event_type, metadata_json
            """,
            (track_id or "", track_id or "", track_id or ""),
        )
    ]
    for event in events:
        meta = _json_load(event.get("metadata_json"), {})
        skill_id = meta.get("skill_id") or meta.get("skill")
        if not skill_id:
            continue
        bucket = lab_activity[skill_id]
        if event.get("event_type") == "lab_passed":
            bucket["passed_labs"] += int(event.get("count") or 0)
        if str(event.get("event_type") or "").startswith("lab_"):
            bucket["attempted_labs"] += int(event.get("count") or 0)

    output = []
    for skill in skills:
        skill_id = skill.get("id")
        q_matches = []
        lesson_matches = []
        for row in questions:
            score = skill_score(_question_text(row), skill)
            if score:
                q_matches.append((score, row))
        for row in lessons:
            text = " ".join([row.get("title") or "", row.get("section") or "", row.get("excerpt") or "", row.get("transcript_sample") or ""])
            score = skill_score(text, skill)
            if score:
                lesson_matches.append((score, row))
        attempts = sum(int(row.get("attempts") or 0) for _, row in q_matches)
        correct = sum(int(row.get("correct_attempts") or 0) for _, row in q_matches)
        misses = sum(int(row.get("missed_attempts") or 0) for _, row in q_matches)
        timed_attempts = sum(int(row.get("timed_attempts") or 0) for _, row in q_matches)
        timed_correct = sum(int(row.get("timed_correct") or 0) for _, row in q_matches)
        completed_lessons = sum(int(row.get("completed") or 0) for _, row in lesson_matches)
        accuracy = _safe_pct(correct, attempts)
        timed_accuracy = _safe_pct(timed_correct, timed_attempts)
        lab = lab_activity.get(skill_id, {"available_labs": 0, "passed_labs": 0, "attempted_labs": 0})
        level = 0
        evidence = []
        if lesson_matches:
            level = max(level, 1)
            evidence.append("content_available")
        if completed_lessons:
            level = max(level, 2)
            evidence.append("lesson_completed")
        if attempts >= 5:
            level = max(level, 3)
            evidence.append("practiced")
        if attempts >= 10 and accuracy >= 75:
            level = max(level, 4)
            evidence.append("accurate")
        if timed_attempts >= 5 and timed_accuracy >= 75:
            level = max(level, 5)
            evidence.append("timed_accurate")
        if lab.get("passed_labs", 0) > 0:
            level = max(level, 6)
            evidence.append("lab_proven")
        if attempts >= 20 and accuracy >= 82 and misses <= 3 and (lab.get("passed_labs", 0) or not lab.get("available_labs", 0)):
            level = max(level, 7)
            evidence.append("exam_ready")
        status = ["not_started", "exposed", "learned", "practiced", "accurate", "timed_accurate", "lab_proven", "exam_ready"][level]
        output.append(
            {
                "skill_id": skill_id,
                "skill": skill.get("title"),
                "domain_id": skill.get("domain_id"),
                "domain": skill.get("domain"),
                "objective": skill.get("objective"),
                "mastery_level": level,
                "mastery_status": status,
                "evidence": evidence,
                "question_count": len(q_matches),
                "lesson_count": len(lesson_matches),
                "completed_lessons": completed_lessons,
                "attempts": attempts,
                "correct_attempts": correct,
                "misses": misses,
                "accuracy_pct": accuracy,
                "timed_attempts": timed_attempts,
                "timed_accuracy_pct": timed_accuracy,
                "available_labs": lab.get("available_labs", 0),
                "passed_labs": lab.get("passed_labs", 0),
                "exam_traps": skill.get("exam_traps") or [],
                "aliases": skill.get("aliases") or [],
            }
        )
    domain_rows: dict[str, dict[str, Any]] = {}
    for row in output:
        domain_id = row.get("domain_id") or row.get("domain") or "other"
        item = domain_rows.setdefault(
            domain_id,
            {
                "domain_id": domain_id,
                "domain": row.get("domain"),
                "skills": 0,
                "avg_mastery": 0,
                "attempts": 0,
                "correct_attempts": 0,
                "accuracy_pct": 0,
                "blockers": 0,
            },
        )
        item["skills"] += 1
        item["avg_mastery"] += row["mastery_level"]
        item["attempts"] += row["attempts"]
        item["correct_attempts"] += row["correct_attempts"]
        if row["mastery_level"] < 4:
            item["blockers"] += 1
    for item in domain_rows.values():
        item["avg_mastery"] = round(item["avg_mastery"] / item["skills"], 1) if item["skills"] else 0
        item["accuracy_pct"] = _safe_pct(item["correct_attempts"], item["attempts"])
    return {"track_id": track_id, "skills": output, "domains": list(domain_rows.values())}


def readiness_model(conn, track_id: str = "snowpro-core", mastery: dict[str, Any] | None = None) -> dict[str, Any]:
    cert = next((cert for cert in certifications() if cert.get("id") == track_id), None)
    mastery = mastery or skill_mastery(conn, track_id)
    skills = mastery["skills"]
    if not skills:
        return {"track_id": track_id, "status": "insufficient_data", "pass_probability_range": [0, 10], "blockers": ["No skill map found"], "next_actions": []}
    avg_level = sum(row["mastery_level"] for row in skills) / len(skills)
    attempts = sum(row["attempts"] for row in skills)
    correct = sum(row["correct_attempts"] for row in skills)
    misses = sum(row["misses"] for row in skills)
    accuracy = _safe_pct(correct, attempts)
    lab_available = sum(row["available_labs"] for row in skills)
    lab_passed = sum(row["passed_labs"] for row in skills)
    low_skills = [row for row in skills if row["mastery_level"] < 4]
    repeated_miss = [row for row in skills if row["misses"] >= 5 and row["accuracy_pct"] < 70]
    full_mock_rows = [
        dict(row)
        for row in conn.execute(
            """
            SELECT COUNT(*) AS attempts, MAX(score) AS best_score
            FROM exam_sessions
            WHERE (? = '' OR track_id = ?) AND mode LIKE '%exam%' AND status = 'finished'
            """,
            (track_id or "", track_id or ""),
        )
    ]
    mock_attempts = int((full_mock_rows[0] or {}).get("attempts") or 0) if full_mock_rows else 0
    best_mock = int((full_mock_rows[0] or {}).get("best_score") or 0) if full_mock_rows else 0
    evidence_score = 0
    evidence_score += (avg_level / 7) * 35
    evidence_score += min(25, attempts / 4)  # 100 attempts -> 25 pts
    evidence_score += (accuracy / 100) * 20 if attempts else 0
    evidence_score += min(10, lab_passed * 2) if lab_available else 4
    evidence_score += min(10, mock_attempts * 5)
    if best_mock >= 80:
        evidence_score += 10
    if misses > 40:
        evidence_score -= 8
    if repeated_miss:
        evidence_score -= min(12, len(repeated_miss) * 2)
    score = int(_clamp(evidence_score))
    blockers = []
    if attempts < 100:
        blockers.append(f"Question evidence is thin: {attempts} attempts recorded; target at least 100 before trusting readiness.")
    if mock_attempts < 2:
        blockers.append("No evidence of two finished timed readiness/mock exams.")
    if best_mock and best_mock < 80:
        blockers.append(f"Best timed exam score is {best_mock}%; target 80%+.")
    if low_skills:
        blockers.append(f"{len(low_skills)} skills are below accurate mastery level.")
    if repeated_miss:
        blockers.append(f"{len(repeated_miss)} skills show repeated misses under 70% accuracy.")
    if lab_available and lab_passed < min(3, lab_available):
        blockers.append(f"Only {lab_passed}/{lab_available} available labs are proven.")
    if score >= 82 and not blockers:
        status = "exam_ready"
    elif score >= 70:
        status = "near_ready"
    elif score >= 45:
        status = "needs_repair"
    elif attempts or any(row["completed_lessons"] for row in skills):
        status = "learning"
    else:
        status = "not_started"
    weak = sorted(low_skills, key=lambda row: (row["mastery_level"], row["accuracy_pct"], -row["misses"]))[:5]
    next_actions = []
    for row in weak[:3]:
        action = "Practice"
        if row["attempts"] < 5:
            action = "Start drill"
        elif row["available_labs"] and not row["passed_labs"]:
            action = "Complete lab"
        elif row["misses"]:
            action = "Repair misses"
        next_actions.append({"action": action, "skill_id": row["skill_id"], "skill": row["skill"], "domain": row["domain"], "reason": f"Mastery {row['mastery_level']}/7 · {row['accuracy_pct']}% accuracy"})
    return {
        "track_id": track_id,
        "certification_title": (cert or {}).get("title", track_id),
        "status": status,
        "readiness_score": score,
        "pass_probability_range": [max(0, score - 8), min(99, score + 6)],
        "attempts": attempts,
        "accuracy_pct": accuracy,
        "misses": misses,
        "avg_mastery_level": round(avg_level, 1),
        "mock_exam_attempts": mock_attempts,
        "best_mock_score": best_mock,
        "lab_passed": lab_passed,
        "lab_available": lab_available,
        "blockers": blockers,
        "next_actions": next_actions,
        "domains": mastery["domains"],
        "weak_skills": weak,
    }


def mistake_queue(conn, track_id: str = "snowpro-core", limit: int = 20) -> dict[str, Any]:
    rows = fetch_question_rows(conn, track_id, limit=8000)
    missed = [row for row in rows if int(row.get("missed_attempts") or 0) > 0]
    items = []
    for row in missed:
        skills = matched_skills(_question_text(row), row.get("track_id") or track_id, limit=1)
        skill = skills[0] if skills else {}
        text = _question_text(row).lower()
        mistake_type = "concept_gap"
        if any(term in text for term in ["except", "not", "least", "most likely"]):
            mistake_type = "exam_trap"
        elif any(term in text for term in ["auto_suspend", "auto resume", "resume", "suspend", "warehouse"]):
            mistake_type = "feature_confusion"
        elif any(term in text for term in ["syntax", "sql", "create", "grant", "copy into", "flatten"]):
            mistake_type = "syntax_or_command_gap"
        elif int(row.get("timed_attempts") or 0) and int(row.get("missed_attempts") or 0) >= int(row.get("correct_attempts") or 0):
            mistake_type = "time_pressure_error"
        items.append(
            {
                "question_id": row["id"],
                "question": row.get("question"),
                "test_title": row.get("test_title"),
                "course_title": row.get("course_title"),
                "misses": int(row.get("missed_attempts") or 0),
                "attempts": int(row.get("attempts") or 0),
                "last_attempted": row.get("last_attempted"),
                "mistake_type": mistake_type,
                "skill_id": skill.get("id"),
                "skill": skill.get("title"),
                "domain": skill.get("domain"),
                "repair_action": repair_action_for_mistake(mistake_type, skill),
            }
        )
    items.sort(key=lambda row: (row["misses"], row["attempts"]), reverse=True)
    return {"track_id": track_id, "items": items[:limit], "total_unresolved": len(items)}


def repair_action_for_mistake(mistake_type: str, skill: dict[str, Any]) -> str:
    skill_name = skill.get("title") or "this skill"
    if mistake_type == "exam_trap":
        return f"Review the exam wording traps for {skill_name}, then retry 5 similar questions."
    if mistake_type == "feature_confusion":
        return f"Compare the similar Snowflake features in {skill_name}, then complete a targeted drill."
    if mistake_type == "syntax_or_command_gap":
        return f"Use a lab challenge to prove the syntax for {skill_name}, then retest."
    if mistake_type == "time_pressure_error":
        return f"Run a timed 10-question drill for {skill_name}."
    return f"Relearn the concept behind {skill_name}, then answer similar questions."


def diagnostic_plan(conn, track_id: str = "snowpro-core", count: int = 30) -> dict[str, Any]:
    count = max(10, min(100, int(count or 30)))
    mastery = skill_mastery(conn, track_id)
    questions = fetch_question_rows(conn, track_id, limit=8000)
    by_domain: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in questions:
        matches = matched_skills(_question_text(row), row.get("track_id") or track_id, limit=1)
        if not matches:
            continue
        domain = matches[0].get("domain") or "Other"
        item = dict(row)
        item["skill_id"] = matches[0].get("id")
        item["skill"] = matches[0].get("title")
        item["domain"] = domain
        by_domain[domain].append(item)
    domains = list(by_domain.keys())
    if not domains:
        return {"track_id": track_id, "question_ids": [], "domains": [], "message": "No mapped questions available for diagnostic."}
    selected: list[dict[str, Any]] = []
    per_domain = max(1, math.ceil(count / len(domains)))
    for domain in domains:
        pool = sorted(by_domain[domain], key=lambda row: (int(row.get("attempts") or 0), row.get("question") or ""))
        selected.extend(pool[:per_domain])
    selected = selected[:count]
    return {
        "track_id": track_id,
        "mode": "diagnostic",
        "target_count": count,
        "question_count": len(selected),
        "question_ids": [row["id"] for row in selected],
        "domains": [{"domain": domain, "available": len(rows)} for domain, rows in by_domain.items()],
        "questions": [
            {"id": row["id"], "question": row.get("question"), "domain": row.get("domain"), "skill": row.get("skill"), "test_title": row.get("test_title")}
            for row in selected
        ],
    }


def command_brief(conn, track_id: str = "snowpro-core", readiness: dict[str, Any] | None = None, mistakes: dict[str, Any] | None = None) -> dict[str, Any]:
    readiness = readiness or readiness_model(conn, track_id)
    mistakes = mistakes or mistake_queue(conn, track_id, limit=5)
    primary = readiness.get("next_actions", [])[:3]
    mission = []
    if readiness["status"] in {"not_started", "learning"} and readiness["attempts"] < 30:
        mission.append({"type": "diagnostic", "title": "Run baseline diagnostic", "detail": "Answer a balanced diagnostic set before trusting the plan.", "href": f"#/practice?track_id={track_id}&mode=diagnostic"})
    for action in primary:
        if action["action"] == "Complete lab":
            href = f"#/labs?certification={track_id}&skill_id={action['skill_id']}"
        else:
            href = f"#/practice?track_id={track_id}&skill_id={action['skill_id']}"
        mission.append({"type": "repair", "title": f"{action['action']}: {action['skill']}", "detail": action["reason"], "href": href})
    if mistakes["items"]:
        mission.append({"type": "mistake_review", "title": "Repair repeated misses", "detail": f"{mistakes['total_unresolved']} unresolved missed questions are waiting.", "href": f"#/intelligence?track_id={track_id}#mistakes"})
    if not mission:
        mission.append({"type": "readiness_exam", "title": "Take a timed readiness exam", "detail": "You have no urgent repair blockers. Validate under exam conditions.", "href": f"#/practice?track_id={track_id}&mode=readiness_exam"})
    return {"track_id": track_id, "readiness": readiness, "mistake_count": mistakes["total_unresolved"], "mission": mission[:5]}


def portfolio(conn) -> dict[str, Any]:
    rows = []
    for cert in certifications():
        track_id = cert.get("id")
        readiness = readiness_model(conn, track_id)
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
    recommended = sorted(rows, key=lambda row: (row["readiness_score"] or 0, -(row["blocker_count"] or 0)), reverse=True)
    return {"certifications": rows, "recommended_order": recommended}
