#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

checks = [
    ("frontend/router-complete.js", '"#/question-studio":"question-studio-v26.js"'),
    ("frontend/views/question-studio-v26.js", "Question Studio"),
    ("frontend/views/question-studio-v26.js", 'import { escapeHtml } from "../api.js";'),
    ("frontend/views/question-studio-v26.js", "/api/skills/map"),
    ("frontend/views/question-studio-v26.js", "unanswered_only"),
    ("docs/DONOR_LEETQUIZ.md", "no public question inventory"),
]

for path, token in checks:
    text = (ROOT / path).read_text(encoding="utf-8")
    if token not in text:
        raise AssertionError(f"{path} missing donor contract token: {token}")

print("LeetQuiz donor integration: PASS")
