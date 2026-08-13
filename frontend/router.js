import { showToast } from "./components/toast.js?v=20260812-v25-production-mock";
import { updateActiveNav } from "./components/nav.js?v=20260812-v25-production-mock";
import { errorPanel, skeleton } from "./ui.js?v=20260731-v21-editorial-replica";

const ASSET_VERSION = "20260812-v25-production-mock-r4";
const guide = () => import(`./views/guide.js?v=${ASSET_VERSION}`);
const mock = () => import(`./views/mock.js?v=${ASSET_VERSION}`);

const routes = {
  "#/home": guide,
  "#/curriculum": guide,
  "#/progress": guide,
  "#/domain": guide,
  "#/skill": guide,
  "#/diagnostic": guide,
  "#/drill": guide,
  "#/mock": mock,
  "#/mock/start": mock,
  "#/mock/session": mock,
  "#/mock/result": mock,
  "#/mock/history": mock,
  "#/exercises": guide,
  "#/quick-reference": guide,
  "#/glossary": guide,
  "#/practice": () => import(`./views/quiz.js?v=${ASSET_VERSION}`),
  "#/labs": () => import(`./views/labs.js?v=${ASSET_VERSION}`),
  "#/journal": () => import(`./views/journal.js?v=${ASSET_VERSION}`),
  "#/article": () => import(`./views/journal.js?v=${ASSET_VERSION}`),
};

const aliases = {
  "#/": "#/home",
  "#/learn": "#/curriculum",
  "#/readiness": "#/progress",
  "#/quiz": "#/practice",
  "#/review": "#/drill",
};

let currentView = null;

export async function route() {
  const root = document.querySelector("#view-root");
  const hash = window.location.hash || "#/home";
  const [rawPath, query = ""] = hash.split("?");
  const path = aliases[rawPath] || rawPath;
  const loader = routes[path] || routes["#/home"];
  window.__SNOWFLAKE_BRAIN_ROUTE_STATUS__ = { status: "loading", route: path, error: null };
  document.body.classList.remove("player-mode", "quiz-active", "replica-exam-active");
  if (currentView?.unmount) currentView.unmount();
  root.innerHTML = skeleton("Loading certification guide...");
  updateActiveNav();
  try {
    currentView = await loader();
    await currentView.default(root, Object.fromEntries(new URLSearchParams(query)));
    root.dataset.routeOk = "true";
    root.dataset.routePath = path;
    root.dataset.viewId = currentView.VIEW_ID || "unknown";
    window.__SNOWFLAKE_BRAIN_ROUTE_STATUS__ = {
      status: "ok",
      route: path,
      view_id: currentView.VIEW_ID || "unknown",
      error: null,
    };
    root.scrollTop = 0;
  } catch (error) {
    root.dataset.routeOk = "false";
    window.__SNOWFLAKE_BRAIN_ROUTE_STATUS__ = {
      status: "error",
      route: path,
      error: error.message || String(error),
    };
    root.innerHTML = errorPanel(error);
    showToast(error.message || "View failed to load", "error");
  }
}
