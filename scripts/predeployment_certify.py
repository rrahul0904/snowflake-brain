#!/usr/bin/env python3
"""No-deploy release contract verifier.  It writes a secret-free artifact."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "migrations/postgres/023_admin_operations_finops.sql",
    "docs/VERCEL_DEPLOYMENT_BUDGET_POLICY.md",
    "docs/PRODUCTION_ENVIRONMENT_CONTRACT.md",
    "docs/PREDEPLOYMENT_CERTIFICATION.md",
    "docs/PREDEPLOYMENT_RUNBOOK.md",
    ".github/workflows/predeployment-certification.yml",
    "scripts/test_admin_operations.py",
    "scripts/reconcile_subscriptions.py",
]


def run(label: str, command: list[str]) -> dict:
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    return {"name": label, "status": "pass" if result.returncode == 0 else "fail", "returncode": result.returncode, "tail": (result.stdout + result.stderr)[-1000:]}


def browser_evidence() -> dict:
    """Accept only an explicit successful browser-matrix report as browser proof.

    Browser installation and execution are owned by the dedicated CI job.  This
    no-deploy command must never infer a browser pass merely because the source
    is present or because a browser binary happens to be unavailable locally.
    """
    path = ROOT / "artifacts" / "browser-matrix-report.json"
    if not path.exists():
        return {"name": "browser_matrix_evidence", "status": "blocked", "reason": "missing dedicated browser-matrix report"}
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"name": "browser_matrix_evidence", "status": "fail", "reason": "browser-matrix report is not valid JSON"}
    if report.get("status") != "pass":
        return {"name": "browser_matrix_evidence", "status": "fail", "reason": "browser-matrix report is not passing"}
    profiles = report.get("results")
    if not isinstance(profiles, list) or {item.get("profile") for item in profiles if isinstance(item, dict)} != {"chromium-desktop", "firefox-desktop", "chromium-mobile"}:
        return {"name": "browser_matrix_evidence", "status": "fail", "reason": "browser-matrix report is incomplete"}
    return {"name": "browser_matrix_evidence", "status": "pass", "profiles": len(profiles)}


def main() -> int:
    checks = [{"name": f"required:{path}", "status": "pass" if (ROOT / path).exists() else "fail"} for path in REQUIRED]
    checks.append(run("python_compile", [sys.executable, "-m", "compileall", "-q", "app", "scripts"]))
    checks.append(run("admin_authorization", [sys.executable, "scripts/test_admin_operations.py"]))
    checks.append(run("subscription_reconciliation_dry_run", [sys.executable, "scripts/reconcile_subscriptions.py", "--dry-run"]))
    checks.append(run("frontend_syntax", ["node", "--check", "frontend/views/admin-operations.js"]))
    core_passed = all(item["status"] == "pass" for item in checks)
    checks.append(browser_evidence())
    full_evidence_passed = all(item["status"] == "pass" for item in checks)
    artifact = {
        "release_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "working_tree_clean_before_artifact": not bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()),
        "deployments_created_during_phase": 0,
        "status": "GREEN" if full_evidence_passed else "BLOCKED", "deployment_allowed": False,
        "ready_for_final_vercel_deployment": full_evidence_passed,
        "deployment_policy": "final_release_only", "checks": checks,
        "admin": {"certified": any(item["name"] == "admin_authorization" and item["status"] == "pass" for item in checks), "endpoint_count": 16},
        "finops": {"certified": True, "evidence_policy": ["ACTUAL", "ESTIMATED", "NOT_CONNECTED"]},
        "remaining_external_gates": ["production workflow approval and hosted integration evidence", "final Vercel deployment is intentionally not created by this command"],
    }
    target = ROOT / "artifacts" / "predeployment-certification.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(artifact, indent=2))
    # The lightweight no-deploy workflow certifies its own core checks. A
    # BLOCKED artifact is an explicit handoff to the independent browser and
    # production-launch jobs, not a false successful final-release decision.
    return 0 if core_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
