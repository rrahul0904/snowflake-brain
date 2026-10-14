#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.content_freshness import (  # noqa: E402
    ContentFreshnessError,
    record_source_content,
    register_source,
)
from app.database import run_migrations  # noqa: E402
from app.question_bank_releases import ensure_question_bank_release_schema  # noqa: E402
from app.question_versions import ensure_question_version_schema  # noqa: E402
from app.content_freshness import ensure_content_freshness_schema  # noqa: E402


TEXT_EXTENSIONS = {".txt", ".md", ".markdown", ".html", ".htm"}
BINARY_DOCUMENT_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}
ALLOWED_EXTENSIONS = TEXT_EXTENSIONS | BINARY_DOCUMENT_EXTENSIONS
DEFAULT_OUTPUT_ROOT = ROOT / "private_content" / "editorial_intake"


class IntakeError(ValueError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _validate_paths(source: Path, transcript: Path | None, output_root: Path) -> None:
    source = source.resolve()
    output_root = output_root.resolve()
    if not source.is_file():
        raise IntakeError(f"Source file does not exist: {source}")
    if source.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise IntakeError(f"Unsupported source type: {source.suffix or 'unknown'}")

    public_roots = [ROOT / "frontend", ROOT / "static", ROOT / "config"]
    if any(_is_within(source, public_root) for public_root in public_roots):
        raise IntakeError("Editorial source files must not originate from public/static/config application paths")

    if _is_within(output_root, ROOT) and not _is_within(output_root, ROOT / "private_content"):
        raise IntakeError("Repository-local editorial intake output must stay under private_content/")

    if source.suffix.lower() in BINARY_DOCUMENT_EXTENSIONS:
        if transcript is None:
            raise IntakeError("PDF/image intake requires --transcript with reviewed extracted/normalized text")
        if not transcript.is_file():
            raise IntakeError(f"Transcript file does not exist: {transcript}")
        if transcript.suffix.lower() not in TEXT_EXTENSIONS:
            raise IntakeError("Transcript must be a text/Markdown/HTML file")


def _read_normalized_text(source: Path, transcript: Path | None) -> tuple[str, Path]:
    text_path = transcript if source.suffix.lower() in BINARY_DOCUMENT_EXTENSIONS else source
    assert text_path is not None
    try:
        text = text_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise IntakeError("Normalized editorial text must be UTF-8") from exc
    normalized = "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")).strip()
    if len(normalized) < 20:
        raise IntakeError("Normalized editorial text is too short for review")
    return normalized, text_path


def ingest_source(
    source: Path,
    *,
    source_key: str,
    source_url: str,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    transcript: Path | None = None,
    title: str = "",
    section: str = "",
    document_version: str = "",
    document_date: str = "",
) -> dict[str, Any]:
    source = source.expanduser().resolve()
    transcript = transcript.expanduser().resolve() if transcript else None
    output_root = output_root.expanduser().resolve()
    _validate_paths(source, transcript, output_root)
    normalized_text, normalized_source = _read_normalized_text(source, transcript)

    key = str(source_key or "").strip()
    if not key:
        raise IntakeError("source_key is required")

    run_migrations()
    ensure_question_version_schema()
    ensure_question_bank_release_schema()
    ensure_content_freshness_schema()

    registered = register_source(
        key,
        source_url,
        source_title=title,
        source_section=section,
        document_version=document_version,
        document_date=document_date,
    )
    freshness = record_source_content(key, normalized_text)

    source_hash = _sha256(source)
    transcript_hash = _sha256(normalized_source)
    intake_id = f"{key}-{source_hash[:12]}"
    target = output_root / intake_id
    target.mkdir(parents=True, exist_ok=False)

    source_copy = target / f"source{source.suffix.lower()}"
    shutil.copy2(source, source_copy)
    normalized_path = target / "normalized.txt"
    normalized_path.write_text(normalized_text, encoding="utf-8")

    manifest = {
        "schema_version": "snowflake-editorial-intake-v1",
        "intake_id": intake_id,
        "source_key": key,
        "source_url": registered["source_url"],
        "source_title": title,
        "source_section": section,
        "document_version": document_version,
        "document_date": document_date,
        "source_filename": source.name,
        "source_extension": source.suffix.lower(),
        "source_mime_type": mimetypes.guess_type(source.name)[0] or "application/octet-stream",
        "source_sha256": source_hash,
        "source_size_bytes": source.stat().st_size,
        "normalized_text_sha256": _text_sha256(normalized_text),
        "normalized_text_bytes": len(normalized_text.encode("utf-8")),
        "transcript_sha256": transcript_hash if transcript is not None else None,
        "transcript_required": source.suffix.lower() in BINARY_DOCUMENT_EXTENSIONS,
        "extraction_mode": "human_supplied_transcript" if transcript is not None else "direct_utf8_text",
        "editorial_status": "needs_review",
        "import_ready": False,
        "question_generation_allowed": False,
        "release_activation_allowed": False,
        "freshness_result": freshness["result"],
        "freshness_fingerprint": freshness["fingerprint"],
    }
    (target / "intake.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return {**manifest, "private_path": str(target)}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Private Snowflake editorial intake for text, PDF, and image source material"
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("--source-key", required=True)
    parser.add_argument("--source-url", required=True, help="Official Snowflake HTTPS source URL")
    parser.add_argument("--transcript", type=Path, help="Required reviewed transcript for PDF/image inputs")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--title", default="")
    parser.add_argument("--section", default="")
    parser.add_argument("--document-version", default="")
    parser.add_argument("--document-date", default="")
    args = parser.parse_args()
    try:
        result = ingest_source(
            args.source,
            source_key=args.source_key,
            source_url=args.source_url,
            output_root=args.output_root,
            transcript=args.transcript,
            title=args.title,
            section=args.section,
            document_version=args.document_version,
            document_date=args.document_date,
        )
    except (IntakeError, ContentFreshnessError, FileExistsError) as exc:
        print(f"intake error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
