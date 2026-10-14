#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

checks = [["frontend/router-complete.js","\"#/practice-hub\":\"practice-hub-v26.js\""],["frontend/views/practice-hub-v26.js","Practice Hub"],["frontend/views/practice-hub-v26.js","getAdaptiveReadiness"],["frontend/views/practice-hub-v26.js","getMockHistory"],["docs/DONOR_ACADEMYOS_AI.md","competing progress store"]]

for path, token in checks:
    text = (ROOT / path).read_text(encoding="utf-8")
    if token not in text:
        raise AssertionError(f"{path} missing donor contract token: {token}")

router = (ROOT / "frontend/router-complete.js").read_text(encoding="utf-8")
pass
print("AcademyOS AI donor integration: PASS")
