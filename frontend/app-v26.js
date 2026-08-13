import { renderNav } from "./components/nav.js";
import { renderFeedback } from "./components/feedback.js";
import { route } from "./router-final.js";

window.__SNOWFLAKE_BRAIN_CLIENT_ERRORS__ = [];
window.addEventListener("error", (event) => window.__SNOWFLAKE_BRAIN_CLIENT_ERRORS__.push(event.message || "Unknown client error"));
window.addEventListener("unhandledrejection", (event) => window.__SNOWFLAKE_BRAIN_CLIENT_ERRORS__.push(event.reason?.message || String(event.reason || "Unhandled promise rejection")));

function applyTheme(theme) {
  const next = theme === "light" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  localStorage.setItem("snowflake-certification.theme", next);
}

async function handleRoute() {
  await route();
  await renderNav();
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
