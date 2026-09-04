export const VIEW_ID = "v26-mistakes";

import { escapeHtml, getMistakeNotebook, getSkillMap, updateMistakeNotebook } from "../api.js";
import { activeTrack } from "../ui.js";
import { studyLayout } from "../components/study-shell.js";
import { emptyState } from "../components/learning-widgets.js";

const ROOT_CAUSES = [
  ["concept_gap", "Concept gap"],
  ["misread_question", "Misread question"],
  ["overconfidence", "Overconfidence"],
  ["weak_terminology", "Weak terminology"],
  ["scenario_confusion", "Scenario confusion"],
  ["time_pressure", "Time pressure"],
];

export default async function mount(container, params = {}) {
  const trackId = params.track_id || activeTrack();
  const filter = ["all", "unmastered", "mastered"].includes(params.filter) ? params.filter : "all";
  const domainFilter = params.domain || "";
  const causeFilter = params.cause || "";
  const [map, active, mastered] = await Promise.all([
    getSkillMap(),
    getMistakeNotebook({ track_id: trackId, status: "active", limit: 200 }).catch(() => ({ counts: {}, items: [] })),
    getMistakeNotebook({ track_id: trackId, status: "mastered", limit: 200 }).catch(() => ({ counts: {}, items: [] })),
  ]);
  const cert = (map.certifications || []).find((item) => item.id === trackId) || (map.certifications || [])[0];
  if (!cert) throw new Error("Certification is not configured");
  const domainMap = new Map((cert.domains || []).map((domain) => [domain.id, domain]));
  const skillMap = new Map((cert.domains || []).flatMap((domain) => (domain.skills || []).map((skill) => [skill.id, { ...skill, domain }] )));

  const enrich = (item) => ({ ...item, domain: domainMap.get(item.domain_id) || null, skill: skillMap.get(item.skill_id) || null });
  const unmasteredItems = (active.items || []).map(enrich);
  const masteredItems = (mastered.items || []).map(enrich);
  const allItems = [...unmasteredItems, ...masteredItems];
  const statusItems = filter === "mastered" ? masteredItems : filter === "unmastered" ? unmasteredItems : allItems;
  const visible = statusItems.filter((item) => (!domainFilter || item.domain_id === domainFilter) && (!causeFilter || normalizedCause(item.root_cause) === causeFilter));
  const masteryRate = allItems.length ? Math.round(masteredItems.length / allItems.length * 100) : 0;
  const highRisk = unmasteredItems.filter((item) => Number(item.miss_count || 0) >= 2 || normalizedCause(item.root_cause) === "overconfidence").length;

  container.innerHTML = studyLayout(cert, "mistakes", `<a class="v26-study-back" href="#/progress?track_id=${encodeURIComponent(trackId)}" aria-label="Back">‹</a>
    <header class="v26-recording-progress-head v26-mistake-head"><p class="v26-kicker">Mistake remediation</p><h1>Mistake Notebook</h1><p>Classify why a miss happened, write the rule you want to remember, revisit the related task, and let repeated correct reviews move it toward mastery.</p></header>
    <section class="v26-mistake-summary">
      ${summaryCard("Total mistakes", allItems.length)}
      ${summaryCard("Unmastered", unmasteredItems.length)}
      ${summaryCard("High risk", highRisk)}
      ${summaryCard("Mastery rate", `${masteryRate}%`)}
    </section>
    <section class="v26-progress-section v26-mistake-filter-panel"><div class="v26-section-heading"><p class="v26-kicker">Filter the pattern</p><h2>Find the mistakes that keep repeating.</h2></div><div class="v26-mistake-filter-grid"><label>Status<select data-filter-status><option value="all" ${filter === "all" ? "selected" : ""}>All</option><option value="unmastered" ${filter === "unmastered" ? "selected" : ""}>Unmastered</option><option value="mastered" ${filter === "mastered" ? "selected" : ""}>Mastered</option></select></label><label>Domain<select data-filter-domain><option value="">All domains</option>${(cert.domains || []).map((domain, index) => `<option value="${escapeHtml(domain.id)}" ${domainFilter === domain.id ? "selected" : ""}>D${index + 1} · ${escapeHtml(domain.title)}</option>`).join("")}</select></label><label>Mistake type<select data-filter-cause><option value="">All mistake types</option>${ROOT_CAUSES.map(([value,label]) => `<option value="${value}" ${causeFilter === value ? "selected" : ""}>${label}</option>`).join("")}</select></label></div></section>
    ${visible.length ? `<section class="v26-mistake-collection-list">${visible.map((item) => mistakeCard(item, trackId)).join("")}</section>` : emptyState("No mistakes match these filters", "Try a different status, domain, or mistake type. Incorrect answers from practice and mocks will continue to populate this notebook.", `#/mistakes?track_id=${encodeURIComponent(trackId)}`, "Clear filters")}
    <section class="v26-mistake-next"><div><p class="v26-kicker">Next action</p><h2>Turn a mistake back into retrieval.</h2><p>Due review is best for scheduled retrieval. Targeted drill is best when a domain or task keeps recurring.</p></div><div><a class="v26-btn primary" href="#/practice?track_id=${encodeURIComponent(trackId)}&mode=srs">Start today’s review</a><a class="v26-btn secondary" href="#/practice?track_id=${encodeURIComponent(trackId)}&mode=drill">Build targeted drill</a></div></section>`, "", []);

  bindActions(container, trackId, filter, domainFilter, causeFilter);
}

function mistakeCard(item, trackId) {
  const status = String(item.status || "open");
  const isMastered = status === "mastered";
  const cause = normalizedCause(item.root_cause);
  const skillHref = item.skill_id ? `#/skill?track_id=${encodeURIComponent(trackId)}&skill_id=${encodeURIComponent(item.skill_id)}` : `#/curriculum?track_id=${encodeURIComponent(trackId)}`;
  const drillHref = item.skill_id ? `#/practice?track_id=${encodeURIComponent(trackId)}&mode=drill&skill_id=${encodeURIComponent(item.skill_id)}` : `#/practice?track_id=${encodeURIComponent(trackId)}&mode=drill${item.domain_id ? `&domain_id=${encodeURIComponent(item.domain_id)}` : ""}`;
  return `<article class="v26-mistake-collection-card ${isMastered ? "mastered" : ""}">
    <div class="v26-mistake-card-meta"><div><span>${escapeHtml(status.replaceAll("_", " "))}</span><b>${Number(item.miss_count || 1)} miss${Number(item.miss_count || 1) === 1 ? "" : "es"}</b></div><em>${escapeHtml(item.domain?.title || item.domain_id || "Domain not mapped")}${item.skill?.task_code ? ` · Task ${escapeHtml(item.skill.task_code)}` : ""}</em></div>
    <h2>${escapeHtml(item.question || "Question unavailable")}</h2>
    <div class="v26-mistake-insights"><div><span>Mistake type</span><select data-root-cause="${escapeHtml(item.question_id)}" aria-label="Mistake type">${ROOT_CAUSES.map(([value,label]) => `<option value="${value}" ${cause === value ? "selected" : ""}>${label}</option>`).join("")}<option value="" ${!cause ? "selected" : ""}>Not classified</option></select></div><div><span>Last missed</span><strong>${formatDate(item.last_missed_at)}</strong></div><div><span>Review state</span><strong>${Number(item.repetitions || 0)} correct repetitions · ${Number(item.lapses || 0)} lapse${Number(item.lapses || 0) === 1 ? "" : "s"}</strong></div></div>
    <div class="v26-mistake-rule"><span>Rule to remember</span><p>${item.note ? escapeHtml(item.note) : "No note yet. Write the distinction, trap, or rule that would stop you making the same mistake again."}</p></div>
    <footer>
      <a href="${skillHref}">Related lesson →</a>
      <a href="${drillHref}">Drill similar →</a>
      <button type="button" data-note="${escapeHtml(item.question_id)}" data-current-note="${escapeHtml(item.note || "")}">${item.note ? "Edit rule" : "Add rule"}</button>
      <button type="button" data-status="${escapeHtml(item.question_id)}" data-next-status="${isMastered ? "open" : "mastered"}">${isMastered ? "Move to unmastered" : "Mark mastered"}</button>
    </footer>
  </article>`;
}

function summaryCard(label, value) { return `<div><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`; }
function normalizedCause(value = "") { return String(value || "").trim().toLowerCase().replaceAll(" ", "_").replaceAll("-", "_"); }
function formatDate(value) { if (!value) return "—"; const date = new Date(String(value).replace(" ", "T") + (String(value).includes("Z") ? "" : "Z")); return Number.isNaN(date.getTime()) ? escapeHtml(String(value)) : date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }); }

function bindActions(container, trackId, filter, domainFilter, causeFilter) {
  const navigateFilters = () => {
    const status = container.querySelector("[data-filter-status]")?.value || "all";
    const domain = container.querySelector("[data-filter-domain]")?.value || "";
    const cause = container.querySelector("[data-filter-cause]")?.value || "";
    const params = new URLSearchParams({ track_id: trackId, filter: status });
    if (domain) params.set("domain", domain);
    if (cause) params.set("cause", cause);
    window.location.hash = `#/mistakes?${params}`;
  };
  ["[data-filter-status]", "[data-filter-domain]", "[data-filter-cause]"].forEach((selector) => container.querySelector(selector)?.addEventListener("change", navigateFilters));
  container.querySelectorAll("[data-note]").forEach((button) => button.addEventListener("click", async () => {
    const note = window.prompt("What rule, distinction, or trap do you want to remember?", button.dataset.currentNote || "");
    if (note === null) return;
    button.disabled = true;
    await updateMistakeNotebook(button.dataset.note, { note }).catch(() => null);
    refresh(trackId, filter, domainFilter, causeFilter);
  }));
  container.querySelectorAll("[data-root-cause]").forEach((select) => select.addEventListener("change", async () => {
    select.disabled = true;
    await updateMistakeNotebook(select.dataset.rootCause, { root_cause: select.value }).catch(() => null);
    select.disabled = false;
  }));
  container.querySelectorAll("[data-status]").forEach((button) => button.addEventListener("click", async () => {
    button.disabled = true;
    await updateMistakeNotebook(button.dataset.status, { status: button.dataset.nextStatus }).catch(() => null);
    refresh(trackId, filter, domainFilter, causeFilter);
  }));
}

function refresh(trackId, filter, domain, cause) {
  const params = new URLSearchParams({ track_id: trackId, filter });
  if (domain) params.set("domain", domain);
  if (cause) params.set("cause", cause);
  window.location.hash = `#/mistakes?${params}`;
  window.dispatchEvent(new HashChangeEvent("hashchange"));
}
