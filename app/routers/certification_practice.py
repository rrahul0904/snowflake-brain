from __future__ import annotations

import json
import math
import random
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..certification_content import configured_skill_map, study_lesson
from ..database import connect
from ..serializers import question_public
from ..skill_brain import flatten_skills, skill_score
from ..auth import require_candidate, require_premium_candidate
from ..entitlements import reserve_daily_questions, validate_mock_start

router = APIRouter()


class CertificationQuizStart(BaseModel):
    track_id: str = "snowpro-core"
    count: int = Field(15, ge=1, le=500)
    mode: str = "drill"
    skill_id: str | None = None
    domain_id: str | None = None
    test_id: str | None = None
    difficulty: str | None = None
    unanswered_only: bool = False


class MockSummary(BaseModel):
    track_id: str = "snowpro-core"
    mode: str = "full-mock"
    score: int = Field(ge=0)
    total: int = Field(ge=1)
    elapsed_seconds: int = Field(default=0, ge=0)
    selection_strategy: str = "blueprint_weighted"
    practice_test_id: str | None = None


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


def _placed_options(correct: str, distractors: list[str], correct_index: int) -> tuple[list[str], list[int]]:
    clean = [str(item).strip() for item in distractors if str(item).strip() and str(item).strip() != correct]
    fallback = [
        "Use the broadest administrative privilege because it is more flexible.",
        "Move the workload outside Snowflake before checking whether the platform already supports it.",
        "Increase compute first without identifying the actual requirement or bottleneck.",
    ]
    while len(clean) < 3:
        clean.append(fallback[len(clean) % len(fallback)])
    options = clean[:3]
    correct_index = max(0, min(3, int(correct_index)))
    options.insert(correct_index, correct)
    return options, [correct_index]


def _canonical_variants(track_id: str, skill: dict[str, Any], target_count: int) -> list[dict[str, Any]]:
    payload = study_lesson(track_id, skill["id"])
    content = (payload or {}).get("content") or {}
    objective = skill.get("objective") or content.get("summary") or f"Apply {skill.get('title')} correctly."
    traps = list(skill.get("exam_traps") or [])
    anti_patterns = list(content.get("anti_patterns") or traps)
    rules = list(content.get("decision_rules") or [])
    trap_explanations = list(content.get("trap_explanations") or [])
    checks = list((content.get("build_exercise") or {}).get("checks") or [])
    worked = content.get("worked_example") or {}
    scenario = content.get("scenario") or {}
    variants: list[dict[str, Any]] = []

    scenario_options = scenario.get("options") or []
    if scenario.get("question") and len(scenario_options) >= 2:
        variants.append(
            {
                "question": scenario["question"],
                "options": scenario_options,
                "correct": [int(scenario.get("correct_index") or 0)],
                "explanation": scenario.get("explanation") or objective,
                "difficulty": "medium",
                "kind": "scenario",
            }
        )

    direct_options, direct_correct = _placed_options(
        objective,
        [
            "Apply a nearby Snowflake feature even when it solves a different layer of the problem.",
            "Prefer the most privileged or expensive option regardless of the stated requirement.",
            "Ignore the task boundary and choose based only on a familiar keyword.",
        ],
        1,
    )
    variants.append(
        {
            "question": f"Which statement best matches the certification objective for {skill.get('title')}?",
            "options": direct_options,
            "correct": direct_correct,
            "explanation": objective,
            "difficulty": "easy",
            "kind": "objective",
        }
    )

    if rules:
        rule = rules[0]
        options, correct = _placed_options(
            str(rule.get("choose") or skill.get("title")),
            [
                "Choose the broadest system role instead of matching the requirement.",
                "Add more compute even though the scenario does not describe a compute bottleneck.",
                "Export the data and rebuild the workflow outside Snowflake by default.",
            ],
            2,
        )
        variants.append(
            {
                "question": f"Requirement: {rule.get('when')}. Which choice is most appropriate?",
                "options": options,
                "correct": correct,
                "explanation": str(rule.get("why") or objective),
                "difficulty": "medium",
                "kind": "decision_rule",
            }
        )

    trap = traps[0] if traps else (anti_patterns[0] if anti_patterns else "Choose a feature without checking the scenario requirement.")
    options, correct = _placed_options(
        trap,
        [
            f"Apply {skill.get('title')} only when its documented responsibility matches the requirement.",
            "Compare adjacent Snowflake features before selecting the answer.",
            "Use the least unnecessary privilege, movement, cost, and operational complexity.",
        ],
        3,
    )
    variants.append(
        {
            "question": f"Which option is a common exam trap or anti-pattern for {skill.get('title')}?",
            "options": options,
            "correct": correct,
            "explanation": f"This is a configured trap for the task: {trap}",
            "difficulty": "medium",
            "kind": "trap",
        }
    )

    if trap_explanations:
        item = trap_explanations[0]
        correction = str(item.get("correction") or objective)
        options, correct = _placed_options(
            correction,
            [
                "The trap is actually the recommended design in every scenario.",
                "The distinction does not matter because all Snowflake features have the same responsibility.",
                "The safest answer is always the option with the most privileges or compute.",
            ],
            0,
        )
        variants.append(
            {
                "question": f"A candidate believes: “{item.get('trap')}” Which correction is most accurate?",
                "options": options,
                "correct": correct,
                "explanation": correction,
                "difficulty": "hard",
                "kind": "trap_correction",
            }
        )

    anti = anti_patterns[0] if anti_patterns else trap
    options, correct = _placed_options(
        anti,
        [
            f"Match {skill.get('title')} to its documented problem boundary.",
            "Validate the scenario constraints before choosing an implementation.",
            "Prefer a simpler Snowflake-native solution when it satisfies the requirement.",
        ],
        1,
    )
    variants.append(
        {
            "question": f"Which implementation choice should you avoid when applying {skill.get('title')}?",
            "options": options,
            "correct": correct,
            "explanation": f"The lesson identifies this as an anti-pattern: {anti}",
            "difficulty": "medium",
            "kind": "anti_pattern",
        }
    )

    check = checks[0] if checks else f"The implementation directly satisfies the objective: {objective}"
    options, correct = _placed_options(
        check,
        [
            "The solution relies on an unrelated feature instead of the task capability.",
            "The solution broadens access or cost without a requirement for it.",
            "The solution ignores the feature boundary described in the lesson.",
        ],
        2,
    )
    variants.append(
        {
            "question": f"Which completion check best demonstrates a correct implementation of {skill.get('title')}?",
            "options": options,
            "correct": correct,
            "explanation": check,
            "difficulty": "medium",
            "kind": "build_check",
        }
    )

    worked_answer = str(worked.get("answer") or objective)
    options, correct = _placed_options(
        worked_answer,
        [
            "Choose the opposite control even though it addresses a different requirement.",
            "Escalate to the broadest administrative option without evidence.",
            "Ignore the stated constraints and optimize a different part of the system.",
        ],
        3,
    )
    variants.append(
        {
            "question": f"Which conclusion best matches the worked example for {skill.get('title')}?",
            "options": options,
            "correct": correct,
            "explanation": worked_answer,
            "difficulty": "hard",
            "kind": "worked_example",
        }
    )

    while len(variants) < target_count:
        index = len(variants)
        options, correct = _placed_options(
            f"Apply {skill.get('title')} when the scenario matches this objective: {objective}",
            [
                "Select a different feature solely because its name appears in the question.",
                "Increase privilege or compute before establishing that it is required.",
                "Ignore the documented task boundary and rely on an unrelated workaround.",
            ],
            index % 4,
        )
        variants.append(
            {
                "question": f"Application check {index + 1}: Which approach correctly applies {skill.get('title')}?",
                "options": options,
                "correct": correct,
                "explanation": objective,
                "difficulty": "medium" if index % 3 else "hard",
                "kind": f"application_{index + 1}",
            }
        )
    return variants[:target_count]


def _ensure_canonical_question_bank(conn: Any, track_id: str) -> int:
    cert = _cert(track_id)
    test_id = f"canonical::{track_id}"
    test_title = f"{cert.get('title') or track_id} Supplemental Drill Bank"
    conn.execute(
        """
        INSERT INTO certification_tracks(id, title, exam_code, description, position)
        VALUES (?, ?, ?, ?, 0)
        ON CONFLICT(id) DO UPDATE SET title=excluded.title, exam_code=excluded.exam_code
        """,
        (
            track_id,
            cert.get("title") or track_id,
            cert.get("exam_code") or "",
            f"Certification track for {cert.get('exam_code') or track_id}",
        ),
    )
    conn.execute(
        """
        INSERT INTO practice_tests(id, track_id, title, exam_code, source_kind, source_path, position, version, is_legacy)
        VALUES (?, ?, ?, ?, 'canonical', ?, 999, 'generated-from-written-lessons', 0)
        ON CONFLICT(id) DO UPDATE SET title=excluded.title, exam_code=excluded.exam_code
        """,
        (test_id, track_id, test_title, cert.get("exam_code") or "", f"canonical://{track_id}"),
    )

    created = 0
    skills = flatten_skills(track_id)
    target_per_skill = max(8, math.ceil(80 / max(1, len(skills))))
    for skill in skills:
        for index, variant in enumerate(_canonical_variants(track_id, skill, target_per_skill)):
            question_id = f"certgen::{track_id}::{skill['id']}::{index + 1}"
            before = conn.total_changes
            conn.execute(
                """
                INSERT OR IGNORE INTO questions(
                  id, track_id, test_id, test_title, question, options_json, correct_json,
                  explanation, source_path, source_kind, assessment_type, tags,
                  difficulty, multiple, question_position
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'canonical', 'certification_canonical', ?, ?, ?, ?)
                """,
                (
                    question_id,
                    track_id,
                    test_id,
                    test_title,
                    variant["question"],
                    json.dumps(variant["options"]),
                    json.dumps(variant["correct"]),
                    variant["explanation"],
                    f"canonical://{track_id}/{skill['id']}/{variant['kind']}",
                    json.dumps([skill["id"], skill.get("domain_id"), "canonical", variant["kind"]]),
                    variant["difficulty"],
                    int(len(variant["correct"]) > 1),
                    index + 1,
                ),
            )
            if conn.total_changes > before:
                created += 1
            conn.execute(
                """
                INSERT INTO question_skill_map(question_id, track_id, domain_id, skill_id, confidence, evidence_json, reviewed)
                VALUES (?, ?, ?, ?, 0.98, ?, 0)
                ON CONFLICT(question_id, skill_id) DO UPDATE SET
                  track_id=excluded.track_id,
                  domain_id=excluded.domain_id,
                  confidence=MAX(question_skill_map.confidence, excluded.confidence),
                  evidence_json=excluded.evidence_json,
                  updated_at=datetime('now')
                """,
                (
                    question_id,
                    track_id,
                    skill.get("domain_id") or "",
                    skill["id"],
                    json.dumps(
                        {
                            "source": "canonical_written_lesson",
                            "variant": variant["kind"],
                            "deterministic_skill_edge": True,
                        }
                    ),
                ),
            )
    conn.execute(
        "UPDATE practice_tests SET question_count=(SELECT COUNT(*) FROM questions WHERE test_id=?) WHERE id=?",
        (test_id, test_id),
    )
    return created


def _question_pool(
    conn: Any,
    track_id: str,
    difficulty: str | None,
    unanswered_only: bool,
    test_id: str | None,
    candidate_id: int,
) -> list[dict[str, Any]]:
    _ensure_canonical_question_bank(conn, track_id)
    filters = ["q.track_id = ?"]
    params: list[Any] = [track_id]
    if test_id:
        filters.append("q.test_id = ?")
        params.append(test_id)
    else:
        # Legacy exam banks must be explicitly selected; they never influence C03 readiness.
        filters.append("q.source_kind <> 'legacy'")
    if difficulty:
        filters.append("q.difficulty = ?")
        params.append(difficulty)
    if unanswered_only:
        filters.append("NOT EXISTS (SELECT 1 FROM question_attempts qa0 WHERE qa0.question_id = q.id AND qa0.candidate_id = ?)")
        params.append(candidate_id)
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
            LEFT JOIN question_attempts qa ON qa.question_id = q.id AND qa.candidate_id = ?
            WHERE {where}
            GROUP BY q.id
            LIMIT 10000
            """,
            [candidate_id, *params],
        )
    ]


def _best_reliable_edges(conn: Any, track_id: str) -> dict[str, dict[str, Any]]:
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


def _assign_edges(
    rows: list[dict[str, Any]],
    track_id: str,
    persisted: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], int, int]:
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


def _source_rank(row: dict[str, Any]) -> int:
    return {"source": 0, "curated": 1, "canonical": 2, "legacy": 9}.get(str(row.get("source_kind") or ""), 3)


def _rank_for_drill(row: dict[str, Any]) -> tuple[Any, ...]:
    attempts = int(row.get("attempts") or 0)
    correct = int(row.get("correct_attempts") or 0)
    misses = int(row.get("missed_attempts") or 0)
    accuracy = (correct / attempts) if attempts else 0
    provenance_rank = {
        "human_reviewed": 0,
        "persisted_high_confidence": 1,
        "heuristic_fallback": 2,
        "unmapped": 3,
    }.get(row.get("mapping_provenance"), 3)
    return (
        0 if attempts == 0 else 1,
        -misses,
        accuracy,
        _source_rank(row),
        provenance_rank,
        attempts,
        row.get("last_attempted") or "",
    )


def _take_unique(target: list[dict[str, Any]], source: list[dict[str, Any]], count: int, seen: set[str]) -> None:
    for row in source:
        if len(target) >= count:
            return
        if row["id"] in seen:
            continue
        target.append(row)
        seen.add(row["id"])


def _prepared_bucket(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = list(rows)
    random.shuffle(rows)
    rows.sort(key=_source_rank)
    return rows


def _balanced_by_domain(rows: list[dict[str, Any]], domains: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("mapped_domain_id"):
            buckets[row["mapped_domain_id"]].append(row)
    for key in list(buckets):
        buckets[key] = _prepared_bucket(buckets[key])
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    active = [domain for domain in domains if buckets.get(domain.get("id"))]
    if active:
        base = max(1, count // len(active))
        for domain in active:
            _take_unique(selected, buckets[domain["id"]], min(count, len(selected) + base), seen)
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
    residual = _prepared_bucket(rows)
    _take_unique(selected, residual, count, seen)
    return selected


def _weighted_by_domain(rows: list[dict[str, Any]], domains: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("mapped_domain_id"):
            buckets[row["mapped_domain_id"]].append(row)
    for key in list(buckets):
        buckets[key] = _prepared_bucket(buckets[key])
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    allocations: list[tuple[dict[str, Any], int]] = []
    for domain in domains:
        weight = float(domain.get("weight") or 0)
        allocations.append((domain, max(1, round(count * weight / 100)) if weight else 0))
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
    _take_unique(selected, _prepared_bucket(rows), count, seen)
    return selected


def _adaptive_drill(
    rows: list[dict[str, Any]],
    count: int,
    skill_id: str | None,
    domain_id: str | None,
) -> list[dict[str, Any]]:
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
                skill_stats[sid]["correct"] / max(1, skill_stats[sid]["attempts"]),
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
    _take_unique(selected, sorted(rows, key=_rank_for_drill), count, seen)
    return selected


@router.post("/certification-quiz/start")
def certification_quiz_start(payload: CertificationQuizStart, candidate: dict = Depends(require_candidate)) -> dict[str, Any]:
    cert = _cert(payload.track_id)
    count = max(1, min(payload.count, 500))
    mode = (payload.mode or "drill").strip().lower()
    with connect() as conn:
        rows = _question_pool(conn, payload.track_id, payload.difficulty, payload.unanswered_only, payload.test_id, candidate["id"])
        persisted = _best_reliable_edges(conn, payload.track_id)
    rows, reliable_count, heuristic_count = _assign_edges(rows, payload.track_id, persisted)
    if not rows:
        return {
            "questions": [],
            "total": 0,
            "selection_strategy": mode,
            "domain_counts": {},
            "mapped_count": 0,
            "heuristic_count": 0,
        }

    if payload.test_id:
        selected = sorted(rows, key=lambda row: (int(row.get("question_position") or 0), row.get("id") or ""))[:count]
        strategy = "source_exam_order"
    elif payload.skill_id:
        selected = _adaptive_drill(rows, count, payload.skill_id, payload.domain_id)
        strategy = "skill_targeted"
    elif payload.domain_id and mode not in {"diagnostic", "mock", "quick-mock", "full-mock", "exam"}:
        selected = _adaptive_drill(rows, count, None, payload.domain_id)
        strategy = "domain_targeted"
    elif mode == "diagnostic":
        selected = _balanced_by_domain(rows, cert.get("domains") or [], count)
        strategy = "domain_balanced"
    elif mode in {"mock", "quick-mock", "full-mock", "exam"}:
        selected = _weighted_by_domain(rows, cert.get("domains") or [], count)
        strategy = "blueprint_weighted_source_first"
    elif mode == "drill":
        selected = _adaptive_drill(rows, count, None, None)
        strategy = "adaptive_weakness"
    else:
        selected = _prepared_bucket(rows)[:count]
        strategy = "random_source_first"

    domain_counts: dict[str, int] = defaultdict(int)
    skill_ids: set[str] = set()
    provenance_counts: dict[str, int] = defaultdict(int)
    source_counts: dict[str, int] = defaultdict(int)
    for row in selected:
        domain_counts[row.get("mapped_domain_id") or "unmapped"] += 1
        if row.get("mapped_skill_id"):
            skill_ids.add(row["mapped_skill_id"])
        provenance_counts[row.get("mapping_provenance") or "unmapped"] += 1
        source_counts[row.get("source_kind") or "unknown"] += 1
    questions = [question_public(row, include_answer=False) for row in selected]
    quota = reserve_daily_questions(candidate["id"], candidate["membership"], len(questions)) if candidate.get("membership") else None
    return {
        "questions": questions,
        "total": len(questions),
        "selection_strategy": strategy,
        "domain_counts": dict(domain_counts),
        "skill_ids": sorted(skill_ids),
        "mapping_provenance": dict(provenance_counts),
        "source_counts": dict(source_counts),
        "reliable_pool_count": reliable_count,
        "heuristic_pool_count": heuristic_count,
        "practice_test_id": payload.test_id,
        "quota": quota,
    }


@router.post("/certification-mock/record")
def record_certification_mock(payload: MockSummary, candidate: dict = Depends(require_premium_candidate)) -> dict[str, Any]:
    cert = _cert(payload.track_id)
    if payload.score > payload.total:
        raise HTTPException(status_code=400, detail="Mock score cannot exceed the total question count")
    normalized_mode = validate_mock_start(candidate, payload.mode)
    if normalized_mode == "quick-mock":
        reserve_daily_questions(candidate["id"], candidate["membership"], payload.total)
    percent = round((payload.score / max(1, payload.total)) * 100)
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO certification_tracks(id, title, exam_code, description, position)
            VALUES (?, ?, ?, ?, 0)
            ON CONFLICT(id) DO UPDATE SET title=excluded.title, exam_code=excluded.exam_code
            """,
            (
                payload.track_id,
                cert.get("title") or payload.track_id,
                cert.get("exam_code") or "",
                f"Certification track for {cert.get('exam_code') or payload.track_id}",
            ),
        )
        cursor = conn.execute(
            """
            INSERT INTO exam_sessions(
              track_id, practice_test_id, mode, started_at, finished_at,
              score, total_questions, status, candidate_id
            ) VALUES (?, ?, ?, datetime('now', ?), datetime('now'), ?, ?, 'finished', ?)
            """,
            (
                payload.track_id,
                payload.practice_test_id,
                "exam_full_mock" if payload.mode in {"full-mock", "exam"} else "exam_quick_mock",
                f"-{max(0, int(payload.elapsed_seconds))} seconds",
                payload.score,
                payload.total,
                candidate["id"],
            ),
        )
        session_id = int(cursor.lastrowid)
        conn.execute(
            """
            INSERT INTO learning_events(event_type, track_id, practice_test_id, metadata_json, candidate_id)
            VALUES ('practice_test_finished', ?, ?, ?, ?)
            """,
            (
                payload.track_id,
                payload.practice_test_id,
                json.dumps(
                    {
                        "session_id": session_id,
                        "mode": payload.mode,
                        "score": payload.score,
                        "total": payload.total,
                        "score_pct": percent,
                        "elapsed_seconds": payload.elapsed_seconds,
                        "selection_strategy": payload.selection_strategy,
                    }
                ),
                candidate["id"],
            ),
        )
    return {"ok": True, "session_id": session_id, "score_pct": percent}
