#!/usr/bin/env python3
"""Release identity is secret-free and admin bootstrap is explicit/audited."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["BRAIN_DB"] = str(Path(tempfile.mkdtemp(prefix="snowflake-release-identity-")) / "state.sqlite")

from app.admin_operations import ensure_admin_operations_schema  # noqa: E402
from app.auth import create_candidate  # noqa: E402
from app.database import connect, run_migrations  # noqa: E402
from app.identity_billing_schema import ensure_identity_billing_schema  # noqa: E402
from app.main import app  # noqa: E402


def main() -> int:
    run_migrations(); ensure_identity_billing_schema(); ensure_admin_operations_schema()
    with TestClient(app) as client:
        release = client.get("/api/release")
    assert release.status_code == 200
    payload = release.json()
    assert set(payload) == {"git_sha", "release_id", "environment", "build_timestamp"}
    assert all(isinstance(value, str) for value in payload.values())
    candidate = create_candidate("Designated Admin", "designated.admin@example.test", "correct-horse-battery")
    command = [sys.executable, "scripts/promote_admin.py", "--email", candidate["email"]]
    refused = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, env=os.environ.copy())
    assert refused.returncode == 2 and "confirm-promote" in refused.stderr
    promoted = subprocess.run(command + ["--confirm-promote"], cwd=ROOT, text=True, capture_output=True, env=os.environ.copy())
    assert promoted.returncode == 0, promoted.stderr
    with connect() as conn:
        role = conn.execute("SELECT role FROM candidate_accounts WHERE id=?", (candidate["id"],)).fetchone()
        audit = conn.execute("SELECT event,metadata_json FROM admin_audit_events WHERE actor_candidate_id=?", (candidate["id"],)).fetchone()
    assert dict(role)["role"] == "admin"
    assert dict(audit)["event"] == "admin.role.promoted"
    assert "secret" not in dict(audit)["metadata_json"].lower()
    print("release identity and explicit admin bootstrap contract passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
