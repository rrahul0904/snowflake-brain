export const VIEW_ID = "v26-exam-traps";

import { escapeHtml, getSkillMap } from "../api.js";
import { activeTrack } from "../ui.js";
import { DOMAIN_COLORS, studyLayout } from "../components/study-shell.js";
import { examTrapCard } from "../components/learning-widgets.js";

export default async function mount(container, params = {}) {
  const trackId = params.track_id || activeTrack();
  const map = await getSkillMap();
  const cert = (map.certifications || []).find((item) => item.id === trackId) || (map.certifications || [])[0];
  if (!cert) throw new Error("Certification is not configured");
  const query = String(params.q || "").trim().toLowerCase();
  const domainFilter = params.domain || "";
  const domains = (cert.domains || []).map((domain, index) => ({ ...domain, index, traps: (domain.skills || []).flatMap((skill) => (skill.exam_traps || []).map((trap) => ({ trap, skill, domain }))) }));
  const total = domains.reduce((sum, domain) => sum + domain.traps.length, 0);

  container.innerHTML = studyLayout(cert, "exam-traps", `<a class="v26-study-back" href="#/reference?track_id=${encodeURIComponent(trackId)}" aria-label="Back">‹</a><header class="v26-recording-progress-head"><p class="v26-kicker">Scenario reasoning</p><h1>Exam Trap Library</h1><p>Study the distractors and misconceptions that make SnowPro scenarios difficult. Every trap stays mapped to its domain and task so you can route straight back to the lesson or a focused drill.</p></header><section class="v26-progress-section"><div class="v26-trap-controls"><label><span>Search traps</span><input type="search" value="${escapeHtml(params.q || "")}" placeholder="Search concept, task, or trap…" data-trap-search></label><label><span>Domain</span><select data-trap-domain><option value="">All domains</option>${domains.map((domain) => `<option value="${escapeHtml(domain.id)}" ${domain.id === domainFilter ? "selected" : ""}>D${domain.index + 1} · ${escapeHtml(domain.title)}</option>`).join("")}</select></label><div><span>Library</span><strong>${total} authored trap${total === 1 ? "" : "s"}</strong></div></div></section><section class="v26-trap-library">${domains.map((domain) => domainSection(domain, trackId, query, domainFilter)).join("") || `<p class="v26-empty-copy">No exam traps are configured for this certification.</p>`}</section>`, "", []);
  bind(container, trackId);
}

function domainSection(domain, trackId, query, domainFilter) {
  if (domainFilter && domain.id !== domainFilter) return "";
  const traps = domain.traps.filter((row) => !query || `${row.trap} ${row.skill.title} ${row.skill.task_code || ""}`.toLowerCase().includes(query));
  if (!traps.length) return "";
  return `<section class="v26-progress-section v26-trap-domain"><div class="v26-section-heading"><div><p class="v26-kicker" style="color:${DOMAIN_COLORS[domain.index % DOMAIN_COLORS.length]}">Domain ${domain.index + 1} · ${Number(domain.weight || 0)}%</p><h2>${escapeHtml(domain.title)}</h2></div><span>${traps.length} trap${traps.length === 1 ? "" : "s"}</span></div><div class="v26-trap-grid">${traps.map((row) => `<div>${examTrapCard({ trap: row.trap, correction: `Return to Task ${row.skill.task_code || ""} and reason from the documented feature boundary.` })}<footer><a href="#/skill?track_id=${encodeURIComponent(trackId)}&skill_id=${encodeURIComponent(row.skill.id)}">Task ${escapeHtml(row.skill.task_code || "")} lesson →</a><a href="#/practice?track_id=${encodeURIComponent(trackId)}&mode=drill&skill_id=${encodeURIComponent(row.skill.id)}">Drill similar →</a></footer></div>`).join("")}</div></section>`;
}

function bind(container, trackId) {
  const search = container.querySelector("[data-trap-search]");
  const domain = container.querySelector("[data-trap-domain]");
  const navigate = () => {
    const params = new URLSearchParams({ track_id: trackId });
    if (search?.value.trim()) params.set("q", search.value.trim());
    if (domain?.value) params.set("domain", domain.value);
    window.location.hash = `#/exam-traps?${params}`;
  };
  search?.addEventListener("change", navigate);
  domain?.addEventListener("change", navigate);
}
