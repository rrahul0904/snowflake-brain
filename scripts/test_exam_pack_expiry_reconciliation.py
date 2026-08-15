#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory(prefix="snowflake-pack-expiry-reconcile-")
os.environ["BRAIN_DB"] = str(Path(TEMP.name) / "pack-expiry.sqlite")
os.environ["SECURITY_RATE_LIMIT_ENABLED"] = "false"

from fastapi.testclient import TestClient  # noqa: E402
from app.database import connect, run_migrations  # noqa: E402
from app.entitlements import apply_membership_plan  # noqa: E402
from app.identity_billing_schema import ensure_identity_billing_schema  # noqa: E402
from app.main import app  # noqa: E402


def check(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    run_migrations()
    ensure_identity_billing_schema()
    client = TestClient(app)
    response = client.post(
        "/api/auth/register",
        json={"display_name": "Pack Reconcile", "email": "pack-reconcile@example.com", "password": "candidate-password"},
    )
    check(response.status_code == 201, response.text)
    candidate_id = int(response.json()["candidate"]["id"])

    purchased_at = datetime.now(timezone.utc) - timedelta(days=20)
    with connect() as conn:
        conn.execute(
            "INSERT INTO billing_purchases(candidate_id,provider,provider_payment_id,product_type,status,purchased_at) "
            "VALUES (?,'stripe','pi_reconcile','exam_pack_35','paid',?)",
            (candidate_id, purchased_at.isoformat()),
        )

    # A subscription temporarily becomes the effective entitlement.
    apply_membership_plan(
        candidate_id,
        "premium_20",
        source="stripe_webhook",
        reason="subscription_active",
        expires_at=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
    )
    check(client.get("/api/auth/me").json()["membership"]["plan_code"] == "premium_20", "subscription effective before expiry")

    # Simulate time passing without a new provider event by making the stored
    # membership expiry older than now. auth/me's existing expiry cleanup updates
    # the membership to expired; the DB trigger must immediately restore the
    # already-paid Exam Pack.
    with connect() as conn:
        conn.execute(
            "UPDATE candidate_memberships SET expires_at=? WHERE candidate_id=? AND status='active' AND plan_code='premium_20'",
            ((datetime.now(timezone.utc) - timedelta(seconds=5)).isoformat(), candidate_id),
        )

    resolved = client.get("/api/auth/me")
    check(resolved.status_code == 200, resolved.text)
    membership = resolved.json()["membership"]
    check(membership["plan_code"] == "exam_pack_35", "paid Exam Pack automatically restored after timed subscription expiry")
    deadline = membership["usage"]["monthly_full_exams"]["access_expires_at"]
    expected_date = (purchased_at + timedelta(days=30)).date().isoformat()
    check(expected_date in deadline, "restored Exam Pack keeps original purchase-based Full Exam deadline")

    with connect() as conn:
        active = conn.execute(
            "SELECT plan_code,source,entitlement_version FROM candidate_memberships WHERE candidate_id=? AND status='active' ORDER BY id DESC LIMIT 1",
            (candidate_id,),
        ).fetchone()
        audit = conn.execute(
            "SELECT reason,source FROM membership_audit_log WHERE candidate_id=? ORDER BY id DESC LIMIT 1",
            (candidate_id,),
        ).fetchone()
    check(active and active["plan_code"] == "exam_pack_35", "restored entitlement persisted")
    check(active["source"] == "entitlement_reconciliation", "reconciliation source recorded")
    check(audit and audit["reason"] == "expired_subscription_exam_pack_fallback", "reconciliation audit written")

    print("Exam Pack expiry reconciliation checks passed.")


if __name__ == "__main__":
    main()
