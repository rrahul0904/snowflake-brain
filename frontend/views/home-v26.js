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
  let cert = { id: "snowpro-core", exam_code: "COF-C03", domains: [] };
  if (account) {
    const map = await getSkillMap().catch(() => ({ certifications: [] }));
    const certs = map.certifications || [];
    cert = certs.find((item) => item.id === trackId) || certs[0] || cert;
  }
  setActiveTrack(cert.id);
  const domains = cert.domains || [];
  const tasks = domains.reduce((sum, domain) => sum + (domain.skills || []).length, 0) || 19;
  const primaryLabel = account ? "Continue learning" : "Create account to start";
  const secondaryLabel = account ? (account.plan_code === "free" ? "Take Weekly Mock" : "Take a Mock Exam") : "Sign in to practise";
  const primaryHref = account ? `#/curriculum?track_id=${encodeURIComponent(cert.id)}` : "#/curriculum";
  const secondaryHref = account ? `#/mock?track_id=${encodeURIComponent(cert.id)}` : "#/mock";
  container.innerHTML = `<main class="v26-page v26-home"><section class="v26-home-hero"><p class="v26-kicker">SnowPro Core certification · ${cert.exam_code || "COF-C03"}</p><h1>Practise until you <em>pass.</em></h1><p class="v26-lede">Prepare with a complete written curriculum behind every timed mock. Create a candidate account before any study material or practice content is unlocked.</p><div class="v26-hero-actions"><a class="v26-btn primary" href="${primaryHref}">${primaryLabel}</a><a class="v26-btn secondary" href="${secondaryHref}">${secondaryLabel}</a></div><div class="v26-proof"><span>${account ? `Blueprint-first preparation across ${domains.length || 5} domains · ${tasks} task statements` : "Account required before accessing certification content"}</span></div><div id="v26-home-globe" class="v26-home-globe"></div></section></main>`;
  disposeGlobe = renderActivityGlobe(container.querySelector("#v26-home-globe"));
  renderHomeExtras(container, cert.id);
}
