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
        'import { escapeHtml } from "../api.js";',
        "Question Studio",
        "unanswered_only",
    ),
    "frontend/views/exam-guide-v26.js": (
        'import { escapeHtml } from "../api.js";',
        "/api/skills/catalog",
        "Blueprint map",
    ),
    "frontend/views/daily-session-v26.js": (
        'import { escapeHtml } from "../api.js";',
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

nav = read("frontend/components/nav.js")
for token in ("Practice Hub", "Daily Session", "Question Studio"):
    if token not in nav:
        raise AssertionError(f"account navigation missing integrated tool: {token}")

for test in (
    "scripts/test_donor_leetquiz.py",
    "scripts/test_donor_claude_cert_guide.py",
    "scripts/test_donor_clouding_academy.py",
    "scripts/test_donor_academyos_ai.py",
):
    if not (ROOT / test).is_file():
        raise AssertionError(f"donor regression missing: {test}")

for doc in (
    "docs/DONOR_LEETQUIZ.md",
    "docs/DONOR_CLAUDE_CERT_GUIDE.md",
    "docs/DONOR_CLOUDING_ACADEMY.md",
    "docs/DONOR_ACADEMYOS_AI.md",
):
    if not (ROOT / doc).is_file():
        raise AssertionError(f"donor boundary doc missing: {doc}")

print("Donor learning suite integration: PASS")
