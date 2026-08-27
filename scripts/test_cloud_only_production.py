#!/usr/bin/env python3
"""Fail CI if the Vercel production profile can fall back to local state.

This intentionally allows SQLite, Docker and localhost in local/CI source
paths.  It examines only the production Vercel contract plus its runtime
configuration behavior.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VARS_FORBIDDEN_IN_VERCEL = {
    "BRAIN_DB",
    "PRIVATE_QUESTION_BANK_DIR",
    "DATABASE_MIGRATION_URL",
}
LOCAL_MARKERS = ("localhost", "127.0.0.1", "sqlite", "file://", "/tmp", "/private/question_bank")


def fail(message: str) -> None:
    raise AssertionError(message)


def vercel_env() -> dict[str, str]:
    payload = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
    env = payload.get("env") or {}
    if not isinstance(env, dict):
        fail("vercel.json env must be an object")
    return {str(key): str(value) for key, value in env.items()}


def check_static_contract() -> None:
    env = vercel_env()
    forbidden = sorted(VARS_FORBIDDEN_IN_VERCEL & set(env))
    if forbidden:
        fail(f"Vercel production env declares local/admin-only settings: {forbidden}")
    for key, value in env.items():
        lowered = value.lower()
        if any(marker in lowered for marker in LOCAL_MARKERS):
            fail(f"Vercel production env {key} contains a local persistence/runtime marker")
    if env.get("QUESTION_BANK_AUTO_IMPORT", "").lower() != "false":
        fail("Vercel production must disable QUESTION_BANK_AUTO_IMPORT")
    if env.get("ALLOW_MEMBERSHIP_DEV_OVERRIDE", "").lower() != "false":
        fail("Vercel production must disable membership development overrides")
    if env.get("APP_BASE_URL") != "https://snowflakecertificationguide.vercel.app":
        fail("Vercel production APP_BASE_URL must use the canonical HTTPS domain")

    deploy_env = (ROOT / "deploy" / "production.env.example").read_text(encoding="utf-8").lower()
    if "private_question_bank_dir=" in deploy_env or "/private/question_bank" in deploy_env:
        fail("production profile must not require a mounted private question-bank directory")
    if "database_url=postgresql://" in deploy_env:
        fail("production profile must not contain a database URL example; credentials belong in Vercel secrets")

    for compose in (ROOT / "docker-compose.yml", ROOT / "docker-compose.account-lifecycle.yml"):
        body = compose.read_text(encoding="utf-8")
        if "DEVELOPMENT / CI ONLY — NOT PRODUCTION" not in body:
            fail(f"{compose.name} must be explicitly marked development/CI only")


def run_config_probe(database_url: str | None, extra: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.update({"VERCEL_ENV": "production", "QUESTION_BANK_AUTO_IMPORT": "false"})
    environment.pop("DATABASE_URL", None)
    if database_url is not None:
        environment["DATABASE_URL"] = database_url
    environment.update(extra or {})
    return subprocess.run(
        [sys.executable, "-c", "from app.config import DATABASE_BACKEND; print(DATABASE_BACKEND)"],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def check_runtime_fail_closed() -> None:
    missing = run_config_probe(None)
    if missing.returncode == 0 or "DATABASE_URL is required" not in f"{missing.stdout}\n{missing.stderr}":
        fail("production configuration accepted a missing DATABASE_URL")
    local = run_config_probe("sqlite:///tmp/snowflake.sqlite")
    if local.returncode == 0 or "must be a PostgreSQL connection URL" not in f"{local.stdout}\n{local.stderr}":
        fail("production configuration accepted SQLite")
    import_bank = run_config_probe(
        "postgresql://runtime:password@example.test:5432/snowflake",
        {"QUESTION_BANK_AUTO_IMPORT": "true"},
    )
    if import_bank.returncode == 0 or "QUESTION_BANK_AUTO_IMPORT" not in f"{import_bank.stdout}\n{import_bank.stderr}":
        fail("production configuration accepted question-bank auto-import")
    migration_secret = run_config_probe(
        "postgresql://runtime:password@example.test:5432/snowflake",
        {"DATABASE_MIGRATION_URL": "postgresql://migration:password@example.test:5432/snowflake"},
    )
    if migration_secret.returncode == 0 or "DATABASE_MIGRATION_URL must not" not in f"{migration_secret.stdout}\n{migration_secret.stderr}":
        fail("production configuration accepted a migration credential in the Vercel runtime")


def main() -> None:
    check_static_contract()
    check_runtime_fail_closed()
    print("Cloud-only production contract: PASS (Vercel + managed PostgreSQL; no local runtime fallback)")


if __name__ == "__main__":
    main()
