export const VIEW_ID = "practice";
import { escapeHtml, formatNumber, getDiagnosticPlan, getExperienceShell, getPracticeTests, gradeQuiz, recordAttempt, startQuiz } from "../api.js?v=20260714-v20-ai-academy";
import { activeTrack, emptyState, navigateWithTrack, pct, setActiveTrack, skeleton, trackOptions } from "../ui.js?v=20260714-v20-ai-academy";
import { showToast } from "../components/toast.js?v=20260714-v20-ai-academy";

const state = {
  trackId: "snowpro-core",
  questions: [],
  index: 0,
  answers: new Map(),
  marked: new Set(),
  submitted: false,
  mode: "drill",
  startedAt: null,
  durationSec: 0,
  timer: null,
};

export function unmount() {
  if (state.timer) clearInterval(state.timer);
  state.timer = null;
}

export default async function mount(container, params = {}) {
  unmount();
  state.trackId = params.track_id || activeTrack();
  setActiveTrack(state.trackId);
  resetSession();
  container.innerHTML = skeleton("Loading exam studio...");
  try {
    const [experience, tests] = await Promise.all([
      getExperienceShell({ track_id: state.trackId }),
      getPracticeTests({ track_id: state.trackId, min_questions: 1 }).catch(() => ({ tests: [] })),
    ]);
    renderStart(container, experience, tests.tests || [], params);
  } catch (error) {
    container.innerHTML = emptyState("Exam studio unavailable", error.message);
  }
}

function resetSession() {
  state.questions = [];
  state.index = 0;
  state.answers = new Map();
  state.marked = new Set();
  state.submitted = false;
  state.mode = "drill";
  state.startedAt = null;
  state.durationSec = 0;
}

function renderStart(container, experience, tests, params = {}) {
  const selected = experience.selected_track_id || state.trackId;
  state.trackId = selected;
  const readiness = experience.readiness || {};
  const attempts = readiness.attempts || 0;
  const accuracy = readiness.accuracy_pct || 0;
  const mockAttempts = readiness.mock_exam_attempts || 0;
  container.innerHTML = `
    <section class="page-shell exam-page product-v10">
      <header class="page-hero split-hero exam-hero">
        <div>
          <p class="eyebrow">Exam Studio</p>
          <h1>Timed practice, source tests, and diagnostic evidence.</h1>
          <p>This workspace separates learning from exam behavior: no explanations until submit, review marking, timer pressure, and score reports that feed the readiness gate.</p>
        </div>
        <label class="cert-filter"><span>Certification</span><select id="track-select">${trackOptions(experience.certifications || [], selected)}</select></label>
      </header>

      <section class="exam-evidence-strip">
        <div><span>Recorded attempts</span><strong>${formatNumber(attempts)}</strong></div>
        <div><span>Current accuracy</span><strong>${accuracy}%</strong></div>
        <div><span>Finished mocks</span><strong>${formatNumber(mockAttempts)}</strong></div>
        <div><span>Readiness</span><strong>${pct(readiness.readiness_score)}%</strong></div>
      </section>

      <section class="exam-mode-grid serious-modes">
        ${modeCard("diagnostic", "Diagnostic baseline", "Balanced first-pass assessment across mapped skills. Use this before trusting the plan.", "30 questions", true, "45 min")}
        ${modeCard("random", "Adaptive drill", "Fast question set for weak-skill repair and repetition.", "15 questions", false, "Untimed")}
        ${modeCard("exam", "Readiness exam", "Timed-style certification simulation. Explanations remain hidden until submit.", "50 questions", false, "90 min")}
      </section>

      <section class="panel test-library-panel">
        <div class="panel-header"><div><p class="eyebrow">Downloaded source tests</p><h2>${tests.length} available practice sets</h2></div><span class="muted">From your local archive</span></div>
        <div class="test-library">${tests.slice(0, 36).map(testCard).join("") || emptyState("No practice tests", "This certification has no source tests mapped yet.")}</div>
      </section>
    </section>
  `;
  container.querySelector("#track-select")?.addEventListener("change", (event) => navigateWithTrack(event.target.value, "#/practice"));
  container.querySelectorAll("[data-mode]").forEach((button) => button.addEventListener("click", () => launch(container, { mode: button.dataset.mode, count: Number(button.dataset.count || 15) })));
  container.querySelectorAll("[data-test]").forEach((button) => button.addEventListener("click", () => launch(container, { mode: "source-test", test_id: button.dataset.test, count: 500 })));
  if (params.mode === "diagnostic") launch(container, { mode: "diagnostic", count: 30 });
}

function modeCard(mode, title, body, count, primary, timer) {
  const n = Number((count.match(/\d+/) || [15])[0]);
  return `<button class="mode-card ${primary ? "featured" : ""}" data-mode="${mode}" data-count="${n}" type="button"><span>${escapeHtml(title)}</span><strong>${escapeHtml(count)}</strong><p>${escapeHtml(body)}</p><small>${escapeHtml(timer)}</small></button>`;
}

function testCard(test) {
  return `<button class="test-card" data-test="${escapeHtml(test.test_id)}" type="button"><strong>${escapeHtml(test.test_title || "Practice Test")}</strong><span>${escapeHtml(test.course_title || "")}</span><small>${test.question_count || 0} questions</small></button>`;
}

async function launch(container, config) {
  container.innerHTML = skeleton("Preparing serious exam session...");
  try {
    let data;
    if (config.mode === "diagnostic") {
      await getDiagnosticPlan({ track_id: state.trackId, count: config.count || 30 }).catch(() => null);
      data = await startQuiz({ track_id: state.trackId, count: config.count || 30, mode: "random" });
      state.durationSec = 45 * 60;
    } else if (config.mode === "exam") {
      data = await startQuiz({ track_id: state.trackId, count: config.count || 50, mode: "random" });
      state.durationSec = 90 * 60;
    } else if (config.mode === "source-test") {
      data = await startQuiz({ track_id: state.trackId, test_id: config.test_id, count: config.count || 500, mode: "sequential" });
      state.durationSec = Math.max(30 * 60, Math.min(150 * 60, (data.questions || []).length * 90));
    } else {
      data = await startQuiz({ track_id: state.trackId, count: config.count || 15, mode: "random" });
      state.durationSec = 0;
    }
    state.questions = data.questions || [];
    state.index = 0;
    state.answers = new Map();
    state.marked = new Set();
    state.submitted = false;
    state.mode = config.mode;
    state.startedAt = Date.now();
    renderQuiz(container);
    startTimer(container);
  } catch (error) {
    showToast(error.message, "error");
    container.innerHTML = emptyState("Unable to start practice", error.message, `<a class="primary-btn" href="#/practice">Back to Exam Studio</a>`);
  }
}

function startTimer(container) {
  if (state.timer) clearInterval(state.timer);
  state.timer = setInterval(() => {
    const node = container.querySelector("#exam-timer");
    if (node) node.textContent = timerText();
  }, 1000);
}

function timerText() {
  if (!state.startedAt) return "--:--";
  const elapsed = Math.floor((Date.now() - state.startedAt) / 1000);
  if (!state.durationSec) return formatClock(elapsed);
  const remaining = Math.max(0, state.durationSec - elapsed);
  return formatClock(remaining);
}

function formatClock(total) {
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  return h ? `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}` : `${m}:${String(s).padStart(2, "0")}`;
}

function renderQuiz(container) {
  if (!state.questions.length) {
    container.innerHTML = emptyState("No questions found", "Try another mode or certification.", `<a class="primary-btn" href="#/practice">Back</a>`);
    return;
  }
  const q = state.questions[state.index];
  const selected = state.answers.get(q.id) || [];
  const unanswered = state.questions.length - state.answers.size;
  container.innerHTML = `
    <section class="quiz-shell-v10">
      <aside class="quiz-nav-panel">
        <a href="#/practice?track_id=${encodeURIComponent(state.trackId)}" class="ghost-link">← Exam Studio</a>
        <h2>${escapeHtml(modeLabel(state.mode))}</h2>
        <div class="exam-timer-card"><span>${state.durationSec ? "Time remaining" : "Elapsed time"}</span><strong id="exam-timer">${timerText()}</strong></div>
        <div class="exam-counters"><span>${state.answers.size} answered</span><span>${unanswered} unanswered</span><span>${state.marked.size} marked</span></div>
        <div class="question-map">${state.questions.map((question, i) => `<button class="q-dot ${i === state.index ? "active" : ""} ${state.answers.has(question.id) ? "answered" : ""} ${state.marked.has(question.id) ? "marked" : ""}" data-index="${i}">${i + 1}</button>`).join("")}</div>
        <button id="submit-quiz" class="primary-btn xl">Submit answers</button>
      </aside>
      <main class="question-stage-v10">
        <div class="question-card-v10">
          <div class="question-meta"><span>Question ${state.index + 1}/${state.questions.length}</span><span>${escapeHtml(q.test_title || "Practice")}</span><span>${escapeHtml(q.difficulty || "medium")}</span></div>
          <h1>${escapeHtml(q.question)}</h1>
          <div class="options-v10">${(q.options || []).map((option, i) => optionRow(q, option, i, selected)).join("")}</div>
          <div class="question-actions"><button id="prev" class="secondary-btn">Previous</button><button id="mark-review" class="secondary-btn">${state.marked.has(q.id) ? "Unmark review" : "Mark for review"}</button><button id="next" class="primary-btn">Next</button></div>
        </div>
      </main>
    </section>
  `;
  bindQuiz(container);
}

function modeLabel(mode) {
  if (mode === "diagnostic") return "Diagnostic baseline";
  if (mode === "exam") return "Timed readiness exam";
  if (mode === "source-test") return "Downloaded source test";
  return "Adaptive drill";
}

function optionRow(q, option, i, selected) {
  const checked = selected.includes(i);
  const type = q.multiple ? "checkbox" : "radio";
  return `<label class="option-row-v10 ${checked ? "selected" : ""}"><input type="${type}" name="answer" value="${i}" ${checked ? "checked" : ""}/><span>${escapeHtml(option)}</span></label>`;
}

function bindQuiz(container) {
  container.querySelectorAll(".q-dot").forEach((button) => button.addEventListener("click", () => { capture(container); state.index = Number(button.dataset.index); renderQuiz(container); }));
  container.querySelectorAll("input[name='answer']").forEach((input) => input.addEventListener("change", () => capture(container)));
  container.querySelector("#prev")?.addEventListener("click", () => { capture(container); state.index = Math.max(0, state.index - 1); renderQuiz(container); });
  container.querySelector("#next")?.addEventListener("click", () => { capture(container); state.index = Math.min(state.questions.length - 1, state.index + 1); renderQuiz(container); });
  container.querySelector("#mark-review")?.addEventListener("click", () => { const id = state.questions[state.index].id; state.marked.has(id) ? state.marked.delete(id) : state.marked.add(id); renderQuiz(container); });
  container.querySelector("#submit-quiz")?.addEventListener("click", () => submit(container));
}

function capture(container) {
  const q = state.questions[state.index];
  const selected = [...container.querySelectorAll("input[name='answer']:checked")].map((input) => Number(input.value));
  if (selected.length) state.answers.set(q.id, selected);
  else state.answers.delete(q.id);
}

async function submit(container) {
  capture(container);
  if (state.timer) clearInterval(state.timer);
  const answers = state.questions.map((question) => ({ question_id: question.id, selected: state.answers.get(question.id) || [] }));
  let graded = { score: 0, total: state.questions.length, results: [] };
  try { graded = await gradeQuiz({ answers }); } catch (error) { showToast(error.message, "error"); }
  const score = graded.score || 0;
  const rows = graded.results?.length ? graded.results.map((question) => ({ question, selected: question.selected || [], isCorrect: question.is_correct })) : state.questions.map((question) => ({ question, selected: state.answers.get(question.id) || [], isCorrect: false }));
  for (const row of rows) {
    try { await recordAttempt(row.question.id, { selected: row.selected || [], correct: Boolean(row.isCorrect), mode: state.mode || "practice" }); } catch {}
  }
  const percent = Math.round((score / Math.max(1, state.questions.length)) * 100);
  const elapsed = state.startedAt ? Math.floor((Date.now() - state.startedAt) / 1000) : 0;
  const bySource = scoreBy(rows, (row) => row.question.test_title || row.question.course_title || "Practice");
  container.innerHTML = `
    <section class="page-shell result-page product-v10">
      <header class="page-hero result-hero split-hero">
        <div><p class="eyebrow">Score report</p><h1>${percent}%</h1><p>${score}/${state.questions.length} correct · ${formatClock(elapsed)} elapsed · ${state.marked.size} marked for review. Incorrect answers were recorded as repair evidence.</p></div>
        <div class="score-verdict"><strong>${percent >= 80 ? "Passing signal" : "Repair required"}</strong><span>${percent >= 80 ? "Validate with another timed set." : "Review misses before another full mock."}</span></div>
      </header>
      <section class="result-grid">
        <article class="panel"><div class="panel-header"><div><p class="eyebrow">Source breakdown</p><h2>Where misses came from</h2></div></div><div class="breakdown-list">${bySource.map(breakdownRow).join("")}</div></article>
        <article class="panel"><div class="panel-header"><div><p class="eyebrow">Next action</p><h2>Repair then retest</h2></div></div><div class="action-stack"><a class="action-tile" href="#/review"><strong>Open repair queue</strong><span>Turn misses into targeted review work.</span></a><a class="action-tile" href="#/learn?track_id=${encodeURIComponent(state.trackId)}"><strong>Watch related lessons</strong><span>Use video and transcripts to close concept gaps.</span></a><a class="action-tile" href="#/practice?track_id=${encodeURIComponent(state.trackId)}"><strong>Start another drill</strong><span>Retest only after reviewing misses.</span></a></div></article>
      </section>
      <section class="result-list">${rows.map(resultRow).join("")}</section>
    </section>
  `;
}

function scoreBy(rows, getter) {
  const map = new Map();
  for (const row of rows) {
    const key = getter(row);
    const item = map.get(key) || { label: key, total: 0, correct: 0 };
    item.total += 1;
    if (row.isCorrect) item.correct += 1;
    map.set(key, item);
  }
  return [...map.values()].sort((a, b) => (a.correct / a.total) - (b.correct / b.total)).slice(0, 8);
}

function breakdownRow(item) {
  const value = Math.round((item.correct / Math.max(1, item.total)) * 100);
  return `<div class="breakdown-row"><span><strong>${escapeHtml(item.label)}</strong><small>${item.correct}/${item.total} correct</small></span><b>${value}%</b></div>`;
}

function resultRow(row) {
  const options = row.question.options || [];
  const correct = row.question.correct || [];
  const selectedText = row.selected.map((i) => options[i]).filter(Boolean).join("; ") || "No answer";
  const correctText = correct.map((i) => options[i]).filter(Boolean).join("; ") || "Answer unavailable";
  return `<details class="result-row-v10 ${row.isCorrect ? "correct" : "wrong"}"><summary><span>${row.isCorrect ? "✓" : "×"}</span><strong>${escapeHtml(row.question.question)}</strong><small>${escapeHtml(row.question.test_title || "")}</small></summary><div><p><b>Your answer:</b> ${escapeHtml(selectedText)}</p><p><b>Correct answer:</b> ${escapeHtml(correctText)}</p>${row.question.explanation ? `<p><b>Explanation:</b> ${escapeHtml(row.question.explanation)}</p>` : ""}</div></details>`;
}
