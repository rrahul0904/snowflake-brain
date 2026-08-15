#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory(prefix="snowflake-google-continuity-")
os.environ["BRAIN_DB"] = str(Path(TEMP.name) / "continuity.sqlite")
os.environ["SECURITY_RATE_LIMIT_ENABLED"] = "false"

from fastapi import HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from app.auth import (  # noqa: E402
    GOOGLE_LINK_COOKIE,
    candidate_by_google_subject,
    create_pending_google_link,
    link_google_identity,
)
from app.database import connect, run_migrations  # noqa: E402
from app.entitlements import apply_membership_plan  # noqa: E402
from app.identity_billing_schema import ensure_identity_billing_schema  # noqa: E402
from app.main import app  # noqa: E402


def check(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def register(client: TestClient, name: str, email: str) -> int:
    response = client.post(
        "/api/auth/register",
        json={"display_name": name, "email": email, "password": "candidate-password"},
    )
    check(response.status_code == 201, response.text)
    return int(response.json()["candidate"]["id"])


def main() -> None:
    run_migrations()
    ensure_identity_billing_schema()

    client = TestClient(app)
    candidate_id = register(client, "Continuity Candidate", "continuity@example.com")
    apply_membership_plan(candidate_id, "premium_40", source="test", reason="continuity_premium")

    # Persist representative candidate-owned learning state before Google is linked.
    with connect() as conn:
        conn.execute(
            "INSERT INTO candidate_task_progress(candidate_id,track_id,skill_id,completed) VALUES (?,?,?,1)",
            (candidate_id, "snowpro-core", "1.1"),
        )

    mock = client.post(
        "/api/mock/sessions",
        json={"track_id": "snowpro-core", "mode": "quick-mock"},
    )
    check(mock.status_code == 200, mock.text)
    session_id = int(mock.json()["session_id"])
    submitted = client.post(
        f"/api/mock/sessions/{session_id}/submit",
        json={"reason": "learner"},
    )
    check(submitted.status_code == 200, submitted.text)

    before = client.get("/api/auth/me").json()
    check(before["membership"]["plan_code"] == "premium_40", "Premium 250 active before linking")

    pending = create_pending_google_link(candidate_id, "google-sub-continuity", "continuity@example.com")
    client.cookies.set(GOOGLE_LINK_COOKIE, pending)
    linked = client.post("/api/auth/google/link", json={"password": "candidate-password"})
    check(linked.status_code == 200, linked.text)
    linked_payload = linked.json()
    check(int(linked_payload["candidate"]["id"]) == candidate_id, "Google link preserves candidate ID")
    check(linked_payload["membership"]["plan_code"] == "premium_40", "Google link preserves paid tier")
    check(set(linked_payload["candidate"]["sign_in_methods"]) == {"email", "google"}, "both sign-in methods resolve to one account")

    returning = candidate_by_google_subject("google-sub-continuity")
    check(returning is not None and int(returning["id"]) == candidate_id, "returning Google subject resolves same candidate")
    check(returning["membership"]["plan_code"] == "premium_40", "returning Google identity resolves same membership")

    progress = client.get("/api/skills/task-progress", params={"track_id": "snowpro-core"})
    check(progress.status_code == 200, progress.text)
    progress_rows = progress.json().get("tasks") or progress.json().get("progress") or progress.json()
    check(progress_rows is not None, "progress remains readable after linking")
    with connect() as conn:
        stored_progress = conn.execute(
            "SELECT completed FROM candidate_task_progress WHERE candidate_id=? AND skill_id='1.1'",
            (candidate_id,),
        ).fetchone()
    check(stored_progress and int(stored_progress["completed"]) == 1, "stored progress remains on same candidate")

    history = client.get("/api/mock/history", params={"track_id": "snowpro-core"})
    check(history.status_code == 200, history.text)
    history_payload = history.json()
    history_rows = history_payload.get("history") or history_payload.get("sessions") or []
    check(any(int(row.get("session_id") or row.get("id") or 0) == session_id for row in history_rows), "completed mock history survives Google linking")

    # The same Google provider subject cannot be attached to another candidate.
    other = TestClient(app)
    other_id = register(other, "Other Candidate", "other-continuity@example.com")
    try:
        link_google_identity(other_id, "google-sub-continuity", "other-continuity@example.com", True)
        raise AssertionError("same Google subject should not link to a second candidate")
    except HTTPException as error:
        check(error.status_code == 409, "provider subject uniqueness prevents duplicate account binding")

    print("Google identity continuity checks passed.")


if __name__ == "__main__":
    main()
