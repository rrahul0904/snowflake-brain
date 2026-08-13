export const VIEW_ID = "v26-practice";

import { escapeHtml, getMockConfig, getPracticeTests, gradeQuiz, recordAttempt, startMockSession, startQuiz } from "../api.js";
import { activeTrack } from "../ui.js";

const state = { questions: [], answers: new Map(), index: 0, mode: "", trackId: "snowpro-core", skillId: "", domainId: "", submitted: false, result: null };

export default async function mount(container, params = {}) {
  state.trackId = params.track_id || activeTrack();
  if (["diagnostic", "drill"].includes(params.mode || "")) return launch(container, params);
  return landing(container);
}

async function landing(container) {
  const [config, current, legacy] = await Promise.all([
    getMockConfig({ track_id: state.trackId }),
    getPracticeTests({ track_id: state.trackId, source_kind: "source" }).catch(() => ({ tests: [] })),
    getPracticeTests({ track_id: state.trackId, include_legacy: true, source_kind: "legacy" }).catch(() => ({ tests: [] })),
  ]);
  const quick = config.quick_mock || {};
  const full = config.full_mock || {};
  container.innerHTML = `<main class="v26-page v26-practice-page"><section class="v26-page-intro centered"><p class="v26-kicker">SnowPro Core · COF-C03</p><h1>Practice</h1><p>Find your gaps, repair a task, or rehearse the timed exam experience.</p></section><section class="v26-section"><div class="v26-practice-grid">${card("Diagnostic", "Find weak areas", "A balanced untimed baseline across all current exam domains.", "25 questions", `#/practice?track_id=${state.trackId}&mode=diagnostic&count=25`, true)}${card("Targeted Drill", "Repair weak tasks", "Focused practice prioritizing the selected task, domain, or your lowest evidence.", "15 questions", `#/practice?track_id=${state.trackId}&mode=drill&count=15`)}${card("Quick Mock", "Timed readiness check", "The same persisted exam player as the full sitting, in a shorter format.", `${quick.question_count || 30} questions · ${quick.time_limit_minutes || 45} min`, `#/mock/start?track_id=${state.trackId}&type=quick-mock`)}${card("Full Mock", "Complete simulation", "Flags, free navigation, autosave, refresh/resume, server timer, and post-exam review.", `${full.question_count || 100} questions · ${full.time_limit_minutes || 120} min`, `#/mock/start?track_id=${state.trackId}&type=full-mock`, false, true)}</div></section>${sourceSection(current.tests || [], legacy.tests || [])}</main>`;
  bindSource(container);
}

function card(kicker, title, body, meta, href, featured = false, full = false) { return `<a class="v26-practice-card ${featured ? "featured" : ""} ${full ? "full" : ""}" href="${href}"><span>${kicker}</span><h2>${title}</h2><p>${body}</p><div><b>${meta}</b><em>Start →</em></div></a>`; }

function sourceSection(current, legacy) {
  if (!current.length && !legacy.length) return "";
  return `<section class="v26-section v26-source-practice"><div class="v26-section-heading"><p class="v26-kicker">Source Practice Exams</p><h2>Fixed imported sittings</h2></div>${current.length ? `<div class="v26-source-test-grid">${current.map((test) => sourceCard(test, false)).join("")}</div>` : `<p class="v26-empty-copy">No current COF-C03 source exams are imported.</p>`}${legacy.length ? `<details class="v26-legacy-tests"><summary>Legacy Practice · COF-C02 <span>${legacy.length}</span></summary><p>Legacy material is kept separate and does not contribute to current COF-C03 readiness.</p><div class="v26-source-test-grid">${legacy.map((test) => sourceCard(test, true)).join("")}</div></details>` : ""}</section>`;
}
function sourceCard(test, legacy) { return `<article><span>${legacy ? "Legacy" : "COF-C03"}</span><h3>${escapeHtml(test.title || "Practice Exam")}</h3><p>${test.actual_question_count || test.question_count || 0} questions</p><button type="button" data-source-test="${escapeHtml(test.id)}">Start Exam →</button></article>`; }
function bindSource(container) { container.querySelectorAll("[data-source-test]").forEach((button) => button.addEventListener("click", async () => { button.disabled = true; try { const session = await startMockSession({ track_id: state.trackId, mode: "source-exam", practice_test_id: button.dataset.sourceTest, randomize_options: true }); window.location.hash = `#/mock/session?session_id=${session.session_id}`; } catch (error) { button.disabled = false; button.textContent = error.message || "Unable to start"; } })); }

async function launch(container, params) {
  const mode = params.mode || "drill";
  state.mode = mode;
  state.skillId = params.skill_id || "";
  state.domainId = params.domain_id || "";
  state.index = 0;
  state.answers = new Map();
  state.submitted = false;
  state.result = null;
  const count = Number(params.count || (mode === "diagnostic" ? 25 : 15));
  container.innerHTML = `<main class="v26-page"><div class="v26-loading">Preparing ${mode === "diagnostic" ? "diagnostic" : "drill"}…</div></main>`;
  const data = await startQuiz({ track_id: state.trackId, count, mode, skill_id: state.skillId || null, domain_id: state.domainId || null });
  state.questions = data.questions || [];
  if (!state.questions.length) throw new Error("No eligible questions are available for this practice session");
  drawSession(container);
}

function drawSession(container) {
  const q = state.questions[state.index];
  const selected = state.answers.get(q.id) || [];
  const answered = state.answers.size;
  container.innerHTML = `<main class="v26-practice-session"><header><a href="#/practice?track_id=${encodeURIComponent(state.trackId)}">← Practice</a><div><span>${state.mode === "diagnostic" ? "Diagnostic Test" : "Targeted Drill"}</span><strong>${answered}/${state.questions.length} answered</strong></div><button type="button" data-submit>Finish</button></header><div class="v26-practice-session-body"><aside><p>${state.mode === "diagnostic" ? "Diagnostic" : "Drill"}</p><div>${state.questions.map((item, index) => `<button class="${index === state.index ? "current" : ""} ${state.answers.has(item.id) ? "done" : ""}" data-jump="${index}">${index + 1}</button>`).join("")}</div></aside><section><p class="v26-kicker">Question ${state.index + 1} of ${state.questions.length}</p><h1>${escapeHtml(q.question)}</h1><fieldset>${(q.options || []).map((option, index) => answer(q, option, index, selected)).join("")}</fieldset><footer><button type="button" data-prev ${state.index === 0 ? "disabled" : ""}>← Previous</button><button type="button" data-next ${state.index === state.questions.length - 1 ? "disabled" : ""}>Next →</button></footer></section></div></main>`;
  bindSession(container);
}

function answer(q, option, index, selected) { const type = q.multiple ? "checkbox" : "radio"; return `<label class="v26-practice-answer ${selected.includes(index) ? "selected" : ""}"><input type="${type}" name="practice-answer" value="${index}" ${selected.includes(index) ? "checked" : ""}/><span>${String.fromCharCode(65 + index)}</span><b>${escapeHtml(option)}</b></label>`; }

function bindSession(container) {
  container.querySelectorAll("[data-jump]").forEach((button) => button.addEventListener("click", () => { capture(container); state.index = Number(button.dataset.jump); drawSession(container); }));
  container.querySelectorAll("input[name='practice-answer']").forEach((input) => input.addEventListener("change", () => { capture(container); drawSession(container); }));
  container.querySelector("[data-prev]")?.addEventListener("click", () => { capture(container); state.index = Math.max(0, state.index - 1); drawSession(container); });
  container.querySelector("[data-next]")?.addEventListener("click", () => { capture(container); state.index = Math.min(state.questions.length - 1, state.index + 1); drawSession(container); });
  container.querySelector("[data-submit]")?.addEventListener("click", () => submit(container));
}

function capture(container) { const q = state.questions[state.index]; let selected = [...container.querySelectorAll("input[name='practice-answer']:checked")].map((input) => Number(input.value)); if (!q.multiple && selected.length > 1) selected = selected.slice(-1); selected.length ? state.answers.set(q.id, selected) : state.answers.delete(q.id); }

async function submit(container) {
  if (state.submitted) return;
  capture(container);
  state.submitted = true;
  const payload = state.questions.map((q) => ({ question_id: q.id, selected: state.answers.get(q.id) || [] }));
  const result = await gradeQuiz({ answers: payload });
  state.result = result;
  for (const row of result.results || []) { await recordAttempt(row.id || row.question_id, { selected: row.selected || [], correct: Boolean(row.is_correct), mode: state.mode }).catch(() => {}); }
  renderResult(container, result);
}

function renderResult(container, result) {
  const total = Math.max(1, result.total || state.questions.length);
  const score = result.score || 0;
  const percent = Math.round(score / total * 100);
  container.innerHTML = `<main class="v26-page v26-practice-result"><a class="v26-back" href="#/practice?track_id=${encodeURIComponent(state.trackId)}">← Practice</a><header class="v26-page-intro centered"><p class="v26-kicker">${state.mode === "diagnostic" ? "Diagnostic Result" : "Drill Result"}</p><h1>${percent}%</h1><p>${score}/${total} correct. Review the explanations below, then continue with the task lessons that need another pass.</p></header><section class="v26-review-list">${(result.results || []).map((row, index) => review(row, index)).join("")}</section><div class="v26-result-actions"><a class="v26-btn primary" href="#/progress?track_id=${encodeURIComponent(state.trackId)}">Open Progress</a><a class="v26-btn secondary" href="#/practice?track_id=${encodeURIComponent(state.trackId)}&mode=${state.mode}">Try another set</a></div></main>`;
}

function review(row, index) { const options = row.options || []; const selected = (row.selected || []).map((i) => options[i]).filter(Boolean).join("; ") || "No answer"; const correct = (row.correct || []).map((i) => options[i]).filter(Boolean).join("; ") || "Answer unavailable"; return `<details class="v26-review-card ${row.is_correct ? "correct" : "incorrect"}"><summary><span>${row.is_correct ? "✓" : "×"}</span><div><small>Question ${index + 1}</small><strong>${escapeHtml(row.question || "")}</strong></div></summary><div class="v26-review-body"><p><b>Your answer</b>${escapeHtml(selected)}</p><p><b>Correct answer</b>${escapeHtml(correct)}</p>${row.explanation ? `<p><b>Explanation</b>${escapeHtml(row.explanation)}</p>` : ""}</div></details>`; }
