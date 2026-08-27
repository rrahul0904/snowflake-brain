#!/usr/bin/env python3
"""Regression gate for least-privilege production migration grants."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    os.environ.setdefault("DATABASE_URL", "postgresql://runtime:password@example.test:5432/snowflake")
    os.environ.setdefault("DATABASE_MIGRATION_URL", "postgresql://migrator:password@example.test:5432/snowflake")
    sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location("migrate_production", ROOT / "scripts" / "migrate_production.py")
    if not spec or not spec.loader:
        raise AssertionError("Unable to load production migration job")
    migration_job = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration_job)

    runtime_queries: list[object] = []
    migration_queries: list[object] = []

    class Result:
        def fetchone(self):
            return ("application_runtime",)

    class Connection:
        def __init__(self, queries: list[object]):
            self.queries = queries
        def __enter__(self):
            return self
        def __exit__(self, *_args):
            return False
        def execute(self, statement):
            self.queries.append(statement)
            return Result()

    def fake_connect(url: str, **_kwargs):
        return Connection(runtime_queries if url == migration_job.DATABASE_URL else migration_queries)

    migration_job.connect = fake_connect
    migration_job.current_schema_name = lambda: "application"
    migration_job.grant_runtime_privileges()

    if runtime_queries != ["SELECT current_user AS role"]:
        raise AssertionError(f"Runtime role was not discovered safely: {runtime_queries!r}")
    if len(migration_queries) != 7:
        raise AssertionError(f"Expected schema/table/sequence/function grants, got {len(migration_queries)} statements")
    print("Production migration privileges: PASS (runtime role receives only required database access)")


if __name__ == "__main__":
    main()
