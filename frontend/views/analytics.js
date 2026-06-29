import { escapeHtml, formatNumber, getContentAudit, getProgressSummary, getStudyReadiness, getTopicProgress } from "../api.js";
import { showToast } from "../components/toast.js";

export default async function mount(container) {
  container.innerHTML = `
    <section class="coach-page review-page">
      <header class="coach-header">
        <div>
          <p class="eyebrow">Review</p>
          <h1>Fix mistakes before they become exam misses.</h1>
          <p class="page-subtitle">Review is not analytics. It is the repair queue for weak topics, missed questions, and content trust warnings.</p>
        </div>
        <a class="primary-btn" href="#/practice?mode=weak">Repair weakest topic</a>
      </header>

      <section class="review-grid">
        <article id="readiness-card" class="panel loading-state">Loading readiness...</article>
        <article id="weak-topics" class="panel loading-state">Loading weak topics...</article>
      </section>

      <section class="review-grid wide-left">
        <article class="panel">
          <div class="panel-header"><div><p class="eyebrow">Practice repair</p><h2>Next actions</h2></div></div>
          <div id="repair-actions" class="action-stack loading-state">Loading actions...</div>
        </article>
        <article class="panel">
          <div class="panel-header"><div><p class="eyebrow">Content trust</p><h2>Warnings</h2></div></div>
          <div id="content-audit" class="warning-list loading-state">Loading audit...</div>
        </article>
      </section>
    </section>
  `;

  try {
    const [summary, topics, readiness, audit] = await Promise.all([
      getProgressSummary(),
      getTopicProgress(),
      getStudyReadiness(),
      getContentAudit().catch(() => null),
    ]);
    renderReadiness(container, summary, readiness);
    renderWeakTopics(container, topics);
    renderRepairActions(container, summary, topics);
    renderAudit(container, audit);
  } catch (error) {
    showToast(error.message, "error");
    container.querySelector("#readiness-card").innerHTML = `<div class="error-state">${escapeHtml(error.message)}</div>`;
  }
}

function renderReadiness(container, summary, readiness) {
  const host = container.querySelector("#readiness-card");
  const score = summary.exam_readiness_pct || 0;
  const status = score >= 80 ? "Exam ready" : score >= 50 ? "Needs review" : "Insufficient data";
  const tracks = readiness.tracks || [];
  const active = tracks.find((track) => track.attempted_questions || track.question_count) || tracks[0];
  const reasons = [];
  if (!summary.total_attempted) reasons.push("No practice sessions recorded yet.");
  if (summary.total_attempted < 100) reasons.push("Practice coverage is under 100 questions.");
  if (summary.accuracy_pct < 75) reasons.push("Accuracy is below a safe passing buffer.");
  if (active && (active.full_mock_tests || 0) < 1) reasons.push("No full mock exam detected for the selected track.");
  host.className = "panel";
  host.innerHTML = `
    <div class="panel-header"><div><p class="eyebrow">Certification readiness</p><h2>${status}</h2></div><span class="score-pill">${score}%</span></div>
    <div class="simple-meter"><span style="width:${Math.max(0, Math.min(100, score))}%"></span></div>
    <div class="warning-list">
      ${reasons.length ? reasons.map((reason) => `<div class="warning">${escapeHtml(reason)}</div>`).join("") : `<div class="success-state">Current activity does not show major readiness blockers.</div>`}
    </div>
    <div class="action-row"><a class="primary-btn" href="#/practice">Take practice test</a><a class="secondary-btn" href="#/learn">Review lessons</a></div>`;
}

function renderWeakTopics(container, topics) {
  const host = container.querySelector("#weak-topics");
  const weak = (topics.topics || []).filter((topic) => topic.attempted).sort((a, b) => a.accuracy - b.accuracy || b.attempted - a.attempted).slice(0, 6);
  host.className = "panel";
  host.innerHTML = `
    <div class="panel-header"><div><p class="eyebrow">Weak topics</p><h2>Repair queue</h2></div></div>
    ${
      weak.length
        ? `<div class="topic-action-list">${weak
            .map((topic) => `<a class="topic-action-row" href="#/practice?tag=${encodeURIComponent(topic.tag)}"><strong>${escapeHtml(topic.tag)}</strong><span>${topic.accuracy}% accuracy · ${topic.attempted} attempts</span><b>Practice</b></a>`)
            .join("")}</div>`
        : `<div class="empty-state">No weak topics yet. Start answering practice questions.</div>`
    }`;
}

function renderRepairActions(container, summary, topics) {
  const weak = (topics.topics || []).filter((topic) => topic.attempted).sort((a, b) => a.accuracy - b.accuracy)[0];
  const actions = [
    weak ? [`#/practice?tag=${encodeURIComponent(weak.tag)}`, `Practice 10 questions on ${weak.tag}`, `${weak.accuracy}% current accuracy`] : ["#/practice", "Start first practice drill", "Build a baseline"],
    ["#/flashcards", "Review due flashcards", "Convert missed facts into memory"],
    ["#/learn", "Return to Learn", "Fill gaps before retesting"],
  ];
  if (summary.accuracy_pct < 75) actions.unshift(["#/practice", "Retake a full practice test", `${summary.accuracy_pct}% overall accuracy`]);
  const host = container.querySelector("#repair-actions");
  host.className = "action-stack";
  host.innerHTML = actions
    .map(([href, title, body]) => `<a class="action-tile compact" href="${href}"><strong>${escapeHtml(title)}</strong><span>${escapeHtml(body)}</span></a>`)
    .join("");
}

function renderAudit(container, audit) {
  const host = container.querySelector("#content-audit");
  host.className = "warning-list";
  if (!audit) {
    host.innerHTML = `<div class="empty-state">Content audit is unavailable.</div>`;
    return;
  }
  const transcript = audit.transcript_quality || {};
  const practice = audit.practice_quality || {};
  const rows = [
    ["Generated notes", transcript.generated_notes || 0, "Lessons where transcript was replaced with generated notes"],
    ["Missing duration", transcript.duration_missing || 0, "Lessons without reliable duration"],
    ["Empty practice shells", practice.empty_shell || practice.empty || 0, "Practice records that should not appear as exams"],
    ["Mapping review", (audit.mapping_review || []).length, "Courses that may be mapped to the wrong certification"],
    ["Duplicate prompts", (audit.duplicate_prompts || []).length, "Repeated questions to review"],
  ];
  host.innerHTML = rows
    .map(([label, value, detail]) => `<div class="audit-row"><strong>${formatNumber(value)}</strong><span>${escapeHtml(label)}</span><small>${escapeHtml(detail)}</small></div>`)
    .join("");
}
