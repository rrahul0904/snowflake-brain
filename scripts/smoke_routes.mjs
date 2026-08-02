#!/usr/bin/env node
/*
Route-level browser smoke test for Snowflake Brain.

Usage after the Docker app is running:
  npm i -D playwright
  npx playwright install chromium
  SNOWFLAKE_BRAIN_BASE_URL=http://localhost:8010 node scripts/smoke_routes.mjs

The app router writes window.__SNOWFLAKE_BRAIN_ROUTE_STATUS__ after every route render.
This test fails on blank pages, thrown route errors, and stale "View failed to load" panels.
*/

const routes = [
  "#/command",
  "#/intelligence",
  "#/learn",
  "#/practice",
  "#/labs",
  "#/readiness",
  "#/search",
  "#/flashcards",
  "#/review",
  "#/ai",
];

const baseUrl = process.env.SNOWFLAKE_BRAIN_BASE_URL || "http://localhost:8010";

const routeExpectations = {
  "#/learn": ["Watch the actual lessons", "Course outline"],
  "#/practice": ["Timed practice, source tests", "Downloaded source tests"],
  "#/labs": ["Lab", "SQL"],
};

async function loadPlaywright() {
  try {
    return await import("playwright");
  } catch (error) {
    console.error("Playwright is required for browser route smoke tests.");
    console.error("Install once with: npm i -D playwright && npx playwright install chromium");
    process.exit(2);
  }
}

function routeUrl(route) {
  return `${baseUrl}/${route}`;
}

const { chromium } = await loadPlaywright();
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 950 } });
const failures = [];

for (const route of routes) {
  const url = routeUrl(route);
  try {
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: 30000 });
    await page.waitForFunction(() => window.__SNOWFLAKE_BRAIN_ROUTE_STATUS__?.status !== "loading", null, { timeout: 30000 });
    const status = await page.evaluate(() => window.__SNOWFLAKE_BRAIN_ROUTE_STATUS__ || {});
    const textLength = await page.locator("#view-root").evaluate((node) => (node.innerText || "").trim().length);
    const failedPanel = await page.locator("text=View failed to load").count();
    if (status.status !== "ok") throw new Error(status.error || "route status not ok");
    if (textLength < 25) throw new Error(`route rendered too little text (${textLength})`);
    if (failedPanel) throw new Error("route displayed failure panel");
    const bodyText = await page.locator("#view-root").evaluate((node) => node.innerText || "");
    for (const expectedText of routeExpectations[route] || []) {
      if (!bodyText.includes(expectedText)) throw new Error(`route missing expected text: ${expectedText}`);
    }
    console.log(`OK ${route} (${textLength} chars)`);
  } catch (error) {
    failures.push(`${route}: ${error.message}`);
    console.error(`FAIL ${route}: ${error.message}`);
  }
}

await browser.close();

if (failures.length) {
  console.error("\nRoute smoke failures:");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}
