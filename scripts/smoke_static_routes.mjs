#!/usr/bin/env node
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const router = fs.readFileSync(path.join(root, "frontend", "router.js"), "utf8");
const index = fs.readFileSync(path.join(root, "frontend", "index.html"), "utf8");
const required = ["command", "career", "academy", "intelligence", "video", "quiz", "labs", "readiness", "search", "flashcards", "analytics", "ai"];
const failures = [];

if (!router.includes('ASSET_VERSION = "20260714-v20-ai-academy"')) failures.push("router asset version is not v20 AI Academy");
if (!index.includes("20260714-v20-ai-academy")) failures.push("index.html does not reference v20 AI Academy assets");
if (/overhaulv8|recoveryv9/.test(router + index)) failures.push("stale v8/v9 asset version found in router/index");
if (!router.includes('"#/learn": () => import(`./views/video.js?v=${ASSET_VERSION}`)')) failures.push("Learn route must load video.js");
if (!router.includes('"#/practice": () => import(`./views/quiz.js?v=${ASSET_VERSION}`)')) failures.push("Practice route must load quiz.js");
if (!router.includes('"#/career": () => import(`./views/career.js?v=${ASSET_VERSION}`)')) failures.push("Career route must load career.js");
if (!router.includes('"#/academy": () => import(`./views/academy.js?v=${ASSET_VERSION}`)')) failures.push("Academy route must load academy.js");
const video = fs.readFileSync(path.join(root, "frontend", "views", "video.js"), "utf8");
const quiz = fs.readFileSync(path.join(root, "frontend", "views", "quiz.js"), "utf8");
if (!video.includes('VIEW_ID = "learn"')) failures.push("video.js must identify as learn view");
if (!video.includes("Watch the actual lessons") || !video.includes("video-stage")) failures.push("video.js no longer contains the real course player");
if (video.includes("Timed practice, source tests, and diagnostic evidence")) failures.push("video.js appears to contain Exam Studio content");
if (!quiz.includes('VIEW_ID = "practice"')) failures.push("quiz.js must identify as practice view");

for (const name of required) {
  const file = path.join(root, "frontend", "views", `${name}.js`);
  if (!fs.existsSync(file)) failures.push(`missing route view ${name}.js`);
  const body = fs.existsSync(file) ? fs.readFileSync(file, "utf8") : "";
  if (/overhaulv8|recoveryv9/.test(body)) failures.push(`stale asset import in ${name}.js`);
  if (!/export default async function mount|export default function mount/.test(body)) failures.push(`view ${name}.js lacks default mount export`);
}

if (failures.length) {
  console.error("Static route smoke failed:");
  failures.forEach((failure) => console.error(`- ${failure}`));
  process.exit(1);
}
console.log("Static route smoke passed.");
