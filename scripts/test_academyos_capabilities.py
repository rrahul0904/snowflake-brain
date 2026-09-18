#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def check(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def main() -> None:
    view = read("frontend/views/academyos-practice-hub-v26.js")
    router = read("frontend/router-complete.js")
    sidebar = read("frontend/components/study-shell.js")
    nav = read("frontend/components/nav.js")
    shell = read("frontend/index-v26.html")

    check('"#/practice-hub":"academyos-practice-hub-v26.js"' in router, "Practice Hub route missing")
    check("Practice Hub" in sidebar, "Practice Hub navigation missing")
    check('["#/practice-hub", "#/practice"]' in nav, "Practice Hub must retain Practice primary-nav identity")
    for token in (
        "Domain Scoring",
        "Diagnostic",
        "Targeted Drill",
        "Quick Mock",
        "Full Mock",
        "Blitz",
        "Architecture Builder",
        "Persistent Progression",
        "getTaskProgress",
        "getMockHistory",
        "getHomeSummary",
        "scheduleTaskReview",
    ):
        check(token in view, f"AcademyOS donor behavior missing: {token}")

    check("progress.completed_tasks" in view, "hub must use persisted curriculum progression")
    check("summary.domains" in view, "hub must render persisted domain scoring")
    check("readiness_score" in view, "hub must surface readiness evidence")
    check("academyos-practice-hub.css" in shell, "Practice Hub stylesheet missing")
    check("bank_pool" not in view and "correct_json" not in view, "private bank metadata leaked")
    print("ACADEMYOS DONOR SLICE: PASS")


if __name__ == "__main__":
    main()
