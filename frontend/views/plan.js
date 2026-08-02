export const VIEW_ID = "plan";
import {
  createStudyRoadmap,
  escapeHtml,
  formatNumber,
  getContentAudit,
  getStudyGoals,
  getStudyReadiness,
  getTodayPlan,
  updateStudyPlanItem,
} from "../api.js";
import { showToast } from "../components/toast.js";

export default async function mount(container) {
  container.innerHTML = `
    <section class="study-plan-page">
      <div class="learning-page-head">
        <div>
          <p class="eyebrow">Study plan</p>
          <h1>Certification roadmap</h1>
          <p>Daily work, readiness, and content quality by track.</p>
        </div>
        <div class="plan-builder">
          <input id="roadmap-date" type="date" value="${defaultTargetDate()}" />
          <label><input id="roadmap-replace" type="checkbox" /> Replace active goals</label>
          <button id="build-roadmap" type="button" class="primary-link">Build 3-cert roadmap</button>
        </div>
      </div>

      <div class="plan-layout">
        <section class="panel plan-goals-panel">
          <div class="panel-title">
            <div><p class="eyebrow">Targets</p><h2>Active goals</h2></div>
          </div>
          <div id="goal-list" class="goal-list"></div>
        </section>

        <section class="panel plan-today-panel">
          <div class="panel-title">
            <div><p class="eyebrow">Today</p><h2>Mission queue</h2></div>
            <span id="today-count" class="streak-badge">0 tasks</span>
          </div>
          <div id="today-list" class="today-list"></div>
        </section>

        <section class="panel plan-readiness-panel">
          <div class="panel-title">
            <div><p class="eyebrow">Readiness</p><h2>Certification scorecard</h2></div>
          </div>
          <div id="readiness-grid" class="readiness-grid"></div>
        </section>

        <section class="panel plan-audit-panel">
          <div class="panel-title">
            <div><p class="eyebrow">Archive audit</p><h2>What the app actually indexed</h2></div>
          </div>
          <div id="audit-summary" class="audit-summary"></div>
          <div id="audit-track-table" class="audit-track-table"></div>
        </section>
      </div>
    </section>
  `;

  container.querySelector("#build-roadmap").addEventListener("click", async () => {
    const button = container.querySelector("#build-roadmap");
    button.disabled = true;
    try {
      const targetEndDate = container.querySelector("#roadmap-date").value;
      const replaceExisting = container.querySelector("#roadmap-replace").checked;
      const response = await createStudyRoadmap({
        track_ids: ["snowpro-core", "associate-platform", "advanced-architect"],
        target_end_date: targetEndDate,
        weekly_hours: 10,
        daily_question_target: 40,
        replace_existing: replaceExisting,
      });
      const created = response.goals?.length || 0;
      const skipped = response.skipped?.length || 0;
      showToast(`Roadmap updated: ${created} goals, ${skipped} skipped`, "success");
      await renderPlan(container);
    } catch (error) {
      showToast(error.message, "error");
    } finally {
      button.disabled = false;
    }
  });

  await renderPlan(container);
}

async function renderPlan(container) {
  const [goals, today, readiness, audit] = await Promise.all([
    getStudyGoals(),
    getTodayPlan(),
    getStudyReadiness(),
    getContentAudit(),
  ]);
  renderGoals(container, goals.goals || []);
  renderToday(container, today.items || []);
  renderReadiness(container, readiness.tracks || []);
  renderAudit(container, audit);
}

function renderGoals(container, goals) {
  const target = container.querySelector("#goal-list");
  if (!goals.length) {
    target.innerHTML = `<div class="empty-state">No active certification goals yet.</div>`;
    return;
  }
  target.innerHTML = goals
    .map(
      (goal) => `
        <article class="goal-card">
          <div>
            <strong>${escapeHtml(goal.track_title)}</strong>
            <span>${formatNumber(goal.question_count)} questions • ${formatNumber(goal.lesson_count)} lessons</span>
          </div>
          <div class="goal-meta">
            <span>${escapeHtml(goal.target_exam_date || "No exam date")}</span>
            <b>${goal.days_remaining ?? "-"} days</b>
          </div>
          <div class="mini-progress"><span style="width:${Math.max(0, Math.min(100, goal.completion_pct || 0))}%"></span></div>
        </article>
      `,
    )
    .join("");
}

function renderToday(container, items) {
  container.querySelector("#today-count").textContent = `${items.length} task${items.length === 1 ? "" : "s"}`;
  const target = container.querySelector("#today-list");
  if (!items.length) {
    target.innerHTML = `<div class="empty-state">No due study tasks.</div>`;
    return;
  }
  target.innerHTML = items
    .slice(0, 12)
    .map(
      (item) => `
        <article class="today-task">
          <span>${escapeHtml(item.item_type.replaceAll("_", " "))}</span>
          <div>
            <strong>${escapeHtml(item.title)}</strong>
            <small>${escapeHtml(item.track_title)}${item.course_title ? ` • ${escapeHtml(item.course_title)}` : ""}</small>
          </div>
          <button type="button" data-complete="${item.id}">Done</button>
        </article>
      `,
    )
    .join("");
  target.querySelectorAll("[data-complete]").forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        await updateStudyPlanItem(button.dataset.complete, { completed: true });
        button.closest(".today-task")?.remove();
        showToast("Task marked complete", "success");
      } catch (error) {
        showToast(error.message, "error");
      }
    });
  });
}

function renderReadiness(container, tracks) {
  container.querySelector("#readiness-grid").innerHTML = tracks
    .map(
      (track) => `
        <article class="readiness-card">
          <div>
            <strong>${escapeHtml(track.track_title)}</strong>
            <span>${formatNumber(track.total_questions)} questions • ${formatNumber(track.full_mock_tests)} full mocks</span>
          </div>
          <b>${track.readiness_pct}%</b>
          <div class="mini-progress"><span style="width:${Math.max(0, Math.min(100, track.readiness_pct || 0))}%"></span></div>
        </article>
      `,
    )
    .join("");
}

function renderAudit(container, audit) {
  const totals = audit.totals || {};
  const quality = audit.transcript_quality || {};
  container.querySelector("#audit-summary").innerHTML = [
    ["Tracks", totals.tracks],
    ["Courses", totals.courses],
    ["Lessons", totals.lessons],
    ["Questions", totals.questions],
    ["Generated notes", quality.generated_notes],
    ["Real transcripts", quality.transcript_like_lessons],
  ]
    .map(([label, value]) => `<div><strong>${formatNumber(value)}</strong><span>${label}</span></div>`)
    .join("");

  container.querySelector("#audit-track-table").innerHTML = `
    <table>
      <thead><tr><th>Track</th><th>Courses</th><th>Lessons</th><th>Questions</th><th>Full mocks</th><th>Micro quizzes</th></tr></thead>
      <tbody>
        ${(audit.tracks || [])
          .map(
            (track) => `
              <tr>
                <td>${escapeHtml(track.track_title)}</td>
                <td>${formatNumber(track.courses)}</td>
                <td>${formatNumber(track.lessons)}</td>
                <td>${formatNumber(track.questions)}</td>
                <td>${formatNumber(track.full_mock_tests)}</td>
                <td>${formatNumber(track.micro_quizzes)}</td>
              </tr>
            `,
          )
          .join("")}
      </tbody>
    </table>
  `;
}

function defaultTargetDate() {
  const target = new Date();
  target.setDate(target.getDate() + 99);
  return target.toISOString().slice(0, 10);
}
