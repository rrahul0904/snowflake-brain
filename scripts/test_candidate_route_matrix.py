#!/usr/bin/env python3
"""Machine-readable contract for candidate-owned/sensitive API routes.

This complements behavioral hostile-subscriber tests by making the protected
object surface explicit. New or retired sensitive routes cannot silently drift
without updating the security matrix and its corresponding behavioral coverage.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

from fastapi.routing import APIRoute


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory(prefix="snowflake-route-matrix-")
os.environ["BRAIN_DB"] = str(Path(TEMP.name) / "routes.sqlite")
os.environ.pop("VERCEL", None)
os.environ.pop("VERCEL_ENV", None)
os.environ.pop("DATABASE_URL", None)

from app.main import app  # noqa: E402


ARTIFACT = ROOT / "artifacts" / "candidate-authorization-matrix.json"
EXPECTED: dict[tuple[str, str], str] = {
    ("GET", "/api/questions/{question_id}"): "served-question-only",
    ("GET", "/api/questions/{question_id}/bookmark"): "served-question-candidate-state",
    ("POST", "/api/questions/{question_id}/bookmark"): "served-question-candidate-state",
    ("GET", "/api/questions/{question_id}/notes"): "served-question-candidate-state",
    ("POST", "/api/questions/{question_id}/notes"): "served-question-candidate-state",
    ("GET", "/api/mock/sessions/{session_id}"): "candidate-owned-mock",
    ("PUT", "/api/mock/sessions/{session_id}/answers/{question_id}"): "candidate-owned-mock",
    ("PUT", "/api/mock/sessions/{session_id}/questions/{question_id}/flag"): "candidate-owned-mock",
    ("POST", "/api/mock/sessions/{session_id}/submit"): "candidate-owned-mock",
    ("GET", "/api/mock/sessions/{session_id}/result"): "candidate-owned-mock",
    ("GET", "/api/intelligence/mock-remediation/{session_id}"): "candidate-owned-mock",
    ("PATCH", "/api/intelligence/mistake-notebook/{question_id}"): "candidate-owned-learning-state",
    ("DELETE", "/api/credentials/{credential_uid}"): "candidate-owned-credential",
    ("POST", "/api/credentials/{credential_uid}/reverify"): "candidate-owned-credential",
    ("DELETE", "/api/auth/sessions/{session_id}"): "candidate-owned-auth-session",
}
FORBIDDEN_RETIRED_PATHS = {
    "/api/intelligence/adaptive/question-ids",
    "/api/intelligence/evidence-audit",
    "/api/intelligence/evidence-review",
    "/api/intelligence/reindex-skill-map",
}


def public_request_path(route: APIRoute) -> str:
    """Normalize Starlette 1.6 APIRouter templates to actual request URLs.

    Included routers expose route.path without the app-level `/api` prefix even
    though clients request `/api/...`. App-declared health/ready/metrics routes
    already contain `/api` and are left unchanged.
    """
    path = route.path
    if path.startswith("/api"):
        return path
    return f"/api{path}"


def main() -> None:
    actual: set[tuple[str, str]] = set()
    all_paths: set[str] = set()
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if route.name == "serve_spa":
            continue
        path = public_request_path(route)
        methods = route.methods or set()
        all_paths.add(path)
        for method in methods:
            if method in {"HEAD", "OPTIONS"}:
                continue
            actual.add((method, path))

    missing = sorted(f"{method} {path}" for (method, path) in EXPECTED if (method, path) not in actual)
    retired_present = sorted(FORBIDDEN_RETIRED_PATHS & all_paths)
    rows = [
        {"method": method, "path": path, "ownership": ownership, "behavioral_suite": "test_authenticated_bank_isolation.py"}
        for (method, path), ownership in sorted(EXPECTED.items())
    ]
    payload = {
        "status": "pass" if not missing and not retired_present else "fail",
        "sensitive_route_count": len(rows),
        "routes": rows,
        "missing_expected_routes": missing,
        "retired_candidate_admin_routes_present": retired_present,
    }
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    if missing:
        raise AssertionError(f"Sensitive candidate route matrix drifted; missing routes: {missing}")
    if retired_present:
        raise AssertionError(f"Retired candidate-reachable admin/inventory routes returned: {retired_present}")


if __name__ == "__main__":
    try:
        main()
    finally:
        TEMP.cleanup()
