#!/usr/bin/env python3
"""Regression coverage for the Vercel production database fail-closed boundary.

This deliberately runs child interpreters so ``app.config`` is imported with
the same environment a serverless function receives. It never opens a database
connection and may therefore run in local CI as well as a Vercel build.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_config(*, database_url: str | None, brain_db: Path | None = None) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["VERCEL_ENV"] = "production"
    environment.pop("BRAIN_DB", None)
    environment.pop("DATABASE_URL", None)
    if brain_db is not None:
        environment["BRAIN_DB"] = str(brain_db)
    if database_url is not None:
        environment["DATABASE_URL"] = database_url
    return subprocess.run(
        [sys.executable, "-c", "from app.config import DATABASE_BACKEND; print(DATABASE_BACKEND)"],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def require_failure(database_url: str | None, expected_message: str, brain_db: Path) -> None:
    result = run_config(database_url=database_url, brain_db=brain_db)
    output = f"{result.stdout}\n{result.stderr}"
    if result.returncode == 0:
        raise AssertionError("Vercel production imported without a valid PostgreSQL DATABASE_URL")
    if expected_message not in output:
        raise AssertionError(f"Expected clear production configuration error, got: {output}")
    if "SQLite fallback is disabled" not in output:
        raise AssertionError(f"Production configuration error did not confirm fail-closed policy: {output}")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="snowflake-vercel-production-db-") as directory:
        sqlite_path = Path(directory) / "must-not-be-created.sqlite"
        require_failure(None, "DATABASE_URL is required", sqlite_path)
        require_failure(
            "sqlite:///tmp/incorrect-production.sqlite",
            "must be a PostgreSQL connection URL",
            sqlite_path,
        )
        if sqlite_path.exists():
            raise AssertionError("Production database boundary created a SQLite persistence file")

    result = run_config(database_url="postgresql://user:password@example.test:5432/snowflake")
    if result.returncode != 0 or result.stdout.strip() != "postgresql":
        raise AssertionError(
            "A PostgreSQL DATABASE_URL must select the PostgreSQL backend without opening a connection: "
            f"{result.stdout}\n{result.stderr}"
        )

    print("Vercel production database boundary: PASS (PostgreSQL required; SQLite fallback blocked)")


if __name__ == "__main__":
    main()
