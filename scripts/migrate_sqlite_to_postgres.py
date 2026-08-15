#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any


TABLE_ORDER = [
    "certification_tracks",
    "certification_task_progress",
    "candidate_accounts",
    "candidate_sessions",
    "membership_events",
    "candidate_memberships",
    "practice_tests",
    "questions",
    "question_versions",
    "question_skill_map",
    "question_attempts",
    "exam_sessions",
    "exam_session_questions",
    "exam_session_answers",
    "question_bank_metadata",
    "question_exposure_stats",
    "candidate_question_history",
    "candidate_task_progress",
    "candidate_daily_activity",
    "candidate_daily_question_usage",
    "candidate_exam_pack_sets",
    "candidate_exam_pack_set_questions",
    "question_bank_imports",
    "candidate_bookmarks",
    "candidate_notes",
    "bookmarks",
    "notes",
    "daily_activity",
    "learning_events",
    "candidate_identities",
    "oauth_login_flows",
    "pending_identity_links",
    "billing_customers",
    "billing_checkout_sessions",
    "billing_subscriptions",
    "billing_purchases",
    "billing_events",
    "membership_audit_log",
    "question_bank_releases",
    "question_bank_release_questions",
    "question_bank_release_events",
    "candidate_srs_state",
    "candidate_mistake_notebook",
    "candidate_study_preferences",
    "candidate_learning_attempt_sync",
    "exam_entitlement_reservations",
    "feedback_submissions",
]

SERIAL_TABLES = {
    "candidate_accounts",
    "candidate_sessions",
    "membership_events",
    "candidate_memberships",
    "candidate_bookmarks",
    "candidate_notes",
    "question_attempts",
    "exam_sessions",
    "exam_session_answers",
    "question_bank_imports",
    "candidate_question_history",
    "candidate_exam_pack_sets",
    "bookmarks",
    "notes",
    "learning_events",
    "candidate_identities",
    "billing_customers",
    "billing_checkout_sessions",
    "billing_subscriptions",
    "billing_purchases",
    "billing_events",
    "membership_audit_log",
    "question_versions",
    "question_bank_releases",
    "question_bank_release_events",
    "exam_entitlement_reservations",
    "feedback_submissions",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Copy the certification-native SQLite database into the configured PostgreSQL database."
    )
    parser.add_argument("--sqlite", required=True, help="Path to the source SQLite database")
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL", ""),
        help="PostgreSQL URL (defaults to DATABASE_URL)",
    )
    parser.add_argument("--schema", default=os.getenv("DATABASE_SCHEMA", "public"))
    parser.add_argument(
        "--allow-nonempty",
        action="store_true",
        help="Allow migration into a target that already contains candidate/question rows",
    )
    return parser.parse_args()


def sqlite_tables(conn: sqlite3.Connection) -> set[str]:
    return {
        str(row[0])
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        if not str(row[0]).startswith("sqlite_")
    }


def sqlite_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [str(row[1]) for row in conn.execute(f'PRAGMA table_info("{table}")')]


def postgres_columns(conn: Any, table: str) -> list[str]:
    rows = conn.execute(
        """
        SELECT column_name
          FROM information_schema.columns
         WHERE table_schema=current_schema() AND table_name=%s
         ORDER BY ordinal_position
        """,
        (table,),
    ).fetchall()
    return [str(row["column_name"]) for row in rows]


def copy_table(source: sqlite3.Connection, target: Any, table: str) -> int:
    source_columns = sqlite_columns(source, table)
    target_columns = set(postgres_columns(target, table))
    columns = [column for column in source_columns if column in target_columns]
    if not columns:
        return 0

    quoted = ",".join(f'"{column}"' for column in columns)
    rows = source.execute(f'SELECT {quoted} FROM "{table}"').fetchall()
    if not rows:
        return 0

    placeholders = ",".join("%s" for _ in columns)
    updates = ",".join(f'"{column}"=excluded."{column}"' for column in columns)
    statement = (
        f'INSERT INTO "{table}" ({quoted}) VALUES ({placeholders}) '
        f'ON CONFLICT DO NOTHING'
    )
    with target.cursor() as cursor:
        cursor.executemany(statement, [tuple(row[column] for column in columns) for row in rows])
    return len(rows)


def reset_sequence(conn: Any, table: str) -> None:
    row = conn.execute("SELECT pg_get_serial_sequence(%s, 'id') AS seq", (table,)).fetchone()
    sequence = row["seq"] if row else None
    if not sequence:
        return
    maximum = conn.execute(f'SELECT COALESCE(MAX(id),0) AS maximum FROM "{table}"').fetchone()["maximum"]
    if int(maximum or 0) > 0:
        conn.execute("SELECT setval(%s::regclass,%s,true)", (sequence, int(maximum)))
    else:
        conn.execute("SELECT setval(%s::regclass,1,false)", (sequence,))


def main() -> None:
    args = parse_args()
    source_path = Path(args.sqlite).expanduser().resolve()
    if not source_path.exists():
        raise SystemExit(f"SQLite source does not exist: {source_path}")
    if not args.database_url.lower().startswith(("postgresql://", "postgres://")):
        raise SystemExit("--database-url / DATABASE_URL must be PostgreSQL")

    # Configure the application before importing its database layer.
    os.environ["DATABASE_URL"] = args.database_url
    os.environ["DATABASE_SCHEMA"] = args.schema
    os.environ["POSTGRES_TEST_ISOLATION"] = "false"

    from app.database import run_migrations  # noqa: WPS433
    from app.postgres_backend import current_schema_name, get_conn  # noqa: WPS433

    run_migrations()
    source = sqlite3.connect(source_path)
    source.row_factory = sqlite3.Row
    source.execute("PRAGMA foreign_keys=ON")
    available = sqlite_tables(source)

    target_adapter = get_conn()
    target = target_adapter.raw_connection
    try:
        target.execute("SET search_path TO " + '"' + current_schema_name().replace('"', '""') + '"' + ", public")
        if not args.allow_nonempty:
            candidate_count = target.execute("SELECT COUNT(*) AS n FROM candidate_accounts").fetchone()["n"]
            question_count = target.execute("SELECT COUNT(*) AS n FROM questions").fetchone()["n"]
            if int(candidate_count or 0) or int(question_count or 0):
                raise SystemExit(
                    "Target PostgreSQL schema is not empty. Use a fresh schema/database or pass --allow-nonempty intentionally."
                )

        copied: dict[str, int] = {}
        for table in TABLE_ORDER:
            if table not in available:
                continue
            # Inserting questions fires the production version trigger. Remove
            # generated baseline versions immediately before restoring the
            # source's authoritative immutable version IDs.
            if table == "question_versions":
                target.execute("DELETE FROM question_versions")
            copied[table] = copy_table(source, target, table)

        for table in SERIAL_TABLES:
            if table in postgres_columns_cache(target):
                reset_sequence(target, table)

        target.commit()
        total = sum(copied.values())
        print(f"SQLite -> PostgreSQL migration complete: {total} rows into schema {current_schema_name()}.")
        for table, count in copied.items():
            print(f"  {table}: {count}")
    except Exception:
        target.rollback()
        raise
    finally:
        source.close()
        target_adapter.close()


def postgres_columns_cache(conn: Any) -> set[str]:
    return {
        str(row["table_name"])
        for row in conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema=current_schema()"
        ).fetchall()
    }


if __name__ == "__main__":
    sys.exit(main())
