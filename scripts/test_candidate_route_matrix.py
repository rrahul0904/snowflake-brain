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
    ("POST", "/api/questions/{question_id}/attempt"): "served-question-candidate-state",
    ("POST", "/api/quiz/grade"): "served-question-only",
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
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def main() -> None:
    # OpenAPI is the canonical client-facing route document and already contains
    # include_router prefixes. Using it avoids Starlette-internal route-template
    # differences across framework versions.
    schema = app.openapi()
    paths = schema.get("paths") or {}
    actual: set[tuple[str, str]] = set()
    all_paths: set[str] = set()
    for path, operations in paths.items():
        if not str(path).startswith("/api/"):
            continue
        all_paths.add(str(path))
        if not isinstance(operations, dict):
            continue
        for method in operations:
            if method.lower() in HTTP_METHODS:
                actual.add((method.upper(), str(path)))

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
