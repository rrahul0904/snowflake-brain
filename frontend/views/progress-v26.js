export const VIEW_ID = "v26-progress";

import {
  escapeHtml,
  getConfidenceCalibration,
  getDueToday,
  getIntelligenceReadiness,
  getMistakeNotebook,
  getMockHistory,
  getMockRemediation,
  getSkillMap,
  getSkillSummary,
  getStudyPlan,
  getTaskProgress,
  saveStudyPreferences,
  updateMistakeNotebook,
} from "../api.js";
import { activeTrack } from "../ui.js";
import { candidate, refreshCandidate } from "../auth.js";
import { DOMAIN_COLORS, studyLayout } from "../components/study-shell.js";

export default async function mount(container, params = {}) {
  const trackId = params.track_id || activeTrack();
  await refreshCandidate().catch(() => {});
  const account = candidate();
  if (!account) throw new Error("Candidate session required");

  const [map, progress, summary, history, due, mistakes, calibration, plan] = await Promise.all([
    getSkillMap(),
    getTaskProgress({ track_id: trackId }).catch(() => ({})),
    getSkillSummary({ track_id: trackId }).catch(() => ({ skills: [], domains: [] })),
    getMockHistory({ track_id: trackId }).catch(() => ({ history: [] })),
    getDueToday({ track_id: trackId, limit: 5 }).catch(() => ({ due_count: 0, questions: [] })),
    getMistakeNotebook({ track_id: trackId, status: "active", limit: 5 }).catch(() => ({ counts: {}, items: [] })),
    getConfidenceCalibration({ track_id: trackId }).catch(() => ({ sample_size: 0, status: "insufficient_data", per_level: [] })),
    getStudyPlan({ track_id: trackId }).catch(() => ({ days: [], priority_skills: [], preferences: { daily_minutes: 45, days_per_week: 6 } })),
  ]);
  const readiness = account.is_premium ? await getIntelligenceReadiness({ track_id: trackId }).catch(() => ({})) : {};
  const latestMock = (history.history || [])[0];
  const remediation = latestMock ? await getMockRemediation(latestMock.session_id).catch(() => null) : null;
  const cert = (map.certifications || []).find((item) => item.id === trackId) || (map.certifications || [])[0];
  if (!cert) throw new Error("Certification is not configured");

  const completed = new Set(progress.completed_skill_ids || []);
  const totalTasks = Number(progress.total_tasks || (cert.domains || []).reduce((sum, domain) => sum + (domain.skills || []).length, 0) || 19);
  const completedTasks = Number(progress.completed_tasks || completed.size || 0);
  const lessonsPct = Math.round(completedTasks / Math.max(1, totalTasks) * 100);
  const attemptedSkills = (summary.skills || []).filter((item) => Number(item.attempts || 0) > 0);
  const practicePct = attemptedSkills.length ? Math.round(attemptedSkills.reduce((sum, item) => sum + Number(item.accuracy_pct || 0), 0) / attemptedSkills.length) : 0;
  const mastered = attemptedSkills.filter((item) => Number(item.accuracy_pct || 0) >= 80).length;
  const drillPct = Math.round(mastered / Math.max(1, totalTasks) * 100);
  const computed = Math.round(lessonsPct * .30 + practicePct * .40 + drillPct * .30);
  const score = Number.isFinite(Number(readiness.readiness_score)) && Number(readiness.readiness_score) > 0 ? Math.round(Number(readiness.readiness_score)) : computed;
  const status = score >= 80 ? "Ready" : score >= 55 ? "Building" : "Not Ready";
  const tasks = [...(summary.skills || [])].filter((item) => Number(item.attempts || 0) > 0).sort((a, b) => Number(a.accuracy_pct || 0) - Number(b.accuracy_pct || 0)).slice(0, 5);
  const hasEvidence = completedTasks > 0 || attemptedSkills.length > 0 || (history.history || []).length > 0;

  container.innerHTML = studyLayout(cert, "progress", `<a class="v26-study-back" href="#/curriculum?track_id=${encodeURIComponent(cert.id)}" aria-label="Back">‹</a><header class="v26-recording-progress-head"><h1>Your Progress</h1><p>Track readiness, work the questions due today, and turn mistakes into the next study action.</p></header>${learningCommandCenter(trackId, due, mistakes, calibration, plan)}<section class="v26-readiness-panel"><span>Exam Readiness</span><div class="v26-readiness-score">${score}<small> / 100</small></div><div class="v26-readiness-status">${status}</div><div class="v26-readiness-components"><div><span>Lessons (30%)</span><b>${lessonsPct}%</b></div><div><span>Practice (40%)</span><b>${practicePct}%</b></div><div><span>Drill mastery (30%)</span><b>${drillPct}%</b></div></div></section>${hasEvidence ? "" : `<section class="v26-no-progress"><strong>No progress yet</strong><p>Complete lessons and answer practice questions to build your readiness score.</p></section>`}<section class="v26-recording-domain-progress"><h2>Domain Progress</h2>${domainProgress(cert, completed)}</section>${planSection(plan)}${mistakeSection(mistakes, trackId)}${calibrationSection(calibration)}${remediationSection(remediation)}${tasks.length ? `<section class="v26-progress-section"><div class="v26-section-heading"><p class="v26-kicker">Review Next</p><h2>Tasks to revisit</h2></div><div class="v26-weak-list">${tasks.map((item) => `<a href="#/skill?track_id=${encodeURIComponent(cert.id)}&skill_id=${encodeURIComponent(item.skill_id)}"><div><strong>${escapeHtml(item.skill || item.skill_id)}</strong><span>${item.attempts || 0} attempts · ${item.accuracy_pct || 0}% accuracy</span></div><em>Review →</em></a>`).join("")}</div></section>` : ""}${(history.history || []).length ? `<section class="v26-progress-section"><div class="v26-section-heading"><p class="v26-kicker">Recent Mocks</p><h2>Timed evidence</h2></div>${mockRows(history.history || [])}</section>` : ""}<p class="v26-scoring-note">Readiness is an internal study score for preparation only; it is not Snowflake's exam scoring formula.</p>`);
  bindLearningActions(container, trackId, plan);
}

function learningCommandCenter(trackId, due, mistakes, calibration, plan) {
  const openMistakes = Number(mistakes.counts?.open || 0) + Number(mistakes.counts?.reviewing || 0);
  const confidence = Number(calibration.sample_size || 0) >= 5 ? `${Math.round(Number(calibration.calibration_score || 0))}/100` : "Collecting";
  const exam = plan.preferences?.exam_date ? `${plan.days_until_exam ?? "?"} days` : "Not set";
  return `<section class="v26-learning-command"><div><span>Due Today</span><strong>${Number(due.due_count || 0)}</strong><a href="#/practice?track_id=${encodeURIComponent(trackId)}&mode=srs">Review now →</a></div><div><span>Active Mistakes</span><strong>${openMistakes}</strong><a href="#mistakes">Open notebook →</a></div><div><span>Confidence</span><strong>${confidence}</strong><small>${escapeHtml(String(calibration.status || "insufficient_data").replaceAll("_", " "))}</small></div><div><span>Exam Date</span><strong>${escapeHtml(exam)}</strong><button type="button" data-edit-plan>Set plan</button></div></section>`;
}

function planSection(plan) {
  const prefs = plan.preferences || {};
  const days = plan.days || [];
  return `<section class="v26-progress-section v26-study-plan"><div class="v26-section-heading"><p class="v26-kicker">Personalized Study Plan</p><h2>Your next seven days</h2><p>${Number(prefs.daily_minutes || 45)} min/day · ${Number(prefs.days_per_week || 6)} study days/week${prefs.exam_date ? ` · exam ${escapeHtml(prefs.exam_date)}` : ""}</p></div>${days.length ? `<div class="v26-plan-grid">${days.map((day, index) => `<article class="${day.active ? "" : "rest"}"><span>${index === 0 ? "Today" : escapeHtml(day.date)}</span><strong>${day.total_minutes || 0} min</strong>${(day.sessions || []).map((session) => `<a href="${escapeHtml(session.href || "#/progress")}"><b>${escapeHtml(session.title || session.type)}</b><em>${session.minutes || 0} min</em></a>`).join("")}</article>`).join("")}</div>` : `<p>No plan evidence yet. Complete a drill to generate priorities.</p>`}<form class="v26-plan-form" data-plan-form hidden><label>Exam date<input type="date" name="exam_date" value="${escapeHtml(prefs.exam_date || "")}"></label><label>Minutes/day<input type="number" min="15" max="240" name="daily_minutes" value="${Number(prefs.daily_minutes || 45)}"></label><label>Days/week<input type="number" min="1" max="7" name="days_per_week" value="${Number(prefs.days_per_week || 6)}"></label><button class="v26-btn primary" type="submit">Save plan</button></form></section>`;
}

function mistakeSection(mistakes, trackId) {
  const items = mistakes.items || [];
  return `<section class="v26-progress-section v26-mistake-notebook" id="mistakes"><div class="v26-section-heading"><p class="v26-kicker">Mistake Notebook</p><h2>Rules worth remembering</h2><p>Missed questions stay active until repeated correct reviews move them toward mastery.</p></div>${items.length ? `<div class="v26-mistake-list">${items.map((item) => `<article><div><span>${escapeHtml(item.status || "open")}</span><b>${item.miss_count || 1} miss${Number(item.miss_count || 1) === 1 ? "" : "es"}</b></div><strong>${escapeHtml(item.question || "")}</strong><p>${item.note ? escapeHtml(item.note) : "No note yet — write the rule or trap you want to remember."}</p><footer><a href="#/practice?track_id=${encodeURIComponent(trackId)}&mode=srs">Review due</a><button type="button" data-mistake-note="${escapeHtml(item.question_id)}" data-current-note="${escapeHtml(item.note || "")}">Add note</button><button type="button" data-mistake-mastered="${escapeHtml(item.question_id)}">Mark mastered</button></footer></article>`).join("")}</div>` : `<p class="v26-empty-copy">No active mistakes. Incorrect answers from drills and mocks will appear here automatically.</p>`}</section>`;
}

function calibrationSection(calibration) {
  const sample = Number(calibration.sample_size || 0);
  const status = String(calibration.status || "insufficient_data").replaceAll("_", " ");
  return `<section class="v26-progress-section v26-calibration"><div class="v26-section-heading"><p class="v26-kicker">Confidence Calibration</p><h2>Do you know when you know?</h2><p>${sample} confidence-rated answers · ${escapeHtml(status)}</p></div>${sample ? `<div class="v26-calibration-grid">${(calibration.per_level || []).map((item) => `<div><span>Confidence ${item.confidence}</span><strong>${item.attempts ? `${item.accuracy_pct}%` : "—"}</strong><small>${item.attempts || 0} answers · expected ${item.expected_pct}%</small></div>`).join("")}</div><p>${Number(calibration.overconfident_misses || 0)} high-confidence misses · ${Number(calibration.underconfident_correct || 0)} low-confidence correct answers.</p>` : `<p class="v26-empty-copy">Rate confidence during practice to build this signal. Five rated answers unlock the first calibration read.</p>`}</section>`;
}

function remediationSection(remediation) {
  if (!remediation || !Number(remediation.mistake_count || 0)) return "";
  return `<section class="v26-progress-section v26-remediation"><div class="v26-section-heading"><p class="v26-kicker">Latest Mock Remediation</p><h2>Repair the misses from score ${Number(remediation.scaled_score || 0)}</h2><p>${Number(remediation.mistake_count || 0)} questions need another pass.</p></div><div class="v26-remediation-actions">${(remediation.actions || []).map((action) => `<a href="${escapeHtml(action.href || "#/progress")}"><strong>${escapeHtml(action.title || "Review")}</strong><em>Start →</em></a>`).join("")}</div></section>`;
}

function bindLearningActions(container, trackId, plan) {
  const form = container.querySelector("[data-plan-form]");
  container.querySelector("[data-edit-plan]")?.addEventListener("click", () => { if (form) form.hidden = !form.hidden; });
  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = new FormData(form);
    const button = form.querySelector("button[type='submit']");
    if (button) button.disabled = true;
    try {
      await saveStudyPreferences({
        track_id: trackId,
        exam_date: data.get("exam_date") || null,
        daily_minutes: Number(data.get("daily_minutes") || plan.preferences?.daily_minutes || 45),
        days_per_week: Number(data.get("days_per_week") || plan.preferences?.days_per_week || 6),
      });
      window.location.reload();
    } catch (error) {
      if (button) { button.disabled = false; button.textContent = error.message || "Unable to save"; }
    }
  });
  container.querySelectorAll("[data-mistake-note]").forEach((button) => button.addEventListener("click", async () => {
    const note = window.prompt("What rule, trap, or correction do you want to remember?", button.dataset.currentNote || "");
    if (note === null) return;
    await updateMistakeNotebook(button.dataset.mistakeNote, { note }).catch(() => null);
    window.location.reload();
  }));
  container.querySelectorAll("[data-mistake-mastered]").forEach((button) => button.addEventListener("click", async () => {
    await updateMistakeNotebook(button.dataset.mistakeMastered, { status: "mastered" }).catch(() => null);
    window.location.reload();
  }));
}

function domainProgress(cert, completed) {
  return (cert.domains || []).map((domain, index) => {
    const skills = domain.skills || [];
    const done = skills.filter((skill) => completed.has(skill.id)).length;
    return `<div><i style="--domain:${DOMAIN_COLORS[index % DOMAIN_COLORS.length]}"></i><span>D${index + 1}: ${escapeHtml(domain.title)}</span><em>${done}/${skills.length} tasks</em></div>`;
  }).join("");
}

function mockRows(rows) {
  return `<div class="v26-history-table">${rows.slice(0, 5).map((row) => `<a href="#/mock/result?session_id=${row.session_id}"><span>${row.finished_at || ""}</span><strong>${String(row.mode || "Mock").replaceAll("_", " ")}</strong><b>${row.scaled_score}</b><em>${row.ready ? "Ready" : "Review"}</em></a>`).join("")}</div>`;
}
