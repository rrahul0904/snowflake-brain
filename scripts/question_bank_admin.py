#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database import run_migrations  # noqa: E402
from app.question_bank import (  # noqa: E402
    bank_status,
    import_question_bank_directory,
    import_question_bank_file,
    validate_question_bank_payload,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Backend-only Snowflake question-bank administration")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate", help="Validate one private bank JSON file without importing it")
    validate.add_argument("path", type=Path)

    imp = sub.add_parser("import", help="Validate and import one private bank JSON file into SQLite")
    imp.add_argument("path", type=Path)

    directory = sub.add_parser("import-dir", help="Import all JSON files from a private bank directory")
    directory.add_argument("path", type=Path, nargs="?")
    directory.add_argument("--dry-run", action="store_true")

    status = sub.add_parser("status", help="Show backend authoring coverage and milestone status")
    status.add_argument("--track-id", default="snowpro-core")

    args = parser.parse_args()
    run_migrations()

    if args.command == "validate":
        payload = json.loads(args.path.read_text(encoding="utf-8"))
        result = validate_question_bank_payload(payload, source_name=args.path.name)
        print(json.dumps({k: v for k, v in result.items() if k != "questions"}, indent=2))
        return 0 if result["valid"] else 2
    if args.command == "import":
        print(json.dumps(import_question_bank_file(args.path), indent=2))
        return 0
    if args.command == "import-dir":
        print(json.dumps(import_question_bank_directory(args.path, dry_run=args.dry_run), indent=2))
        return 0
    if args.command == "status":
        print(json.dumps(bank_status(args.track_id), indent=2))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
