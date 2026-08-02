export const VIEW_ID = "readiness";
import { escapeHtml, getExperienceCommandCenter } from "../api.js?v=20260714-v20-ai-academy";
import { activeTrack, emptyState, pct, progressBar, setActiveTrack, skeleton, statusLabel, trackOptions } from "../ui.js?v=20260714-v20-ai-academy";

export default async function mount(container, params = {}) {
  const trackId = params.track_id || activeTrack();
  setActiveTrack(trackId);
  container.innerHTML = skeleton("Loading readiness evidence...");
  try {
    const data = await getExperienceCommandCenter({ track_id: trackId });
    render(container, data);
  } catch (error) {
    container.innerHTML = emptyState("Readiness gate unavailable", error.message);
  }
}

function render(container, data) {
  const selected = data.selected_track_id || activeTrack();
  const readiness = data.readiness || {};
  const score = pct(readiness.readiness_score);
  const blockers = readiness.blockers || [];
  const actions = readiness.next_actions || [];
  const domains = readiness.domains || [];
  const probability = readiness.pass_probability_range || [0, 0];

  container.innerHTML = `
    <section class="page-shell readiness-page">
      <header class="page-hero readiness-hero">
        <div>
          <p class="eyebrow">Evidence gate</p>
          <h1>${score >= 82 && !blockers.length ? "Ready signal detected." : "Do not book the exam until evidence supports it."}</h1>
          <p>Readiness is based on practice accuracy, timed performance, lab proof, mistake repair, and content coverage — not completion theater.</p>
        </div>
        <label class="cert-filter"><span>Certification</span><select id="track-select">${trackOptions(data.certifications || [], selected)}</select></label>
      </header>

      <section class="readiness-scoreboard">
        <div class="readiness-giant">
          <div class="orb large" style="--score:${score}"><span>${score}%</span></div>
          <div><p class="eyebrow">Readiness status</p><h2>${statusLabel(readiness.status)}</h2><p>Pass probability estimate: <strong>${probability[0] || 0}–${probability[1] || 0}%</strong></p></div>
        </div>
        <div class="readiness-evidence-grid">
          ${evidence("Question attempts", readiness.attempts || 0, "Target: 100+")}
          ${evidence("Accuracy", `${readiness.accuracy_pct || 0}%`, "Target: 80%+")}
          ${evidence("Mock exams", readiness.mock_exam_attempts || 0, "Target: 2 finished")}
          ${evidence("Labs proven", `${readiness.lab_passed || 0}/${readiness.lab_available || 0}`, "Target: key domains")}
          ${evidence("Misses", readiness.misses || 0, "Target: low/repaired")}
          ${evidence("Mastery", `${readiness.avg_mastery_level || 0}/7`, "Target: 5+")}
        </div>
      </section>

      <section class="readiness-grid">
        <article class="panel blocker-panel serious">
          <div class="panel-header"><div><p class="eyebrow">Blocking reasons</p><h2>${blockers.length || "No"} active blockers</h2></div></div>
          <div class="blocker-list big">
            ${blockers.length ? blockers.map((item) => `<div class="blocker"><span>!</span><p>${escapeHtml(item)}</p></div>`).join("") : `<div class="success-state">No major blockers detected. Run a timed readiness exam to confirm.</div>`}
          </div>
        </article>
        <article class="panel">
          <div class="panel-header"><div><p class="eyebrow">Next actions</p><h2>What moves the score</h2></div></div>
          <div class="action-stack">${actions.length ? actions.map(actionItem).join("") : `<a class="action-tile" href="#/practice?track_id=${encodeURIComponent(selected)}&mode=exam"><strong>Take timed readiness exam</strong><span>No repair action is currently stronger than validation.</span></a>`}</div>
        </article>
      </section>

      <section class="panel">
        <div class="panel-header"><div><p class="eyebrow">Domain evidence</p><h2>Where the gate is weak</h2></div><a href="#/intelligence?track_id=${encodeURIComponent(selected)}">Open graph</a></div>
        <div class="domain-evidence-table">
          ${domains.map(domainRow).join("") || emptyState("No domain evidence", "Run a diagnostic to populate the readiness gate.")}
        </div>
      </section>
    </section>
  `;
  container.querySelector("#track-select")?.addEventListener("change", (event) => {
    setActiveTrack(event.target.value);
    window.dispatchEvent(new CustomEvent("track-change", { detail: { track_id: event.target.value } }));
  });
}

function evidence(label, value, target) {
  return `<div class="evidence-card"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong><small>${escapeHtml(target)}</small></div>`;
}

function actionItem(action) {
  const href = action.action === "Complete lab" ? `#/labs?skill_id=${encodeURIComponent(action.skill_id || "")}` : `#/practice?skill_id=${encodeURIComponent(action.skill_id || "")}`;
  return `<a class="action-tile" href="${href}"><strong>${escapeHtml(action.action || "Repair")}: ${escapeHtml(action.skill || "Skill")}</strong><span>${escapeHtml(action.reason || action.domain || "")}</span></a>`;
}

function domainRow(domain) {
  const score = Math.round(((domain.avg_mastery || 0) / 7) * 100);
  return `<div class="domain-evidence-row"><span><strong>${escapeHtml(domain.domain || domain.domain_id || "Domain")}</strong><small>${domain.skills || 0} skills</small></span><span>${domain.accuracy_pct || 0}% accuracy</span><span>${domain.blockers || 0} blockers</span><span>${progressBar(score)}</span></div>`;
}
