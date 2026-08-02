export const VIEW_ID = "curriculum";

import { escapeHtml, getLessons, getTrackCourses, getTracks } from "../api.js?v=20260731-v21-editorial-replica";
import { activeTrack, setActiveTrack } from "../ui.js?v=20260731-v21-editorial-replica";

let requestToken = 0;

export default async function mount(container, params = {}) {
  const token = ++requestToken;
  const trackId = params.track_id || activeTrack();
  setActiveTrack(trackId);
  const [trackData, courseData] = await Promise.all([getTracks(), getTrackCourses(trackId)]);
  if (token !== requestToken) return;
  const tracks = trackData.tracks || [];
  const track = tracks.find((item) => item.id === trackId) || tracks[0] || { id: trackId, title: "Certification" };
  const courses = courseData.courses || [];
  const learningCourses = courses.filter((course) => Number(course.lesson_count || 0) > 0);
  const practiceCourses = courses.filter((course) => Number(course.question_count || 0) > 0);

  container.innerHTML = `
    <div class="replica-page replica-enter">
      <section class="replica-page-heading">
        <p class="replica-kicker">Curriculum · ${escapeHtml(track.title)}</p>
        <h1>Learn the platform.<br><em>Practise until it sticks.</em></h1>
        <p>${escapeHtml(track.description || "Follow source courses, lessons, and practice material for the selected certification.")}</p>
      </section>

      <section class="replica-section" aria-labelledby="learning-title">
        <div class="replica-section-heading">
          <div><p class="replica-kicker">01 · Learn</p><h2 id="learning-title">Courses &amp; lessons</h2></div>
          <span>${learningCourses.reduce((sum, item) => sum + Number(item.lesson_count || 0), 0)} lessons</span>
        </div>
        <div class="replica-course-list">
          ${learningCourses.length ? learningCourses.map(courseRow).join("") : `<p class="replica-empty-copy">No video lessons are mapped to this certification yet.</p>`}
        </div>
      </section>

      <section class="replica-section" aria-labelledby="practice-title">
        <div class="replica-section-heading">
          <div><p class="replica-kicker">02 · Test</p><h2 id="practice-title">Practice banks</h2></div>
          <a href="#/practice?track_id=${encodeURIComponent(track.id)}">Open practice</a>
        </div>
        <div class="replica-resource-grid compact">
          ${practiceCourses.slice(0, 8).map((course) => `
            <a class="replica-resource-card" href="#/practice?track_id=${encodeURIComponent(track.id)}&course_id=${encodeURIComponent(course.id)}">
              <span>${course.practice_test_count || 0} tests · ${course.question_count || 0} questions</span>
              <strong>${escapeHtml(course.title)}</strong>
              <small>Source course</small>
            </a>`).join("")}
        </div>
      </section>
    </div>
  `;

  container.querySelectorAll("[data-course-id]").forEach((button) => {
    button.addEventListener("click", () => toggleCourse(container, button, track.id));
  });
}

function courseRow(course, index) {
  return `
    <article class="replica-course" data-course="${escapeHtml(course.id)}">
      <button class="replica-course-trigger" data-course-id="${escapeHtml(course.id)}" type="button" aria-expanded="false">
        <span class="replica-course-number">${String(index + 1).padStart(2, "0")}</span>
        <span class="replica-course-copy"><strong>${escapeHtml(course.title)}</strong><small>${course.lesson_count || 0} lessons · ${course.question_count || 0} questions</small></span>
        <span class="replica-course-toggle" aria-hidden="true">+</span>
      </button>
      <div class="replica-course-lessons" data-lessons-for="${escapeHtml(course.id)}"></div>
    </article>`;
}

async function toggleCourse(container, button, trackId) {
  const courseId = button.dataset.courseId;
  const article = button.closest(".replica-course");
  const target = article.querySelector("[data-lessons-for]");
  const open = article.classList.toggle("open");
  button.setAttribute("aria-expanded", String(open));
  article.querySelector(".replica-course-toggle").textContent = open ? "−" : "+";
  if (!open || target.dataset.loaded) return;
  target.innerHTML = `<div class="replica-inline-loading">Loading lessons...</div>`;
  try {
    const data = await getLessons({ track_id: trackId, course_id: courseId, limit: 500 });
    const lessons = data.lessons || [];
    target.innerHTML = lessons.length ? lessons.map((lesson, index) => `
      <a class="replica-lesson-row" href="#/lesson?track_id=${encodeURIComponent(trackId)}&lesson_id=${encodeURIComponent(lesson.id)}">
        <span>${String(index + 1).padStart(2, "0")}</span>
        <strong>${escapeHtml(lesson.title)}</strong>
        <small>${lesson.transcript_path ? "Transcript" : "Study notes"}</small>
      </a>`).join("") : `<p class="replica-empty-copy">No lessons found in this course.</p>`;
    target.dataset.loaded = "true";
  } catch (error) {
    target.innerHTML = `<p class="replica-empty-copy">${escapeHtml(error.message)}</p>`;
  }
}

