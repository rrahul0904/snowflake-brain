export const VIEW_ID = "v26-due-today";

import { escapeHtml, getDueToday, getSkillMap } from "../api.js";
import { activeTrack } from "../ui.js";
import { studyLayout } from "../components/study-shell.js";
import { emptyState, evidenceNotice } from "../components/learning-widgets.js";

export default async function mount(container, params = {}) {
  const trackId = params.track_id || activeTrack();
  const [map, due] = await Promise.all([
    getSkillMap(),
    getDueToday({ track_id: trackId, limit: 100 }).catch(() => ({ due_count: 0, questions: [] })),
  ]);
  const cert = (map.certifications || []).find((item) => item.id === trackId) || (map.certifications || [])[0];
  if (!cert) throw new Error("Certification is not configured");
  const skills = new Map((cert.domains || []).flatMap((domain) => (domain.skills || []).map((skill) => [skill.id, { ...skill, domain }] )));
  const rows = due.questions || [];
  const highRisk = rows.filter((row) => Number(row.lapses || 0) >= 2 || Number(row.last_confidence || 0) >= 4).length;
  const overdue = rows.filter((row) => dueState(row.due_at) === "overdue").length;

  container.innerHTML = studyLayout(cert, "due", `<a class="v26-study-back" href="#/progress?track_id=${encodeURIComponent(trackId)}" aria-label="Back">‹</a><header class="v26-recording-progress-head"><p class="v26-kicker">Spaced review</p><h1>Due Today</h1><p>Review the concepts whose retrieval interval has matured. This queue is generated from your own attempts; it is not a generic daily question list.</p>${evidenceNotice("Due dates come from Snowflake Brain spaced-review state. Correct reviews extend intervals; misses and low-confidence correct answers return sooner.")}</header><section class="v26-learning-command"><div><span>Due now</span><strong>${Number(due.due_count || 0)}</strong><small>Review items</small></div><div><span>Overdue</span><strong>${overdue}</strong><small>Past scheduled review</small></div><div><span>High risk</span><strong>${highRisk}</strong><small>Repeated lapses / confidence risk</small></div><div><span>Queue</span><strong>${rows.length}</strong><small>Loaded now</small></div></section>${rows.length ? `<section class="v26-progress-section"><div class="v26-section-heading"><p class="v26-kicker">Review queue</p><h2>Retrieve first, then restudy if needed.</h2></div><div class="v26-due-queue">${rows.map((row) => dueCard(row, skills.get(row.skill_id), trackId)).join("")}</div></section><section class="v26-result-actions"><a class="v26-btn primary" href="#/practice?track_id=${encodeURIComponent(trackId)}&mode=srs">Start today’s review</a><a class="v26-btn secondary" href="#/mistakes?track_id=${encodeURIComponent(trackId)}">Open mistake notebook</a></section>` : emptyState("Your review queue is clear", "Nothing is scheduled for retrieval right now. Keep studying and practising; new misses and low-confidence answers will create future review work.", `#/practice?track_id=${encodeURIComponent(trackId)}&mode=drill`, "Start targeted drill")}`, "", []);
}

function dueCard(row, skill, trackId) {
  const state = dueState(row.due_at);
  const lesson = row.skill_id ? `#/skill?track_id=${encodeURIComponent(trackId)}&skill_id=${encodeURIComponent(row.skill_id)}` : `#/curriculum?track_id=${encodeURIComponent(trackId)}`;
  const drill = row.skill_id ? `#/practice?track_id=${encodeURIComponent(trackId)}&mode=drill&skill_id=${encodeURIComponent(row.skill_id)}` : `#/practice?track_id=${encodeURIComponent(trackId)}&mode=drill`;
  return `<article class="v26-due-card ${state}"><header><span>${state === "overdue" ? "Overdue" : "Due now"}</span><b>${escapeHtml(skill?.task_code ? `Task ${skill.task_code}` : row.domain_id || "Review")}</b><em>${Number(row.lapses || 0)} lapse${Number(row.lapses || 0) === 1 ? "" : "s"}</em></header><h3>${escapeHtml(row.question || "Review item")}</h3><p>${escapeHtml(skill?.title || "Mapped certification concept")}</p><dl><dt>Last confidence</dt><dd>${confidenceLabel(row.last_confidence)}</dd><dt>Previous interval</dt><dd>${Number(row.interval_days || 0)} day${Number(row.interval_days || 0) === 1 ? "" : "s"}</dd><dt>Correct repetitions</dt><dd>${Number(row.repetitions || 0)}</dd></dl><footer><a href="${lesson}">Lesson</a><a href="${drill}">Drill</a><a href="#/mistakes?track_id=${encodeURIComponent(trackId)}">Mistakes</a><a href="#/glossary?track_id=${encodeURIComponent(trackId)}">Glossary</a><a href="#/exercises?track_id=${encodeURIComponent(trackId)}">Build exercise</a></footer></article>`;
}

function confidenceLabel(value) { const n = Number(value || 0); if (!n) return "Not rated"; if (n <= 2) return "Low"; if (n === 3) return "Medium"; return "High"; }
function dueState(value) { if (!value) return "due"; const date = new Date(String(value).replace(" ", "T") + (String(value).includes("Z") ? "" : "Z")); if (Number.isNaN(date.getTime())) return "due"; return Date.now() - date.getTime() > 86400000 ? "overdue" : "due"; }
