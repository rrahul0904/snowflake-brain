export const VIEW_ID = "practice";
import { escapeHtml, formatNumber, getDiagnosticPlan, getExperienceShell, gradeQuiz, recordAttempt, startQuiz } from "../api.js?v=20260812-v23-cert-guide";
import { activeTrack, emptyState, navigateWithTrack, pct, setActiveTrack, skeleton, trackOptions } from "../ui.js?v=20260731-v21-editorial-replica";
import { showToast } from "../components/toast.js?v=20260731-v21-editorial-replica";

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
  container.innerHTML = skeleton("Loading practice session...");
  try {
    const experience = await getExperienceShell({ track_id: state.trackId });
    const requestedMode = params.mode || "";
    if (["diagnostic", "drill", "quick-mock", "full-mock", "exam"].includes(requestedMode)) {
      await launch(container, { mode: requestedMode, count: Number(params.count || 0) || undefined });
      return;
    }
    renderStart(container, experience);
  } catch (error) {
    container.innerHTML = emptyState("Practice unavailable", error.message);
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

function renderStart(container, experience) {
  const selected = experience.selected_track_id || state.trackId;
  state.trackId = selected;
  const readiness = experience.readiness || {};
  container.innerHTML = `
    <section class="page-shell exam-page product-v10">
      <header class="page-hero split-hero exam-hero">
        <div>
          <p class="eyebrow">Practice</p>
          <h1>Diagnostic, drill, and mock exam.</h1>
          <p>Use the diagnostic to find weak domains, drill to reinforce them, and timed mocks to rehearse exam behavior before you book the real exam.</p>
        </div>
        <label class="cert-filter"><span>Certification</span><select id="track-select">${trackOptions(experience.certifications || [], selected)}</select></label>
      </header>

      <section class="exam-evidence-strip">
        <div><span>Recorded attempts</span><strong>${formatNumber(readiness.attempts || 0)}</strong></div>
        <div><span>Current accuracy</span><strong>${pct(readiness.accuracy_pct || 0)}%</strong></div>
        <div><span>Finished mocks</span><strong>${formatNumber(readiness.mock_exam_attempts || 0)}</strong></div>
        <div><span>Readiness</span><strong>${pct(readiness.readiness_score || 0)}%</strong></div>
      </section>

      <section class="exam-mode-grid serious-modes">
        ${modeCard("diagnostic", "Diagnostic assessment", "Untimed placement test across the certification blueprint. Use it to decide what to study first.", "25 questions", true, "Untimed")}
        ${modeCard("drill", "Drill mode", "Short repeated practice for concept reinforcement and mistake repair.", "15 questions", false, "Untimed")}
        ${modeCard("quick-mock", "Quick mock", "A shorter timed sitting for a readiness check between study sessions.", "30 questions", false, "60 min")}
        ${modeCard("full-mock", "Full mock", "A long timed simulation with review flags, free navigation, and explanations after submit.", "65 questions", false, "130 min")}
      </section>
    </section>
  `;
  container.querySelector("#track-select")?.addEventListener("change", (event) => navigateWithTrack(event.target.value, "#/practice"));
  container.querySelectorAll("[data-mode]").forEach((button) => button.addEventListener("click", () => launch(container, { mode: button.dataset.mode, count: Number(button.dataset.count || 15) })));
}

function modeCard(mode, title, body, count, primary, timer) {
  const n = Number((count.match(/\d+/) || [15])[0]);
  return `<button class="mode-card ${primary ? "featured" : ""}" data-mode="${mode}" data-count="${n}" type="button"><span>${escapeHtml(title)}</span><strong>${escapeHtml(count)}</strong><p>${escapeHtml(body)}</p><small>${escapeHtml(timer)}</small></button>`;
}

async function launch(container, config) {
  container.innerHTML = skeleton("Preparing practice session...");
  try {
    let count = Number(config.count || 0);
    if (config.mode === "diagnostic") {
      count = count || 25;
      await getDiagnosticPlan({ track_id: state.trackId, count }).catch(() => null);
      state.durationSec = 0;
    } else if (config.mode === "drill") {
      count = count || 15;
      state.durationSec = 0;
    } else if (config.mode === "quick-mock") {
      count = count || 30;
      state.durationSec = count * 120;
    } else if (config.mode === "full-mock" || config.mode === "exam") {
      count = count || 65;
      state.durationSec = count * 120;
    } else {
      count = count || 15;
      state.durationSec = 0;
    }

    const data = await startQuiz({ track_id: state.trackId, count, mode: "random" });
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
    container.innerHTML = emptyState("Unable to start practice", error.message, `<a class="primary-btn" href="#/mock?track_id=${encodeURIComponent(state.trackId)}">Back to Practice</a>`);
  }
}

function startTimer(container) {
  if (state.timer) clearInterval(state.timer);
  state.timer = setInterval(() => {
    const node = container.querySelector("#exam-timer");
    if (node) node.textContent = timerText();
    if (state.durationSec && remainingSeconds() <= 0 && !state.submitted) submit(container);
  }, 1000);
}

function elapsedSeconds() {
  return state.startedAt ? Math.floor((Date.now() - state.startedAt) / 1000) : 0;
}

function remainingSeconds() {
  return Math.max(0, state.durationSec - elapsedSeconds());
}

function timerText() {
  if (!state.startedAt) return "--:--";
  return formatClock(state.durationSec ? remainingSeconds() : elapsedSeconds());
}

function formatClock(total) {
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  return h ? `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}` : `${m}:${String(s).padStart(2, "0")}`;
}

function renderQuiz(container) {
  if (!state.questions.length) {
    container.innerHTML = emptyState("No questions found", "Try another certification or practice mode.", `<a class="primary-btn" href="#/mock?track_id=${encodeURIComponent(state.trackId)}">Back</a>`);
    return;
  }
  const q = state.questions[state.index];
  const selected = state.answers.get(q.id) || [];
  const unanswered = state.questions.length - state.answers.size;
  container.innerHTML = `
    <section class="quiz-shell-v10">
      <aside class="quiz-nav-panel">
        <a href="#/mock?track_id=${encodeURIComponent(state.trackId)}" class="ghost-link">← Practice</a>
        <h2>${escapeHtml(modeLabel(state.mode))}</h2>
        <div class="exam-timer-card"><span>${state.durationSec ? "Time remaining" : "Elapsed time"}</span><strong id="exam-timer">${timerText()}</strong></div>
        <div class="exam-counters"><span>${state.answers.size} answered</span><span>${unanswered} unanswered</span><span>${state.marked.size} marked</span></div>
        <div class="question-map">${state.questions.map((question, i) => `<button class="q-dot ${i === state.index ? "active" : ""} ${state.answers.has(question.id) ? "answered" : ""} ${state.marked.has(question.id) ? "marked" : ""}" data-index="${i}">${i + 1}</button>`).join("")}</div>
        <button id="submit-quiz" class="primary-btn xl">Submit answers</button>
      </aside>
      <main class="question-stage-v10">
        <div class="question-card-v10">
          <div class="question-meta"><span>Question ${state.index + 1}/${state.questions.length}</span><span>${escapeHtml(q.test_title || "Certification practice")}</span><span>${escapeHtml(q.difficulty || "medium")}</span></div>
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
  if (mode === "diagnostic") return "Diagnostic Assessment";
  if (mode === "quick-mock") return "Quick Mock";
  if (mode === "full-mock" || mode === "exam") return "Full Mock Exam";
  return "Drill Mode";
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
  if (state.submitted) return;
  state.submitted = true;
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
  const elapsed = elapsedSeconds();
  const bySet = scoreBy(rows, (row) => row.question.test_title || "Certification practice");
  container.innerHTML = `
    <section class="page-shell result-page product-v10">
      <header class="page-hero result-hero split-hero">
        <div><p class="eyebrow">Score Report</p><h1>${percent}%</h1><p>${score}/${state.questions.length} correct · ${formatClock(elapsed)} elapsed · ${state.marked.size} marked for review.</p></div>
        <div class="score-verdict"><strong>${percent >= 80 ? "Strong readiness signal" : "More study recommended"}</strong><span>${percent >= 80 ? "Validate with another timed set before booking." : "Review the missed concepts, then drill them again."}</span></div>
      </header>
      <section class="result-grid">
        <article class="panel"><div class="panel-header"><div><p class="eyebrow">Performance breakdown</p><h2>Where misses occurred</h2></div></div><div class="breakdown-list">${bySet.map(breakdownRow).join("")}</div></article>
        <article class="panel"><div class="panel-header"><div><p class="eyebrow">Next action</p><h2>Review, drill, retest</h2></div></div><div class="action-stack"><a class="action-tile" href="#/progress?track_id=${encodeURIComponent(state.trackId)}"><strong>Open Progress Dashboard</strong><span>See readiness and weak domains.</span></a><a class="action-tile" href="#/curriculum?track_id=${encodeURIComponent(state.trackId)}"><strong>Review task lessons</strong><span>Return to the exam blueprint and close concept gaps.</span></a><a class="action-tile" href="#/drill?track_id=${encodeURIComponent(state.trackId)}"><strong>Start Drill Mode</strong><span>Reinforce weak concepts before another mock.</span></a></div></article>
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
