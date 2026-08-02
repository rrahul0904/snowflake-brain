export const VIEW_ID = "intelligence";
import { escapeHtml, getExperienceCommandCenter, reindexSkillMap } from "../api.js?v=20260714-v20-ai-academy";
import { activeTrack, emptyState, pct, progressBar, setActiveTrack, skeleton, statusLabel, trackOptions } from "../ui.js?v=20260714-v20-ai-academy";
import { showToast } from "../components/toast.js?v=20260714-v20-ai-academy";

export default async function mount(container, params = {}) {
  const trackId = params.track_id || activeTrack();
  setActiveTrack(trackId);
  container.innerHTML = skeleton("Loading certification graph...");
  try {
    const data = await getExperienceCommandCenter({ track_id: trackId });
    render(container, data);
  } catch (error) {
    container.innerHTML = emptyState("Intelligence layer unavailable", error.message, `<button onclick="location.reload()">Retry</button>`);
  }
}

function render(container, data) {
  const selected = data.selected_track_id || activeTrack();
  const certs = data.certifications || [];
  const mastery = data.mastery || { skills: [], domains: [] };
  const readiness = data.readiness || {};
  const portfolio = data.portfolio?.certifications || [];
  const skills = mastery.skills || [];

  container.innerHTML = `
    <section class="page-shell intelligence-page">
      <header class="page-hero split-hero intelligence-hero">
        <div>
          <p class="eyebrow">Certification graph</p>
          <h1>Skills, evidence, traps, and readiness in one operating layer.</h1>
          <p>The platform connects certifications → domains → skills → lessons → questions → labs → mistakes, so practice becomes targeted evidence instead of random activity.</p>
        </div>
        <div class="hero-control-card">
          <label>Active certification<select id="track-select">${trackOptions(certs, selected)}</select></label>
          <button id="reindex" class="secondary-btn">Rebuild skill map</button>
        </div>
      </header>

      <section class="portfolio-strip">
        ${portfolio.map((cert) => portfolioCard(cert, selected)).join("")}
      </section>

      <section class="intel-grid">
        <article class="panel readiness-model-card">
          <div class="panel-header"><div><p class="eyebrow">Evidence model</p><h2>${statusLabel(readiness.status)}</h2></div><span class="score-chip">${pct(readiness.readiness_score)}%</span></div>
          ${progressBar(readiness.readiness_score, "readiness")}
          <div class="evidence-stats">
            <span><strong>${readiness.attempts || 0}</strong><small>question attempts</small></span>
            <span><strong>${readiness.avg_mastery_level || 0}/7</strong><small>avg mastery</small></span>
            <span><strong>${readiness.lab_passed || 0}/${readiness.lab_available || 0}</strong><small>labs proven</small></span>
            <span><strong>${readiness.mock_exam_attempts || 0}</strong><small>mock exams</small></span>
          </div>
        </article>
        <article class="panel graph-explainer">
          <div class="panel-header"><div><p class="eyebrow">How the brain thinks</p><h2>Evidence hierarchy</h2></div></div>
          <div class="graph-flow">
            ${["Expose", "Practice", "Timed", "Lab", "Retain", "Ready"].map((item, i) => `<span style="--i:${i}">${item}</span>`).join("<b>→</b>")}
          </div>
          <p class="muted">Readiness improves only when the user produces evidence: accurate questions, timed performance, lab validation, and resolved mistakes.</p>
        </article>
      </section>

      <section class="domain-board">
        ${(mastery.domains || []).map(domainCard).join("") || emptyState("No domains mapped", "This certification needs a skill map configuration.")}
      </section>

      <section class="panel mastery-table-panel">
        <div class="panel-header"><div><p class="eyebrow">Skill mastery matrix</p><h2>${skills.length} mapped skills</h2></div><a href="#/practice?track_id=${encodeURIComponent(selected)}">Practice weak skills</a></div>
        <div class="mastery-table">
          <div class="mastery-head"><span>Skill</span><span>Domain</span><span>Evidence</span><span>Accuracy</span><span>Mastery</span></div>
          ${skills.map(skillRow).join("") || `<div class="empty-state">No skills available.</div>`}
        </div>
      </section>
    </section>
  `;

  container.querySelector("#track-select")?.addEventListener("change", (event) => {
    setActiveTrack(event.target.value);
    window.dispatchEvent(new CustomEvent("track-change", { detail: { track_id: event.target.value } }));
  });
  container.querySelector("#reindex")?.addEventListener("click", async () => {
    try {
      const button = container.querySelector("#reindex");
      button.disabled = true;
      button.textContent = "Rebuilding...";
      const result = await reindexSkillMap(selected);
      showToast(`Mapped ${result.mapped || 0} questions`, "success");
      window.dispatchEvent(new CustomEvent("track-change", { detail: { track_id: selected } }));
    } catch (error) {
      showToast(error.message, "error");
    }
  });
}

function portfolioCard(cert, selected) {
  const score = pct(cert.readiness_score);
  return `<a class="portfolio-card ${cert.track_id === selected ? "active" : ""}" href="#/intelligence?track_id=${encodeURIComponent(cert.track_id)}">
    <span>${escapeHtml(cert.title || cert.track_id)}</span>
    <strong>${score}%</strong>
    ${progressBar(score)}
    <small>${statusLabel(cert.status)} · ${cert.blocker_count || 0} blockers</small>
  </a>`;
}

function domainCard(domain) {
  const level = Number(domain.avg_mastery || 0);
  const score = Math.round((level / 7) * 100);
  return `<article class="domain-card"><span>${escapeHtml(domain.domain || domain.domain_id || "Domain")}</span><strong>${level}/7</strong>${progressBar(score)}<small>${domain.skills || 0} skills · ${domain.blockers || 0} blockers · ${domain.accuracy_pct || 0}% accuracy</small></article>`;
}

function skillRow(skill) {
  const score = Math.round(((skill.mastery_level || 0) / 7) * 100);
  const evidence = [
    skill.completed_lessons ? "lesson" : null,
    skill.attempts ? `${skill.attempts} attempts` : null,
    skill.timed_attempts ? "timed" : null,
    skill.passed_labs ? "lab" : null,
  ].filter(Boolean).join(" · ") || "no evidence";
  return `<a class="mastery-row" href="#/practice?skill_id=${encodeURIComponent(skill.skill_id || "")}">
    <span><strong>${escapeHtml(skill.skill || "Skill")}</strong><small>${escapeHtml(skill.objective || "")}</small></span>
    <span>${escapeHtml(skill.domain || "")}</span>
    <span>${escapeHtml(evidence)}</span>
    <span>${skill.accuracy_pct || 0}%</span>
    <span><b>${skill.mastery_level || 0}/7</b>${progressBar(score)}</span>
  </a>`;
}
