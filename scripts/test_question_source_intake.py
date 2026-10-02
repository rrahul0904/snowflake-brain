#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory(prefix="snowflake-source-intake-")
TMP = Path(TEMP.name)
os.environ["BRAIN_DB"] = str(TMP / "source-intake.sqlite")
os.environ["SECURITY_RATE_LIMIT_ENABLED"] = "false"

from app.content_freshness import ContentFreshnessError, review_queue  # noqa: E402
from scripts.question_source_intake import IntakeError, ingest_source  # noqa: E402


def check(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    output_root = TMP / "private-output"

    text_source = TMP / "architecture.md"
    text_source.write_text(
        "# Snowflake architecture\nStorage, compute, and cloud services have distinct responsibilities.\n"
        "This reviewed source text is long enough for editorial intake.",
        encoding="utf-8",
    )
    text_result = ingest_source(
        text_source,
        source_key="intake-test-architecture",
        source_url="https://docs.snowflake.com/en/user-guide/intro-key-concepts",
        output_root=output_root,
        title="Snowflake architecture test source",
    )
    check(text_result["editorial_status"] == "needs_review", "text intake must require editorial review")
    check(text_result["import_ready"] is False, "source intake must never become import-ready automatically")
    check(text_result["question_generation_allowed"] is False, "source intake must not auto-generate questions")
    check(text_result["release_activation_allowed"] is False, "source intake must not activate a release")
    target = Path(text_result["private_path"])
    check((target / "intake.json").is_file(), "private intake manifest missing")
    check((target / "normalized.txt").is_file(), "normalized private text missing")
    check(text_result["source_sha256"], "source hash missing")
    check(text_result["normalized_text_sha256"], "normalized text hash missing")

    fake_pdf = TMP / "source.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4\nprivate editorial test bytes\n%%EOF")
    try:
        ingest_source(
            fake_pdf,
            source_key="intake-test-pdf-no-transcript",
            source_url="https://docs.snowflake.com/en/user-guide/intro-key-concepts",
            output_root=output_root,
        )
    except IntakeError as exc:
        check("transcript" in str(exc).lower(), "PDF without transcript failed for the wrong reason")
    else:
        raise AssertionError("PDF intake must fail closed without a reviewed transcript")

    transcript = TMP / "source-transcript.txt"
    transcript.write_text(
        "Reviewed transcript for the PDF source. This text describes Snowflake storage, compute, "
        "and cloud-services architecture and is intentionally supplied by the editorial operator.",
        encoding="utf-8",
    )
    pdf_result = ingest_source(
        fake_pdf,
        source_key="intake-test-pdf",
        source_url="https://docs.snowflake.com/en/user-guide/intro-key-concepts",
        output_root=output_root,
        transcript=transcript,
    )
    check(pdf_result["extraction_mode"] == "human_supplied_transcript", "PDF extraction mode must be explicit")
    check(pdf_result["transcript_required"] is True, "PDF transcript requirement not recorded")
    check(pdf_result["transcript_sha256"], "reviewed transcript hash missing")

    bad_source = TMP / "untrusted.txt"
    bad_source.write_text(
        "This is deliberately long enough to reach the URL provenance validation boundary.",
        encoding="utf-8",
    )
    try:
        ingest_source(
            bad_source,
            source_key="intake-test-untrusted",
            source_url="https://example.com/snowflake-not-official",
            output_root=output_root,
        )
    except ContentFreshnessError:
        pass
    else:
        raise AssertionError("unapproved provenance host must fail closed")

    try:
        ingest_source(
            text_source,
            source_key="intake-test-public-path",
            source_url="https://docs.snowflake.com/en/user-guide/intro-key-concepts",
            output_root=ROOT / "frontend" / "editorial-intake",
        )
    except IntakeError:
        pass
    else:
        raise AssertionError("repository-local intake must not write into public application paths")

    queue = review_queue("snowpro-core", status="open")
    source_reasons = [row for row in queue if row.get("artifact_type") == "source"]
    check(len(source_reasons) >= 2, "private intake must create editorial source review work")

    print("Private text/PDF/image editorial intake: PASS")


if __name__ == "__main__":
    try:
        main()
    finally:
        TEMP.cleanup()
