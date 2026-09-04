export const VIEW_ID = "v26-adaptive-readiness";

import {
  escapeHtml,
  getAdaptiveReadiness,
  gradeQuiz,
  recordAttempt,
  startQuiz,
} from "../api.js";
import { activeTrack } from "../ui.js";
import { evidenceNotice, readinessRadar, readinessRing } from "../components/learning-widgets.js";

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
  const primary = recommendations[0] || null;
  container.innerHTML = `<main class="v26-page v26-adaptive-page">
    <section class="v26-page-intro">
      <p class="v26-kicker">Adaptive Readiness · SnowPro Core</p>
      <h1>What should you study next?</h1>
      <p>Turn retention, accuracy, confidence, pace, coverage, mock evidence, and exam runway into a focused next action.</p>
      <div class="v26-hero-actions"><button class="v26-btn primary" type="button" data-start-adaptive>Start 15-question adaptive session</button><a class="v26-btn secondary" href="#/progress?track_id=${encodeURIComponent(state.trackId)}">Open full progress</a></div>
      ${evidenceNotice(evidence.statement || "Readiness is a Snowflake Brain study signal, not a probability of passing the official exam.")}
    </section>
    <section class="v26-adaptive-overview">
      <article class="v26-adaptive-signal"><p class="v26-kicker">Study readiness</p><h2>${score ? `${Math.round(score)} / 100` : "Building evidence"}</h2><p><strong>${escapeHtml(readinessLabel(data.readiness_band))}</strong> · ${escapeHtml(String(data.evidence_confidence || "low"))} evidence confidence.</p>${readinessRing(score, "Readiness score")}<div class="v26-component-bars">${componentBar("Mastery", components.mastery)}${componentBar("Retention", components.retention)}${componentBar("Calibration", components.calibration)}${componentBar("Mock", components.mock)}${componentBar("Coverage", components.coverage)}${componentBar("Pace", components.pace)}</div></article>
      ${readinessRadar(components)}
    </section>
    <section class="v26-section">
      <div class="v26-section-heading"><div><p class="v26-kicker">Next best study action</p><h2>${escapeHtml(primary ? recommendationTitle(primary.recommendation_type) : "Build enough evidence to prioritize confidently")}</h2><p>${escapeHtml(primary?.reason_text || "Complete an adaptive session or targeted drill so the engine can prioritize your next repair with current evidence.")}</p></div><span>${Number(data.recommended_daily_minutes || 0) ? `${Number(data.recommended_daily_minutes)} min/day suggested` : "No schedule estimate yet"}</span></div>
      <div class="v26-drill-stats"><div><strong>${Number(evidence.unique_questions_seen || 0)}</strong><span>Unique questions seen</span></div><div><strong>${Number(evidence.srs_due || 0)}</strong><span>Reviews due</span></div><div><strong>${Number(evidence.probable_guess_count || 0)}</strong><span>Probable guesses</span></div><div><strong>${data.runway_days == null ? "—" : Number(data.runway_days)}</strong><span>Days to exam</span></div></div>
    </section>
    <section class="v26-section"><div class="v26-section-heading"><div><p class="v26-kicker">Highest-value actions</p><h2>Adaptive plan</h2></div></div><div class="v26-study-plan-grid">${recommendations.length ? recommendations.slice(0, 6).map(recommendationCard).join("") : `<article><span>building evidence</span><h3>Complete an adaptive session</h3><p>Current evidence is not yet strong enough to produce a precise task priority.</p></article>`}</div></section>
    <section class="v26-section"><p class="v26-kicker">How this score works</p><h2>Evidence, not an exam prediction.</h2><p>The score is deliberately pulled toward a neutral prior when evidence is sparse. A few lucky correct answers cannot make the interface claim you are exam-ready.</p></section>
  </main>`;
  container.querySelector("[data-start-adaptive]")?.addEventListener("click", () => launchAdaptiveSession(container));
}

function componentBar(label, value) {
  const number = Math.max(0, Math.min(100, Number(value || 0)));
  return `<div><span>${escapeHtml(label)}</span><progress max="100" value="${number}" aria-label="${escapeHtml(label)} ${Math.round(number)} percent"></progress><strong>${Math.round(number)}</strong></div>`;
}

function recommendationCard(item) {
  const reason = String(item.reason_code || "adaptive_priority").replaceAll("_", " ");
  const focus = [item.domain_id, item.skill_id].filter(Boolean).join(" · ");
  const href = recommendationHref(item);
  return `<article><span>${escapeHtml(reason)}</span><h3>${escapeHtml(recommendationTitle(item.recommendation_type))}</h3><p>${escapeHtml(item.reason_text || "Prioritized from your current evidence.")}</p>${focus ? `<small>${escapeHtml(focus)}</small>` : ""}${href ? `<a href="${href}">Start action →</a>` : ""}</article>`;
}

function recommendationHref(item) {
  const id = encodeURIComponent(state.trackId);
  if (item.skill_id) return `#/skill?track_id=${id}&skill_id=${encodeURIComponent(item.skill_id)}`;
  if (item.domain_id) return `#/practice?track_id=${id}&mode=drill&domain_id=${encodeURIComponent(item.domain_id)}`;
  if (item.recommendation_type === "retention") return `#/practice?track_id=${id}&mode=srs`;
  if (item.recommendation_type === "coverage") return `#/curriculum?track_id=${id}`;
  return `#/practice?track_id=${id}&mode=drill`;
}

function recommendationTitle(type) {
  return ({ retention: "Clear retention debt", remediation: "Repair a weak skill", exam_runway: "Use the remaining runway", coverage: "Broaden exam coverage" })[type] || "Next study action";
}

function readinessLabel(band) {
  return ({ strong: "Ready", progressing: "Almost Ready", needs_focus: "Needs Focus", building_evidence: "Building evidence", insufficient_evidence: "Building evidence" })[band] || "Building evidence";
}

async function launchAdaptiveSession(container) {
  container.innerHTML = `<main class="v26-page"><div class="v26-loading" aria-live="polite">Building your highest-value practice set…</div></main>`;
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
  container.innerHTML = `<main class="v26-practice-session"><header><a href="#/adaptive?track_id=${encodeURIComponent(state.trackId)}">← Adaptive readiness</a><div><span>Adaptive Practice</span><strong>${state.answers.size}/${state.questions.length} answered</strong></div><button type="button" data-submit>Finish</button></header><div class="v26-practice-session-body"><aside><p>Adaptive</p><div>${state.questions.map((item, index) => `<button class="${index === state.index ? "current" : ""} ${state.answers.has(item.id) ? "done" : ""}" data-jump="${index}" aria-label="Question ${index + 1}${state.answers.has(item.id) ? ", answered" : ""}">${index + 1}</button>`).join("")}</div></aside><section><p class="v26-kicker">Question ${state.index + 1} of ${state.questions.length}</p><h1>${escapeHtml(question.question)}</h1><fieldset><legend class="sr-only">Choose ${question.multiple ? "all correct answers" : "one answer"}</legend>${(question.options || []).map((option, index) => answerOption(question, option, index, selected)).join("")}</fieldset><div class="v26-confidence-scale"><span>How confident are you?</span><div>${[[1,"Low"],[3,"Medium"],[5,"High"]].map(([level,label]) => `<button type="button" class="${confidence === level ? "active" : ""}" data-confidence="${level}" aria-pressed="${confidence === level}">${label}</button>`).join("")}</div><small>Confidence is recorded with your answer to identify overconfidence and uncertainty patterns.</small></div><footer><button type="button" data-prev ${state.index === 0 ? "disabled" : ""}>← Previous</button><button type="button" data-next ${state.index === state.questions.length - 1 ? "disabled" : ""}>Next →</button></footer></section></div></main>`;
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
  container.innerHTML = `<main class="v26-page"><div class="v26-loading" aria-live="polite">Updating your readiness evidence…</div></main>`;
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
