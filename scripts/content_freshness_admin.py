#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.content_freshness import (  # noqa: E402
    ContentFreshnessError,
    check_all_sources,
    check_source,
    ensure_content_freshness_schema,
    get_source,
    link_artifact,
    provenance_status,
    register_source,
    release_freshness_report,
    review_queue,
    set_freshness_policy,
    verify_artifact_link,
    verify_source,
)
from app.database import run_migrations  # noqa: E402
from app.question_bank_releases import ensure_question_bank_release_schema  # noqa: E402
from app.question_versions import ensure_question_version_schema  # noqa: E402


def _json(value) -> None:
    print(json.dumps(value, indent=2, sort_keys=True, default=str))


def _bootstrap() -> None:
    run_migrations()
    ensure_question_version_schema()
    ensure_question_bank_release_schema()
    ensure_content_freshness_schema()


def _load_manifest(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("sources"), list):
        raise ContentFreshnessError("Provenance manifest must contain a sources array.")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Official Snowflake source provenance, freshness checks, and editorial review administration"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    register = sub.add_parser("source-register", help="Register an official documentation source")
    register.add_argument("source_key")
    register.add_argument("source_url")
    register.add_argument("--title", default="")
    register.add_argument("--section", default="")
    register.add_argument("--document-version", default="")
    register.add_argument("--document-date", default="")

    manifest = sub.add_parser("manifest-import", help="Register sources and artifact links from an editorial JSON manifest")
    manifest.add_argument("path", type=Path)

    link = sub.add_parser("link", help="Link an official source to a question, lesson, skill, or reference")
    link.add_argument("source_key")
    link.add_argument("artifact_type", choices=["question", "lesson", "skill", "reference"])
    link.add_argument("artifact_key")
    link.add_argument("--track-id", default="snowpro-core")
    link.add_argument("--section", default="")
    link.add_argument("--assertion-kind", default="supports")

    check = sub.add_parser("check", help="Fetch and fingerprint one registered official source")
    check.add_argument("source_key")

    sub.add_parser("check-all", help="Fetch and fingerprint all non-retired registered sources")

    verify = sub.add_parser("verify-source", help="Editorially verify the current source fingerprint")
    verify.add_argument("source_key")
    verify.add_argument("--reviewer", required=True)
    verify.add_argument("--confidence", type=int, default=100)
    verify.add_argument("--document-version", default="")
    verify.add_argument("--document-date", default="")
    verify.add_argument("--notes", default="")

    verify_link = sub.add_parser("verify-link", help="Verify that a source supports one linked certification artifact")
    verify_link.add_argument("source_key")
    verify_link.add_argument("artifact_type", choices=["question", "lesson", "skill", "reference"])
    verify_link.add_argument("artifact_key")
    verify_link.add_argument("--reviewer", required=True)
    verify_link.add_argument("--confidence", type=int, default=100)
    verify_link.add_argument("--notes", default="")

    queue = sub.add_parser("review-list", help="List the editorial freshness review queue")
    queue.add_argument("--track-id", default="snowpro-core")
    queue.add_argument("--status", default="open", choices=["open", "acknowledged", "resolved", "ignored"])

    status = sub.add_parser("status", help="Show provenance coverage, review backlog and active-release gate status")
    status.add_argument("--track-id", default="snowpro-core")

    report = sub.add_parser("release-report", help="Evaluate one release against freshness/provenance policy")
    report.add_argument("release_key")
    report.add_argument("--allow-unlinked", action="store_true")
    report.add_argument("--max-age-days", type=int, default=120)

    policy = sub.add_parser("policy-set", help="Enable/disable the hard release freshness gate for a track")
    policy.add_argument("--track-id", default="snowpro-core")
    policy.add_argument("--enforce", choices=["on", "off"], required=True)
    policy.add_argument("--allow-unlinked", action="store_true")
    policy.add_argument("--max-age-days", type=int, default=120)
    policy.add_argument("--actor", default="admin")
    policy.add_argument("--release-key")

    args = parser.parse_args()
    _bootstrap()

    try:
        if args.command == "source-register":
            # Editing a verified source URL under the same key can silently change
            # what an editorial approval means. Require a new key instead.
            try:
                existing = get_source(args.source_key)
            except ContentFreshnessError:
                existing = None
            if existing and str(existing["source_url"]) != str(args.source_url):
                raise ContentFreshnessError(
                    "A source_key cannot be repointed to a different URL. Retire it and register a new source_key."
                )
            _json(
                register_source(
                    args.source_key,
                    args.source_url,
                    source_title=args.title,
                    source_section=args.section,
                    document_version=args.document_version,
                    document_date=args.document_date,
                )
            )
            return 0

        if args.command == "manifest-import":
            payload = _load_manifest(args.path)
            imported_sources = 0
            imported_links = 0
            for item in payload["sources"]:
                if not isinstance(item, dict):
                    raise ContentFreshnessError("Each sources entry must be an object.")
                source = register_source(
                    str(item.get("source_key") or ""),
                    str(item.get("source_url") or ""),
                    source_title=str(item.get("source_title") or ""),
                    source_section=str(item.get("source_section") or ""),
                    document_version=str(item.get("document_version") or ""),
                    document_date=str(item.get("document_date") or ""),
                )
                imported_sources += 1
                for link_item in item.get("links") or []:
                    link_artifact(
                        str(source["source_key"]),
                        str(link_item.get("artifact_type") or ""),
                        str(link_item.get("artifact_key") or ""),
                        track_id=str(link_item.get("track_id") or "snowpro-core"),
                        source_section=str(link_item.get("source_section") or ""),
                        assertion_kind=str(link_item.get("assertion_kind") or "supports"),
                    )
                    imported_links += 1
            _json({"sources": imported_sources, "links": imported_links})
            return 0

        if args.command == "link":
            _json(
                link_artifact(
                    args.source_key,
                    args.artifact_type,
                    args.artifact_key,
                    track_id=args.track_id,
                    source_section=args.section,
                    assertion_kind=args.assertion_kind,
                )
            )
            return 0

        if args.command == "check":
            _json(check_source(args.source_key))
            return 0

        if args.command == "check-all":
            result = check_all_sources()
            _json(result)
            # Source changes are not failures: they are editorial work. Network /
            # parser failures are operational failures and make the scheduled job red.
            return 2 if result["failed"] else 0

        if args.command == "verify-source":
            _json(
                verify_source(
                    args.source_key,
                    args.reviewer,
                    confidence=args.confidence,
                    document_version=args.document_version,
                    document_date=args.document_date,
                    notes=args.notes,
                )
            )
            return 0

        if args.command == "verify-link":
            _json(
                verify_artifact_link(
                    args.source_key,
                    args.artifact_type,
                    args.artifact_key,
                    args.reviewer,
                    confidence=args.confidence,
                    notes=args.notes,
                )
            )
            return 0

        if args.command == "review-list":
            _json(review_queue(args.track_id, status=args.status))
            return 0

        if args.command == "status":
            _json(provenance_status(args.track_id))
            return 0

        if args.command == "release-report":
            result = release_freshness_report(
                args.release_key,
                require_all_questions=not args.allow_unlinked,
                max_verification_age_days=args.max_age_days,
            )
            _json(result)
            return 0 if result["gate_pass"] else 3

        if args.command == "policy-set":
            _json(
                set_freshness_policy(
                    args.track_id,
                    enforcement_enabled=args.enforce == "on",
                    require_all_questions=not args.allow_unlinked,
                    max_verification_age_days=args.max_age_days,
                    actor=args.actor,
                    release_key=args.release_key,
                )
            )
            return 0
    except ContentFreshnessError as exc:
        print(f"content freshness error: {exc}", file=sys.stderr)
        return 2

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
