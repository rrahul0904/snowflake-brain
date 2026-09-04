#!/usr/bin/env python3
"""Permanent server-side authorization and abuse contract for every admin API."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient
from fastapi.routing import APIRoute, iter_route_contexts

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("BRAIN_DB", os.path.join(tempfile.gettempdir(), "snowflake-admin-operations.sqlite"))
try:
    os.remove(os.environ["BRAIN_DB"])
except FileNotFoundError:
    pass

from app.auth import create_candidate, revoke_all_candidate_sessions
from app.database import connect, run_migrations
from app.main import app


def require(actual: int, expected: int, label: str) -> None:
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected}, received {actual}")


def paths() -> list[str]:
    result = sorted({str(context.path) for context in iter_route_contexts(app.routes) if str(context.path).startswith("/api/admin/") and isinstance(context.original_route, APIRoute) and "GET" in (context.original_route.methods or set())})
    if len(result) != 16:
        raise AssertionError(f"Expected 16 admin GET endpoints, found {len(result)}: {result}")
    return result


def login(client: TestClient, email: str) -> None:
    require(client.post("/api/auth/login", json={"email": email, "password": "correct-horse-battery"}).status_code, 200, "login")


def main() -> int:
    run_migrations()
    candidate = create_candidate("Candidate User", "candidate@example.test", "correct-horse-battery")
    admin = create_candidate("Admin User", "admin@example.test", "correct-horse-battery")
    with connect() as conn:
        conn.execute("UPDATE candidate_accounts SET role='admin' WHERE id=?", (admin["id"],))
    endpoints = paths()
    with TestClient(app) as client:
        for path in endpoints:
            require(client.get(path).status_code, 401, f"anonymous {path}")
        login(client, "candidate@example.test")
        for path in endpoints:
            require(client.get(path).status_code, 403, f"candidate {path}")
        client.post("/api/auth/logout")
        login(client, "admin@example.test")
        for path in endpoints:
            require(client.get(path).status_code, 200, f"admin {path}")
        require(client.get("/api/admin/users?page=0").status_code, 422, "invalid page")
        require(client.get("/api/admin/users?page_size=999").status_code, 422, "large page")
        require(client.get("/api/admin/users?plan=%27%20OR%201%3D1--").status_code, 200, "parameterized filter")
        # KPI totals must be independent of pagination. Add enough rows to make
        # the first page incomplete and assert the aggregate still sees all.
        with connect() as conn:
            for index in range(51):
                plan = ("premium_20", "premium_40", "premium_100")[index % 3]
                conn.execute(
                    "INSERT INTO billing_subscriptions(candidate_id,provider,provider_customer_id,provider_subscription_id,provider_price_id,internal_plan,status) VALUES (?,?,?,?,?,?,?)",
                    (candidate["id"], "stripe", f"cus_{index}", f"sub_{index}", f"price_{index}", plan, "active"),
                )
        paged = client.get("/api/admin/subscriptions?page=1&page_size=1")
        require(paged.status_code, 200, "paginated subscriptions")
        if paged.json()["kpis"]["active_subscribers"] != 51 or paged.json()["kpis"]["mrr"] != 2720.0:
            raise AssertionError("subscription KPI totals changed with pagination")
        with connect() as conn:
            conn.execute("UPDATE candidate_accounts SET role='candidate' WHERE id=?", (admin["id"],))
        require(client.get("/api/admin/overview").status_code, 403, "role changed after session")
        with connect() as conn:
            conn.execute("UPDATE candidate_accounts SET role='admin' WHERE id=?", (admin["id"],))
        revoke_all_candidate_sessions(admin["id"])
        require(client.get("/api/admin/overview").status_code, 401, "expired/revoked admin session")
    print(f"admin operations contract passed for {len(endpoints)} endpoints")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
