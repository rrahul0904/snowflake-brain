#!/usr/bin/env python3
"""Launch gate for basic content-IP and certification-integrity controls.

This is a repository compliance check, not a legal determination or plagiarism engine.
It prevents obvious regressions in public claims, required notices, and provenance policy.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    ROOT / "docs" / "CONTENT_IP_COPYRIGHT_POLICY.md",
    ROOT / "docs" / "IP_REGISTRATION_RUNBOOK.md",
    ROOT / "beta-demo" / "legal.html",
    ROOT / "docs" / "COF_C03_PRIVATE_BANK_1200_MANIFEST.md",
]

PUBLIC_FILES = [
    ROOT / "beta-demo" / "index.html",
    ROOT / "beta-demo" / "app.js",
    ROOT / "beta-demo" / "blueprint-sync.js",
]

# Phrases that should never be used as affirmative marketing/source claims in the
# public learning experience. Legal/policy files are intentionally excluded.
BANNED_PUBLIC_PATTERNS = {
    "braindump": re.compile(r"\bbraindump(s)?\b", re.I),
    "exam dump download": re.compile(r"\bexam\s+dumps?\s+(download|pdf|questions?)\b", re.I),
    "leaked exam": re.compile(r"\bleaked\s+(exam|snowpro|certification)\b", re.I),
    "recalled live exam": re.compile(r"\brecalled\s+(live\s+)?exam\s+questions?\b", re.I),
    "guaranteed pass": re.compile(r"\b(100\s*%\s*)?(guaranteed\s+pass|pass\s+guarantee)\b", re.I),
    "actual exam dumps": re.compile(r"\bactual\s+exam\s+dumps?\b", re.I),
}


def fail(message: str, failures: list[str]) -> None:
    failures.append(message)


def main() -> int:
    failures: list[str] = []
    warnings: list[str] = []

    for path in REQUIRED_FILES:
        if not path.is_file():
            fail(f"Required IP/compliance artifact is missing: {path.relative_to(ROOT)}", failures)

    for path in PUBLIC_FILES:
        if not path.is_file():
            fail(f"Expected public beta file is missing: {path.relative_to(ROOT)}", failures)
            continue
        text = path.read_text(encoding="utf-8")
        for label, pattern in BANNED_PUBLIC_PATTERNS.items():
            if pattern.search(text):
                fail(f"Prohibited public-content pattern ({label}) found in {path.relative_to(ROOT)}", failures)

    index = ROOT / "beta-demo" / "index.html"
    if index.is_file():
        text = index.read_text(encoding="utf-8").lower()
        if "not affiliated with or endorsed by snowflake inc." not in text:
            fail("Public beta must retain an explicit Snowflake non-affiliation/endorsement disclaimer", failures)
        if "confidential exam content" not in text:
            fail("Public beta must state that practice material is not confidential exam content", failures)
        if "snowflake certification platform" in text:
            warnings.append(
                "The working product title contains the third-party SNOWFLAKE mark. "
                "Use a distinct ownable brand before trademark filing/commercial launch."
            )

    legal = ROOT / "beta-demo" / "legal.html"
    if legal.is_file():
        text = legal.read_text(encoding="utf-8").lower()
        required_legal_phrases = [
            "copyright & intellectual property notice",
            "not affiliated with, sponsored by, approved by, or endorsed by snowflake inc.",
            "we do not knowingly publish live, leaked, stolen, recalled, reconstructed, or confidential certification exam questions",
            "ip notice:",
        ]
        for phrase in required_legal_phrases:
            if phrase not in text:
                fail(f"Public legal notice is missing required language: {phrase}", failures)

    manifest = ROOT / "docs" / "COF_C03_PRIVATE_BANK_1200_MANIFEST.md"
    if manifest.is_file():
        text = manifest.read_text(encoding="utf-8").lower()
        if "independently authored" not in text:
            fail("Private-bank manifest must preserve the independently-authored provenance statement", failures)
        if "does **not** reproduce live certification questions" not in text:
            fail("Private-bank manifest must preserve the no-live-exam/no-dump statement", failures)
        if "docs.snowflake.com" not in text:
            fail("Private-bank manifest must document official factual source references", failures)

    # Do not allow official-looking logo assets to silently enter the public beta.
    for base in (ROOT / "beta-demo", ROOT / "frontend"):
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            name = path.name.lower()
            if "snowflake-logo" in name or "snowpro-logo" in name:
                fail(f"Potential third-party logo asset requires explicit rights review: {path.relative_to(ROOT)}", failures)

    for warning in warnings:
        print(f"WARNING: {warning}")

    if failures:
        print("CONTENT IP COMPLIANCE: FAIL")
        for item in failures:
            print(f" - {item}")
        return 1

    print("CONTENT IP COMPLIANCE: PASS")
    print(" - required copyright/IP policy artifacts present")
    print(" - public non-affiliation and confidential-exam disclaimers present")
    print(" - no prohibited dump/leak/pass-guarantee claims detected in public beta files")
    print(" - private question-bank provenance assertions present")
    print(" - no Snowflake/SnowPro logo-named assets detected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
