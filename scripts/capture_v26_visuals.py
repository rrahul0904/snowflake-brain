#!/usr/bin/env python3
from __future__ import annotations

import http.cookiejar
import json
import os
import time
import urllib.request
import uuid
from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

BASE = os.environ.get("V26_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
OUT = Path(os.environ.get("V26_VISUAL_DIR", "artifacts/v26-visual-parity"))
OUT.mkdir(parents=True, exist_ok=True)
COOKIE_JAR = http.cookiejar.CookieJar()
OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(COOKIE_JAR))


def api(path: str, method: str = "GET", body: dict[str, Any] | None = None) -> Any:
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(f"{BASE}{path}", data=data, method=method, headers={"Content-Type": "application/json"})
    with OPENER.open(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_server() -> None:
    deadline = time.time() + 45
    while time.time() < deadline:
        try:
            if api("/api/health").get("status") == "ok":
                return
        except Exception:
            time.sleep(0.5)
    raise RuntimeError("V26 server did not become ready")


def first_skill() -> tuple[str, str]:
    payload = api("/api/skills/map")
    cert = next(row for row in payload["certifications"] if row["id"] == "snowpro-core")
    domain = cert["domains"][0]
    return domain["id"], domain["skills"][0]["id"]


def set_theme(page: Page, theme: str) -> None:
    if page.locator("html").get_attribute("data-theme") != theme:
        page.locator("[data-theme-toggle]").click()
    page.wait_for_timeout(120)


def route(page: Page, hash_path: str, *, theme: str | None = None) -> None:
    page.goto(f"{BASE}/{hash_path}", wait_until="domcontentloaded")
    page.wait_for_selector("#view-root[data-route-ok='true']")
    page.wait_for_timeout(260)
    if theme:
        set_theme(page, theme)
    page.mouse.wheel(0, -100_000)
    page.wait_for_timeout(80)


def shot(page: Page, name: str, *, full_page: bool = True) -> None:
    page.screenshot(path=str(OUT / f"{name}.png"), full_page=full_page, animations="disabled")


def require(page: Page, selector: str, label: str) -> None:
    page.wait_for_selector(selector)
    if not page.locator(selector).count():
        raise AssertionError(f"Recording contract missing for {label}: {selector}")


def clear_active_mock() -> None:
    active = api("/api/mock/sessions/active?track_id=snowpro-core")
    session = active.get("session")
    if session:
        try:
            api(f"/api/mock/session-control/{session['session_id']}/cancel", "POST", {})
        except Exception:
            api(f"/api/mock/sessions/{session['session_id']}/submit", "POST", {"reason": "learner"})


def create_mock(mode: str = "weekly-mock") -> dict[str, Any]:
    clear_active_mock()
    return api("/api/mock/sessions", "POST", {"track_id": "snowpro-core", "mode": mode})


def browser_page(browser: Browser, width: int, height: int, *, authenticated: bool = True) -> tuple[BrowserContext, Page, list[str]]:
    context = browser.new_context(viewport={"width": width, "height": height}, reduced_motion="no-preference")
    if authenticated:
        context.add_cookies([{"name": cookie.name, "value": cookie.value, "url": BASE} for cookie in COOKIE_JAR])
    page = context.new_page()
    problems: list[str] = []
    page.on("console", lambda msg: problems.append(f"console {msg.type}: {msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda exc: problems.append(f"pageerror: {exc}"))
    return context, page, problems


def assert_no_browser_errors(problems: list[str], label: str) -> None:
    if problems:
        raise AssertionError(f"Browser errors during {label}: {problems}")


def guest_identity_pass(browser: Browser) -> None:
    context, page, problems = browser_page(browser, 1440, 1000, authenticated=False)
    page.add_init_script("localStorage.setItem('snowflake-certification.theme','light')")
    route(page, "#/home")
    page.locator(".v26-login-link[data-auth-intent='login']").click()
    require(page, ".v26-auth-modal", "guest sign in")
    shot(page, "00-light-google-sign-in")
    google = page.locator("[data-google-auth]")
    if not google.count() or "Continue with Google" not in google.inner_text():
        raise AssertionError("Continue with Google is missing from sign-in")
    page.locator(".v26-modal-close[data-auth-close]").click()
    page.wait_for_selector(".v26-auth-modal", state="detached")
    page.locator(".v26-signup-link[data-auth-intent='signup']").click()
    require(page, ".v26-auth-modal", "guest create account")
    shot(page, "00b-light-google-create-account")
    page.locator(".v26-modal-close[data-auth-close]").click()
    page.wait_for_selector(".v26-auth-modal", state="detached")
    route(page, "#/curriculum?track_id=snowpro-core")
    require(page, "#view-root[data-view-id='authentication-required']", "guest content boundary")
    if page.locator(".v26-curriculum-list,.v26-domain-task-rows,.v26-study-nav").count():
        raise AssertionError("Anonymous certification content rendered behind the candidate gate")
    shot(page, "00d-guest-content-login-gate")
    assert_no_browser_errors(problems, "guest identity pass")
    context.close()


def guest_mobile_identity_pass(browser: Browser) -> None:
    context, page, problems = browser_page(browser, 390, 844, authenticated=False)
    page.add_init_script("localStorage.setItem('snowflake-certification.theme','light')")
    route(page, "#/home")
    page.locator("[data-menu]").click()
    page.locator(".v26-mobile-auth[data-auth-intent='login']").click()
    require(page, ".v26-auth-modal", "mobile guest sign in")
    shot(page, "00c-mobile-google-sign-in")
    assert_no_browser_errors(problems, "guest mobile identity pass")
    context.close()


def recording_page_pass(page: Page, domain_id: str, skill_id: str) -> None:
    route(page, "#/curriculum?track_id=snowpro-core", theme="light")
    require(page, ".v26-curriculum-list", "Exam Domains overview")
    if page.locator(".v26-domain-block").count() != 5:
        raise AssertionError("Exam Domains must render five editorial syllabus rows")
    shot(page, "17-light-exam-domains")
    page.locator("[data-domain-toggle]").first.click()
    require(page, ".v26-domain-block [data-domain-tasks]:not([hidden])", "Expanded curriculum task rows")
    shot(page, "17a-light-exam-domains-expanded")

    route(page, f"#/domain?track_id=snowpro-core&domain_id={domain_id}", theme="light")
    require(page, ".v26-domain-task-rows", "Domain detail task statements")
    require(page, ".v26-side-tasks", "Expanded active-domain sidebar tasks")
    shot(page, "17b-light-domain-detail")

    route(page, f"#/skill?track_id=snowpro-core&skill_id={skill_id}", theme="light")
    require(page, ".v26-lesson-head", "Task lesson")
    require(page, ".v26-side-tasks", "Lesson active-domain sidebar")
    shot(page, "17c-light-task-lesson")

    route(page, "#/progress?track_id=snowpro-core", theme="light")
    require(page, ".v26-readiness-panel", "Progress readiness panel")
    require(page, ".v26-recording-domain-progress", "Progress domain list")
    shot(page, "17d-light-progress")

    route(page, "#/practice?track_id=snowpro-core&mode=drill", theme="light")
    require(page, ".v26-drill-stats", "Drill Mode setup stats")
    require(page, ".v26-domain-filter-chips", "Drill Mode domain filters")
    shot(page, "17e-light-drill-mode")

    route(page, "#/exercises?track_id=snowpro-core", theme="light")
    require(page, ".v26-exercise-domain-list", "Build Exercises grouped by domain")
    if page.locator(".v26-exercise-domain").count() != 5:
        raise AssertionError("Build Exercises must group content into five domains")
    shot(page, "17f-light-build-exercises")

    route(page, "#/practice?track_id=snowpro-core&mode=diagnostic", theme="light")
    require(page, ".v26-diagnostic-card", "Diagnostic Assessment setup")
    require(page, ".v26-diagnostic-domains", "Diagnostic domain coverage")
    shot(page, "17g-light-diagnostic")

    route(page, "#/quick-reference?track_id=snowpro-core", theme="light")
    require(page, ".v26-lookup-card-grid", "Quick Reference landing")
    if page.locator(".v26-lookup-card").count() != 5:
        raise AssertionError("Quick Reference must render five domain sheets")
    shot(page, "17h-light-quick-reference")

    route(page, "#/glossary?track_id=snowpro-core", theme="light")
    require(page, ".v26-lookup-card-grid", "Glossary landing")
    if page.locator(".v26-lookup-card").count() != 5:
        raise AssertionError("Glossary must render five domain cards")
    shot(page, "17i-light-glossary")

    route(page, "#/mock?track_id=snowpro-core", theme="light")
    require(page, ".v26-mock-facts", "Mock Exam facts")
    shot(page, "18-light-mock")

    route(page, "#/reference?track_id=snowpro-core", theme="light")
    require(page, ".v26-resource-grid", "Resources")
    shot(page, "19-light-reference")

    route(page, "#/journal?track_id=snowpro-core", theme="light")
    require(page, ".replica-journal-grid", "SnowPro Journal")
    shot(page, "19b-light-journal")


def desktop_pass(browser: Browser, domain_id: str, skill_id: str) -> int:
    context, page, problems = browser_page(browser, 1440, 1100)
    page.add_init_script("localStorage.setItem('snowflake-certification.theme','dark')")
    route(page, "#/home", theme="dark")
    require(page, "[data-globe-canvas]", "home globe")
    page.wait_for_timeout(700)
    shot(page, "01-dark-home")
    globe = page.locator("[data-globe]")
    box = globe.bounding_box()
    if box:
        page.mouse.move(box["x"] + box["width"] * 0.72, box["y"] + box["height"] * 0.5)
        page.mouse.down()
        page.mouse.move(box["x"] + box["width"] * 0.38, box["y"] + box["height"] * 0.42, steps=12)
        page.mouse.up()
        page.wait_for_timeout(180)
    shot(page, "02-dark-home-globe-rotated")
    route(page, "#/certifications", theme="dark"); shot(page, "03-dark-certifications")
    route(page, "#/curriculum?track_id=snowpro-core", theme="dark")
    require(page, ".v26-curriculum-list", "dark curriculum")
    shot(page, "04-dark-curriculum")
    page.locator("[data-domain-toggle]").first.click()
    require(page, ".v26-domain-block [data-domain-tasks]:not([hidden])", "dark expanded curriculum")
    shot(page, "04b-dark-curriculum-expanded")
    route(page, f"#/domain?track_id=snowpro-core&domain_id={domain_id}", theme="dark"); shot(page, "05-dark-domain-detail")
    route(page, f"#/skill?track_id=snowpro-core&skill_id={skill_id}", theme="dark"); shot(page, "06-dark-lesson")
    route(page, "#/practice?track_id=snowpro-core", theme="dark"); require(page, ".v26-due-strip", "practice due strip"); shot(page, "07-dark-practice")
    route(page, "#/reference?track_id=snowpro-core", theme="dark"); shot(page, "08-dark-reference")
    route(page, "#/journal?track_id=snowpro-core", theme="dark"); shot(page, "09-dark-journal")
    clear_active_mock()
    route(page, "#/mock?track_id=snowpro-core", theme="dark"); shot(page, "10-dark-mock-landing")
    route(page, "#/mock/start?track_id=snowpro-core&type=weekly-mock", theme="dark"); shot(page, "11-dark-mock-start")

    session = create_mock("weekly-mock")
    session_id = int(session["session_id"])
    # Force an SPA remount after the server-side session is created. Navigating to
    # the identical hash does not emit hashchange, so leave Mock Start and re-enter.
    route(page, "#/mock?track_id=snowpro-core", theme="dark")
    route(page, "#/mock/start?track_id=snowpro-core&type=weekly-mock", theme="dark")
    require(page, ".v26-interrupted-sitting", "interrupted sitting resume state")
    shot(page, "12-dark-interrupted-sitting")
    route(page, f"#/mock/session?session_id={session_id}", theme="dark")
    shot(page, "13-dark-exam-player")
    page.locator("input[name='answer']").first.check()
    page.wait_for_timeout(350)
    page.locator("[data-flag]").click()
    page.wait_for_timeout(250)
    shot(page, "14-dark-exam-answered-flagged")

    route(page, "#/home", theme="dark")
    page.locator("[data-feedback-open]").click()
    require(page, ".feedback-panel:not([hidden])", "feedback drawer")
    page.wait_for_timeout(220)
    shot(page, "15-dark-feedback-drawer")
    page.locator("[data-feedback-close]").click()
    route(page, "#/membership", theme="dark"); shot(page, "15b-dark-membership-account")
    route(page, "#/account", theme="dark"); require(page, ".v26-account-sessions", "account sessions"); shot(page, "15c-dark-account-sessions")
    route(page, "#/home", theme="light"); page.wait_for_timeout(500); shot(page, "16-light-home")
    recording_page_pass(page, domain_id, skill_id)
    route(page, "#/home", theme="light")
    page.locator("[data-feedback-open]").click(); require(page, ".feedback-panel:not([hidden])", "light feedback drawer"); page.wait_for_timeout(220); shot(page, "20-light-feedback-drawer")
    assert_no_browser_errors(problems, "desktop pass")
    context.close()
    return session_id


def mobile_pass(browser: Browser, session_id: int) -> None:
    context, page, problems = browser_page(browser, 390, 844)
    page.add_init_script("localStorage.setItem('snowflake-certification.theme','light')")
    route(page, "#/home", theme="light"); require(page, "[data-globe-canvas]", "mobile home"); page.wait_for_timeout(500); shot(page, "21-mobile-home")
    route(page, "#/curriculum?track_id=snowpro-core", theme="light"); require(page, ".v26-curriculum-list", "mobile curriculum"); shot(page, "22-mobile-curriculum")
    route(page, f"#/mock/session?session_id={session_id}", theme="light"); shot(page, "23-mobile-exam-player")
    page.locator("[data-open-nav]").click(); page.wait_for_timeout(160); shot(page, "24-mobile-exam-navigator")
    assert_no_browser_errors(problems, "mobile pass")
    context.close()


def write_manifest(domain_id: str, skill_id: str, session_id: int) -> None:
    manifest = {
        "base_url": BASE,
        "reference": "user-supplied 2026-08-14 authenticated-page screen recording plus candidate identity/membership security feature",
        "screenshots": sorted(path.name for path in OUT.glob("*.png")),
        "domain_id": domain_id,
        "skill_id": skill_id,
        "mock_session_id": session_id,
        "recording_contract_pages": ["Home", "Rotated Globe", "Certification Chooser", "Exam Domains", "Expanded Curriculum", "Domain Detail", "Task Lesson", "Progress", "Practice", "Drill Mode", "Build Exercises", "Diagnostic Assessment", "Quick Reference", "Glossary", "Mock Exam", "Mock Start", "Interrupted Sitting", "Exam Player", "Answered and Flagged Exam", "Feedback Drawer", "Resources", "SnowPro Journal", "Light Mode", "Mobile Home", "Mobile Curriculum", "Mobile Exam", "Mobile Navigator"],
        "identity": "Google sign-in is rendered in guest desktop/mobile states. CI uses disabled-provider mode because no production OAuth secret is stored in GitHub.",
        "content_boundary": "Guest browser contexts deep-link to curriculum and must render authentication-required without loading domain content. Study APIs require a valid candidate session.",
        "paid_access": "Membership and account/session states are rendered; paid activation remains server-authoritative and requires deployment billing credentials.",
        "activity_truthfulness": "No synthetic learner markers are injected. Live markers require privacy-safe aggregated activity from /api/activity/globe; otherwise the globe renders the truthful worldwide fallback.",
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def main() -> None:
    wait_server()
    suffix = uuid.uuid4().hex
    api("/api/auth/register", "POST", {"display_name": "Visual Parity Candidate", "email": f"visual-{suffix}@example.com", "password": f"visual-{suffix}"})
    domain_id, skill_id = first_skill()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        guest_identity_pass(browser)
        guest_mobile_identity_pass(browser)
        session_id = desktop_pass(browser, domain_id, skill_id)
        mobile_pass(browser, session_id)
        browser.close()
    write_manifest(domain_id, skill_id, session_id)
    print(f"V26 visual capture complete: {len(list(OUT.glob('*.png')))} screenshots -> {OUT}")


if __name__ == "__main__":
    main()
