#!/usr/bin/env node
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const router = fs.readFileSync(path.join(root, "frontend", "router.js"), "utf8");
const index = fs.readFileSync(path.join(root, "frontend", "index.html"), "utf8");
const app = fs.readFileSync(path.join(root, "frontend", "app.js"), "utf8");
const nav = fs.readFileSync(path.join(root, "frontend", "components", "nav.js"), "utf8");
const api = fs.readFileSync(path.join(root, "frontend", "api.js"), "utf8");
const guide = fs.readFileSync(path.join(root, "frontend", "views", "guide.js"), "utf8");
const failures = [];
const assetVersion = "20260812-v23-cert-guide";

const guideRoutes = [
  "#/home",
  "#/curriculum",
  "#/progress",
  "#/domain",
  "#/skill",
  "#/diagnostic",
  "#/exercises",
  "#/quick-reference",
  "#/glossary",
];

const directRoutes = [
  ["#/archive", "curriculum.js", "curriculum"],
  ["#/lesson", "lesson.js", "lesson"],
  ["#/practice", "quiz.js", "practice"],
  ["#/reference", "reference.js", "reference"],
  ["#/journal", "journal.js", "journal"],
  ["#/article", "journal.js", "journal"],
];

const aliases = {
  "#/": "#/home",
  "#/command": "#/home",
  "#/today": "#/progress",
  "#/learn": "#/curriculum",
  "#/lessons": "#/archive",
  "#/video": "#/lesson",
  "#/quiz": "#/practice",
  "#/labs": "#/exercises",
  "#/readiness": "#/progress",
  "#/search": "#/reference",
  "#/ai": "#/reference",
};

if (!router.includes(`const ASSET_VERSION = "${assetVersion}"`)) failures.push(`router asset version is not ${assetVersion}`);
if (!index.includes(`/static/app.js?v=${assetVersion}`)) failures.push("index.html does not load the v23 application entry point");
if (!index.includes(`/static/guide.css?v=${assetVersion}`)) failures.push("index.html does not load the v23 guide stylesheet");
if (!app.includes(`./router.js?v=${assetVersion}`)) failures.push("app.js does not load the v23 router");
if (!app.includes('window.location.hash = "#/home"')) failures.push("app.js must boot new sessions into the certification home");
if (!index.includes("<title>Snowflake Certification Studio</title>")) failures.push("index.html is missing the product title");

if (!guide.includes('export const VIEW_ID = "certification-guide"')) failures.push("guide.js must identify as certification-guide");
if (!/export default async function mount|export default function mount/.test(guide)) failures.push("guide.js lacks a default mount export");
for (const fn of ["renderHome", "renderCurriculum", "renderProgress", "renderDomain", "renderSkill", "renderDiagnostic", "renderExercises", "renderQuickReference", "renderGlossary"]) {
  if (!guide.includes(`function ${fn}`) && !guide.includes(`async function ${fn}`)) failures.push(`guide.js is missing ${fn}`);
}

for (const route of guideRoutes) {
  if (!router.includes(`"${route}": guide`)) failures.push(`${route} must load the certification guide module`);
}

for (const [route, moduleName, viewId] of directRoutes) {
  const expected = `"${route}": () => import(\`./views/${moduleName}?v=\${ASSET_VERSION}\`)`;
  if (!router.includes(expected)) failures.push(`${route} must load ${moduleName}`);
  const file = path.join(root, "frontend", "views", moduleName);
  if (!fs.existsSync(file)) {
    failures.push(`missing routed view ${moduleName}`);
    continue;
  }
  const body = fs.readFileSync(file, "utf8");
  if (!body.includes(`export const VIEW_ID = "${viewId}"`)) failures.push(`${moduleName} must identify as ${viewId}`);
}

for (const [legacyRoute, targetRoute] of Object.entries(aliases)) {
  if (!router.includes(`"${legacyRoute}": "${targetRoute}"`)) failures.push(`legacy alias ${legacyRoute} must resolve to ${targetRoute}`);
}

for (const item of ["Curriculum", "Practice", "Reference", "Journal", "Progress"]) {
  if (!nav.includes(`"${item}"`)) failures.push(`navigation is missing ${item}`);
}
if (!nav.includes('href="#/home"')) failures.push("brand must link to certification home");
if (!api.includes("/api/intelligence/evidence-audit")) failures.push("frontend API must expose evidence audit for readiness confidence");
if (!router.includes('routes["#/home"]')) failures.push("unknown routes must fall back to certification home");
if (!router.includes("window.__SNOWFLAKE_BRAIN_ROUTE_STATUS__")) failures.push("router must expose route health status for browser smoke tests");

if (failures.length) {
  console.error("Static route smoke failed:");
  failures.forEach((failure) => console.error(`- ${failure}`));
  process.exit(1);
}

console.log("Static route smoke passed for v23 Snowflake certification guide.");
