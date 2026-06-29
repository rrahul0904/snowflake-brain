import { getIndexStatus, getStudyGoals } from "../api.js";

export async function renderTopbar() {
  const topbar = document.querySelector("#topbar");
  topbar.innerHTML = `
    <div class="topbar-identity coach-topbar-identity">
      <strong>Snowflake Brain</strong>
      <span id="active-goal-label">Checking goal...</span>
    </div>
    <div class="topbar-status coach-topbar-status">
      <span class="local-pill">Local mode</span>
      <span id="index-status" class="muted">Index status...</span>
      <a href="#/readiness" class="system-link">Exam readiness</a>
    </div>
  `;
  await refreshTopbar();
}

export async function refreshTopbar() {
  try {
    const [status, goals] = await Promise.all([getIndexStatus(), getStudyGoals().catch(() => ({ goals: [] }))]);
    const goal = (goals.goals || [])[0];
    document.querySelector("#active-goal-label").textContent = goal
      ? `Goal: ${goal.track_title}${goal.target_exam_date ? ` · ${goal.target_exam_date}` : ""}`
      : "No exam goal set";
    document.querySelector("#index-status").textContent = status.running
      ? "Indexing content"
      : `${status.questions_indexed || 0} questions · ${status.lessons_indexed || 0} lessons`;
  } catch {
    document.querySelector("#active-goal-label").textContent = "Goal unavailable";
    document.querySelector("#index-status").textContent = "Index unavailable";
  }
}
