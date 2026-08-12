import { renderNav } from "./components/nav.js?v=20260812-v23-cert-guide";
import { renderTopbar, refreshTopbar } from "./components/topbar.js?v=20260731-v21-editorial-replica";
import { route } from "./router.js?v=20260812-v23-cert-guide";

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
