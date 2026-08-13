from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from .certification_content import study_lesson
from .skill_brain import flatten_skills


def _pct(numerator: int | float, denominator: int | float) -> int:
    return round((numerator / denominator) * 100) if denominator else 0


def _json_load(value: str | None) -> dict[str, Any]:
    try:
        parsed = json.loads(value or "{}")
        return parsed if isinstance(parsed, dict) else {}
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def _skill_index(track_id: str) -> dict[str, dict[str, Any]]:
    return {str(skill.get("id")): skill for skill in flatten_skills(track_id) if skill.get("id")}


def _question_rows(conn: Any, track_id: str) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in conn.execute(
            """
            SELECT
              q.id,
              q.question,
              q.track_id AS resolved_track_id,
              q.test_id,
              q.source_kind,
              qsm.skill_id,
              qsm.domain_id,
              qsm.track_id AS mapping_track_id,
              qsm.confidence,
              qsm.reviewed,
              qsm.evidence_json
            FROM questions q
            LEFT JOIN question_skill_map qsm ON qsm.question_id = q.id
            WHERE (? = '' OR q.track_id = ? OR COALESCE(qsm.track_id, '') = ?)
              AND q.source_kind <> 'legacy'
            ORDER BY q.id, COALESCE(qsm.reviewed, 0) DESC, COALESCE(qsm.confidence, 0) DESC
            """,
            (track_id or "", track_id or "", track_id or ""),
        )
    ]


def _group_valid(
    rows: list[dict[str, Any]],
    valid_skill_ids: set[str],
) -> tuple[dict[str, list[dict[str, Any]]], int]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    stale = 0
    for row in rows:
        item = dict(row)
        if item.get("skill_id") and item.get("skill_id") not in valid_skill_ids:
            stale += 1
            item["stale_skill_id"] = item.get("skill_id")
            item["skill_id"] = None
            item["domain_id"] = None
        grouped[str(item["id"])].append(item)
    return dict(grouped), stale


def _coverage_summary(
    grouped: dict[str, list[dict[str, Any]]],
    confidence_threshold: float,
) -> dict[str, int]:
    total = len(grouped)
    mapped = reviewed = high_confidence = low_confidence = ambiguous = 0
    for rows in grouped.values():
        mappings = [row for row in rows if row.get("skill_id")]
        if not mappings:
            continue
        mapped += 1
        if len({row.get("skill_id") for row in mappings}) > 1:
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
) -> list[dict[str, Any]]:
    queue: list[dict[str, Any]] = []
    for item_id, rows in grouped.items():
        mappings = [row for row in rows if row.get("skill_id")]
        base = rows[0]
        if not mappings:
            queue.append(
                {
                    "item_type": "question",
                    "item_id": item_id,
                    "title": base.get("question") or item_id,
                    "track_id": base.get("resolved_track_id") or "",
                    "reason": "unmapped",
                    "mappings": [],
                }
            )
            continue
        mappings.sort(
            key=lambda row: (int(row.get("reviewed") or 0), float(row.get("confidence") or 0)),
            reverse=True,
        )
        best = mappings[0]
        reasons = []
        if not any(int(row.get("reviewed") or 0) == 1 for row in mappings):
            reasons.append("unreviewed")
        if float(best.get("confidence") or 0) < confidence_threshold:
            reasons.append("low_confidence")
        if len({row.get("skill_id") for row in mappings}) > 1:
            reasons.append("ambiguous")
        if not reasons:
            continue
        queue.append(
            {
                "item_type": "question",
                "item_id": item_id,
                "title": base.get("question") or item_id,
                "track_id": base.get("resolved_track_id") or best.get("mapping_track_id") or "",
                "reason": ",".join(reasons),
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
    queue.sort(key=lambda row: ("low_confidence" not in row["reason"], "ambiguous" not in row["reason"], row["item_id"]))
    return queue[:limit]


def _written_content_summary(track_id: str) -> dict[str, int]:
    skills = flatten_skills(track_id)
    curated = 0
    usable = 0
    for skill in skills:
        lesson = study_lesson(track_id, skill["id"]) or {}
        if lesson:
            usable += 1
        if lesson.get("content_quality") == "curated":
            curated += 1
    total = len(skills)
    return {
        "total": total,
        "usable": usable,
        "curated": curated,
        "coverage_pct": _pct(usable, total),
        "curated_pct": _pct(curated, total),
    }


def evidence_audit(
    conn: Any,
    track_id: str = "",
    confidence_threshold: float = 0.65,
    limit: int = 50,
) -> dict[str, Any]:
    confidence_threshold = max(0.0, min(1.0, float(confidence_threshold)))
    limit = max(1, min(250, int(limit)))
    valid_skill_ids = set(_skill_index(track_id))
    question_grouped, stale_mappings = _group_valid(_question_rows(conn, track_id), valid_skill_ids)
    questions = _coverage_summary(question_grouped, confidence_threshold)
    written = _written_content_summary(track_id)

    trust_score = round(
        questions["coverage_pct"] * 0.45
        + questions["reviewed_pct"] * 0.25
        + questions["high_confidence_pct"] * 0.20
        + written["curated_pct"] * 0.10
    )
    trust_status = "strong" if trust_score >= 85 else "moderate" if trust_score >= 65 else "weak"
    blockers: list[str] = []
    if questions["coverage_pct"] < 90:
        blockers.append(f"Only {questions['coverage_pct']}% of scoped questions have a current-task mapping.")
    if questions["reviewed_pct"] < 70:
        blockers.append(f"Only {questions['reviewed_pct']}% of mapped questions have been human-reviewed.")
    if questions["low_confidence"]:
        blockers.append(f"{questions['low_confidence']} question mappings are below the {confidence_threshold:.2f} confidence threshold.")
    if questions["ambiguous"]:
        blockers.append(f"{questions['ambiguous']} questions currently map to more than one current task.")
    if stale_mappings:
        blockers.append(f"{stale_mappings} persisted mapping edges point to retired task IDs and are ignored by V24.")
    if written["coverage_pct"] < 100:
        blockers.append(f"Written lesson coverage is {written['coverage_pct']}%; every configured task should have a lesson.")

    return {
        "track_id": track_id,
        "confidence_threshold": confidence_threshold,
        "mapping_trust_score": trust_score,
        "mapping_trust_status": trust_status,
        "questions": questions,
        "written_lessons": written,
        "stale_mapping_edges": stale_mappings,
        "blockers": blockers,
        "question_review_queue": _review_queue(question_grouped, confidence_threshold, limit),
        "lesson_review_queue": [],
    }


def _review_payload(
    evidence_json: str | None,
    decision: str,
    previous_skill_id: str,
    new_skill_id: str | None,
) -> str:
    payload = _json_load(evidence_json)
    payload["human_review"] = {
        "decision": decision,
        "previous_skill_id": previous_skill_id,
        "new_skill_id": new_skill_id,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }
    return json.dumps(payload)


def review_mapping(
    conn: Any,
    *,
    mapping_type: str,
    item_id: str,
    skill_id: str,
    decision: str,
    track_id: str = "",
    content_type: str = "",
    replacement_skill_id: str | None = None,
    confidence: float | None = None,
) -> dict[str, Any]:
    del content_type
    if mapping_type.strip().lower() != "question":
        raise ValueError("V24 reviews question-to-task mappings only; written lessons come from the certification blueprint/content files")
    decision = decision.strip().lower()
    if decision not in {"approve", "reject", "replace"}:
        raise ValueError("decision must be approve, reject, or replace")
    if decision == "replace" and not replacement_skill_id:
        raise ValueError("replacement_skill_id is required for replace")

    row = conn.execute(
        """
        SELECT qsm.*, q.track_id AS resolved_track_id
        FROM question_skill_map qsm
        JOIN questions q ON q.id = qsm.question_id
        WHERE qsm.question_id = ? AND qsm.skill_id = ?
        """,
        (item_id, skill_id),
    ).fetchone()
    if not row:
        raise ValueError("mapping not found")
    current = dict(row)
    effective_track = track_id or current.get("track_id") or current.get("resolved_track_id") or ""
    skills = _skill_index(effective_track)
    if skill_id not in skills:
        raise ValueError(f"skill_id '{skill_id}' is not configured for track '{effective_track}'")

    reviewed_confidence = max(
        0.0,
        min(1.0, float(confidence if confidence is not None else max(float(current.get("confidence") or 0), 0.95))),
    )
    if decision == "approve":
        evidence = _review_payload(current.get("evidence_json"), decision, skill_id, skill_id)
        conn.execute(
            """
            UPDATE question_skill_map
            SET reviewed = 1, confidence = ?, evidence_json = ?, updated_at = datetime('now')
            WHERE question_id = ? AND skill_id = ?
            """,
            (reviewed_confidence, evidence, item_id, skill_id),
        )
        return {
            "status": "approved",
            "mapping_type": "question",
            "item_id": item_id,
            "skill_id": skill_id,
            "track_id": effective_track,
            "confidence": reviewed_confidence,
        }

    if decision == "reject":
        conn.execute(
            "DELETE FROM question_skill_map WHERE question_id = ? AND skill_id = ?",
            (item_id, skill_id),
        )
        return {
            "status": "rejected",
            "mapping_type": "question",
            "item_id": item_id,
            "skill_id": skill_id,
            "track_id": effective_track,
        }

    replacement = str(replacement_skill_id)
    if replacement not in skills:
        raise ValueError(f"replacement_skill_id '{replacement}' is not configured for track '{effective_track}'")
    replacement_skill = skills[replacement]
    evidence = _review_payload(current.get("evidence_json"), decision, skill_id, replacement)
    conn.execute(
        "DELETE FROM question_skill_map WHERE question_id = ? AND skill_id = ?",
        (item_id, skill_id),
    )
    conn.execute(
        """
        INSERT INTO question_skill_map(question_id, track_id, domain_id, skill_id, confidence, evidence_json, reviewed)
        VALUES (?, ?, ?, ?, ?, ?, 1)
        ON CONFLICT(question_id, skill_id) DO UPDATE SET
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
    return {
        "status": "replaced",
        "mapping_type": "question",
        "item_id": item_id,
        "skill_id": replacement,
        "track_id": effective_track,
        "confidence": reviewed_confidence,
    }
