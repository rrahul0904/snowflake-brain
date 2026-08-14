export const VIEW_ID = "v26-progress";

import { escapeHtml, getIntelligenceReadiness, getMockHistory, getSkillMap, getSkillSummary, getTaskProgress } from "../api.js";
import { activeTrack } from "../ui.js";
import { candidate, refreshCandidate } from "../auth.js";
import { DOMAIN_COLORS, studyLayout } from "../components/study-shell.js";

export default async function mount(container, params = {}) {
  const trackId = params.track_id || activeTrack();
  await refreshCandidate().catch(() => {});
  const account = candidate();
  if (!account) throw new Error("Candidate session required");

  const [map, progress, summary] = await Promise.all([
    getSkillMap(),
    getTaskProgress({ track_id: trackId }).catch(() => ({})),
    getSkillSummary({ track_id: trackId }).catch(() => ({ skills: [], domains: [] })),
  ]);
  const [readiness, history] = account.is_premium ? await Promise.all([
    getIntelligenceReadiness({ track_id: trackId }).catch(() => ({})),
    getMockHistory({ track_id: trackId }).catch(() => ({ history: [] })),
  ]) : [{}, { history: [] }];
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

  container.innerHTML = studyLayout(cert, "progress", `<a class="v26-study-back" href="#/curriculum?track_id=${encodeURIComponent(cert.id)}" aria-label="Back">‹</a><header class="v26-recording-progress-head"><h1>Your Progress</h1><p>Track your readiness across all five domains and see where another study pass will help most.</p></header><section class="v26-readiness-panel"><span>Exam Readiness</span><div class="v26-readiness-score">${score}<small> / 100</small></div><div class="v26-readiness-status">${status}</div><div class="v26-readiness-components"><div><span>Lessons (30%)</span><b>${lessonsPct}%</b></div><div><span>Practice (40%)</span><b>${practicePct}%</b></div><div><span>Drill mastery (30%)</span><b>${drillPct}%</b></div></div></section>${hasEvidence ? "" : `<section class="v26-no-progress"><strong>No progress yet</strong><p>Complete lessons and answer practice questions to build your readiness score.</p></section>`}<section class="v26-recording-domain-progress"><h2>Domain Progress</h2>${domainProgress(cert, completed)}</section>${tasks.length ? `<section class="v26-progress-section"><div class="v26-section-heading"><p class="v26-kicker">Review Next</p><h2>Tasks to revisit</h2></div><div class="v26-weak-list">${tasks.map((item) => `<a href="#/skill?track_id=${encodeURIComponent(cert.id)}&skill_id=${encodeURIComponent(item.skill_id)}"><div><strong>${escapeHtml(item.skill || item.skill_id)}</strong><span>${item.attempts || 0} attempts · ${item.accuracy_pct || 0}% accuracy</span></div><em>Review →</em></a>`).join("")}</div></section>` : ""}${account.is_premium && (history.history || []).length ? `<section class="v26-progress-section"><div class="v26-section-heading"><p class="v26-kicker">Recent Mocks</p><h2>Timed evidence</h2></div>${mockRows(history.history || [])}</section>` : ""}<p class="v26-scoring-note">Readiness is an internal study score for preparation only; it is not Snowflake's exam scoring formula.</p>`);
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
