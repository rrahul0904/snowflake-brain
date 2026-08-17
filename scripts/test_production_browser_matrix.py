#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
import traceback
from dataclasses import dataclass
from pathlib import Path

from playwright.sync_api import Browser, Page, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
BASE_URL = os.getenv("LAUNCH_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
REPORT_PATH = ROOT / "artifacts" / "browser-matrix-report.json"


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


def write_report(payload: dict) -> None:
    REPORT_PATH.parent.mkdir(exist_ok=True)
    REPORT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def wait_for_route(page: Page, route: str) -> None:
    page.wait_for_function(
        """expected => {
          const state = window.__SNOWFLAKE_BRAIN_ROUTE_STATUS__;
          return Boolean(state && state.status === 'ok' && state.route === expected);
        }""",
        arg=route,
        timeout=10_000,
    )


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


def assert_membership_layout(page: Page, profile: Profile) -> dict:
    cards = page.locator(".v26-membership-page .v26-plan-card")
    if cards.count() != 5:
        raise AssertionError(f"{profile.name} membership expected five plans, found {cards.count()}")

    metrics = page.evaluate(
        """() => {
          const first = document.querySelector('.v26-membership-page .v26-plan-card');
          const heading = first?.querySelector('h2');
          const feature = first?.querySelector('li');
          const root = document.documentElement;
          return {
            overflow: root.scrollWidth > window.innerWidth + 2,
            headingPx: heading ? parseFloat(getComputedStyle(heading).fontSize) : 0,
            featurePx: feature ? parseFloat(getComputedStyle(feature).fontSize) : 0,
          };
        }"""
    )
    if metrics["overflow"]:
        raise AssertionError(f"{profile.name} membership has horizontal overflow")
    if not 26 <= metrics["headingPx"] <= 34:
        raise AssertionError(f"{profile.name} membership plan heading scale regressed: {metrics['headingPx']}px")
    if metrics["featurePx"] < 12:
        raise AssertionError(f"{profile.name} membership feature text is too small: {metrics['featurePx']}px")
    return metrics


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

    try:
        started = time.perf_counter()
        page.goto(f"{BASE_URL}/#/home", wait_until="networkidle", timeout=20_000)
        wait_for_route(page, "#/home")
        load_ms = (time.perf_counter() - started) * 1000
        if load_ms > 8_000:
            raise AssertionError(f"{profile.name} public-home network-idle load exceeded 8s: {load_ms:.1f} ms")
        page.locator("h1").first.wait_for(state="visible", timeout=10_000)
        assert_accessible_baseline(page, f"{profile.name} home")
        assert_client_clean(page, f"{profile.name} home")

        # Public privacy page must remain independently navigable on every launch profile.
        page.goto(f"{BASE_URL}/#/privacy", wait_until="networkidle", timeout=20_000)
        wait_for_route(page, "#/privacy")
        page.get_by_role("heading", name="Your certification data stays under your control.").wait_for(
            state="visible", timeout=10_000
        )
        assert_accessible_baseline(page, f"{profile.name} privacy")
        assert_client_clean(page, f"{profile.name} privacy")

        # Membership is a public commercial surface and must not regress on desktop or mobile.
        page.goto(f"{BASE_URL}/#/membership", wait_until="networkidle", timeout=20_000)
        wait_for_route(page, "#/membership")
        page.locator(".v26-membership-page h1").wait_for(state="visible", timeout=10_000)
        if "Study freely" not in page.locator(".v26-membership-page h1").inner_text():
            raise AssertionError(f"{profile.name} membership headline did not render")
        membership_metrics = assert_membership_layout(page, profile)
        assert_accessible_baseline(page, f"{profile.name} membership")
        assert_client_clean(page, f"{profile.name} membership")

        # Account action links must be public and fail safely when incomplete.
        page.goto(f"{BASE_URL}/#/account-action", wait_until="networkidle", timeout=20_000)
        wait_for_route(page, "#/account-action")
        page.get_by_role("heading", name="Invalid or incomplete link").wait_for(state="visible", timeout=10_000)
        assert_accessible_baseline(page, f"{profile.name} account action")
        assert_client_clean(page, f"{profile.name} account action")

        register_candidate(page, profile.name.replace("-", ""))

        # Registration must visibly remain unverified in the normal account experience.
        page.goto(f"{BASE_URL}/#/account", wait_until="networkidle", timeout=20_000)
        wait_for_route(page, "#/account")
        page.get_by_text("Verification required", exact=True).wait_for(state="visible", timeout=10_000)
        page.get_by_text("Action required", exact=True).wait_for(state="visible", timeout=10_000)
        assert_accessible_baseline(page, f"{profile.name} account")
        assert_client_clean(page, f"{profile.name} account")

        page.goto(f"{BASE_URL}/#/adaptive?track_id=snowpro-core", wait_until="networkidle", timeout=20_000)
        wait_for_route(page, "#/adaptive")
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
        return {
            "profile": profile.name,
            "status": "pass",
            "home_load_ms": round(load_ms, 2),
            "membership_heading_px": membership_metrics["headingPx"],
            "membership_feature_px": membership_metrics["featurePx"],
        }
    finally:
        context.close()


def main() -> None:
    results: list[dict] = []
    try:
        with sync_playwright() as playwright:
            for profile in PROFILES:
                browser_type = getattr(playwright, profile.engine)
                browser = browser_type.launch(headless=True)
                try:
                    result = run_profile(browser, profile)
                    results.append(result)
                    print(
                        f"Browser profile PASS: {profile.name} "
                        f"({result['home_load_ms']} ms; membership heading {result['membership_heading_px']}px)",
                        flush=True,
                    )
                except Exception as exc:
                    failure = {
                        "profile": profile.name,
                        "engine": profile.engine,
                        "status": "failure",
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                        "traceback": traceback.format_exc(),
                    }
                    results.append(failure)
                    write_report({"status": "failure", "results": results})
                    print(f"Browser profile FAILURE: {profile.name}: {type(exc).__name__}: {exc}", flush=True)
                    raise
                finally:
                    browser.close()
        write_report({"status": "pass", "results": results})
        print("Production browser matrix: PASS")
        for item in results:
            print(
                f"- {item['profile']}: home network-idle {item['home_load_ms']} ms; "
                f"membership heading {item['membership_heading_px']} px; "
                f"feature text {item['membership_feature_px']} px"
            )
    except Exception:
        if not REPORT_PATH.exists():
            write_report({"status": "failure", "results": results, "traceback": traceback.format_exc()})
        raise


if __name__ == "__main__":
    main()
