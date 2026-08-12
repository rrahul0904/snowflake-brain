import { getSkillMap } from "../api.js?v=20260812-v23-cert-guide";
import { activeTrack, navigateWithTrack, normalizeTrack, setActiveTrack, trackOptions } from "../ui.js?v=20260731-v21-editorial-replica";

export async function renderTopbar() {
  const topbar = document.querySelector("#topbar");
  if (topbar) {
    topbar.className = "replica-context-bar";
    topbar.setAttribute("aria-hidden", "true");
    topbar.innerHTML = "";
  }
  await refreshTopbar();
}

export async function refreshTopbar() {
  const select = document.querySelector("#replica-track-select");
  if (!select) return;
  try {
    const data = await getSkillMap();
    const tracks = data.certifications || [];
    const requested = activeTrack();
    const selected = normalizeTrack(requested, tracks);
    setActiveTrack(selected);
    select.innerHTML = trackOptions(tracks, selected);
    select.value = selected;
    select.onchange = () => navigateWithTrack(select.value, "#/home");
  } catch {
    select.innerHTML = `<option value="snowpro-core">SnowPro Core · COF-C03</option>`;
  }
}
