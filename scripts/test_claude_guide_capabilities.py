#!/usr/bin/env python3
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def check(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def main() -> None:
    content = read("app/certification_content.py")
    lesson = read("frontend/views/lesson-v26.js")
    router = read("frontend/router-complete.js")
    study = read("frontend/components/study-shell.js")
    ast.parse(content)

    for route in ("#/exam-guide", "#/curriculum", "#/domain", "#/skill", "#/quick-reference", "#/glossary", "#/exam-traps"):
        check(route in router or route in study or route in lesson, f"certification guide route missing: {route}")

    for token in ("Decision Rules", "Exam Traps", "Worked Example", "Practice Scenario", "Build Exercise"):
        check(token in lesson, f"task lesson element missing: {token}")

    for token in ("Task Workbench", "Concept Check", "Exam Sim", "Build Coach", "sourceTrust"):
        check(token in lesson, f"Claude-guide donor behavior missing: {token}")

    for token in ("source_trust", "certification_verified_at", "official_snowflake_documentation_preferred", "source_count"):
        check(token in content, f"source freshness/trust contract missing: {token}")

    check('data-learning-mode="concept-check"' in lesson, "Concept Check is not wired to the lesson scenario")
    check('data-learning-mode="build-coach"' in lesson, "Build Coach is not wired to the build exercise")
    print("CLAUDE CERTIFICATION GUIDE DONOR SLICE: PASS")


if __name__ == "__main__":
    main()
