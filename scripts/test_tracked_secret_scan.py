#!/usr/bin/env python3
"""High-signal secret scan across Git-tracked text files.

This is intentionally conservative: it blocks recognizable private keys and
provider credential formats plus non-local PostgreSQL URLs containing concrete
credentials, while allowing documented placeholders and disposable localhost CI
DSNs. The report records only path/pattern metadata and never echoes a secret.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts" / "tracked-secret-scan.json"

TOKEN_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("github_token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})\b")),
    ("stripe_secret", re.compile(r"\bsk_(?:live|test)_[A-Za-z0-9]{20,}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{20,}\b")),
)
POSTGRES_URL = re.compile(r"\bpostgres(?:ql)?://[^\s'\"<>]+", re.IGNORECASE)
PLACEHOLDER_MARKERS = (
    "change_me",
    "changeme",
    "replace_me",
    "replace-me",
    "password",
    "example",
    "your_",
    "your-",
    "<",
    ">",
    "${",
    "...",
)
LOCAL_DB_HOSTS = {"localhost", "127.0.0.1", "postgres", "db"}


def tracked_files() -> list[Path]:
    output = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    return [ROOT / raw.decode("utf-8") for raw in output.split(b"\0") if raw]


def concrete_remote_database_url(value: str) -> bool:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return False
    host = (parsed.hostname or "").lower()
    password = parsed.password or ""
    if not host or host in LOCAL_DB_HOSTS or host.endswith(".local"):
        return False
    lowered = value.lower()
    if any(marker in lowered for marker in PLACEHOLDER_MARKERS):
        return False
    return bool(parsed.username and password)


def main() -> None:
    findings: list[dict[str, str]] = []
    scanned = 0
    for path in tracked_files():
        if not path.is_file():
            continue
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if b"\0" in data[:8192]:
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            continue
        scanned += 1
        relative = str(path.relative_to(ROOT))
        for name, pattern in TOKEN_PATTERNS:
            if pattern.search(text):
                findings.append({"path": relative, "pattern": name})
        for match in POSTGRES_URL.finditer(text):
            if concrete_remote_database_url(match.group(0)):
                findings.append({"path": relative, "pattern": "credentialed_remote_postgres_url"})
                break

    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "pass" if not findings else "fail",
        "tracked_text_files_scanned": scanned,
        "finding_count": len(findings),
        "findings": findings,
    }
    ARTIFACT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    if findings:
        raise SystemExit("Tracked secret scan found high-signal credential material; values are intentionally redacted")


if __name__ == "__main__":
    main()
