#!/usr/bin/env python3
"""Privacy-safe structural audit for a governed private question-bank artifact.

The script never prints stems, options, rationales, source titles, or question IDs.
Only aggregate counts, hashes, and bias/quality statistics are emitted.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

EXPECTED_SHA256 = "da57f636a57180631448fda79cfdcad2acf8e38ae2f381ea891a8cea91e704c5"
EXPECTED_VERSION = "2026-08-14-beta-1200-v2"
EXPECTED_TOTAL = 1200
EXPECTED_POOLS = {"free": 216, "practice": 504, "mock_reserved": 360, "diagnostic": 120}
EXPECTED_DOMAINS = {
    "features-architecture": 372,
    "account-governance": 240,
    "loading-connectivity": 216,
    "performance-transformation": 252,
    "data-collaboration": 120,
}
EXPECTED_TASKS = {
    "1.1": 62, "1.2": 62, "1.3": 62, "1.4": 62, "1.5": 62, "1.6": 62,
    "2.1": 80, "2.2": 80, "2.3": 80,
    "3.1": 72, "3.2": 72, "3.3": 72,
    "4.1": 63, "4.2": 63, "4.3": 63, "4.4": 63,
    "5.1": 40, "5.2": 40, "5.3": 40,
}
EXPECTED_DIFFICULTY = {"foundation": 180, "exam": 480, "applied": 420, "challenge": 120}
EXPECTED_TYPES = {
    "standard_mcq": 304,
    "scenario": 152,
    "best_answer": 304,
    "troubleshooting": 152,
    "architecture_decision": 146,
    "multi_select": 142,
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized_hash(value: str) -> str:
    normalized = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", value.lower())).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def longest_option_positions(options: list[str]) -> set[int]:
    if not options:
        return set()
    lengths = [len(re.sub(r"\s+", " ", str(option)).strip()) for option in options]
    maximum = max(lengths)
    return {index for index, length in enumerate(lengths) if length == maximum}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    artifact = args.artifact.expanduser().resolve()
    if not artifact.is_file():
        print(json.dumps({"status": "BLOCKED", "reason": "artifact_not_found"}, sort_keys=True))
        return 2

    digest = sha256_file(artifact)
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    questions: list[dict[str, Any]] = list(payload.get("questions") or [])

    pools: collections.Counter[str] = collections.Counter()
    domains: collections.Counter[str] = collections.Counter()
    tasks: collections.Counter[str] = collections.Counter()
    difficulties: collections.Counter[str] = collections.Counter()
    types: collections.Counter[str] = collections.Counter()
    correct_positions: collections.Counter[str] = collections.Counter()
    stem_hashes: collections.Counter[str] = collections.Counter()

    malformed = 0
    duplicate_ids = 0
    rationale_missing = 0
    distractor_rationale_incomplete = 0
    source_missing = 0
    stale_source_date_missing = 0
    correct_is_longest = 0
    single_choice = 0
    multi_select_valid = 0
    seen_ids: set[str] = set()

    for question in questions:
        qid = str(question.get("id") or "")
        if not qid or qid in seen_ids:
            duplicate_ids += 1
        seen_ids.add(qid)
        pools[str(question.get("bank_pool") or "")] += 1
        domains[str(question.get("domain_id") or "")] += 1
        tasks[str(question.get("task_code") or "")] += 1
        difficulties[str(question.get("difficulty_band") or "")] += 1
        qtype = str(question.get("question_type") or "")
        types[qtype] += 1

        stem = str(question.get("question") or "")
        stem_hashes[normalized_hash(stem)] += 1
        options = list(question.get("options") or [])
        correct = question.get("correct_options") or []
        if not stem or len(options) < 2 or not isinstance(correct, list) or not correct:
            malformed += 1
            continue
        if any(not isinstance(index, int) or index < 0 or index >= len(options) for index in correct):
            malformed += 1
            continue
        if any(not str(option).strip() for option in options):
            malformed += 1

        if not str(question.get("correct_rationale") or "").strip():
            rationale_missing += 1
        distractors = list(question.get("distractor_rationales") or [])
        if len(distractors) != len(options) or any(not str(value).strip() for value in distractors):
            distractor_rationale_incomplete += 1
        refs = list(question.get("source_refs") or [])
        if not refs or any(not str(ref.get("url") or "").startswith("https://") for ref in refs if isinstance(ref, dict)):
            source_missing += 1
        if not question.get("source_verified_at"):
            stale_source_date_missing += 1

        if len(correct) == 1:
            single_choice += 1
            position = correct[0]
            correct_positions[str(position)] += 1
            if position in longest_option_positions([str(option) for option in options]):
                correct_is_longest += 1
        elif qtype == "multi_select" and len(correct) >= 2:
            multi_select_valid += 1

    duplicate_normalized_stems = sum(count - 1 for count in stem_hashes.values() if count > 1)
    longest_pct = round((correct_is_longest / single_choice * 100), 2) if single_choice else 0.0
    positional_pct = {
        key: round(value / single_choice * 100, 2) if single_choice else 0.0
        for key, value in sorted(correct_positions.items())
    }

    errors: list[str] = []
    checks = [
        (payload.get("schema_version") == "snowflake-question-bank-v1", "schema_version"),
        (payload.get("bank_version") == EXPECTED_VERSION, "bank_version"),
        (payload.get("track_id") == "snowpro-core", "track_id"),
        (payload.get("exam_code") == "COF-C03", "exam_code"),
        (digest == EXPECTED_SHA256, "sha256"),
        (len(questions) == EXPECTED_TOTAL, "total_questions"),
        (dict(pools) == EXPECTED_POOLS, "pool_counts"),
        (dict(domains) == EXPECTED_DOMAINS, "domain_counts"),
        (dict(tasks) == EXPECTED_TASKS, "task_counts"),
        (dict(difficulties) == EXPECTED_DIFFICULTY, "difficulty_counts"),
        (dict(types) == EXPECTED_TYPES, "question_type_counts"),
        (duplicate_ids == 0, "duplicate_ids"),
        (malformed == 0, "malformed_questions"),
        (rationale_missing == 0, "missing_correct_rationales"),
        (distractor_rationale_incomplete == 0, "incomplete_distractor_rationales"),
        (source_missing == 0, "missing_source_refs"),
        (stale_source_date_missing == 0, "missing_source_verified_at"),
    ]
    errors.extend(label for passed, label in checks if not passed)

    # Bias signals are reported rather than automatically "fixed". Thresholds
    # deliberately flag strong structural bias while avoiding content leakage.
    position_values = list(positional_pct.values())
    max_position_pct = max(position_values, default=0.0)
    bias_warnings: list[str] = []
    if max_position_pct > 35.0:
        bias_warnings.append("correct_option_position_concentration")
    if longest_pct > 45.0:
        bias_warnings.append("correct_answer_length_signal")
    if duplicate_normalized_stems > 0:
        bias_warnings.append("duplicate_normalized_stems")

    report = {
        "status": "PASS" if not errors and (not args.strict or not bias_warnings) else "FAIL",
        "artifact_sha256": digest,
        "bank_version": payload.get("bank_version"),
        "total_questions": len(questions),
        "pool_counts": dict(sorted(pools.items())),
        "domain_counts": dict(sorted(domains.items())),
        "task_counts": dict(sorted(tasks.items())),
        "difficulty_counts": dict(sorted(difficulties.items())),
        "question_type_counts": dict(sorted(types.items())),
        "single_choice_questions": single_choice,
        "multi_select_valid": multi_select_valid,
        "correct_option_position_pct": positional_pct,
        "correct_answer_is_longest_pct": longest_pct,
        "duplicate_normalized_stem_count": duplicate_normalized_stems,
        "duplicate_id_count": duplicate_ids,
        "malformed_question_count": malformed,
        "missing_correct_rationale_count": rationale_missing,
        "incomplete_distractor_rationale_count": distractor_rationale_incomplete,
        "missing_source_ref_count": source_missing,
        "missing_source_verified_at_count": stale_source_date_missing,
        "errors": errors,
        "bias_warnings": bias_warnings,
        "privacy": "aggregate-only; no question text, options, rationales, source titles, or question IDs emitted",
    }

    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)
    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(rendered + "\n", encoding="utf-8")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
