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
    ("app/routers/question_feedback.py", "/questions/{question_id}/feedback"),
    ("frontend/views/practice-v26.js", "Report question"),
    ("scripts/question_source_intake.py", "human_supplied_transcript"),
    ("scripts/question_source_intake.py", "question_generation_allowed"),
]

for path, token in checks:
    text = (ROOT / path).read_text(encoding="utf-8")
    if token not in text:
        raise AssertionError(f"{path} missing donor contract token: {token}")

print("LeetQuiz donor integration: PASS")
