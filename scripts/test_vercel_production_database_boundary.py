#!/usr/bin/env python3
"""Regression coverage for the hosted Vercel database fail-closed boundary.

The test runs child interpreters so ``app.config`` is imported with the same
Preview/Production environment a serverless function receives. It never opens a
database connection and therefore runs safely in local CI.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_config(
    *,
    vercel_env: str,
    database_url: str | None,
    brain_db: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["VERCEL"] = "1"
    environment["VERCEL_ENV"] = vercel_env
    environment["QUESTION_BANK_AUTO_IMPORT"] = "false"
    environment.pop("BRAIN_DB", None)
    environment.pop("DATABASE_URL", None)
    environment.pop("DATABASE_MIGRATION_URL", None)
    if brain_db is not None:
        environment["BRAIN_DB"] = str(brain_db)
    if database_url is not None:
        environment["DATABASE_URL"] = database_url
    return subprocess.run(
        [sys.executable, "-c", "from app.config import DATABASE_BACKEND, IS_VERCEL_RUNTIME; print(DATABASE_BACKEND, IS_VERCEL_RUNTIME)"],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def require_failure(vercel_env: str, database_url: str | None, expected_message: str, brain_db: Path) -> None:
    result = run_config(vercel_env=vercel_env, database_url=database_url, brain_db=brain_db)
    output = f"{result.stdout}\n{result.stderr}"
    if result.returncode == 0:
        raise AssertionError(f"Vercel {vercel_env} imported without a valid PostgreSQL DATABASE_URL")
    if expected_message not in output:
        raise AssertionError(f"Expected clear Vercel configuration error, got: {output}")
    if "SQLite fallback is disabled" not in output:
        raise AssertionError(f"Vercel configuration error did not confirm fail-closed policy: {output}")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="snowflake-vercel-db-") as directory:
        sqlite_path = Path(directory) / "must-not-be-created.sqlite"
        for environment_name in ("preview", "production"):
            require_failure(environment_name, None, "DATABASE_URL is required", sqlite_path)
            require_failure(
                environment_name,
                "sqlite:///tmp/incorrect-vercel.sqlite",
                "must be a PostgreSQL connection URL",
                sqlite_path,
            )
        if sqlite_path.exists():
            raise AssertionError("Vercel database boundary created a SQLite persistence file")

    for environment_name in ("preview", "production"):
        result = run_config(
            vercel_env=environment_name,
            database_url="postgresql://user:password@example.test:5432/snowflake",
        )
        if result.returncode != 0 or result.stdout.strip() != "postgresql True":
            raise AssertionError(
                f"Vercel {environment_name} must select PostgreSQL without opening a connection: "
                f"{result.stdout}\n{result.stderr}"
            )

    print("Vercel database boundary: PASS (Preview/Production require PostgreSQL; SQLite fallback blocked)")


if __name__ == "__main__":
    main()
