#!/usr/bin/env python3
"""Authorization contract: anonymous 401, candidate 403, explicit admin allowed."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, root)
os.environ.setdefault("BRAIN_DB", os.path.join(tempfile.gettempdir(), "snowflake-admin-auth.sqlite"))
try:
    os.remove(os.environ["BRAIN_DB"])
except FileNotFoundError:
    pass

from app.auth import create_candidate
from app.database import connect, run_migrations
from app.main import app


def expect(actual: int, expected: int) -> None:
    if actual != expected:
        raise AssertionError(f"Expected {expected}, received {actual}")


def main() -> int:
    run_migrations()
    candidate = create_candidate("Candidate User", "candidate@example.test", "correct-horse-battery")
    admin = create_candidate("Admin User", "admin@example.test", "correct-horse-battery")
    with connect() as conn:
        conn.execute("UPDATE candidate_accounts SET role='admin' WHERE id=?", (admin["id"],))
    with TestClient(app) as client:
        expect(client.get("/api/admin/overview").status_code, 401)
        client.post("/api/auth/login", json={"email": "candidate@example.test", "password": "correct-horse-battery"})
        expect(client.get("/api/admin/overview").status_code, 403)
        client.post("/api/auth/logout")
        client.post("/api/auth/login", json={"email": "admin@example.test", "password": "correct-horse-battery"})
        response = client.get("/api/admin/overview")
        expect(response.status_code, 200)
        assert response.json()["finops"]["evidence"] == ["NOT_CONNECTED"]
    print("admin authorization contract passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
