#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory(prefix="snowflake-schema-concurrency-")
DB_PATH = Path(TEMP.name) / "schema.sqlite"
os.environ["BRAIN_DB"] = str(DB_PATH)

from app.config import DATABASE_BACKEND  # noqa: E402
from app.database import connect, run_migrations  # noqa: E402
from app.identity_billing_schema import SCHEMA_VERSION, ensure_identity_billing_schema  # noqa: E402


def main() -> None:
    try:
        run_migrations()
        failures: list[str] = []
        with ThreadPoolExecutor(max_workers=16) as pool:
            futures = [pool.submit(ensure_identity_billing_schema) for _ in range(64)]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as exc:  # pragma: no cover - failure reporting
                    failures.append(repr(exc))
        if failures:
            raise AssertionError(f"Concurrent schema bootstrap failed: {failures[:3]}")

        with connect() as conn:
            if DATABASE_BACKEND == "postgresql":
                trigger_count = conn.execute(
                    """
                    SELECT COUNT(*) AS n
                    FROM pg_trigger t
                    JOIN pg_class c ON c.oid=t.tgrelid
                    JOIN pg_namespace ns ON ns.oid=c.relnamespace
                    WHERE NOT t.tgisinternal
                      AND ns.nspname=current_schema()
                      AND t.tgname='trg_restore_exam_pack_after_membership_expiry'
                    """
                ).fetchone()["n"]
                identity_table = conn.execute(
                    """
                    SELECT COUNT(*) AS n
                    FROM information_schema.tables
                    WHERE table_schema=current_schema() AND table_name='candidate_identities'
                    """
                ).fetchone()["n"]
            else:
                trigger_count = conn.execute(
                    "SELECT COUNT(*) AS n FROM sqlite_master WHERE type='trigger' AND name='trg_restore_exam_pack_after_membership_expiry'"
                ).fetchone()["n"]
                identity_table = conn.execute(
                    "SELECT COUNT(*) AS n FROM sqlite_master WHERE type='table' AND name='candidate_identities'"
                ).fetchone()["n"]
            migration_count = conn.execute(
                "SELECT COUNT(*) AS n FROM schema_migrations WHERE version=?",
                (SCHEMA_VERSION,),
            ).fetchone()["n"]

        if int(trigger_count) != 1:
            raise AssertionError(f"Expected one Exam Pack reconciliation trigger, found {trigger_count}")
        if int(migration_count) != 1:
            raise AssertionError(f"Expected one identity/billing migration row, found {migration_count}")
        if int(identity_table) != 1:
            raise AssertionError("candidate_identities table was not created")

        print("Identity/billing schema concurrent bootstrap: PASS")
    finally:
        TEMP.cleanup()


if __name__ == "__main__":
    main()
