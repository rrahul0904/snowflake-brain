export const VIEW_ID = "production-mock-exam";

import {
  escapeHtml,
  getActiveMockSession,
  getMockConfig,
  getMockHistory,
  getMockResult,
  getMockSession,
  getPracticeTests,
  saveMockAnswer,
  saveMockFlag,
  startMockSession,
  submitMockSession,
} from "../api.js?v=20260812-v25-production-mock";
import { activeTrack, emptyState, skeleton } from "../ui.js?v=20260731-v21-editorial-replica";
import { showToast } from "../components/toast.js?v=20260731-v21-editorial-replica";

const state = {
  session: null,
  index: 0,
  filter: "all",
  reviewFilter: "all",
  timer: null,
  serverLoadedAt: 0,
  serverRemaining: 0,
  pending: new Map(),
  warned: new Set(),
  submitting: false,
};

export function unmount() {
  if (state.timer) clearInterval(state.timer);
  state.timer = null;
  document.body.classList.remove("mock-player-active");
}

export default async function mount(container, params = {}) {
  unmount();
  const path = (window.location.hash || "#/mock").split("?")[0];
  container.innerHTML = skeleton("Loading SnowPro practice...");
  try {
    if (path === "#/mock/start") return renderStart(container, params);
    if (path === "#/mock/session") return renderPlayer(container, Number(params.session_id || 0));
    if (path === "#/mock/result") return renderResult(container, Number(params.session_id || 0));
    if (path === "#/mock/history") return renderHistory(container);
    return renderLanding(container);
  } catch (error) {
    container.innerHTML = emptyState("Mock exam unavailable", error.message, `<a class="mock-button primary" href="#/mock">Return to Practice</a>`);
  }
}

async function renderLanding(container) {
  const trackId = activeTrack();
  const [config, active, current, legacy, history] = await Promise.all([
    getMockConfig({ track_id: trackId }),
    getActiveMockSession({ track_id: trackId }),
    getPracticeTests({ track_id: trackId, source_kind: "source" }),
    getPracticeTests({ track_id: trackId, include_legacy: true, source_kind: "legacy" }),
    getMockHistory({ track_id: trackId }),
  ]);
  const quick = config.quick_mock;
  const full = config.full_mock;
  const currentTests = current.tests || [];
  const legacyTests = legacy.tests || [];
  container.innerHTML = `<main class="mock-page mock-landing replica-enter">
    <header class="mock-hero">
      <div>
        <p class="mock-kicker">SnowPro Core · COF-C03</p>
        <h1>Mock <em>Exam</em></h1>
        <p>Simulate a focused certification sitting using questions mapped to the current five-domain SnowPro Core blueprint.</p>
        <div class="mock-hero-actions">
          <a class="mock-button primary" href="#/mock/start?type=quick-mock">Start Quick Mock</a>
          <a class="mock-button secondary" href="#/mock/start?type=full-mock">Choose Full Sitting</a>
        </div>
      </div>
      <div class="mock-threshold" aria-label="Practice readiness threshold">
        <span>Practice threshold</span><strong>${config.pass_scaled_score}</strong><small>/ ${config.score_scale}</small>
        <p>Readiness estimate, not Snowflake's confidential production score.</p>
      </div>
    </header>
    ${active.session ? `<section class="mock-resume"><div><span>Active sitting</span><strong>${escapeHtml(modeName(active.session.mode))}</strong><small>${formatClock(active.session.remaining_seconds)} remaining</small></div><a class="mock-button primary" href="#/mock/session?session_id=${active.session.session_id}">Resume Exam</a></section>` : ""}
    <section class="mock-section">
      <div class="mock-section-head"><div><p class="mock-kicker">Choose a sitting</p><h2>Practice at the right depth.</h2></div><p>Both generated modes use the same source-first selection policy and blueprint weighting.</p></div>
      <div class="mock-sitting-grid">
        ${sittingCard("Quick Mock", "A shorter readiness check between study sessions.", quick, "quick-mock")}
        ${sittingCard("Full Mock", "The complete Snowflake Brain certification simulation.", full, "full-mock", true)}
      </div>
    </section>
    <section class="mock-section">
      <div class="mock-section-head"><div><p class="mock-kicker">Exam format</p><h2>Built from the blueprint.</h2></div></div>
      <div class="mock-fact-grid">
        ${fact("5", "Domains")}${fact(String(config.task_count), "Task statements")}${fact(String(config.pass_scaled_score), "Practice threshold")}${fact(String(config.score_scale), "Score scale")}
      </div>
      <div class="mock-domain-list">${config.domains.map((domain) => `<div><strong>${domain.weight}%</strong><span>${escapeHtml(domain.title)}</span><small>${domain.task_count} tasks</small></div>`).join("")}</div>
    </section>
    <section class="mock-section mock-before">
      <div><p class="mock-kicker">Before you start</p><h2>Timed means timed.</h2></div>
      <ul><li>Questions and option order may be randomized.</li><li>Multi-select answers require exact set equality.</li><li>Flag questions and navigate freely.</li><li>The timer cannot be paused and survives refresh.</li><li>The sitting submits automatically at zero.</li><li>Explanations appear only after submission.</li></ul>
    </section>
    ${sourceLibrary(currentTests, legacyTests, config.question_bank)}
    ${historyPreview(history.history || [])}
    <section class="mock-section mock-next"><div><p class="mock-kicker">Not ready?</p><h2>Build evidence first.</h2></div><div class="mock-hero-actions"><a class="mock-button secondary" href="#/practice?track_id=${encodeURIComponent(trackId)}&mode=diagnostic">Take Diagnostic</a><a class="mock-button secondary" href="#/curriculum?track_id=${encodeURIComponent(trackId)}">Review Curriculum</a></div></section>
  </main>`;
  bindSourceStarts(container, trackId);
}

function sittingCard(title, description, setting, type, featured = false) {
  return `<article class="mock-sitting ${featured ? "featured" : ""}"><div><span>${featured ? "Complete simulation" : "Readiness check"}</span><h3>${title}</h3><p>${description}</p></div><dl><div><dt>Questions</dt><dd>${setting.question_count}</dd></div><div><dt>Minutes</dt><dd>${setting.time_limit_minutes}</dd></div></dl><a class="mock-button ${featured ? "primary" : "secondary"}" href="#/mock/start?type=${type}">Choose ${title}</a></article>`;
}

function fact(value, label) { return `<div class="mock-fact"><strong>${escapeHtml(value)}</strong><span>${escapeHtml(label)}</span></div>`; }

function sourceLibrary(current, legacy, counts) {
  const currentBody = current.length ? current.map(testCard).join("") : `<div class="mock-empty"><strong>No COF-C03 source bank imported</strong><p>The simulator is ready for the normalized bank. Run the importer when the user-provided JSON is available; generated mocks continue to use curated and canonical questions.</p></div>`;
  const legacyBody = legacy.length ? legacy.map((test) => testCard(test, true)).join("") : `<p class="mock-muted">No COF-C02 legacy bank is installed.</p>`;
  return `<section class="mock-section"><div class="mock-section-head"><div><p class="mock-kicker">Source practice exams</p><h2>Fixed imported sittings.</h2></div><p>${counts.source_questions || 0} current source questions · ${counts.legacy_questions || 0} legacy questions</p></div><div class="mock-source-grid">${currentBody}</div><details class="mock-legacy"><summary>Legacy practice · COF-C02</summary><p>Legacy material — excluded from COF-C03 readiness and generated mocks.</p><div class="mock-source-grid">${legacyBody}</div></details></section>`;
}

function testCard(test, legacy = false) {
  return `<article class="mock-source-card"><span>${legacy ? "Legacy source exam" : "COF-C03 source exam"}</span><h3>${escapeHtml(test.title)}</h3><p>${test.actual_question_count || test.question_count} questions</p><button class="mock-button secondary" type="button" data-source-test="${escapeHtml(test.id)}">Start</button></article>`;
}

function historyPreview(rows) {
  if (!rows.length) return "";
  return `<section class="mock-section"><div class="mock-section-head"><div><p class="mock-kicker">Recent evidence</p><h2>Mock history.</h2></div><a href="#/mock/history">View all →</a></div><div class="mock-history-list">${rows.slice(0, 3).map(historyRow).join("")}</div></section>`;
}

function historyRow(row) {
  return `<a class="mock-history-row" href="#/mock/result?session_id=${row.session_id}"><time>${formatDate(row.finished_at)}</time><strong>${escapeHtml(modeName(row.mode))}</strong><b>${row.scaled_score}</b><span class="${row.ready ? "ready" : "review"}">${row.ready ? "Ready" : "Needs review"}</span><small>${formatMinutes(row.elapsed_seconds)}</small><small>${escapeHtml(row.weakest_domain?.title || "No domain evidence")}</small></a>`;
}

function bindSourceStarts(container, trackId) {
  container.querySelectorAll("[data-source-test]").forEach((button) => button.addEventListener("click", async () => {
    button.disabled = true;
    try {
      const session = await startMockSession({ track_id: trackId, mode: "source-exam", practice_test_id: button.dataset.sourceTest, randomize_options: true });
      window.location.hash = `#/mock/session?session_id=${session.session_id}`;
    } catch (error) { showToast(error.message, "error"); button.disabled = false; }
  }));
}

async function renderStart(container, params) {
  const trackId = activeTrack();
  const config = await getMockConfig({ track_id: trackId });
  const initial = params.type === "full-mock" ? "full-mock" : "quick-mock";
  container.innerHTML = `<main class="mock-page mock-start replica-enter"><a class="mock-back" href="#/mock">← Practice</a><header class="mock-page-heading"><p class="mock-kicker">SnowPro Core · COF-C03</p><h1>Choose Your <em>Sitting</em></h1><p>Confirm the format before the persistent timer begins.</p></header><section class="mock-choice" role="radiogroup" aria-label="Mock exam length">${choice(config.quick_mock, "quick-mock", "Quick Mock", initial)}${choice(config.full_mock, "full-mock", "Full Mock", initial)}</section><section class="mock-start-details"><div><p class="mock-kicker">Exam format</p><dl data-sitting-facts></dl></div><div><p class="mock-kicker">Domain weights</p><div class="mock-weight-bars">${config.domains.map((domain) => `<div><span>${escapeHtml(domain.title)}</span><i style="--weight:${domain.weight}%"></i><strong>${domain.weight}%</strong></div>`).join("")}</div></div></section><section class="mock-instructions"><p class="mock-kicker">Before you start</p><ul><li>Answers and review flags save as you work.</li><li>You can move freely between questions.</li><li>Refreshing resumes the same sitting and deadline.</li><li>Explanations remain hidden until submission.</li></ul></section><div class="mock-start-action"><p>${escapeHtml(config.scoring_note)}</p><button class="mock-button primary" type="button" data-start-exam>Start Exam</button></div></main>`;
  let selected = initial;
  const update = () => {
    container.querySelectorAll("[data-sitting]").forEach((node) => node.classList.toggle("selected", node.dataset.sitting === selected));
    const setting = selected === "full-mock" ? config.full_mock : config.quick_mock;
    container.querySelector("[data-sitting-facts]").innerHTML = `<div><dt>Sitting</dt><dd>${escapeHtml(setting.label)}</dd></div><div><dt>Questions</dt><dd>${setting.question_count}</dd></div><div><dt>Time limit</dt><dd>${setting.time_limit_minutes} minutes</dd></div><div><dt>Question types</dt><dd>Single and multi-select</dd></div><div><dt>Pass threshold</dt><dd>${config.pass_scaled_score} / ${config.score_scale}</dd></div>`;
  };
  container.querySelectorAll("[data-sitting]").forEach((node) => node.addEventListener("click", () => { selected = node.dataset.sitting; node.querySelector("input").checked = true; update(); }));
  container.querySelector("[data-start-exam]").addEventListener("click", async (event) => {
    event.currentTarget.disabled = true;
    event.currentTarget.textContent = "Preparing sitting…";
    try {
      const session = await startMockSession({ track_id: trackId, mode: selected });
      window.location.hash = `#/mock/session?session_id=${session.session_id}`;
    } catch (error) { showToast(error.message, "error"); event.currentTarget.disabled = false; event.currentTarget.textContent = "Start Exam"; }
  });
  update();
}

function choice(setting, mode, label, selected) {
  return `<label class="mock-choice-card ${selected === mode ? "selected" : ""}" data-sitting="${mode}"><input type="radio" name="sitting" value="${mode}" ${selected === mode ? "checked" : ""}/><span>${mode === "full-mock" ? "Complete simulation" : "Readiness check"}</span><strong>${label}</strong><p>${setting.question_count} questions · ${setting.time_limit_minutes} minutes</p><small>${escapeHtml(setting.label)}</small></label>`;
}

async function renderPlayer(container, sessionId) {
  if (!sessionId) throw new Error("A session ID is required.");
  const session = await getMockSession(sessionId);
  if (session.status !== "in_progress") { window.location.hash = `#/mock/result?session_id=${sessionId}`; return; }
  state.session = session;
  state.index = 0;
  state.filter = "all";
  state.serverLoadedAt = Date.now();
  state.serverRemaining = session.remaining_seconds;
  state.pending.clear();
  state.warned.clear();
  document.body.classList.add("mock-player-active");
  drawPlayer(container);
  startTimer(container);
}

function drawPlayer(container) {
  const session = state.session;
  const questions = session.questions;
  const visible = filteredQuestions();
  const current = questions[state.index] || questions[0];
  const selected = current.selected || [];
  const answered = questions.filter((q) => q.selected?.length).length;
  const flagged = questions.filter((q) => q.flagged).length;
  container.innerHTML = `<section class="mock-player" aria-label="Mock exam player"><header class="mock-player-bar"><div><span>SnowPro Core</span><strong>COF-C03 · ${escapeHtml(modeName(session.mode))}</strong></div><div class="mock-player-time"><span>Time remaining</span><strong id="mock-timer" aria-live="off">${formatClock(remaining())}</strong></div><button class="mock-button primary" type="button" data-submit>Submit</button></header><div class="mock-player-body"><aside class="mock-navigator" id="mock-navigator"><div class="mock-nav-head"><div><span>Questions</span><strong>${answered}/${questions.length} answered</strong></div><button type="button" class="mock-nav-close" data-close-nav aria-label="Close question navigator">×</button></div><div class="mock-filters" role="group" aria-label="Question filters">${filterButton("all", "All", questions.length)}${filterButton("unanswered", "Unanswered", questions.length - answered)}${filterButton("flagged", "Flagged", flagged)}</div><div class="mock-question-map">${visible.map((question) => questionButton(question, questions.indexOf(question))).join("") || `<p>No questions match this filter.</p>`}</div><div class="mock-nav-legend"><span><i class="answered"></i>Answered</span><span><i class="flagged"></i>Flagged</span><span><i></i>Unanswered</span></div><button class="mock-button primary wide" type="button" data-submit>Review & Submit</button></aside><main class="mock-question-stage"><div class="mock-question-top"><button class="mock-button secondary mock-nav-open" type="button" data-open-nav>Questions</button><div><span>Question ${current.position} of ${questions.length}</span><strong>${escapeHtml(domainLabel(current.domain_id))} · ${escapeHtml(taskLabel(current.skill_id))}</strong></div><button class="mock-flag ${current.flagged ? "active" : ""}" type="button" data-flag aria-pressed="${current.flagged}">${current.flagged ? "Flagged for review" : "Flag for review"}</button></div><article class="mock-question"><div class="mock-question-kind">${current.multiple ? "Select all that apply." : "Select one answer."}</div><h1>${escapeHtml(current.question)}</h1><fieldset><legend class="sr-only">Answer choices</legend>${current.options.map((option, index) => answerChoice(current, option, index, selected)).join("")}</fieldset><div class="mock-save-state" data-save-state aria-live="polite">Answers save automatically.</div></article><footer class="mock-question-actions"><button class="mock-button secondary" type="button" data-prev ${state.index === 0 ? "disabled" : ""}>Previous</button><button class="mock-button primary" type="button" data-next ${state.index === questions.length - 1 ? "disabled" : ""}>Next</button></footer></main></div><dialog class="mock-dialog" data-submit-dialog><div class="mock-dialog-content"><p class="mock-kicker">Finish sitting</p><h2>Submit exam?</h2><div class="mock-submit-counts"><span><strong>${answered}</strong>Answered</span><span><strong>${questions.length - answered}</strong>Unanswered</span><span><strong>${flagged}</strong>Flagged</span></div>${questions.length - answered ? `<p class="mock-warning">Unanswered questions will be scored as incorrect.</p>` : ""}<div class="mock-dialog-actions"><button class="mock-button secondary" type="button" data-cancel-submit>Continue Exam</button><button class="mock-button primary" type="button" data-confirm-submit>Submit Exam</button></div></div></dialog></section>`;
  bindPlayer(container);
}

function filteredQuestions() {
  const questions = state.session.questions;
  if (state.filter === "unanswered") return questions.filter((q) => !q.selected?.length);
  if (state.filter === "flagged") return questions.filter((q) => q.flagged);
  return questions;
}

function filterButton(value, label, count) { return `<button type="button" class="${state.filter === value ? "active" : ""}" data-filter="${value}">${label}<span>${count}</span></button>`; }
function questionButton(question, index) { const classes = [index === state.index ? "current" : "", question.selected?.length ? "answered" : "", question.flagged ? "flagged" : ""].filter(Boolean).join(" "); return `<button type="button" class="${classes}" data-question-index="${index}" aria-label="Question ${question.position}${question.selected?.length ? ", answered" : ", unanswered"}${question.flagged ? ", flagged" : ""}"><span>${question.position}</span><small>${question.selected?.length ? "Answered" : "Open"}${question.flagged ? " · Flagged" : ""}</small></button>`; }
function answerChoice(question, option, index, selected) { const type = question.multiple ? "checkbox" : "radio"; const checked = selected.includes(index); return `<label class="mock-answer ${checked ? "selected" : ""}"><input type="${type}" name="answer" value="${index}" ${checked ? "checked" : ""}/><span class="mock-letter">${String.fromCharCode(65 + index)}</span><span>${escapeHtml(option)}</span></label>`; }

function bindPlayer(container) {
  container.querySelectorAll("[data-question-index]").forEach((button) => button.addEventListener("click", () => { state.index = Number(button.dataset.questionIndex); drawPlayer(container); }));
  container.querySelectorAll("[data-filter]").forEach((button) => button.addEventListener("click", () => { state.filter = button.dataset.filter; drawPlayer(container); }));
  container.querySelectorAll("input[name='answer']").forEach((input) => input.addEventListener("change", () => persistCurrentAnswer(container)));
  container.querySelector("[data-prev]")?.addEventListener("click", () => { state.index = Math.max(0, state.index - 1); drawPlayer(container); });
  container.querySelector("[data-next]")?.addEventListener("click", () => { state.index = Math.min(state.session.questions.length - 1, state.index + 1); drawPlayer(container); });
  container.querySelector("[data-flag]")?.addEventListener("click", () => toggleFlag(container));
  container.querySelectorAll("[data-submit]").forEach((button) => button.addEventListener("click", () => openSubmit(container)));
  container.querySelector("[data-cancel-submit]")?.addEventListener("click", () => container.querySelector("[data-submit-dialog]")?.close("cancel"));
  container.querySelector("[data-confirm-submit]")?.addEventListener("click", () => {
    container.querySelector("[data-submit-dialog]")?.close("submit");
    finishExam(container, "learner");
  });
  container.querySelector("[data-open-nav]")?.addEventListener("click", () => document.body.classList.add("mock-nav-open"));
  container.querySelector("[data-close-nav]")?.addEventListener("click", () => document.body.classList.remove("mock-nav-open"));
}

async function persistCurrentAnswer(container) {
  const question = state.session.questions[state.index];
  const inputs = [...container.querySelectorAll("input[name='answer']:checked")];
  const selected = inputs.map((input) => Number(input.value));
  question.selected = selected;
  question.answered = selected.length > 0;
  container.querySelectorAll(".mock-answer").forEach((label) => label.classList.toggle("selected", label.querySelector("input").checked));
  const status = container.querySelector("[data-save-state]");
  status.textContent = "Saving…";
  state.pending.set(question.id, selected);
  try {
    await saveMockAnswer(state.session.session_id, question.id, selected);
    state.pending.delete(question.id);
    status.textContent = "Saved.";
  } catch (error) {
    status.textContent = "Saved locally. Retrying…";
    showToast(`Answer save delayed: ${error.message}`, "error");
    window.setTimeout(() => retryPending(container), 1800);
  }
}

async function retryPending(container) {
  for (const [questionId, selected] of [...state.pending.entries()]) {
    try { await saveMockAnswer(state.session.session_id, questionId, selected); state.pending.delete(questionId); } catch { return; }
  }
  const status = container.querySelector("[data-save-state]");
  if (status) status.textContent = "Saved.";
}

async function toggleFlag(container) {
  const question = state.session.questions[state.index];
  const next = !question.flagged;
  question.flagged = next;
  drawPlayer(container);
  try { await saveMockFlag(state.session.session_id, question.id, next); } catch (error) { question.flagged = !next; showToast(error.message, "error"); drawPlayer(container); }
}

function openSubmit(container) {
  const dialog = container.querySelector("[data-submit-dialog]");
  dialog.showModal();
}

async function finishExam(container, reason) {
  if (state.submitting) return;
  state.submitting = true;
  if (state.timer) clearInterval(state.timer);
  container.querySelectorAll("button").forEach((button) => { button.disabled = true; });
  try {
    await retryPending(container);
    const result = await submitMockSession(state.session.session_id, reason);
    window.location.hash = `#/mock/result?session_id=${result.session_id}`;
  } catch (error) { state.submitting = false; showToast(error.message, "error"); drawPlayer(container); startTimer(container); }
}

function startTimer(container) {
  state.timer = window.setInterval(() => {
    const seconds = remaining();
    const timer = container.querySelector("#mock-timer");
    if (timer) timer.textContent = formatClock(seconds);
    for (const threshold of [1800, 600, 300, 60]) {
      if (seconds <= threshold && seconds > threshold - 2 && !state.warned.has(threshold)) { state.warned.add(threshold); showToast(`${formatClock(threshold)} remaining`, "info"); }
    }
    if (seconds <= 0) finishExam(container, "timer");
  }, 1000);
}

function remaining() { return Math.max(0, state.serverRemaining - Math.floor((Date.now() - state.serverLoadedAt) / 1000)); }

async function renderResult(container, sessionId) {
  if (!sessionId) throw new Error("A session ID is required.");
  const result = await getMockResult(sessionId);
  const reviews = filteredReviews(result.reviews || []);
  const verdict = result.ready ? "READY" : "NEEDS REVIEW";
  container.innerHTML = `<main class="mock-page mock-results replica-enter"><a class="mock-back" href="#/mock">← Practice</a><header class="mock-result-hero"><div><p class="mock-kicker">SnowPro Core · COF-C03</p><h1>Mock Exam <em>Result</em></h1><p>${result.raw_correct} / ${result.total_questions} correct · ${formatMinutes(result.elapsed_seconds)}</p></div><div class="mock-score"><strong>${result.scaled_score}</strong><span>/ ${result.score_scale}</span><b class="${result.ready ? "ready" : "review"}">${verdict}</b><small>${result.pass_scaled_score} / ${result.score_scale} pass threshold</small></div></header><p class="mock-score-note">${escapeHtml(result.scoring_note)}</p><section class="mock-section"><div class="mock-section-head"><div><p class="mock-kicker">Domain performance</p><h2>Weighted readiness evidence.</h2></div><p>${result.weighted_accuracy}% weighted · ${result.raw_accuracy}% raw accuracy</p></div><div class="mock-result-domains">${result.domain_performance.map(domainResult).join("")}</div></section><section class="mock-section mock-strength-grid"><div><p class="mock-kicker">Strongest areas</p>${taskList(result.strongest_tasks, "No strong-area evidence yet.")}</div><div><p class="mock-kicker">Needs review</p>${taskList(result.weakest_tasks, "No weak-area evidence yet.")}</div></section><section class="mock-section"><div class="mock-section-head"><div><p class="mock-kicker">Next best action</p><h2>Review, drill, retest.</h2></div></div><div class="mock-action-grid"><a class="mock-action" href="#/practice?track_id=${encodeURIComponent(result.track_id)}&mode=drill"><strong>Drill weak tasks</strong><span>Prioritize missed concepts.</span></a><button class="mock-action" type="button" data-review-incorrect><strong>Review incorrect questions</strong><span>Study explanations and links.</span></button><a class="mock-action" href="#/curriculum?track_id=${encodeURIComponent(result.track_id)}"><strong>Review curriculum</strong><span>Return to written task lessons.</span></a><a class="mock-action" href="#/mock/start?type=full-mock"><strong>Take another mock</strong><span>Create a fresh sitting.</span></a></div></section><section class="mock-section" id="question-review"><div class="mock-section-head"><div><p class="mock-kicker">Question review</p><h2>Understand every miss.</h2></div><div class="mock-review-filters">${reviewFilter("all", result.reviews.length)}${reviewFilter("correct", result.counts.correct)}${reviewFilter("incorrect", result.counts.incorrect + result.counts.unanswered)}${reviewFilter("flagged", result.counts.flagged)}</div></div><div class="mock-review-list">${reviews.map(reviewCard).join("") || `<div class="mock-empty">No questions match this filter.</div>`}</div></section></main>`;
  container.querySelectorAll("[data-review-filter]").forEach((button) => button.addEventListener("click", () => { state.reviewFilter = button.dataset.reviewFilter; renderResult(container, sessionId); }));
  container.querySelector("[data-review-incorrect]")?.addEventListener("click", () => { state.reviewFilter = "incorrect"; renderResult(container, sessionId).then(() => container.querySelector("#question-review")?.scrollIntoView({ behavior: "smooth" })); });
}

function domainResult(domain) { return `<article><div><strong>${domain.weight}%</strong><span>${escapeHtml(domain.title)}</span></div><div class="mock-progress"><i style="--progress:${domain.accuracy}%"></i></div><b>${domain.accuracy}%</b><small>${domain.correct}/${domain.total}</small></article>`; }
function taskList(tasks, empty) { return tasks?.length ? `<div class="mock-task-list">${tasks.map((task) => `<article><span>Task ${escapeHtml(task.task_code)}</span><strong>${escapeHtml(task.title)}</strong><b>${task.accuracy}%</b><div><a href="${task.lesson_url}">Review lesson</a><a href="${task.drill_url}">Drill task</a></div></article>`).join("")}</div>` : `<p class="mock-muted">${empty}</p>`; }
function reviewFilter(value, count) { return `<button type="button" class="${state.reviewFilter === value ? "active" : ""}" data-review-filter="${value}">${value[0].toUpperCase() + value.slice(1)} <span>${count}</span></button>`; }
function filteredReviews(reviews) { if (state.reviewFilter === "correct") return reviews.filter((q) => q.is_correct); if (state.reviewFilter === "incorrect") return reviews.filter((q) => !q.is_correct); if (state.reviewFilter === "flagged") return reviews.filter((q) => q.flagged); return reviews; }
function reviewCard(item) { const answer = labels(item.selected, item.options); const correct = labels(item.correct, item.options); return `<article class="mock-review-card ${item.is_correct ? "correct" : "incorrect"}"><header><span>Question ${item.position}</span><b>${item.is_correct ? "Correct" : item.selected.length ? "Incorrect" : "Unanswered"}</b>${item.flagged ? "<small>Flagged</small>" : ""}</header><p class="mock-review-meta">Domain: ${escapeHtml(item.domain_title)} · Task ${escapeHtml(item.task_code)} ${escapeHtml(item.skill_title)}</p><h3>${escapeHtml(item.question)}</h3><div class="mock-answer-review"><p><strong>Your answer</strong>${escapeHtml(answer || "No answer")}</p><p><strong>Correct answer</strong>${escapeHtml(correct)}</p></div><div class="mock-explanation"><strong>Explanation</strong><p>${escapeHtml(item.explanation || "No explanation was supplied with this source question.")}</p></div><footer><a href="${item.lesson_url}">Review Task ${escapeHtml(item.task_code)}</a><a href="${item.drill_url}">Drill This Task</a></footer></article>`; }

async function renderHistory(container) {
  const data = await getMockHistory({ track_id: activeTrack() });
  const rows = data.history || [];
  container.innerHTML = `<main class="mock-page replica-enter"><a class="mock-back" href="#/mock">← Practice</a><header class="mock-page-heading"><p class="mock-kicker">Readiness evidence</p><h1>Mock <em>History</em></h1><p>Every persisted sitting and its weakest domain.</p></header><section class="mock-section"><div class="mock-history-list mock-history-full"><div class="mock-history-head"><span>Date</span><span>Sitting</span><span>Score</span><span>Result</span><span>Time</span><span>Weakest domain</span></div>${rows.map(historyRow).join("") || `<div class="mock-empty"><strong>No completed mocks yet.</strong><p>Start a quick or full sitting to build readiness evidence.</p></div>`}</div></section></main>`;
}

function labels(indices, options = []) { return indices.map((index) => `${String.fromCharCode(65 + Number(index))}. ${options[Number(index)] || ""}`.trim()).join("; "); }
function modeName(mode) { return ({ "exam_quick_mock": "Quick Mock", "exam_full_mock": "Full Mock", "exam_source": "Source Practice Exam", "quick-mock": "Quick Mock", "full-mock": "Full Mock" })[mode] || "Mock Exam"; }
function domainLabel(id) { const match = String(id || "").match(/^(features|account|loading|performance|data)/); return match ? `${match[1][0].toUpperCase()}${match[1].slice(1)} domain` : "Blueprint domain"; }
function taskLabel(id) { return id && id !== "unmapped" ? id.replaceAll("-", " ") : "Mapped task"; }
function formatClock(total) { const seconds = Math.max(0, Number(total) || 0); const h = Math.floor(seconds / 3600); const m = Math.floor((seconds % 3600) / 60); const s = seconds % 60; return h ? `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}` : `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`; }
function formatMinutes(seconds) { const minutes = Math.round((Number(seconds) || 0) / 60); return minutes >= 60 ? `${Math.floor(minutes / 60)}h ${minutes % 60}m` : `${minutes} min`; }
function formatDate(value) { if (!value) return "—"; const normalized = value.includes("T") ? value : value.replace(" ", "T") + "Z"; return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", year: "numeric" }).format(new Date(normalized)); }
