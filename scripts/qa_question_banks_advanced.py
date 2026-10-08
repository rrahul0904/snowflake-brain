#!/usr/bin/env python3
"""Advanced QA for Snowflake certification question banks.

Standard-library-only audit intended to run after materialization. It checks:
- per-exam topic / type / difficulty diversity
- option and solution quality invariants
- release-aware lifecycle/source metadata
- within-exam semantic near-duplicates using SimHash + 3-gram Jaccard
- cross-exam near-duplicate counts as a non-blocking report
- deterministic corpus hashes for publishing receipts

Exit code is non-zero only for blocking quality defects. Cross-exam semantic overlap is
reported because adjacent SnowPro exams legitimately share Snowflake concepts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BANK = ROOT / "data" / "question-banks"
STOP = {
    "a", "an", "the", "is", "are", "to", "and", "or", "of", "in", "for", "that",
    "with", "which", "what", "should", "be", "also", "most", "best", "snowflake",
}


def load_jsonl(pattern: str):
    rows = []
    for p in sorted(BANK.glob(pattern)):
        with p.open("r", encoding="utf-8") as fh:
            for n, raw in enumerate(fh, 1):
                if not raw.strip():
                    continue
                obj = json.loads(raw)
                obj["__path"] = str(p.relative_to(ROOT))
                obj["__line"] = n
                rows.append(obj)
    return rows


def loc(x):
    return f"{x.get('__path','?')}:{x.get('__line','?')}"


def tokens(text: str):
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOP]


def shingles(tok, k=3):
    if len(tok) < k:
        return set(tok)
    return {" ".join(tok[i:i+k]) for i in range(len(tok) - k + 1)}


def simhash(sh):
    vec = [0] * 64
    for s in sh:
        h = int.from_bytes(hashlib.blake2b(s.encode("utf-8"), digest_size=8).digest(), "big")
        for b in range(64):
            vec[b] += 1 if (h >> b) & 1 else -1
    out = 0
    for b, val in enumerate(vec):
        if val >= 0:
            out |= 1 << b
    return out


def hamming(a, b):
    return (a ^ b).bit_count()


def stable_record_hash(rows, id_field):
    h = hashlib.sha256()
    for row in sorted(rows, key=lambda x: x[id_field]):
        clean = {k: v for k, v in row.items() if not k.startswith("__")}
        h.update(json.dumps(clean, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def main():
    global BANK
    ap = argparse.ArgumentParser()
    ap.add_argument("--bank-root", default=str(BANK), help="question-bank root (defaults to repo data/question-banks)")
    ap.add_argument("--report", default=None)
    ap.add_argument("--near-jaccard", type=float, default=0.90)
    ap.add_argument("--near-hamming", type=int, default=3)
    args = ap.parse_args()

    BANK = Path(args.bank_root).resolve()
    if args.report is None:
        args.report = str(BANK / "generated" / "advanced-qa-report.json")
    questions = load_jsonl("**/questions*.jsonl")
    solutions = load_jsonl("**/solutions*.jsonl")
    s_by_id = {s["question_id"]: s for s in solutions}
    errors = []
    warnings = []

    for q in questions:
        opts = q.get("options", [])
        keys = [str(o.get("key")) for o in opts]
        texts = [re.sub(r"\s+", " ", str(o.get("text", "")).strip().lower()) for o in opts]
        if len(opts) < 2:
            errors.append(f"{loc(q)}: fewer than two answer options")
        if len(keys) != len(set(keys)):
            errors.append(f"{loc(q)}: duplicate option keys")
        if len(texts) != len(set(texts)):
            errors.append(f"{loc(q)}: duplicate option text")
        if not q.get("answer_key"):
            errors.append(f"{loc(q)}: empty answer key")
        if q.get("question_type") == "multi_select" and len(q.get("answer_key", [])) < 2:
            errors.append(f"{loc(q)}: multi_select does not have multiple answers")
        if q.get("question_type") != "multi_select" and len(q.get("answer_key", [])) > 1:
            warnings.append(f"{loc(q)}: non-multi-select has multiple answer keys")
        if len(q.get("prompt", "")) < 40:
            errors.append(f"{loc(q)}: prompt is too short")
        if "release-aware" in q.get("tags", []) or "source-class:release-aware" in q.get("tags", []):
            if not q.get("lifecycle_note"):
                errors.append(f"{loc(q)}: release-aware item lacks lifecycle_note")
            if not any(s.get("type") == "official_announcement" for s in q.get("sources", [])):
                errors.append(f"{loc(q)}: release-aware item lacks official_announcement source")

        sol = s_by_id.get(q.get("id"))
        if not sol:
            errors.append(f"{loc(q)}: missing solution")
            continue
        if len(sol.get("explanation", "")) < 20:
            errors.append(f"{loc(sol)}: explanation too short")
        if len(sol.get("reasoning", "")) < 40:
            errors.append(f"{loc(sol)}: reasoning too short")
        if len(sol.get("distractor_analysis", [])) < max(1, len(opts) - len(q.get("answer_key", [])) - 1):
            warnings.append(f"{loc(sol)}: sparse distractor analysis")
        if not sol.get("exam_trap"):
            errors.append(f"{loc(sol)}: missing exam_trap")

    by_exam = defaultdict(list)
    for q in questions:
        by_exam[q.get("exam_code")].append(q)
    coverage = {}
    for code, rows in sorted(by_exam.items()):
        topics = Counter(q.get("topic") for q in rows)
        qtypes = Counter(q.get("question_type") for q in rows)
        diffs = Counter(q.get("difficulty") for q in rows)
        objectives = Counter(q.get("blueprint_objective") for q in rows)
        release_aware = sum(
            1 for q in rows
            if "release-aware" in q.get("tags", []) or "source-class:release-aware" in q.get("tags", [])
        )
        coverage[code] = {
            "questions": len(rows),
            "unique_topics": len(topics),
            "unique_question_types": len(qtypes),
            "unique_objectives": len(objectives),
            "difficulty_counts": dict(diffs),
            "question_type_counts": dict(qtypes),
            "release_aware": release_aware,
            "top_topics": topics.most_common(10),
        }
        if len(topics) < 8:
            errors.append(f"{code}: only {len(topics)} unique topics")
        if len(qtypes) < 3:
            errors.append(f"{code}: only {len(qtypes)} question types")
        if len(diffs) < 3:
            errors.append(f"{code}: not all three difficulty bands are represented")
        if release_aware > 750:
            errors.append(f"{code}: release-aware count {release_aware} exceeds 750 cap")

    band_index = defaultdict(list)
    fingerprints = []
    near_same_exam = []
    near_cross_exam = []
    for i, q in enumerate(questions):
        sh = shingles(tokens(q.get("prompt", "")))
        fp = simhash(sh)
        candidates = set()
        for band in range(4):
            key = (band, (fp >> (band * 16)) & 0xFFFF)
            candidates.update(band_index[key])
        for j in candidates:
            fp2, sh2, q2 = fingerprints[j]
            if hamming(fp, fp2) > args.near_hamming:
                continue
            union = sh | sh2
            score = len(sh & sh2) / max(1, len(union))
            if score < args.near_jaccard:
                continue
            pair = {
                "left": q2["id"],
                "right": q["id"],
                "left_exam": q2["exam_code"],
                "right_exam": q["exam_code"],
                "jaccard": round(score, 4),
                "hamming": hamming(fp, fp2),
            }
            if q2["exam_code"] == q["exam_code"]:
                near_same_exam.append(pair)
            else:
                near_cross_exam.append(pair)
        fingerprints.append((fp, sh, q))
        for band in range(4):
            key = (band, (fp >> (band * 16)) & 0xFFFF)
            band_index[key].append(i)

    if near_same_exam:
        errors.append(f"semantic near-duplicate pairs within the same exam: {len(near_same_exam)}")

    report = {
        "questions": len(questions),
        "solutions": len(solutions),
        "question_sha256": stable_record_hash(questions, "id"),
        "solution_sha256": stable_record_hash(solutions, "question_id"),
        "coverage": coverage,
        "semantic_near_duplicates": {
            "same_exam_count": len(near_same_exam),
            "cross_exam_count": len(near_cross_exam),
            "thresholds": {"jaccard": args.near_jaccard, "hamming": args.near_hamming},
            "same_exam_examples": near_same_exam[:100],
            "cross_exam_examples": near_cross_exam[:100],
        },
        "warnings": warnings[:500],
        "error_count": len(errors),
        "errors": errors[:500],
        "status": "pass" if not errors else "fail",
    }
    out = Path(args.report)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(f"Advanced QA: {len(questions)} questions / {len(solutions)} solutions")
    print(f"Within-exam semantic near-duplicates: {len(near_same_exam)}")
    print(f"Cross-exam semantic near-duplicates (reported): {len(near_cross_exam)}")
    print(f"Warnings: {len(warnings)}")
    print(f"Errors: {len(errors)}")
    print(f"Report: {out}")
    if errors:
        for e in errors[:50]:
            print(f"ERROR: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
