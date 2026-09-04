#!/usr/bin/env python3
"""Reject unsafe claims in the generated predeployment certification artifact."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    path = ROOT / "artifacts" / "predeployment-certification.json"
    if not path.exists():
        raise AssertionError("Predeployment artifact is missing")
    artifact = json.loads(path.read_text(encoding="utf-8"))
    required = {"release_sha", "deployments_created_during_phase", "checks", "admin", "finops", "ready_for_final_vercel_deployment"}
    missing = sorted(required - set(artifact))
    if missing: raise AssertionError(f"Certification artifact missing: {missing}")
    if artifact.get("deployments_created_during_phase") != 0: raise AssertionError("Artifact claims a deployment-budget violation")
    browser = next((item for item in artifact.get("checks", []) if item.get("name") == "browser_matrix_evidence"), None)
    if artifact.get("ready_for_final_vercel_deployment") and (artifact.get("status") != "GREEN" or not artifact.get("admin", {}).get("certified") or not browser or browser.get("status") != "pass"):
        raise AssertionError("Artifact cannot claim readiness without green/admin/browser evidence")
    if any(check.get("status") != "pass" for check in artifact.get("checks", [])) and artifact.get("status") == "GREEN":
        raise AssertionError("Artifact claims GREEN despite a failed check")
    print("predeployment certification artifact contract passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
