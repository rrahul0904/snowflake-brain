#!/usr/bin/env python3
"""Fail CI if a hosted Vercel runtime can fall back to local/admin or insecure state.

SQLite, Docker and localhost remain valid for explicit local/CI workflows. This
gate examines only the Vercel deployment contract and imports ``app.config`` in
both Preview and Production serverless environments.
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
        fail(f"Vercel env declares local/admin-only settings: {forbidden}")
    for key, value in env.items():
        lowered = value.lower()
        if any(marker in lowered for marker in LOCAL_MARKERS):
            fail(f"Vercel env {key} contains a local persistence/runtime marker")
    if env.get("QUESTION_BANK_AUTO_IMPORT", "").lower() != "false":
        fail("Vercel must disable QUESTION_BANK_AUTO_IMPORT")
    if env.get("ALLOW_MEMBERSHIP_DEV_OVERRIDE", "").lower() != "false":
        fail("Vercel must disable membership development overrides")
    for key in ("AUTH_COOKIE_SECURE", "FORCE_HTTPS", "SECURITY_RATE_LIMIT_ENABLED"):
        if env.get(key, "").lower() != "true":
            fail(f"Vercel must enforce {key}=true")
    if env.get("APP_BASE_URL") != "https://snowflakecertificationguide.vercel.app":
        fail("Vercel APP_BASE_URL must use the canonical HTTPS domain")

    deploy_env = (ROOT / "deploy" / "production.env.example").read_text(encoding="utf-8").lower()
    if "private_question_bank_dir=" in deploy_env or "/private/question_bank" in deploy_env:
        fail("production profile must not require a mounted private question-bank directory")
    if "database_url=postgresql://" in deploy_env:
        fail("production profile must not contain a database URL example; credentials belong in Vercel secrets")

    for compose in (ROOT / "docker-compose.yml", ROOT / "docker-compose.account-lifecycle.yml"):
        body = compose.read_text(encoding="utf-8")
        if "DEVELOPMENT / CI ONLY — NOT PRODUCTION" not in body:
            fail(f"{compose.name} must be explicitly marked development/CI only")


def run_config_probe(
    vercel_environment: str,
    database_url: str | None,
    extra: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.update(
        {
            "VERCEL": "1",
            "VERCEL_ENV": vercel_environment,
            "QUESTION_BANK_AUTO_IMPORT": "false",
            "AUTH_COOKIE_SECURE": "true",
            "FORCE_HTTPS": "true",
            "SECURITY_RATE_LIMIT_ENABLED": "true",
            "ALLOW_MEMBERSHIP_DEV_OVERRIDE": "false",
            "APP_BASE_URL": "https://snowflakecertificationguide.vercel.app",
        }
    )
    for key in ("DATABASE_URL", "DATABASE_MIGRATION_URL", "BRAIN_DB", "PRIVATE_QUESTION_BANK_DIR"):
        environment.pop(key, None)
    if database_url is not None:
        environment["DATABASE_URL"] = database_url
    environment.update(extra or {})
    return subprocess.run(
        [sys.executable, "-c", "from app.config import DATABASE_BACKEND, IS_VERCEL_RUNTIME; print(DATABASE_BACKEND, IS_VERCEL_RUNTIME)"],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def check_runtime_fail_closed() -> None:
    for vercel_environment in ("preview", "production"):
        missing = run_config_probe(vercel_environment, None)
        if missing.returncode == 0 or "DATABASE_URL is required" not in f"{missing.stdout}\n{missing.stderr}":
            fail(f"Vercel {vercel_environment} accepted a missing DATABASE_URL")

        local = run_config_probe(vercel_environment, "sqlite:///tmp/snowflake.sqlite")
        if local.returncode == 0 or "must be a PostgreSQL connection URL" not in f"{local.stdout}\n{local.stderr}":
            fail(f"Vercel {vercel_environment} accepted SQLite")

        import_bank = run_config_probe(
            vercel_environment,
            "postgresql://runtime:password@example.test:5432/snowflake",
            {"QUESTION_BANK_AUTO_IMPORT": "true"},
        )
        if import_bank.returncode == 0 or "QUESTION_BANK_AUTO_IMPORT" not in f"{import_bank.stdout}\n{import_bank.stderr}":
            fail(f"Vercel {vercel_environment} accepted question-bank auto-import")

        migration_secret = run_config_probe(
            vercel_environment,
            "postgresql://runtime:password@example.test:5432/snowflake",
            {"DATABASE_MIGRATION_URL": "postgresql://migration:password@example.test:5432/snowflake"},
        )
        if migration_secret.returncode == 0 or "DATABASE_MIGRATION_URL must not" not in f"{migration_secret.stdout}\n{migration_secret.stderr}":
            fail(f"Vercel {vercel_environment} accepted a migration credential in request-serving runtime")

        for setting, insecure_value, expected in (
            ("AUTH_COOKIE_SECURE", "false", "AUTH_COOKIE_SECURE must be true"),
            ("FORCE_HTTPS", "false", "FORCE_HTTPS must be true"),
            ("SECURITY_RATE_LIMIT_ENABLED", "false", "SECURITY_RATE_LIMIT_ENABLED must be true"),
            ("ALLOW_MEMBERSHIP_DEV_OVERRIDE", "true", "ALLOW_MEMBERSHIP_DEV_OVERRIDE must be false"),
            ("APP_BASE_URL", "http://example.test", "APP_BASE_URL must use HTTPS"),
        ):
            insecure = run_config_probe(
                vercel_environment,
                "postgresql://runtime:password@example.test:5432/snowflake",
                {setting: insecure_value},
            )
            if insecure.returncode == 0 or expected not in f"{insecure.stdout}\n{insecure.stderr}":
                fail(f"Vercel {vercel_environment} accepted insecure {setting}={insecure_value!r}")

        valid = run_config_probe(
            vercel_environment,
            "postgresql://runtime:password@example.test:5432/snowflake",
        )
        if valid.returncode != 0 or valid.stdout.strip() != "postgresql True":
            fail(f"Vercel {vercel_environment} rejected valid PostgreSQL runtime configuration: {valid.stdout}\n{valid.stderr}")


def main() -> None:
    check_static_contract()
    check_runtime_fail_closed()
    print(
        "Cloud-only Vercel contract: PASS "
        "(Preview/Production use managed PostgreSQL, secure hosted settings, and no local/admin fallback)"
    )


if __name__ == "__main__":
    main()
