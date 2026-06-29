import { renderNav } from "./components/nav.js?v=20260629-coachv3";
import { renderTopbar } from "./components/topbar.js?v=20260629-coachv3";
import { route } from "./router.js?v=20260629-coachv3";

async function boot() {
  await Promise.all([renderNav(), renderTopbar()]);
  window.addEventListener("hashchange", route);
  if (!window.location.hash) window.location.hash = "#/today";
  await route();
}

boot();
