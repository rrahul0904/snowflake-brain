#!/usr/bin/env python3
"""Create the release identity bundled with a Vercel build.

Production builds must originate from Vercel's Git integration. A CLI upload
does not receive ``VERCEL_GIT_COMMIT_SHA`` and is deliberately rejected rather
than claiming an unrelated environment variable as its source revision.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "app" / "release_manifest.json"


def main() -> None:
    sha = os.getenv("VERCEL_GIT_COMMIT_SHA", "").strip()
    if not sha:
        raise SystemExit("Production build refused: VERCEL_GIT_COMMIT_SHA is required for an immutable Git release.")
    if len(sha) != 40 or any(char not in "0123456789abcdef" for char in sha.lower()):
        raise SystemExit("Production build refused: VERCEL_GIT_COMMIT_SHA is not a full commit SHA.")
    payload = {
        "git_sha": sha.lower(),
        "build_timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_dirty": False,
    }
    TARGET.write_text(json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
