export const VIEW_ID = "v26-mistakes";

import { escapeHtml, getMistakeNotebook, getSkillMap, updateMistakeNotebook } from "../api.js";
import { activeTrack } from "../ui.js";
import { studyLayout } from "../components/study-shell.js";

export default async function mount(container, params = {}) {
  const trackId = params.track_id || activeTrack();
  const filter = ["all", "unmastered", "mastered"].includes(params.filter) ? params.filter : "all";
  const [map, active, mastered] = await Promise.all([
    getSkillMap(),
    getMistakeNotebook({ track_id: trackId, status: "active", limit: 100 }).catch(() => ({ counts: {}, items: [] })),
    getMistakeNotebook({ track_id: trackId, status: "mastered", limit: 100 }).catch(() => ({ counts: {}, items: [] })),
  ]);
  const cert = (map.certifications || []).find((item) => item.id === trackId) || (map.certifications || [])[0];
  if (!cert) throw new Error("Certification is not configured");

  const unmasteredItems = active.items || [];
  const masteredItems = mastered.items || [];
  const allItems = [...unmasteredItems, ...masteredItems];
  const visible = filter === "mastered" ? masteredItems : filter === "unmastered" ? unmasteredItems : allItems;
  const masteryRate = allItems.length ? Math.round(masteredItems.length / allItems.length * 100) : 0;

  container.innerHTML = studyLayout(cert, "mistakes", `<a class="v26-study-back" href="#/progress?track_id=${encodeURIComponent(trackId)}" aria-label="Back">‹</a>
    <header class="v26-recording-progress-head v26-mistake-head"><p class="v26-kicker">Remediation loop</p><h1>Mistake Collection</h1><p>Every recurring miss should become a rule you remember. Review, annotate, retry, and move concepts to mastered only when the evidence supports it.</p></header>
    <section class="v26-mistake-summary">
      ${summaryCard("Total mistakes", allItems.length)}
      ${summaryCard("Unmastered", unmasteredItems.length)}
      ${summaryCard("Mastered", masteredItems.length)}
      ${summaryCard("Mastery rate", `${masteryRate}%`)}
    </section>
    <nav class="v26-mistake-filters" aria-label="Mistake filters">
      ${filterLink(trackId, "all", `All (${allItems.length})`, filter)}
      ${filterLink(trackId, "unmastered", `Unmastered (${unmasteredItems.length})`, filter)}
      ${filterLink(trackId, "mastered", `Mastered (${masteredItems.length})`, filter)}
    </nav>
    ${visible.length ? `<section class="v26-mistake-collection-list">${visible.map((item) => mistakeCard(item, trackId)).join("")}</section>` : emptyState(filter, trackId)}
    <section class="v26-mistake-next"><div><p class="v26-kicker">Next action</p><h2>Turn mistakes back into practice.</h2><p>Use spaced review when questions are due, or launch a targeted drill if the same domain keeps recurring.</p></div><div><a class="v26-btn primary" href="#/practice?track_id=${encodeURIComponent(trackId)}&mode=srs">Review due mistakes</a><a class="v26-btn secondary" href="#/practice?track_id=${encodeURIComponent(trackId)}&mode=drill">Start targeted drill</a></div></section>`);

  bindActions(container, trackId, filter);
}

function mistakeCard(item, trackId) {
  const status = String(item.status || "open");
  const isMastered = status === "mastered";
  const skillHref = item.skill_id ? `#/skill?track_id=${encodeURIComponent(trackId)}&skill_id=${encodeURIComponent(item.skill_id)}` : `#/curriculum?track_id=${encodeURIComponent(trackId)}`;
  return `<article class="v26-mistake-collection-card ${isMastered ? "mastered" : ""}">
    <div class="v26-mistake-card-meta"><div><span>${escapeHtml(status.replaceAll("_", " "))}</span><b>${Number(item.miss_count || 1)} miss${Number(item.miss_count || 1) === 1 ? "" : "es"}</b></div>${item.domain_title ? `<em>${escapeHtml(item.domain_title)}</em>` : ""}</div>
    <h2>${escapeHtml(item.question || "Question unavailable")}</h2>
    <div class="v26-mistake-rule"><span>Rule to remember</span><p>${item.note ? escapeHtml(item.note) : "No note yet. Write the distinction, trap, or rule that would stop you making the same mistake again."}</p></div>
    <footer>
      <a href="${skillHref}">Related lesson →</a>
      <button type="button" data-note="${escapeHtml(item.question_id)}" data-current-note="${escapeHtml(item.note || "")}">${item.note ? "Edit note" : "Add note"}</button>
      <button type="button" data-status="${escapeHtml(item.question_id)}" data-next-status="${isMastered ? "open" : "mastered"}">${isMastered ? "Move to unmastered" : "Mark mastered"}</button>
    </footer>
  </article>`;
}

function summaryCard(label, value) {
  return `<div><span>${label}</span><strong>${value}</strong></div>`;
}

function filterLink(trackId, value, label, current) {
  return `<a class="${value === current ? "active" : ""}" href="#/mistakes?track_id=${encodeURIComponent(trackId)}&filter=${value}">${label}</a>`;
}

function emptyState(filter, trackId) {
  const message = filter === "mastered" ? "Nothing has been marked mastered yet." : filter === "unmastered" ? "No active mistakes — keep practising." : "Your mistake collection is empty.";
  return `<section class="v26-no-progress v26-mistake-empty"><strong>${message}</strong><p>Incorrect answers from practice and mock remediation will appear here automatically.</p><a class="v26-btn primary" href="#/practice?track_id=${encodeURIComponent(trackId)}">Start practice</a></section>`;
}

function bindActions(container, trackId, filter) {
  container.querySelectorAll("[data-note]").forEach((button) => button.addEventListener("click", async () => {
    const note = window.prompt("What rule, distinction, or trap do you want to remember?", button.dataset.currentNote || "");
    if (note === null) return;
    button.disabled = true;
    await updateMistakeNotebook(button.dataset.note, { note }).catch(() => null);
    window.location.hash = `#/mistakes?track_id=${encodeURIComponent(trackId)}&filter=${filter}`;
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  }));
  container.querySelectorAll("[data-status]").forEach((button) => button.addEventListener("click", async () => {
    button.disabled = true;
    await updateMistakeNotebook(button.dataset.status, { status: button.dataset.nextStatus }).catch(() => null);
    window.location.hash = `#/mistakes?track_id=${encodeURIComponent(trackId)}&filter=${filter}`;
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  }));
}
