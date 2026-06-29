import { showToast } from "./components/toast.js?v=20260629-coachv3";
import { updateActiveNav } from "./components/nav.js?v=20260629-coachv3";

const ASSET_VERSION = "20260629-coachv3";

const routes = {
  "#/": () => import(`./views/dashboard.js?v=${ASSET_VERSION}`),
  "#/setup": () => import(`./views/dashboard.js?v=${ASSET_VERSION}`),
  "#/today": () => import(`./views/dashboard.js?v=${ASSET_VERSION}`),
  "#/plan": () => import(`./views/plan.js?v=${ASSET_VERSION}`),
  "#/quiz": () => import(`./views/quiz.js?v=${ASSET_VERSION}`),
  "#/practice": () => import(`./views/quiz.js?v=${ASSET_VERSION}`),
  "#/video": () => import(`./views/video.js?v=${ASSET_VERSION}`),
  "#/lessons": () => import(`./views/video.js?v=${ASSET_VERSION}`),
  "#/learn": () => import(`./views/video.js?v=${ASSET_VERSION}`),
  "#/search": () => import(`./views/search.js?v=${ASSET_VERSION}`),
  "#/flashcards": () => import(`./views/flashcards.js?v=${ASSET_VERSION}`),
  "#/labs": () => import(`./views/labs.js?v=${ASSET_VERSION}`),
  "#/ai": () => import(`./views/ai.js?v=${ASSET_VERSION}`),
  "#/analytics": () => import(`./views/analytics.js?v=${ASSET_VERSION}`),
  "#/review": () => import(`./views/analytics.js?v=${ASSET_VERSION}`),
  "#/readiness": () => import(`./views/readiness.js?v=${ASSET_VERSION}`),
};

let currentView = null;

export async function route() {
  const root = document.querySelector("#view-root");
  const hash = window.location.hash || "#/today";
  const [path, query = ""] = hash.split("?");
  const loader = routes[path] || routes["#/today"];
  document.body.classList.remove("player-mode", "quiz-active");
  if (currentView?.unmount) currentView.unmount();
  root.innerHTML = `<div class="loading-panel">Loading...</div>`;
  updateActiveNav();
  try {
    currentView = await loader();
    await currentView.default(root, Object.fromEntries(new URLSearchParams(query)));
    root.scrollTop = 0;
  } catch (error) {
    root.innerHTML = `<div class="error-panel"><h1>View failed to load</h1><p>${error.message}</p></div>`;
    showToast(error.message, "error");
  }
}
