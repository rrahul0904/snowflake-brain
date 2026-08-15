#!/usr/bin/env python3
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.question_bank import MODE_DOMAIN_COUNTS  # noqa: E402
from app.question_bank_selection import _select_blueprint_with_fresh_fallback  # noqa: E402
from app.routers.certification_practice import _cert  # noqa: E402


def check(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def make_row(domain_id: str, index: int, *, excluded: bool = False) -> dict:
    return {
        "id": f"freshness::{domain_id}::{index}",
        "mapped_domain_id": domain_id,
        "mapped_skill_id": f"task::{domain_id}",
        "domain_id": domain_id,
        "task_id": f"task::{domain_id}",
        "difficulty_band": "applied",
        "difficulty": "medium",
        "bank_pool": "mock_reserved",
        "candidate_served_count": 1 if excluded else 0,
        "candidate_last_served": f"2026-{index + 1:02d}-01T00:00:00" if excluded else "",
        "global_served_count": index if excluded else 0,
    }


def main() -> None:
    domains = _cert("snowpro-core").get("domains") or []
    targets = MODE_DOMAIN_COUNTS["full-mock"]
    rows: list[dict] = []
    excluded_ids: set[str] = set()

    for domain in domains:
        domain_id = str(domain["id"])
        target = int(targets[domain_id])
        if domain_id == "account-governance":
            # Exactly 18 fresh questions for a 20-question bucket, plus five
            # reset-window repeats ordered oldest -> newest.
            for index in range(18):
                rows.append(make_row(domain_id, 100 + index))
            for index in range(5):
                row = make_row(domain_id, index, excluded=True)
                rows.append(row)
                excluded_ids.add(row["id"])
        else:
            # Other domains have enough fresh inventory and must not borrow any
            # excluded questions simply because one bucket is short.
            for index in range(target + 3):
                rows.append(make_row(domain_id, 200 + index))

    selected, repeated_count = _select_blueprint_with_fresh_fallback(
        rows,
        domains,
        100,
        "full-mock",
        excluded_ids,
    )
    check(len(selected) == 100, "Full Mock still contains exactly 100 questions")
    counts = Counter(row["mapped_domain_id"] for row in selected)
    check(counts == Counter(targets), "fresh fallback preserves the exact Full Mock domain blueprint")
    selected_repeats = [row for row in selected if row["id"] in excluded_ids]
    check(repeated_count == len(selected_repeats) == 2, "only the two-question account-governance deficit repeats")
    check(
        {row["id"] for row in selected_repeats}
        == {"freshness::account-governance::0", "freshness::account-governance::1"},
        "the least-recently-seen repeats are selected first",
    )
    check(
        all(row["mapped_domain_id"] == "account-governance" for row in selected_repeats),
        "no healthy blueprint bucket repeats because another domain is short",
    )

    # If every bucket has enough fresh questions, the reset produces zero repeats.
    all_fresh = [row for row in rows if row["id"] not in excluded_ids]
    # Add the two missing account-governance questions as fresh alternatives.
    all_fresh.extend(
        [
            make_row("account-governance", 500),
            make_row("account-governance", 501),
        ]
    )
    fresh_selected, fresh_repeats = _select_blueprint_with_fresh_fallback(
        all_fresh,
        domains,
        100,
        "full-mock",
        excluded_ids,
    )
    check(len(fresh_selected) == 100 and fresh_repeats == 0, "complete fresh inventory produces a fully fresh 100Q sitting")
    check(Counter(row["mapped_domain_id"] for row in fresh_selected) == Counter(targets), "fully fresh sitting preserves blueprint")

    print("Blueprint-aware fresh reset fallback checks passed.")


if __name__ == "__main__":
    main()
