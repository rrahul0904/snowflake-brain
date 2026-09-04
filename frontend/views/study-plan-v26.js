export const VIEW_ID = "v26-study-plan";

import { escapeHtml, getSkillMap, getStudyPlan, saveStudyPreferences } from "../api.js";
import { activeTrack } from "../ui.js";
import { studyLayout } from "../components/study-shell.js";
import { evidenceNotice } from "../components/learning-widgets.js";

export default async function mount(container, params = {}) {
  const trackId = params.track_id || activeTrack();
  const [map, plan] = await Promise.all([
    getSkillMap(),
    getStudyPlan({ track_id: trackId }).catch(() => ({ preferences: { daily_minutes: 45, days_per_week: 6 }, days: [], priority_skills: [] })),
  ]);
  const cert = (map.certifications || []).find((item) => item.id === trackId) || (map.certifications || [])[0];
  if (!cert) throw new Error("Certification is not configured");
  const prefs = plan.preferences || {};
  const days = plan.days || [];
  const today = days[0] || null;
  const week = days.slice(1);
  const priorities = plan.priority_skills || [];
  const runway = plan.days_until_exam;

  container.innerHTML = studyLayout(cert, "plan", `<a class="v26-study-back" href="#/progress?track_id=${encodeURIComponent(trackId)}" aria-label="Back">‹</a><header class="v26-recording-progress-head"><p class="v26-kicker">Exam-readiness plan</p><h1>Study Plan</h1><p>Turn your exam date, available study time, weak skills, spaced review, mistakes, and readiness evidence into a practical sequence of work.</p>${evidenceNotice("This plan is generated from Snowflake Brain learning evidence and your study preferences. It is not an official Snowflake schedule or exam recommendation.")}</header><section class="v26-learning-command"><div><span>Exam date</span><strong>${escapeHtml(prefs.exam_date || "Not set")}</strong><small>${runway == null ? "Set a date to calculate runway" : runway >= 0 ? `${runway} days remaining` : "Date has passed"}</small></div><div><span>Daily target</span><strong>${Number(prefs.daily_minutes || 45)}</strong><small>minutes</small></div><div><span>Study days</span><strong>${Number(prefs.days_per_week || 6)}</strong><small>days per week</small></div><div><span>Current readiness</span><strong>${Math.round(Number(plan.readiness_score || 0)) || "—"}</strong><small>/100 internal evidence</small></div></section><section class="v26-progress-section"><div class="v26-section-heading"><p class="v26-kicker">Today</p><h2>${today?.active ? "Do the work with the highest current value." : "Recovery / catch-up day"}</h2></div>${dayCard(today, true)}</section><section class="v26-progress-section"><div class="v26-section-heading"><p class="v26-kicker">This week</p><h2>Keep the loop small and repeatable.</h2></div><div class="v26-plan-grid">${week.length ? week.map((day) => dayCard(day, false)).join("") : `<p class="v26-empty-copy">No weekly plan has been generated yet.</p>`}</div></section><section class="v26-progress-section"><div class="v26-section-heading"><p class="v26-kicker">Before next mock</p><h2>Repair priority skills before adding more timed evidence.</h2></div><div class="v26-priority-skill-grid">${priorities.length ? priorities.slice(0, 5).map(priorityCard).join("") : `<p class="v26-empty-copy">Complete lessons or practice to generate skill priorities.</p>`}</div><div class="v26-result-actions"><a class="v26-btn primary" href="#/practice?track_id=${encodeURIComponent(trackId)}&mode=drill">Targeted drill</a><a class="v26-btn secondary" href="#/mock?track_id=${encodeURIComponent(trackId)}">Open mock exams</a></div></section><section class="v26-progress-section"><div class="v26-section-heading"><p class="v26-kicker">Before exam</p><h2>${beforeExamHeadline(runway, plan)}</h2><p>${beforeExamDetail(runway, plan)}</p></div><div class="v26-result-actions"><a class="v26-btn secondary" href="#/adaptive?track_id=${encodeURIComponent(trackId)}">Check adaptive readiness</a><a class="v26-btn secondary" href="#/due?track_id=${encodeURIComponent(trackId)}">Clear due review</a><a class="v26-btn secondary" href="#/mistakes?track_id=${encodeURIComponent(trackId)}">Repair mistakes</a></div></section><section class="v26-progress-section"><div class="v26-section-heading"><p class="v26-kicker">Plan settings</p><h2>Adjust the runway.</h2></div><form class="v26-plan-form command-plan" data-plan-form><label>Exam date<input type="date" name="exam_date" value="${escapeHtml(prefs.exam_date || "")}"></label><label>Minutes per study day<input type="number" min="15" max="240" name="daily_minutes" value="${Number(prefs.daily_minutes || 45)}"></label><label>Study days per week<input type="number" min="1" max="7" name="days_per_week" value="${Number(prefs.days_per_week || 6)}"></label><button class="v26-btn primary" type="submit">Save plan</button><span data-plan-status aria-live="polite"></span></form></section>`, "", []);

  bindPlan(container, trackId, prefs);
}

function dayCard(day, prominent) {
  if (!day) return `<p class="v26-empty-copy">No plan evidence yet.</p>`;
  return `<article class="${day.active ? "" : "rest"} ${prominent ? "today" : ""}"><span>${prominent ? "Today" : escapeHtml(day.date)}</span><strong>${Number(day.total_minutes || 0)} min</strong>${(day.sessions || []).map((session) => `<a href="${escapeHtml(session.href || "#/progress")}"><b>${escapeHtml(session.title || session.type)}</b><em>${Number(session.minutes || 0)} min</em></a>`).join("")}</article>`;
}

function priorityCard(item) {
  return `<article><span>${item.due_count ? `${Number(item.due_count)} due` : item.open_misses ? `${Number(item.open_misses)} open misses` : "Priority skill"}</span><h3>${escapeHtml(item.skill || item.skill_id)}</h3><p>${Number(item.attempts || 0) ? `${Number(item.accuracy_pct || 0)}% accuracy · mastery level ${Number(item.mastery_level || 1)}` : "No practice evidence yet."}</p><footer><a href="${escapeHtml(item.lesson_url || "#/curriculum")}">Review lesson →</a><a href="${escapeHtml(item.drill_url || "#/practice")}">Drill →</a></footer></article>`;
}

function beforeExamHeadline(runway, plan) {
  if (runway == null) return "Set an exam date only when you want a real runway.";
  if (runway < 0) return "Update the exam date before trusting this plan.";
  const score = Number(plan.readiness_score || 0);
  if (runway <= 7 && score < 70) return "The runway is short; focus on evidence, not volume.";
  if (score >= 82) return "Maintain retrieval and rehearse under time pressure.";
  return "Keep repairing weak skills before you rely on full mocks.";
}

function beforeExamDetail(runway, plan) {
  if (runway == null) return "Without an exam date, the plan stays useful for weekly study but does not make time-pressure recommendations.";
  return `${Math.max(0, Number(runway))} days remain. Current internal readiness is ${Math.round(Number(plan.readiness_score || 0)) || 0}/100 with ${Number(plan.due_today || 0)} review items due and ${Number(plan.open_mistakes || 0)} active mistakes.`;
}

function bindPlan(container, trackId, prefs) {
  const form = container.querySelector("[data-plan-form]");
  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = new FormData(form);
    const button = form.querySelector("button[type='submit']");
    const status = form.querySelector("[data-plan-status]");
    if (button) button.disabled = true;
    if (status) status.textContent = "Saving…";
    try {
      await saveStudyPreferences({ track_id: trackId, exam_date: data.get("exam_date") || null, daily_minutes: Number(data.get("daily_minutes") || prefs.daily_minutes || 45), days_per_week: Number(data.get("days_per_week") || prefs.days_per_week || 6) });
      if (status) status.textContent = "Plan saved. Refreshing priorities…";
      window.dispatchEvent(new HashChangeEvent("hashchange"));
    } catch (error) {
      if (button) button.disabled = false;
      if (status) status.textContent = error.message || "Unable to save plan";
    }
  });
}
