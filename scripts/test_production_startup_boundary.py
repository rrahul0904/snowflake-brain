#!/usr/bin/env python3
"""Prove that every hosted Vercel startup verifies rather than mutates state."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_boundary(vercel_environment: str) -> None:
    environment = os.environ.copy()
    environment.update(
        {
            "VERCEL": "1",
            "VERCEL_ENV": vercel_environment,
            "DATABASE_URL": "postgresql://runtime:password@example.test:5432/snowflake",
            "QUESTION_BANK_AUTO_IMPORT": "false",
            "AUTH_COOKIE_SECURE": "true",
            "FORCE_HTTPS": "true",
            "SECURITY_RATE_LIMIT_ENABLED": "true",
            "ALLOW_MEMBERSHIP_DEV_OVERRIDE": "false",
            "APP_BASE_URL": "https://snowflakecertificationguide.vercel.app",
        }
    )
    environment.pop("DATABASE_MIGRATION_URL", None)
    code = """
import app.main as main

events = []
main.assert_production_schema_ready = lambda: events.append('verify')
main.run_migrations = lambda: events.append('migrate')
main.ensure_identity_billing_schema = lambda: events.append('identity')
main.ensure_question_version_schema = lambda: events.append('versions')
main.ensure_question_bank_release_schema = lambda: events.append('release')
main.ensure_learning_intelligence_schema = lambda: events.append('learning')
main.ensure_account_lifecycle_schema = lambda: events.append('lifecycle')
main.ensure_adaptive_readiness_schema = lambda: events.append('adaptive')
main.ensure_talent_schema = lambda: events.append('talent')
main.feedback.ensure_feedback_schema = lambda: events.append('feedback')
main.import_question_bank_directory = lambda: events.append('import')
main.ensure_active_release_baseline = lambda *args: events.append('baseline')
main.startup()
assert events == ['verify'], events
print('verification-only')
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode or result.stdout.strip() != "verification-only":
        raise AssertionError(
            f"Vercel {vercel_environment} startup boundary failed:\n{result.stdout}\n{result.stderr}"
        )


def main() -> None:
    for environment_name in ("preview", "production"):
        run_boundary(environment_name)
    print("Vercel startup boundary: PASS (Preview/Production schema verification only)")


if __name__ == "__main__":
    main()
