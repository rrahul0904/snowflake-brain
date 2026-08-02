import { renderNav } from "./components/nav.js?v=20260731-v21-editorial-replica";
import { renderTopbar, refreshTopbar } from "./components/topbar.js?v=20260731-v21-editorial-replica";
import { route } from "./router.js?v=20260731-v21-editorial-replica";

async function boot() {
  await Promise.all([renderNav(), renderTopbar()]);
  window.addEventListener("hashchange", route);
  window.addEventListener("track-change", () => {
    refreshTopbar();
    route();
  });
  if (!window.location.hash) window.location.hash = "#/curriculum";
  await route();
}

boot();
