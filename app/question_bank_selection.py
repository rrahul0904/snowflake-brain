from __future__ import annotations

from collections import defaultdict
from typing import Any

from fastapi import HTTPException

from .database import connect
from .question_bank import (
    filter_rows_for_entitlement,
    question_exposure_rank,
    record_questions_served,
    select_blueprint_questions,
)
from .routers.certification_practice import (
    CertificationQuizStart,
    _adaptive_drill,
    _assign_edges,
    _best_reliable_edges,
    _cert,
    _question_pool,
)
from .serializers import question_public
from .entitlements import reserve_daily_questions


TIMED_MOCK_MODES = {
    "weekly-mock",
    "quick-mock",
    "full-mock",
    "lifetime-practice",
    "source-exam",
    "mock",
    "exam",
}


def _enrich_rows(rows: list[dict[str, Any]], candidate_id: int) -> list[dict[str, Any]]:
    if not rows:
        return rows
    ids = [row["id"] for row in rows]
    placeholders = ",".join("?" for _ in ids)
    with connect() as conn:
        metadata = {
            row["question_id"]: dict(row)
            for row in conn.execute(
                f"""
                SELECT question_id, domain_id, task_id, task_code, question_type, cognitive_level,
                       difficulty_band, bank_pool, authoring_status, authoring_version
                FROM question_bank_metadata
                WHERE question_id IN ({placeholders})
                """,
                ids,
            )
        }
        exposure = {
            row["question_id"]: dict(row)
            for row in conn.execute(
                f"""
                SELECT question_id, served_count AS global_served_count, last_served_at AS global_last_served
                FROM question_exposure_stats
                WHERE question_id IN ({placeholders})
                """,
                ids,
            )
        }
        history = {
            row["question_id"]: dict(row)
            for row in conn.execute(
                f"""
                SELECT question_id, COUNT(*) AS candidate_served_count, MAX(served_at) AS candidate_last_served
                FROM candidate_question_history
                WHERE candidate_id=? AND question_id IN ({placeholders})
                GROUP BY question_id
                """,
                [candidate_id, *ids],
            )
        }
    for row in rows:
        row.update(metadata.get(row["id"], {}))
        row.update(exposure.get(row["id"], {}))
        row.update(history.get(row["id"], {}))
        row.setdefault("candidate_served_count", 0)
        row.setdefault("global_served_count", 0)
    return rows


def _safe_fallback_rows(rows: list[dict[str, Any]], *, pinned_internal_test: bool) -> list[dict[str, Any]]:
    if pinned_internal_test:
        return rows
    return [
        row
        for row in rows
        if row.get("bank_pool") or str(row.get("source_kind") or "") in {"canonical", "curated"}
    ]


def _select_targeted(rows: list[dict[str, Any]], count: int, mode: str, skill_id: str | None, domain_id: str | None) -> list[dict[str, Any]]:
    target = rows
    if skill_id:
        scoped = [row for row in rows if row.get("mapped_skill_id") == skill_id]
        if scoped:
            target = scoped
    elif domain_id:
        scoped = [row for row in rows if row.get("mapped_domain_id") == domain_id]
        if scoped:
            target = scoped
    adaptive = _adaptive_drill(target, count, skill_id, domain_id)
    ranked = sorted(adaptive, key=lambda row: question_exposure_rank(row, mode))
    if len(ranked) >= count:
        return ranked[:count]
    seen = {row["id"] for row in ranked}
    for row in sorted(rows, key=lambda item: question_exposure_rank(item, mode)):
        if row["id"] not in seen:
            ranked.append(row)
            seen.add(row["id"])
        if len(ranked) >= count:
            break
    return ranked[:count]


def select_certification_questions(
    payload: CertificationQuizStart,
    candidate: dict[str, Any],
    *,
    trusted_exam_session: bool = False,
    exclude_question_ids: set[str] | None = None,
) -> dict[str, Any]:
    cert = _cert(payload.track_id)
    count = max(1, min(int(payload.count), 500))
    mode = str(payload.mode or "drill").strip().lower().replace("_", "-")

    if mode in TIMED_MOCK_MODES and not trusted_exam_session:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "mock_session_required",
                "message": "Timed and reserved mock questions are only available through the server-managed mock-session endpoint.",
            },
        )

    with connect() as conn:
        rows = _question_pool(
            conn,
            payload.track_id,
            payload.difficulty,
            payload.unanswered_only,
            payload.test_id,
            candidate["id"],
        )
        persisted = _best_reliable_edges(conn, payload.track_id)
    rows, reliable_count, heuristic_count = _assign_edges(rows, payload.track_id, persisted)
    rows = _enrich_rows(rows, candidate["id"])
    rows = _safe_fallback_rows(rows, pinned_internal_test=bool(payload.test_id and trusted_exam_session))
    rows = filter_rows_for_entitlement(rows, candidate["membership"], mode, count)

    excluded = {str(item) for item in (exclude_question_ids or set()) if str(item)}
    exclusion_applied = False
    if excluded:
        fresh_rows = [row for row in rows if str(row.get("id") or "") not in excluded]
        if len(fresh_rows) >= count:
            rows = fresh_rows
            exclusion_applied = True

    if not rows:
        return {
            "questions": [],
            "total": 0,
            "selection_strategy": mode,
            "domain_counts": {},
            "mapped_count": 0,
            "heuristic_count": 0,
            "quota": None,
        }

    if payload.test_id:
        selected = sorted(rows, key=lambda row: (int(row.get("question_position") or 0), row.get("id") or ""))[:count]
        strategy = "source_exam_order"
    elif payload.skill_id:
        selected = _select_targeted(rows, count, mode, payload.skill_id, payload.domain_id)
        strategy = "skill_targeted_exposure_aware"
    elif payload.domain_id and mode != "diagnostic":
        selected = _select_targeted(rows, count, mode, None, payload.domain_id)
        strategy = "domain_targeted_exposure_aware"
    elif mode in {"diagnostic", "weekly-mock", "quick-mock", "full-mock", "lifetime-practice", "mock", "exam"}:
        # The Free weekly product is a 30-question full-content timed mock. It
        # deliberately uses the same 30Q blueprint composition as Quick Mock,
        # while entitlement filtering above still limits Free to the Free pool.
        blueprint_mode = "quick-mock" if mode == "weekly-mock" and count == 30 else mode
        selected = select_blueprint_questions(rows, cert.get("domains") or [], count, blueprint_mode)
        strategy = "blueprint_weighted_private_bank"
    elif mode == "drill":
        selected = _select_targeted(rows, count, mode, None, None)
        strategy = "adaptive_weakness_exposure_aware"
    else:
        selected = sorted(rows, key=lambda row: question_exposure_rank(row, mode))[:count]
        strategy = "exposure_aware"

    if exclusion_applied:
        strategy += "_fresh_reset_set"

    domain_counts: dict[str, int] = defaultdict(int)
    skill_ids: set[str] = set()
    provenance_counts: dict[str, int] = defaultdict(int)
    source_counts: dict[str, int] = defaultdict(int)
    pool_counts: dict[str, int] = defaultdict(int)
    difficulty_counts: dict[str, int] = defaultdict(int)
    for row in selected:
        domain_counts[row.get("mapped_domain_id") or "unmapped"] += 1
        if row.get("mapped_skill_id"):
            skill_ids.add(row["mapped_skill_id"])
        provenance_counts[row.get("mapping_provenance") or "unmapped"] += 1
        source_counts[row.get("source_kind") or "unknown"] += 1
        pool_counts[row.get("bank_pool") or "fallback"] += 1
        difficulty_counts[row.get("difficulty_band") or row.get("difficulty") or "unknown"] += 1

    questions = [question_public(row, include_answer=False) for row in selected]
    quota = None
    if not trusted_exam_session and candidate.get("membership"):
        quota = reserve_daily_questions(candidate["id"], candidate["membership"], len(questions))

    record_questions_served(candidate["id"], selected, mode=mode)
    return {
        "questions": questions,
        "total": len(questions),
        "selection_strategy": strategy,
        "domain_counts": dict(domain_counts),
        "skill_ids": sorted(skill_ids),
        "mapping_provenance": dict(provenance_counts),
        "source_counts": dict(source_counts),
        "pool_counts": dict(pool_counts),
        "difficulty_counts": dict(difficulty_counts),
        "reliable_pool_count": reliable_count,
        "heuristic_pool_count": heuristic_count,
        "practice_test_id": payload.test_id,
        "quota": quota,
        "reset_exclusion_applied": exclusion_applied,
        "reset_excluded_count": len(excluded),
    }
