#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

TEXT_SUFFIXES = {".txt", ".md", ".csv", ".json"}
PDF_SUFFIXES = {".pdf"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
ALLOWED_SUFFIXES = TEXT_SUFFIXES | PDF_SUFFIXES | IMAGE_SUFFIXES
PROHIBITED_MARKERS = (
    "actual exam questions",
    "real exam questions",
    "exam dump",
    "braindump",
    "recalled questions",
    "leaked exam",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def transcript_text(path: Path | None) -> str:
    if not path:
        return ""
    if not path.is_file():
        raise SystemExit(f"Transcript does not exist: {path}")
    return path.read_text(encoding="utf-8").strip()


def extract(path: Path, transcript: Path | None) -> tuple[str, str]:
    suffix = path.suffix.lower()
    if suffix in TEXT_SUFFIXES:
        return path.read_text(encoding="utf-8").strip(), "native_text"

    supplied = transcript_text(transcript)
    if supplied:
        return supplied, "operator_supplied_transcript"

    if suffix in PDF_SUFFIXES:
        binary = shutil.which("pdftotext")
        if binary:
            result = subprocess.run(
                [binary, str(path), "-"],
                check=True,
                capture_output=True,
                text=True,
                timeout=60,
            )
            return result.stdout.strip(), "pdftotext"
        raise SystemExit("PDF intake requires pdftotext or --transcript. No content was imported.")

    if suffix in IMAGE_SUFFIXES:
        binary = shutil.which("tesseract")
        if binary:
            result = subprocess.run(
                [binary, str(path), "stdout"],
                check=True,
                capture_output=True,
                text=True,
                timeout=60,
            )
            return result.stdout.strip(), "tesseract"
        raise SystemExit("Image intake requires tesseract or --transcript. No content was imported.")

    raise SystemExit(f"Unsupported source type: {suffix}")


def risk_flags(text: str) -> list[str]:
    lowered = " ".join(text.lower().split())
    return [marker for marker in PROHIBITED_MARKERS if marker in lowered]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a private, review-only Snowflake content-intake package from text, PDF, or image source material."
    )
    parser.add_argument("source")
    parser.add_argument("--track-id", default="snowpro-core")
    parser.add_argument("--actor", required=True)
    parser.add_argument("--transcript", help="Operator-reviewed UTF-8 transcript for PDF/image sources when local extraction is unavailable.")
    parser.add_argument("--source-url", default="")
    parser.add_argument("--output-dir", default="private_content/intake")
    args = parser.parse_args()

    source = Path(args.source).expanduser().resolve()
    if not source.is_file():
        raise SystemExit(f"Source does not exist: {source}")
    if source.suffix.lower() not in ALLOWED_SUFFIXES:
        raise SystemExit(f"Allowed source types: {', '.join(sorted(ALLOWED_SUFFIXES))}")

    transcript = Path(args.transcript).expanduser().resolve() if args.transcript else None
    text, extraction = extract(source, transcript)
    if len(text) < 20:
        raise SystemExit("Extracted/transcribed text is too short for review intake.")

    flags = risk_flags(text)
    source_hash = sha256(source)
    intake_id = f"{args.track_id}-{source_hash[:16]}"
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"{intake_id}.json"
    payload = {
        "intake_id": intake_id,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "track_id": args.track_id,
        "actor": args.actor,
        "source_filename": source.name,
        "source_suffix": source.suffix.lower(),
        "source_sha256": source_hash,
        "source_url": args.source_url,
        "extraction_method": extraction,
        "text": text,
        "integrity_flags": flags,
        "status": "blocked_integrity_review" if flags else "pending_editorial_authoring",
        "release_boundary": "intake_only_not_candidate_visible",
        "next_step": "Independently author questions, import through the private bank, run automated QA, human content review, independent SME approval, staging, and activation.",
    }
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in payload.items() if key != "text"}, indent=2))
    print(f"private_intake_path={output}")
    return 3 if flags else 0


if __name__ == "__main__":
    raise SystemExit(main())
