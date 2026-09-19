#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory(prefix="snowflake-daily-recall-")
os.environ["BRAIN_DB"] = str(Path(TEMP.name) / "daily-recall.sqlite")
os.environ["SECURITY_RATE_LIMIT_ENABLED"] = "false"
os.environ["ACCOUNT_EMAIL_DELIVERY_MODE"] = "outbox"
os.environ["BILLING_ENABLED"] = "false"
os.environ["GOOGLE_AUTH_ENABLED"] = "false"

from fastapi.testclient import TestClient  # noqa: E402
from app.database import connect, run_migrations  # noqa: E402
from app.main import app  # noqa: E402


def check(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    run_migrations()
    client = TestClient(app)
    signup = client.post(
        "/api/auth/register",
        json={
            "display_name": "Daily Recall Candidate",
            "email": "daily-recall@example.com",
            "password": "DailyRecallPassword!123",
        },
    )
    check(signup.status_code == 201, signup.text)
    candidate_id = int((signup.json().get("candidate") or {}).get("id") or 0)
    check(candidate_id > 0, "candidate id missing")

    empty = client.get("/api/intelligence/daily-streak?track_id=snowpro-core")
    check(empty.status_code == 200, empty.text)
    check(empty.json()["streak_days"] == 0, "new candidate streak must start at zero")

    skill_map = client.get("/api/skills/map")
    check(skill_map.status_code == 200, skill_map.text)
    certifications = skill_map.json().get("certifications") or []
    core = next((row for row in certifications if row.get("id") == "snowpro-core"), None)
    check(core is not None, "SnowPro Core skill map is missing")
    configured_skills = [
        str(skill.get("id") or "")
        for domain in (core.get("domains") or [])
        for skill in (domain.get("skills") or [])
        if skill.get("id")
    ]
    check(configured_skills, "SnowPro Core has no configured recall tasks")
    primary_skill = configured_skills[0]

    invalid = client.post(
        "/api/intelligence/daily-recall",
        json={"track_id": "snowpro-core", "skill_id": "fabricated-task"},
    )
    check(invalid.status_code == 404, "fabricated recall task must be rejected")

    first = client.post(
        "/api/intelligence/daily-recall",
        json={"track_id": "snowpro-core", "skill_id": primary_skill},
    )
    check(first.status_code == 200, first.text)
    check(first.json()["recorded"] is True, "first daily recall should persist")
    check(first.json()["streak_days"] == 1, "today's first recall should start a one-day streak")
    check(first.json()["completed_today"] == 1, "today's recall count is incorrect")

    duplicate = client.post(
        "/api/intelligence/daily-recall",
        json={"track_id": "snowpro-core", "skill_id": "snowflake-architecture"},
    )
    check(duplicate.status_code == 200, duplicate.text)
    check(duplicate.json()["recorded"] is False, "same skill/day recall must be idempotent")
    check(duplicate.json()["completed_today"] == 1, "duplicate recall inflated today's count")

    now = datetime.now(timezone.utc)
    with connect() as conn:
        for offset, skill in ((1, configured_skills[min(1, len(configured_skills) - 1)]), (2, configured_skills[min(2, len(configured_skills) - 1)])):
            created = (now - timedelta(days=offset)).strftime("%Y-%m-%d %H:%M:%S")
            conn.execute(
                """
                INSERT INTO learning_events(event_type,track_id,skill_id,metadata_json,candidate_id,created_at)
                VALUES ('daily_recall_completed','snowpro-core',?,'{}',?,?)
                """,
                (skill, candidate_id, created),
            )

    persisted = client.get("/api/intelligence/daily-streak?track_id=snowpro-core")
    check(persisted.status_code == 200, persisted.text)
    body = persisted.json()
    check(body["streak_days"] == 3, f"expected three persisted consecutive days: {body}")
    check(primary_skill in body["today_skill_ids"], "today skill state is not persisted")

    view = (ROOT / "frontend" / "views" / "daily-session-v26.js").read_text(encoding="utf-8")
    check("localStorage" not in view, "daily recall must not fall back to browser-local persistence")
    check("recordDailyRecall" in view and "getDailyStreak" in view, "daily view is not wired to persisted APIs")

    print("Persisted Clouding daily recall streak: PASS")


if __name__ == "__main__":
    try:
        main()
    finally:
        TEMP.cleanup()
