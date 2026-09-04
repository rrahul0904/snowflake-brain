#!/usr/bin/env python3
"""Record one UTC aggregate daily operations snapshot without PII."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.admin_operations import ensure_admin_operations_schema, overview
from app.account_lifecycle import ensure_account_lifecycle_schema
from app.database import connect, run_migrations
from app.identity_billing_schema import ensure_identity_billing_schema
from app.question_bank_releases import ensure_question_bank_release_schema
from app.adaptive_readiness import ensure_adaptive_readiness_schema
from app.task_review import _ensure_task_review_schema


def main() -> int:
    run_migrations()
    ensure_identity_billing_schema()
    ensure_account_lifecycle_schema()
    ensure_question_bank_release_schema()
    ensure_adaptive_readiness_schema()
    ensure_admin_operations_schema()
    report = overview()
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    users, learning, subscriptions, finops = report["users"], report["learning"], report["subscriptions"], report["finops"]
    today_cutoff = datetime.now(timezone.utc).strftime("%Y-%m-%d 00:00:00")
    with connect() as conn:
        _ensure_task_review_schema(conn)
        review_completions = conn.execute(
            "SELECT COUNT(*) AS value FROM candidate_task_reviews WHERE last_reviewed_at>=?", (today_cutoff,)
        ).fetchone()["value"]
        readiness = conn.execute(
            "SELECT AVG(readiness_score) AS value FROM candidate_readiness_snapshots"
        ).fetchone()["value"]
        new_subscribers = conn.execute(
            "SELECT COUNT(*) AS value FROM billing_subscriptions WHERE created_at>=?", (today_cutoff,)
        ).fetchone()["value"]
        conn.execute(
            "INSERT INTO operations_daily_snapshots(snapshot_date,registrations,active_users,paid_users,new_subscribers,mrr,revenue,questions_answered,mock_submissions,average_readiness,estimated_cost,daily_active_users,weekly_active_users,monthly_active_users,practice_sessions,review_completions) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(snapshot_date) DO UPDATE SET registrations=excluded.registrations,active_users=excluded.active_users,paid_users=excluded.paid_users,new_subscribers=excluded.new_subscribers,mrr=excluded.mrr,revenue=excluded.revenue,questions_answered=excluded.questions_answered,mock_submissions=excluded.mock_submissions,average_readiness=excluded.average_readiness,estimated_cost=excluded.estimated_cost,daily_active_users=excluded.daily_active_users,weekly_active_users=excluded.weekly_active_users,monthly_active_users=excluded.monthly_active_users,practice_sessions=excluded.practice_sessions,review_completions=excluded.review_completions",
            (date, users["today"], users["active_today"], subscriptions["active"], new_subscribers, subscriptions["mrr"], None, learning["questions_today"], learning["mocks_completed"], readiness, finops["monthly_cost"], users["active_today"], users["active_seven_days"], users["active_thirty_days"], learning["sessions_today"], review_completions),
        )
    print(json.dumps({"snapshot_date": date, "registrations": users["today"], "paid_users": subscriptions["active"], "daily_active_users": users["active_today"], "review_completions": review_completions}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
