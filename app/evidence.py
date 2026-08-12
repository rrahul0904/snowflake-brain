from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from .skill_brain import flatten_skills


def _pct(numerator: int | float, denominator: int | float) -> int:
    if not denominator:
        return 0
    return round((numerator / denominator) * 100)


def _json_load(value: str | None) -> dict[str, Any]:
    try:
        parsed = json.loads(value or "{}")
        return parsed if isinstance(parsed, dict) else {}
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def _skill_index(track_id: str) -> dict[str, dict[str, Any]]:
    return {str(skill.get("id")): skill for skill in flatten_skills(track_id) if skill.get("id")}


def _question_rows(conn, track_id: str) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in conn.execute(
            """
            SELECT
              q.id,
              q.question,
              q.course_id,
              q.course_title,
              q.test_id,
              COALESCE(c.track_id, pt.track_id, '') AS resolved_track_id,
              qsm.skill_id,
              qsm.domain_id,
              qsm.track_id AS mapping_track_id,
              qsm.confidence,
              qsm.reviewed,
              qsm.evidence_json
            FROM questions q
            LEFT JOIN courses c ON c.id = q.course_id
            LEFT JOIN practice_tests pt ON pt.id = q.test_id
            LEFT JOIN question_skill_map qsm ON qsm.question_id = q.id
            WHERE (? = '' OR COALESCE(c.track_id, pt.track_id, '') = ? OR COALESCE(qsm.track_id, '') = ?)
            ORDER BY q.id, COALESCE(qsm.confidence, 0) DESC
            """,
            (track_id or "", track_id or "", track_id or ""),
        )
    ]


def _lesson_rows(conn, track_id: str) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in conn.execute(
            """
            SELECT
              l.id,
              l.title,
              l.course_id,
              l.course_title,
              COALESCE(c.track_id, '') AS resolved_track_id,
              csm.skill_id,
              csm.domain_id,
              csm.track_id AS mapping_track_id,
              csm.confidence,
              csm.reviewed,
              csm.evidence_json
            FROM lessons l
            LEFT JOIN courses c ON c.id = l.course_id
            LEFT JOIN content_skill_map csm
              ON csm.content_type = 'lesson' AND csm.content_id = l.id
            WHERE (? = '' OR COALESCE(c.track_id, '') = ? OR COALESCE(csm.track_id, '') = ?)
            ORDER BY l.id, COALESCE(csm.confidence, 0) DESC
            """,
            (track_id or "", track_id or "", track_id or ""),
        )
    ]


def _group(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["id"])].append(row)
    return dict(grouped)


def _coverage_summary(grouped: dict[str, list[dict[str, Any]]], confidence_threshold: float) -> dict[str, int]:
    total = len(grouped)
    mapped = 0
    reviewed = 0
    high_confidence = 0
    low_confidence = 0
    ambiguous = 0

    for rows in grouped.values():
        mappings = [row for row in rows if row.get("skill_id")]
        if not mappings:
            continue
        mapped += 1
        if len(mappings) > 1:
            ambiguous += 1
        best_confidence = max(float(row.get("confidence") or 0) for row in mappings)
        if best_confidence >= confidence_threshold:
            high_confidence += 1
        else:
            low_confidence += 1
        if any(int(row.get("reviewed") or 0) == 1 for row in mappings):
            reviewed += 1

    return {
        "total": total,
        "mapped": mapped,
        "unmapped": total - mapped,
        "reviewed": reviewed,
        "unreviewed_mapped": mapped - reviewed,
        "high_confidence": high_confidence,
        "low_confidence": low_confidence,
        "ambiguous": ambiguous,
        "coverage_pct": _pct(mapped, total),
        "reviewed_pct": _pct(reviewed, mapped),
        "high_confidence_pct": _pct(high_confidence, mapped),
    }


def _review_queue(
    grouped: dict[str, list[dict[str, Any]]],
    confidence_threshold: float,
    limit: int,
    item_type: str,
) -> list[dict[str, Any]]:
    queue: list[dict[str, Any]] = []
    for item_id, rows in grouped.items():
        mappings = [row for row in rows if row.get("skill_id")]
        base = rows[0]
        if not mappings:
            queue.append(
                {
                    "item_type": item_type,
                    "item_id": item_id,
                    "title": base.get("question") or base.get("title") or item_id,
                    "track_id": base.get("resolved_track_id") or "",
                    "reason": "unmapped",
                    "priority": 0,
                    "mappings": [],
                }
            )
            continue

        mappings.sort(key=lambda row: float(row.get("confidence") or 0), reverse=True)
        best = mappings[0]
        reasons = []
        if not any(int(row.get("reviewed") or 0) == 1 for row in mappings):
            reasons.append("unreviewed")
        if float(best.get("confidence") or 0) < confidence_threshold:
            reasons.append("low_confidence")
        if len(mappings) > 1:
            reasons.append("ambiguous")
        if not reasons:
            continue

        priority = 1
        if "low_confidence" in reasons:
            priority = 0
        elif "ambiguous" in reasons:
            priority = 0
        queue.append(
            {
                "item_type": item_type,
                "item_id": item_id,
                "title": base.get("question") or base.get("title") or item_id,
                "track_id": base.get("resolved_track_id") or best.get("mapping_track_id") or "",
                "reason": ",".join(reasons),
                "priority": priority,
                "mappings": [
                    {
                        "skill_id": row.get("skill_id"),
                        "domain_id": row.get("domain_id"),
                        "confidence": round(float(row.get("confidence") or 0), 3),
                        "reviewed": bool(row.get("reviewed")),
                        "evidence": _json_load(row.get("evidence_json")),
                    }
                    for row in mappings
                ],
            }
        )

    queue.sort(key=lambda row: (row["priority"], row["reason"], row["item_id"]))
    for row in queue:
        row.pop("priority", None)
    return queue[:limit]


def evidence_audit(
    conn,
    track_id: str = "",
    confidence_threshold: float = 0.65,
    limit: int = 50,
) -> dict[str, Any]:
    confidence_threshold = max(0.0, min(1.0, float(confidence_threshold)))
    limit = max(1, min(250, int(limit)))

    question_grouped = _group(_question_rows(conn, track_id))
    lesson_grouped = _group(_lesson_rows(conn, track_id))
    questions = _coverage_summary(question_grouped, confidence_threshold)
    lessons = _coverage_summary(lesson_grouped, confidence_threshold)

    trust_score = round(
        questions["coverage_pct"] * 0.40
        + questions["reviewed_pct"] * 0.25
        + questions["high_confidence_pct"] * 0.20
        + lessons["coverage_pct"] * 0.15
    )
    trust_status = "strong" if trust_score >= 85 else "moderate" if trust_score >= 65 else "weak"

    blockers: list[str] = []
    if questions["coverage_pct"] < 90:
        blockers.append(f"Only {questions['coverage_pct']}% of scoped questions have a skill mapping.")
    if questions["reviewed_pct"] < 70:
        blockers.append(f"Only {questions['reviewed_pct']}% of mapped questions have been human-reviewed.")
    if questions["low_confidence"]:
        blockers.append(f"{questions['low_confidence']} question mappings are below the {confidence_threshold:.2f} confidence threshold.")
    if questions["ambiguous"]:
        blockers.append(f"{questions['ambiguous']} questions currently map to more than one skill.")
    if lessons["coverage_pct"] < 60:
        blockers.append(f"Only {lessons['coverage_pct']}% of scoped lessons have a persisted skill mapping.")

    return {
        "track_id": track_id,
        "confidence_threshold": confidence_threshold,
        "mapping_trust_score": trust_score,
        "mapping_trust_status": trust_status,
        "questions": questions,
        "lessons": lessons,
        "blockers": blockers,
        "question_review_queue": _review_queue(question_grouped, confidence_threshold, limit, "question"),
        "lesson_review_queue": _review_queue(lesson_grouped, confidence_threshold, limit, "lesson"),
    }


def _review_payload(evidence_json: str | None, decision: str, previous_skill_id: str, new_skill_id: str | None) -> str:
    payload = _json_load(evidence_json)
    payload["human_review"] = {
        "decision": decision,
        "previous_skill_id": previous_skill_id,
        "new_skill_id": new_skill_id,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }
    return json.dumps(payload)


def review_mapping(
    conn,
    *,
    mapping_type: str,
    item_id: str,
    skill_id: str,
    decision: str,
    track_id: str = "",
    content_type: str = "lesson",
    replacement_skill_id: str | None = None,
    confidence: float | None = None,
) -> dict[str, Any]:
    mapping_type = mapping_type.strip().lower()
    decision = decision.strip().lower()
    if mapping_type not in {"question", "content"}:
        raise ValueError("mapping_type must be 'question' or 'content'")
    if decision not in {"approve", "reject", "replace"}:
        raise ValueError("decision must be approve, reject, or replace")
    if decision == "replace" and not replacement_skill_id:
        raise ValueError("replacement_skill_id is required for replace")

    if mapping_type == "question":
        row = conn.execute(
            """
            SELECT qsm.*, COALESCE(c.track_id, pt.track_id, '') AS resolved_track_id
            FROM question_skill_map qsm
            JOIN questions q ON q.id = qsm.question_id
            LEFT JOIN courses c ON c.id = q.course_id
            LEFT JOIN practice_tests pt ON pt.id = q.test_id
            WHERE qsm.question_id = ? AND qsm.skill_id = ?
            """,
            (item_id, skill_id),
        ).fetchone()
        table = "question_skill_map"
        id_column = "question_id"
        conflict_columns = "question_id, skill_id"
    else:
        row = conn.execute(
            """
            SELECT csm.*, COALESCE(c.track_id, '') AS resolved_track_id
            FROM content_skill_map csm
            LEFT JOIN lessons l ON csm.content_type = 'lesson' AND l.id = csm.content_id
            LEFT JOIN courses c ON c.id = l.course_id
            WHERE csm.content_type = ? AND csm.content_id = ? AND csm.skill_id = ?
            """,
            (content_type, item_id, skill_id),
        ).fetchone()
        table = "content_skill_map"
        id_column = "content_id"
        conflict_columns = "content_type, content_id, skill_id"

    if not row:
        raise ValueError("mapping not found")
    current = dict(row)
    effective_track = track_id or current.get("track_id") or current.get("resolved_track_id") or ""
    skills = _skill_index(effective_track)
    if skill_id not in skills:
        raise ValueError(f"skill_id '{skill_id}' is not configured for track '{effective_track}'")

    reviewed_confidence = max(0.0, min(1.0, float(confidence if confidence is not None else max(float(current.get("confidence") or 0), 0.95))))

    if decision == "approve":
        evidence = _review_payload(current.get("evidence_json"), decision, skill_id, skill_id)
        if mapping_type == "question":
            conn.execute(
                """
                UPDATE question_skill_map
                SET reviewed = 1, confidence = ?, evidence_json = ?, updated_at = datetime('now')
                WHERE question_id = ? AND skill_id = ?
                """,
                (reviewed_confidence, evidence, item_id, skill_id),
            )
        else:
            conn.execute(
                """
                UPDATE content_skill_map
                SET reviewed = 1, confidence = ?, evidence_json = ?, updated_at = datetime('now')
                WHERE content_type = ? AND content_id = ? AND skill_id = ?
                """,
                (reviewed_confidence, evidence, content_type, item_id, skill_id),
            )
        return {
            "status": "approved",
            "mapping_type": mapping_type,
            "item_id": item_id,
            "skill_id": skill_id,
            "track_id": effective_track,
            "confidence": reviewed_confidence,
        }

    if decision == "reject":
        if mapping_type == "question":
            conn.execute("DELETE FROM question_skill_map WHERE question_id = ? AND skill_id = ?", (item_id, skill_id))
        else:
            conn.execute(
                "DELETE FROM content_skill_map WHERE content_type = ? AND content_id = ? AND skill_id = ?",
                (content_type, item_id, skill_id),
            )
        return {
            "status": "rejected",
            "mapping_type": mapping_type,
            "item_id": item_id,
            "skill_id": skill_id,
            "track_id": effective_track,
        }

    replacement = str(replacement_skill_id)
    if replacement not in skills:
        raise ValueError(f"replacement_skill_id '{replacement}' is not configured for track '{effective_track}'")
    replacement_skill = skills[replacement]
    evidence = _review_payload(current.get("evidence_json"), decision, skill_id, replacement)

    if mapping_type == "question":
        conn.execute("DELETE FROM question_skill_map WHERE question_id = ? AND skill_id = ?", (item_id, skill_id))
        conn.execute(
            f"""
            INSERT INTO {table}({id_column}, track_id, domain_id, skill_id, confidence, evidence_json, reviewed)
            VALUES (?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT({conflict_columns}) DO UPDATE SET
              track_id = excluded.track_id,
              domain_id = excluded.domain_id,
              confidence = excluded.confidence,
              evidence_json = excluded.evidence_json,
              reviewed = 1,
              updated_at = datetime('now')
            """,
            (
                item_id,
                effective_track,
                replacement_skill.get("domain_id") or "",
                replacement,
                reviewed_confidence,
                evidence,
            ),
        )
    else:
        conn.execute(
            "DELETE FROM content_skill_map WHERE content_type = ? AND content_id = ? AND skill_id = ?",
            (content_type, item_id, skill_id),
        )
        conn.execute(
            f"""
            INSERT INTO {table}(content_type, {id_column}, track_id, domain_id, skill_id, confidence, evidence_json, reviewed)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT({conflict_columns}) DO UPDATE SET
              track_id = excluded.track_id,
              domain_id = excluded.domain_id,
              confidence = excluded.confidence,
              evidence_json = excluded.evidence_json,
              reviewed = 1,
              updated_at = datetime('now')
            """,
            (
                content_type,
                item_id,
                effective_track,
                replacement_skill.get("domain_id") or "",
                replacement,
                reviewed_confidence,
                evidence,
            ),
        )

    return {
        "status": "replaced",
        "mapping_type": mapping_type,
        "item_id": item_id,
        "previous_skill_id": skill_id,
        "skill_id": replacement,
        "track_id": effective_track,
        "confidence": reviewed_confidence,
    }
