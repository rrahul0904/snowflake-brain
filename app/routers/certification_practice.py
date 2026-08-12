from __future__ import annotations

import json
import random
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..certification_content import configured_skill_map
from ..database import connect
from ..serializers import question_public
from ..skill_brain import flatten_skills, skill_score

router = APIRouter()


class CertificationQuizStart(BaseModel):
    track_id: str = "snowpro-core"
    count: int = Field(15, ge=1, le=500)
    mode: str = "drill"
    skill_id: str | None = None
    domain_id: str | None = None
    difficulty: str | None = None
    unanswered_only: bool = False


class MockSummary(BaseModel):
    track_id: str = "snowpro-core"
    mode: str = "full-mock"
    score: int = Field(ge=0)
    total: int = Field(ge=1)
    elapsed_seconds: int = Field(default=0, ge=0)
    selection_strategy: str = "blueprint_weighted"


def _cert(track_id: str) -> dict[str, Any]:
    for cert in configured_skill_map().get("certifications") or []:
        if cert.get("id") == track_id:
            return cert
    raise HTTPException(status_code=404, detail="Certification track is not configured")


def _question_text(row: dict[str, Any]) -> str:
    return " ".join(
        [
            row.get("question") or "",
            row.get("explanation") or "",
            row.get("tags") or "",
            row.get("test_title") or "",
        ]
    )


def _question_pool(conn, track_id: str, difficulty: str | None, unanswered_only: bool) -> list[dict[str, Any]]:
    filters = ["COALESCE(c.track_id, pt.track_id, '') = ?"]
    params: list[Any] = [track_id]
    if difficulty:
        filters.append("q.difficulty = ?")
        params.append(difficulty)
    if unanswered_only:
        filters.append("NOT EXISTS (SELECT 1 FROM question_attempts qa0 WHERE qa0.question_id = q.id)")
    where = " AND ".join(filters)
    return [
        dict(row)
        for row in conn.execute(
            f"""
            SELECT q.*,
                   COUNT(qa.id) AS attempts,
                   COALESCE(SUM(CASE WHEN qa.correct = 1 THEN 1 ELSE 0 END), 0) AS correct_attempts,
                   COALESCE(SUM(CASE WHEN qa.correct = 0 THEN 1 ELSE 0 END), 0) AS missed_attempts,
                   MAX(qa.attempted_at) AS last_attempted
            FROM questions q
            LEFT JOIN courses c ON c.id = q.course_id
            LEFT JOIN practice_tests pt ON pt.id = q.test_id
            LEFT JOIN question_attempts qa ON qa.question_id = q.id
            WHERE {where}
            GROUP BY q.id
            LIMIT 10000
            """,
            params,
        )
    ]


def _best_reliable_edges(conn, track_id: str) -> dict[str, dict[str, Any]]:
    edges = [
        dict(row)
        for row in conn.execute(
            """
            SELECT question_id, track_id, domain_id, skill_id, confidence, reviewed
            FROM question_skill_map
            WHERE track_id = ? AND (reviewed = 1 OR confidence >= 0.70)
            ORDER BY question_id, reviewed DESC, confidence DESC, updated_at DESC
            """,
            (track_id,),
        )
    ]
    best: dict[str, dict[str, Any]] = {}
    for edge in edges:
        best.setdefault(edge["question_id"], edge)
    return best


def _assign_edges(rows: list[dict[str, Any]], track_id: str, persisted: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], int, int]:
    skills = {skill["id"]: skill for skill in flatten_skills(track_id)}
    mapped = 0
    heuristic = 0
    for row in rows:
        edge = persisted.get(row["id"])
        if edge and edge.get("skill_id") in skills:
            row["mapped_skill_id"] = edge.get("skill_id")
            row["mapped_domain_id"] = edge.get("domain_id") or skills[edge["skill_id"]].get("domain_id")
            row["mapping_provenance"] = "human_reviewed" if edge.get("reviewed") else "persisted_high_confidence"
            mapped += 1
            continue
        best_skill = None
        best_score = 0.0
        text = _question_text(row)
        for skill in skills.values():
            score = float(skill_score(text, skill) or 0)
            if score > best_score:
                best_score = score
                best_skill = skill
        if best_skill and best_score > 0:
            row["mapped_skill_id"] = best_skill.get("id")
            row["mapped_domain_id"] = best_skill.get("domain_id")
            row["mapping_provenance"] = "heuristic_fallback"
            heuristic += 1
        else:
            row["mapped_skill_id"] = None
            row["mapped_domain_id"] = None
            row["mapping_provenance"] = "unmapped"
    return rows, mapped, heuristic


def _rank_for_drill(row: dict[str, Any]) -> tuple[Any, ...]:
    attempts = int(row.get("attempts") or 0)
    correct = int(row.get("correct_attempts") or 0)
    misses = int(row.get("missed_attempts") or 0)
    accuracy = (correct / attempts) if attempts else 0
    # Unseen first, then repeatedly missed / low-accuracy questions, then older items.
    return (0 if attempts == 0 else 1, -misses, accuracy, attempts, row.get("last_attempted") or "")


def _take_unique(target: list[dict[str, Any]], source: list[dict[str, Any]], count: int, seen: set[str]) -> None:
    for row in source:
        if len(target) >= count:
            return
        if row["id"] in seen:
            continue
        target.append(row)
        seen.add(row["id"])


def _balanced_by_domain(rows: list[dict[str, Any]], domains: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("mapped_domain_id"):
            buckets[row["mapped_domain_id"]].append(row)
    for bucket in buckets.values():
        random.shuffle(bucket)
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    active = [domain for domain in domains if buckets.get(domain.get("id"))]
    if active:
        base = max(1, count // len(active))
        for domain in active:
            _take_unique(selected, buckets[domain["id"]], min(count, len(selected) + base), seen)
        # Round-robin residual gives every domain a chance before generic fill.
        while len(selected) < count:
            changed = False
            for domain in active:
                before = len(selected)
                _take_unique(selected, buckets[domain["id"]], len(selected) + 1, seen)
                changed = changed or len(selected) > before
                if len(selected) >= count:
                    break
            if not changed:
                break
    residual = list(rows)
    random.shuffle(residual)
    _take_unique(selected, residual, count, seen)
    return selected


def _weighted_by_domain(rows: list[dict[str, Any]], domains: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("mapped_domain_id"):
            buckets[row["mapped_domain_id"]].append(row)
    for bucket in buckets.values():
        random.shuffle(bucket)
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    allocations: list[tuple[dict[str, Any], int]] = []
    for domain in domains:
        weight = float(domain.get("weight") or 0)
        target = max(1, round(count * weight / 100)) if weight else 0
        allocations.append((domain, target))
    # Adjust allocation to approximately match requested count.
    allocations.sort(key=lambda item: float(item[0].get("weight") or 0), reverse=True)
    while sum(value for _, value in allocations) > count and allocations:
        for idx, (domain, value) in enumerate(allocations):
            if value > 1 and sum(v for _, v in allocations) > count:
                allocations[idx] = (domain, value - 1)
    while sum(value for _, value in allocations) < count and allocations:
        for idx, (domain, value) in enumerate(allocations):
            allocations[idx] = (domain, value + 1)
            if sum(v for _, v in allocations) >= count:
                break
    for domain, allocation in allocations:
        _take_unique(selected, buckets.get(domain.get("id"), []), min(count, len(selected) + allocation), seen)
    residual = list(rows)
    random.shuffle(residual)
    _take_unique(selected, residual, count, seen)
    return selected


def _adaptive_drill(rows: list[dict[str, Any]], count: int, skill_id: str | None, domain_id: str | None) -> list[dict[str, Any]]:
    target = rows
    if skill_id:
        targeted = [row for row in rows if row.get("mapped_skill_id") == skill_id]
        if targeted:
            target = targeted
    elif domain_id:
        targeted = [row for row in rows if row.get("mapped_domain_id") == domain_id]
        if targeted:
            target = targeted
    else:
        # Derive skill weakness from aggregate attempts/accuracy and select from weakest first.
        skill_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"attempts": 0, "correct": 0, "misses": 0})
        for row in rows:
            sid = row.get("mapped_skill_id")
            if not sid:
                continue
            skill_stats[sid]["attempts"] += int(row.get("attempts") or 0)
            skill_stats[sid]["correct"] += int(row.get("correct_attempts") or 0)
            skill_stats[sid]["misses"] += int(row.get("missed_attempts") or 0)
        weakness = sorted(
            skill_stats,
            key=lambda sid: (
                0 if skill_stats[sid]["attempts"] == 0 else 1,
                (skill_stats[sid]["correct"] / max(1, skill_stats[sid]["attempts"])),
                -skill_stats[sid]["misses"],
                skill_stats[sid]["attempts"],
            ),
        )
        rank = {sid: index for index, sid in enumerate(weakness)}
        target = sorted(rows, key=lambda row: (rank.get(row.get("mapped_skill_id"), 9999), *_rank_for_drill(row)))
    target = sorted(target, key=_rank_for_drill)
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    _take_unique(selected, target, count, seen)
    residual = sorted(rows, key=_rank_for_drill)
    _take_unique(selected, residual, count, seen)
    return selected


@router.post("/certification-quiz/start")
def certification_quiz_start(payload: CertificationQuizStart) -> dict[str, Any]:
    cert = _cert(payload.track_id)
    count = max(1, min(payload.count, 500))
    mode = (payload.mode or "drill").strip().lower()
    with connect() as conn:
        rows = _question_pool(conn, payload.track_id, payload.difficulty, payload.unanswered_only)
        persisted = _best_reliable_edges(conn, payload.track_id)
    rows, reliable_count, heuristic_count = _assign_edges(rows, payload.track_id, persisted)
    if not rows:
        return {"questions": [], "total": 0, "selection_strategy": mode, "domain_counts": {}, "mapped_count": 0, "heuristic_count": 0}

    if payload.skill_id:
        selected = _adaptive_drill(rows, count, payload.skill_id, payload.domain_id)
        strategy = "skill_targeted"
    elif payload.domain_id and mode not in {"diagnostic", "mock", "quick-mock", "full-mock"}:
        selected = _adaptive_drill(rows, count, None, payload.domain_id)
        strategy = "domain_targeted"
    elif mode == "diagnostic":
        selected = _balanced_by_domain(rows, cert.get("domains") or [], count)
        strategy = "domain_balanced"
    elif mode in {"mock", "quick-mock", "full-mock", "exam"}:
        selected = _weighted_by_domain(rows, cert.get("domains") or [], count)
        strategy = "blueprint_weighted"
    elif mode == "drill":
        selected = _adaptive_drill(rows, count, None, None)
        strategy = "adaptive_weakness"
    else:
        selected = list(rows)
        random.shuffle(selected)
        selected = selected[:count]
        strategy = "random"

    domain_counts: dict[str, int] = defaultdict(int)
    skill_ids: set[str] = set()
    provenance_counts: dict[str, int] = defaultdict(int)
    for row in selected:
        domain_counts[row.get("mapped_domain_id") or "unmapped"] += 1
        if row.get("mapped_skill_id"):
            skill_ids.add(row["mapped_skill_id"])
        provenance_counts[row.get("mapping_provenance") or "unmapped"] += 1

    questions = [question_public(row, include_answer=False) for row in selected]
    return {
        "questions": questions,
        "total": len(questions),
        "selection_strategy": strategy,
        "domain_counts": dict(domain_counts),
        "skill_ids": sorted(skill_ids),
        "mapping_provenance": dict(provenance_counts),
        "reliable_pool_count": reliable_count,
        "heuristic_pool_count": heuristic_count,
    }


@router.post("/certification-mock/record")
def record_certification_mock(payload: MockSummary) -> dict[str, Any]:
    _cert(payload.track_id)
    percent = round((payload.score / max(1, payload.total)) * 100)
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO exam_sessions(track_id, mode, started_at, finished_at, score, total_questions, status)
            VALUES (?, ?, datetime('now', ?), datetime('now'), ?, ?, 'finished')
            """,
            (
                payload.track_id,
                "exam_full_mock" if payload.mode in {"full-mock", "exam"} else "exam_quick_mock",
                f"-{max(0, int(payload.elapsed_seconds))} seconds",
                payload.score,
                payload.total,
            ),
        )
        session_id = int(cursor.lastrowid)
        conn.execute(
            """
            INSERT INTO learning_events(event_type, track_id, metadata_json)
            VALUES ('practice_test_finished', ?, ?)
            """,
            (
                payload.track_id,
                json.dumps({
                    "session_id": session_id,
                    "mode": payload.mode,
                    "score": payload.score,
                    "total": payload.total,
                    "score_pct": percent,
                    "elapsed_seconds": payload.elapsed_seconds,
                    "selection_strategy": payload.selection_strategy,
                }),
            ),
        )
    return {"ok": True, "session_id": session_id, "score_pct": percent}
