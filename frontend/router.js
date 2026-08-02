import { showToast } from "./components/toast.js?v=20260731-v21-editorial-replica";
import { updateActiveNav } from "./components/nav.js?v=20260731-v21-editorial-replica";
import { errorPanel, skeleton } from "./ui.js?v=20260731-v21-editorial-replica";

const ASSET_VERSION = "20260731-v21-editorial-replica";

const routes = {
  "#/curriculum": () => import(`./views/curriculum.js?v=${ASSET_VERSION}`),
  "#/lesson": () => import(`./views/lesson.js?v=${ASSET_VERSION}`),
  "#/practice": () => import(`./views/quiz.js?v=${ASSET_VERSION}`),
  "#/reference": () => import(`./views/reference.js?v=${ASSET_VERSION}`),
  "#/journal": () => import(`./views/journal.js?v=${ASSET_VERSION}`),
  "#/article": () => import(`./views/journal.js?v=${ASSET_VERSION}`),
};

const aliases = {
  "#/": "#/curriculum",
  "#/command": "#/curriculum",
  "#/today": "#/curriculum",
  "#/setup": "#/curriculum",
  "#/academy": "#/curriculum",
  "#/intelligence": "#/curriculum",
  "#/learn": "#/lesson",
  "#/lessons": "#/curriculum",
  "#/video": "#/lesson",
  "#/quiz": "#/practice",
  "#/labs": "#/reference",
  "#/readiness": "#/practice",
  "#/career": "#/journal",
  "#/search": "#/reference",
  "#/flashcards": "#/curriculum",
  "#/review": "#/practice",
  "#/analytics": "#/practice",
  "#/ai": "#/reference",
};

let currentView = null;

export async function route() {
  const root = document.querySelector("#view-root");
  const hash = window.location.hash || "#/curriculum";
  const [rawPath, query = ""] = hash.split("?");
  const path = aliases[rawPath] || rawPath;
  const loader = routes[path] || routes["#/curriculum"];
  window.__SNOWFLAKE_BRAIN_ROUTE_STATUS__ = { status: "loading", route: path, error: null };
  document.body.classList.remove("player-mode", "quiz-active", "replica-exam-active");
  if (currentView?.unmount) currentView.unmount();
  root.innerHTML = skeleton("Loading...");
  updateActiveNav();
  try {
    currentView = await loader();
    await currentView.default(root, Object.fromEntries(new URLSearchParams(query)));
    root.dataset.routeOk = "true";
    root.dataset.routePath = path;
    root.dataset.viewId = currentView.VIEW_ID || "unknown";
    window.__SNOWFLAKE_BRAIN_ROUTE_STATUS__ = { status: "ok", route: path, view_id: currentView.VIEW_ID || "unknown", error: null };
    root.scrollTop = 0;
  } catch (error) {
    root.dataset.routeOk = "false";
    window.__SNOWFLAKE_BRAIN_ROUTE_STATUS__ = { status: "error", route: path, error: error.message || String(error) };
    root.innerHTML = errorPanel(error);
    showToast(error.message || "View failed to load", "error");
  }
}
