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
    request = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
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
    skill = domain["skills"][0]
    return domain["id"], skill["id"]


def set_theme(page: Page, theme: str) -> None:
    if page.locator("html").get_attribute("data-theme") != theme:
        page.locator("[data-theme-toggle]").click()
    page.wait_for_timeout(120)


def route(page: Page, hash_path: str, *, theme: str | None = None) -> None:
    page.goto(f"{BASE}/{hash_path}", wait_until="domcontentloaded")
    page.wait_for_selector("#view-root[data-route-ok='true']")
    page.wait_for_timeout(250)
    if theme:
        set_theme(page, theme)
    page.mouse.wheel(0, -100_000)
    page.wait_for_timeout(80)


def shot(page: Page, name: str, *, full_page: bool = True) -> None:
    page.screenshot(path=str(OUT / f"{name}.png"), full_page=full_page, animations="disabled")


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
    page.add_init_script("localStorage.setItem('snowflake-certification.theme','dark')")
    route(page, "#/home")
    page.locator(".v26-login-link[data-auth-intent='login']").click()
    page.wait_for_selector(".v26-auth-modal")
    page.wait_for_timeout(350)
    shot(page, "00-dark-google-sign-in")
    check_google = page.locator("[data-google-auth]")
    if not check_google.count() or "Continue with Google" not in check_google.inner_text():
        raise AssertionError("Continue with Google is missing from sign-in")
    page.locator(".v26-modal-close[data-auth-close]").click()
    page.wait_for_selector(".v26-auth-modal", state="detached")
    page.locator(".v26-signup-link[data-auth-intent='signup']").click()
    page.wait_for_selector(".v26-auth-modal")
    page.wait_for_timeout(200)
    shot(page, "00b-dark-google-create-account")
    page.locator(".v26-modal-close[data-auth-close]").click()
    page.wait_for_selector(".v26-auth-modal", state="detached")

    # Deep-linking to study content without a session must render only the access
    # gate. The protected view module is not imported or mounted.
    route(page, "#/curriculum?track_id=snowpro-core")
    page.wait_for_selector("#view-root[data-view-id='authentication-required']")
    if page.locator("[data-domain-toggle]").count():
        raise AssertionError("Anonymous curriculum content rendered behind the candidate gate")
    shot(page, "00d-guest-content-login-gate")

    assert_no_browser_errors(problems, "guest identity pass")
    context.close()


def guest_mobile_identity_pass(browser: Browser) -> None:
    context, page, problems = browser_page(browser, 390, 844, authenticated=False)
    page.add_init_script("localStorage.setItem('snowflake-certification.theme','dark')")
    route(page, "#/home")
    page.locator("[data-menu]").click()
    page.locator(".v26-mobile-auth[data-auth-intent='login']").click()
    page.wait_for_selector(".v26-auth-modal")
    page.wait_for_timeout(200)
    shot(page, "00c-mobile-google-sign-in")
    assert_no_browser_errors(problems, "guest mobile identity pass")
    context.close()


def desktop_pass(browser: Browser, domain_id: str, skill_id: str) -> int:
    context, page, problems = browser_page(browser, 1440, 1100)
    page.add_init_script("localStorage.setItem('snowflake-certification.theme','dark')")

    route(page, "#/home")
    page.wait_for_selector("[data-globe-canvas]")
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

    route(page, "#/certifications")
    shot(page, "03-dark-certifications")

    route(page, "#/curriculum?track_id=snowpro-core")
    shot(page, "04-dark-curriculum")
    toggle = page.locator("[data-domain-toggle]").first
    if toggle.count() and toggle.get_attribute("aria-expanded") == "false":
        toggle.click()
    shot(page, "05-dark-curriculum-expanded")

    route(page, f"#/skill?track_id=snowpro-core&skill_id={skill_id}")
    shot(page, "06-dark-lesson")

    route(page, "#/practice?track_id=snowpro-core")
    shot(page, "07-dark-practice")

    route(page, "#/reference?track_id=snowpro-core")
    shot(page, "08-dark-reference")

    route(page, "#/journal?track_id=snowpro-core")
    shot(page, "09-dark-journal")

    clear_active_mock()
    route(page, "#/mock?track_id=snowpro-core")
    shot(page, "10-dark-mock-landing")

    route(page, "#/mock/start?track_id=snowpro-core&type=full-mock")
    shot(page, "11-dark-mock-start")

    session = create_mock("weekly-mock")
    session_id = int(session["session_id"])
    route(page, "#/mock/start?track_id=snowpro-core&type=quick-mock")
    page.wait_for_selector(".v26-interrupted-sitting")
    shot(page, "12-dark-interrupted-sitting")

    route(page, f"#/mock/session?session_id={session_id}")
    shot(page, "13-dark-exam-player")
    first_answer = page.locator("input[name='answer']").first
    first_answer.check()
    page.wait_for_timeout(350)
    page.locator("[data-flag]").click()
    page.wait_for_timeout(250)
    shot(page, "14-dark-exam-answered-flagged")

    route(page, "#/home")
    page.locator("[data-feedback-open]").click()
    page.wait_for_selector(".feedback-panel:not([hidden])")
    page.wait_for_timeout(220)
    shot(page, "15-dark-feedback-drawer")
    page.locator("[data-feedback-close]").click()

    route(page, "#/membership")
    shot(page, "15b-dark-membership-account")

    route(page, "#/account")
    page.wait_for_selector(".v26-account-sessions")
    shot(page, "15c-dark-account-sessions")

    set_theme(page, "light")
    route(page, "#/home", theme="light")
    page.wait_for_timeout(500)
    shot(page, "16-light-home")

    route(page, "#/curriculum?track_id=snowpro-core", theme="light")
    shot(page, "17-light-curriculum")

    route(page, "#/mock?track_id=snowpro-core", theme="light")
    shot(page, "18-light-mock")

    route(page, "#/reference?track_id=snowpro-core", theme="light")
    shot(page, "19-light-reference")

    route(page, "#/home", theme="light")
    page.locator("[data-feedback-open]").click()
    page.wait_for_selector(".feedback-panel:not([hidden])")
    page.wait_for_timeout(220)
    shot(page, "20-light-feedback-drawer")

    assert_no_browser_errors(problems, "desktop pass")
    context.close()
    return session_id


def mobile_pass(browser: Browser, session_id: int) -> None:
    context, page, problems = browser_page(browser, 390, 844)
    page.add_init_script("localStorage.setItem('snowflake-certification.theme','dark')")

    route(page, "#/home")
    page.wait_for_selector("[data-globe-canvas]")
    page.wait_for_timeout(500)
    shot(page, "21-mobile-home")

    route(page, "#/curriculum?track_id=snowpro-core")
    shot(page, "22-mobile-curriculum")

    route(page, f"#/mock/session?session_id={session_id}")
    shot(page, "23-mobile-exam-player")
    page.locator("[data-open-nav]").click()
    page.wait_for_timeout(160)
    shot(page, "24-mobile-exam-navigator")

    assert_no_browser_errors(problems, "mobile pass")
    context.close()


def write_manifest(domain_id: str, skill_id: str, session_id: int) -> None:
    manifest = {
        "base_url": BASE,
        "reference": "user-supplied screen recording plus candidate identity/membership security feature",
        "screenshots": sorted(path.name for path in OUT.glob("*.png")),
        "domain_id": domain_id,
        "skill_id": skill_id,
        "mock_session_id": session_id,
        "identity": "Google sign-in is rendered in guest desktop/mobile states. CI uses disabled-provider mode because no production OAuth secret is stored in GitHub.",
        "content_boundary": "Guest browser contexts deep-link to curriculum and must render authentication-required without loading domain content. Study APIs require a valid candidate session.",
        "paid_access": "Membership and account/session states are rendered; paid activation remains server-authoritative and requires deployment billing credentials.",
        "activity_truthfulness": "No synthetic learner markers are injected. Live markers require privacy-safe aggregated activity from /api/activity/globe; otherwise the globe renders the truthful worldwide fallback.",
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def main() -> None:
    wait_server()
    suffix = uuid.uuid4().hex
    # Create the isolated CI candidate before requesting any certification
    # metadata. Guest browser contexts below intentionally do not receive this
    # cookie and therefore still prove the anonymous boundary.
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
