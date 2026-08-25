#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs" / "COF_C03_PRIVATE_BANK_1200_MANIFEST.md"
DEPLOYMENT = ROOT / "docs" / "PRIVATE_QUESTION_BANK_DEPLOYMENT.md"

EXPECTED_VERSION = "2026-08-14-beta-1200-v2"
EXPECTED_FILENAME = "snowpro_core_cof_c03_private_bank_1200_beta_v2.json"
EXPECTED_SHA = "da57f636a57180631448fda79cfdcad2acf8e38ae2f381ea891a8cea91e704c5"
EXPECTED_TOTAL = 1200
EXPECTED_DOMAINS = [372, 240, 216, 252, 120]
EXPECTED_POOLS = {"Free": 216, "Practice": 504, "Diagnostic": 120, "Mock reserved": 360}
EXPECTED_DIFFICULTIES = {"Foundation": 180, "Applied": 420, "Exam": 480, "Challenge": 120}


def require(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def extract_int(text: str, pattern: str, label: str) -> int:
    match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
    require(match, f"missing {label}")
    return int(match.group(1).replace(",", ""))


def main() -> None:
    manifest = MANIFEST.read_text(encoding="utf-8")
    deployment = DEPLOYMENT.read_text(encoding="utf-8")

    require(f"Bank version: `{EXPECTED_VERSION}`" in manifest, "question-bank version drifted")
    require(f"Private artifact filename: `{EXPECTED_FILENAME}`" in manifest, "private artifact filename drifted")
    require(f"SHA-256: `{EXPECTED_SHA}`" in manifest, "manifest SHA-256 drifted")
    require(re.fullmatch(r"[0-9a-f]{64}", EXPECTED_SHA), "expected bank SHA is malformed")

    total = extract_int(manifest, r"Total questions:\s*\*\*([0-9,]+)\*\*", "total question count")
    require(total == EXPECTED_TOTAL, f"manifest total must be {EXPECTED_TOTAL}, found {total}")

    domain_rows = re.findall(r"^\| (?:Snowflake AI Data Cloud Features and Architecture|Account Management and Data Governance|Data Loading, Unloading, and Connectivity|Performance Optimization, Querying, and Transformation|Data Collaboration) \| [0-9]+% \| ([0-9,]+) \|$", manifest, flags=re.MULTILINE)
    domain_counts = [int(value.replace(",", "")) for value in domain_rows]
    require(domain_counts == EXPECTED_DOMAINS, f"domain allocation drifted: {domain_counts}")
    require(sum(domain_counts) == total, "domain totals do not equal bank total")

    task_rows = re.findall(r"^\| ([1-5]\.[1-6]) \| .+? \| ([0-9,]+) \| ([0-9,]+) \| ([0-9,]+) \| ([0-9,]+) \| ([0-9,]+) \|$", manifest, flags=re.MULTILINE)
    require(len(task_rows) == 19, f"expected 19 task rows, found {len(task_rows)}")
    task_total = sum(int(row[1].replace(",", "")) for row in task_rows)
    require(task_total == total, f"task totals {task_total} do not equal {total}")

    for label, expected in EXPECTED_POOLS.items():
        value = extract_int(manifest, rf"^- {re.escape(label)}:\s*\*\*([0-9,]+)\*\*", f"{label} pool")
        require(value == expected, f"{label} pool expected {expected}, found {value}")
    require(sum(EXPECTED_POOLS.values()) == total, "configured pool totals do not equal bank total")

    for label, expected in EXPECTED_DIFFICULTIES.items():
        value = extract_int(manifest, rf"^- {re.escape(label)}:\s*\*\*([0-9,]+)\*\*", f"{label} difficulty")
        require(value == expected, f"{label} difficulty expected {expected}, found {value}")
    require(sum(EXPECTED_DIFFICULTIES.values()) == total, "configured difficulty totals do not equal bank total")

    # Deployment instructions and content manifest must identify the exact same private artifact.
    for token in (EXPECTED_VERSION, EXPECTED_FILENAME, EXPECTED_SHA, "Questions: 1,200"):
        require(token in deployment, f"deployment runbook does not match manifest token: {token}")

    # The active tier policy is the source of truth: Free's weekly full-content mock is 30Q/45m.
    require(
        re.search(r"Free Weekly Mock\s+is\s+30\s+questions\b", deployment, flags=re.IGNORECASE),
        "deployment runbook has stale Free Weekly Mock count",
    )
    require(
        re.search(r"Free Weekly Mock[^\n]*45\s+minutes", deployment, flags=re.IGNORECASE),
        "deployment runbook is missing the Free Weekly Mock duration",
    )

    print("Question-bank manifest/deployment integrity contract passed: 1,200 questions, 5 domains, 19 tasks.")


if __name__ == "__main__":
    main()
