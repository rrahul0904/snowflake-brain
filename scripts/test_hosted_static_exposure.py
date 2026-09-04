#!/usr/bin/env python3
"""Safe black-box probe for hosted static/build/private-file exposure.

Set SECURITY_BASE_URL to a local, preview, or production deployment. The probe
never authenticates, never mutates state, and records only status/content-type,
byte counts, and SHA-256 hashes. Response bodies are inspected in memory for
high-signal secret/question-bank markers but are never written to artifacts.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import httpx


BASE = os.environ.get("SECURITY_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts" / "hosted-static-exposure.json"

SENSITIVE_PATHS = (
    "/.env",
    "/.env.local",
    "/.env.production",
    "/.git/config",
    "/private_content/",
    "/private/",
    "/question_bank/",
    "/question-bank/",
    "/data/",
    "/config/",
    "/migrations/",
    "/tests/",
    "/scripts/",
    "/artifacts/",
    "/brain.sqlite",
    "/data.sqlite",
    "/app.db",
    "/backup.dump",
    "/backup.sql",
    "/database.backup",
    "/static/app-complete.js.map",
    "/static/router-complete.js.map",
    "/static/api.js.map",
)
FRONTEND_PATHS = (
    "/static/app-complete.js",
    "/static/router-complete.js",
    "/static/api.js",
)
# Build private-key sentinels from fragments so this defensive probe does not
# itself contain a complete credential marker that the tracked-secret gate must
# correctly reject everywhere else in the repository.
_PRIVATE_KEY_MARKER = b"-----BEGIN " + b"PRIVATE KEY-----"
_RSA_PRIVATE_KEY_MARKER = b"-----BEGIN RSA " + b"PRIVATE KEY-----"
BODY_MARKERS = (
    _PRIVATE_KEY_MARKER,
    _RSA_PRIVATE_KEY_MARKER,
    b"DATABASE_MIGRATION_URL=postgres",
    b"STRIPE_SECRET_KEY=sk_",
    b"GOOGLE_OIDC_CLIENT_SECRET=",
    b"postgresql://",
    b"postgres://",
    b"neon.tech",
    b"correct_json",
    b"correct_options",
    b"answer_key",
)


def is_spa_shell(body: bytes, content_type: str) -> bool:
    lowered = body[:20000].lower()
    return "text/html" in content_type.lower() and b"<title>snowflake certification guide</title>" in lowered


def digest(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def main() -> None:
    rows: list[dict[str, object]] = []
    findings: list[dict[str, str]] = []
    with httpx.Client(follow_redirects=False, timeout=15.0) as client:
        for path in SENSITIVE_PATHS:
            response = client.get(f"{BASE}{path}")
            body = response.content
            content_type = response.headers.get("content-type", "")
            shell = is_spa_shell(body, content_type)
            rows.append(
                {
                    "path": path,
                    "status": response.status_code,
                    "content_type": content_type.split(";", 1)[0],
                    "bytes": len(body),
                    "sha256": digest(body),
                    "spa_shell_fallback": shell,
                }
            )
            if response.status_code == 200 and not shell:
                findings.append({"path": path, "issue": "sensitive_path_returned_non_shell_200"})
            for marker in BODY_MARKERS:
                if marker.lower() in body.lower():
                    findings.append({"path": path, "issue": f"sensitive_marker:{marker.decode('ascii', 'ignore')[:32]}"})

        for path in FRONTEND_PATHS:
            response = client.get(f"{BASE}{path}")
            body = response.content
            rows.append(
                {
                    "path": path,
                    "status": response.status_code,
                    "content_type": response.headers.get("content-type", "").split(";", 1)[0],
                    "bytes": len(body),
                    "sha256": digest(body),
                }
            )
            if response.status_code != 200:
                findings.append({"path": path, "issue": f"frontend_asset_unavailable:{response.status_code}"})
                continue
            for marker in BODY_MARKERS:
                if marker.lower() in body.lower():
                    findings.append({"path": path, "issue": f"frontend_sensitive_marker:{marker.decode('ascii', 'ignore')[:32]}"})

    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "pass" if not findings else "fail",
        "base_url": BASE,
        "checks": rows,
        "finding_count": len(findings),
        "findings": findings,
    }
    ARTIFACT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    if findings:
        raise SystemExit("Hosted static exposure probe found blocking evidence; response bodies are intentionally not persisted")


if __name__ == "__main__":
    main()
