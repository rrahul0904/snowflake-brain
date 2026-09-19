#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


router = read("frontend/router-complete.js")
public_routes = router.split("const publicRoutes", 1)[1].split(";", 1)[0]

required_routes = {
    '"#/question-studio":"question-studio-v26.js"',
    '"#/daily-session":"daily-session-v26.js"',
    '"#/practice-hub":"practice-hub-v26.js"',
    '"#/exam-guide":"exam-guide-v26.js"',
}
for token in required_routes:
    if token not in router:
        raise AssertionError(f"integrated donor route missing: {token}")

if '"#/exam-guide"' not in public_routes:
    raise AssertionError("exam guide must remain public")
for protected in ('"#/question-studio"', '"#/daily-session"', '"#/practice-hub"'):
    if protected in public_routes:
        raise AssertionError(f"candidate donor route accidentally public: {protected}")

views = {
    "frontend/views/question-studio-v26.js": (
        "getSkillMap",
        "getStudyLesson",
        "Question Studio",
        "Socratic Coach",
        "unanswered_only",
    ),
    "frontend/views/exam-guide-v26.js": (
        "getCertificationCatalog",
        "Source verification:",
        "Blueprint map",
        "Official Snowflake page",
    ),
    "frontend/views/daily-session-v26.js": (
        "getDailyStreak",
        "recordDailyRecall",
        "Blitz recall",
        "Architecture Builder",
    ),
    "frontend/views/practice-hub-v26.js": (
        'from "../api.js"',
        "#/daily-session?track_id=",
        "Practice Hub",
    ),
}
for path, tokens in views.items():
    text = read(path)
    for token in tokens:
        if token not in text:
            raise AssertionError(f"{path} missing integration token: {token}")

daily_view = read("frontend/views/daily-session-v26.js")
if "localStorage" in daily_view:
    raise AssertionError("integrated daily recall must use server-persisted evidence")

api = read("frontend/api.js")
for token in (
    "submitQuestionFeedback",
    "getQuestionFeedback",
    "getDailyStreak",
    "recordDailyRecall",
):
    if token not in api:
        raise AssertionError(f"combined client API missing donor helper: {token}")

backend_contracts = {
    "app/routers/question_feedback.py": (
        "/questions/{question_id}/feedback",
        "/admin/question-feedback",
    ),
    "app/public_discovery.py": (
        "/discover/{certification_id}",
        "/sitemap.xml",
    ),
    "app/production_schema.py": ('"question_feedback"',),
    "app/account_lifecycle.py": (
        '"question_corrections"',
        "DELETE FROM question_feedback",
    ),
    "app/learning_intelligence.py": (
        "def daily_recall_streak",
        "def record_daily_recall",
    ),
    "app/routers/intelligence.py": (
        "/intelligence/daily-streak",
        "/intelligence/daily-recall",
    ),
}
for path, tokens in backend_contracts.items():
    text = read(path)
    for token in tokens:
        if token not in text:
            raise AssertionError(f"{path} missing combined backend token: {token}")

if not (ROOT / "migrations/postgres/20260918_001_question_feedback.sql").is_file():
    raise AssertionError("question feedback PostgreSQL migration missing")

nav = read("frontend/components/nav.js")
for token in ("Practice Hub", "Daily Session", "Question Studio"):
    if token not in nav:
        raise AssertionError(f"account navigation missing integrated tool: {token}")

required_tests = (
    "scripts/test_question_feedback.py",
    "scripts/test_question_source_intake.py",
    "scripts/test_public_discovery.py",
    "scripts/test_daily_recall_streak.py",
    "scripts/test_donor_leetquiz.py",
    "scripts/test_donor_claude_cert_guide.py",
    "scripts/test_donor_clouding_academy.py",
    "scripts/test_donor_academyos_ai.py",
)
for test in required_tests:
    if not (ROOT / test).is_file():
        raise AssertionError(f"donor regression missing: {test}")

verify = read("scripts/verify_all.sh")
for token in (
    "Public certification SEO/discovery",
    "Private editorial source intake",
    "Served-question correction workflow",
    "Persisted daily recall streak",
    "Donor ES-module import smoke",
    "Combined donor learning suite",
):
    if token not in verify:
        raise AssertionError(f"full verification missing donor gate: {token}")

for doc in (
    "docs/DONOR_LEETQUIZ.md",
    "docs/DONOR_CLAUDE_CERT_GUIDE.md",
    "docs/DONOR_CLOUDING_ACADEMY.md",
    "docs/DONOR_ACADEMYOS_AI.md",
):
    if not (ROOT / doc).is_file():
        raise AssertionError(f"donor boundary doc missing: {doc}")

print("Donor learning suite integration: PASS")
