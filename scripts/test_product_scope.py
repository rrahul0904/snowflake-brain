#!/usr/bin/env python3
from __future__ import annotations

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
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
            for token in BANNED_TOKENS:
                if token.lower() in text:
                    findings.append(f"{path.relative_to(ROOT)} -> {token}")
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
