#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import statistics
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory(prefix="snowflake-production-launch-")
os.environ.setdefault("BRAIN_DB", str(Path(TEMP.name) / "launch.sqlite"))
os.environ.setdefault("ACCOUNT_EMAIL_DELIVERY_MODE", "outbox")
os.environ.setdefault("AUTH_COOKIE_SECURE", "false")
os.environ.setdefault("FORCE_HTTPS", "false")
os.environ.setdefault("BILLING_ENABLED", "false")
os.environ.setdefault("GOOGLE_AUTH_ENABLED", "false")

from fastapi.testclient import TestClient  # noqa: E402

from app.config import DATABASE_BACKEND  # noqa: E402
from app.main import app  # noqa: E402


REQUIRED_PHASE_FILES = [
    "app/learning_intelligence.py",
    "app/postgres_backend.py",
    "app/observability.py",
    "app/account_lifecycle.py",
    "app/content_freshness.py",
    "app/question_editorial.py",
    "app/question_editorial_policy.py",
    "app/adaptive_readiness.py",
    "frontend/views/adaptive-v26.js",
    "scripts/test_account_lifecycle.py",
    "scripts/test_content_freshness_pipeline.py",
    "scripts/test_question_editorial_maturity.py",
    "scripts/test_adaptive_readiness_intelligence.py",
    ".github/workflows/content-freshness-scheduled.yml",
]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def check_file_inventory() -> dict:
    missing = [path for path in REQUIRED_PHASE_FILES if not (ROOT / path).exists()]
    if missing:
        raise AssertionError(f"Roadmap phase artifacts missing: {missing}")
    return {"name": "phase_artifact_inventory", "status": "pass", "files": len(REQUIRED_PHASE_FILES)}


def check_production_environment() -> dict:
    env = read("deploy/production.env.example")
    required_pairs = {
        "AUTH_COOKIE_SECURE": "true",
        "FORCE_HTTPS": "true",
        "SECURITY_RATE_LIMIT_ENABLED": "true",
        "ACCOUNT_EMAIL_DELIVERY_MODE": "webhook",
        "QUESTION_BANK_AUTO_IMPORT": "false",
    }
    for key, value in required_pairs.items():
        if f"{key}={value}" not in env:
            raise AssertionError(f"Production profile must set {key}={value}")
    if "DATABASE_URL=SET_IN_VERCEL_SECRET_STORE_ONLY" not in env:
        raise AssertionError("Production profile must require a Vercel-only PostgreSQL secret")
    if "OBSERVABILITY_METRICS_TOKEN=REPLACE_ME" not in env:
        raise AssertionError("Metrics token must be an explicit deployment secret")
    if "ACCOUNT_EMAIL_ACTION_BASE_URL=https://" not in env:
        raise AssertionError("Account actions must use a public HTTPS URL")
    compose = read("docker-compose.yml")
    if "DEVELOPMENT / CI ONLY — NOT PRODUCTION" not in compose:
        raise AssertionError("Docker Compose must be explicitly restricted to development/CI")
    return {"name": "production_environment", "status": "pass"}


def check_product_boundary() -> dict:
    tracked = "\n".join(
        path.as_posix() for path in (ROOT / "app").rglob("*.py")
    ) + "\n" + "\n".join(path.as_posix() for path in (ROOT / "frontend").rglob("*.js"))
    forbidden_paths = [ROOT / "app/routers/courses.py", ROOT / "app/ingest.py", ROOT / "frontend/views/quiz.js"]
    existing = [path.relative_to(ROOT).as_posix() for path in forbidden_paths if path.exists()]
    if existing:
        raise AssertionError(f"Legacy course/video runtime returned: {existing}")
    index = read("frontend/index-v26.html")
    if "<meta name=\"description\"" not in index or "<title>Snowflake Certification Guide</title>" not in index:
        raise AssertionError("Public shell is missing basic SEO title/description")
    if "Skip to content" not in index or "accessibility.css" not in index:
        raise AssertionError("Public shell is missing accessibility baseline")
    adaptive = read("frontend/views/adaptive-v26.js")
    if "not a probability" not in adaptive:
        raise AssertionError("Adaptive readiness must disclaim pass-probability interpretation")
    privacy = read("app/account_lifecycle.py")
    for token in ("account_export_payload", "delete_account", "account_deletion_receipts"):
        if token not in privacy:
            raise AssertionError(f"Privacy lifecycle primitive missing: {token}")
    return {"name": "certification_product_boundary", "status": "pass", "tracked_runtime_indexed": bool(tracked)}


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * p))))
    return ordered[index]


def check_runtime_security_and_load() -> dict:
    with TestClient(app) as client:
        health = client.get("/api/health")
        ready = client.get("/api/ready")
        if health.status_code != 200 or ready.status_code != 200:
            raise AssertionError(f"Health/readiness failed: {health.status_code}/{ready.status_code}")

        protected = [
            "/api/account/export",
            "/api/intelligence/adaptive/readiness",
            "/api/intelligence/due-today",
            "/api/mock/config",
        ]
        for path in protected:
            response = client.get(path)
            if response.status_code not in {401, 403}:
                raise AssertionError(f"Protected route is accessible without a candidate session: {path} -> {response.status_code}")

        metrics = client.get("/api/metrics")
        if metrics.status_code != 404:
            raise AssertionError("Metrics endpoint must be hidden when no infrastructure token is configured")

        response = client.get("/")
        security_headers = {key.lower(): value for key, value in response.headers.items()}
        for name in ("content-security-policy", "x-content-type-options", "referrer-policy"):
            if name not in security_headers:
                raise AssertionError(f"Missing production security header: {name}")

        registration = client.post(
            "/api/auth/register",
            json={
                "display_name": "Launch Gate Candidate",
                "email": "launch-gate@example.com",
                "password": "LaunchGatePassword!123",
            },
        )
        if registration.status_code != 201 or registration.json().get("email_verified") is not False:
            raise AssertionError(f"Account verification boundary failed: {registration.status_code} {registration.text}")

        # Lightweight request-load budget. Existing entitlement/schema tests cover
        # destructive races; this adds a broad HTTP concurrency and latency budget.
        samples: list[float] = []

        def hit_ready(_: int) -> int:
            started = time.perf_counter()
            result = client.get("/api/ready")
            samples.append((time.perf_counter() - started) * 1000)
            return result.status_code

        with ThreadPoolExecutor(max_workers=16) as executor:
            statuses = list(executor.map(hit_ready, range(96)))
        if any(status != 200 for status in statuses):
            raise AssertionError("Concurrent readiness load produced a non-200 response")
        p95 = percentile(samples, 0.95)
        if p95 > 1500:
            raise AssertionError(f"Readiness p95 exceeded launch budget: {p95:.1f} ms")

        sequential: list[float] = []
        for _ in range(40):
            started = time.perf_counter()
            result = client.get("/api/health")
            if result.status_code != 200:
                raise AssertionError("Health endpoint failed during latency budget")
            sequential.append((time.perf_counter() - started) * 1000)
        health_p95 = percentile(sequential, 0.95)
        if health_p95 > 500:
            raise AssertionError(f"Health p95 exceeded launch budget: {health_p95:.1f} ms")

    return {
        "name": "runtime_security_load",
        "status": "pass",
        "backend": DATABASE_BACKEND,
        "concurrent_requests": 96,
        "ready_p95_ms": round(p95, 2),
        "health_p95_ms": round(health_p95, 2),
        "ready_median_ms": round(statistics.median(samples), 2),
    }


def main() -> None:
    output_dir = ROOT / "artifacts"
    output_dir.mkdir(exist_ok=True)
    checks = []
    try:
        checks.extend([
            check_file_inventory(),
            check_production_environment(),
            check_product_boundary(),
            check_runtime_security_and_load(),
        ])
        report = {
            "status": "pass",
            "blocking_items": 0,
            "database_backend": DATABASE_BACKEND,
            "checks": checks,
        }
        (output_dir / "production-readiness-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
        print("Production launch convergence: PASS (0 blocking items)")
    finally:
        TEMP.cleanup()


if __name__ == "__main__":
    main()
