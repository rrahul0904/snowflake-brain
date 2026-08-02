from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from .config import SNOWFLAKE_LABS_CONFIG, SNOWFLAKE_LABS_MODE
from .skill_brain import certifications, flatten_skills


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": "missing", "mode": SNOWFLAKE_LABS_MODE, "labs": []}
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_lab_config() -> dict[str, Any]:
    data = _read_json(SNOWFLAKE_LABS_CONFIG)
    data.setdefault("mode", SNOWFLAKE_LABS_MODE)
    data.setdefault("labs", [])
    return data


def labs() -> list[dict[str, Any]]:
    return load_lab_config().get("labs", [])


def lab_by_id(lab_id: str) -> dict[str, Any] | None:
    for lab in labs():
        if str(lab.get("id")) == str(lab_id):
            return dict(lab)
    return None


def _normalize_sql(sql: str) -> str:
    without_line_comments = re.sub(r"--.*?$", " ", sql or "", flags=re.MULTILINE)
    without_block_comments = re.sub(r"/\*.*?\*/", " ", without_line_comments, flags=re.DOTALL)
    return re.sub(r"\s+", " ", without_block_comments.upper()).strip()


def _contains(normalized: str, pattern: str) -> bool:
    pattern_norm = re.sub(r"\s+", " ", str(pattern).upper()).strip()
    return bool(pattern_norm) and pattern_norm in normalized


def validate_sql(lab: dict[str, Any], sql: str) -> dict[str, Any]:
    normalized = _normalize_sql(sql)
    tests = lab.get("validation_tests") or []
    results: list[dict[str, Any]] = []
    for idx, test in enumerate(tests, start=1):
        test_type = test.get("type", "contains_all")
        patterns = test.get("patterns") or test.get("required_patterns") or []
        forbidden = test.get("forbidden_patterns") or []
        name = test.get("name") or f"Validation {idx}"
        passed = False
        missing: list[str] = []
        found: list[str] = []

        if test_type == "contains_all":
            for pattern in patterns:
                if _contains(normalized, pattern):
                    found.append(pattern)
                else:
                    missing.append(pattern)
            passed = not missing
        elif test_type == "contains_any":
            found = [pattern for pattern in patterns if _contains(normalized, pattern)]
            passed = bool(found)
            missing = [] if passed else list(patterns)
        elif test_type == "regex":
            expr = test.get("pattern") or ""
            passed = bool(re.search(expr, sql or "", flags=re.IGNORECASE | re.MULTILINE | re.DOTALL))
            missing = [] if passed else [expr]
        elif test_type == "ordered_contains":
            cursor = 0
            passed = True
            for pattern in patterns:
                pattern_norm = re.sub(r"\s+", " ", str(pattern).upper()).strip()
                pos = normalized.find(pattern_norm, cursor)
                if pos < 0:
                    missing.append(pattern)
                    passed = False
                    break
                found.append(pattern)
                cursor = pos + len(pattern_norm)
        elif test_type == "minimum_statement_count":
            required = int(test.get("count") or 1)
            actual = len([part for part in (sql or "").split(";") if part.strip()])
            passed = actual >= required
            if not passed:
                missing = [f"{required} statements required; found {actual}"]
        else:
            missing = [f"Unsupported validation type: {test_type}"]
            passed = False

        failed_forbidden = [pattern for pattern in forbidden if _contains(normalized, pattern)]
        if failed_forbidden:
            passed = False

        results.append(
            {
                "name": name,
                "type": test_type,
                "passed": passed,
                "found": found,
                "missing": missing,
                "forbidden_found": failed_forbidden,
                "message": test.get("message") or ("Passed" if passed else "Needs work"),
            }
        )

    passed_count = sum(1 for result in results if result["passed"])
    total = len(results)
    passed = total > 0 and passed_count == total
    if passed:
        feedback = "Passed. Your SQL satisfies every offline validation test."
    elif total:
        feedback = f"{passed_count}/{total} checks passed. Fix the failed checks, then submit again."
    else:
        feedback = "No validation tests are configured for this lab."
    return {
        "passed": passed,
        "passed_count": passed_count,
        "total": total,
        "score_pct": round((passed_count / total) * 100) if total else 0,
        "feedback": feedback,
        "results": results,
        "mode": SNOWFLAKE_LABS_MODE,
        "solution_unlocked": True,
    }


def lab_catalog() -> list[dict[str, Any]]:
    # Build one lookup across every configured certification.  v4 only looked at
    # SnowPro Core, which made cross-certification labs feel disconnected from
    # the Skill Brain.
    skill_lookup: dict[str, dict[str, Any]] = {}
    for cert in certifications():
        for skill in flatten_skills(cert.get("id")):
            skill_lookup[str(skill.get("id"))] = skill

    output = []
    for lab in labs():
        row = {key: lab.get(key) for key in [
            "id", "title", "certification", "domain_id", "domain", "skill_id", "skill",
            "difficulty", "estimated_minutes", "why_it_matters", "scenario"
        ]}
        skill = skill_lookup.get(str(lab.get("skill_id")))
        row["exam_traps"] = (lab.get("exam_traps") or (skill.get("exam_traps", []) if skill else []))
        row["test_count"] = len(lab.get("validation_tests") or [])
        output.append(row)
    return output
