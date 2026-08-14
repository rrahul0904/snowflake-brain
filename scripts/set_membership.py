#!/usr/bin/env python3
"""Development-only CLI for changing a candidate's server-side membership plan.

This tool is intentionally not exposed through HTTP. Production paid access is
provisioned by verified billing events, not by browser state or reusable keys.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.auth import normalize_email  # noqa: E402
from app.database import connect, run_migrations  # noqa: E402
from app.entitlements import apply_membership_plan  # noqa: E402
from app.identity_billing_schema import ensure_identity_billing_schema  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Set a local candidate membership (development only).")
    parser.add_argument("email")
    parser.add_argument("plan", choices=("free", "premium", "premium_20", "premium_40", "premium_100", "exam_pack_35"))
    args = parser.parse_args()
    run_migrations()
    ensure_identity_billing_schema()
    email = normalize_email(args.email)
    with connect() as conn:
        candidate = conn.execute("SELECT id FROM candidate_accounts WHERE email = ? COLLATE NOCASE", (email,)).fetchone()
    if not candidate:
        raise SystemExit(f"Candidate not found: {email}")
    candidate_id = int(candidate["id"])
    requested_plan = "premium_20" if args.plan == "premium" else args.plan
    change = apply_membership_plan(
        candidate_id,
        requested_plan,
        source="development_override",
        reason="development_cli",
    )
    with connect() as conn:
        conn.execute(
            "UPDATE candidate_accounts SET plan = ?, updated_at = datetime('now') WHERE id = ?",
            ("free" if requested_plan == "free" else "premium", candidate_id),
        )
    print(
        f"Development membership updated: {email} -> {requested_plan} "
        f"(entitlement_version={change['entitlement_version']})"
    )


if __name__ == "__main__":
    main()
