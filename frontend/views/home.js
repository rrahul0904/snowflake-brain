export const VIEW_ID = "v26-home";

import { getSkillMap, getTaskProgress } from "../api.js";
import { activeTrack, setActiveTrack } from "../ui.js";
import { renderActivityGlobe } from "../components/globe.js";

let disposeGlobe = null;
export function unmount() { disposeGlobe?.(); disposeGlobe = null; }

export default async function mount(container, params = {}) {
  unmount();
  const trackId = params.track_id || activeTrack();
  const map = await getSkillMap();
  const certs = map.certifications || [];
  const cert = certs.find((item) => item.id === trackId) || certs[0] || { id: "snowpro-core", exam_code: "COF-C03", domains: [] };
  setActiveTrack(cert.id);
  const progress = await getTaskProgress({ track_id: cert.id }).catch(() => ({ completed_tasks: 0, total_tasks: 19 }));
  const domains = cert.domains || [];
  const tasks = domains.reduce((sum, domain) => sum + (domain.skills || []).length, 0) || 19;
  container.innerHTML = `<main class="v26-page v26-home">
    <section class="v26-home-hero">
      <p class="v26-kicker">SnowPro Core · ${cert.exam_code || "COF-C03"}</p>
      <h1>Practise until you <em>pass.</em></h1>
      <p class="v26-lede">A focused Snowflake certification guide built around the current exam blueprint, written task lessons, deliberate practice, and timed mocks.</p>
      <div class="v26-hero-actions"><a class="v26-btn primary" href="#/curriculum?track_id=${encodeURIComponent(cert.id)}">Start learning</a><a class="v26-btn secondary" href="#/mock?track_id=${encodeURIComponent(cert.id)}">Take a mock exam</a></div>
      <div class="v26-proof"><span>${domains.length || 5} domains</span><i></i><span>${tasks} task statements</span><i></i><span>${progress.completed_tasks || 0}/${progress.total_tasks || tasks} completed</span></div>
      <div id="v26-home-globe" class="v26-home-globe"></div>
    </section>
  </main>`;
  disposeGlobe = renderActivityGlobe(container.querySelector("#v26-home-globe"));
}
