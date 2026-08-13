import { renderNav } from "./components/nav.js";
import { renderFeedback } from "./components/feedback.js";
import { activeTrack } from "./ui.js";
import { route } from "./router-final.js";

window.__SNOWFLAKE_BRAIN_CLIENT_ERRORS__ = [];
window.addEventListener("error", (event) => window.__SNOWFLAKE_BRAIN_CLIENT_ERRORS__.push(event.message || "Unknown client error"));
window.addEventListener("unhandledrejection", (event) => window.__SNOWFLAKE_BRAIN_CLIENT_ERRORS__.push(event.reason?.message || String(event.reason || "Unhandled promise rejection")));

function applyTheme(theme) {
  const next = theme === "light" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  localStorage.setItem("snowflake-certification.theme", next);
}

function renderFooter() {
  const path = (window.location.hash || "#/home").split("?")[0];
  let footer = document.querySelector("#v26-footer");
  if (!footer) { footer = document.createElement("footer"); footer.id = "v26-footer"; document.body.appendChild(footer); }
  if (path === "#/mock/session") { footer.hidden = true; return; }
  footer.hidden = false;
  const track = encodeURIComponent(activeTrack());
  footer.innerHTML = `<div class="v26-footer-inner"><div class="v26-footer-brand"><strong>Snowflake Certified</strong><p>Blueprint-first SnowPro preparation with written lessons, deliberate practice, and timed mock exams.</p><small>Independent certification-prep software.</small></div><nav><div><span>Curriculum</span><a href="#/curriculum?track_id=${track}">Exam Domains</a><a href="#/progress?track_id=${track}">Progress</a><a href="#/exercises?track_id=${track}">Build Exercises</a></div><div><span>Practice</span><a href="#/practice?track_id=${track}&mode=diagnostic">Diagnostic</a><a href="#/practice?track_id=${track}&mode=drill">Drill</a><a href="#/mock?track_id=${track}">Mock Exam</a></div><div><span>Reference</span><a href="#/quick-reference?track_id=${track}">Quick Reference</a><a href="#/glossary?track_id=${track}">Glossary</a><a href="#/reference?track_id=${track}">Resources</a></div><div><span>About</span><a href="#/about">About</a><a href="#/changelog">Changelog</a><a href="#/privacy">Privacy</a><a href="#/journal?track_id=${track}">Journal</a></div></nav></div>`;
}

async function handleRoute() {
  await route();
  await renderNav();
  renderFooter();
}

window.__setSnowflakeTheme = applyTheme;
applyTheme(localStorage.getItem("snowflake-certification.theme") || "dark");

async function boot() {
  await renderNav();
  renderFeedback();
  window.addEventListener("hashchange", handleRoute);
  window.addEventListener("track-change", handleRoute);
  window.addEventListener("theme-toggle", (event) => applyTheme(event.detail?.theme));
  if (!window.location.hash) window.location.hash = "#/home";
  await handleRoute();
}

boot();
