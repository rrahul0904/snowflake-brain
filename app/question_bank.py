from __future__ import annotations

import hashlib
import json
import math
import random
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from fastapi import HTTPException

from .certification_content import configured_skill_map
from .config import PRIVATE_QUESTION_BANK_DIR
from .database import connect
from .entitlements import plan_details
from .serializers import json_list


QUESTION_BANK_SCHEMA_VERSION = "snowflake-question-bank-v1"
ALLOWED_POOLS = {"free", "practice", "diagnostic", "mock_reserved"}
ALLOWED_DIFFICULTY_BANDS = {"foundation", "applied", "exam", "challenge"}
ALLOWED_AUTHORING_STATUS = {"draft", "review", "active", "retired"}
ALLOWED_QUESTION_TYPES = {
    "standard_mcq",
    "scenario",
    "architecture_decision",
    "troubleshooting",
    "sql_interpretation",
    "best_answer",
    "multi_select",
}

# These are app simulation settings, not claims about the exact live exam.
MODE_DOMAIN_COUNTS: dict[str, dict[str, int]] = {
    "weekly-mock": {
        "features-architecture": 6,
        "account-governance": 4,
        "loading-connectivity": 4,
        "performance-transformation": 4,
        "data-collaboration": 2,
    },
    "quick-mock": {
        "features-architecture": 9,
        "account-governance": 6,
        "loading-connectivity": 5,
        "performance-transformation": 7,
        "data-collaboration": 3,
    },
    "full-mock": {
        "features-architecture": 31,
        "account-governance": 20,
        "loading-connectivity": 18,
        "performance-transformation": 21,
        "data-collaboration": 10,
    },
    "lifetime-practice": {
        "features-architecture": 31,
        "account-governance": 20,
        "loading-connectivity": 18,
        "performance-transformation": 21,
        "data-collaboration": 10,
    },
}

MODE_DIFFICULTY_RATIOS: dict[str, dict[str, float]] = {
    "weekly-mock": {"foundation": 0.30, "applied": 0.40, "exam": 0.25, "challenge": 0.05},
    "quick-mock": {"foundation": 0.00, "applied": 0.35, "exam": 0.50, "challenge": 0.15},
    "full-mock": {"foundation": 0.15, "applied": 0.35, "exam": 0.40, "challenge": 0.10},
    "lifetime-practice": {"foundation": 0.15, "applied": 0.35, "exam": 0.40, "challenge": 0.10},
    "diagnostic": {"foundation": 0.20, "applied": 0.40, "exam": 0.30, "challenge": 0.10},
}

MILESTONE_TARGETS = {
    "internal_mvp": 600,
    "beta": 1200,
    "commercial_v1": 2000,
    "mature": 3000,
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


def _normalized_text(value: str) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _content_hash(question: dict[str, Any]) -> str:
    payload = {
        "question": question["question"],
        "options": question["options"],
        "correct_options": question["correct_options"],
        "correct_rationale": question["correct_rationale"],
    }
    return hashlib.sha256(_json(payload).encode("utf-8")).hexdigest()


def _certification_index(track_id: str) -> tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    cert = next(
        (item for item in configured_skill_map().get("certifications") or [] if item.get("id") == track_id),
        None,
    )
    if not cert:
        raise ValueError(f"Certification track is not configured: {track_id}")
    domains = {domain["id"]: domain for domain in cert.get("domains") or []}
    tasks: dict[str, dict[str, Any]] = {}
    for domain in domains.values():
        for skill in domain.get("skills") or []:
            tasks[skill["id"]] = {**skill, "domain_id": domain["id"], "domain_title": domain.get("title")}
    return cert, domains, tasks


def validate_question_bank_payload(payload: dict[str, Any], *, source_name: str = "question-bank") -> dict[str, Any]:
    errors: list[str] = []
    schema_version = str(payload.get("schema_version") or "")
    track_id = str(payload.get("track_id") or "")
    exam_code = str(payload.get("exam_code") or "")
    if schema_version != QUESTION_BANK_SCHEMA_VERSION:
        errors.append(f"schema_version must be {QUESTION_BANK_SCHEMA_VERSION}")
    if not track_id:
        errors.append("track_id is required")
    if not exam_code:
        errors.append("exam_code is required")
    if errors:
        return {"valid": False, "errors": errors, "questions": [], "coverage": {}}

    try:
        cert, domains, tasks = _certification_index(track_id)
    except ValueError as exc:
        return {"valid": False, "errors": [str(exc)], "questions": [], "coverage": {}}
    if exam_code != str(cert.get("exam_code") or exam_code):
        errors.append(f"exam_code {exam_code} does not match configured {cert.get('exam_code')}")

    raw_questions = payload.get("questions")
    if not isinstance(raw_questions, list) or not raw_questions:
        errors.append("questions must be a non-empty array")
        return {"valid": False, "errors": errors, "questions": [], "coverage": {}}

    normalized: list[dict[str, Any]] = []
    ids: set[str] = set()
    stems: set[str] = set()
    coverage: dict[str, int] = defaultdict(int)
    pools: dict[str, int] = defaultdict(int)
    difficulty: dict[str, int] = defaultdict(int)

    for position, raw in enumerate(raw_questions, start=1):
        prefix = f"{source_name} question #{position}"
        if not isinstance(raw, dict):
            errors.append(f"{prefix}: must be an object")
            continue
        qid = str(raw.get("id") or "").strip()
        domain_id = str(raw.get("domain_id") or "").strip()
        task_id = str(raw.get("task_id") or "").strip()
        task = tasks.get(task_id)
        question_type = str(raw.get("question_type") or "standard_mcq").strip()
        band = str(raw.get("difficulty_band") or "applied").strip()
        pool = str(raw.get("bank_pool") or "practice").strip()
        status = str(raw.get("authoring_status") or "review").strip()
        question = str(raw.get("question") or "").strip()
        options = raw.get("options")
        correct_options = raw.get("correct_options")
        correct_rationale = str(raw.get("correct_rationale") or "").strip()
        distractor_rationales = raw.get("distractor_rationales") or []
        source_refs = raw.get("source_refs") or []

        if not qid:
            errors.append(f"{prefix}: id is required")
        elif qid in ids:
            errors.append(f"{prefix}: duplicate id {qid}")
        else:
            ids.add(qid)
        if domain_id not in domains:
            errors.append(f"{prefix}: unknown domain_id {domain_id}")
        if not task:
            errors.append(f"{prefix}: unknown task_id {task_id}")
        elif task.get("domain_id") != domain_id:
            errors.append(f"{prefix}: task {task_id} belongs to {task.get('domain_id')}, not {domain_id}")
        if question_type not in ALLOWED_QUESTION_TYPES:
            errors.append(f"{prefix}: unsupported question_type {question_type}")
        if band not in ALLOWED_DIFFICULTY_BANDS:
            errors.append(f"{prefix}: unsupported difficulty_band {band}")
        if pool not in ALLOWED_POOLS:
            errors.append(f"{prefix}: unsupported bank_pool {pool}")
        if status not in ALLOWED_AUTHORING_STATUS:
            errors.append(f"{prefix}: unsupported authoring_status {status}")
        if len(question) < 20:
            errors.append(f"{prefix}: question is too short")
        normalized_stem = _normalized_text(question)
        if normalized_stem in stems:
            errors.append(f"{prefix}: duplicate normalized question stem")
        stems.add(normalized_stem)
        if not isinstance(options, list) or len(options) < 3:
            errors.append(f"{prefix}: options must contain at least 3 choices")
            options = list(options or []) if isinstance(options, list) else []
        options = [str(item).strip() for item in options]
        if len(set(options)) != len(options):
            errors.append(f"{prefix}: answer choices must be unique")
        if not isinstance(correct_options, list) or not correct_options:
            errors.append(f"{prefix}: correct_options must contain at least one index")
            correct_options = []
        cleaned_correct: list[int] = []
        for item in correct_options:
            try:
                idx = int(item)
            except (TypeError, ValueError):
                errors.append(f"{prefix}: correct option index {item!r} is invalid")
                continue
            if idx < 0 or idx >= len(options):
                errors.append(f"{prefix}: correct option index {idx} is outside the options array")
            else:
                cleaned_correct.append(idx)
        cleaned_correct = sorted(set(cleaned_correct))
        if question_type == "multi_select" and len(cleaned_correct) < 2:
            errors.append(f"{prefix}: multi_select requires at least two correct options")
        if question_type != "multi_select" and len(cleaned_correct) > 1:
            errors.append(f"{prefix}: multiple correct options require question_type=multi_select")
        if len(correct_rationale) < 20:
            errors.append(f"{prefix}: correct_rationale is required and must explain the answer")
        if not isinstance(distractor_rationales, list):
            errors.append(f"{prefix}: distractor_rationales must be an array")
            distractor_rationales = []
        if len(distractor_rationales) not in {0, len(options)}:
            errors.append(f"{prefix}: distractor_rationales must be empty or align one-to-one with options")
        if not isinstance(source_refs, list) or not source_refs:
            errors.append(f"{prefix}: at least one official source reference is required")
            source_refs = []
        for ref in source_refs:
            if not isinstance(ref, dict) or not str(ref.get("url") or "").startswith("https://docs.snowflake.com/"):
                errors.append(f"{prefix}: every source_refs entry must point to official docs.snowflake.com")

        task_code = str(raw.get("task_code") or (task or {}).get("task_code") or "")
        normalized_row = {
            "id": qid,
            "track_id": track_id,
            "exam_code": exam_code,
            "domain_id": domain_id,
            "task_id": task_id,
            "task_code": task_code,
            "question_type": question_type,
            "cognitive_level": str(raw.get("cognitive_level") or "apply").strip(),
            "difficulty_band": band,
            "bank_pool": pool,
            "authoring_status": status,
            "authoring_version": str(raw.get("authoring_version") or payload.get("bank_version") or "1"),
            "question": question,
            "options": options,
            "correct_options": cleaned_correct,
            "correct_rationale": correct_rationale,
            "distractor_rationales": distractor_rationales,
            "concepts": list(raw.get("concepts") or []),
            "trap_tags": list(raw.get("trap_tags") or []),
            "source_refs": source_refs,
            "source_verified_at": str(raw.get("source_verified_at") or payload.get("source_verified_at") or ""),
        }
        normalized_row["content_hash"] = _content_hash(normalized_row)
        normalized.append(normalized_row)
        if status == "active":
            coverage[task_id] += 1
            pools[pool] += 1
            difficulty[band] += 1

    return {
        "valid": not errors,
        "errors": errors,
        "questions": normalized,
        "coverage": {
            "active_questions": sum(coverage.values()),
            "by_task": dict(sorted(coverage.items())),
            "by_pool": dict(sorted(pools.items())),
            "by_difficulty": dict(sorted(difficulty.items())),
            "tasks_covered": sum(1 for task_id in tasks if coverage.get(task_id, 0) > 0),
            "tasks_total": len(tasks),
        },
    }


def import_question_bank_payload(
    payload: dict[str, Any],
    *,
    source_name: str,
    dry_run: bool = False,
) -> dict[str, Any]:
    validation = validate_question_bank_payload(payload, source_name=source_name)
    if not validation["valid"]:
        raise ValueError("Question bank validation failed:\n- " + "\n- ".join(validation["errors"]))
    rows = validation["questions"]
    if dry_run:
        return {"dry_run": True, "imported": 0, **validation["coverage"]}

    track_id = str(payload["track_id"])
    exam_code = str(payload["exam_code"])
    bank_version = str(payload.get("bank_version") or "1")
    payload_hash = hashlib.sha256(_json(payload).encode("utf-8")).hexdigest()
    imported = 0
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        for row in rows:
            qid = row["id"]
            difficulty_legacy = {
                "foundation": "easy",
                "applied": "medium",
                "exam": "hard",
                "challenge": "hard",
            }[row["difficulty_band"]]
            tags = list(dict.fromkeys([row["task_id"], row["domain_id"], *row["concepts"], *row["trap_tags"]]))
            conn.execute(
                """
                INSERT INTO questions(
                  id, track_id, test_id, test_title, question, options_json, correct_json,
                  explanation, source_path, source_kind, assessment_type, tags, difficulty,
                  multiple, question_position
                ) VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, 'private_bank', ?, ?, ?, ?, 0)
                ON CONFLICT(id) DO UPDATE SET
                  track_id=excluded.track_id,
                  question=excluded.question,
                  options_json=excluded.options_json,
                  correct_json=excluded.correct_json,
                  explanation=excluded.explanation,
                  source_path=excluded.source_path,
                  source_kind='private_bank',
                  assessment_type=excluded.assessment_type,
                  tags=excluded.tags,
                  difficulty=excluded.difficulty,
                  multiple=excluded.multiple
                """,
                (
                    qid,
                    track_id,
                    f"{exam_code} Private Question Bank",
                    row["question"],
                    _json(row["options"]),
                    _json(row["correct_options"]),
                    row["correct_rationale"],
                    f"private://{source_name}#{qid}",
                    f"bank_{row['question_type']}",
                    _json(tags),
                    difficulty_legacy,
                    int(len(row["correct_options"]) > 1),
                ),
            )
            conn.execute(
                """
                INSERT INTO question_bank_metadata(
                  question_id, certification_id, exam_version, domain_id, task_id, task_code,
                  question_type, cognitive_level, difficulty_band, bank_pool, authoring_status,
                  authoring_version, concepts_json, trap_tags_json, distractor_rationales_json,
                  source_refs_json, source_verified_at, content_hash, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(question_id) DO UPDATE SET
                  certification_id=excluded.certification_id,
                  exam_version=excluded.exam_version,
                  domain_id=excluded.domain_id,
                  task_id=excluded.task_id,
                  task_code=excluded.task_code,
                  question_type=excluded.question_type,
                  cognitive_level=excluded.cognitive_level,
                  difficulty_band=excluded.difficulty_band,
                  bank_pool=excluded.bank_pool,
                  authoring_status=excluded.authoring_status,
                  authoring_version=excluded.authoring_version,
                  concepts_json=excluded.concepts_json,
                  trap_tags_json=excluded.trap_tags_json,
                  distractor_rationales_json=excluded.distractor_rationales_json,
                  source_refs_json=excluded.source_refs_json,
                  source_verified_at=excluded.source_verified_at,
                  content_hash=excluded.content_hash,
                  updated_at=datetime('now')
                """,
                (
                    qid,
                    track_id,
                    exam_code,
                    row["domain_id"],
                    row["task_id"],
                    row["task_code"],
                    row["question_type"],
                    row["cognitive_level"],
                    row["difficulty_band"],
                    row["bank_pool"],
                    row["authoring_status"],
                    row["authoring_version"],
                    _json(row["concepts"]),
                    _json(row["trap_tags"]),
                    _json(row["distractor_rationales"]),
                    _json(row["source_refs"]),
                    row["source_verified_at"] or None,
                    row["content_hash"],
                ),
            )
            conn.execute(
                """
                INSERT INTO question_skill_map(
                  question_id, track_id, domain_id, skill_id, confidence, evidence_json, reviewed
                ) VALUES (?, ?, ?, ?, 1.0, ?, 1)
                ON CONFLICT(question_id, skill_id) DO UPDATE SET
                  track_id=excluded.track_id,
                  domain_id=excluded.domain_id,
                  confidence=1.0,
                  evidence_json=excluded.evidence_json,
                  reviewed=1,
                  updated_at=datetime('now')
                """,
                (
                    qid,
                    track_id,
                    row["domain_id"],
                    row["task_id"],
                    _json({"source": "private_question_bank", "task_code": row["task_code"], "content_hash": row["content_hash"]}),
                ),
            )
            conn.execute(
                "INSERT OR IGNORE INTO question_exposure_stats(question_id) VALUES (?)",
                (qid,),
            )
            imported += 1
        conn.execute(
            """
            INSERT INTO question_bank_imports(source_name, track_id, bank_version, payload_hash, question_count, imported_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
            """,
            (source_name, track_id, bank_version, payload_hash, imported),
        )
    return {"dry_run": False, "imported": imported, **validation["coverage"]}


def import_question_bank_file(path: Path, *, dry_run: bool = False) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return import_question_bank_payload(payload, source_name=path.name, dry_run=dry_run)


def import_question_bank_directory(path: Path | None = None, *, dry_run: bool = False) -> dict[str, Any]:
    root = (path or PRIVATE_QUESTION_BANK_DIR).expanduser()
    if not root.exists():
        return {"directory": str(root), "files": 0, "imported": 0, "results": []}
    results = []
    imported = 0
    for file in sorted(root.glob("*.json")):
        result = import_question_bank_file(file, dry_run=dry_run)
        results.append({"file": file.name, **result})
        imported += int(result.get("imported") or 0)
    return {"directory": str(root), "files": len(results), "imported": imported, "results": results}


def allowed_pools_for_membership(membership: dict[str, Any], mode: str) -> tuple[str, ...]:
    plan = plan_details(membership.get("plan_code"), membership.get("tier") or "free")
    normalized = str(mode or "drill").strip().lower().replace("_", "-")
    if plan["code"] == "exam_pack_35":
        if normalized in {"full-mock", "lifetime-practice", "source-exam"}:
            return ("mock_reserved", "practice")
        return ("practice", "diagnostic", "free")
    if plan["tier"] == "free":
        if normalized == "weekly-mock":
            return ("free",)
        if normalized == "diagnostic":
            return ("diagnostic", "free")
        return ("free",)
    if normalized in {"quick-mock", "full-mock", "lifetime-practice", "exam"}:
        return ("mock_reserved", "practice")
    if normalized == "diagnostic":
        return ("diagnostic", "practice", "free")
    return ("practice", "free")


def filter_rows_for_entitlement(
    rows: list[dict[str, Any]],
    membership: dict[str, Any],
    mode: str,
    count: int,
) -> list[dict[str, Any]]:
    allowed = allowed_pools_for_membership(membership, mode)
    managed: list[dict[str, Any]] = []
    fallback: list[dict[str, Any]] = []
    for row in rows:
        pool = str(row.get("bank_pool") or "")
        status = str(row.get("authoring_status") or "")
        if pool:
            if status == "active" and pool in allowed:
                managed.append(row)
        else:
            fallback.append(row)
    # Once the private bank has enough eligible material for a sitting, do not
    # dilute it with generated fallback questions. During staged authoring the
    # old canonical bank keeps CI/dev functional without becoming commercial content.
    return managed if len(managed) >= count else [*managed, *fallback]


def _largest_remainder(weights: list[tuple[str, float]], count: int) -> dict[str, int]:
    raw = [(key, count * weight / 100.0) for key, weight in weights]
    base = {key: int(math.floor(value)) for key, value in raw}
    remainder = count - sum(base.values())
    order = sorted(raw, key=lambda item: (item[1] - math.floor(item[1]), item[1]), reverse=True)
    for key, _ in order[:remainder]:
        base[key] += 1
    return base


def domain_targets(domains: list[dict[str, Any]], count: int, mode: str) -> dict[str, int]:
    normalized = str(mode or "").strip().lower().replace("_", "-")
    exact = MODE_DOMAIN_COUNTS.get(normalized)
    if exact and sum(exact.values()) == count:
        return dict(exact)
    return _largest_remainder([(str(domain.get("id")), float(domain.get("weight") or 0)) for domain in domains], count)


def difficulty_targets(count: int, mode: str) -> dict[str, int]:
    normalized = str(mode or "diagnostic").strip().lower().replace("_", "-")
    ratios = MODE_DIFFICULTY_RATIOS.get(normalized, MODE_DIFFICULTY_RATIOS["diagnostic"])
    return _largest_remainder([(key, value * 100.0) for key, value in ratios.items()], count)


def _difficulty_band(row: dict[str, Any]) -> str:
    managed = str(row.get("difficulty_band") or "")
    if managed in ALLOWED_DIFFICULTY_BANDS:
        return managed
    legacy = str(row.get("difficulty") or "medium").lower()
    return {"easy": "foundation", "medium": "applied", "hard": "exam"}.get(legacy, "applied")


def _pool_rank(row: dict[str, Any], mode: str) -> int:
    normalized = str(mode or "drill").strip().lower().replace("_", "-")
    pool = str(row.get("bank_pool") or "")
    if normalized in {"quick-mock", "full-mock", "lifetime-practice", "exam"}:
        order = {"mock_reserved": 0, "practice": 1, "free": 2, "diagnostic": 3, "": 5}
    elif normalized == "diagnostic":
        order = {"diagnostic": 0, "practice": 1, "free": 2, "": 5}
    else:
        order = {"practice": 0, "free": 1, "diagnostic": 2, "": 5}
    return order.get(pool, 6)


def question_exposure_rank(row: dict[str, Any], mode: str) -> tuple[Any, ...]:
    managed_rank = 0 if row.get("bank_pool") else 1
    seen = int(row.get("candidate_served_count") or 0)
    last_seen = str(row.get("candidate_last_served") or "")
    global_seen = int(row.get("global_served_count") or 0)
    return (
        managed_rank,
        _pool_rank(row, mode),
        0 if seen == 0 else 1,
        seen,
        last_seen,
        global_seen,
    )


def _prepared(rows: Iterable[dict[str, Any]], mode: str) -> list[dict[str, Any]]:
    values = list(rows)
    random.shuffle(values)
    values.sort(key=lambda row: question_exposure_rank(row, mode))
    return values


def _select_domain_rows(rows: list[dict[str, Any]], count: int, mode: str) -> list[dict[str, Any]]:
    if count <= 0:
        return []
    difficulty_goal = difficulty_targets(count, mode)
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in _prepared(rows, mode):
        by_task[str(row.get("mapped_skill_id") or row.get("task_id") or "unmapped")].append(row)

    # First spread across task statements. For a 100-question Full Mock this
    # guarantees all 19 tasks are represented whenever the bank has coverage.
    for task_id in sorted(by_task):
        if len(selected) >= count:
            break
        candidates = by_task[task_id]
        preferred = sorted(
            candidates,
            key=lambda row: (
                0 if difficulty_goal.get(_difficulty_band(row), 0) > 0 else 1,
                question_exposure_rank(row, mode),
            ),
        )
        if preferred:
            row = preferred[0]
            selected.append(row)
            seen.add(row["id"])
            band = _difficulty_band(row)
            if difficulty_goal.get(band, 0) > 0:
                difficulty_goal[band] -= 1

    # Then satisfy the remaining difficulty mix as closely as possible.
    for band in ("foundation", "applied", "exam", "challenge"):
        need = max(0, difficulty_goal.get(band, 0))
        for row in _prepared([item for item in rows if _difficulty_band(item) == band], mode):
            if need <= 0 or len(selected) >= count:
                break
            if row["id"] in seen:
                continue
            selected.append(row)
            seen.add(row["id"])
            need -= 1

    for row in _prepared(rows, mode):
        if len(selected) >= count:
            break
        if row["id"] not in seen:
            selected.append(row)
            seen.add(row["id"])
    return selected[:count]


def select_blueprint_questions(
    rows: list[dict[str, Any]],
    domains: list[dict[str, Any]],
    count: int,
    mode: str,
) -> list[dict[str, Any]]:
    targets = domain_targets(domains, count, mode)
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        domain_id = str(row.get("mapped_domain_id") or row.get("domain_id") or "")
        if domain_id:
            buckets[domain_id].append(row)
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for domain in domains:
        domain_id = str(domain.get("id") or "")
        target = int(targets.get(domain_id, 0))
        for row in _select_domain_rows(buckets.get(domain_id, []), target, mode):
            if row["id"] not in seen:
                selected.append(row)
                seen.add(row["id"])
    for row in _prepared(rows, mode):
        if len(selected) >= count:
            break
        if row["id"] not in seen:
            selected.append(row)
            seen.add(row["id"])
    return selected[:count]


def record_questions_served(
    candidate_id: int,
    questions: list[dict[str, Any]],
    *,
    mode: str,
    session_id: int | None = None,
) -> None:
    if not questions:
        return
    with connect() as conn:
        for row in questions:
            question_id = str(row.get("id") or "")
            if not question_id:
                continue
            meta = conn.execute(
                "SELECT bank_pool, authoring_version FROM question_bank_metadata WHERE question_id=?",
                (question_id,),
            ).fetchone()
            pool = str(meta["bank_pool"] if meta else row.get("bank_pool") or "fallback")
            version = str(meta["authoring_version"] if meta else "legacy")
            conn.execute(
                """
                INSERT INTO candidate_question_history(
                  candidate_id, question_id, session_id, mode, pool, served_at, question_version
                ) VALUES (?, ?, ?, ?, ?, datetime('now'), ?)
                """,
                (candidate_id, question_id, session_id, mode, pool, version),
            )
            conn.execute(
                """
                INSERT INTO question_exposure_stats(question_id, served_count, last_served_at)
                VALUES (?, 1, datetime('now'))
                ON CONFLICT(question_id) DO UPDATE SET
                  served_count=question_exposure_stats.served_count + 1,
                  last_served_at=datetime('now')
                """,
                (question_id,),
            )


def attach_recent_serves_to_session(candidate_id: int, question_ids: list[str], mode: str, session_id: int) -> None:
    if not question_ids:
        return
    with connect() as conn:
        for question_id in question_ids:
            row = conn.execute(
                """
                SELECT id FROM candidate_question_history
                WHERE candidate_id=? AND question_id=? AND mode=? AND session_id IS NULL
                ORDER BY id DESC LIMIT 1
                """,
                (candidate_id, question_id, mode),
            ).fetchone()
            if row:
                conn.execute("UPDATE candidate_question_history SET session_id=? WHERE id=?", (session_id, row["id"]))


def record_question_answer(
    candidate_id: int,
    question_id: str,
    *,
    selected: list[int],
    correct: bool,
    response_time_ms: int | None = None,
    confidence: int | None = None,
) -> None:
    with connect() as conn:
        history = conn.execute(
            """
            SELECT id FROM candidate_question_history
            WHERE candidate_id=? AND question_id=? AND answered_at IS NULL
            ORDER BY id DESC LIMIT 1
            """,
            (candidate_id, question_id),
        ).fetchone()
        if history:
            conn.execute(
                """
                UPDATE candidate_question_history
                SET answered_at=datetime('now'), selected_json=?, correct=?, response_time_ms=?, confidence=?
                WHERE id=?
                """,
                (_json(sorted(set(selected))), int(correct), response_time_ms, confidence, history["id"]),
            )
        conn.execute(
            """
            INSERT INTO question_exposure_stats(question_id, correct_count, incorrect_count)
            VALUES (?, ?, ?)
            ON CONFLICT(question_id) DO UPDATE SET
              correct_count=question_exposure_stats.correct_count + excluded.correct_count,
              incorrect_count=question_exposure_stats.incorrect_count + excluded.incorrect_count
            """,
            (question_id, int(correct), int(not correct)),
        )


def question_review_metadata(question_id: str) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT distractor_rationales_json, source_refs_json, concepts_json, trap_tags_json,
                   question_type, cognitive_level, difficulty_band, task_code
            FROM question_bank_metadata WHERE question_id=?
            """,
            (question_id,),
        ).fetchone()
    if not row:
        return {}
    return {
        "distractor_rationales": json_list(row["distractor_rationales_json"]),
        "source_refs": json_list(row["source_refs_json"]),
        "concepts": json_list(row["concepts_json"]),
        "trap_tags": json_list(row["trap_tags_json"]),
        "question_type": row["question_type"],
        "cognitive_level": row["cognitive_level"],
        "difficulty_band": row["difficulty_band"],
        "task_code": row["task_code"],
    }


def candidate_was_served_question(candidate_id: int, question_id: str) -> bool:
    with connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM candidate_question_history WHERE candidate_id=? AND question_id=? LIMIT 1",
            (candidate_id, question_id),
        ).fetchone()
    return bool(row)


def managed_question(question_id: str) -> bool:
    with connect() as conn:
        return bool(conn.execute("SELECT 1 FROM question_bank_metadata WHERE question_id=?", (question_id,)).fetchone())


def exam_pack_set_question_ids(candidate_id: int, track_id: str, set_kind: str) -> list[str]:
    with connect() as conn:
        row = conn.execute(
            "SELECT id FROM candidate_exam_pack_sets WHERE candidate_id=? AND track_id=? AND set_kind=?",
            (candidate_id, track_id, set_kind),
        ).fetchone()
        if not row:
            return []
        return [
            item["question_id"]
            for item in conn.execute(
                "SELECT question_id FROM candidate_exam_pack_set_questions WHERE set_id=? ORDER BY position",
                (row["id"],),
            )
        ]


def store_exam_pack_set(candidate_id: int, track_id: str, set_kind: str, question_ids: list[str]) -> None:
    if not question_ids:
        return
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        existing = conn.execute(
            "SELECT id FROM candidate_exam_pack_sets WHERE candidate_id=? AND track_id=? AND set_kind=?",
            (candidate_id, track_id, set_kind),
        ).fetchone()
        if existing:
            return
        cursor = conn.execute(
            "INSERT INTO candidate_exam_pack_sets(candidate_id, track_id, set_kind) VALUES (?, ?, ?)",
            (candidate_id, track_id, set_kind),
        )
        set_id = int(cursor.lastrowid)
        for position, question_id in enumerate(question_ids, start=1):
            conn.execute(
                "INSERT INTO candidate_exam_pack_set_questions(set_id, question_id, position) VALUES (?, ?, ?)",
                (set_id, question_id, position),
            )


def bank_status(track_id: str = "snowpro-core") -> dict[str, Any]:
    cert, domains, tasks = _certification_index(track_id)
    with connect() as conn:
        active_rows = [
            dict(row)
            for row in conn.execute(
                """
                SELECT domain_id, task_id, difficulty_band, bank_pool, COUNT(*) AS count
                FROM question_bank_metadata
                WHERE certification_id=? AND authoring_status='active'
                GROUP BY domain_id, task_id, difficulty_band, bank_pool
                """,
                (track_id,),
            )
        ]
        imports = int(
            conn.execute("SELECT COUNT(*) AS count FROM question_bank_imports WHERE track_id=?", (track_id,)).fetchone()["count"]
            or 0
        )
    by_domain: dict[str, int] = defaultdict(int)
    by_task: dict[str, int] = defaultdict(int)
    by_pool: dict[str, int] = defaultdict(int)
    by_difficulty: dict[str, int] = defaultdict(int)
    for row in active_rows:
        count = int(row["count"] or 0)
        by_domain[row["domain_id"]] += count
        by_task[row["task_id"]] += count
        by_pool[row["bank_pool"]] += count
        by_difficulty[row["difficulty_band"]] += count
    active_total = sum(by_task.values())
    target = MILESTONE_TARGETS["internal_mvp"]
    domain_target = _largest_remainder(
        [(domain_id, float(domain.get("weight") or 0)) for domain_id, domain in domains.items()],
        target,
    )
    return {
        "track_id": track_id,
        "exam_code": cert.get("exam_code"),
        "active_questions": active_total,
        "imports": imports,
        "tasks_covered": sum(1 for task_id in tasks if by_task.get(task_id, 0) > 0),
        "tasks_total": len(tasks),
        "by_domain": dict(sorted(by_domain.items())),
        "by_task": dict(sorted(by_task.items())),
        "by_pool": dict(sorted(by_pool.items())),
        "by_difficulty": dict(sorted(by_difficulty.items())),
        "milestones": {
            key: {"target": value, "remaining": max(0, value - active_total), "reached": active_total >= value}
            for key, value in MILESTONE_TARGETS.items()
        },
        "internal_mvp_domain_targets": domain_target,
        "source_directory": str(PRIVATE_QUESTION_BANK_DIR),
    }
