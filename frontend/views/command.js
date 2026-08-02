export const VIEW_ID = "command";
import { escapeHtml, formatNumber, getExperienceCommandCenter } from "../api.js?v=20260714-v20-ai-academy";
import { activeTrack, certBadge, emptyState, metricCard, pct, progressBar, setActiveTrack, skeleton, statusLabel, statSentence, trackOptions } from "../ui.js?v=20260714-v20-ai-academy";
import { showToast } from "../components/toast.js?v=20260714-v20-ai-academy";

export default async function mount(container, params = {}) {
  const trackId = params.track_id || activeTrack();
  setActiveTrack(trackId);
  container.innerHTML = skeleton("Building command center...");
  try {
    const data = await getExperienceCommandCenter({ track_id: trackId });
    render(container, data);
  } catch (error) {
    showToast(error.message, "error");
    container.innerHTML = emptyState("Command center unavailable", error.message, `<button onclick="location.reload()">Retry</button>`);
  }
}

function render(container, data) {
  const readiness = data.readiness || {};
  const score = pct(readiness.readiness_score);
  const probability = readiness.pass_probability_range || [0, 0];
  const command = data.command_brief || {};
  const mission = command.mission || [];
  const summary = data.summary || {};
  const certs = data.certifications || [];
  const selected = data.selected_track_id || activeTrack();
  const cert = certs.find((item) => item.id === selected) || {};
  const blockers = readiness.blockers || [];

  container.innerHTML = `
    <section class="page-shell command-page">
      <section class="hero-command">
        <div class="hero-copy">
          <div class="hero-kicker">${certBadge(selected)} <span>Certification training platform</span></div>
          <h1>${escapeHtml(cert.title || "Snowflake certification command center")}</h1>
          <p>The platform now works as an training workspace: diagnose skill gaps, drive practice, prove labs, repair misses, and enforce a readiness gate before exam day.</p>
          <div class="hero-actions">
            <a class="primary-btn xl" href="#/practice?track_id=${encodeURIComponent(selected)}&mode=diagnostic">Start diagnostic</a>
            <a class="secondary-btn xl" href="#/labs?certification=${encodeURIComponent(selected)}">Open lab runner</a>
            <a class="ghost-link" href="#/intelligence?track_id=${encodeURIComponent(selected)}">View skill graph →</a>
          </div>
        </div>
        <div class="readiness-orb-card">
          <div class="orb" style="--score:${score}"><span>${score}%</span></div>
          <strong>${statusLabel(readiness.status)}</strong>
          <small>Pass probability estimate ${probability[0] || 0}–${probability[1] || 0}%</small>
          ${progressBar(score, "readiness")}
        </div>
      </section>

      <section class="quick-metrics">
        ${metricCard("Archive", statSentence(summary), "Local course corpus", "blue")}
        ${metricCard("Attempts", formatNumber(summary.attempts || 0), "Recorded evidence", "violet")}
        ${metricCard("Mistakes", formatNumber(data.mistakes?.total_unresolved || 0), "Unresolved repair queue", "amber")}
        ${metricCard("Labs", formatNumber((data.labs || []).length), "Configured challenges", "green")}
      </section>

      <section class="command-grid">
        <article class="panel mission-panel">
          <div class="panel-header">
            <div><p class="eyebrow">Today’s command brief</p><h2>Do the next highest-value work</h2></div>
            <select id="track-select" class="inline-select">${trackOptions(certs, selected)}</select>
          </div>
          <div class="mission-timeline">
            ${mission.length ? mission.map((item, index) => missionItem(item, index)).join("") : emptyState("No mission generated", "Take a diagnostic or complete first practice evidence.")}
          </div>
        </article>

        <article class="panel blocker-panel">
          <div class="panel-header"><div><p class="eyebrow">Readiness gate</p><h2>Blocking evidence</h2></div><a href="#/readiness?track_id=${encodeURIComponent(selected)}">Open</a></div>
          <div class="blocker-list">
            ${blockers.length ? blockers.slice(0, 5).map((item) => `<div class="blocker"><span>!</span><p>${escapeHtml(item)}</p></div>`).join("") : `<div class="success-state">No major blockers detected. Validate under timed exam conditions.</div>`}
          </div>
        </article>
      </section>

      <section class="command-grid three">
        <article class="panel">
          <div class="panel-header"><div><p class="eyebrow">Skills</p><h2>Weakest skill signals</h2></div><a href="#/intelligence?track_id=${encodeURIComponent(selected)}">Graph</a></div>
          <div class="skill-mini-list">${renderWeakSkills(readiness.weak_skills || [])}</div>
        </article>
        <article class="panel">
          <div class="panel-header"><div><p class="eyebrow">Labs</p><h2>Skill-proving challenges</h2></div><a href="#/labs?certification=${encodeURIComponent(selected)}">Runner</a></div>
          <div class="lab-mini-list">${renderLabs(data.labs || [], selected)}</div>
        </article>
        <article class="panel">
          <div class="panel-header"><div><p class="eyebrow">Content trust</p><h2>Quality warnings</h2></div><a href="#/review">Audit</a></div>
          <div class="trust-stack">${renderTrust(data.content_trust || {})}</div>
        </article>
      </section>
    </section>
  `;

  container.querySelector("#track-select")?.addEventListener("change", (event) => {
    setActiveTrack(event.target.value);
    window.dispatchEvent(new CustomEvent("track-change", { detail: { track_id: event.target.value } }));
  });
}

function missionItem(item, index) {
  return `<a class="mission-item" href="${escapeHtml(item.href || "#/practice")}">
    <span class="mission-index">${index + 1}</span>
    <span><strong>${escapeHtml(item.title || "Mission item")}</strong><small>${escapeHtml(item.detail || "")}</small></span>
    <b>Start</b>
  </a>`;
}

function renderWeakSkills(skills) {
  if (!skills.length) return emptyState("No weak skill evidence yet", "Run a diagnostic to create the first skill baseline.");
  return skills.slice(0, 5).map((skill) => `<a class="skill-row" href="#/practice?skill_id=${encodeURIComponent(skill.skill_id || "")}"><span><strong>${escapeHtml(skill.skill || "Skill")}</strong><small>${escapeHtml(skill.domain || "Domain")} · ${skill.accuracy_pct || 0}% accuracy</small></span><b>${skill.mastery_level || 0}/7</b></a>`).join("");
}

function renderLabs(labs, selected) {
  if (!labs.length) return emptyState("No labs mapped yet", "Add labs to the certification configuration.");
  return labs.slice(0, 5).map((lab) => `<a class="lab-row" href="#/labs?certification=${encodeURIComponent(selected)}&lab_id=${encodeURIComponent(lab.id || "")}"><span><strong>${escapeHtml(lab.title || "Lab")}</strong><small>${escapeHtml(lab.domain || "Skill challenge")} · ${escapeHtml(lab.difficulty || "")}</small></span><b>${lab.estimated_minutes || 20}m</b></a>`).join("");
}

function renderTrust(trust) {
  const rows = [
    ["Generated notes", trust.generated_notes || 0],
    ["Missing duration", trust.missing_duration || 0],
    ["Empty practice shells", trust.empty_practice_shells || 0],
    ["Thin explanations", trust.questions_without_explanation || 0],
  ];
  return rows.map(([label, value]) => `<div class="trust-row"><span>${escapeHtml(label)}</span><strong>${formatNumber(value)}</strong></div>`).join("");
}
