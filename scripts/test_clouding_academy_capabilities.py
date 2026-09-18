#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def check(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def main() -> None:
    view = read("frontend/views/clouding-practice-v26.js")
    router = read("frontend/router-complete.js")
    sidebar = read("frontend/components/study-shell.js")
    shell = read("frontend/index-v26.html")

    for route in ("#/daily-session", "#/blitz", "#/architecture-builder"):
        check(route in router, f"Clouding route missing: {route}")

    for token in ("Daily Certification Session", "Blitz Recall", "Architecture Builder", "getHomeSummary", "getStudyLesson", "scheduleTaskReview"):
        check(token in view, f"Clouding donor behavior missing: {token}")

    check("readiness_score" in view, "daily session must use readiness evidence")
    check("completed_tasks" in view, "daily session must use persisted curriculum progress")
    check("decision_rules" in view, "architecture builder must derive scenarios from curated decision rules")
    check("Again schedules the mapped task" in view, "Blitz review persistence contract missing")
    check("Daily Session" in sidebar and "Blitz Recall" in sidebar and "Architecture Builder" in sidebar, "study navigation incomplete")
    check("clouding-learning.css" in shell, "Clouding stylesheet missing")
    check("bank_pool" not in view and "correct_json" not in view, "private question-bank metadata leaked")
    print("CLOUDING ACADEMY DONOR SLICE: PASS")


if __name__ == "__main__":
    main()
