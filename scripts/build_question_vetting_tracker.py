#!/usr/bin/env python3
"""Build an auditable vetting tracker for every Snowflake certification question/solution pair."""
from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
BANK = ROOT / "data" / "question-banks"
GENERATED = BANK / "generated"
VETTING = BANK / "vetting"
EVIDENCE_PATH = VETTING / "concept-evidence.json"
OUT_DIR = GENERATED / "vetting"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(kind: str):
    rows = []
    seen = set()
    for pattern in (f"**/{kind}*.jsonl", f"**/{kind}/*.jsonl"):
        for path in BANK.glob(pattern):
            if path in seen or OUT_DIR in path.parents:
                continue
            seen.add(path)
            for raw in path.read_text(encoding="utf-8").splitlines():
                if raw.strip():
                    row = json.loads(raw)
                    row["__path"] = str(path.relative_to(ROOT))
                    rows.append(row)
    return rows


def norm(text):
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def concept_id(record):
    for tag in record.get("tags", []):
        if isinstance(tag, str) and tag.startswith("concept:"):
            return tag.split(":", 1)[1]
    return None


def archetype(record):
    for tag in record.get("tags", []):
        if isinstance(tag, str) and tag.startswith("archetype:"):
            return tag.split(":", 1)[1]
    return None


def official(url):
    host = (urlparse(url).hostname or "").lower()
    return host == "snowflake.com" or host.endswith(".snowflake.com") or host == "snowflakecomputing.com" or host.endswith(".snowflakecomputing.com")


def mechanical_issues(q, s):
    issues = []
    if not s:
        return ["missing_solution"]
    if q.get("answer_key") != s.get("answer_key"):
        issues.append("answer_key_mismatch")
    options = q.get("options", [])
    opt_by = {str(o.get("key")): o.get("text", "") for o in options}
    if len(opt_by) != len(options):
        issues.append("duplicate_option_key")
    if len(set(norm(v) for v in opt_by.values())) != len(opt_by):
        issues.append("duplicate_option_text")
    for answer in q.get("answer_key", []):
        if answer not in opt_by:
            issues.append("answer_missing_option")
    if q.get("question_type") != "multi_select" and len(q.get("answer_key", [])) != 1:
        issues.append("unexpected_multi_answer")
    if q.get("question_type") == "multi_select" and len(q.get("answer_key", [])) < 2:
        issues.append("invalid_multi_select")

    wrong = set(opt_by) - set(q.get("answer_key", []))
    da = s.get("distractor_analysis", [])
    da_keys = [x.get("key") for x in da]
    if set(da_keys) != wrong or len(da_keys) != len(set(da_keys)):
        issues.append("distractor_analysis_coverage")

    q_urls = {x.get("url") for x in q.get("sources", []) if x.get("url")}
    s_urls = {x.get("url") for x in s.get("sources", []) if x.get("url")}
    # Curated questions can include an exam/study-guide mapping URL in addition to the solution evidence URL.
    if not s_urls.issubset(q_urls):
        issues.append("solution_source_not_in_question_sources")
    if not q_urls or not s_urls:
        issues.append("missing_source")
    if any(not official(url) for url in q_urls | s_urls):
        issues.append("non_snowflake_source")

    if not q.get("blueprint_objective"):
        issues.append("missing_blueprint_objective")
    if not s.get("explanation"):
        issues.append("missing_explanation")
    if not s.get("reasoning"):
        issues.append("missing_reasoning")
    if not s.get("exam_trap"):
        issues.append("missing_exam_trap")

    cid = concept_id(q)
    arch = archetype(q)
    if cid and q.get("answer_key"):
        answer = q["answer_key"][0]
        correct = opt_by.get(answer, "")
        if arch in {"single_select", "distinction"}:
            if norm(correct) != norm(s.get("explanation")):
                issues.append("generated_fact_answer_drift")
        elif norm(correct) != norm(q.get("topic")):
            issues.append("generated_feature_answer_drift")

    if "source-class:release-aware" in q.get("tags", []) and not q.get("lifecycle_note"):
        issues.append("release_aware_missing_lifecycle")
    return sorted(set(issues))


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    evidence = load_json(EVIDENCE_PATH).get("concepts", {}) if EVIDENCE_PATH.exists() else {}
    questions = load_jsonl("questions")
    solutions = load_jsonl("solutions")
    s_by_id = {s["question_id"]: s for s in solutions}

    tracker_path = OUT_DIR / "question-vetting.csv"
    concept_path = OUT_DIR / "concept-vetting.csv"
    summary_path = OUT_DIR / "vetting-summary.json"

    summary = {
        "total_questions": len(questions),
        "total_solutions": len(solutions),
        "mechanical_pass": 0,
        "mechanical_hold": 0,
        "source_live_verified": 0,
        "source_live_review_pending": 0,
        "curated_manual_review_required": 0,
        "promotion_eligible": 0,
        "by_exam": {},
        "issue_counts": {},
        "concepts_live_verified": len(evidence),
    }
    issue_counts = Counter()
    exam_stats = defaultdict(lambda: Counter())
    concept_stats = defaultdict(lambda: Counter())

    fields = [
        "question_id", "exam_code", "certification_id", "blueprint_objective", "topic", "concept_id",
        "question_type", "difficulty", "question_status", "solution_status", "mechanical_status", "mechanical_issues",
        "source_status", "canonical_source_url", "source_verified_on", "manual_content_review", "promotion_eligible",
        "question_path", "solution_path"
    ]
    with tracker_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for q in sorted(questions, key=lambda x: (x.get("exam_code", ""), x.get("id", ""))):
            s = s_by_id.get(q["id"])
            issues = mechanical_issues(q, s)
            mechanical = "PASS" if not issues else "HOLD"
            cid = concept_id(q)
            ev = evidence.get(cid) if cid else None
            if ev and ev.get("status") == "live_verified":
                source_status = "LIVE_VERIFIED"
                canonical = ev.get("canonical_url")
                verified_on = ev.get("verified_on")
            elif cid:
                source_status = "LIVE_REVIEW_PENDING"
                canonical = (q.get("sources") or [{}])[0].get("url")
                verified_on = ""
            else:
                source_status = "CURATED_MANUAL_REVIEW_REQUIRED"
                canonical = (q.get("sources") or [{}])[0].get("url")
                verified_on = ""

            # Human/manual record review remains separate from automated checks.
            manual = "PENDING"
            eligible = mechanical == "PASS" and source_status == "LIVE_VERIFIED" and manual == "PASS"
            writer.writerow({
                "question_id": q["id"],
                "exam_code": q.get("exam_code"),
                "certification_id": q.get("certification_id"),
                "blueprint_objective": q.get("blueprint_objective"),
                "topic": q.get("topic"),
                "concept_id": cid or "",
                "question_type": q.get("question_type"),
                "difficulty": q.get("difficulty"),
                "question_status": q.get("status"),
                "solution_status": s.get("status") if s else "MISSING",
                "mechanical_status": mechanical,
                "mechanical_issues": ";".join(issues),
                "source_status": source_status,
                "canonical_source_url": canonical or "",
                "source_verified_on": verified_on or "",
                "manual_content_review": manual,
                "promotion_eligible": "YES" if eligible else "NO",
                "question_path": q.get("__path", ""),
                "solution_path": s.get("__path", "") if s else "",
            })

            summary["mechanical_pass" if mechanical == "PASS" else "mechanical_hold"] += 1
            if source_status == "LIVE_VERIFIED":
                summary["source_live_verified"] += 1
            elif source_status == "LIVE_REVIEW_PENDING":
                summary["source_live_review_pending"] += 1
            else:
                summary["curated_manual_review_required"] += 1
            summary["promotion_eligible"] += int(eligible)
            exam_stats[q["exam_code"]]["total"] += 1
            exam_stats[q["exam_code"]]["mechanical_pass"] += int(mechanical == "PASS")
            exam_stats[q["exam_code"]]["source_live_verified"] += int(source_status == "LIVE_VERIFIED")
            for issue in issues:
                issue_counts[issue] += 1
            if cid:
                concept_stats[cid]["questions"] += 1
                concept_stats[cid]["mechanical_pass"] += int(mechanical == "PASS")
                concept_stats[cid]["source_live_verified"] += int(source_status == "LIVE_VERIFIED")

    with concept_path.open("w", encoding="utf-8", newline="") as handle:
        fields2 = ["concept_id", "questions", "mechanical_pass", "source_status", "canonical_source_url", "verified_on"]
        writer = csv.DictWriter(handle, fieldnames=fields2)
        writer.writeheader()
        for cid in sorted(concept_stats):
            ev = evidence.get(cid, {})
            writer.writerow({
                "concept_id": cid,
                "questions": concept_stats[cid]["questions"],
                "mechanical_pass": concept_stats[cid]["mechanical_pass"],
                "source_status": "LIVE_VERIFIED" if ev.get("status") == "live_verified" else "LIVE_REVIEW_PENDING",
                "canonical_source_url": ev.get("canonical_url", ""),
                "verified_on": ev.get("verified_on", ""),
            })

    summary["issue_counts"] = dict(sorted(issue_counts.items()))
    summary["by_exam"] = {code: dict(values) for code, values in sorted(exam_stats.items())}
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print("Question-bank vetting tracker")
    print(f"Questions tracked: {summary['total_questions']}")
    print(f"Mechanical PASS: {summary['mechanical_pass']}")
    print(f"Mechanical HOLD: {summary['mechanical_hold']}")
    print(f"Live-source verified: {summary['source_live_verified']}")
    print(f"Live-source pending: {summary['source_live_review_pending']}")
    print(f"Curated manual review required: {summary['curated_manual_review_required']}")
    print(f"Promotion eligible: {summary['promotion_eligible']} (manual review intentionally required)")
    if summary["mechanical_hold"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
