import { showToast } from "./components/toast.js";
import { updateActiveNav } from "./components/nav.js";
import { errorPanel, skeleton } from "./ui.js";

const home = () => import("./views/home-v26.js");
const certifications = () => import("./views/certifications.js");
const curriculum = () => import("./views/curriculum-v26.js");
const lesson = () => import("./views/lesson-v26.js");
const guide = () => import("./views/guide.js");
const practice = () => import("./views/practice.js");
const quiz = () => import("./views/quiz.js");
const mockLanding = () => import("./views/mock-landing.js");
const mockStart = () => import("./views/mock-start-v26.js");
const examSession = () => import("./views/exam-session-v26.js");
const mock = () => import("./views/mock.js");
const reference = () => import("./views/reference.js");
const journal = () => import("./views/journal.js");

const routes = {
  "#/home": home,
  "#/certifications": certifications,
  "#/curriculum": curriculum,
  "#/domain": curriculum,
  "#/skill": lesson,
  "#/progress": guide,
  "#/quick-reference": guide,
  "#/glossary": guide,
  "#/exercises": guide,
  "#/practice": practice,
  "#/quiz": quiz,
  "#/diagnostic": quiz,
  "#/drill": quiz,
  "#/mock": mockLanding,
  "#/mock/start": mockStart,
  "#/mock/session": examSession,
  "#/mock/result": mock,
  "#/mock/history": mock,
  "#/reference": reference,
  "#/journal": journal,
  "#/article": journal,
  "#/labs": () => import("./views/labs.js"),
};

const aliases = { "#/": "#/home", "#/learn": "#/curriculum", "#/readiness": "#/progress", "#/review": "#/drill" };
let currentView = null;

export async function route() {
  const root = document.querySelector("#view-root");
  const hash = window.location.hash || "#/home";
  const [rawPath, query = ""] = hash.split("?");
  const path = aliases[rawPath] || rawPath;
  const loader = routes[path];
  if (!loader) {
    window.history.replaceState(null, "", "#/home");
    return route();
  }
  window.__SNOWFLAKE_BRAIN_ROUTE_STATUS__ = { status: "loading", route: path, error: null };
  document.body.classList.remove("player-mode", "quiz-active", "replica-exam-active", "mock-player-active", "v26-exam-active", "v26-exam-nav-open");
  currentView?.unmount?.();
  root.innerHTML = skeleton("Loading certification guide...");
  updateActiveNav();
  try {
    currentView = await loader();
    await currentView.default(root, Object.fromEntries(new URLSearchParams(query)));
    root.dataset.routeOk = "true";
    root.dataset.routePath = path;
    root.dataset.viewId = currentView.VIEW_ID || "unknown";
    window.__SNOWFLAKE_BRAIN_ROUTE_STATUS__ = { status: "ok", route: path, view_id: currentView.VIEW_ID || "unknown", error: null };
    root.scrollTop = 0;
    window.scrollTo({ top: 0, behavior: "instant" });
  } catch (error) {
    root.dataset.routeOk = "false";
    window.__SNOWFLAKE_BRAIN_ROUTE_STATUS__ = { status: "error", route: path, error: error.message || String(error) };
    root.innerHTML = errorPanel(error);
    showToast(error.message || "View failed to load", "error");
  }
}
