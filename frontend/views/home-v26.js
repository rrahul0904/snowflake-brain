export const VIEW_ID = "v26-home-complete";

import { getSkillMap } from "../api.js";
import { activeTrack, setActiveTrack } from "../ui.js";
import { renderActivityGlobe } from "../components/globe.js";
import { renderHomeExtras } from "../components/home-extras.js";
import { candidate, refreshCandidate } from "../auth.js";

let disposeGlobe = null;
export function unmount() { disposeGlobe?.(); disposeGlobe = null; }

export default async function mount(container, params = {}) {
  unmount();
  const trackId = params.track_id || activeTrack();
  await refreshCandidate().catch(() => {});
  const account = candidate();
  const map = await getSkillMap();
  const certs = map.certifications || [];
  const cert = certs.find((item) => item.id === trackId) || certs[0] || { id: "snowpro-core", exam_code: "COF-C03", domains: [] };
  setActiveTrack(cert.id);
  const domains = cert.domains || [];
  const tasks = domains.reduce((sum, domain) => sum + (domain.skills || []).length, 0) || 19;
  const primaryLabel = account ? "Continue learning" : "Start learning";
  const secondaryLabel = account?.plan_code === "free" ? "Take Weekly Mock" : "Take a Mock Exam";
  const secondaryHref = `#/mock?track_id=${encodeURIComponent(cert.id)}`;
  container.innerHTML = `<main class="v26-page v26-home"><section class="v26-home-hero"><p class="v26-kicker">SnowPro Core certification · ${cert.exam_code || "COF-C03"}</p><h1>Practise until you <em>pass.</em></h1><p class="v26-lede">Prepare with a complete written curriculum behind every timed mock: learn the Snowflake blueprint, repair weak tasks, then rehearse the exam experience.</p><div class="v26-hero-actions"><a class="v26-btn primary" href="#/curriculum?track_id=${encodeURIComponent(cert.id)}">${primaryLabel}</a><a class="v26-btn secondary" href="${secondaryHref}">${secondaryLabel}</a></div><div class="v26-proof"><span>Blueprint-first preparation across ${domains.length || 5} domains · ${tasks} task statements</span></div><div id="v26-home-globe" class="v26-home-globe"></div></section></main>`;
  disposeGlobe = renderActivityGlobe(container.querySelector("#v26-home-globe"));
  renderHomeExtras(container, cert.id);
}
