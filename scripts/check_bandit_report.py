#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

REPORT = Path("bandit-report.json")


def allowed_false_positive(issue: dict) -> bool:
    """Allow only the known non-security SHA-1 use for a deterministic test-schema name."""
    filename = str(issue.get("filename", "")).replace("\\", "/")
    code = str(issue.get("code", ""))
    return (
        issue.get("test_id") == "B324"
        and filename == "app/postgres_backend.py"
        and "POSTGRES_TEST_ISOLATION" in code
        and "hashlib.sha1(str(BRAIN_DB).encode" in code
    )


def main() -> None:
    payload = json.loads(REPORT.read_text(encoding="utf-8"))
    blockers: list[dict] = []
    allowed: list[dict] = []
    for issue in payload.get("results", []):
        if str(issue.get("issue_severity", "")).upper() != "HIGH":
            continue
        if str(issue.get("issue_confidence", "")).upper() != "HIGH":
            continue
        if allowed_false_positive(issue):
            allowed.append(issue)
            continue
        blockers.append(issue)

    if blockers:
        rendered = "\n".join(
            f"{item.get('test_id')} {item.get('filename')}:{item.get('line_number')} "
            f"{item.get('issue_text')}"
            for item in blockers
        )
        raise SystemExit(f"Blocking Bandit findings:\n{rendered}")

    medium = sum(
        1
        for issue in payload.get("results", [])
        if str(issue.get("issue_severity", "")).upper() == "MEDIUM"
    )
    print(
        f"Bandit blocking policy passed; {medium} medium findings remain visible for review; "
        f"{len(allowed)} exact non-security SHA-1 test-schema finding allowed."
    )


if __name__ == "__main__":
    main()
