export const VIEW_ID = "v26-home-complete";

import { getSkillMap } from "../api.js";
import { activeTrack, setActiveTrack } from "../ui.js";
import { renderActivityGlobe } from "../components/globe.js";
import { renderHomeCommandCenter } from "../components/home-command-center.js";
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
  const domainCount = domains.length || 5;
  const tasks = domains.reduce((sum, domain) => sum + (domain.skills || []).length, 0) || 19;
  const primaryLabel = account ? "Continue preparing" : "Start preparing";
  const secondaryLabel = account ? "Take a mock exam" : "Explore certifications";
  const primaryHref = account ? `#/curriculum?track_id=${encodeURIComponent(cert.id)}` : "#/certifications";
  const secondaryHref = account ? `#/mock?track_id=${encodeURIComponent(cert.id)}` : "#/certifications";
  const headline = account ? "Know what to study next." : "Prepare for SnowPro with a system that knows what to study next.";
  const lede = account
    ? "Use your real study evidence to focus weak domains, clear due reviews, repair mistakes, and decide when you are ready for the next timed mock."
    : "Study SnowPro domains, diagnose weaknesses, practise targeted drills, take timed mocks, review mistakes, and track readiness with a focused Snowflake learning system.";

  container.innerHTML = `<main class="v26-page v26-home"><section class="v26-home-hero"><p class="v26-kicker">Snowflake Study Command Center · ${cert.exam_code || "COF-C03"}</p><h1>${headline.replace("next.", "<em>next.</em>")}</h1><p class="v26-lede">${lede}</p><div class="v26-hero-actions"><a class="v26-btn primary" href="${primaryHref}">${primaryLabel}</a><a class="v26-btn secondary" href="${secondaryHref}">${secondaryLabel}</a></div><div class="v26-proof"><span>${account ? `Blueprint-first preparation across ${domainCount} weighted domains · ${tasks} task statements` : "Official exam facts stay separate from Snowflake Brain practice configuration · candidate access required for study content"}</span></div><div id="v26-home-globe" class="v26-home-globe"></div></section><section class="v26-home-facts" aria-label="SnowPro Core preparation facts"><div><strong>${domainCount}</strong><span>Weighted domains</span></div><div><strong>${tasks}</strong><span>Task statements</span></div><div><strong>30 / 100</strong><span>Snowflake Brain mock sizes</span></div><div><strong>750</strong><span>Internal practice threshold</span></div></section></main>`;
  disposeGlobe = renderActivityGlobe(container.querySelector("#v26-home-globe"));
  await renderHomeCommandCenter(container, cert.id, account);
  renderHomeExtras(container, cert.id);
}
