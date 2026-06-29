import { escapeHtml, formatNumber, getContentAudit, getProgressSummary, getStudyGoals, getStudyReadiness } from "../api.js";

export default async function mount(container, params = {}) {
  container.innerHTML = `
    <section class="coach-page readiness-page">
      <header class="coach-header">
        <div>
          <p class="eyebrow">Readiness</p>
          <h1>Are you ready to book the exam?</h1>
          <p class="page-subtitle">This page is intentionally strict. It should tell you what is blocking certification readiness.</p>
        </div>
        <a class="primary-btn" href="#/practice?mode=readiness">Take readiness exam</a>
      </header>
      <div id="readiness-root" class="loading-state">Checking readiness...</div>
    </section>
  `;

  try {
    const [goals, progress, readiness, audit] = await Promise.all([
      getStudyGoals().catch(() => ({ goals: [] })),
      getProgressSummary().catch(() => null),
      getStudyReadiness(params.track_id ? { track_id: params.track_id } : {}).catch(() => ({ tracks: [] })),
      getContentAudit().catch(() => null),
    ]);
    const goal = (goals.goals || [])[0];
    const track = (readiness.tracks || []).find((item) => !params.track_id || item.track_id === params.track_id) || (readiness.tracks || [])[0] || {};
    renderReadiness(container, { goal, progress, track, audit });
  } catch (error) {
    container.querySelector("#readiness-root").innerHTML = `<div class="error-state">${escapeHtml(error.message)}</div>`;
  }
}

function renderReadiness(container, { goal, progress, track, audit }) {
  const root = container.querySelector("#readiness-root");
  const blockers = readinessBlockers(progress, track, audit);
  const score = progress?.exam_readiness_pct || 0;
  const verdict = blockers.length ? "Not ready yet" : "Ready with caution";
  root.className = "readiness-cockpit";
  root.innerHTML = `
    <section class="panel readiness-verdict ${blockers.length ? "blocked" : "ready"}">
      <div>
        <p class="eyebrow">Verdict</p>
        <h2>${verdict}</h2>
        <p>${goal ? escapeHtml(goal.track_title) : "No active goal selected"} · readiness score ${score}%</p>
      </div>
      <div class="score-pill giant">${score}%</div>
    </section>

    <section class="coach-grid">
      <article class="panel">
        <div class="panel-header"><div><p class="eyebrow">Blocking reasons</p><h2>Fix before booking</h2></div></div>
        <div class="readiness-blocker-list">
          ${blockers.length ? blockers.map((blocker) => `<div class="readiness-blocker"><strong>${escapeHtml(blocker.title)}</strong><span>${escapeHtml(blocker.detail)}</span><a href="${blocker.href}">${escapeHtml(blocker.action)}</a></div>`).join("") : `<div class="success-state">No critical blockers detected. Take one more full mock to confirm.</div>`}
        </div>
      </article>

      <article class="panel">
        <div class="panel-header"><div><p class="eyebrow">Evidence</p><h2>What this is based on</h2></div></div>
        <div class="coach-stat-list">
          <div><strong>${formatNumber(progress?.total_attempted || 0)}</strong><span>questions attempted</span></div>
          <div><strong>${progress?.accuracy_pct || 0}%</strong><span>overall accuracy</span></div>
          <div><strong>${formatNumber(track.question_count || 0)}</strong><span>questions in selected track</span></div>
          <div><strong>${formatNumber(track.practice_test_count || 0)}</strong><span>source practice tests</span></div>
        </div>
      </article>
    </section>

    <section class="panel readiness-thresholds">
      <p class="eyebrow">Required before exam day</p>
      <div class="threshold-grid">
        <div><strong>Diagnostic complete</strong><span>At least 30 questions answered.</span></div>
        <div><strong>Coverage</strong><span>100+ questions attempted for the certification.</span></div>
        <div><strong>Accuracy</strong><span>80%+ on repeated practice.</span></div>
        <div><strong>Mock exams</strong><span>Two full mocks above 80% before booking.</span></div>
        <div><strong>Repair loop</strong><span>Weak topics and repeated mistakes reviewed.</span></div>
        <div><strong>Content trust</strong><span>Know where transcripts are generated notes only.</span></div>
      </div>
    </section>
  `;
}

function readinessBlockers(progress, track, audit) {
  const blockers = [];
  if (!progress?.total_attempted) {
    blockers.push({ title: "No diagnostic completed", detail: "The coach has no baseline. Start with 30 mixed questions.", action: "Take diagnostic", href: "#/practice?mode=diagnostic" });
  }
  if ((progress?.total_attempted || 0) < 100) {
    blockers.push({ title: "Question coverage is too low", detail: `${formatNumber(progress?.total_attempted || 0)} questions attempted. Get to at least 100 before trusting readiness.`, action: "Practice more", href: "#/practice" });
  }
  if ((progress?.accuracy_pct || 0) < 75) {
    blockers.push({ title: "Accuracy below safe buffer", detail: `${progress?.accuracy_pct || 0}% overall accuracy. Target 80%+ before exam day.`, action: "Repair weak topics", href: "#/review" });
  }
  if ((track.practice_test_count || 0) === 0) {
    blockers.push({ title: "No source mock exam detected", detail: "This track may not have enough full-exam evidence.", action: "Use mixed readiness exam", href: "#/practice?mode=readiness" });
  }
  const generated = audit?.transcript_quality?.generated_notes || 0;
  if (generated > 0) {
    blockers.push({ title: "Some lessons are generated notes", detail: `${formatNumber(generated)} lessons do not have original transcript quality. Use questions to validate learning.`, action: "Use Learn + Practice loop", href: "#/learn" });
  }
  return blockers;
}
