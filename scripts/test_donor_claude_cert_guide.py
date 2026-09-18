#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

checks = [
    ("frontend/router-complete.js", '"#/exam-guide":"exam-guide-v26.js"'),
    ("frontend/views/exam-guide-v26.js", "/api/skills/catalog"),
    ("frontend/views/exam-guide-v26.js", "Blueprint map"),
    ("frontend/views/exam-guide-v26.js", 'import { escapeHtml } from "../api.js";'),
    ("frontend/views/exam-guide-v26.js", "Exam Traps"),
    ("docs/DONOR_CLAUDE_CERT_GUIDE.md", "No parallel content store"),
    ("app/security.py", '"/static/views/exam-guide-v26.js"'),
]

for path, token in checks:
    text = (ROOT / path).read_text(encoding="utf-8")
    if token not in text:
        raise AssertionError(f"{path} missing donor contract token: {token}")

router = (ROOT / "frontend/router-complete.js").read_text(encoding="utf-8")
public_routes = router.split("const publicRoutes", 1)[1].split(";", 1)[0]
if '"#/exam-guide"' not in public_routes:
    raise AssertionError("exam guide must remain public")

exam_guide = (ROOT / "frontend/views/exam-guide-v26.js").read_text(encoding="utf-8")
if "/api/skills/map" in exam_guide:
    raise AssertionError("public exam guide must not use protected skill-map API")

print("Claude Certification Guide donor integration: PASS")
