import { renderNav } from "./components/nav.js";
import { renderFeedback } from "./components/feedback.js";
import { renderHomeExtras } from "./components/home-extras.js";
import { enhanceStudyLayout } from "./components/study-sidebar.js";
import { activeTrack } from "./ui.js";
import { route } from "./router.js";

window.__SNOWFLAKE_BRAIN_CLIENT_ERRORS__ = [];
window.addEventListener("error", (event) => window.__SNOWFLAKE_BRAIN_CLIENT_ERRORS__.push(event.message || "Unknown client error"));
window.addEventListener("unhandledrejection", (event) => window.__SNOWFLAKE_BRAIN_CLIENT_ERRORS__.push(event.reason?.message || String(event.reason || "Unhandled promise rejection")));

function applyTheme(theme) {
  const next = theme === "light" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  localStorage.setItem("snowflake-certification.theme", next);
}

function ensureV26Styles() {
  if (document.querySelector('link[data-v26-study]')) return;
  const link = document.createElement("link");
  link.rel = "stylesheet";
  link.href = "/static/v26-study.css?v=20260813-v26-recording-r1";
  link.dataset.v26Study = "true";
  document.head.appendChild(link);
}

async function handleRoute() {
  await route();
  const path = (window.location.hash || "#/home").split("?")[0];
  const root = document.querySelector("#view-root");
  if (path === "#/home" && !root.querySelector(".v26-home-extras")) renderHomeExtras(root, activeTrack());
  if (["#/curriculum", "#/progress", "#/domain", "#/skill", "#/quick-reference", "#/glossary", "#/exercises"].includes(path)) await enhanceStudyLayout(root);
}

window.__setSnowflakeTheme = applyTheme;
applyTheme(localStorage.getItem("snowflake-certification.theme") || "dark");
ensureV26Styles();

async function boot() {
  await renderNav();
  renderFeedback();
  window.addEventListener("hashchange", handleRoute);
  window.addEventListener("track-change", async () => { await renderNav(); await handleRoute(); });
  window.addEventListener("theme-toggle", (event) => applyTheme(event.detail?.theme));
  if (!window.location.hash) window.location.hash = "#/home";
  await handleRoute();
}

boot();
