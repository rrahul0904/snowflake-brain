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
  "#/drill",
  "#/mock",
  "#/exercises",
  "#/quick-reference",
  "#/glossary",
];

const directRoutes = [
  ["#/practice", "quiz.js", "practice"],
  ["#/labs", "labs.js", "labs"],
  ["#/reference", "reference.js", "reference"],
  ["#/journal", "journal.js", "journal"],
  ["#/article", "journal.js", "journal"],
];

const aliases = {
  "#/": "#/home",
  "#/command": "#/home",
  "#/today": "#/progress",
  "#/learn": "#/curriculum",
  "#/lessons": "#/curriculum",
  "#/lesson": "#/curriculum",
  "#/video": "#/curriculum",
  "#/quiz": "#/practice",
  "#/readiness": "#/progress",
  "#/search": "#/reference",
  "#/ai": "#/reference",
  "#/archive": "#/curriculum",
};

if (!router.includes(`const ASSET_VERSION = "${assetVersion}"`)) failures.push(`router asset version is not ${assetVersion}`);
if (!index.includes(`/static/app.js?v=${assetVersion}`)) failures.push("index.html does not load the v23 application entry point");
if (!index.includes(`/static/guide.css?v=${assetVersion}`)) failures.push("index.html does not load the v23 guide stylesheet");
if (!index.includes(`/static/guide-study.css?v=${assetVersion}`)) failures.push("index.html does not load task-study styles");
if (!app.includes(`./router.js?v=${assetVersion}`)) failures.push("app.js does not load the v23 router");
if (!app.includes('window.location.hash = "#/home"')) failures.push("app.js must boot new sessions into certification home");
if (!index.includes("<title>Snowflake Certification Guide</title>")) failures.push("index.html is missing the certification guide title");

if (!guide.includes('export const VIEW_ID = "certification-guide"')) failures.push("guide.js must identify as certification-guide");
if (!/export default async function mount|export default function mount/.test(guide)) failures.push("guide.js lacks a default mount export");
for (const fn of ["renderHome", "renderCurriculum", "renderProgress", "renderDomain", "renderSkill", "renderDiagnostic", "renderDrill", "renderMock", "renderExercises", "renderQuickReference", "renderGlossary"]) {
  if (!guide.includes(`function ${fn}`) && !guide.includes(`async function ${fn}`)) failures.push(`guide.js is missing ${fn}`);
}
for (const phrase of ["What You Need to Know", "Exam Traps", "Practice Scenario", "Build Exercise", "Mark Complete", "Next Lesson"]) {
  if (!guide.includes(phrase)) failures.push(`task lesson is missing ${phrase}`);
}
if (!guide.includes("/api/skills/task-progress")) failures.push("guide must persist task completion through the task-progress API");

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

for (const removed of ["frontend/views/lesson.js", "frontend/views/video.js", "frontend/views/curriculum.js"]) {
  if (fs.existsSync(path.join(root, removed))) failures.push(`${removed} should be removed from the video-free certification product`);
}
for (const item of ["Curriculum", "Practice", "Reference", "Blog"]) {
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

console.log("Static route smoke passed for video-free v23 Snowflake certification guide.");
