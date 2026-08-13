import { renderNav } from "./components/nav.js?v=20260812-v25-production-mock-r2";
import { renderTopbar, refreshTopbar } from "./components/topbar.js?v=20260812-v25-production-mock-r2";
import { route } from "./router.js?v=20260813-v25-production-mock-r7";

window.__SNOWFLAKE_BRAIN_CLIENT_ERRORS__ = [];
window.addEventListener("error", (event) => window.__SNOWFLAKE_BRAIN_CLIENT_ERRORS__.push(event.message || "Unknown client error"));
window.addEventListener("unhandledrejection", (event) => window.__SNOWFLAKE_BRAIN_CLIENT_ERRORS__.push(event.reason?.message || String(event.reason || "Unhandled promise rejection")));

async function boot() {
  await Promise.all([renderNav(), renderTopbar()]);
  window.addEventListener("hashchange", route);
  window.addEventListener("track-change", () => {
    refreshTopbar();
    route();
  });
  if (!window.location.hash) window.location.hash = "#/home";
  await route();
}

boot();
