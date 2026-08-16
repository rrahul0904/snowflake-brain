export const VIEW_ID = "v26-adaptive-readiness";

import {
  escapeHtml,
  getAdaptiveReadiness,
  gradeQuiz,
  recordAttempt,
  startQuiz,
} from "../api.js";
import { activeTrack } from "../ui.js";

const state = {
  trackId: "snowpro-core",
  readiness: null,
  questions: [],
  answers: new Map(),
  confidences: new Map(),
  responseTimes: new Map(),
  openedAt: new Map(),
  index: 0,
  result: null,
};

export default async function mount(container, params = {}) {
  state.trackId = params.track_id || activeTrack();
  state.readiness = await getAdaptiveReadiness({ track_id: state.trackId, refresh: true });
  renderDashboard(container);
}

function renderDashboard(container) {
  const data = state.readiness || {};
  const components = data.components || {};
  const evidence = data.evidence || {};
  const recommendations = data.recommendations || [];
  const score = Number(data.readiness_score || 0);
  container.innerHTML = `<main class="v26-page v26-adaptive-page">
    <section class="v26-page-intro">
      <p class="v26-kicker">Adaptive Intelligence · SnowPro Core</p>
      <h1>What should you study next?</h1>
      <p>Your plan responds to retention, recent accuracy, confidence, pace, coverage, mock evidence, and your exam runway.</p>
      <div class="v26-hero-actions"><button class="v26-btn primary" type="button" data-start-adaptive>Start 15-question adaptive session</button><a class="v26-btn secondary" href="#/progress?track_id=${encodeURIComponent(state.trackId)}">Open full progress</a></div>
    </section>
    <section class="v26-section v26-learning-command" data-adaptive-readiness>
      <div class="v26-section-heading"><div><p class="v26-kicker">Study readiness</p><h2>${Math.round(score)} / 100</h2></div><span>${escapeHtml(String(data.evidence_confidence || "low"))} evidence confidence</span></div>
      <p><strong>${escapeHtml(readinessLabel(data.readiness_band))}</strong> · ${escapeHtml(evidence.statement || "This is a study-readiness indicator, not a probability of passing the SnowPro exam.")}</p>
      <div class="v26-readiness-panel">${componentCard("Mastery", components.mastery)}${componentCard("Retention", components.retention)}${componentCard("Calibration", components.calibration)}${componentCard("Mock", components.mock)}${componentCard("Coverage", components.coverage)}${componentCard("Pace", components.pace)}</div>
      <div class="v26-drill-stats"><div><strong>${Number(evidence.unique_questions_seen || 0)}</strong><span>Unique questions seen</span></div><div><strong>${Number(evidence.srs_due || 0)}</strong><span>Reviews due</span></div><div><strong>${Number(evidence.probable_guess_count || 0)}</strong><span>Probable guesses</span></div><div><strong>${data.runway_days == null ? "—" : Number(data.runway_days)}</strong><span>Days to exam</span></div></div>
    </section>
    <section class="v26-section"><div class="v26-section-heading"><div><p class="v26-kicker">Highest-value next actions</p><h2>Adaptive plan</h2></div><span>${Number(data.recommended_daily_minutes || 0)} min/day suggested</span></div><div class="v26-study-plan-grid">${recommendations.length ? recommendations.slice(0, 6).map(recommendationCard).join("") : `<article><h3>Build more evidence</h3><p>Complete an adaptive session so the engine has enough current evidence to prioritize your next study pass.</p></article>`}</div></section>
    <section class="v26-section"><p class="v26-kicker">How this score works</p><h2>Evidence, not a pass prediction</h2><p>The score is deliberately pulled toward a neutral prior when evidence is sparse. A few lucky correct answers cannot make the dashboard claim you are exam-ready.</p></section>
  </main>`;
  container.querySelector("[data-start-adaptive]")?.addEventListener("click", () => launchAdaptiveSession(container));
}

function componentCard(label, value) {
  const number = Math.max(0, Math.min(100, Number(value || 0)));
  return `<div><span>${escapeHtml(label)}</span><strong>${Math.round(number)}%</strong><progress max="100" value="${number}"></progress></div>`;
}

function recommendationCard(item) {
  const reason = String(item.reason_code || "adaptive_priority").replaceAll("_", " ");
  const focus = [item.domain_id, item.skill_id].filter(Boolean).join(" · ");
  return `<article><span>${escapeHtml(reason)}</span><h3>${escapeHtml(recommendationTitle(item.recommendation_type))}</h3><p>${escapeHtml(item.reason_text || "Prioritized from your current evidence.")}</p>${focus ? `<small>${escapeHtml(focus)}</small>` : ""}</article>`;
}

function recommendationTitle(type) {
  return ({ retention: "Clear retention debt", remediation: "Repair a weak skill", exam_runway: "Use the remaining runway", coverage: "Broaden exam coverage" })[type] || "Next study action";
}

function readinessLabel(band) {
  return ({ strong: "Strong evidence", progressing: "Progressing", needs_focus: "Needs focused repair", building_evidence: "Building evidence", insufficient_evidence: "Insufficient evidence" })[band] || "Building evidence";
}

async function launchAdaptiveSession(container) {
  container.innerHTML = `<main class="v26-page"><div class="v26-loading">Building your highest-value practice set…</div></main>`;
  const payload = await startQuiz({ track_id: state.trackId, count: 15, mode: "adaptive", skill_id: null, domain_id: null });
  state.questions = payload.questions || [];
  if (!state.questions.length) throw new Error("No eligible adaptive questions are available right now");
  state.answers = new Map();
  state.confidences = new Map();
  state.responseTimes = new Map();
  state.openedAt = new Map();
  state.index = 0;
  state.result = null;
  renderQuestion(container);
}

function renderQuestion(container) {
  const question = state.questions[state.index];
  if (!state.openedAt.has(question.id)) state.openedAt.set(question.id, Date.now());
  const selected = state.answers.get(question.id) || [];
  const confidence = Number(state.confidences.get(question.id) || 0);
  container.innerHTML = `<main class="v26-practice-session"><header><a href="#/adaptive?track_id=${encodeURIComponent(state.trackId)}">← Adaptive readiness</a><div><span>Adaptive Practice</span><strong>${state.answers.size}/${state.questions.length} answered</strong></div><button type="button" data-submit>Finish</button></header><div class="v26-practice-session-body"><aside><p>Adaptive</p><div>${state.questions.map((item, index) => `<button class="${index === state.index ? "current" : ""} ${state.answers.has(item.id) ? "done" : ""}" data-jump="${index}">${index + 1}</button>`).join("")}</div></aside><section><p class="v26-kicker">Question ${state.index + 1} of ${state.questions.length}</p><h1>${escapeHtml(question.question)}</h1><fieldset>${(question.options || []).map((option, index) => answerOption(question, option, index, selected)).join("")}</fieldset><div class="v26-confidence-scale"><span>How confident are you?</span><div>${[1,2,3,4,5].map((level) => `<button type="button" class="${confidence === level ? "active" : ""}" data-confidence="${level}" aria-pressed="${confidence === level}">${level}</button>`).join("")}</div><small>1 = guessing · 5 = certain</small></div><footer><button type="button" data-prev ${state.index === 0 ? "disabled" : ""}>← Previous</button><button type="button" data-next ${state.index === state.questions.length - 1 ? "disabled" : ""}>Next →</button></footer></section></div></main>`;
  bindQuestion(container);
}

function answerOption(question, option, index, selected) {
  const type = question.multiple ? "checkbox" : "radio";
  return `<label class="v26-practice-answer ${selected.includes(index) ? "selected" : ""}"><input type="${type}" name="adaptive-answer" value="${index}" ${selected.includes(index) ? "checked" : ""}/><span>${String.fromCharCode(65 + index)}</span><b>${escapeHtml(option)}</b></label>`;
}

function capture(container) {
  const question = state.questions[state.index];
  const inputs = [...container.querySelectorAll("input[name='adaptive-answer']:checked")];
  if (inputs.length) {
    state.answers.set(question.id, inputs.map((input) => Number(input.value)));
    if (!state.responseTimes.has(question.id)) state.responseTimes.set(question.id, Math.max(1, Date.now() - Number(state.openedAt.get(question.id) || Date.now())));
  }
}

function bindQuestion(container) {
  container.querySelectorAll("input[name='adaptive-answer']").forEach((input) => input.addEventListener("change", () => { capture(container); renderQuestion(container); }));
  container.querySelectorAll("[data-confidence]").forEach((button) => button.addEventListener("click", () => { const question = state.questions[state.index]; state.confidences.set(question.id, Number(button.dataset.confidence)); renderQuestion(container); }));
  container.querySelectorAll("[data-jump]").forEach((button) => button.addEventListener("click", () => { capture(container); state.index = Number(button.dataset.jump); renderQuestion(container); }));
  container.querySelector("[data-prev]")?.addEventListener("click", () => { capture(container); state.index -= 1; renderQuestion(container); });
  container.querySelector("[data-next]")?.addEventListener("click", () => { capture(container); state.index += 1; renderQuestion(container); });
  container.querySelector("[data-submit]")?.addEventListener("click", () => submitAdaptive(container));
}

async function submitAdaptive(container) {
  capture(container);
  if (!state.answers.size) throw new Error("Answer at least one question before finishing");
  container.innerHTML = `<main class="v26-page"><div class="v26-loading">Updating your readiness evidence…</div></main>`;
  const answers = [...state.answers.entries()].map(([question_id, selected]) => ({ question_id, selected }));
  const result = await gradeQuiz({ answers });
  const byId = new Map((result.results || []).map((row) => [row.id, row]));
  await Promise.all(answers.map(({ question_id, selected }) => recordAttempt(question_id, {
    selected,
    mode: "adaptive",
    confidence: Number(state.confidences.get(question_id) || 3),
    response_time_ms: Number(state.responseTimes.get(question_id) || 0),
  })));
  state.result = result;
  state.readiness = await getAdaptiveReadiness({ track_id: state.trackId, refresh: true });
  const percent = result.total ? Math.round(Number(result.score || 0) / Number(result.total) * 100) : 0;
  container.innerHTML = `<main class="v26-page"><section class="v26-page-intro centered"><p class="v26-kicker">Adaptive session complete</p><h1>${result.score}/${result.total} correct · ${percent}%</h1><p>Your new attempts, confidence, response time, and retention evidence are now reflected in the adaptive model.</p><div class="v26-hero-actions"><button class="v26-btn primary" type="button" data-view-updated>View updated readiness</button><button class="v26-btn secondary" type="button" data-another>Another adaptive session</button></div></section><section class="v26-section"><div class="v26-source-test-grid">${answers.map(({ question_id }, index) => { const review = byId.get(question_id) || {}; return `<article><span>${review.is_correct ? "Correct" : "Review"}</span><h3>Question ${index + 1}</h3><p>${escapeHtml(review.explanation || "Your attempt has been recorded for future adaptive selection.")}</p></article>`; }).join("")}</div></section></main>`;
  container.querySelector("[data-view-updated]")?.addEventListener("click", () => renderDashboard(container));
  container.querySelector("[data-another]")?.addEventListener("click", () => launchAdaptiveSession(container));
}
