#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

REPORT = Path("bandit-report.json")

# SHA-1 here is used only to derive a deterministic, non-secret PostgreSQL test
# schema suffix. It is not used for passwords, credentials, signatures, or
# integrity. Keep this allowance exact so any other B324 remains blocking.
ALLOWED_FALSE_POSITIVES = {
    ("B324", "app/postgres_backend.py", "hashlib.sha1(str(BRAIN_DB).encode(\"utf-8\")).hexdigest()[:12]"),
}


def main() -> None:
    payload = json.loads(REPORT.read_text(encoding="utf-8"))
    blockers: list[dict] = []
    for issue in payload.get("results", []):
        if str(issue.get("issue_severity", "")).upper() != "HIGH":
            continue
        if str(issue.get("issue_confidence", "")).upper() != "HIGH":
            continue
        filename = str(issue.get("filename", "")).replace("\\", "/")
        code = str(issue.get("code", ""))
        key = (str(issue.get("test_id", "")), filename, code.strip())
        if key in ALLOWED_FALSE_POSITIVES:
            continue
        blockers.append(issue)

    if blockers:
        rendered = "\n".join(
            f"{item.get('test_id')} {item.get('filename')}:{item.get('line_number')} "
            f"{item.get('issue_text')}"
            for item in blockers
        )
        raise SystemExit(f"Blocking Bandit findings:\n{rendered}")

    medium = sum(1 for issue in payload.get("results", []) if str(issue.get("issue_severity", "")).upper() == "MEDIUM")
    print(f"Bandit blocking policy passed; {medium} medium findings remain visible in bandit-report.json for review.")


if __name__ == "__main__":
    main()
