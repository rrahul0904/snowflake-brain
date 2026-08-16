#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database import run_migrations  # noqa: E402
from app.question_bank_releases import ensure_question_bank_release_schema, promote_release  # noqa: E402
from app.question_editorial import (  # noqa: E402
    EditorialError,
    bank_health,
    ensure_question_editorial_schema,
    question_status,
    release_editorial_report,
    review_question,
    run_qa,
)
from app.question_editorial_policy import (  # noqa: E402
    ensure_question_editorial_policy_schema,
    set_editorial_policy,
)
from app.question_versions import ensure_question_version_schema  # noqa: E402


def _json(value) -> None:
    print(json.dumps(value, indent=2, sort_keys=True, default=str))


def _bootstrap() -> None:
    run_migrations()
    ensure_question_version_schema()
    ensure_question_bank_release_schema()
    ensure_question_editorial_schema()
    ensure_question_editorial_policy_schema()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Automated QA plus explicit human content/SME review for Snowflake certification questions"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    qa = sub.add_parser("qa-run", help="Run automated editorial QA against the active question bank")
    qa.add_argument("--track-id", default="snowpro-core")
    qa.add_argument("--include-non-active", action="store_true")
    qa.add_argument("--scope", default="bank")

    status = sub.add_parser("question-status", help="Show QA findings and current human approvals for one question")
    status.add_argument("question_id")

    review = sub.add_parser("review", help="Record an explicit human content or SME decision")
    review.add_argument("question_id")
    review.add_argument("stage", choices=["content", "sme"])
    review.add_argument("action", choices=["approved", "changes_requested"])
    review.add_argument("--actor", required=True)
    review.add_argument("--notes", default="")

    health = sub.add_parser("bank-health", help="Report editorial health by SnowPro domain")
    health.add_argument("--track-id", default="snowpro-core")

    readiness = sub.add_parser("release-readiness", help="Check immutable release versions against QA/content/SME approvals")
    readiness.add_argument("release_key")

    promote = sub.add_parser("release-promote", help="Promote a release only when the required editorial stage is current")
    promote.add_argument("release_key")
    promote.add_argument("target_status", choices=["qa_passed", "sme_approved", "staging"])
    promote.add_argument("--actor", required=True)

    policy = sub.add_parser("policy-set", help="Enable or disable the database editorial release gate")
    policy.add_argument("--track-id", default="snowpro-core")
    policy.add_argument("--enforce", choices=["on", "off"], required=True)
    policy.add_argument("--minimum-qa-score", type=float, default=70.0)
    policy.add_argument("--allow-without-content-review", action="store_true")
    policy.add_argument("--allow-without-sme-review", action="store_true")
    policy.add_argument("--actor", default="admin")
    policy.add_argument("--release-key")

    args = parser.parse_args()
    try:
        _bootstrap()
        if args.command == "qa-run":
            _json(
                run_qa(
                    args.track_id,
                    active_only=not args.include_non_active,
                    scope=args.scope,
                )
            )
            return 0

        if args.command == "question-status":
            _json(question_status(args.question_id))
            return 0

        if args.command == "review":
            _json(
                review_question(
                    args.question_id,
                    args.stage,
                    args.action,
                    args.actor,
                    notes=args.notes,
                )
            )
            return 0

        if args.command == "bank-health":
            _json(bank_health(args.track_id))
            return 0

        if args.command == "release-readiness":
            report = release_editorial_report(args.release_key)
            _json(report)
            return 0 if report["gate_pass"] else 3

        if args.command == "release-promote":
            report = release_editorial_report(args.release_key)
            if args.target_status == "qa_passed" and report["qa_pct"] < 100.0:
                raise EditorialError("Release cannot enter qa_passed until every immutable release item has current passing QA")
            if args.target_status in {"sme_approved", "staging"} and not report["gate_pass"]:
                raise EditorialError("Release cannot advance until current QA, human content review, and explicit SME approval are complete")
            result = promote_release(args.release_key, args.target_status, actor=args.actor)
            _json(result)
            return 0

        if args.command == "policy-set":
            _json(
                set_editorial_policy(
                    args.track_id,
                    enforcement_enabled=args.enforce == "on",
                    minimum_qa_score=args.minimum_qa_score,
                    require_content_review=not args.allow_without_content_review,
                    require_sme_review=not args.allow_without_sme_review,
                    actor=args.actor,
                    release_key=args.release_key,
                )
            )
            return 0
    except EditorialError as exc:
        print(f"editorial error: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
