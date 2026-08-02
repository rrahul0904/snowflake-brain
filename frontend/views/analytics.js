export const VIEW_ID = "review";
import { escapeHtml, getExperienceCommandCenter } from "../api.js?v=20260714-v20-ai-academy";
import { activeTrack, emptyState, setActiveTrack, skeleton, trackOptions } from "../ui.js?v=20260714-v20-ai-academy";

export default async function mount(container, params = {}) {
  const trackId = params.track_id || activeTrack();
  setActiveTrack(trackId);
  container.innerHTML = skeleton("Loading repair queue...");
  try {
    const data = await getExperienceCommandCenter({ track_id: trackId });
    render(container, data);
  } catch (error) {
    container.innerHTML = emptyState("Repair queue unavailable", error.message);
  }
}

function render(container, data) {
  const selected = data.selected_track_id || activeTrack();
  const mistakes = data.mistakes?.items || [];
  const weak = data.readiness?.weak_skills || [];
  const trust = data.content_trust || {};
  container.innerHTML = `
    <section class="page-shell repair-page-v8">
      <header class="page-hero split-hero repair-hero"><div><p class="eyebrow">Repair Queue</p><h1>Fix repeated errors before they become exam misses.</h1><p>The repair queue prioritizes mistake types, weak skills, lab gaps, and content trust warnings.</p></div><label class="cert-filter"><span>Certification</span><select id="track-select">${trackOptions(data.certifications || [], selected)}</select></label></header>
      <section class="repair-grid-v8">
        <article class="panel"><div class="panel-header"><div><p class="eyebrow">Mistake queue</p><h2>${mistakes.length} high-priority misses</h2></div></div><div class="mistake-list-v8">${mistakes.length ? mistakes.map(mistakeRow).join("") : emptyState("No mistakes recorded", "Answer practice questions to create repair evidence.")}</div></article>
        <article class="panel"><div class="panel-header"><div><p class="eyebrow">Weak skills</p><h2>Repair these first</h2></div></div><div class="skill-mini-list">${weak.length ? weak.map((skill) => `<a class="skill-row" href="#/practice?skill_id=${encodeURIComponent(skill.skill_id || "")}"><span><strong>${escapeHtml(skill.skill || "Skill")}</strong><small>${escapeHtml(skill.domain || "")} · ${skill.accuracy_pct || 0}% accuracy</small></span><b>${skill.mastery_level || 0}/7</b></a>`).join("") : emptyState("No weak skills yet", "Start with a diagnostic.")}</div></article>
      </section>
      <section class="panel"><div class="panel-header"><div><p class="eyebrow">Content trust</p><h2>Archive quality warnings</h2></div></div><div class="trust-matrix-v8">${trustRow("Generated notes", trust.generated_notes)}${trustRow("Missing lesson duration", trust.missing_duration)}${trustRow("Empty practice shells", trust.empty_practice_shells)}${trustRow("Questions with thin explanations", trust.questions_without_explanation)}</div></section>
    </section>`;
  container.querySelector("#track-select")?.addEventListener("change", (event) => { setActiveTrack(event.target.value); window.dispatchEvent(new CustomEvent("track-change", { detail: { track_id: event.target.value } })); });
}

function mistakeRow(item) {
  return `<article class="mistake-row-v8"><span>${escapeHtml(item.mistake_type || "mistake")}</span><strong>${escapeHtml(item.skill || item.test_title || "Missed question")}</strong><p>${escapeHtml(item.repair_action || "Review the concept and retry similar questions.")}</p><small>${item.misses || 0} misses · ${escapeHtml(item.domain || "")}</small></article>`;
}
function trustRow(label, value = 0) { return `<div class="trust-metric"><span>${escapeHtml(label)}</span><strong>${value || 0}</strong></div>`; }
