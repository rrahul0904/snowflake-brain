#!/usr/bin/env python3
"""Explicitly promote one existing candidate to administrator.

This is a controlled operations command, never an application endpoint. In
PostgreSQL it requires the deployment-only migration credential, ensuring a
request-serving runtime account cannot promote anyone.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import DATABASE_BACKEND, DATABASE_MIGRATION_URL, DATABASE_SCHEMA
from app.database import connect


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Promote exactly one existing candidate to administrator.")
    parser.add_argument("--email", required=True, help="Exact existing candidate email")
    parser.add_argument("--confirm-promote", action="store_true", help="Required explicit confirmation")
    args = parser.parse_args()
    if not args.confirm_promote:
        parser.error("--confirm-promote is required; no account was changed")
    args.email = args.email.strip().lower()
    if not args.email:
        parser.error("--email must not be empty")
    return args


def promote_sqlite(email: str) -> dict[str, int | str]:
    with connect() as conn:
        row = conn.execute("SELECT id FROM candidate_accounts WHERE email=? COLLATE NOCASE", (email,)).fetchone()
        if not row:
            raise LookupError("No candidate account exists for the supplied email")
        candidate_id = int(dict(row)["id"])
        conn.execute("UPDATE candidate_accounts SET role='admin' WHERE id=?", (candidate_id,))
        conn.execute(
            "INSERT INTO admin_audit_events(actor_candidate_id,event,target_type,target_id,result,metadata_json) VALUES (?,?,?,?,?,?)",
            (candidate_id, "admin.role.promoted", "candidate_account", str(candidate_id), "success", '{"source":"promote_admin"}'),
        )
    return {"candidate_id": candidate_id, "email": email}


def promote_postgres(email: str) -> dict[str, int | str]:
    if not DATABASE_MIGRATION_URL:
        raise RuntimeError("DATABASE_MIGRATION_URL is required for PostgreSQL admin promotion")
    from psycopg import connect as pg_connect, sql
    from psycopg.rows import dict_row

    with pg_connect(DATABASE_MIGRATION_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql.SQL("SET LOCAL search_path TO {}, public").format(sql.Identifier(DATABASE_SCHEMA)))
            cursor.execute("SELECT id FROM candidate_accounts WHERE lower(email)=lower(%s)", (email,))
            row = cursor.fetchone()
            if not row:
                raise LookupError("No candidate account exists for the supplied email")
            candidate_id = int(row["id"])
            cursor.execute("UPDATE candidate_accounts SET role='admin' WHERE id=%s", (candidate_id,))
            cursor.execute(
                "INSERT INTO admin_audit_events(actor_candidate_id,event,target_type,target_id,result,metadata_json) VALUES (%s,%s,%s,%s,%s,%s)",
                (candidate_id, "admin.role.promoted", "candidate_account", str(candidate_id), "success", '{"source":"promote_admin"}'),
            )
    return {"candidate_id": candidate_id, "email": email}


def main() -> int:
    args = parse_args()
    try:
        result = promote_postgres(args.email) if DATABASE_BACKEND == "postgresql" else promote_sqlite(args.email)
    except (LookupError, RuntimeError) as exc:
        print(f"Admin promotion refused: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"status": "promoted", **result}, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
