import { showToast } from "./components/toast.js";
import { updateActiveNav } from "./components/nav.js";
import { errorPanel, skeleton } from "./ui.js";

const views = {
  "#/home": "home-v26.js",
  "#/certifications": "certifications.js",
  "#/curriculum": "curriculum-v26.js",
  "#/domain": "curriculum-v26.js",
  "#/skill": "lesson-v26.js",
  "#/progress": "progress-v26.js",
  "#/quick-reference": "lookup-v26.js",
  "#/glossary": "lookup-v26.js",
  "#/exercises": "exercises-v26.js",
  "#/practice": "practice-v26.js",
  "#/mock": "mock-landing.js",
  "#/mock/start": "mock-start-v26.js",
  "#/mock/session": "exam-session-v26.js",
  "#/mock/result": "exam-result-v26.js",
  "#/mock/history": "exam-result-v26.js",
  "#/reference": "reference.js",
  "#/journal": "journal.js",
  "#/article": "journal.js",
  "#/labs": "labs.js",
  "#/about": "info-v26.js",
  "#/changelog": "info-v26.js",
  "#/privacy": "info-v26.js"
};

let currentView = null;

function resolve(path, query) {
  const params = new URLSearchParams(query);
  if (path === "#/" ) path = "#/home";
  if (path === "#/learn") path = "#/curriculum";
  if (path === "#/readiness") path = "#/progress";
  if (path === "#/quiz") path = "#/practice";
  if (path === "#/diagnostic") { path = "#/practice"; params.set("mode", "diagnostic"); }
  if (path === "#/drill" || path === "#/review") { path = "#/practice"; params.set("mode", "drill"); }
  return { path, params };
}

export async function route() {
  const root = document.querySelector("#view-root");
  const [rawPath, query = ""] = (window.location.hash || "#/home").split("?");
  const { path, params } = resolve(rawPath, query);
  const file = views[path];
  if (!file) { window.history.replaceState(null, "", "#/home"); return route(); }
  document.body.classList.remove("player-mode", "quiz-active", "replica-exam-active", "mock-player-active", "v26-exam-active", "v26-exam-nav-open");
  currentView?.unmount?.();
  root.innerHTML = skeleton("Loading certification guide...");
  updateActiveNav();
  try {
    currentView = await import(`./views/${file}`);
    await currentView.default(root, Object.fromEntries(params));
    root.dataset.routeOk = "true";
    root.dataset.routePath = path;
    root.dataset.viewId = currentView.VIEW_ID || "unknown";
    window.__SNOWFLAKE_BRAIN_ROUTE_STATUS__ = { status: "ok", route: path, view_id: currentView.VIEW_ID || "unknown", error: null };
    window.scrollTo({ top: 0, behavior: "instant" });
    window.dispatchEvent(new CustomEvent("v26-route-complete", { detail: { path } }));
  } catch (error) {
    root.dataset.routeOk = "false";
    root.innerHTML = errorPanel(error);
    showToast(error.message || "View failed to load", "error");
    window.__SNOWFLAKE_BRAIN_ROUTE_STATUS__ = { status: "error", route: path, error: error.message || String(error) };
  }
}
