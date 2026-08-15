#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database import run_migrations  # noqa: E402
from app.observability import record_background_failure, record_release_event  # noqa: E402
from app.question_bank import (  # noqa: E402
    bank_status,
    import_question_bank_directory,
    import_question_bank_file,
    validate_question_bank_payload,
)
from app.question_bank_releases import (  # noqa: E402
    activate_release,
    compare_releases,
    create_release,
    ensure_question_bank_release_schema,
    get_release,
    list_releases,
    promote_release,
    retire_release,
    rollback_release,
)
from app.question_versions import ensure_question_version_schema  # noqa: E402


def _release_question_ids_from_source(path: Path) -> tuple[str, list[str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    validation = validate_question_bank_payload(payload, source_name=path.name)
    if not validation["valid"]:
        raise ValueError("Question bank validation failed:\n- " + "\n- ".join(validation["errors"]))
    ids = [
        str(row["id"])
        for row in validation["questions"]
        if str(row.get("authoring_status") or "") == "active"
    ]
    return str(payload["track_id"]), ids


def _observed_release(action: str, release_key: str, operation: Callable[[], dict]) -> dict:
    try:
        result = operation()
    except Exception:
        record_release_event(action, "failure", release_key=release_key)
        raise
    record_release_event(action, "success", release_key=release_key)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Backend-only Snowflake question-bank administration")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate", help="Validate one private bank JSON file without importing it")
    validate.add_argument("path", type=Path)

    imp = sub.add_parser("import", help="Validate and import one private bank JSON file into the configured database")
    imp.add_argument("path", type=Path)

    directory = sub.add_parser("import-dir", help="Import all JSON files from a private bank directory")
    directory.add_argument("path", type=Path, nargs="?")
    directory.add_argument("--dry-run", action="store_true")

    status = sub.add_parser("status", help="Show backend authoring coverage and milestone status")
    status.add_argument("--track-id", default="snowpro-core")

    release_create = sub.add_parser("release-create", help="Snapshot a new draft question-bank release")
    release_create.add_argument("release_key")
    release_create.add_argument("--track-id", default="snowpro-core")
    release_create.add_argument("--source", type=Path, help="Use exactly the active question IDs in this validated bank JSON")
    release_create.add_argument("--actor", default="admin")
    release_create.add_argument("--notes", default="")

    release_promote = sub.add_parser("release-promote", help="Advance a release through QA, SME approval, and staging")
    release_promote.add_argument("release_key")
    release_promote.add_argument("target_status", choices=["qa_passed", "sme_approved", "staging"])
    release_promote.add_argument("--actor", default="admin")

    release_activate = sub.add_parser("release-activate", help="Atomically activate a staging release and retire the previous active release")
    release_activate.add_argument("release_key")
    release_activate.add_argument("--actor", default="admin")

    release_rollback = sub.add_parser("release-rollback", help="Atomically restore a previously retired release")
    release_rollback.add_argument("release_key")
    release_rollback.add_argument("--actor", default="admin")

    release_retire = sub.add_parser("release-retire", help="Retire a non-active release")
    release_retire.add_argument("release_key")
    release_retire.add_argument("--actor", default="admin")

    release_show = sub.add_parser("release-show", help="Show one release and its audit events")
    release_show.add_argument("release_key")

    release_list = sub.add_parser("release-list", help="List releases for a certification track")
    release_list.add_argument("--track-id", default="snowpro-core")

    release_compare = sub.add_parser("release-compare", help="Compare membership/version changes between two releases")
    release_compare.add_argument("left_release")
    release_compare.add_argument("right_release")

    args = parser.parse_args()
    try:
        run_migrations()
        ensure_question_version_schema()
        ensure_question_bank_release_schema()
    except Exception as exc:
        record_background_failure("question_bank_admin_bootstrap", exc)
        raise

    if args.command == "validate":
        payload = json.loads(args.path.read_text(encoding="utf-8"))
        result = validate_question_bank_payload(payload, source_name=args.path.name)
        print(json.dumps({k: v for k, v in result.items() if k != "questions"}, indent=2))
        return 0 if result["valid"] else 2
    if args.command == "import":
        try:
            result = import_question_bank_file(args.path)
        except Exception as exc:
            record_background_failure("question_bank_import", exc)
            raise
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "import-dir":
        try:
            result = import_question_bank_directory(args.path, dry_run=args.dry_run)
        except Exception as exc:
            record_background_failure("question_bank_import_dir", exc)
            raise
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "status":
        print(json.dumps(bank_status(args.track_id), indent=2))
        return 0
    if args.command == "release-create":
        track_id = args.track_id
        question_ids = None
        if args.source:
            track_id, question_ids = _release_question_ids_from_source(args.source)
        result = _observed_release(
            "create",
            args.release_key,
            lambda: create_release(
                args.release_key,
                track_id,
                question_ids=question_ids,
                actor=args.actor,
                notes=args.notes,
            ),
        )
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "release-promote":
        result = _observed_release(
            "promote",
            args.release_key,
            lambda: promote_release(args.release_key, args.target_status, actor=args.actor),
        )
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "release-activate":
        result = _observed_release(
            "activate",
            args.release_key,
            lambda: activate_release(args.release_key, actor=args.actor),
        )
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "release-rollback":
        result = _observed_release(
            "rollback",
            args.release_key,
            lambda: rollback_release(args.release_key, actor=args.actor),
        )
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "release-retire":
        result = _observed_release(
            "retire",
            args.release_key,
            lambda: retire_release(args.release_key, actor=args.actor),
        )
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "release-show":
        print(json.dumps(get_release(args.release_key), indent=2))
        return 0
    if args.command == "release-list":
        print(json.dumps(list_releases(args.track_id), indent=2))
        return 0
    if args.command == "release-compare":
        print(json.dumps(compare_releases(args.left_release, args.right_release), indent=2))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
