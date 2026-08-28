#!/usr/bin/env python3
"""Build a machine-readable security release decision from redacted evidence."""

from __future__ import annotations

import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
OUT = ARTIFACTS / "security-release-report.json"


def load(name: str) -> dict:
    path = ARTIFACTS / name
    if not path.exists():
        return {"status": "missing"}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"status": "invalid"}
    return value if isinstance(value, dict) else {"status": "invalid"}


def main() -> None:
    hosted = load("hosted-runtime-security.json")
    static = load("hosted-static-exposure.json")
    bank = load("production-bank-inventory.json")
    live_black_box = os.environ.get("LIVE_BLACK_BOX_STATUS", "blocked").strip().lower()

    blockers: list[str] = []
    if hosted.get("status") != "pass":
        blockers.append("hosted_runtime_security")
    if static.get("status") != "pass":
        blockers.append("hosted_static_exposure")
    if bank.get("status") != "pass":
        blockers.append("production_bank_inventory")
    if live_black_box != "pass":
        blockers.append("live_black_box")

    payload = {
        "status": "go" if not blockers else "no-go",
        "main_sha": os.environ.get("RELEASE_MAIN_SHA", ""),
        "pr_number": os.environ.get("RELEASE_PR_NUMBER", ""),
        "merge_sha": os.environ.get("RELEASE_MERGE_SHA", ""),
        "vercel_deployment_id": os.environ.get("VERCEL_DEPLOYMENT_ID", ""),
        "vercel_deployment_sha": os.environ.get("VERCEL_DEPLOYMENT_SHA", ""),
        "production_url": os.environ.get("SECURITY_BASE_URL", ""),
        "database_boundary": hosted.get("status", "missing"),
        "production_soak": hosted.get("status", "missing"),
        "static_exposure_tests": static.get("status", "missing"),
        "question_inventory_status": bank.get("status", "missing"),
        "active_release_present": bool(bank.get("active_release_present", False)),
        "active_question_count": int(bank.get("active_release_question_count", 0) or 0),
        "pool_counts": bank.get("pool_counts", {}),
        "production_black_box": live_black_box,
        "known_critical": 0 if not blockers else None,
        "known_high": 0 if not blockers else None,
        "blocking_items": blockers,
    }
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    if blockers:
        raise SystemExit("Security release remains NO-GO: " + ", ".join(blockers))


if __name__ == "__main__":
    main()
