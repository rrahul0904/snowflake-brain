import {
  addFlashcard,
  addQuestionNote,
  askBrain,
  escapeHtml,
  formatNumber,
  getCourses,
  getPracticeTests,
  getQuestion,
  getTopicProgress,
  getTracks,
  recordAttempt,
  startQuiz,
  toggleBookmark,
} from "../api.js";
import { showToast } from "../components/toast.js";

const topics = ["architecture", "warehouse", "rbac", "snowpipe", "streams tasks", "time travel", "dynamic tables", "cortex", "snowpark"];

const QUIZ_TRACK_KEY = "snowflake-brain.quiz-track";
const QUIZ_COURSE_KEY = "snowflake-brain.quiz-course";
const QUIZ_TEST_KEY = "snowflake-brain.quiz-test";

const state = {
  mode: "practice",
  tracks: [],
  courses: [],
  tests: [],
  weakTopics: [],
  selectedTestId: "",
  questions: [],
  details: {},
  current: 0,
  selected: {},
  submitted: {},
  review: new Set(),
  examSubmitted: false,
};

export default async function mount(container, params = {}) {
  container.innerHTML = `
    <section class="coach-page practice-page">
      <header class="coach-header">
        <div>
          <p class="eyebrow">Practice</p>
          <h1>Practice is the center of passing.</h1>
          <p class="page-subtitle">Start with a diagnostic, repair weak topics, then prove readiness with mock exams.</p>
        </div>
        <a class="secondary-btn" href="#/readiness">Check readiness</a>
      </header>

      <section id="quiz-setup" class="practice-coach-layout">
        <aside class="panel practice-control-panel">
          <p class="eyebrow">Exam scope</p>
          <label class="field"><span>Certification</span><select id="track-filter"></select></label>
          <label class="field"><span>Course focus</span><select id="course-filter"></select></label>
          <label class="field"><span>Topic for drills</span><select id="topic-filter"><option value="">Auto / all topics</option>${topics.map((topic) => `<option value="${topic}">${topic}</option>`).join("")}</select></label>
          <label class="field"><span>Question count</span><select id="count"><option>10</option><option>20</option><option selected>30</option><option>50</option><option>75</option></select></label>
          <div id="quiz-stats" class="muted small-copy">Loading practice library...</div>
        </aside>

        <main class="practice-coach-main">
          <section class="practice-mode-grid">
            <article class="panel practice-mode-card priority">
              <p class="eyebrow">Step 1</p>
              <h2>Diagnostic test</h2>
              <p>30 mixed questions from the selected certification. Use this to find your baseline and weak topics.</p>
              <button id="start-diagnostic" class="primary-btn wide" type="button">Start diagnostic</button>
            </article>
            <article class="panel practice-mode-card">
              <p class="eyebrow">Repair</p>
              <h2>Weak-topic drill</h2>
              <p id="weak-topic-copy">Answer focused questions from the topic you are weakest in.</p>
              <button id="start-weak" class="primary-btn wide" type="button">Repair weakest topic</button>
            </article>
            <article class="panel practice-mode-card">
              <p class="eyebrow">Exam simulation</p>
              <h2>Readiness exam</h2>
              <p>75-question exam mode. No feedback until final submit.</p>
              <button id="start-readiness" class="secondary-btn wide" type="button">Start readiness exam</button>
            </article>
          </section>

          <section class="panel full-test-panel">
            <div class="panel-header catalog-header">
              <div>
                <p class="eyebrow">Full mock exams and source tests</p>
                <h2 id="setup-title">Choose a downloaded test</h2>
                <span id="deck-summary" class="muted">Loading tests...</span>
              </div>
              <div class="catalog-actions">
                <button id="start-practice" class="primary-btn" type="button">Start guided practice</button>
                <button id="start-exam" class="secondary-btn" type="button">Start exam mode</button>
              </div>
            </div>
            <label class="field"><span>Search downloaded tests</span><input id="test-search" placeholder="Practice Test 1, COF-C03, RBAC..." /></label>
            <div id="test-list" class="practice-test-grid empty-state">Loading practice tests...</div>
          </section>
        </main>
      </section>

      <section id="session" class="hidden"></section>
      <section id="score-report" class="hidden"></section>
    </section>
  `;

  try {
    const [tracks, courses, tests, topicsData] = await Promise.all([
      getTracks(),
      getCourses(),
      getPracticeTests({ min_questions: 1 }),
      getTopicProgress().catch(() => ({ topics: [] })),
    ]);
    state.tracks = tracks.tracks || [];
    state.courses = (courses.courses || []).filter((course) => course.question_count > 0);
    state.tests = tests.tests || [];
    state.weakTopics = (topicsData.topics || []).filter((topic) => topic.attempted).sort((a, b) => a.accuracy - b.accuracy || b.attempted - a.attempted);

    const defaults = resolveDefaultQuizSelection(params);
    renderTrackOptions(container, defaults.trackId, defaults.courseId);
    renderCourseOptions(container, defaults.courseId);
    if (params.tag) container.querySelector("#topic-filter").value = params.tag;
    state.selectedTestId = defaults.testId;
    renderCoachPracticeState(container);
    renderTestCatalog(container);
  } catch (error) {
    showToast(error.message, "error");
    container.querySelector("#test-list").innerHTML = `<div class="error-state">${escapeHtml(error.message)}</div>`;
  }

  container.querySelector("#track-filter").addEventListener("change", () => {
    state.selectedTestId = "";
    localStorage.setItem(QUIZ_TRACK_KEY, container.querySelector("#track-filter").value);
    renderCourseOptions(container);
    selectFirstVisibleTest(container);
    renderCoachPracticeState(container);
    renderTestCatalog(container);
  });
  container.querySelector("#course-filter").addEventListener("change", () => {
    state.selectedTestId = "";
    localStorage.setItem(QUIZ_COURSE_KEY, container.querySelector("#course-filter").value);
    selectFirstVisibleTest(container);
    renderCoachPracticeState(container);
    renderTestCatalog(container);
  });
  container.querySelector("#test-search").addEventListener("input", () => renderTestCatalog(container));
  container.querySelector("#start-diagnostic").addEventListener("click", (event) => startCoachSession(container, { label: "Start diagnostic", mode: "practice", count: 30, type: "diagnostic", button: event.currentTarget }));
  container.querySelector("#start-weak").addEventListener("click", (event) => startCoachSession(container, { label: "Repair weakest topic", mode: "practice", count: 20, topic: currentWeakTopic(container), type: "weak", button: event.currentTarget }));
  container.querySelector("#start-readiness").addEventListener("click", (event) => startCoachSession(container, { label: "Start readiness exam", mode: "exam", count: 75, type: "readiness", button: event.currentTarget }));
  container.querySelector("#start-practice").addEventListener("click", () => start(container, "practice"));
  container.querySelector("#start-exam").addEventListener("click", () => start(container, "exam"));
  window.addEventListener("keydown", handleKeys);

  if (params.mode === "diagnostic") {
    container.querySelector("#start-diagnostic")?.focus();
  }
}

export function unmount() {
  window.removeEventListener("keydown", handleKeys);
  document.body.classList.remove("quiz-active");
}

function renderCoachPracticeState(container) {
  const weak = currentWeakTopic(container);
  const copy = container.querySelector("#weak-topic-copy");
  copy.textContent = weak
    ? `${weak} is your weakest detected topic. Drill it until you can clear 80%.`
    : "No weak topic has been detected yet. Take the diagnostic first or choose a topic manually.";
}

function currentWeakTopic(container) {
  const manual = container.querySelector("#topic-filter")?.value;
  if (manual) return manual;
  return state.weakTopics[0]?.tag || "";
}

function renderCourseOptions(container, requestedCourseId = null) {
  const trackId = container.querySelector("#track-filter").value;
  const courses = state.courses.filter((course) => !trackId || course.track_id === trackId);
  const previous = requestedCourseId || localStorage.getItem(QUIZ_COURSE_KEY) || container.querySelector("#course-filter").value;
  container.querySelector("#course-filter").innerHTML = `<option value="">All courses in this certification</option>` + courses.map((course) => `<option value="${course.id}">${escapeHtml(course.title)} (${formatNumber(course.question_count)})</option>`).join("");
  container.querySelector("#course-filter").value = courses.some((course) => course.id === previous) ? previous : "";
  if (container.querySelector("#course-filter").value) localStorage.setItem(QUIZ_COURSE_KEY, container.querySelector("#course-filter").value);
}

function renderTrackOptions(container, requestedTrackId, requestedCourseId) {
  const course = state.courses.find((item) => item.id === requestedCourseId);
  const testTracks = new Set(state.tests.map((test) => test.track_id).filter(Boolean));
  const tracks = state.tracks.filter((track) => testTracks.has(track.id));
  const select = container.querySelector("#track-filter");
  select.innerHTML = tracks.map((track) => `<option value="${track.id}">${escapeHtml(track.title)} (${formatNumber(track.question_count)} q)</option>`).join("");
  const preferredTrack = requestedTrackId || course?.track_id || localStorage.getItem(QUIZ_TRACK_KEY) || "snowpro-core";
  select.value = tracks.some((track) => track.id === preferredTrack) ? preferredTrack : tracks[0]?.id || "";
}

function renderTestCatalog(container) {
  const host = container.querySelector("#test-list");
  const query = container.querySelector("#test-search").value.trim().toLowerCase();
  const tests = filteredTests(container)
    .filter((test) => Number(test.question_count || 0) > 0)
    .filter((test) => {
      const haystack = `${test.course_title} ${test.test_title}`.toLowerCase();
      return !query || haystack.includes(query);
    })
    .sort((a, b) => {
      const fullA = Number(a.question_count || 0) >= 50 ? 0 : 1;
      const fullB = Number(b.question_count || 0) >= 50 ? 0 : 1;
      return fullA - fullB || Number(b.question_count || 0) - Number(a.question_count || 0);
    });
  if (state.selectedTestId && !tests.some((test) => test.test_id === state.selectedTestId)) state.selectedTestId = tests[0]?.test_id || "";
  if (!state.selectedTestId && tests.length) state.selectedTestId = tests[0].test_id;

  const questionCount = tests.reduce((sum, test) => sum + Number(test.question_count || 0), 0);
  container.querySelector("#quiz-stats").textContent = `${formatNumber(tests.length)} source tests · ${formatNumber(questionCount)} questions in current scope`;
  renderDeckSummary(container);

  if (!tests.length) {
    host.className = "practice-test-grid empty-state";
    host.innerHTML = "No source tests match this certification/course filter.";
    return;
  }
  host.className = "practice-test-grid coach-test-grid";
  host.innerHTML = tests.slice(0, 24)
    .map(
      (test) => `
        <button class="test-card ${test.test_id === state.selectedTestId ? "active" : ""}" data-test-id="${escapeHtml(test.test_id)}" type="button">
          <span class="status-badge">${Number(test.question_count || 0) >= 50 ? "Mock exam" : "Quiz"}</span>
          <strong>${escapeHtml(test.test_title)}</strong>
          <small>${formatNumber(test.question_count)} questions</small>
          <small>${escapeHtml(test.course_title)}</small>
        </button>`,
    )
    .join("");
  host.querySelectorAll(".test-card").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedTestId = button.dataset.testId || "";
      localStorage.setItem(QUIZ_TEST_KEY, state.selectedTestId);
      renderTestCatalog(container);
    });
  });
}

function renderDeckSummary(container) {
  const selectedTest = currentTest();
  if (selectedTest) {
    container.querySelector("#setup-title").textContent = selectedTest.test_title;
    container.querySelector("#deck-summary").textContent = `${formatNumber(selectedTest.question_count)} questions · ${selectedTest.course_title}`;
  } else {
    container.querySelector("#setup-title").textContent = "Choose a downloaded practice test";
    container.querySelector("#deck-summary").textContent = "Or start with the diagnostic / weak-topic drill above.";
  }
}

async function startCoachSession(container, options) {
  const button = options.button;
  const original = button?.textContent || options.label;
  if (button) {
    button.disabled = true;
    button.textContent = "Loading...";
  }
  const trackId = container.querySelector("#track-filter").value || null;
  const courseId = container.querySelector("#course-filter").value || null;
  try {
    await loadQuestions(container, {
      mode: options.mode || "practice",
      trackId,
      courseId,
      testId: null,
      count: options.count || Number(container.querySelector("#count").value || 30),
      tags: options.topic ? [options.topic] : [],
      orderMode: "random",
    });
  } finally {
    if (button) {
      button.disabled = false;
      button.textContent = original;
    }
  }
}

async function start(container, mode) {
  const selectedTest = currentTest();
  const button = mode === "exam" ? container.querySelector("#start-exam") : container.querySelector("#start-practice");
  if (!selectedTest) {
    showToast("Choose a downloaded test first", "error");
    return;
  }
  const original = button.textContent;
  button.disabled = true;
  button.textContent = "Loading...";
  try {
    await loadQuestions(container, {
      mode,
      trackId: selectedTest.track_id || container.querySelector("#track-filter").value || null,
      courseId: selectedTest.course_id || container.querySelector("#course-filter").value || null,
      testId: selectedTest.test_id,
      count: Number(selectedTest.question_count || 1),
      tags: [],
      orderMode: "ordered",
    });
  } finally {
    button.disabled = false;
    button.textContent = original;
  }
}

async function loadQuestions(container, options) {
  try {
    state.mode = options.mode;
    const data = await startQuiz({
      course_id: options.courseId,
      track_id: options.trackId,
      test_id: options.testId,
      count: options.count,
      mode: options.orderMode || "random",
      tags: options.tags || [],
      unanswered_only: false,
    });
    state.questions = data.questions || [];
    state.details = {};
    state.current = 0;
    state.selected = {};
    state.submitted = {};
    state.review = new Set();
    state.examSubmitted = false;
    if (!state.questions.length) {
      showToast("No questions matched this selection", "error");
      return;
    }
    document.body.classList.add("quiz-active");
    container.querySelector("#quiz-setup").classList.add("hidden");
    container.querySelector("#score-report").classList.add("hidden");
    container.querySelector("#session").classList.remove("hidden");
    renderSession(container);
  } catch (error) {
    showToast(error.message, "error");
  }
}

function renderSession(container) {
  const host = container.querySelector("#session");
  const question = state.questions[state.current];
  if (!question) return;
  const selected = new Set(state.selected[question.id] || []);
  const submitted = state.submitted[question.id];
  const locked = (state.mode === "practice" && Boolean(submitted)) || state.examSubmitted;
  const answered = Object.values(state.selected).filter((value) => value?.length).length;
  host.innerHTML = `
    <div class="session-header panel">
      <div>
        <p class="eyebrow">${state.mode === "exam" ? "Exam mode" : "Practice mode"}</p>
        <h2>Question ${state.current + 1} of ${state.questions.length}</h2>
        <p class="muted">${state.mode === "exam" ? `${answered}/${state.questions.length} answered · answers are graded after final submit` : "Submit one answer to see feedback."}</p>
      </div>
      <div class="session-actions"><button id="exit-session" class="secondary-btn" type="button">Exit</button><button id="finish-session" class="primary-btn" type="button">${state.mode === "exam" ? "Finish test" : "Score practice"}</button></div>
    </div>
    <div class="progress-line"><b>${state.current + 1}/${state.questions.length}</b><span><i style="width:${((state.current + 1) / state.questions.length) * 100}%"></i></span></div>
    <article class="practice-question-card panel">
      <h2>${escapeHtml(question.question)}</h2>
      <div class="practice-answers">
        ${question.options
          .map((option, index) => {
            const letter = String.fromCharCode(65 + index);
            return `<label class="practice-answer ${selected.has(index) ? "selected" : ""} ${answerClass(question, index)}">
              <input type="${question.multiple ? "checkbox" : "radio"}" name="answer" value="${index}" ${selected.has(index) ? "checked" : ""} ${locked ? "disabled" : ""}/>
              <b>${letter}</b><span>${escapeHtml(option)}</span>
            </label>`;
          })
          .join("")}
      </div>
    </article>
    <section id="explanation" class="practice-explanation panel ${shouldShowExplanation(question) ? "" : "hidden"}">${renderExplanation(question)}</section>
    <div class="practice-actionbar clean-actionbar panel">
      <button id="prev" class="secondary-btn" type="button">Previous</button>
      <button id="submit-answer" class="primary-btn" type="button" ${state.examSubmitted || (state.mode === "practice" && submitted) ? "disabled" : ""}>${submitButtonLabel(question)}</button>
      <button id="next" class="secondary-btn" type="button">Next</button>
      <button id="mark-review" class="secondary-btn ${state.review.has(question.id) ? "active" : ""}" type="button">Mark for review</button>
      <button id="bookmark" class="secondary-btn" type="button">Bookmark</button>
      <button id="ask-tutor" class="secondary-btn" type="button">Ask tutor</button>
    </div>
    <details class="panel question-map">
      <summary>Question map</summary>
      <div class="question-map-grid">${state.questions
        .map((item, index) => `<button class="map-dot ${index === state.current ? "active" : ""} ${(state.selected[item.id] || []).length ? "answered" : ""} ${state.submitted[item.id]?.correct ? "correct" : ""} ${state.submitted[item.id] && !state.submitted[item.id].correct ? "incorrect" : ""}" data-index="${index}" type="button">${index + 1}</button>`)
        .join("")}</div>
    </details>
    <div id="tutor-panel" class="panel tutor-panel hidden"></div>
  `;

  host.querySelectorAll("input[name='answer']").forEach((input) => input.addEventListener("change", () => updateSelection(container)));
  host.querySelectorAll(".practice-answer").forEach((answer) => {
    answer.addEventListener("click", (event) => {
      event.preventDefault();
      if (locked) return;
      chooseAnswer(container, Number(answer.querySelector("input").value));
    });
  });
  host.querySelector("#prev").disabled = state.current === 0;
  host.querySelector("#next").disabled = state.current === state.questions.length - 1;
  host.querySelector("#prev").addEventListener("click", () => move(container, -1));
  host.querySelector("#next").addEventListener("click", () => move(container, 1));
  host.querySelector("#submit-answer").addEventListener("click", () => submitCurrent(container));
  host.querySelector("#finish-session").addEventListener("click", () => finishSession(container));
  host.querySelector("#exit-session").addEventListener("click", () => exitSession(container));
  host.querySelector("#mark-review").addEventListener("click", () => toggleReview(container));
  host.querySelector("#bookmark").addEventListener("click", () => bookmark(container));
  host.querySelector("#ask-tutor").addEventListener("click", () => askTutor(container));
  host.querySelectorAll(".map-dot").forEach((button) => button.addEventListener("click", () => {
    state.current = Number(button.dataset.index);
    renderSession(container);
  }));
  wireExplanationActions(host, question);
}

function updateSelection(container) {
  const question = state.questions[state.current];
  state.selected[question.id] = Array.from(container.querySelectorAll("input[name='answer']:checked")).map((input) => Number(input.value));
  renderSession(container);
}

function chooseAnswer(container, index) {
  const question = state.questions[state.current];
  const selected = new Set(state.selected[question.id] || []);
  if (question.multiple) {
    if (selected.has(index)) selected.delete(index);
    else selected.add(index);
    state.selected[question.id] = [...selected].sort((a, b) => a - b);
  } else {
    state.selected[question.id] = [index];
  }
  renderSession(container);
}

async function submitCurrent(container) {
  const question = state.questions[state.current];
  const selected = state.selected[question.id] || [];
  if (!selected.length) {
    showToast("Select an answer before submitting", "error");
    return;
  }
  if (state.mode === "exam" && !state.examSubmitted) {
    showToast("Answer saved. It will be graded after Finish test.", "success");
    if (state.current < state.questions.length - 1) move(container, 1);
    else renderSession(container);
    return;
  }
  if (state.submitted[question.id]) return;
  const detail = await ensureDetail(question.id);
  const correct = sameSet(selected, detail.correct || []);
  state.submitted[question.id] = { selected, correct };
  await recordAttempt(question.id, { selected, correct, mode: state.mode });
  renderSession(container);
}

async function finishSession(container) {
  if (!state.questions.length) return;
  if (state.mode === "exam" && !state.examSubmitted) {
    for (const question of state.questions) {
      const detail = await ensureDetail(question.id);
      const selected = state.selected[question.id] || [];
      const correct = sameSet(selected, detail.correct || []);
      state.submitted[question.id] = { selected, correct };
      await recordAttempt(question.id, { selected, correct, mode: "exam" });
    }
    state.examSubmitted = true;
  }
  renderScoreReport(container);
}

function renderScoreReport(container) {
  const submitted = Object.values(state.submitted);
  const total = state.questions.length;
  const correct = correctCount();
  const unanswered = total - Object.values(state.selected).filter((value) => value?.length).length;
  const incorrect = Math.max(0, total - correct - unanswered);
  const score = Math.round((correct / Math.max(1, total)) * 100);
  container.querySelector("#session").classList.add("hidden");
  const report = container.querySelector("#score-report");
  report.className = "panel score-report";
  report.innerHTML = `
    <p class="eyebrow">Score report</p>
    <h1>${correct}/${total} correct</h1>
    <div class="score-pill big">${score}%</div>
    <div class="simple-meter"><span style="width:${score}%"></span></div>
    <div class="metric-grid">
      <div class="metric"><strong>${correct}</strong><span>Correct</span></div>
      <div class="metric"><strong>${incorrect}</strong><span>Incorrect</span></div>
      <div class="metric"><strong>${unanswered}</strong><span>Unanswered</span></div>
      <div class="metric"><strong>${submitted.length}</strong><span>Submitted</span></div>
    </div>
    <div class="action-row">
      <button id="review-misses" class="primary-btn" type="button">Review missed questions</button>
      <button id="retake" class="secondary-btn" type="button">Retake this test</button>
      <a class="secondary-btn" href="#/review">Go to Review</a>
    </div>
    <div id="miss-list" class="miss-list hidden"></div>
  `;
  report.querySelector("#retake").addEventListener("click", () => exitSession(container));
  report.querySelector("#review-misses").addEventListener("click", () => renderMisses(report));
}

function renderMisses(report) {
  const missed = state.questions.filter((question) => state.submitted[question.id] && !state.submitted[question.id].correct);
  const host = report.querySelector("#miss-list");
  host.className = "miss-list";
  host.innerHTML = missed.length
    ? missed
        .map((question, index) => `<button class="miss-row" data-id="${question.id}" type="button"><strong>${index + 1}. ${escapeHtml(question.question)}</strong><span>Review in session</span></button>`)
        .join("")
    : `<div class="success-state">No missed submitted questions.</div>`;
  host.querySelectorAll(".miss-row").forEach((button) => {
    button.addEventListener("click", () => {
      state.current = state.questions.findIndex((question) => question.id === button.dataset.id);
      report.classList.add("hidden");
      document.querySelector("#session").classList.remove("hidden");
      renderSession(document.querySelector("#view-root"));
    });
  });
}

function exitSession(container) {
  state.questions = [];
  state.details = {};
  state.selected = {};
  state.submitted = {};
  state.current = 0;
  state.examSubmitted = false;
  document.body.classList.remove("quiz-active");
  container.querySelector("#session").classList.add("hidden");
  container.querySelector("#score-report").classList.add("hidden");
  container.querySelector("#quiz-setup").classList.remove("hidden");
}

function renderExplanation(question) {
  if (!shouldShowExplanation(question)) return "";
  const detail = state.details[question.id];
  const submitted = state.submitted[question.id];
  return `
    <div class="result-banner ${submitted.correct ? "correct" : "incorrect"}">${submitted.correct ? "Correct" : "Incorrect"}</div>
    <p>${escapeHtml(detail.explanation || "No explanation was included with this downloaded question.")}</p>
    <div class="note-row">
      <button id="flashcard" class="secondary-btn" type="button">Add flashcard</button>
      <input id="note" placeholder="Write a note for this question" />
      <button id="save-note" class="secondary-btn" type="button">Save note</button>
    </div>`;
}

function wireExplanationActions(host, question) {
  const flashcard = host.querySelector("#flashcard");
  const saveNote = host.querySelector("#save-note");
  if (!flashcard || !saveNote) return;
  flashcard.addEventListener("click", async () => {
    const detail = state.details[question.id];
    const back = (detail.correct || []).map((idx) => detail.options[idx]).join("; ") + "\n\n" + (detail.explanation || "");
    await addFlashcard({ front: detail.question, back, source: "question", source_id: detail.id, tags: detail.tags || [] });
    showToast("Flashcard added", "success");
  });
  saveNote.addEventListener("click", async () => {
    const detail = state.details[question.id];
    const body = host.querySelector("#note").value.trim();
    if (!body) return;
    await addQuestionNote(detail.id, body);
    host.querySelector("#note").value = "";
    showToast("Note saved", "success");
  });
}

async function askTutor(container) {
  const question = state.questions[state.current];
  const panel = container.querySelector("#tutor-panel");
  panel.className = "panel tutor-panel";
  panel.innerHTML = `<p class="eyebrow">Local tutor</p><div class="loading-state">Searching local course context...</div>`;
  try {
    const selected = state.selected[question.id] || [];
    const result = await askBrain({
      question: `Explain this practice question. Question: ${question.question}. Selected answer indexes: ${selected.join(", ") || "none"}`,
      context_limit: 6,
      course_id: question.course_id,
      question_id: question.id,
      selected_answer: selected,
    });
    panel.innerHTML = `<p class="eyebrow">Local tutor</p><pre>${escapeHtml(result.answer || "No answer found.")}</pre>`;
  } catch (error) {
    panel.innerHTML = `<div class="error-state">${escapeHtml(error.message)}</div>`;
  }
}

function submitButtonLabel(question) {
  if (state.examSubmitted) return "Test submitted";
  if (state.mode === "exam") return "Save and next";
  return state.submitted[question.id] ? "Submitted" : "Submit answer";
}

function shouldShowExplanation(question) {
  return Boolean(state.submitted[question.id] && state.details[question.id]);
}

function answerClass(question, index) {
  if (!shouldShowExplanation(question)) return "";
  const detail = state.details[question.id];
  const submitted = state.submitted[question.id];
  const correct = new Set(detail.correct || []);
  const selected = new Set(submitted.selected || []);
  if (correct.has(index)) return "correct";
  if (selected.has(index)) return "incorrect";
  return "";
}

function currentTest() {
  return state.tests.find((test) => test.test_id === state.selectedTestId);
}

function filteredTests(container) {
  const trackId = container.querySelector("#track-filter")?.value;
  const courseId = container.querySelector("#course-filter")?.value;
  return state.tests.filter((test) => (!trackId || test.track_id === trackId) && (!courseId || test.course_id === courseId));
}

function correctCount() {
  return Object.values(state.submitted).filter((item) => item.correct).length;
}

function move(container, delta) {
  state.current = Math.max(0, Math.min(state.questions.length - 1, state.current + delta));
  renderSession(container);
}

function toggleReview(container) {
  const id = state.questions[state.current].id;
  if (state.review.has(id)) state.review.delete(id);
  else state.review.add(id);
  renderSession(container);
}

async function bookmark(container) {
  const id = state.questions[state.current].id;
  const result = await toggleBookmark(id);
  showToast(result.bookmarked ? "Bookmarked" : "Bookmark removed", "success");
}

async function ensureDetail(id) {
  if (!state.details[id]) state.details[id] = await getQuestion(id);
  return state.details[id];
}

function sameSet(a, b) {
  const left = [...a].sort((x, y) => x - y);
  const right = [...b].sort((x, y) => x - y);
  return left.length === right.length && left.every((item, index) => item === right[index]);
}

function handleKeys(event) {
  const container = document.querySelector("#view-root");
  if (!container || !state.questions.length || ["INPUT", "TEXTAREA", "SELECT"].includes(event.target.tagName)) return;
  if (event.key === "ArrowLeft") move(container, -1);
  if (event.key === "ArrowRight") move(container, 1);
  if (event.code === "Space") {
    event.preventDefault();
    submitCurrent(container);
  }
}

function resolveDefaultQuizSelection(params) {
  const requestedTest = state.tests.find((test) => test.test_id === params.test_id);
  if (requestedTest) return { trackId: requestedTest.track_id, courseId: requestedTest.course_id, testId: requestedTest.test_id };
  const requestedCourse = state.courses.find((course) => course.id === params.course_id);
  const savedTest = state.tests.find((test) => test.test_id === localStorage.getItem(QUIZ_TEST_KEY));
  if (savedTest && (!params.track_id || savedTest.track_id === params.track_id) && (!requestedCourse || savedTest.course_id === requestedCourse.id)) {
    return { trackId: savedTest.track_id, courseId: savedTest.course_id, testId: savedTest.test_id };
  }
  const preferredTrack = params.track_id || requestedCourse?.track_id || localStorage.getItem(QUIZ_TRACK_KEY) || "snowpro-core";
  const preferredCourseId = requestedCourse?.id || localStorage.getItem(QUIZ_COURSE_KEY);
  const firstCourseTest = pickBestTest(state.tests.filter((test) => test.course_id === preferredCourseId && (!preferredTrack || test.track_id === preferredTrack)));
  if (firstCourseTest) return { trackId: firstCourseTest.track_id, courseId: firstCourseTest.course_id, testId: firstCourseTest.test_id };
  const bestTrackTest = pickBestTest(state.tests.filter((test) => test.track_id === preferredTrack));
  if (bestTrackTest) return { trackId: bestTrackTest.track_id, courseId: bestTrackTest.course_id, testId: bestTrackTest.test_id };
  const fallback = pickBestTest(state.tests.filter((test) => test.track_id === "snowpro-core")) || pickBestTest(state.tests);
  return { trackId: fallback?.track_id || "", courseId: fallback?.course_id || "", testId: fallback?.test_id || "" };
}

function pickBestTest(tests) {
  return [...tests].sort((a, b) => {
    const scoreA = Number(a.question_count || 0) >= 50 ? 0 : 1;
    const scoreB = Number(b.question_count || 0) >= 50 ? 0 : 1;
    return scoreA - scoreB || Number(a.test_position || 0) - Number(b.test_position || 0) || Number(b.question_count || 0) - Number(a.question_count || 0);
  })[0];
}

function selectFirstVisibleTest(container) {
  const first = filteredTests(container).sort((a, b) => Number(a.test_position || 0) - Number(b.test_position || 0))[0];
  state.selectedTestId = first?.test_id || "";
  if (state.selectedTestId) localStorage.setItem(QUIZ_TEST_KEY, state.selectedTestId);
}
