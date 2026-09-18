#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

checks = [["frontend/router-complete.js","\"#/daily-session\":\"daily-session-v26.js\""],["frontend/views/daily-session-v26.js","Daily Certification Session"],["frontend/views/daily-session-v26.js","Blitz recall"],["frontend/views/daily-session-v26.js","Architecture Builder"],["docs/DONOR_CLOUDING_ACADEMY.md","does not create a second curriculum"]]

for path, token in checks:
    text = (ROOT / path).read_text(encoding="utf-8")
    if token not in text:
        raise AssertionError(f"{path} missing donor contract token: {token}")

router = (ROOT / "frontend/router-complete.js").read_text(encoding="utf-8")
pass
print("Clouding Academy donor integration: PASS")
