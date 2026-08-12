#!/usr/bin/env node
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const router = fs.readFileSync(path.join(root, "frontend", "router.js"), "utf8");
const index = fs.readFileSync(path.join(root, "frontend", "index.html"), "utf8");
const app = fs.readFileSync(path.join(root, "frontend", "app.js"), "utf8");
const failures = [];
const assetVersion = "20260731-v21-editorial-replica";

const routes = [
  ["#/curriculum", "curriculum.js", "curriculum"],
  ["#/lesson", "lesson.js", "lesson"],
  ["#/practice", "quiz.js", "practice"],
  ["#/reference", "reference.js", "reference"],
  ["#/journal", "journal.js", "journal"],
  ["#/article", "journal.js", "journal"],
];

const aliases = {
  "#/": "#/curriculum",
  "#/command": "#/curriculum",
  "#/today": "#/curriculum",
  "#/academy": "#/curriculum",
  "#/intelligence": "#/curriculum",
  "#/learn": "#/lesson",
  "#/video": "#/lesson",
  "#/quiz": "#/practice",
  "#/readiness": "#/practice",
  "#/career": "#/journal",
  "#/search": "#/reference",
  "#/ai": "#/reference",
};

if (!router.includes(`const ASSET_VERSION = "${assetVersion}"`)) {
  failures.push(`router asset version is not ${assetVersion}`);
}
if (!index.includes(`/static/app.js?v=${assetVersion}`)) {
  failures.push("index.html does not load the v21 application entry point");
}
if (!index.includes(`/static/replica.css?v=${assetVersion}`)) {
  failures.push("index.html does not load the v21 editorial stylesheet");
}
if (!app.includes(`./router.js?v=${assetVersion}`)) {
  failures.push("app.js does not load the v21 router");
}
if (!index.includes("<title>Snowflake Certification Studio</title>")) {
  failures.push("index.html is missing the current product title");
}

for (const [route, moduleName, viewId] of routes) {
  const expected = `"${route}": () => import(\`./views/${moduleName}?v=\${ASSET_VERSION}\`)`;
  if (!router.includes(expected)) {
    failures.push(`${route} must load ${moduleName}`);
  }

  const file = path.join(root, "frontend", "views", moduleName);
  if (!fs.existsSync(file)) {
    failures.push(`missing routed view ${moduleName}`);
    continue;
  }
  const body = fs.readFileSync(file, "utf8");
  if (!body.includes(`export const VIEW_ID = "${viewId}"`)) {
    failures.push(`${moduleName} must identify as ${viewId}`);
  }
  if (!/export default async function mount|export default function mount/.test(body)) {
    failures.push(`${moduleName} lacks a default mount export`);
  }
}

for (const [legacyRoute, targetRoute] of Object.entries(aliases)) {
  if (!router.includes(`"${legacyRoute}": "${targetRoute}"`)) {
    failures.push(`legacy alias ${legacyRoute} must resolve to ${targetRoute}`);
  }
}

if (!router.includes('routes["#/curriculum"]')) {
  failures.push("unknown routes must fall back to curriculum");
}
if (!router.includes("window.__SNOWFLAKE_BRAIN_ROUTE_STATUS__")) {
  failures.push("router must expose route health status for browser smoke tests");
}

if (failures.length) {
  console.error("Static route smoke failed:");
  failures.forEach((failure) => console.error(`- ${failure}`));
  process.exit(1);
}

console.log("Static route smoke passed for v21 editorial workspace.");
