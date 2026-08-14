#!/usr/bin/env python3
"""Development-only CLI for changing a candidate's server-side membership tier."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.auth import membership_for_candidate, normalize_email  # noqa: E402
from app.database import connect, run_migrations  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Set a local candidate membership (development only).")
    parser.add_argument("email")
    parser.add_argument("plan", choices=("free", "premium", "premium_20", "premium_40", "premium_100", "exam_pack_35"))
    args = parser.parse_args()
    run_migrations()
    email = normalize_email(args.email)
    with connect() as conn:
        candidate = conn.execute("SELECT id FROM candidate_accounts WHERE email = ? COLLATE NOCASE", (email,)).fetchone()
    if not candidate:
        raise SystemExit(f"Candidate not found: {email}")
    candidate_id = int(candidate["id"])
    requested_plan = "premium_20" if args.plan == "premium" else args.plan
    requested_tier = "free" if requested_plan == "free" else "premium"
    previous_membership = membership_for_candidate(candidate_id)
    previous = previous_membership.get("plan_code") or previous_membership["tier"]
    with connect() as conn:
        if requested_tier == "premium":
            conn.execute(
                "UPDATE candidate_memberships SET status = 'cancelled', updated_at = datetime('now') "
                "WHERE candidate_id = ? AND tier = 'premium' AND status = 'active'",
                (candidate_id,),
            )
            conn.execute(
                "INSERT INTO candidate_memberships(candidate_id, tier, plan_code, status, source) "
                "VALUES (?, 'premium', ?, 'active', 'development_cli')",
                (candidate_id, requested_plan),
            )
        else:
            conn.execute(
                "UPDATE candidate_memberships SET status = 'cancelled', updated_at = datetime('now') "
                "WHERE candidate_id = ? AND tier = 'premium' AND status = 'active'",
                (candidate_id,),
            )
            active_free = conn.execute(
                "SELECT id FROM candidate_memberships WHERE candidate_id = ? AND tier = 'free' AND status = 'active' LIMIT 1",
                (candidate_id,),
            ).fetchone()
            if not active_free:
                conn.execute(
                    "INSERT INTO candidate_memberships(candidate_id, tier, plan_code, status, source) "
                    "VALUES (?, 'free', 'free', 'active', 'development_cli')",
                    (candidate_id,),
                )
        conn.execute("UPDATE candidate_accounts SET plan = ?, updated_at = datetime('now') WHERE id = ?", (requested_tier, candidate_id))
        if previous != requested_plan:
            conn.execute(
                "INSERT INTO membership_events(candidate_id, previous_plan, next_plan, source) VALUES (?, ?, ?, 'development_cli')",
                (candidate_id, previous, requested_plan),
            )
    print(f"Development membership updated: {email} -> {requested_plan}")


if __name__ == "__main__":
    main()
