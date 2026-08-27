#!/usr/bin/env python3
"""Prove that Vercel startup verifies rather than mutates schema state."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    environment = os.environ.copy()
    environment.update(
        {
            "VERCEL_ENV": "production",
            "DATABASE_URL": "postgresql://runtime:password@example.test:5432/snowflake",
            "QUESTION_BANK_AUTO_IMPORT": "false",
        }
    )
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
print('Production startup boundary: PASS (schema verification only)')
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise AssertionError(f"Production startup boundary failed:\n{result.stdout}\n{result.stderr}")
    print(result.stdout.strip())


if __name__ == "__main__":
    main()
