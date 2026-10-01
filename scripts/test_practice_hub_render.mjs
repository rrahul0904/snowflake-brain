import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const source = await readFile(new URL("../frontend/views/practice-hub-v26.js", import.meta.url), "utf8");
const withControlledApi = source.replace(
  /^import \{ escapeHtml, getAdaptiveReadiness, getMockHistory, getSkillSummary \} from "\.\.\/api\.js";$/m,
  `const escapeHtml = (value) => String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#39;");
const getAdaptiveReadiness = async () => ({ readiness_score: 84, evidence: { recent_mock_count: 1 } });
const getMockHistory = async () => ({ history: [{ session_id: 731, mode: "exam_quick_mock", ready: true, scaled_score: 760 }] });
const getSkillSummary = async () => ({ skills: [{ task_code: "1.1", title: "Virtual Warehouse", attempts: 4, accuracy_pct: 75 }] });`
);
assert.notEqual(withControlledApi, source, "the API import seam must be replaced for the render test");
const moduleUrl = `data:text/javascript;base64,${Buffer.from(withControlledApi).toString("base64")}`;
const { default: render } = await import(moduleUrl);
const root = { innerHTML: "" };
await render(root, { track_id: "snowpro-core" });

assert.match(root.innerHTML, /<strong>84%<\/strong><span>Evidence readiness/);
assert.match(root.innerHTML, /760\/1000 · 76%/);
assert.match(root.innerHTML, /Review result/);
assert.match(root.innerHTML, /731/);
assert.doesNotMatch(root.innerHTML, /0\/0 · 0%/);
console.log("Practice Hub canonical readiness and mock-history rendering: PASS");
