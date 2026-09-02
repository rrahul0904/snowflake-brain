#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

BASE = os.environ.get("V26_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
OUT = Path(os.environ.get("V26_VISUAL_DIR", "artifacts/v26-visual-parity")) / "reverse-engineering-public"
OUT.mkdir(parents=True, exist_ok=True)

ROUTES = {
    "home": "#/home",
    "certifications": "#/certifications",
    "core-exam-guide": "#/exam-guide?track_id=snowpro-core",
    "data-engineer-exam-guide": "#/exam-guide?track_id=advanced-data-engineer",
    "architect-exam-guide": "#/exam-guide?track_id=advanced-architect",
    "content-integrity": "#/content-integrity",
    "membership": "#/membership",
    "pricing": "#/pricing",
    "about": "#/about",
    "terms": "#/terms",
    "privacy": "#/privacy",
}
VIEWPORTS = [(1440, 1000), (1024, 900), (768, 900), (390, 844)]
THEMES = ("light", "dark")


def wait_server() -> None:
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{BASE}/api/health", timeout=3) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(0.25)
    raise RuntimeError("server not ready")


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")


def page_metrics(page: Page) -> dict:
    return page.evaluate(
        """() => ({
          scrollWidth: document.documentElement.scrollWidth,
          clientWidth: document.documentElement.clientWidth,
          bodyScrollWidth: document.body?.scrollWidth || 0,
          viewId: document.querySelector('#view-root')?.dataset?.viewId || '',
          routeOk: document.querySelector('#view-root')?.dataset?.routeOk || '',
          url: location.href,
        })"""
    )


def diagnostic_failure(page: Page, *, width: int, height: int, theme: str, name: str, error: Exception) -> None:
    metrics = page_metrics(page)
    label = f"{width}x{height}-{theme}-{slug(name)}"
    failure_path = OUT / f"FAIL-{label}.png"
    try:
        page.screenshot(path=str(failure_path), full_page=True, animations="disabled")
    except Exception as screenshot_error:
        print(f"VISUAL_QA_FAILURE_SCREENSHOT_ERROR label={label} error={screenshot_error}", flush=True)
    print(
        "VISUAL_QA_FAILURE "
        f"route={name} viewport={width}x{height} theme={theme} "
        f"assertion={type(error).__name__}:{error} "
        f"scrollWidth={metrics.get('scrollWidth')} clientWidth={metrics.get('clientWidth')} "
        f"bodyScrollWidth={metrics.get('bodyScrollWidth')} viewId={metrics.get('viewId')} "
        f"routeOk={metrics.get('routeOk')} url={metrics.get('url')} "
        f"screenshot={failure_path}",
        flush=True,
    )


def assert_no_horizontal_overflow(page: Page, label: str) -> None:
    metrics = page_metrics(page)
    if metrics["scrollWidth"] > metrics["clientWidth"] + 2:
        raise AssertionError(
            f"horizontal overflow: {label} scrollWidth={metrics['scrollWidth']} clientWidth={metrics['clientWidth']}"
        )


def assert_route_contract(page: Page, name: str) -> None:
    page.wait_for_selector("#view-root[data-route-ok='true']")
    if name == "certifications":
        page.wait_for_selector(".v26-cert-fact-card")
        if page.locator(".v26-cert-fact-card").count() < 3:
            raise AssertionError("focused certification fact cards missing")
        if "Study guide coming soon" not in page.locator("#view-root").inner_text():
            raise AssertionError("certification/product availability separation missing")
    elif name.endswith("exam-guide"):
        page.wait_for_selector(".v26-exam-fact-grid")
        text = page.locator("#view-root").inner_text()
        if "Source verification:" not in text or "Official Snowflake page" not in text:
            raise AssertionError("exam guide provenance missing")
    elif name == "content-integrity":
        text = page.locator("#view-root").inner_text()
        for phrase in ("Original preparation", "no exam dumps", "not affiliated"):
            if phrase.lower() not in text.lower():
                raise AssertionError(f"content-integrity phrase missing: {phrase}")
    elif name in {"membership", "pricing"}:
        text = page.locator("#view-root").inner_text()
        if "Checkout is not enabled" not in text and "hosted checkout" not in text.lower():
            raise AssertionError("billing availability honesty copy missing")


def set_theme(page: Page, theme: str) -> None:
    page.evaluate("theme => window.__setSnowflakeTheme?.(theme)", theme)
    page.wait_for_timeout(80)
    actual = page.locator("html").get_attribute("data-theme")
    if actual != theme:
        raise AssertionError(f"theme did not apply: wanted {theme}, got {actual}")


def run_viewport(browser, width: int, height: int) -> int:
    context = browser.new_context(viewport={"width": width, "height": height}, reduced_motion="reduce")
    page = context.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda exc: errors.append(f"pageerror: {exc}"))
    page.on("console", lambda msg: errors.append(f"console {msg.type}: {msg.text}") if msg.type == "error" else None)
    shots = 0

    try:
        for theme in THEMES:
            for name, route in ROUTES.items():
                errors.clear()
                try:
                    page.goto(f"{BASE}/{route}", wait_until="domcontentloaded")
                    page.wait_for_selector("#view-root[data-route-ok='true']")
                    set_theme(page, theme)
                    page.wait_for_timeout(100)
                    assert_route_contract(page, name)
                    assert_no_horizontal_overflow(page, f"{width}x{height}-{theme}-{name}")
                    if errors:
                        raise AssertionError("browser errors: " + " | ".join(errors))
                    page.screenshot(
                        path=str(OUT / f"{width}x{height}-{theme}-{slug(name)}.png"),
                        full_page=True,
                        animations="disabled",
                    )
                    shots += 1
                except Exception as error:
                    diagnostic_failure(page, width=width, height=height, theme=theme, name=name, error=error)
                    raise

        page.goto(f"{BASE}/#/curriculum?track_id=snowpro-core", wait_until="domcontentloaded")
        page.wait_for_selector("#view-root[data-view-id='authentication-required']")
        if page.locator(".v26-study-nav,.v26-curriculum-list").count():
            raise AssertionError("anonymous study content rendered during public acceptance matrix")
        if errors:
            raise AssertionError("browser errors: " + " | ".join(errors))
        return shots
    finally:
        context.close()


def main() -> None:
    wait_server()
    total = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            for width, height in VIEWPORTS:
                total += run_viewport(browser, width, height)
        finally:
            browser.close()
    print(f"Reverse-engineering public visual acceptance: PASS screenshots={total}")


if __name__ == "__main__":
    main()
