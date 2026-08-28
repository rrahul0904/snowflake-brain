#!/usr/bin/env python3
"""Read-only hosted runtime soak and browser-security-header verification.

This probe is safe for Preview and Production. It performs only GET requests,
never authenticates, never persists response bodies, and records only status,
headers needed for the security contract, response sizes, and SHA-256 digests.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts" / "hosted-runtime-security.json"
BASE = os.environ.get("SECURITY_BASE_URL", "https://snowflakecertificationguide.vercel.app").rstrip("/")
SOAK_REQUESTS = max(1, min(100, int(os.environ.get("SOAK_REQUESTS", "20"))))
SOAK_DELAY_SECONDS = max(0.0, min(10.0, float(os.environ.get("SOAK_DELAY_SECONDS", "0.15"))))
EXPECTED_BACKEND = os.environ.get("EXPECTED_DATABASE_BACKEND", "postgresql").strip().lower()


def digest(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def snapshot(response: httpx.Response) -> dict[str, object]:
    return {
        "status": response.status_code,
        "bytes": len(response.content),
        "sha256": digest(response.content),
        "content_type": response.headers.get("content-type", "").split(";", 1)[0],
        "cache_control": response.headers.get("cache-control", ""),
        "x_vercel_cache": response.headers.get("x-vercel-cache", ""),
    }


def main() -> None:
    findings: list[str] = []
    probes: list[dict[str, object]] = []
    header_evidence: dict[str, str] = {}

    with httpx.Client(follow_redirects=True, timeout=20.0) as client:
        for index in range(SOAK_REQUESTS):
            for path, expected_status in (("/api/health", 200), ("/api/ready", 200)):
                try:
                    response = client.get(f"{BASE}{path}")
                except Exception as exc:
                    findings.append(f"{path}:request_error:{type(exc).__name__}")
                    continue
                row = {"iteration": index + 1, "path": path, **snapshot(response)}
                probes.append(row)
                if response.status_code != expected_status:
                    findings.append(f"{path}:status:{response.status_code}")
                    continue
                try:
                    payload = response.json()
                except Exception:
                    findings.append(f"{path}:non_json_response")
                    continue
                if path == "/api/health":
                    if payload.get("status") != "ok":
                        findings.append("health:status_not_ok")
                    if EXPECTED_BACKEND and str(payload.get("database_backend", "")).lower() != EXPECTED_BACKEND:
                        findings.append("health:unexpected_database_backend")
                else:
                    if payload.get("status") != "ready":
                        findings.append("ready:status_not_ready")
                    database = payload.get("database") or {}
                    if not isinstance(database, dict) or database.get("status") != "ok":
                        findings.append("ready:database_not_ok")
                    elif EXPECTED_BACKEND and str(database.get("backend", "")).lower() != EXPECTED_BACKEND:
                        findings.append("ready:unexpected_database_backend")
            if index + 1 < SOAK_REQUESTS and SOAK_DELAY_SECONDS:
                time.sleep(SOAK_DELAY_SECONDS)

        try:
            home = client.get(f"{BASE}/")
        except Exception as exc:
            findings.append(f"home:request_error:{type(exc).__name__}")
        else:
            probes.append({"iteration": 1, "path": "/", **snapshot(home)})
            if home.status_code != 200:
                findings.append(f"home:status:{home.status_code}")
            required_headers = {
                "content-security-policy": None,
                "x-content-type-options": "nosniff",
                "x-frame-options": "DENY",
                "referrer-policy": None,
                "permissions-policy": None,
            }
            if BASE.lower().startswith("https://"):
                required_headers["strict-transport-security"] = None
            for name, exact in required_headers.items():
                value = home.headers.get(name, "")
                header_evidence[name] = value
                if not value:
                    findings.append(f"home:missing_header:{name}")
                elif exact is not None and value.lower() != exact.lower():
                    findings.append(f"home:invalid_header:{name}")
            csp = home.headers.get("content-security-policy", "").lower()
            if csp and "frame-ancestors 'none'" not in csp:
                findings.append("home:csp_frame_ancestors_not_none")
            if "*" in csp:
                findings.append("home:csp_contains_wildcard")

    payload = {
        "status": "pass" if not findings else "fail",
        "base_url": BASE,
        "soak_requests": SOAK_REQUESTS,
        "expected_database_backend": EXPECTED_BACKEND,
        "probe_count": len(probes),
        "probes": probes,
        "security_headers": header_evidence,
        "finding_count": len(findings),
        "findings": sorted(set(findings)),
    }
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in payload.items() if k != "probes"}, indent=2))
    if findings:
        raise SystemExit("Hosted runtime security soak failed; see redacted artifact evidence")


if __name__ == "__main__":
    main()
