from __future__ import annotations

import json
import math
from collections import defaultdict
from typing import Any

from .certification_content import configured_skill_map
from .lab_challenges import labs as configured_labs
from .skill_brain import flatten_skills, matched_skills


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
        ]
    )


def _safe_pct(numerator: int | float, denominator: int | float) -> int:
    return round((numerator / denominator) * 100) if denominator else 0


def _clamp(value: float, low: float = 0, high: float = 100) -> float:
    return max(low, min(high, value))


def fetch_question_rows(conn: Any, track_id: str = "", limit: int = 8000, candidate_id: int | None = None) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in conn.execute(
            """
            SELECT
              q.id, q.track_id, q.test_id, q.test_title, q.question,
              q.options_json, q.correct_json, q.explanation, q.tags,
              q.difficulty, q.assessment_type, q.source_kind,
              COUNT(a.id) AS attempts,
              COALESCE(SUM(CASE WHEN a.correct = 1 THEN 1 ELSE 0 END), 0) AS correct_attempts,
              COALESCE(SUM(CASE WHEN a.correct = 0 THEN 1 ELSE 0 END), 0) AS missed_attempts,
              MAX(a.attempted_at) AS last_attempted,
              COALESCE(SUM(CASE WHEN (a.mode LIKE '%exam%' OR a.mode LIKE '%mock%') AND a.correct = 1 THEN 1 ELSE 0 END), 0) AS timed_correct,
              COALESCE(SUM(CASE WHEN a.mode LIKE '%exam%' OR a.mode LIKE '%mock%' THEN 1 ELSE 0 END), 0) AS timed_attempts
            FROM questions q
            LEFT JOIN question_attempts a ON a.question_id = q.id
              AND (? IS NULL OR a.candidate_id = ?)
            WHERE (? = '' OR q.track_id = ?)
              AND q.source_kind <> 'legacy'
            GROUP BY q.id
            LIMIT ?
            """,
            (candidate_id, candidate_id, track_id or "", track_id or "", limit),
        )
    ]


def build_question_skill_map(conn: Any, track_id: str = "") -> dict[str, Any]:
    """Refresh heuristic mappings without overwriting human-reviewed decisions."""
    rows = fetch_question_rows(conn, track_id)
    inserted = 0
    low_confidence = 0
    for row in rows:
        matches = matched_skills(_question_text(row), row.get("track_id") or track_id, limit=3)
        if not matches:
            low_confidence += 1
            continue
        best = matches[0]
        confidence = float(best.get("confidence") or 0)
        low_confidence += int(confidence < 0.55)
        conn.execute(
            """
            INSERT INTO question_skill_map(question_id, track_id, domain_id, skill_id, confidence, evidence_json, reviewed)
            VALUES (?, ?, ?, ?, ?, ?, 0)
            ON CONFLICT(question_id, skill_id) DO UPDATE SET
              track_id = excluded.track_id,
              domain_id = excluded.domain_id,
              confidence = excluded.confidence,
              evidence_json = excluded.evidence_json,
              updated_at = datetime('now')
            WHERE question_skill_map.reviewed = 0
            """,
            (
                row["id"],
                best.get("certification") or row.get("track_id") or track_id or "",
                best.get("domain_id") or "",
                best.get("id") or "",
                confidence,
                json.dumps({"matches": matches[:3], "source": "heuristic_v24"}),
            ),
        )
        inserted += 1
    return {"questions_scanned": len(rows), "mapped": inserted, "low_confidence": low_confidence}


def _mapping_resolution(
    conn: Any,
    track_id: str,
    questions: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, int]]:
    skills = {skill["id"]: skill for skill in flatten_skills(track_id)}
    edges = [
        dict(row)
        for row in conn.execute(
            """
            SELECT question_id, domain_id, skill_id, confidence, reviewed, evidence_json
            FROM question_skill_map
            WHERE track_id = ?
            ORDER BY question_id, reviewed DESC, confidence DESC, updated_at DESC
            """,
            (track_id,),
        )
    ]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge in edges:
        # Retired/old blueprint IDs are stale evidence, not valid mappings.
        if edge.get("skill_id") in skills:
            grouped[edge["question_id"]].append(edge)

    resolved: dict[str, dict[str, Any]] = {}
    stats: dict[str, int] = defaultdict(int)
    for row in questions:
        candidates = grouped.get(row["id"], [])
        reviewed = [edge for edge in candidates if int(edge.get("reviewed") or 0) == 1]
        strong = [edge for edge in candidates if float(edge.get("confidence") or 0) >= 0.70]
        edge = reviewed[0] if reviewed else strong[0] if strong else None
        if edge:
            provenance = "human_reviewed" if reviewed else "persisted_high_confidence"
            resolved[row["id"]] = {
                "skill_id": edge["skill_id"],
                "domain_id": edge.get("domain_id") or skills[edge["skill_id"]].get("domain_id"),
                "provenance": provenance,
                "confidence": float(edge.get("confidence") or 0),
            }
            stats[provenance] += 1
            continue
        matches = matched_skills(_question_text(row), row.get("track_id") or track_id, limit=1)
        if matches and matches[0].get("id") in skills:
            best = matches[0]
            resolved[row["id"]] = {
                "skill_id": best.get("id"),
                "domain_id": best.get("domain_id"),
                "provenance": "heuristic_fallback",
                "confidence": float(best.get("confidence") or 0),
            }
            stats["heuristic_fallback"] += 1
        else:
            stats["unmapped"] += 1
    return resolved, dict(stats)


def _lab_skill_activity(conn: Any, track_id: str, candidate_id: int | None = None) -> dict[str, dict[str, int]]:
    activity: dict[str, dict[str, int]] = defaultdict(
        lambda: {"available_labs": 0, "passed_labs": 0, "attempted_labs": 0}
    )
    for lab in configured_labs():
        if track_id and lab.get("certification") != track_id:
            continue
        skill_id = lab.get("skill_id") or lab.get("skill")
        if skill_id:
            activity[skill_id]["available_labs"] += 1

    for event in conn.execute(
        """
        SELECT event_type, skill_id, metadata_json, COUNT(*) AS count
        FROM learning_events
        WHERE (? = '' OR track_id = ?) AND (? IS NULL OR candidate_id = ?)
        GROUP BY event_type, skill_id, metadata_json
        """,
        (track_id or "", track_id or "", candidate_id, candidate_id),
    ):
        meta = _json_load(event["metadata_json"], {})
        skill_id = event["skill_id"] or meta.get("skill_id") or meta.get("skill")
        if not skill_id:
            continue
        if event["event_type"] == "lab_passed":
            activity[skill_id]["passed_labs"] += int(event["count"] or 0)
        if str(event["event_type"] or "").startswith("lab_"):
            activity[skill_id]["attempted_labs"] += int(event["count"] or 0)
    return activity


def skill_mastery(conn: Any, track_id: str = "snowpro-core", candidate_id: int | None = None) -> dict[str, Any]:
    skills = flatten_skills(track_id)
    questions = fetch_question_rows(conn, track_id, candidate_id=candidate_id)
    resolved, mapping_stats = _mapping_resolution(conn, track_id, questions)
    by_skill: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in questions:
        assignment = resolved.get(row["id"])
        if assignment:
            item = dict(row)
            item["mapping_provenance"] = assignment["provenance"]
            item["mapping_confidence"] = assignment["confidence"]
            by_skill[assignment["skill_id"]].append(item)

    completed = {
        row["skill_id"]
        for row in conn.execute(
            "SELECT skill_id FROM candidate_task_progress WHERE candidate_id = ? AND track_id = ? AND completed = 1",
            (candidate_id, track_id),
        )
    } if candidate_id is not None else set()
    lab_activity = _lab_skill_activity(conn, track_id, candidate_id)
    output = []
    for skill in skills:
        skill_id = skill.get("id")
        q_rows = by_skill.get(skill_id, [])
        attempts = sum(int(row.get("attempts") or 0) for row in q_rows)
        correct = sum(int(row.get("correct_attempts") or 0) for row in q_rows)
        misses = sum(int(row.get("missed_attempts") or 0) for row in q_rows)
        timed_attempts = sum(int(row.get("timed_attempts") or 0) for row in q_rows)
        timed_correct = sum(int(row.get("timed_correct") or 0) for row in q_rows)
        accuracy = _safe_pct(correct, attempts)
        timed_accuracy = _safe_pct(timed_correct, timed_attempts)
        task_completed = skill_id in completed
        lab = lab_activity.get(
            skill_id,
            {"available_labs": 0, "passed_labs": 0, "attempted_labs": 0},
        )

        level = 1
        evidence = ["written_task_available"]
        if task_completed:
            level = max(level, 2)
            evidence.append("task_completed")
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
        if attempts >= 20 and accuracy >= 82 and misses <= 3 and (
            lab.get("passed_labs", 0) or not lab.get("available_labs", 0)
        ):
            level = max(level, 7)
            evidence.append("exam_ready")

        provenance_counts: dict[str, int] = defaultdict(int)
        for row in q_rows:
            provenance_counts[row.get("mapping_provenance") or "unmapped"] += 1
        status = [
            "not_started",
            "exposed",
            "learned",
            "practiced",
            "accurate",
            "timed_accurate",
            "lab_proven",
            "exam_ready",
        ][level]
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
                "task_completed": task_completed,
                "question_count": len(q_rows),
                "mapped_question_count": len(q_rows),
                "attempts": attempts,
                "correct_attempts": correct,
                "misses": misses,
                "accuracy_pct": accuracy,
                "timed_attempts": timed_attempts,
                "timed_accuracy_pct": timed_accuracy,
                "available_labs": lab.get("available_labs", 0),
                "passed_labs": lab.get("passed_labs", 0),
                "mapping_provenance": dict(provenance_counts),
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

    mapped = len(resolved)
    reliable = int(mapping_stats.get("human_reviewed", 0)) + int(
        mapping_stats.get("persisted_high_confidence", 0)
    )
    heuristic = int(mapping_stats.get("heuristic_fallback", 0))
    mapping_trust = round(((reliable + heuristic * 0.5) / mapped) * 100) if mapped else 0
    return {
        "track_id": track_id,
        "skills": output,
        "domains": list(domain_rows.values()),
        "mapping_stats": mapping_stats,
        "mapping_trust_pct": mapping_trust,
        "mapped_questions": mapped,
        "total_questions": len(questions),
    }


def readiness_model(
    conn: Any,
    track_id: str = "snowpro-core",
    mastery: dict[str, Any] | None = None,
    candidate_id: int | None = None,
) -> dict[str, Any]:
    cert = next(
        (cert for cert in configured_skill_map().get("certifications") or [] if cert.get("id") == track_id),
        None,
    )
    mastery = mastery or skill_mastery(conn, track_id, candidate_id=candidate_id)
    skills = mastery.get("skills") or []
    if not skills:
        return {
            "track_id": track_id,
            "status": "insufficient_data",
            "readiness_score": 0,
            "readiness_confidence": 0,
            "readiness_confidence_status": "insufficient",
            "blockers": ["No task blueprint found"],
            "next_actions": [],
        }

    avg_level = sum(row["mastery_level"] for row in skills) / len(skills)
    attempts = sum(row["attempts"] for row in skills)
    correct = sum(row["correct_attempts"] for row in skills)
    misses = sum(row["misses"] for row in skills)
    accuracy = _safe_pct(correct, attempts)
    lab_available = sum(row["available_labs"] for row in skills)
    lab_passed = sum(row["passed_labs"] for row in skills)
    task_completed = sum(1 for row in skills if row.get("task_completed"))
    low_skills = [row for row in skills if row["mastery_level"] < 4]
    repeated_miss = [row for row in skills if row["misses"] >= 5 and row["accuracy_pct"] < 70]
    mock = dict(
        conn.execute(
            """
            SELECT COUNT(*) AS attempts,
                   MAX(CASE WHEN total_questions > 0 THEN ROUND(score * 100.0 / total_questions) ELSE 0 END) AS best_score
            FROM exam_sessions
            WHERE (? = '' OR track_id = ?) AND mode LIKE '%exam%' AND status = 'finished'
              AND (? IS NULL OR candidate_id = ?)
            """,
            (track_id or "", track_id or "", candidate_id, candidate_id),
        ).fetchone()
    )
    mock_attempts = int(mock.get("attempts") or 0)
    best_mock = int(mock.get("best_score") or 0)

    evidence_score = (avg_level / 7) * 35 + min(25, attempts / 4) + ((accuracy / 100) * 20 if attempts else 0)
    evidence_score += min(10, lab_passed * 2) if lab_available else 4
    evidence_score += min(10, mock_attempts * 5)
    if best_mock >= 80:
        evidence_score += 10
    if misses > 40:
        evidence_score -= 8
    if repeated_miss:
        evidence_score -= min(12, len(repeated_miss) * 2)
    score = int(_clamp(evidence_score))

    question_skill_coverage = _safe_pct(sum(1 for row in skills if row["attempts"] > 0), len(skills))
    mapping_trust = int(mastery.get("mapping_trust_pct") or 0)
    attempt_confidence = min(100, attempts)
    mock_confidence = min(100, mock_attempts * 50)
    task_confidence = _safe_pct(task_completed, len(skills))
    confidence = int(
        _clamp(
            mapping_trust * 0.35
            + attempt_confidence * 0.25
            + question_skill_coverage * 0.20
            + mock_confidence * 0.15
            + task_confidence * 0.05
        )
    )
    confidence_status = (
        "strong" if confidence >= 80 else "moderate" if confidence >= 55 else "weak" if confidence >= 30 else "insufficient"
    )

    blockers = []
    if attempts < 100:
        blockers.append(f"Question evidence is thin: {attempts} mapped attempts; target at least 100 before trusting readiness.")
    if mock_attempts < 2:
        blockers.append("Complete at least two timed mock exams.")
    if best_mock and best_mock < 80:
        blockers.append(f"Best timed mock score is {best_mock}%; target 80%+.")
    if low_skills:
        blockers.append(f"{len(low_skills)} tasks are below accurate mastery level.")
    if repeated_miss:
        blockers.append(f"{len(repeated_miss)} tasks show repeated misses under 70% accuracy.")
    if lab_available and lab_passed < min(3, lab_available):
        blockers.append(f"Only {lab_passed}/{lab_available} available labs are proven.")
    if mapping_trust < 65:
        blockers.append(f"Evidence mapping trust is only {mapping_trust}%; review or strengthen question mappings.")

    if score >= 82 and not blockers:
        status = "exam_ready"
    elif score >= 70:
        status = "near_ready"
    elif score >= 45:
        status = "needs_repair"
    elif attempts or task_completed:
        status = "learning"
    else:
        status = "not_started"

    weak = sorted(low_skills, key=lambda row: (row["mastery_level"], row["accuracy_pct"], -row["misses"]))[:5]
    next_actions = []
    for row in weak[:3]:
        action = (
            "Start drill"
            if row["attempts"] < 5
            else "Complete lab"
            if row["available_labs"] and not row["passed_labs"]
            else "Repair misses"
            if row["misses"]
            else "Practice"
        )
        next_actions.append(
            {
                "action": action,
                "skill_id": row["skill_id"],
                "skill": row["skill"],
                "domain": row["domain"],
                "reason": f"Mastery {row['mastery_level']}/7 · {row['accuracy_pct']}% accuracy",
            }
        )

    return {
        "track_id": track_id,
        "certification_title": (cert or {}).get("title", track_id),
        "status": status,
        "readiness_score": score,
        "readiness_confidence": confidence,
        "readiness_confidence_status": confidence_status,
        "confidence_reasons": [
            f"Question-to-task mapping trust: {mapping_trust}%",
            f"{attempts} mapped question attempts across {question_skill_coverage}% of tasks",
            f"{mock_attempts} persisted timed mock exams",
            f"{task_completed}/{len(skills)} written task lessons completed",
        ],
        "pass_probability_range": [max(0, score - 8), min(99, score + 6)],
        "attempts": attempts,
        "accuracy_pct": accuracy,
        "misses": misses,
        "avg_mastery_level": round(avg_level, 1),
        "mock_exam_attempts": mock_attempts,
        "best_mock_score": best_mock,
        "lab_passed": lab_passed,
        "lab_available": lab_available,
        "task_completed": task_completed,
        "mapping_trust_pct": mapping_trust,
        "blockers": blockers,
        "next_actions": next_actions,
        "domains": mastery["domains"],
        "weak_skills": weak,
    }


def _resolved_skill_for_row(
    resolved: dict[str, dict[str, Any]],
    row: dict[str, Any],
    skills: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    assignment = resolved.get(row["id"])
    return skills.get(assignment.get("skill_id")) if assignment else {}


def mistake_queue(conn: Any, track_id: str = "snowpro-core", limit: int = 20, candidate_id: int | None = None) -> dict[str, Any]:
    rows = fetch_question_rows(conn, track_id, limit=8000, candidate_id=candidate_id)
    resolved, _ = _mapping_resolution(conn, track_id, rows)
    skills = {skill["id"]: skill for skill in flatten_skills(track_id)}
    items = []
    for row in rows:
        if int(row.get("missed_attempts") or 0) <= 0:
            continue
        skill = _resolved_skill_for_row(resolved, row, skills)
        text = _question_text(row).lower()
        mistake_type = "concept_gap"
        if any(term in text for term in ["except", " not ", "least", "most likely"]):
            mistake_type = "exam_trap"
        elif any(term in text for term in ["auto_suspend", "auto resume", "warehouse", "cache"]):
            mistake_type = "feature_confusion"
        elif any(term in text for term in ["syntax", "create", "grant", "copy into", "flatten"]):
            mistake_type = "syntax_or_command_gap"
        elif int(row.get("timed_attempts") or 0) and int(row.get("missed_attempts") or 0) >= int(row.get("correct_attempts") or 0):
            mistake_type = "time_pressure_error"
        items.append(
            {
                "question_id": row["id"],
                "question": row.get("question"),
                "test_title": row.get("test_title"),
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
    skill_name = skill.get("title") or "this task"
    if mistake_type == "exam_trap":
        return f"Review the exam traps for {skill_name}, then retry a targeted drill."
    if mistake_type == "feature_confusion":
        return f"Compare the decision rules for {skill_name}, then drill the task."
    if mistake_type == "syntax_or_command_gap":
        return f"Complete the build exercise for {skill_name}, then retest."
    if mistake_type == "time_pressure_error":
        return f"Run a timed mock after repairing {skill_name}."
    return f"Relearn the written task for {skill_name}, then answer similar questions."


def diagnostic_plan(conn: Any, track_id: str = "snowpro-core", count: int = 30, candidate_id: int | None = None) -> dict[str, Any]:
    count = max(10, min(100, int(count or 30)))
    questions = fetch_question_rows(conn, track_id, limit=8000, candidate_id=candidate_id)
    resolved, _ = _mapping_resolution(conn, track_id, questions)
    skills = {skill["id"]: skill for skill in flatten_skills(track_id)}
    by_domain: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in questions:
        skill = _resolved_skill_for_row(resolved, row, skills)
        if not skill:
            continue
        domain = skill.get("domain") or "Other"
        item = dict(row)
        item["skill_id"] = skill.get("id")
        item["skill"] = skill.get("title")
        item["domain"] = domain
        by_domain[domain].append(item)
    domains = list(by_domain)
    if not domains:
        return {
            "track_id": track_id,
            "question_ids": [],
            "domains": [],
            "message": "No mapped questions available for diagnostic.",
        }
    selected = []
    per_domain = max(1, math.ceil(count / len(domains)))
    for domain in domains:
        pool = sorted(
            by_domain[domain],
            key=lambda row: (int(row.get("attempts") or 0), 0 if row.get("source_kind") == "source" else 1, row.get("question") or ""),
        )
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
            {
                "id": row["id"],
                "question": row.get("question"),
                "domain": row.get("domain"),
                "skill": row.get("skill"),
                "test_title": row.get("test_title"),
            }
            for row in selected
        ],
    }


def command_brief(
    conn: Any,
    track_id: str = "snowpro-core",
    readiness: dict[str, Any] | None = None,
    mistakes: dict[str, Any] | None = None,
    candidate_id: int | None = None,
) -> dict[str, Any]:
    readiness = readiness or readiness_model(conn, track_id, candidate_id=candidate_id)
    mistakes = mistakes or mistake_queue(conn, track_id, limit=5, candidate_id=candidate_id)
    mission = []
    if readiness["status"] in {"not_started", "learning"} and readiness["attempts"] < 30:
        mission.append(
            {
                "type": "diagnostic",
                "title": "Run baseline diagnostic",
                "detail": "Answer a balanced diagnostic before trusting the plan.",
                "href": f"#/diagnostic?track_id={track_id}",
            }
        )
    for action in readiness.get("next_actions", [])[:3]:
        href = (
            f"#/exercises?track_id={track_id}&skill_id={action['skill_id']}"
            if action["action"] == "Complete lab"
            else f"#/drill?track_id={track_id}&skill_id={action['skill_id']}"
        )
        mission.append(
            {
                "type": "repair",
                "title": f"{action['action']}: {action['skill']}",
                "detail": action["reason"],
                "href": href,
            }
        )
    if mistakes["items"]:
        mission.append(
            {
                "type": "mistake_review",
                "title": "Repair repeated misses",
                "detail": f"{mistakes['total_unresolved']} missed questions need repair.",
                "href": f"#/drill?track_id={track_id}",
            }
        )
    if not mission:
        mission.append(
            {
                "type": "readiness_exam",
                "title": "Take a timed mock exam",
                "detail": "No urgent repair blocker remains. Validate under exam conditions.",
                "href": f"#/mock?track_id={track_id}",
            }
        )
    return {
        "track_id": track_id,
        "readiness": readiness,
        "mistake_count": mistakes["total_unresolved"],
        "mission": mission[:5],
    }


def portfolio(conn: Any, candidate_id: int | None = None) -> dict[str, Any]:
    rows = []
    for cert in configured_skill_map().get("certifications") or []:
        readiness = readiness_model(conn, cert.get("id"), candidate_id=candidate_id)
        rows.append(
            {
                "track_id": cert.get("id"),
                "title": cert.get("title"),
                "exam_code": cert.get("exam_code"),
                "official": cert.get("official", False),
                "status": readiness.get("status"),
                "readiness_score": readiness.get("readiness_score"),
                "readiness_confidence": readiness.get("readiness_confidence"),
                "attempts": readiness.get("attempts"),
                "accuracy_pct": readiness.get("accuracy_pct"),
                "blockers": readiness.get("blockers", [])[:3],
            }
        )
    rows.sort(key=lambda row: row.get("readiness_score") or 0, reverse=True)
    return {"certifications": rows}
