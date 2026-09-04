#!/usr/bin/env python3
"""Read-only local billing reconciliation. Repairs are deliberately unsupported."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.admin_operations import ensure_admin_operations_schema
from app.database import connect, run_migrations
from app.identity_billing_schema import ensure_identity_billing_schema


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", required=True, help="Report only; never mutate entitlements.")
    parser.parse_args()
    run_migrations()
    ensure_identity_billing_schema()
    ensure_admin_operations_schema()
    findings: list[dict[str, str | int]] = []
    with connect() as conn:
        rows = conn.execute("SELECT candidate_id,provider_customer_id,provider_subscription_id,provider_price_id FROM billing_subscriptions").fetchall()
        seen: set[str] = set()
        for raw in rows:
            row = dict(raw); candidate_id = int(row["candidate_id"])
            if not row["provider_customer_id"]: findings.append({"type": "missing_stripe_customer", "candidate_id": candidate_id})
            if not row["provider_price_id"]: findings.append({"type": "unknown_price", "candidate_id": candidate_id})
            subscription_id = str(row["provider_subscription_id"] or "")
            if subscription_id in seen: findings.append({"type": "duplicate_subscription", "candidate_id": candidate_id})
            seen.add(subscription_id)
    print(json.dumps({"mode": "dry_run", "finding_count": len(findings), "findings": findings}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
