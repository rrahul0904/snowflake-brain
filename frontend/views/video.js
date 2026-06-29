import { escapeHtml, formatNumber, getCourses, getLesson, getLessons, getTracks, getTranscript, recordLessonProgress } from "../api.js";
import { showToast } from "../components/toast.js";

const state = {
  tracks: [],
  courses: [],
  lessons: [],
  activeLessonId: null,
  activeLesson: null,
  chunks: [],
  notesOnly: false,
  activeTab: "transcript",
};

const LESSON_TRACK_KEY = "snowflake-brain.lesson-track";
const LESSON_COURSE_KEY = "snowflake-brain.lesson-course";

export default async function mount(container, params = {}) {
  container.innerHTML = `
    <section class="rescue-page lessons-page">
      <header class="page-header rescue-header">
        <div>
          <p class="eyebrow">Learn</p>
          <h1>Study the lessons that move your exam score</h1>
          <p class="page-subtitle">Use the videos as exam preparation: understand the concept, check transcript quality, then practice the related questions.</p>
        </div>
        <a class="secondary-btn" href="#/today">Back to Today</a>
      </header>

      <div class="toolbar lesson-toolbar">
        <label class="field"><span>Certification</span><select id="track-select"></select></label>
        <label class="field"><span>Course</span><select id="course-select"></select></label>
        <label class="field grow"><span>Search within course</span><input id="lesson-search" placeholder="warehouse, RBAC, Snowpipe..." /></label>
      </div>

      <div id="lesson-breadcrumb" class="breadcrumb muted">Loading course...</div>

      <section class="lesson-workspace">
        <aside class="panel lesson-outline-panel">
          <div class="panel-header"><div><p class="eyebrow">Course path</p><h2>Lessons in order</h2></div><span id="lesson-count" class="status-badge">0</span></div>
          <div id="lessons" class="course-outline empty-state">Loading lessons...</div>
        </aside>

        <main id="player" class="panel lesson-stage">
          <div class="empty-state"><h2>Select a lesson</h2><p>Choose a lesson from the outline.</p></div>
        </main>

        <aside id="study-panel" class="panel study-panel">
          <div class="empty-state"><h2>Study panel</h2><p>Lesson actions will appear here.</p></div>
        </aside>
      </section>
    </section>
  `;

  try {
    const [tracks, courses] = await Promise.all([getTracks(), getCourses()]);
    state.tracks = tracks.tracks || [];
    state.courses = (courses.courses || []).filter((course) => course.lesson_count > 0);

    let requestedCourseId = params.course_id;
    if (!requestedCourseId && params.lesson_id) {
      const lesson = await getLesson(params.lesson_id);
      requestedCourseId = lesson.course_id;
    }
    const defaultCourse = resolveDefaultLessonCourse(requestedCourseId, params.track_id);
    renderTrackSelect(container, defaultCourse?.track_id || params.track_id, defaultCourse?.id);
    renderCourseSelect(container, defaultCourse?.id || requestedCourseId);
    await loadLessons(container, params.lesson_id);
  } catch (error) {
    showToast(error.message, "error");
    container.querySelector("#player").innerHTML = `<div class="error-state">${escapeHtml(error.message)}</div>`;
  }

  container.querySelector("#track-select").addEventListener("change", () => {
    state.activeLessonId = null;
    localStorage.setItem(LESSON_TRACK_KEY, container.querySelector("#track-select").value);
    renderCourseSelect(container);
    loadLessons(container);
  });
  container.querySelector("#course-select").addEventListener("change", () => {
    state.activeLessonId = null;
    localStorage.setItem(LESSON_COURSE_KEY, container.querySelector("#course-select").value);
    loadLessons(container);
  });
  container.querySelector("#lesson-search").addEventListener("input", () => loadLessons(container));
}

function renderTrackSelect(container, requestedTrackId, requestedCourseId) {
  const course = state.courses.find((item) => item.id === requestedCourseId);
  const lessonTracks = new Set(state.courses.map((item) => item.track_id).filter(Boolean));
  const tracks = state.tracks.filter((track) => lessonTracks.has(track.id));
  const select = container.querySelector("#track-select");
  select.innerHTML = tracks.map((track) => `<option value="${track.id}">${escapeHtml(track.title)} (${formatNumber(track.lesson_count)})</option>`).join("");
  const preferredTrack = requestedTrackId || course?.track_id || localStorage.getItem(LESSON_TRACK_KEY) || "snowpro-core";
  select.value = tracks.some((track) => track.id === preferredTrack) ? preferredTrack : tracks[0]?.id || "";
}

function renderCourseSelect(container, requestedCourseId) {
  const trackId = container.querySelector("#track-select").value;
  const sorted = state.courses
    .filter((course) => !trackId || course.track_id === trackId)
    .sort((a, b) => (b.lesson_count || 0) - (a.lesson_count || 0));
  const select = container.querySelector("#course-select");
  select.innerHTML = sorted.map((course) => `<option value="${course.id}">${escapeHtml(course.title)} (${formatNumber(course.lesson_count)})</option>`).join("");
  const saved = localStorage.getItem(LESSON_COURSE_KEY);
  const requested = sorted.find((course) => course.id === requestedCourseId) || sorted.find((course) => course.id === saved);
  select.value = requested?.id || sorted[0]?.id || "";
  if (select.value) localStorage.setItem(LESSON_COURSE_KEY, select.value);
  updateBreadcrumb(container);
}

async function loadLessons(container, openLessonId = null) {
  const courseId = container.querySelector("#course-select").value;
  const q = container.querySelector("#lesson-search").value.trim();
  if (!courseId) {
    container.querySelector("#lessons").innerHTML = `<div class="empty-state">No course with lessons was found for this track.</div>`;
    return;
  }

  try {
    const data = await getLessons({ course_id: courseId, q, limit: 3000 });
    state.lessons = data.lessons || [];
    container.querySelector("#lesson-count").textContent = formatNumber(state.lessons.length);
    renderLessons(container);
    updateBreadcrumb(container);
    const activeExists = state.lessons.some((lesson) => lesson.id === state.activeLessonId);
    const target = openLessonId || (activeExists ? state.activeLessonId : state.lessons[0]?.id);
    if (target) await openLesson(container, target);
  } catch (error) {
    showToast(error.message, "error");
  }
}

function renderLessons(container) {
  const host = container.querySelector("#lessons");
  if (!state.lessons.length) {
    host.className = "course-outline empty-state";
    host.textContent = "No lessons match this course/search.";
    return;
  }
  host.className = "course-outline";
  host.innerHTML = groupLessons()
    .map(
      (group, groupIndex) => `
        <details class="outline-section" ${groupIndex === 0 || group.lessons.some((lesson) => lesson.id === state.activeLessonId) ? "open" : ""}>
          <summary><strong>${escapeHtml(group.title)}</strong><small>${group.lessons.length} lessons</small></summary>
          <div class="outline-lessons">
            ${group.lessons
              .map((lesson) => {
                const globalIndex = state.lessons.findIndex((item) => item.id === lesson.id) + 1;
                return `<button class="lesson-row ${lesson.id === state.activeLessonId ? "active" : ""}" data-id="${lesson.id}" type="button">
                  <span class="lesson-number">${globalIndex}</span>
                  <span class="lesson-copy"><strong>${escapeHtml(lesson.title)}</strong><small>${formatDuration(lesson.duration_s || lesson.duration)}</small></span>
                </button>`;
              })
              .join("")}
          </div>
        </details>`,
    )
    .join("");
  host.querySelectorAll(".lesson-row").forEach((button) => button.addEventListener("click", () => openLesson(container, button.dataset.id)));
}

async function openLesson(container, id) {
  state.activeLessonId = id;
  state.activeTab = "transcript";
  renderLessons(container);
  try {
    const [lesson, transcript] = await Promise.all([getLesson(id), getTranscript(id)]);
    state.activeLesson = lesson;
    state.chunks = transcript.chunks || [];
    state.notesOnly = state.chunks.length === 1 && /English study notes/i.test(state.chunks[0].text || "");
    updateBreadcrumb(container);
    updateUrl(container, lesson);
    renderLessonStage(container);
    renderStudyPanel(container);
  } catch (error) {
    showToast(error.message, "error");
  }
}

function renderLessonStage(container) {
  const lesson = state.activeLesson;
  if (!lesson) return;
  const media = lesson.video_path ? `/api/media?path=${encodeURIComponent(lesson.video_path)}` : "";
  container.querySelector("#player").innerHTML = `
    <div class="lesson-title-block">
      <div>
        <p class="eyebrow">${escapeHtml(lesson.section || "Course")}</p>
        <h2>${escapeHtml(lesson.title)}</h2>
      </div>
      ${qualityBadge(state.chunks, state.notesOnly)}
    </div>
    <div class="player-video-wrap compact-video">
      ${media ? `<video id="video" controls src="${media}"></video>` : `<div class="video-empty">No video file found for this lesson.</div>`}
    </div>
    <div class="lesson-tabbar">
      <button class="${state.activeTab === "transcript" ? "active" : ""}" data-tab="transcript" type="button">Transcript / Notes</button>
      <button class="${state.activeTab === "overview" ? "active" : ""}" data-tab="overview" type="button">Overview</button>
    </div>
    <section id="lesson-tab-panel" class="lesson-tab-panel">${renderTabPanel(lesson)}</section>
  `;
  container.querySelectorAll(".lesson-tabbar button").forEach((button) => {
    button.addEventListener("click", () => {
      state.activeTab = button.dataset.tab;
      renderLessonStage(container);
    });
  });
  wireTranscript(container);
}

function renderStudyPanel(container) {
  const lesson = state.activeLesson;
  if (!lesson) return;
  const index = state.lessons.findIndex((item) => item.id === lesson.id);
  const next = state.lessons[index + 1];
  const related = lesson.related_questions || [];
  container.querySelector("#study-panel").innerHTML = `
    <div class="panel-header"><div><p class="eyebrow">Exam loop</p><h2>Finish, then practice</h2></div></div>
    <button id="mark-complete" class="primary-btn wide" type="button">Complete lesson and continue</button>
    ${next ? `<button id="next-lesson" class="secondary-btn wide" type="button">Next lesson</button>` : `<div class="success-state">This is the last lesson in the current list.</div>`}

    <div class="study-panel-section">
      <p class="eyebrow">Content quality</p>
      ${qualityBadge(state.chunks, state.notesOnly)}
      ${state.notesOnly ? `<div class="warning">Generated notes only. Original transcript was missing or unusable.</div>` : ""}
      ${!(lesson.duration_s || lesson.duration) ? `<div class="warning">Duration unavailable.</div>` : ""}
    </div>

    <div class="study-panel-section">
      <p class="eyebrow">Related questions</p>
      <div class="related-question-list compact">
        ${related.length ? related.slice(0, 5).map((question) => `<a class="related-question" href="#/practice?course_id=${encodeURIComponent(lesson.course_id)}"><strong>${escapeHtml(question.question)}</strong></a>`).join("") : `<div class="empty-state">No related questions indexed for this lesson.</div>`}
      </div>
      <a class="primary-btn wide" href="#/practice?mode=topic&course_id=${encodeURIComponent(lesson.course_id)}">Practice questions from this course</a>
    </div>
  `;
  container.querySelector("#mark-complete").addEventListener("click", async () => {
    try {
      await recordLessonProgress({ lesson_id: lesson.id, completed: true, watched_s: Math.floor(container.querySelector("#video")?.currentTime || 0) });
      showToast("Lesson marked complete", "success");
      if (next) await openLesson(container, next.id);
    } catch (error) {
      showToast(error.message, "error");
    }
  });
  const nextButton = container.querySelector("#next-lesson");
  if (nextButton && next) nextButton.addEventListener("click", () => openLesson(container, next.id));
}

function renderTabPanel(lesson) {
  if (state.activeTab === "overview") {
    return `
      <p class="lesson-overview-copy">${escapeHtml(lesson.excerpt || "This lesson is ready in the local Snowflake course library.")}</p>
      <div class="lesson-meta clean-meta">
        <span>${escapeHtml(lesson.course_title)}</span>
        <span>${formatDuration(lesson.duration_s || lesson.duration)}</span>
        <span>${state.notesOnly ? "Generated notes" : `${formatNumber(state.chunks.length)} transcript cues`}</span>
      </div>`;
  }
  return `
    <div class="transcript-head">
      <div><p class="eyebrow">${state.notesOnly ? "Generated notes" : "Transcript"}</p><h3>${state.notesOnly ? "English-only study notes" : "English transcript cues"}</h3></div>
    </div>
    <div id="transcript" class="${state.notesOnly ? "study-note-panel" : "transcript-list"}">${renderTranscript(state.chunks, state.notesOnly)}</div>`;
}

function renderTranscript(chunks, notesOnly) {
  if (!chunks.length) return `<div class="empty-state">No English transcript or notes were indexed for this lesson.</div>`;
  if (notesOnly) return `<p>${escapeHtml(chunks[0].text)}</p>`;
  return chunks
    .map((cue) => `<button class="cue" data-start="${cue.start_s || 0}" type="button"><span>${formatTime(cue.start_s)}</span><strong>${escapeHtml(cue.text)}</strong></button>`)
    .join("");
}

function groupLessons() {
  const groups = [];
  const byKey = new Map();
  for (const lesson of state.lessons) {
    const title = lesson.section || "Course";
    if (!byKey.has(title)) {
      const group = { title, lessons: [] };
      byKey.set(title, group);
      groups.push(group);
    }
    byKey.get(title).lessons.push(lesson);
  }
  return groups;
}

function resolveDefaultLessonCourse(requestedCourseId, requestedTrackId) {
  const requested = state.courses.find((course) => course.id === requestedCourseId);
  if (requested) return requested;
  const savedCourse = state.courses.find((course) => course.id === localStorage.getItem(LESSON_COURSE_KEY));
  if (savedCourse && (!requestedTrackId || savedCourse.track_id === requestedTrackId)) return savedCourse;
  const savedTrack = requestedTrackId || localStorage.getItem(LESSON_TRACK_KEY) || "snowpro-core";
  const coursesForTrack = state.courses.filter((course) => course.track_id === savedTrack);
  if (coursesForTrack.length) return coursesForTrack.sort((a, b) => (b.lesson_count || 0) - (a.lesson_count || 0))[0];
  return [...state.courses].sort((a, b) => (b.lesson_count || 0) - (a.lesson_count || 0))[0];
}

function currentCourse(container) {
  const id = container.querySelector("#course-select")?.value;
  return state.courses.find((course) => course.id === id);
}

function currentTrack(container) {
  const id = container.querySelector("#track-select")?.value;
  return state.tracks.find((track) => track.id === id);
}

function updateBreadcrumb(container) {
  const track = currentTrack(container);
  const course = currentCourse(container);
  const lesson = state.activeLesson;
  container.querySelector("#lesson-breadcrumb").textContent = [track?.title, course?.title, lesson?.section, lesson?.title].filter(Boolean).join(" > ") || "Select a course";
}

function updateUrl(container, lesson) {
  const trackId = container.querySelector("#track-select").value;
  const url = `#/learn?track_id=${encodeURIComponent(trackId)}&course_id=${encodeURIComponent(lesson.course_id)}&lesson_id=${encodeURIComponent(lesson.id)}`;
  history.replaceState(null, "", url);
}

function qualityBadge(chunks, notesOnly) {
  if (!chunks.length) return `<span class="content-quality-badge danger">Missing transcript</span>`;
  if (notesOnly) return `<span class="content-quality-badge warning">Generated notes</span>`;
  return `<span class="content-quality-badge success">Real transcript</span>`;
}

function wireTranscript(container) {
  const video = container.querySelector("#video");
  if (!video) return;
  container.querySelectorAll(".cue").forEach((cue) => {
    cue.addEventListener("click", () => {
      video.currentTime = Number(cue.dataset.start || 0);
      video.play();
    });
  });
}

function formatTime(value) {
  const seconds = Math.floor(value || 0);
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

function formatDuration(value) {
  const seconds = Number(value || 0);
  if (!seconds) return "Duration unavailable";
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} min`;
  return `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
}
