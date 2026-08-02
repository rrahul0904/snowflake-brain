export const VIEW_ID = "academy";

import {
  completeDataAiLesson,
  escapeHtml,
  getDataAiCurriculum,
  submitDataAiCheck,
  submitDataAiLab,
} from "../api.js?v=20260714-v20-ai-academy";
import { emptyState, skeleton } from "../ui.js?v=20260714-v20-ai-academy";
import { showToast } from "../components/toast.js?v=20260714-v20-ai-academy";

const state = {
  curriculum: null,
  activeLessonId: null,
  selectedAnswer: null,
  checkResult: null,
  labResult: null,
  labDrafts: {},
};

export default async function mount(container, params = {}) {
  container.innerHTML = skeleton("Loading AI Academy...");
  try {
    state.curriculum = await getDataAiCurriculum();
    const lessons = allLessons();
    state.activeLessonId = params.lesson_id || lessons.find((lesson) => !lesson.completed)?.id || lessons[0]?.id;
    state.selectedAnswer = null;
    state.checkResult = null;
    state.labResult = null;
    render(container);
  } catch (error) {
    showToast(error.message, "error");
    container.innerHTML = emptyState("AI Academy unavailable", error.message, `<button onclick="location.reload()">Retry</button>`);
  }
}

function allLessons() {
  return (state.curriculum?.modules || []).flatMap((module) => module.lessons || []);
}

function activeLesson() {
  return allLessons().find((lesson) => lesson.id === state.activeLessonId) || allLessons()[0];
}

function activeModule() {
  return (state.curriculum?.modules || []).find((module) => (module.lessons || []).some((lesson) => lesson.id === state.activeLessonId));
}

function activeLab(lesson) {
  if (!lesson?.lab_id) return null;
  return (state.curriculum?.labs || []).find((lab) => lab.id === lesson.lab_id) || null;
}

function render(container) {
  const curriculum = state.curriculum;
  const lesson = activeLesson();
  const module = activeModule();
  const progress = curriculum.progress || {};
  if (!lesson || !module) {
    container.innerHTML = emptyState("No AI lessons found", "The curriculum does not contain any lessons yet.");
    return;
  }
  const lab = activeLab(lesson);
  const lessonIndex = allLessons().findIndex((item) => item.id === lesson.id);
  const nextLesson = allLessons()[lessonIndex + 1];

  container.innerHTML = `
    <section class="page-shell academy-page">
      <header class="academy-hero">
        <div>
          <p class="eyebrow">AI Academy · Phase 1</p>
          <h1>Build the systems behind production AI.</h1>
          <p>Technical lessons, immediate checks, and validated exercises across product data, machine learning, LLM applications, and responsible operations.</p>
        </div>
        <div class="academy-progress-orb" style="--academy-progress:${progress.percent || 0}">
          <strong>${progress.percent || 0}%</strong><span>evidence complete</span>
        </div>
      </header>

      <section class="academy-stats" aria-label="AI Academy progress">
        ${progressStat(progress.lessons_completed, progress.total_lessons, "Lessons", "Read and completed")}
        ${progressStat(progress.checks_passed, progress.total_checks, "Checks", "Correctly answered")}
        ${progressStat(progress.labs_passed, progress.total_labs, "Labs", "Validation passed")}
        ${progressStat(curriculum.estimated_hours, "hours", "Phase 1", "Estimated effort")}
      </section>

      <section class="academy-workspace">
        <aside class="academy-outline panel">
          <div class="academy-outline-header"><p class="eyebrow">Curriculum</p><h2>${escapeHtml(curriculum.title)}</h2><span>${allLessons().length} lessons · ${(curriculum.labs || []).length} labs</span></div>
          <div class="academy-module-list">
            ${(curriculum.modules || []).map(moduleItem).join("")}
          </div>
        </aside>

        <main class="academy-lesson panel">
          <header class="academy-lesson-header">
            <div><p class="eyebrow">${escapeHtml(module.title)} · Lesson ${lessonIndex + 1} of ${allLessons().length}</p><h2>${escapeHtml(lesson.title)}</h2></div>
            <div class="academy-lesson-meta"><span>${lesson.duration_minutes} min</span><span>${escapeHtml(module.level)}</span>${lesson.completed ? "<b>Completed</b>" : ""}</div>
          </header>

          <section class="academy-objectives">
            <h3>Learning objectives</h3>
            <ul>${(lesson.objectives || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
          </section>

          <section class="academy-explanation">
            <h3>Core idea</h3>
            <p>${escapeHtml(lesson.explanation)}</p>
          </section>

          <section class="academy-concept-grid">
            ${(lesson.concepts || []).map((concept) => `<article><span></span><h3>${escapeHtml(concept.title)}</h3><p>${escapeHtml(concept.body)}</p></article>`).join("")}
          </section>

          <section class="academy-code-block">
            <header><span>${escapeHtml(lesson.code_language || "text")}</span><strong>Reference pattern</strong></header>
            <pre><code>${escapeHtml(lesson.code || "")}</code></pre>
          </section>

          ${knowledgeCheck(lesson)}
          ${lab ? labWorkspace(lab) : ""}

          <footer class="academy-lesson-actions">
            <button class="secondary-btn" id="complete-ai-lesson" ${lesson.completed ? "disabled" : ""}>${lesson.completed ? "Lesson completed" : "Mark lesson complete"}</button>
            ${nextLesson ? `<button class="primary-btn" data-next-lesson="${escapeHtml(nextLesson.id)}">Next lesson</button>` : `<a class="primary-btn" href="#/career">Return to Career Lab</a>`}
          </footer>
        </main>
      </section>
    </section>`;
  bind(container);
}

function progressStat(value, total, label, detail) {
  const display = total === "hours" ? `${value}h` : `${value || 0}/${total || 0}`;
  return `<article><strong>${display}</strong><span>${label}</span><small>${detail}</small></article>`;
}

function moduleItem(module) {
  const lessons = module.lessons || [];
  const completed = lessons.filter((lesson) => lesson.completed).length;
  const active = lessons.some((lesson) => lesson.id === state.activeLessonId);
  return `<section class="academy-module ${active ? "active" : ""}">
    <header><div><span>${escapeHtml(module.level)}</span><strong>${escapeHtml(module.title)}</strong></div><small>${completed}/${lessons.length}</small></header>
    <div>${lessons.map((lesson) => `<button class="academy-lesson-link ${lesson.id === state.activeLessonId ? "active" : ""}" data-ai-lesson="${escapeHtml(lesson.id)}"><span>${lesson.completed ? "✓" : ""}</span><strong>${escapeHtml(lesson.title)}</strong><small>${lesson.duration_minutes}m${lesson.knowledge_check?.passed ? " · check passed" : ""}</small></button>`).join("")}</div>
  </section>`;
}

function knowledgeCheck(lesson) {
  const check = lesson.knowledge_check || {};
  const result = state.checkResult;
  return `<section class="academy-check ${check.passed ? "passed" : ""}">
    <div class="academy-section-title"><div><p class="eyebrow">Knowledge check</p><h3>${escapeHtml(check.question)}</h3></div>${check.passed ? "<span>Passed</span>" : ""}</div>
    <div class="academy-options">
      ${(check.options || []).map((option, index) => {
        const selected = state.selectedAnswer === index;
        const correct = result && result.correct_index === index;
        const incorrect = result && selected && !result.correct;
        return `<button data-answer="${index}" class="${selected ? "selected" : ""} ${correct ? "correct" : ""} ${incorrect ? "incorrect" : ""}" ${result ? "disabled" : ""}><span>${String.fromCharCode(65 + index)}</span>${escapeHtml(option)}</button>`;
      }).join("")}
    </div>
    ${result ? `<div class="academy-feedback ${result.correct ? "correct" : "incorrect"}"><strong>${result.correct ? "Correct" : "Review this"}</strong><p>${escapeHtml(result.explanation)}</p></div>` : ""}
    <button class="primary-btn" id="submit-ai-check" ${state.selectedAnswer === null || result ? "disabled" : ""}>${check.passed && !result ? "Check passed" : "Check answer"}</button>
  </section>`;
}

function labWorkspace(lab) {
  const result = state.labResult;
  const draft = state.labDrafts[lab.id] ?? lab.starter_code ?? "";
  return `<section class="academy-lab ${lab.completed ? "passed" : ""}">
    <div class="academy-section-title"><div><p class="eyebrow">Hands-on evidence · ${escapeHtml(lab.language)}</p><h3>${escapeHtml(lab.title)}</h3></div>${lab.completed ? "<span>Passed</span>" : `<span>${lab.estimated_minutes} min</span>`}</div>
    <p>${escapeHtml(lab.scenario)}</p>
    <div class="academy-lab-grid">
      <div><h4>Requirements</h4><ul>${(lab.requirements || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul></div>
      <div class="academy-editor"><header><span>${escapeHtml(lab.language)} workspace</span><small>Safe offline validation</small></header><textarea id="ai-lab-editor" spellcheck="false">${escapeHtml(draft)}</textarea><button class="primary-btn" id="validate-ai-lab">Run validation</button></div>
    </div>
    ${result ? labResults(result) : ""}
  </section>`;
}

function labResults(result) {
  return `<div class="academy-lab-results ${result.passed ? "passed" : "failed"}">
    <header><strong>${result.passed ? "Lab passed" : "Validation incomplete"}</strong><span>${result.passed_count}/${result.total} checks · ${result.score_pct}%</span></header>
    <div>${(result.results || []).map((item) => `<p><span>${item.passed ? "✓" : "×"}</span><strong>${escapeHtml(item.name)}</strong><small>${escapeHtml(item.message)}</small></p>`).join("")}</div>
    ${result.solution ? `<details><summary>Review one valid solution</summary><pre>${escapeHtml(result.solution)}</pre></details>` : ""}
  </div>`;
}

async function refresh(container) {
  state.curriculum = await getDataAiCurriculum();
  render(container);
}

function selectLesson(container, lessonId) {
  state.activeLessonId = lessonId;
  state.selectedAnswer = null;
  state.checkResult = null;
  state.labResult = null;
  render(container);
  container.closest(".view-root")?.scrollTo({ top: 0, behavior: "smooth" });
}

function bind(container) {
  container.querySelectorAll("[data-ai-lesson]").forEach((button) => button.addEventListener("click", () => selectLesson(container, button.dataset.aiLesson)));
  container.querySelectorAll("[data-answer]").forEach((button) => button.addEventListener("click", () => {
    state.selectedAnswer = Number(button.dataset.answer);
    state.checkResult = null;
    render(container);
  }));
  container.querySelector("#submit-ai-check")?.addEventListener("click", async () => {
    const lesson = activeLesson();
    try {
      state.checkResult = await submitDataAiCheck(lesson.knowledge_check.id, state.selectedAnswer);
      if (state.checkResult.correct) {
        state.curriculum = await getDataAiCurriculum();
        showToast("Knowledge check passed", "success");
      }
      render(container);
    } catch (error) {
      showToast(error.message, "error");
    }
  });
  container.querySelector("#complete-ai-lesson")?.addEventListener("click", async () => {
    try {
      await completeDataAiLesson(activeLesson().id);
      await refresh(container);
      showToast("Lesson evidence recorded", "success");
    } catch (error) {
      showToast(error.message, "error");
    }
  });
  container.querySelector("#validate-ai-lab")?.addEventListener("click", async () => {
    const lab = activeLab(activeLesson());
    const editor = container.querySelector("#ai-lab-editor");
    state.labDrafts[lab.id] = editor?.value || "";
    try {
      state.labResult = await submitDataAiLab(lab.id, state.labDrafts[lab.id]);
      if (state.labResult.passed) {
        state.curriculum = await getDataAiCurriculum();
        showToast("Lab evidence recorded", "success");
      }
      render(container);
    } catch (error) {
      showToast(error.message, "error");
    }
  });
  container.querySelector("[data-next-lesson]")?.addEventListener("click", (event) => selectLesson(container, event.currentTarget.dataset.nextLesson));
}
