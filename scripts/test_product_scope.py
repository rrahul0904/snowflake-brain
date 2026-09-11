#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

BANNED_TOKENS = {
    "#/video",
    "video-player",
    "transcript-player",
    "course-player",
    "/api/video",
    "/api/media",
    "/api/courses",
    "youtube.com/embed",
    "youtu.be/",
    "player.vimeo.com",
    "<video",
}

# Backend routers are typically mounted under /api, so route decorators can be
# relative (for example @router.get("/media")). Catch those definitions too.
BANNED_BACKEND_ROUTE_PATTERNS = (
    re.compile(r"@(?:router|app)\.(?:get|post|put|patch|delete|options|head)\(\s*[\"']/(?:video|media|courses)(?:[\"'/])", re.IGNORECASE),
    re.compile(r"APIRouter\([^)]*\bprefix\s*=\s*[\"']/(?:video|media|courses)(?:[\"'/])", re.IGNORECASE | re.DOTALL),
)

SCAN_ROOTS = [ROOT / "frontend", ROOT / "app"]
TEXT_SUFFIXES = {".py", ".js", ".html", ".css", ".json", ".md", ".txt"}


def check(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def scan_active_runtime() -> list[str]:
    findings: list[str] = []
    for base in SCAN_ROOTS:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            lowered = text.lower()
            for token in BANNED_TOKENS:
                if token.lower() in lowered:
                    findings.append(f"{path.relative_to(ROOT)} -> {token}")
            if path.suffix.lower() == ".py":
                for pattern in BANNED_BACKEND_ROUTE_PATTERNS:
                    if pattern.search(text):
                        findings.append(f"{path.relative_to(ROOT)} -> relative video/course/media API route")
    return findings


def main() -> None:
    scope = ROOT / "docs" / "PRODUCT_SCOPE.md"
    check(scope.is_file(), "authoritative PRODUCT_SCOPE.md is missing")
    scope_text = scope.read_text(encoding="utf-8").lower()
    check("video learning is intentionally **not part of this product**" in scope_text, "video exclusion is not explicit in product scope")

    readme = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    check("it is not a video course platform" in readme, "README product boundary no longer excludes video-course runtime")

    findings = scan_active_runtime()
    check(not findings, "retired video/course/media runtime resurfaced:\n" + "\n".join(findings))

    print("PRODUCT SCOPE: PASS")
    print("video_learning=INTENTIONALLY_NOT_IMPLEMENTED")
    print("active_video_course_runtime=0")


if __name__ == "__main__":
    main()
