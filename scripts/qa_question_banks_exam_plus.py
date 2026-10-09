#!/usr/bin/env python3
"""Audit Snowflake certification banks against the Exam+ specialist standard.

This is intentionally stricter than source/structural validation. It measures the
current corpus against certification-level difficulty targets and specialist review
state without pretending automated checks are human/SME approval.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
BANK = ROOT / "data" / "question-banks"
TEAMS = BANK / "vetting" / "specialist-teams.v1.json"
TRACKER = BANK / "vetting" / "specialist-review-tracker.v1.json"
DEFAULT_REPORT = BANK / "generated" / "exam-plus-readiness-report.json"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(kind: str):
    rows = []
    seen = set()
    for pattern in (f"**/{kind}*.jsonl", f"**/{kind}/*.jsonl"):
        for path in BANK.glob(pattern):
            if path in seen:
                continue
            seen.add(path)
            for raw in path.read_text(encoding="utf-8").splitlines():
                if raw.strip():
                    rows.append(json.loads(raw))
    return rows


def official_source(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return (
        host == "snowflake.com"
        or host.endswith(".snowflake.com")
        or host == "snowflakecomputing.com"
        or host.endswith(".snowflakecomputing.com")
    )


def words(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text or ""))


def tag_value(record: dict, prefix: str) -> str | None:
    for tag in record.get("tags", []):
        if isinstance(tag, str) and tag.startswith(prefix):
            return tag.split(":", 1)[1]
    return None


def target_counts(mix: dict, total: int) -> dict:
    # Percentages in specialist-teams.v1.json intentionally sum to 100.
    return {name: int(round(total * pct / 100.0)) for name, pct in mix.items()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument(
        "--require-complete",
        action="store_true",
        help="fail unless every certification has completed specialist disposition and meets Exam+ targets",
    )
    args = parser.parse_args()

    teams_doc = load_json(TEAMS)
    tracker = load_json(TRACKER)
    teams = teams_doc["teams"]
    questions = load_jsonl("questions")
    solutions = load_jsonl("solutions")
    s_by_id = {s["question_id"]: s for s in solutions}

    q_by_exam = defaultdict(list)
    for q in questions:
        q_by_exam[q["exam_code"]].append(q)

    report = {
        "as_of": teams_doc["as_of"],
        "standard": "data/question-banks/vetting/exam-plus-quality-standard.md",
        "mode": "specialist_readiness",
        "important": "Automated readiness is not specialist approval. exam_plus_verified remains zero until blind specialist review records a promotion.",
        "global": {},
        "by_exam": {},
    }

    total_source_blockers = 0
    total_solution_blockers = 0
    total_foundation_excess = 0
    total_pending = 0
    total_pairs = 0

    for code, team in teams.items():
        rows = q_by_exam.get(code, [])
        total = len(rows)
        total_pairs += total
        diff = Counter(q.get("difficulty", "unknown") for q in rows)
        qtypes = Counter(q.get("question_type", "unknown") for q in rows)
        archetypes = Counter(tag_value(q, "archetype:") or "curated" for q in rows)

        applied = 0
        source_blockers = 0
        solution_blockers = 0
        ambiguity_risk = 0
        rich_solution = 0

        for q in rows:
            s = s_by_id.get(q["id"])
            if not q.get("sources") or any(not official_source(src.get("url", "")) for src in q.get("sources", [])):
                source_blockers += 1

            if not s:
                solution_blockers += 1
                continue

            option_keys = {str(o.get("key")) for o in q.get("options", [])}
            wrong_keys = option_keys - set(q.get("answer_key", []))
            distractor_keys = {str(x.get("key")) for x in s.get("distractor_analysis", [])}
            solution_ok = (
                words(s.get("explanation", "")) >= 8
                and words(s.get("reasoning", "")) >= 16
                and words(s.get("exam_trap", "")) >= 6
                and wrong_keys == distractor_keys
                and bool(s.get("sources"))
            )
            if solution_ok:
                rich_solution += 1
            else:
                solution_blockers += 1

            arch = tag_value(q, "archetype:")
            if (
                q.get("question_type") in {"scenario", "architecture_decision", "troubleshooting", "sql_reasoning", "multi_select"}
                or arch in {"scenario", "architecture_decision", "troubleshooting", "operational", "distinction"}
            ):
                applied += 1

            prompt = (q.get("prompt") or "").lower()
            # Heuristic only: these patterns are review flags, never automatic factual failures.
            if any(token in prompt for token in (" always ", " never ", " only ")) and q.get("question_type") == "single_select":
                ambiguity_risk += 1

        target = target_counts(team["difficulty_mix"], total or 5000)
        # The legacy corpus has foundation/exam/advanced. Treat legacy advanced only as
        # an Exam+ *candidate*, never as verified Exam+ content.
        foundation_excess = max(0, diff.get("foundation", 0) - target["foundation"])
        high_reasoning_target = target["exam_plus"] + target["expert_stretch"]
        legacy_advanced_candidate_gap = max(0, high_reasoning_target - diff.get("advanced", 0))
        applied_pct = (100.0 * applied / total) if total else 0.0
        rich_solution_pct = (100.0 * rich_solution / total) if total else 0.0

        specialist = tracker["by_exam"][code]
        pending = specialist["pending"]
        total_pending += pending
        total_foundation_excess += foundation_excess
        total_source_blockers += source_blockers
        total_solution_blockers += solution_blockers

        report["by_exam"][code] = {
            "name": team["name"],
            "level": team["level"],
            "pairs": total,
            "current_legacy_difficulty": dict(diff),
            "target_exam_plus_mix": target,
            "question_types": dict(qtypes),
            "archetypes": dict(archetypes),
            "applied_reasoning_items": applied,
            "applied_reasoning_percent": round(applied_pct, 2),
            "rich_solution_items": rich_solution,
            "rich_solution_percent": round(rich_solution_pct, 2),
            "source_blockers": source_blockers,
            "solution_blockers": solution_blockers,
            "heuristic_ambiguity_review_flags": ambiguity_risk,
            "foundation_items_above_new_ceiling": foundation_excess,
            "additional_high_reasoning_items_needed_if_every_legacy_advanced_item_passes_specialist_review": legacy_advanced_candidate_gap,
            "expert_stretch_target": target["expert_stretch"],
            "specialist_review": specialist,
            "exam_plus_complete": (
                pending == 0
                and source_blockers == 0
                and solution_blockers == 0
                and foundation_excess == 0
                and specialist["exam_plus_verified"] + specialist["expert_stretch_verified"] >= high_reasoning_target
            ),
        }

    report["global"] = {
        "pairs": total_pairs,
        "source_blockers": total_source_blockers,
        "solution_blockers": total_solution_blockers,
        "pairs_pending_specialist_disposition": total_pending,
        "foundation_items_above_new_ceilings": total_foundation_excess,
        "specialist_exam_parity_verified": tracker["global"]["exam_parity_verified"],
        "specialist_exam_plus_verified": tracker["global"]["exam_plus_verified"],
        "specialist_expert_stretch_verified": tracker["global"]["expert_stretch_verified"],
        "exam_plus_program_complete": all(x["exam_plus_complete"] for x in report["by_exam"].values()),
    }

    path = Path(args.report)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print("Snowflake Exam+ specialist readiness audit")
    print(f"Pairs: {total_pairs}")
    print(f"Source blockers: {total_source_blockers}")
    print(f"Solution completeness blockers: {total_solution_blockers}")
    print(f"Pending specialist dispositions: {total_pending}")
    print(f"Foundation items above new ceilings: {total_foundation_excess}")
    print(f"Exam+ program complete: {report['global']['exam_plus_program_complete']}")
    for code, item in report["by_exam"].items():
        print(
            f"  {code}: applied={item['applied_reasoning_percent']:.2f}% "
            f"rich_solution={item['rich_solution_percent']:.2f}% "
            f"foundation_excess={item['foundation_items_above_new_ceiling']} "
            f"pending={item['specialist_review']['pending']}"
        )

    if args.require_complete and not report["global"]["exam_plus_program_complete"]:
        print("FAIL: Exam+ specialist completion gate has not been met.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
