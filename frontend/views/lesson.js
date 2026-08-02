export const VIEW_ID = "lesson";

import { askBrain, escapeHtml, getLesson, getLessons, getTranscript, recordLessonProgress } from "../api.js?v=20260731-v21-editorial-replica";
import { activeTrack } from "../ui.js?v=20260731-v21-editorial-replica";

let activeTab = "overview";

export default async function mount(container, params = {}) {
  const trackId = params.track_id || activeTrack();
  let lessonId = params.lesson_id || "";
  if (!lessonId) {
    const first = await getLessons({ track_id: trackId, limit: 1 });
    lessonId = first.lessons?.[0]?.id || "";
  }
  if (!lessonId) throw new Error("No lesson is available for this certification.");
  const [lesson, transcript, outline] = await Promise.all([
    getLesson(lessonId),
    getTranscript(lessonId).catch(() => ({ chunks: [] })),
    getLessons({ track_id: trackId, limit: 200 }),
  ]);
  render(container, lesson, transcript.chunks || [], outline.lessons || [], trackId);
}

function render(container, lesson, chunks, lessons, trackId) {
  const media = lesson.video_path ? `/api/media?path=${encodeURIComponent(lesson.video_path)}` : "";
  container.innerHTML = `
    <div class="replica-lesson replica-enter">
      <div class="replica-lesson-breadcrumb"><a href="#/curriculum?track_id=${encodeURIComponent(trackId)}">Curriculum</a><span>/</span><span>${escapeHtml(lesson.course_title || "Course")}</span></div>
      <section class="replica-video-stage">
        ${media ? `<video id="replica-lesson-video" controls preload="metadata" playsinline src="${media}"></video>` : `<div class="replica-media-empty"><strong>Video unavailable</strong><span>Study notes remain available below.</span></div>`}
      </section>
      <header class="replica-lesson-heading">
        <div><p class="replica-kicker">${escapeHtml(lesson.section || "Lesson")}</p><h1>${escapeHtml(lesson.title)}</h1><p>${escapeHtml(lesson.course_title || "Snowflake course")}</p></div>
        <button id="lesson-complete" type="button">Mark complete</button>
      </header>
      <nav class="replica-lesson-tabs" aria-label="Lesson sections">
        ${[["overview","Overview"],["transcript","Transcript"],["notes","Notes"],["tutor","Ask Tutor"]].map(([id,label]) => `<button data-tab="${id}" class="${activeTab === id ? "active" : ""}" type="button">${label}</button>`).join("")}
      </nav>
      <div class="replica-lesson-layout">
        <main id="replica-lesson-content" class="replica-lesson-content"></main>
        <aside class="replica-outline">
          <div><p class="replica-kicker">Course content</p><h2>${escapeHtml(lesson.course_title || "Lessons")}</h2></div>
          <div class="replica-outline-scroll">
            ${lessons.filter((item) => item.course_id === lesson.course_id).map((item, index) => `<a class="${item.id === lesson.id ? "active" : ""}" href="#/lesson?track_id=${encodeURIComponent(trackId)}&lesson_id=${encodeURIComponent(item.id)}"><span>${String(index + 1).padStart(2,"0")}</span><strong>${escapeHtml(item.title)}</strong></a>`).join("")}
          </div>
        </aside>
      </div>
    </div>`;
  renderTab(container, lesson, chunks, trackId);
  container.querySelectorAll("[data-tab]").forEach((button) => button.addEventListener("click", () => {
    activeTab = button.dataset.tab;
    container.querySelectorAll("[data-tab]").forEach((node) => node.classList.toggle("active", node === button));
    renderTab(container, lesson, chunks, trackId);
  }));
  container.querySelector("#lesson-complete")?.addEventListener("click", async (event) => {
    await recordLessonProgress({ lesson_id: lesson.id, completed: true, progress_pct: 100 });
    event.currentTarget.textContent = "Completed";
    event.currentTarget.disabled = true;
  });
}

function renderTab(container, lesson, chunks, trackId) {
  const host = container.querySelector("#replica-lesson-content");
  const notesOnly = chunks.length && chunks.every((chunk) => Number(chunk.start_s || 0) === 0);
  if (activeTab === "transcript") {
    host.innerHTML = `<article class="replica-reading"><p class="replica-kicker">${notesOnly ? "Generated notes" : `${chunks.length} transcript cues`}</p><h2>${notesOnly ? "Study notes" : "Transcript"}</h2><div class="replica-transcript">${chunks.length ? chunks.map((chunk) => `<button data-seek="${Number(chunk.start_s || 0)}" type="button"><span>${formatTime(chunk.start_s)}</span><p>${escapeHtml(chunk.text || "")}</p></button>`).join("") : `<p>No English transcript was indexed for this lesson.</p>`}</div></article>`;
    const video = container.querySelector("#replica-lesson-video");
    host.querySelectorAll("[data-seek]").forEach((button) => button.addEventListener("click", () => {
      if (!video) return;
      video.currentTime = Number(button.dataset.seek || 0);
      video.play().catch(() => {});
    }));
    return;
  }
  if (activeTab === "notes") {
    host.innerHTML = `<article class="replica-reading"><p class="replica-kicker">Private notes</p><h2>Capture what matters.</h2><textarea id="lesson-note" placeholder="Write your notes for this lesson..."></textarea><div class="replica-note-actions"><button id="save-note" type="button">Save locally</button><span id="note-status"></span></div></article>`;
    const key = `snowflake-studio.lesson-note.${lesson.id}`;
    const area = host.querySelector("#lesson-note");
    area.value = localStorage.getItem(key) || "";
    host.querySelector("#save-note").addEventListener("click", () => {
      localStorage.setItem(key, area.value);
      host.querySelector("#note-status").textContent = "Saved";
    });
    return;
  }
  if (activeTab === "tutor") {
    host.innerHTML = `<article class="replica-reading replica-tutor"><p class="replica-kicker">Contextual tutor</p><h2>Ask from this lesson.</h2><div id="tutor-messages"><p>Ask for an explanation, comparison, example, or follow-up question. Answers are grounded in your local archive.</p></div><form id="tutor-form"><input id="tutor-question" placeholder="What should I understand about ${escapeHtml(lesson.title)}?" required><button type="submit">Ask</button></form></article>`;
    host.querySelector("#tutor-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const input = host.querySelector("#tutor-question");
      const messages = host.querySelector("#tutor-messages");
      const question = input.value.trim();
      if (!question) return;
      messages.innerHTML = `<p>Searching the selected course context...</p>`;
      try {
        const response = await askBrain({ question: `${question}\nCurrent lesson: ${lesson.title}\nCourse: ${lesson.course_title}`, context_limit: 6, track_id: trackId, lesson_id: lesson.id });
        const answer = response.answer || response.response || response.text || "No grounded answer was returned.";
        const sources = response.sources || response.citations || [];
        messages.innerHTML = `<div class="replica-tutor-answer"><p>${escapeHtml(answer)}</p>${sources.length ? `<div>${sources.slice(0,6).map((source) => `<a href="${source.lesson_id ? `#/lesson?lesson_id=${encodeURIComponent(source.lesson_id)}` : "#/reference"}">${escapeHtml(source.title || source.course_title || "Course source")}</a>`).join("")}</div>` : ""}</div>`;
      } catch (error) {
        messages.innerHTML = `<p>${escapeHtml(error.message)}</p>`;
      }
    });
    return;
  }
  host.innerHTML = `<article class="replica-reading"><p class="replica-kicker">Lesson overview</p><h2>${escapeHtml(lesson.title)}</h2><p class="replica-lead">${escapeHtml(lesson.excerpt || "Study this lesson, capture the key idea, and prove recall with practice questions.")}</p><div class="replica-study-actions"><a href="#/practice?track_id=${encodeURIComponent(trackId)}&course_id=${encodeURIComponent(lesson.course_id || "")}">Practice this course →</a><button data-open-tutor type="button">Ask about this lesson</button></div></article>`;
  host.querySelector("[data-open-tutor]")?.addEventListener("click", () => {
    activeTab = "tutor";
    container.querySelectorAll("[data-tab]").forEach((node) => node.classList.toggle("active", node.dataset.tab === "tutor"));
    renderTab(container, lesson, chunks, trackId);
  });
}

function formatTime(value) {
  const seconds = Math.floor(Number(value || 0));
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

