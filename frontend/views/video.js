export const VIEW_ID = "learn";
import { escapeHtml, formatNumber, getCourses, getLesson, getLessons, getTracks, getTranscript, recordLessonProgress } from "../api.js?v=20260714-v20-ai-academy";
import { activeTrack, emptyState, navigateWithTrack, setActiveTrack, skeleton, trackOptions } from "../ui.js?v=20260714-v20-ai-academy";
import { showToast } from "../components/toast.js?v=20260714-v20-ai-academy";

const state = {
  tracks: [],
  courses: [],
  lessons: [],
  activeLessonId: null,
  activeTab: "overview",
};

const COURSE_KEY = "snowflake-brain.selected-course.v10";
const courseKey = (trackId) => `${COURSE_KEY}.${trackId || "all"}`;

export default async function mount(container, params = {}) {
  const trackId = params.track_id || activeTrack();
  setActiveTrack(trackId);
  container.innerHTML = skeleton("Loading course library and video player...");
  try {
    const [tracks, courses] = await Promise.all([getTracks(), getCourses()]);
    state.tracks = tracks.tracks || [];
    state.courses = (courses.courses || []).filter((course) => Number(course.lesson_count || 0) > 0);
    let requestedCourseId = params.course_id || localStorage.getItem(courseKey(trackId));
    if (params.lesson_id && !requestedCourseId) {
      const lesson = await getLesson(params.lesson_id);
      requestedCourseId = lesson.course_id;
    }
    renderShell(container, trackId, requestedCourseId, params.lesson_id);
    await loadLessons(container, params.lesson_id);
  } catch (error) {
    container.innerHTML = emptyState("Course library unavailable", error.message, `<button onclick="location.reload()">Retry</button>`);
  }
}

function renderShell(container, trackId, requestedCourseId, openLessonId) {
  const tracksWithLessons = new Set(state.courses.map((course) => course.track_id).filter(Boolean));
  const usableTracks = state.tracks.filter((track) => tracksWithLessons.has(track.id));
  const selectedTrack = usableTracks.some((track) => track.id === trackId) ? trackId : usableTracks[0]?.id || trackId;
  const courses = coursesForTrack(selectedTrack);
  const selectedCourse = courses.find((course) => course.id === requestedCourseId) || courses[0];
  if (selectedCourse?.id) localStorage.setItem(courseKey(selectedTrack), selectedCourse.id);

  container.innerHTML = `
    <section class="page-shell academy-page real-course-library">
      <header class="course-command-header">
        <div>
          <p class="eyebrow">Course Library</p>
          <h1>Watch the actual lessons. Practice from the same source.</h1>
          <p>This view is grounded in your local Udemy/Snowflake archive: video player, transcript cues, course outline, and related practice in one workspace.</p>
        </div>
        <div class="course-command-controls">
          <label>Certification<select id="track-select">${trackOptions(usableTracks, selectedTrack)}</select></label>
          <label>Course<select id="course-select">${courseOptions(courses, selectedCourse?.id)}</select></label>
        </div>
      </header>

      <section class="course-workbench">
        <main class="course-main-panel panel">
          <div id="video-stage" class="video-stage">
            ${emptyState("Select a lesson", "Choose a lesson from the course outline to load the video, transcript, and practice links.")}
          </div>
          <div id="lesson-tabs" class="lesson-tabs-v9"></div>
          <section id="lesson-detail" class="lesson-detail-v9"></section>
        </main>

        <aside class="course-outline-panel panel">
          <div class="outline-toolbar">
            <div>
              <p class="eyebrow">Course outline</p>
              <h2 id="course-title">${escapeHtml(selectedCourse?.title || "Course")}</h2>
            </div>
            <input id="lesson-search" placeholder="Search videos: RBAC, Snowpipe, COPY..." />
          </div>
          <div id="course-stats" class="course-stat-row"></div>
          <div id="lesson-list" class="outline-list-v9"></div>
        </aside>
      </section>
    </section>
  `;

  container.querySelector("#track-select")?.addEventListener("change", (event) => {
    state.activeLessonId = null;
    navigateWithTrack(event.target.value, "#/learn");
  });

  container.querySelector("#course-select")?.addEventListener("change", async (event) => {
    localStorage.setItem(courseKey(container.querySelector("#track-select")?.value || activeTrack()), event.target.value);
    state.activeLessonId = null;
    await loadLessons(container);
  });

  container.querySelector("#lesson-search")?.addEventListener("input", () => renderLessonList(container));
}

function coursesForTrack(trackId) {
  return state.courses
    .filter((course) => !trackId || course.track_id === trackId)
    .sort((a, b) => Number(b.lesson_count || 0) - Number(a.lesson_count || 0));
}

function courseOptions(courses, selectedId = "") {
  return courses
    .map((course) => `<option value="${escapeHtml(course.id)}" ${course.id === selectedId ? "selected" : ""}>${escapeHtml(course.title)} (${formatNumber(course.lesson_count || 0)})</option>`)
    .join("");
}

async function loadLessons(container, openLessonId = null) {
  const courseId = container.querySelector("#course-select")?.value || "";
  const trackId = container.querySelector("#track-select")?.value || activeTrack();
  const title = state.courses.find((course) => course.id === courseId)?.title || "Course";
  const titleNode = container.querySelector("#course-title");
  if (titleNode) titleNode.textContent = title;
  if (!courseId) {
    const host = container.querySelector("#lesson-list");
    if (host) host.innerHTML = emptyState("No video course found", "This certification does not currently have indexed video lessons.");
    return;
  }
  try {
    const data = await getLessons({ course_id: courseId, track_id: trackId, limit: 3000 });
    state.lessons = data.lessons || [];
    renderStats(container);
    renderLessonList(container);
    const target = openLessonId || (state.lessons.some((lesson) => lesson.id === state.activeLessonId) ? state.activeLessonId : state.lessons[0]?.id);
    if (target) await openLesson(container, target);
  } catch (error) {
    showToast(error.message, "error");
    const host = container.querySelector("#lesson-list");
    if (host) host.innerHTML = emptyState("Could not load lessons", error.message);
  }
}

function renderStats(container) {
  const totalDuration = state.lessons.reduce((sum, lesson) => sum + Number(lesson.duration_s || lesson.duration || 0), 0);
  const sections = new Set(state.lessons.map((lesson) => lesson.section || "Course")).size;
  const host = container.querySelector("#course-stats");
  if (!host) return;
  host.innerHTML = `
    <span><strong>${formatNumber(state.lessons.length)}</strong> videos</span>
    <span><strong>${formatNumber(sections)}</strong> sections</span>
    <span><strong>${formatDuration(totalDuration)}</strong></span>
  `;
}

function renderLessonList(container, options = {}) {
  const host = container.querySelector("#lesson-list");
  if (!host) return;
  const previousScroll = host.scrollTop;
  const q = (container.querySelector("#lesson-search")?.value || "").trim().toLowerCase();
  const lessons = state.lessons.filter((lesson) => !q || `${lesson.title} ${lesson.section} ${lesson.course_title}`.toLowerCase().includes(q));
  if (!lessons.length) {
    host.innerHTML = emptyState("No matching videos", "Try another Snowflake term.");
    return;
  }
  const groups = groupLessons(lessons);
  host.innerHTML = groups.map((group, index) => {
    const open = index === 0 || group.lessons.some((lesson) => lesson.id === state.activeLessonId);
    const duration = group.lessons.reduce((sum, lesson) => sum + Number(lesson.duration_s || lesson.duration || 0), 0);
    return `
      <details class="outline-section-v9" ${open ? "open" : ""}>
        <summary><span><strong>${escapeHtml(group.title)}</strong><small>${group.lessons.length} videos · ${formatDuration(duration)}</small></span><b>⌄</b></summary>
        <div class="outline-lessons-v9">
          ${group.lessons.map((lesson) => lessonButton(lesson)).join("")}
        </div>
      </details>
    `;
  }).join("");
  host.scrollTop = previousScroll;
  bindOutlineScroll(host);
  host.querySelectorAll("[data-lesson-id]").forEach((button) => button.addEventListener("click", () => openLesson(container, button.dataset.lessonId)));
  requestAnimationFrame(() => {
    if (options.revealActive) scrollActiveLessonIntoView(host);
  });
}

function bindOutlineScroll(host) {
  if (host.dataset.scrollMarkerBound) return;
  host.dataset.scrollMarkerBound = "1";
}

function scrollActiveLessonIntoView(host) {
  const active = host.querySelector(".video-lesson-row.active");
  if (!active) return;
  const hostRect = host.getBoundingClientRect();
  const rowRect = active.getBoundingClientRect();
  const pad = 24;
  if (rowRect.top < hostRect.top + pad || rowRect.bottom > hostRect.bottom - pad) {
    active.scrollIntoView({ block: "center", behavior: "smooth" });
  }
}

function groupLessons(lessons) {
  const groups = [];
  const byKey = new Map();
  for (const lesson of lessons) {
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

function lessonButton(lesson) {
  const index = state.lessons.findIndex((item) => item.id === lesson.id) + 1;
  return `
    <button class="video-lesson-row ${lesson.id === state.activeLessonId ? "active" : ""}" data-lesson-id="${escapeHtml(lesson.id)}" type="button">
      <span class="play-dot">▶</span>
      <span><strong>${index}. ${escapeHtml(lesson.title)}</strong><small>${formatDuration(lesson.duration_s || lesson.duration)} · ${escapeHtml(lesson.course_title || "")}</small></span>
    </button>
  `;
}

async function openLesson(container, lessonId) {
  state.activeLessonId = lessonId;
  renderLessonList(container, { revealActive: true });
  try {
    const [lesson, transcript] = await Promise.all([getLesson(lessonId), getTranscript(lessonId).catch(() => ({ chunks: [] }))]);
    const chunks = transcript.chunks || [];
    const transcriptText = chunks.map((chunk) => chunk.text).join("\n\n");
    const notesOnly = /English study notes/i.test(transcriptText);
    renderVideoStage(container, lesson);
    renderLessonTabs(container, lesson, chunks, notesOnly);
    renderTab(container, lesson, chunks, notesOnly);
  } catch (error) {
    showToast(error.message, "error");
  }
}

function renderVideoStage(container, lesson) {
  const media = lesson.video_path ? `/api/media?path=${encodeURIComponent(lesson.video_path)}` : "";
  const host = container.querySelector("#video-stage");
  if (!host) return;
  host.innerHTML = `
    <div class="actual-video-card">
      ${media ? `<video id="lesson-video" controls preload="metadata" playsinline src="${media}"></video>` : `<div class="video-missing"><strong>No video file indexed for this lesson.</strong><span>The lesson still has transcript/study material if available.</span></div>`}
    </div>
    <div class="now-playing-card">
      <p class="eyebrow">Now playing</p>
      <h2>${escapeHtml(lesson.title)}</h2>
      <p>${escapeHtml(lesson.course_title || "Snowflake course")} · ${escapeHtml(lesson.section || "Course")}</p>
    </div>
  `;
}

function renderLessonTabs(container, lesson, chunks, notesOnly) {
  const host = container.querySelector("#lesson-tabs");
  if (!host) return;
  const tabs = [
    ["overview", "Overview"],
    ["transcript", notesOnly ? "Study notes" : `Transcript (${formatNumber(chunks.length)})`],
    ["questions", "Practice"],
    ["actions", "Next actions"],
  ];
  host.innerHTML = tabs.map(([key, label]) => `<button class="${state.activeTab === key ? "active" : ""}" data-tab="${key}" type="button">${escapeHtml(label)}</button>`).join("");
  host.querySelectorAll("[data-tab]").forEach((button) => button.addEventListener("click", () => {
    state.activeTab = button.dataset.tab;
    renderLessonTabs(container, lesson, chunks, notesOnly);
    renderTab(container, lesson, chunks, notesOnly);
  }));
}

function renderTab(container, lesson, chunks, notesOnly) {
  const host = container.querySelector("#lesson-detail");
  if (!host) return;
  if (state.activeTab === "transcript") {
    host.innerHTML = `
      <div class="lesson-panel-head"><div><p class="eyebrow">${notesOnly ? "Generated notes" : "Transcript cues"}</p><h2>${notesOnly ? "Study context" : "Click a cue to seek the video"}</h2></div></div>
      <div id="transcript-list" class="${notesOnly ? "study-note-panel-v9" : "transcript-list-v9"}">${renderTranscript(chunks, notesOnly)}</div>
    `;
    wireTranscript(container);
    return;
  }
  if (state.activeTab === "questions") {
    const related = lesson.related_questions || [];
    host.innerHTML = `
      <div class="lesson-panel-head"><div><p class="eyebrow">Practice from this source</p><h2>Turn the video into exam evidence</h2></div><a class="primary-btn" href="#/practice?course_id=${encodeURIComponent(lesson.course_id || "")}">Open course questions</a></div>
      <div class="related-question-list-v9">
        ${related.length ? related.slice(0, 8).map((question) => `<a href="#/practice?course_id=${encodeURIComponent(lesson.course_id || "")}"><span>${escapeHtml(question.difficulty || "practice")}</span><strong>${escapeHtml(question.question || "Question")}</strong></a>`).join("") : emptyState("No direct question links yet", "Use the course question pool or search by concept.")}
      </div>
    `;
    return;
  }
  if (state.activeTab === "actions") {
    host.innerHTML = `
      <div class="lesson-panel-head"><div><p class="eyebrow">Next best actions</p><h2>Do not just watch. Prove it.</h2></div><button id="mark-complete" class="secondary-btn">Mark lesson complete</button></div>
      <div class="evidence-actions-grid">
        <a href="#/practice?course_id=${encodeURIComponent(lesson.course_id || "")}"><strong>Practice related questions</strong><span>Use the same course source for retention testing.</span></a>
        <a href="#/labs"><strong>Open lab runner</strong><span>Prove the concept with Snowflake SQL challenge validation.</span></a>
        <a href="#/search?q=${encodeURIComponent(lesson.title || "")}"><strong>Search the brain</strong><span>Find matching lessons, questions, and notes.</span></a>
      </div>
    `;
    container.querySelector("#mark-complete")?.addEventListener("click", async () => {
      try {
        await recordLessonProgress({ lesson_id: lesson.id, completed: true, progress_pct: 100 });
        showToast("Lesson marked complete", "success");
      } catch (error) {
        showToast(error.message, "error");
      }
    });
    return;
  }
  host.innerHTML = `
    <div class="lesson-panel-head"><div><p class="eyebrow">Lesson overview</p><h2>${escapeHtml(lesson.title)}</h2></div><span class="trust-pill ${notesOnly ? "warn" : "ok"}">${notesOnly ? "generated notes" : "transcript available"}</span></div>
    <div class="lesson-overview-v9">
      <p>${escapeHtml(lesson.excerpt || "This lesson is available from your local Snowflake course archive.")}</p>
      <dl>
        <div><dt>Course</dt><dd>${escapeHtml(lesson.course_title || "")}</dd></div>
        <div><dt>Section</dt><dd>${escapeHtml(lesson.section || "Course")}</dd></div>
        <div><dt>Duration</dt><dd>${formatDuration(lesson.duration_s || lesson.duration)}</dd></div>
        <div><dt>Transcript</dt><dd>${notesOnly ? "Generated study notes" : `${formatNumber(chunks.length)} cues`}</dd></div>
      </dl>
    </div>
  `;
}

function renderTranscript(chunks, notesOnly) {
  if (!chunks.length) return emptyState("No transcript indexed", "The video can still be watched from the local media file.");
  if (notesOnly) return `<pre>${escapeHtml(chunks.map((chunk) => chunk.text).join("\n\n"))}</pre>`;
  return chunks.map((cue) => `<button class="cue-v9" data-start="${Number(cue.start_s || 0)}" type="button"><span>${formatTime(cue.start_s)}</span><strong>${escapeHtml(cue.text || "")}</strong></button>`).join("");
}

function wireTranscript(container) {
  const video = container.querySelector("#lesson-video");
  if (!video) return;
  container.querySelectorAll(".cue-v9").forEach((cue) => {
    cue.addEventListener("click", () => {
      video.currentTime = Number(cue.dataset.start || 0);
      video.play().catch(() => {});
    });
  });
}

function formatTime(value) {
  const seconds = Math.floor(Number(value || 0));
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

function formatDuration(value) {
  const seconds = Number(value || 0);
  if (!seconds) return "duration unknown";
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} min`;
  return `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
}
