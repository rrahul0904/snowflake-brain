#!/usr/bin/env python3
"""Validate Snowflake certification question/solution corpus integrity.

Standard-library-only validation for the evidence-first certification corpus. Checks
parseability, IDs, pairing, answer keys, Snowflake-owned sources, blueprint objectives,
5,000-item authoring allocations, release-aware lifecycle metadata, duplicate prompts,
and optional final 5,000-per-exam completion gates.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
BANK_ROOT = ROOT / "data" / "question-banks"
BLUEPRINT_PATH = BANK_ROOT / "blueprints" / "2026-10-07.json"
ALLOCATION_PATH = BANK_ROOT / "coverage" / "authoring-targets.5000.json"
ALLOWED_SOURCE_HOST_SUFFIXES = ("snowflake.com", "snowflakecomputing.com")
MIN_PER_EXAM = 5000


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_jsonl_files(kind: str):
    records = []
    errors = []
    patterns = [f"**/{kind}*.jsonl", f"**/{kind}/*.jsonl"]
    seen_paths = set()
    for pattern in patterns:
        for path in BANK_ROOT.glob(pattern):
            if path in seen_paths:
                continue
            seen_paths.add(path)
            with path.open("r", encoding="utf-8") as handle:
                for lineno, raw in enumerate(handle, 1):
                    line = raw.strip()
                    if not line:
                        continue
                    try:
                        value = json.loads(line)
                    except json.JSONDecodeError as exc:
                        errors.append(f"{path.relative_to(ROOT)}:{lineno}: invalid JSON: {exc}")
                        continue
                    value["__path"] = str(path.relative_to(ROOT))
                    value["__line"] = lineno
                    records.append(value)
    return records, errors


def source_is_official(url: str) -> bool:
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return False
    return any(host == suffix or host.endswith("." + suffix) for suffix in ALLOWED_SOURCE_HOST_SUFFIXES)


def normalize_prompt(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def loc(record) -> str:
    return f"{record.get('__path', '?')}:{record.get('__line', '?')}"


def validate_authoring_allocations(tracked, objective_sets, errors):
    if not ALLOCATION_PATH.exists():
        errors.append(f"missing allocation matrix: {ALLOCATION_PATH.relative_to(ROOT)}")
        return

    allocation = load_json(ALLOCATION_PATH)
    if allocation.get("target_per_exam") != MIN_PER_EXAM:
        errors.append(
            f"allocation target_per_exam is {allocation.get('target_per_exam')}; expected {MIN_PER_EXAM}"
        )

    exam_allocations = allocation.get("exams", {})
    extras = sorted(set(exam_allocations) - set(tracked))
    if extras:
        errors.append(f"allocation matrix contains untracked exams: {', '.join(extras)}")

    for code in tracked:
        item = exam_allocations.get(code)
        if not item:
            errors.append(f"allocation matrix missing tracked exam {code}")
            continue
        rows = item.get("allocations", [])
        total = sum(row.get("target", 0) for row in rows)
        if total != MIN_PER_EXAM:
            errors.append(f"{code}: authoring allocations sum to {total}, expected {MIN_PER_EXAM}")
        objectives = [row.get("objective") for row in rows]
        if len(objectives) != len(set(objectives)):
            errors.append(f"{code}: duplicate objective in authoring allocation matrix")
        actual = set(objectives)
        expected = objective_sets[code]
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        if missing:
            errors.append(f"{code}: allocation missing blueprint objectives: {missing}")
        if extra:
            errors.append(f"{code}: allocation has non-blueprint objectives: {extra}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--require-target",
        action="store_true",
        help="fail unless every tracked exam has at least 5,000 questions and paired solutions",
    )
    args = parser.parse_args()

    errors = []
    warnings = []

    blueprint = load_json(BLUEPRINT_PATH)
    tracked = {item["exam_code"]: item for item in blueprint["certifications"]}
    objective_sets = {code: set(item["objectives"]) for code, item in tracked.items()}
    validate_authoring_allocations(tracked, objective_sets, errors)

    questions, parse_errors_q = load_jsonl_files("questions")
    solutions, parse_errors_s = load_jsonl_files("solutions")
    errors.extend(parse_errors_q)
    errors.extend(parse_errors_s)

    q_by_id = {}
    s_by_id = {}
    prompt_seen = {}
    q_counts = Counter()
    s_counts = Counter()

    required_q = {
        "id", "certification_id", "exam_code", "blueprint_objective", "topic",
        "question_type", "difficulty", "prompt", "options", "answer_key", "sources",
        "as_of", "status",
    }
    required_s = {
        "question_id", "certification_id", "exam_code", "answer_key", "explanation",
        "reasoning", "distractor_analysis", "exam_trap", "sources", "as_of", "status",
    }

    for q in questions:
        missing = sorted(required_q - set(q))
        if missing:
            errors.append(f"{loc(q)}: question missing fields: {', '.join(missing)}")
            continue
        qid = q["id"]
        if qid in q_by_id:
            errors.append(f"{loc(q)}: duplicate question id {qid}")
        q_by_id[qid] = q
        code = q["exam_code"]
        q_counts[code] += 1
        if code not in tracked:
            errors.append(f"{loc(q)}: untracked exam code {code}")
        elif q["blueprint_objective"] not in objective_sets[code]:
            errors.append(
                f"{loc(q)}: objective is not in locked blueprint for {code}: {q['blueprint_objective']!r}"
            )
        keys = [str(option.get("key")) for option in q.get("options", [])]
        if len(keys) != len(set(keys)):
            errors.append(f"{loc(q)}: duplicate option keys")
        for answer in q.get("answer_key", []):
            if answer not in keys:
                errors.append(f"{loc(q)}: answer key {answer!r} is not an option key")
        if not q.get("sources"):
            errors.append(f"{loc(q)}: question has no source")
        for source in q.get("sources", []):
            if not source_is_official(source.get("url", "")):
                errors.append(f"{loc(q)}: non-Snowflake source URL: {source.get('url')}")

        if "release-aware" in q.get("tags", []):
            if not q.get("lifecycle_note"):
                errors.append(f"{loc(q)}: release-aware question is missing lifecycle_note")
            if not any(source.get("type") == "official_announcement" for source in q.get("sources", [])):
                errors.append(f"{loc(q)}: release-aware question must cite an official_announcement source")

        normalized = normalize_prompt(q["prompt"])
        if normalized in prompt_seen:
            errors.append(
                f"{loc(q)}: exact normalized prompt duplicate of {prompt_seen[normalized]}"
            )
        else:
            prompt_seen[normalized] = qid

    for s in solutions:
        missing = sorted(required_s - set(s))
        if missing:
            errors.append(f"{loc(s)}: solution missing fields: {', '.join(missing)}")
            continue
        qid = s["question_id"]
        if qid in s_by_id:
            errors.append(f"{loc(s)}: duplicate solution for question {qid}")
        s_by_id[qid] = s
        code = s["exam_code"]
        s_counts[code] += 1
        if code not in tracked:
            errors.append(f"{loc(s)}: untracked exam code {code}")
        if not s.get("sources"):
            errors.append(f"{loc(s)}: solution has no source")
        for source in s.get("sources", []):
            if not source_is_official(source.get("url", "")):
                errors.append(f"{loc(s)}: non-Snowflake source URL: {source.get('url')}")

    for qid, q in q_by_id.items():
        solution = s_by_id.get(qid)
        if not solution:
            errors.append(f"{loc(q)}: no paired solution for {qid}")
            continue
        if solution["exam_code"] != q["exam_code"]:
            errors.append(f"{loc(solution)}: exam_code mismatch for {qid}")
        if solution["certification_id"] != q["certification_id"]:
            errors.append(f"{loc(solution)}: certification_id mismatch for {qid}")
        if solution["answer_key"] != q["answer_key"]:
            errors.append(f"{loc(solution)}: solution answer_key differs from question for {qid}")

    orphaned = sorted(set(s_by_id) - set(q_by_id))
    for qid in orphaned:
        errors.append(f"{loc(s_by_id[qid])}: orphan solution with no question: {qid}")

    for code in tracked:
        if q_counts[code] == 0:
            errors.append(f"no questions found for tracked exam {code}")
        if s_counts[code] == 0:
            errors.append(f"no solutions found for tracked exam {code}")
        if q_counts[code] != s_counts[code]:
            errors.append(
                f"count mismatch for {code}: {q_counts[code]} questions vs {s_counts[code]} solutions"
            )
        if args.require_target and q_counts[code] < MIN_PER_EXAM:
            errors.append(f"{code}: only {q_counts[code]} questions; target is {MIN_PER_EXAM}")
        elif q_counts[code] < MIN_PER_EXAM:
            warnings.append(f"{code}: {q_counts[code]}/{MIN_PER_EXAM} questions")

    print("Snowflake question-bank validation")
    print(f"Tracked exams: {len(tracked)}")
    print(f"Questions: {len(questions)}")
    print(f"Solutions: {len(solutions)}")
    print(f"Authoring allocation target: {MIN_PER_EXAM} per exam")
    print("Counts by exam:")
    for code in tracked:
        print(f"  {code}: {q_counts[code]} questions / {s_counts[code]} solutions")

    if warnings:
        print("\nProgress warnings:")
        for warning in warnings:
            print(f"  WARN: {warning}")

    if errors:
        print("\nValidation errors:", file=sys.stderr)
        for error in errors:
            print(f"  ERROR: {error}", file=sys.stderr)
        return 1

    print("\nPASS: structural, blueprint, allocation, pairing, and freshness checks succeeded.")
    if not args.require_target:
        print("Target count gate was not requested; run with --require-target for final release gating.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
