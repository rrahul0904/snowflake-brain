#!/usr/bin/env python3
from __future__ import annotations

import http.cookiejar
import json
import os
import re
import time
import urllib.request
import uuid
from pathlib import Path
from typing import Any

from playwright.sync_api import Page, sync_playwright

BASE = os.environ.get("V26_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
OUT = Path(os.environ.get("V26_VISUAL_DIR", "artifacts/v26-visual-parity")) / "command-center-tools"
OUT.mkdir(parents=True, exist_ok=True)
COOKIE_JAR = http.cookiejar.CookieJar()
OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(COOKIE_JAR))
VIEWPORTS = [(1440, 1000), (1024, 900), (768, 900), (390, 844)]
THEMES = ("light", "dark")


def api(path: str, method: str = "GET", body: dict[str, Any] | None = None) -> Any:
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(f"{BASE}{path}", data=data, method=method, headers={"Content-Type": "application/json"})
    with OPENER.open(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_server() -> None:
    deadline = time.time() + 45
    while time.time() < deadline:
        try:
            if api("/api/health").get("status") == "ok": return
        except Exception: time.sleep(0.4)
    raise RuntimeError("server not ready")


def register_candidate() -> None:
    email = f"command-center-{uuid.uuid4().hex[:8]}@example.com"
    payload = api("/api/auth/register", "POST", {"display_name": "Command Center QA", "email": email, "password": "CommandCenterVisual!123"})
    if not payload.get("authenticated"): raise AssertionError("candidate registration did not establish a session")


def certification_ids() -> tuple[str, str]:
    payload = api("/api/skills/map")
    cert = next(item for item in payload.get("certifications", []) if item.get("id") == "snowpro-core")
    domain = (cert.get("domains") or [])[0]
    skill = (domain.get("skills") or [])[0]
    return str(domain["id"]), str(skill["id"])


def routes(domain_id: str, skill_id: str) -> dict[str, tuple[str, tuple[str, ...]]]:
    return {
        "home-command-center": ("#/home", (".v26-home-hero", ".v26-home-command-wrap", "[data-evidence-confidence]")),
        "curriculum-domain-map": ("#/curriculum?track_id=snowpro-core", (".v26-curriculum-list", ".v26-study-nav")),
        "domain-detail": (f"#/domain?track_id=snowpro-core&domain_id={domain_id}", (".v26-learning-command", ".v26-domain-task-section")),
        "task-handbook": (f"#/skill?track_id=snowpro-core&skill_id={skill_id}", (".v26-lesson-head", ".v26-decision-rules", "[data-add-review]")),
        "targeted-drill": (f"#/practice?track_id=snowpro-core&mode=drill&skill_id={skill_id}", ("[data-difficulty]", "[data-unanswered-only]", "[data-session-count]")),
        "progress": ("#/progress?track_id=snowpro-core", (".v26-readiness-panel", ".v26-recording-domain-progress")),
        "adaptive-readiness": ("#/adaptive?track_id=snowpro-core", (".v26-adaptive-overview", ".v26-readiness-radar")),
        "due-today": ("#/due?track_id=snowpro-core", (".v26-recording-progress-head",)),
        "mistake-notebook": ("#/mistakes?track_id=snowpro-core", (".v26-mistake-summary", ".v26-mistake-filter-panel")),
        "confidence-calibration": ("#/confidence?track_id=snowpro-core", (".v26-recording-progress-head",)),
        "study-plan": ("#/study-plan?track_id=snowpro-core", (".command-plan",)),
        "exam-traps": ("#/exam-traps?track_id=snowpro-core", (".v26-trap-controls", ".v26-trap-library")),
        "build-exercises": ("#/exercises?track_id=snowpro-core", (".v26-learning-command", ".v26-exercise-domain-list")),
        "lab-workspace": ("#/labs?certification=snowpro-core", (".lab-runner-frame",)),
    }


def set_theme(page: Page, theme: str) -> None:
    page.evaluate("theme => window.__setSnowflakeTheme?.(theme)", theme)
    page.wait_for_timeout(80)
    if page.locator("html").get_attribute("data-theme") != theme: raise AssertionError(f"theme did not apply: {theme}")


def no_overflow(page: Page, label: str) -> None:
    if page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth + 2"):
        raise AssertionError(f"horizontal overflow: {label}")


def run(browser, width: int, height: int, route_map: dict[str, tuple[str, tuple[str, ...]]]) -> int:
    context = browser.new_context(viewport={"width": width, "height": height}, reduced_motion="reduce")
    context.add_cookies([{"name": cookie.name, "value": cookie.value, "url": BASE} for cookie in COOKIE_JAR])
    page = context.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda exc: errors.append(f"pageerror: {exc}"))
    page.on("console", lambda msg: errors.append(f"console {msg.type}: {msg.text}") if msg.type == "error" else None)
    shots = 0
    for theme in THEMES:
        for name, (hash_path, selectors) in route_map.items():
            errors.clear()
            page.goto(f"{BASE}/{hash_path}", wait_until="domcontentloaded")
            page.wait_for_selector("#view-root[data-route-ok='true']")
            set_theme(page, theme)
            page.wait_for_timeout(120)
            for selector in selectors: page.wait_for_selector(selector)
            if page.locator("#view-root[data-view-id='authentication-required']").count(): raise AssertionError(f"authenticated route unexpectedly gated: {name}")
            no_overflow(page, f"{width}x{height}-{theme}-{name}")
            if errors: raise AssertionError("browser errors: " + " | ".join(errors))
            page.screenshot(path=str(OUT / f"{width}x{height}-{theme}-{slug(name)}.png"), full_page=True, animations="disabled")
            shots += 1
    context.close()
    return shots


def slug(value: str) -> str: return re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")


def main() -> None:
    wait_server(); register_candidate(); domain_id, skill_id = certification_ids(); route_map = routes(domain_id, skill_id)
    total = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            for width, height in VIEWPORTS: total += run(browser, width, height, route_map)
        finally: browser.close()
    print(f"Command Center authenticated visual acceptance: PASS screenshots={total}")


if __name__ == "__main__": main()
