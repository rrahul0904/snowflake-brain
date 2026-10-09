#!/usr/bin/env python3
"""Apply vetted canonical Snowflake source URLs to generated and curated records."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BANK = ROOT / "data" / "question-banks"
GENERATED = BANK / "generated"
OVERRIDES_PATH = BANK / "vetting" / "source-overrides.json"
CURATED_POLICY_PATH = BANK / "vetting" / "curated-review-policy.json"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def concept_id(record):
    for tag in record.get("tags", []):
        if isinstance(tag, str) and tag.startswith("concept:"):
            return tag.split(":", 1)[1]
    return None


def canonical_source(existing, override):
    original = existing[0] if existing else {}
    return [{
        "type": original.get("type", "official_docs"),
        "title": override.get("title") or original.get("title"),
        "url": override["canonical_url"],
        "section": original.get("section"),
    }]


def rewrite_jsonl(path: Path, transform):
    changed = 0
    output = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        record = json.loads(raw)
        record, did_change = transform(record)
        changed += int(did_change)
        output.append(json.dumps(record, separators=(",", ":"), ensure_ascii=False))
    path.write_text("\n".join(output) + "\n", encoding="utf-8")
    return changed


def main():
    overrides = load_json(OVERRIDES_PATH).get("concepts", {})
    curated_overrides = load_json(CURATED_POLICY_PATH).get("source_overrides_by_question_id", {})
    qid_to_concept = {}
    q_changed = 0
    s_changed = 0

    for path in sorted(GENERATED.glob("*/questions.generated.jsonl")):
        def transform_question(record):
            cid = concept_id(record)
            if cid:
                qid_to_concept[record["id"]] = cid
            override = overrides.get(cid)
            if not override:
                return record, False
            before = record.get("sources", [])
            after = canonical_source(before, override)
            record["sources"] = after
            return record, before != after
        q_changed += rewrite_jsonl(path, transform_question)

    for path in sorted(GENERATED.glob("*/solutions.generated.jsonl")):
        def transform_solution(record):
            cid = qid_to_concept.get(record["question_id"])
            override = overrides.get(cid)
            if not override:
                return record, False
            before = record.get("sources", [])
            after = canonical_source(before, override)
            record["sources"] = after
            return record, before != after
        s_changed += rewrite_jsonl(path, transform_solution)

    for path in sorted(list((BANK / "seed").glob("questions*.jsonl")) + list((BANK / "release-aware").glob("questions*.jsonl"))):
        def transform_curated_question(record):
            override = curated_overrides.get(record["id"])
            if not override:
                return record, False
            before = record.get("sources", [])
            after = canonical_source(before, override)
            record["sources"] = after
            return record, before != after
        q_changed += rewrite_jsonl(path, transform_curated_question)

    for path in sorted(list((BANK / "seed").glob("solutions*.jsonl")) + list((BANK / "release-aware").glob("solutions*.jsonl"))):
        def transform_curated_solution(record):
            override = curated_overrides.get(record["question_id"])
            if not override:
                return record, False
            before = record.get("sources", [])
            after = canonical_source(before, override)
            record["sources"] = after
            return record, before != after
        s_changed += rewrite_jsonl(path, transform_curated_solution)

    print(f"Canonical source overrides applied: {q_changed} questions / {s_changed} solutions")


if __name__ == "__main__":
    main()
