#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "artifacts" / "reverse-engineering-coverage.json"

REQUIRED_CATEGORIES = {
    "GLOBAL_SHELL", "HOME", "CERTIFICATION_DISCOVERY", "CERTIFICATION_FACTS", "CURRICULUM",
    "DOMAIN", "LESSON", "PROGRESS", "DRILL", "DIAGNOSTIC", "PRACTICE", "MOCK_START",
    "MOCK_PLAYER", "RESULTS", "QUICK_REFERENCE", "GLOSSARY", "BUILD_EXERCISES", "REFERENCE",
    "JOURNAL", "FEEDBACK", "THEME", "RESPONSIVE", "ACCESSIBILITY", "ACTIVITY_GLOBE", "AUTH",
    "ACCOUNT_LIFECYCLE", "MEMBERSHIP", "BILLING", "QUESTION_BANK", "CONTENT_GOVERNANCE",
    "ADAPTIVE_READINESS", "LEARNING_INTELLIGENCE", "CREDENTIALS", "TRUST_LEGAL", "OBSERVABILITY",
    "SECURITY", "PRODUCTION_OPERATIONS",
}
ALLOWED = {
    "IMPLEMENTED_AND_TESTED",
    "INTENTIONALLY_NOT_IMPLEMENTED",
    "SUPERSEDED_BY_BETTER_SNOWFLAKE_NATIVE_IMPLEMENTATION",
    "EXTERNAL_CONFIGURATION",
    "FUTURE_SCOPE",
}
FORBIDDEN_P01 = {"MISSING_TO_IMPLEMENT", "PARTIAL", "TODO", "PLACEHOLDER", "UNKNOWN", "MAYBE"}
REQUIRED_FIELDS = {
    "id", "source", "source_date", "category", "requirement", "priority", "current_status",
    "implementation_evidence", "test_evidence", "route", "backend_component", "frontend_component",
    "intentional_difference", "rationale", "external_dependency", "final_disposition",
}


def check(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def validate_matrix() -> dict:
    check(MATRIX.is_file(), "coverage matrix JSON is missing")
    payload = json.loads(MATRIX.read_text(encoding="utf-8"))
    rows = payload.get("requirements") or []
    check(rows, "coverage matrix has no requirements")
    ids: set[str] = set()
    categories: set[str] = set()
    for index, row in enumerate(rows):
        missing = REQUIRED_FIELDS - set(row)
        check(not missing, f"coverage row {index} missing fields: {sorted(missing)}")
        rid = str(row["id"])
        check(rid and rid not in ids, f"duplicate/empty requirement id: {rid}")
        ids.add(rid)
        category = str(row["category"])
        categories.add(category)
        priority = str(row["priority"])
        disposition = str(row["final_disposition"])
        check(disposition in ALLOWED, f"invalid final disposition for {rid}: {disposition}")
        check(str(row["current_status"]) == disposition, f"status/disposition drift for {rid}")
        check(str(row["requirement"]).strip(), f"missing requirement text for {rid}")
        check(str(row["rationale"]).strip(), f"missing rationale for {rid}")
        if priority in {"P0", "P1"}:
            check(disposition not in FORBIDDEN_P01, f"P0/P1 remains unresolved: {rid} -> {disposition}")
            check(disposition in ALLOWED, f"P0/P1 lacks explicit allowed disposition: {rid}")
        if disposition == "IMPLEMENTED_AND_TESTED":
            check(row["implementation_evidence"], f"implemented row lacks implementation evidence: {rid}")
            check(row["test_evidence"], f"implemented row lacks test evidence: {rid}")
        if disposition == "EXTERNAL_CONFIGURATION":
            check(str(row["external_dependency"] or "").strip(), f"external row lacks dependency: {rid}")
        if disposition in {"INTENTIONALLY_NOT_IMPLEMENTED", "SUPERSEDED_BY_BETTER_SNOWFLAKE_NATIVE_IMPLEMENTATION", "FUTURE_SCOPE"}:
            check(str(row["intentional_difference"] or "").strip(), f"non-parity row lacks explicit difference: {rid}")
    check(REQUIRED_CATEGORIES <= categories, f"coverage categories missing: {sorted(REQUIRED_CATEGORIES - categories)}")
    unresolved = [row["id"] for row in rows if row["priority"] in {"P0", "P1"} and row["final_disposition"] in FORBIDDEN_P01]
    check(not unresolved, f"P0/P1 unresolved: {unresolved}")
    return payload


def validate_certification_facts() -> None:
    catalog = json.loads(read("config/certification_catalog.json"))
    by_id = {row["id"]: row for row in catalog.get("official_certifications") or []}
    for cid in ("snowpro-core", "advanced-data-engineer", "advanced-architect"):
        row = by_id[cid]
        for key in ("source_url", "official_exam_url", "policy_url", "source_verified_at", "fact_status", "source_status"):
            check(row.get(key), f"{cid} missing verified-fact field: {key}")
        check(row["fact_status"] == "verified_with_explicit_unknowns", f"{cid} fact status")
    core = by_id["snowpro-core"]
    check(core["fee_usd"] == 175, "Core fee contract")
    check(core["domain_count"] == 5, "Core domain count")
    check([row["weight"] for row in core["exam_domains"]] == [31, 20, 18, 21, 10], "Core domain weights")
    check(core["credential_validity_months"] == 24, "credential validity contract")
    check(core["retake_wait_days"] == 7 and core["retake_limit_per_12_months"] == 4, "retake policy contract")
    for key in ("item_count", "item_formats", "duration_minutes", "scoring"):
        check(core[key] is None, f"unverified Core fact must remain null: {key}")
        check(core["source_status"].get(key) == "not_verified", f"unverified Core fact must be marked: {key}")
    check(by_id["advanced-data-engineer"]["fee_usd"] == 375, "Data Engineer fee contract")
    check(by_id["advanced-architect"]["fee_usd"] == 375, "Architect fee contract")


def validate_product_gaps() -> None:
    security = read("app/security.py")
    check('"/api/skills/catalog"' in security, "public catalog API boundary missing")
    check('"/static/views/certifications.js"' in security, "public certification view missing")
    check('"/api/skills/map"' not in security.split("PUBLIC_API_EXACT", 1)[1].split("PUBLIC_API_PREFIXES", 1)[0], "skill map accidentally public")

    router = read("frontend/router-complete.js")
    check('"#/certifications"' in router and '"#/content-integrity"' in router, "public informational routes missing")

    cert_view = read("frontend/views/certifications.js")
    check("source_verified_at" in cert_view and "Published items" in cert_view and "Study guide coming soon" in cert_view, "certification fact UI incomplete")

    info = read("frontend/views/info-v26.js")
    for token in ("Not guessed", "source_verified_at", "Official Snowflake page", "no exam dumps"):
        check(token.lower() in info.lower(), f"exam/trust UI missing: {token}")

    sidebar = read("frontend/components/study-shell.js")
    lesson = read("frontend/views/lesson-v26.js")
    curriculum = read("frontend/views/curriculum-v26.js")
    check("data-sidebar-skill" in sidebar and "v26-task-complete" in sidebar, "sidebar completion marker missing")
    check("syncSidebarCompletion" in lesson and "completedSkillIds" in sidebar, "lesson completion does not update sidebar")
    check("Promise.all" in curriculum and "getTaskProgress" in curriculum, "curriculum completion must use one progress fetch")

    result = read("frontend/views/exam-result-v26.js")
    check('reviewFilter === "unanswered"' in result, "unanswered review filter missing")
    check('filterButton("unanswered", "Unanswered"' in result, "unanswered filter control missing")

    footer = read("frontend/app-complete.js")
    check("Not affiliated with, sponsored by, approved by, or endorsed by Snowflake Inc." in footer, "footer non-affiliation missing")
    check("#/content-integrity" in footer, "content-integrity footer link missing")
    check((ROOT / "docs" / "CONTENT_INTEGRITY_AND_IP_POLICY.md").is_file(), "V26 content integrity policy missing")
    check(not (ROOT / "beta-demo").exists(), "retired beta-demo architecture was resurrected")


def validate_lab_depth() -> None:
    payload = json.loads(read("config/snowflake_lab_challenges.json"))
    core = [row for row in payload.get("labs") or [] if row.get("certification") == "snowpro-core"]
    check(core, "SnowPro Core labs missing")
    required = {
        "title", "difficulty", "estimated_minutes", "scenario", "instructions", "expected_output",
        "starter_sql", "hints", "validation_tests", "solution_sql", "exam_traps",
    }
    for row in core:
        missing = required - set(row)
        check(not missing, f"Core lab {row.get('id')} missing instructional fields: {sorted(missing)}")
        check(row["hints"] and row["validation_tests"], f"Core lab {row.get('id')} lacks deterministic coaching")


def validate_bank_contract() -> None:
    manifest = read("docs/COF_C03_PRIVATE_BANK_1200_MANIFEST.md")
    for token in (
        "da57f636a57180631448fda79cfdcad2acf8e38ae2f381ea891a8cea91e704c5",
        "**1,200**", "free", "practice", "mock", "diagnostic",
    ):
        check(token.lower() in manifest.lower(), f"private bank manifest contract missing: {token}")
    audit = read("scripts/audit_private_bank_quality.py")
    check("no question text" in audit.lower(), "private-bank audit privacy contract missing")
    check("EXPECTED_TOTAL = 1200" in audit and "correct_answer_is_longest_pct" in audit, "private-bank bias audit incomplete")


def main() -> None:
    payload = validate_matrix()
    validate_certification_facts()
    validate_product_gaps()
    validate_lab_depth()
    validate_bank_contract()
    rows = payload["requirements"]
    p01 = [row for row in rows if row["priority"] in {"P0", "P1"}]
    counts: dict[str, int] = {}
    for row in p01:
        counts[row["final_disposition"]] = counts.get(row["final_disposition"], 0) + 1
    print("REVERSE ENGINEERING COMPLETENESS: PASS")
    print(f"requirements={len(rows)} p0_p1={len(p01)}")
    print("p0_p1_dispositions=" + json.dumps(counts, sort_keys=True))
    print("p0_p1_missing=0")


if __name__ == "__main__":
    main()
