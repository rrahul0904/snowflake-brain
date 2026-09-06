#!/usr/bin/env python3
"""Regression guard: hosted request code cannot bootstrap or reconcile schema.

This is deliberately source-level as well as endpoint-oriented: a request can
reach helpers through FastAPI dependencies, so checking only router bodies
would miss an auth or service-layer DDL regression.
"""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def main() -> int:
    activity = source("app/routers/activity.py")
    intelligence = source("app/routers/intelligence.py")
    require("CREATE TABLE" not in activity and "_ensure_table" not in activity, "globe GET contains runtime DDL")
    require("sync_candidate_learning_state" not in intelligence, "intelligence GET still performs a write-time sync")

    # These helpers are reachable through auth dependencies, credential/talent
    # services, admin authorization, and candidate learning routes. Their DDL
    # bodies remain only for SQLite local/CI compatibility and must be gated
    # before any connection or PRAGMA work occurs in PostgreSQL.
    for path, function in (
        ("app/identity_billing_schema.py", "ensure_identity_billing_schema"),
        ("app/talent_schema.py", "ensure_talent_schema"),
        ("app/learning_intelligence.py", "ensure_learning_intelligence_schema"),
        ("app/learning_sync.py", "ensure_learning_sync_schema"),
        ("app/account_lifecycle.py", "ensure_account_lifecycle_schema"),
        ("app/question_versions.py", "ensure_question_version_schema"),
        ("app/question_bank_releases.py", "ensure_question_bank_release_schema"),
        ("app/exam_entitlement_reservations.py", "ensure_exam_entitlement_reservation_schema"),
    ):
        body = source(path).split(f"def {function}", 1)[1].split("\ndef ", 1)[0]
        guard = body.find('DATABASE_BACKEND == "postgresql"')
        ddl_positions = [index for index in (body.find("CREATE TABLE"), body.find("ALTER TABLE"), body.find("executescript")) if index >= 0]
        first_statement = min(ddl_positions) if ddl_positions else len(body)
        require(guard >= 0 and guard < first_statement and "return" in body[guard:first_statement], f"{function} can execute hosted DDL")

    release = source("scripts/write_release_manifest.py")
    require("VERCEL_GIT_COMMIT_SHA" in release and "source_dirty\": False" in release, "release manifest does not require clean Git identity")
    frontend = source("frontend/components/home-command-center.js")
    require("getHomeSummary" in frontend and "Promise.race" not in frontend, "Home command center still fans out or waits on a timeout")
    shell = source("frontend/app-complete.js")
    require("async function handleRoute(){await route();footer()" in shell, "ordinary route navigation still rerenders the navigation shell")
    print("runtime DDL boundary: PASS (hosted request helpers are migration-only; Home uses one aggregate)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
