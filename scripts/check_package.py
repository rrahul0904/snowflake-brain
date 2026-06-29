#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"

BANNED_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    "__MACOSX",
    "data",
    "static",
    "review_artifacts",
    "node_modules",
}
BANNED_SUFFIXES = {
    ".sqlite",
    ".db",
    ".pyc",
    ".pyo",
    ".DS_Store",
}


def default_zip() -> Path:
    candidates = sorted(DIST.glob("*.zip"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not candidates:
        raise SystemExit("No zip found in dist/. Run scripts/package_review.sh first.")
    return candidates[0]


def main() -> None:
    parser = argparse.ArgumentParser(description="Check a Snowflake Brain source package for private/runtime leaks.")
    parser.add_argument("zip_path", nargs="?", default=None)
    args = parser.parse_args()

    zip_path = Path(args.zip_path) if args.zip_path else default_zip()
    leaks: list[str] = []
    with zipfile.ZipFile(zip_path) as archive:
        for name in archive.namelist():
            parts = {part for part in Path(name).parts if part}
            if parts & BANNED_PARTS:
                leaks.append(name)
                continue
            if any(name.endswith(suffix) for suffix in BANNED_SUFFIXES):
                leaks.append(name)

    if leaks:
        print(f"Package leak check failed: {zip_path}")
        for leak in leaks[:80]:
            print(f"- {leak}")
        if len(leaks) > 80:
            print(f"... {len(leaks) - 80} more")
        sys.exit(1)
    print(f"Package leak check passed: {zip_path}")


if __name__ == "__main__":
    main()

