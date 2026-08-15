#!/usr/bin/env python3
from __future__ import annotations

import json
import logging
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory(prefix="snowflake-observability-")
os.environ["BRAIN_DB"] = str(Path(TEMP.name) / "observability.sqlite")
os.environ["OBSERVABILITY_ENABLED"] = "true"
os.environ["OBSERVABILITY_METRICS_TOKEN"] = "observability-test-token"
os.environ["OBSERVABILITY_5XX_ALERT_THRESHOLD"] = "2"
os.environ["OBSERVABILITY_AUTH_FAILURE_ALERT_THRESHOLD"] = "2"
os.environ["OBSERVABILITY_ALERT_COOLDOWN_SECONDS"] = "30"
os.environ["OBSERVABILITY_ERROR_WEBHOOK_URL"] = ""
os.environ["OBSERVABILITY_ALERT_WEBHOOK_URL"] = ""

from fastapi.testclient import TestClient  # noqa: E402

from app.database import connect  # noqa: E402
from app.main import app  # noqa: E402
from app.observability import (  # noqa: E402
    JsonFormatter,
    metrics_snapshot,
    metrics_token_matches,
    record_background_failure,
    record_exam_event,
    record_readiness_failure,
    record_release_event,
    record_request,
    record_stripe_webhook_failure,
    redact,
    report_exception,
    request_id_from_header,
    reset_observability_for_tests,
)


def check_redaction() -> None:
    payload = redact(
        {
            "password": "super-secret",
            "authorization": "Bearer abc",
            "cookie": "session=xyz",
            "stripe_signature": "sig",
            "selected": [1, 2],
            "safe": "visible",
            "nested": {"token_hash": "secret-token", "operation": "login"},
        }
    )
    assert payload["password"] == "[REDACTED]"
    assert payload["authorization"] == "[REDACTED]"
    assert payload["cookie"] == "[REDACTED]"
    assert payload["stripe_signature"] == "[REDACTED]"
    assert payload["selected"] == "[REDACTED]"
    assert payload["nested"]["token_hash"] == "[REDACTED]"
    assert payload["safe"] == "visible"

    formatter = JsonFormatter()
    record = logging.LogRecord("test", logging.INFO, __file__, 1, "event", (), None)
    record.event = "safe_event"
    record.request_id = "request-test-123"
    record.fields = {"password": "must-not-leak", "safe": "ok"}
    rendered = formatter.format(record)
    assert "must-not-leak" not in rendered
    decoded = json.loads(rendered)
    assert decoded["fields"]["password"] == "[REDACTED]"
    assert decoded["request_id"] == "request-test-123"


def check_request_id_helpers() -> None:
    preserved = request_id_from_header("client-request-123")
    assert preserved == "client-request-123"
    replaced = request_id_from_header("bad id with spaces")
    assert replaced != "bad id with spaces"
    assert re.fullmatch(r"[0-9a-f]{32}", replaced)
    assert metrics_token_matches("Bearer observability-test-token", "observability-test-token")
    assert not metrics_token_matches("Bearer wrong-token", "observability-test-token")


def check_live_middleware_and_metrics() -> None:
    reset_observability_for_tests()
    with TestClient(app) as client:
        supplied = client.get("/api/health", headers={"X-Request-ID": "client-request-456"})
        assert supplied.status_code == 200
        assert supplied.headers["x-request-id"] == "client-request-456"
        assert supplied.json()["observability"] == "structured-v1"

        malformed = client.get("/api/ready", headers={"X-Request-ID": "not valid id"})
        assert malformed.status_code == 200
        generated = malformed.headers["x-request-id"]
        assert generated != "not valid id"
        assert re.fullmatch(r"[0-9a-f]{32}", generated)

        denied_metrics = client.get("/api/metrics")
        assert denied_metrics.status_code == 401
        wrong_metrics = client.get("/api/metrics", headers={"Authorization": "Bearer wrong"})
        assert wrong_metrics.status_code == 401

        # Invalid credentials are monitored as an auth-failure signal without
        # logging the supplied email/password.
        for _ in range(2):
            login = client.post(
                "/api/auth/login",
                json={"email": "does-not-exist@example.com", "password": "NotThePassword123!"},
            )
            assert login.status_code == 401

        with connect() as conn:
            assert int(conn.execute("SELECT 1 AS ok").fetchone()["ok"]) == 1

        authorized = client.get(
            "/api/metrics",
            headers={"Authorization": "Bearer observability-test-token"},
        )
        assert authorized.status_code == 200
        snapshot = authorized.json()
        assert snapshot["counters"]["http.requests.total"] >= 6
        assert snapshot["counters"]["auth.failures.total"] == 2
        assert snapshot["recent_failures"]["auth_failures"] == 2
        assert snapshot["counters"]["db.operations.total"] > 0
        assert any(key.startswith("http.route.GET /api/health") for key in snapshot["latency"])
        assert any(key.startswith("db.operation.sqlite.SELECT") for key in snapshot["latency"])


def check_alert_and_operational_signals() -> None:
    reset_observability_for_tests()
    record_request("GET", "/api/test", 500, 12.5)
    record_request("GET", "/api/test", 500, 9.0)
    # Third event remains inside the alert cooldown and must not create a storm.
    record_request("GET", "/api/test", 500, 4.0)
    record_stripe_webhook_failure("signature_invalid")
    record_exam_event("start", "success")
    record_exam_event("submit", "failure")
    record_release_event("activate", "success", release_key="release-test")
    record_release_event("activate", "failure", release_key="release-test-bad")
    record_readiness_failure("database", error_type="ConnectionError")
    record_background_failure("content_import", RuntimeError("secret message must not be emitted"))
    report_exception(RuntimeError("candidate@example.com private detail"), route="/api/test", method="GET", duration_ms=3.2)

    snapshot = metrics_snapshot()
    assert snapshot["counters"]["http.status.5xx"] == 3
    assert snapshot["counters"]["alert.api_5xx"] == 1
    assert snapshot["counters"]["stripe.webhook.failures.total"] == 1
    assert snapshot["counters"]["exam.start.success"] == 1
    assert snapshot["counters"]["exam.submit.failure"] == 1
    assert snapshot["counters"]["release.activate.success"] == 1
    assert snapshot["counters"]["release.activate.failure"] == 1
    assert snapshot["counters"]["readiness.failure.database"] == 1
    assert snapshot["counters"]["background.content_import.failure"] == 1
    assert snapshot["counters"]["exception.unhandled"] == 1


def main() -> None:
    try:
        check_redaction()
        check_request_id_helpers()
        check_live_middleware_and_metrics()
        check_alert_and_operational_signals()
        print("Production observability: PASS (request IDs, safe JSON logs, metrics, DB timing, alerts, feature signals)")
    finally:
        TEMP.cleanup()


if __name__ == "__main__":
    main()
