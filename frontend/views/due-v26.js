export const VIEW_ID = "v26-due-today";

import { escapeHtml, getDueToday, getSkillMap, markTaskReviewed } from "../api.js";
import { activeTrack } from "../ui.js";
import { studyLayout } from "../components/study-shell.js";
import { emptyState, evidenceNotice } from "../components/learning-widgets.js";

export default async function mount(container, params = {}) {
  const trackId = params.track_id || activeTrack();
  const [map, due] = await Promise.all([
    getSkillMap(),
    getDueToday({ track_id: trackId, limit: 100 }).catch(() => ({ due_count: 0, questions: [], task_reviews: [] })),
  ]);
  const cert = (map.certifications || []).find((item) => item.id === trackId) || (map.certifications || [])[0];
  if (!cert) throw new Error("Certification is not configured");
  const skills = new Map((cert.domains || []).flatMap((domain) => (domain.skills || []).map((skill) => [skill.id, { ...skill, domain }] )));
  const rows = due.questions || [];
  const taskRows = due.task_reviews || [];
  const highRisk = rows.filter((row) => Number(row.lapses || 0) >= 2 || Number(row.last_confidence || 0) >= 4).length;
  const overdue = rows.filter((row) => dueState(row.due_at) === "overdue").length + taskRows.filter((row) => dueState(row.next_review_at) === "overdue").length;
  const total = Number(due.due_count || rows.length + taskRows.length);

  container.innerHTML = studyLayout(cert, "due", `<a class="v26-study-back" href="#/progress?track_id=${encodeURIComponent(trackId)}" aria-label="Back">‹</a><header class="v26-recording-progress-head"><p class="v26-kicker">Spaced review</p><h1>Due Today</h1><p>Review questions whose retrieval interval matured and concepts you explicitly scheduled from lessons. The two evidence types stay visually distinct.</p>${evidenceNotice("Question due dates come from attempt evidence. Task reviews are manual concept reminders with deterministic intervals; neither is a generic daily question list.")}</header><section class="v26-learning-command"><div><span>Due now</span><strong>${total}</strong><small>Question + concept reviews</small></div><div><span>Question reviews</span><strong>${Number(due.question_due_count ?? rows.length)}</strong><small>Attempt-driven SRS</small></div><div><span>Concept reviews</span><strong>${Number(due.task_due_count ?? taskRows.length)}</strong><small>Lesson tasks you scheduled</small></div><div><span>Overdue</span><strong>${overdue}</strong><small>Past scheduled review</small></div></section>${taskRows.length ? `<section class="v26-progress-section"><div class="v26-section-heading"><p class="v26-kicker">Concept review</p><h2>Tasks you asked Snowflake Brain to bring back.</h2></div><div class="v26-task-review-queue">${taskRows.map((row) => taskCard(row, skills.get(row.skill_id), trackId)).join("")}</div></section>` : ""}${rows.length ? `<section class="v26-progress-section"><div class="v26-section-heading"><p class="v26-kicker">Question review</p><h2>Retrieve first, then restudy if needed.</h2></div><div class="v26-due-queue">${rows.map((row) => dueCard(row, skills.get(row.skill_id), trackId)).join("")}</div></section><section class="v26-result-actions"><a class="v26-btn primary" href="#/practice?track_id=${encodeURIComponent(trackId)}&mode=srs">Start question reviews</a><a class="v26-btn secondary" href="#/mistakes?track_id=${encodeURIComponent(trackId)}">Open mistake notebook</a></section>` : ""}${!rows.length && !taskRows.length ? emptyState("Your review queue is clear", "Nothing is scheduled for retrieval right now. Keep studying and practising; new misses and manually scheduled lesson tasks will create future review work.", `#/practice?track_id=${encodeURIComponent(trackId)}&mode=drill`, "Start targeted drill") : ""}`, "", []);

  container.querySelectorAll("[data-task-reviewed]").forEach((button) => button.addEventListener("click", async () => {
    button.disabled = true;
    button.textContent = "Scheduling next review…";
    try {
      const payload = await markTaskReviewed({ track_id: trackId, skill_id: button.dataset.taskReviewed });
      const card = button.closest("[data-task-review-card]");
      card?.classList.add("reviewed");
      button.textContent = `Reviewed · next ${formatDue(payload.review?.next_review_at)}`;
    } catch (error) {
      button.disabled = false;
      button.textContent = error.message || "Reviewed";
    }
  }));
}

function taskCard(row, skill, trackId) {
  const state = dueState(row.next_review_at);
  const lesson = `#/skill?track_id=${encodeURIComponent(trackId)}&skill_id=${encodeURIComponent(row.skill_id)}`;
  const drill = `#/practice?track_id=${encodeURIComponent(trackId)}&mode=drill&skill_id=${encodeURIComponent(row.skill_id)}`;
  return `<article class="v26-task-review-card ${state}" data-task-review-card><header><span>Concept review · ${state === "overdue" ? "Overdue" : "Due now"}</span><b>${escapeHtml(skill?.task_code ? `Task ${skill.task_code}` : row.skill_id)}</b></header><h3>${escapeHtml(skill?.title || "Scheduled certification task")}</h3><p>${escapeHtml(skill?.objective || "Re-open the lesson, retrieve the key decision rule, then validate it with focused practice.")}</p><dl><dt>Previous interval</dt><dd>${Number(row.interval_days || 0)} day${Number(row.interval_days || 0) === 1 ? "" : "s"}</dd><dt>Completed reviews</dt><dd>${Number(row.review_count || 0)}</dd><dt>Scheduled</dt><dd>${formatDue(row.next_review_at)}</dd></dl><footer><a href="${lesson}">Open Lesson</a><a href="${drill}">Practice This Task</a><button type="button" data-task-reviewed="${escapeHtml(row.skill_id)}">Reviewed</button></footer></article>`;
}

function dueCard(row, skill, trackId) {
  const state = dueState(row.due_at);
  const lesson = row.skill_id ? `#/skill?track_id=${encodeURIComponent(trackId)}&skill_id=${encodeURIComponent(row.skill_id)}` : `#/curriculum?track_id=${encodeURIComponent(trackId)}`;
  const drill = row.skill_id ? `#/practice?track_id=${encodeURIComponent(trackId)}&mode=drill&skill_id=${encodeURIComponent(row.skill_id)}` : `#/practice?track_id=${encodeURIComponent(trackId)}&mode=drill`;
  return `<article class="v26-due-card ${state}"><header><span>Question review · ${state === "overdue" ? "Overdue" : "Due now"}</span><b>${escapeHtml(skill?.task_code ? `Task ${skill.task_code}` : row.domain_id || "Review")}</b><em>${Number(row.lapses || 0)} lapse${Number(row.lapses || 0) === 1 ? "" : "s"}</em></header><h3>${escapeHtml(row.question || "Review item")}</h3><p>${escapeHtml(skill?.title || "Mapped certification concept")}</p><dl><dt>Last confidence</dt><dd>${confidenceLabel(row.last_confidence)}</dd><dt>Previous interval</dt><dd>${Number(row.interval_days || 0)} day${Number(row.interval_days || 0) === 1 ? "" : "s"}</dd><dt>Correct repetitions</dt><dd>${Number(row.repetitions || 0)}</dd></dl><footer><a href="${lesson}">Lesson</a><a href="${drill}">Drill</a><a href="#/mistakes?track_id=${encodeURIComponent(trackId)}">Mistakes</a><a href="#/glossary?track_id=${encodeURIComponent(trackId)}">Glossary</a><a href="#/exercises?track_id=${encodeURIComponent(trackId)}">Build exercise</a></footer></article>`;
}

function confidenceLabel(value) { const n = Number(value || 0); if (!n) return "Not rated"; if (n <= 2) return "Low"; if (n === 3) return "Medium"; return "High"; }
function dueState(value) { if (!value) return "due"; const date = new Date(String(value).replace(" ", "T") + (String(value).includes("Z") ? "" : "Z")); if (Number.isNaN(date.getTime())) return "due"; return Date.now() - date.getTime() > 86400000 ? "overdue" : "due"; }
function formatDue(value) { if (!value) return "now"; const date = new Date(String(value).replace(" ", "T") + (String(value).includes("Z") ? "" : "Z")); return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }); }
