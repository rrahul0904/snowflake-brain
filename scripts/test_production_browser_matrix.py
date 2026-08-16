#!/usr/bin/env python3
from __future__ import annotations

import os
import time
from dataclasses import dataclass

from playwright.sync_api import Browser, Page, sync_playwright


BASE_URL = os.getenv("LAUNCH_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


@dataclass(frozen=True)
class Profile:
    engine: str
    name: str
    viewport: dict[str, int]
    mobile: bool = False


PROFILES = [
    Profile("chromium", "chromium-desktop", {"width": 1440, "height": 1000}),
    Profile("firefox", "firefox-desktop", {"width": 1440, "height": 1000}),
    Profile("chromium", "chromium-mobile", {"width": 390, "height": 844}, True),
]


def assert_accessible_baseline(page: Page, label: str) -> None:
    issues = page.evaluate(
        """() => {
          const issues = [];
          const ids = [...document.querySelectorAll('[id]')].map(el => el.id).filter(Boolean);
          const dupes = ids.filter((id, i) => ids.indexOf(id) !== i);
          if (dupes.length) issues.push(`duplicate ids: ${[...new Set(dupes)].join(',')}`);
          document.querySelectorAll('img').forEach(img => { if (!img.hasAttribute('alt')) issues.push('image missing alt'); });
          document.querySelectorAll('button,a').forEach(el => {
            const name = (el.getAttribute('aria-label') || el.textContent || '').trim();
            if (!name) issues.push(`${el.tagName.toLowerCase()} missing accessible name`);
          });
          const h1 = document.querySelector('h1');
          if (!h1 || !h1.textContent.trim()) issues.push('missing h1');
          const main = document.querySelector('main');
          if (!main) issues.push('missing main landmark');
          return issues;
        }"""
    )
    if issues:
        raise AssertionError(f"Accessibility baseline failed for {label}: {issues}")


def assert_client_clean(page: Page, label: str) -> None:
    errors = page.evaluate("() => window.__SNOWFLAKE_BRAIN_CLIENT_ERRORS__ || []")
    if errors:
        raise AssertionError(f"Client errors for {label}: {errors}")


def register_candidate(page: Page, suffix: str) -> None:
    result = page.evaluate(
        """async ({suffix}) => {
          const response = await fetch('/api/auth/register', {
            method: 'POST',
            credentials: 'same-origin',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({
              display_name: 'Launch Browser Candidate',
              email: `launch-browser-${suffix}@example.com`,
              password: 'LaunchBrowserPassword!123'
            })
          });
          return {status: response.status, body: await response.json()};
        }""",
        {"suffix": suffix},
    )
    if result["status"] != 201 or result["body"].get("email_verified") is not False:
        raise AssertionError(f"Browser registration failed: {result}")


def run_profile(browser: Browser, profile: Profile) -> dict:
    context = browser.new_context(
        viewport=profile.viewport,
        is_mobile=profile.mobile,
        has_touch=profile.mobile,
    )
    page = context.new_page()
    console_errors: list[str] = []
    page.on("pageerror", lambda error: console_errors.append(str(error)))
    page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)

    started = time.perf_counter()
    page.goto(f"{BASE_URL}/#/home", wait_until="networkidle", timeout=20_000)
    load_ms = (time.perf_counter() - started) * 1000
    if load_ms > 8_000:
        raise AssertionError(f"{profile.name} public-home network-idle load exceeded 8s: {load_ms:.1f} ms")
    page.locator("h1").first.wait_for(state="visible", timeout=10_000)
    assert_accessible_baseline(page, f"{profile.name} home")
    assert_client_clean(page, f"{profile.name} home")

    page.goto(f"{BASE_URL}/#/privacy", wait_until="networkidle", timeout=20_000)
    if "Privacy" not in page.locator("body").inner_text():
        raise AssertionError(f"{profile.name} privacy route did not render")
    assert_accessible_baseline(page, f"{profile.name} privacy")

    register_candidate(page, profile.name.replace("-", ""))
    page.goto(f"{BASE_URL}/#/adaptive?track_id=snowpro-core", wait_until="networkidle", timeout=20_000)
    page.get_by_role("heading", name="What should you study next?").wait_for(state="visible", timeout=10_000)
    body = page.locator("body").inner_text().lower()
    if "not a probability" not in body:
        raise AssertionError(f"{profile.name} adaptive readiness disclaimer is missing")
    if "start 15-question adaptive session" not in body:
        raise AssertionError(f"{profile.name} adaptive practice entry point is missing")
    assert_accessible_baseline(page, f"{profile.name} adaptive")
    assert_client_clean(page, f"{profile.name} adaptive")

    if console_errors:
        raise AssertionError(f"Browser console errors for {profile.name}: {console_errors}")
    context.close()
    return {"profile": profile.name, "home_load_ms": round(load_ms, 2)}


def main() -> None:
    results = []
    with sync_playwright() as playwright:
        for profile in PROFILES:
            browser_type = getattr(playwright, profile.engine)
            browser = browser_type.launch(headless=True)
            try:
                results.append(run_profile(browser, profile))
            finally:
                browser.close()
    print("Production browser matrix: PASS")
    for item in results:
        print(f"- {item['profile']}: home network-idle {item['home_load_ms']} ms")


if __name__ == "__main__":
    main()
