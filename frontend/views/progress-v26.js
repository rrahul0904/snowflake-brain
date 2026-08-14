export const VIEW_ID = "v26-progress";

import { escapeHtml, getIntelligenceReadiness, getMockHistory, getSkillMap, getSkillSummary, getTaskProgress } from "../api.js";
import { activeTrack } from "../ui.js";
import { candidate, refreshCandidate } from "../auth.js";

const COLORS = ["#c87966", "#859db8", "#c49a62", "#7b9e91", "#b97b82"];

export default async function mount(container, params = {}) {
  const trackId = params.track_id || activeTrack();
  await refreshCandidate().catch(() => {});
  const account = candidate();
  if (!account) {
    container.innerHTML = `<main class="v26-page"><section class="v26-page-intro centered"><p class="v26-kicker">Progress</p><h1>Your preparation evidence belongs to you.</h1><p>Create a Free candidate account to persist completed tasks, diagnostic and drill attempts, bookmarks, notes, and build-exercise activity.</p><div class="v26-hero-actions"><button class="v26-btn primary" type="button" data-auth-intent="signup">Create Free Account</button><button class="v26-btn secondary" type="button" data-auth-intent="login">Sign In</button></div></section></main>`;
    return;
  }
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
  const basicAttempts = (summary.skills || []).reduce((sum, item) => sum + Number(item.attempts || 0), 0);
  const score = account.is_premium ? Math.round(Number(readiness.readiness_score || 0)) : Math.round(Number(progress.completed_tasks || 0) / Math.max(1, Number(progress.total_tasks || 19)) * 100);
  const tasks = [...(summary.skills || [])].sort((a, b) => Number(a.accuracy_pct || 0) - Number(b.accuracy_pct || 0)).slice(0, 6);
  container.innerHTML = `<div class="v26-study-layout">${sidebar(cert)}<main class="v26-study-content"><header class="v26-study-heading"><p class="v26-kicker">Progress · ${escapeHtml(cert.exam_code || "COF-C03")}</p><h1>${account.is_premium ? "Your readiness" : "Your learning progress"}</h1><p>${account.is_premium ? "See learning completion, domain performance, and persisted mock evidence in one view." : "Track completed tasks and untimed practice. Premium exam analytics stay separate until they are genuinely available to your membership."}</p></header><section class="v26-progress-hero"><div class="major"><span>${account.is_premium ? "Overall readiness" : "Curriculum completion"}</span><strong>${score}%</strong><div class="v26-meter"><i style="width:${clamp(score)}%"></i></div></div><div><span>Tasks complete</span><strong>${progress.completed_tasks || 0}/${progress.total_tasks || 19}</strong></div><div><span>Practice attempts</span><strong>${account.is_premium ? readiness.attempts || basicAttempts : basicAttempts}</strong></div>${account.is_premium ? `<div><span>Mock sittings</span><strong>${(history.history || []).length}</strong></div>` : `<div class="premium-locked"><span>Exam analytics</span><strong>Premium</strong></div>`}</section><section class="v26-progress-section"><div class="v26-section-heading"><p class="v26-kicker">Domain Performance</p><h2>Learning evidence</h2></div><div class="v26-domain-performance">${domainRows(cert, summary.domains || [])}</div></section><section class="v26-progress-section"><div class="v26-section-heading"><p class="v26-kicker">Review Next</p><h2>Tasks to revisit</h2></div>${tasks.length ? `<div class="v26-weak-list">${tasks.map((item) => `<a href="#/skill?track_id=${encodeURIComponent(cert.id)}&skill_id=${encodeURIComponent(item.skill_id)}"><div><strong>${escapeHtml(item.skill || item.skill_id)}</strong><span>${item.attempts || 0} attempts · ${item.accuracy_pct || 0}% accuracy</span></div><em>Review →</em></a>`).join("")}</div>` : `<p class="v26-empty-copy">Take the diagnostic to establish your first practice baseline.</p>`}</section><section class="v26-progress-section"><div class="v26-section-heading"><p class="v26-kicker">${account.is_premium ? "Recent Mocks" : "Premium Practice"}</p><h2>${account.is_premium ? "Timed evidence" : "Exam-depth analytics"}</h2></div>${account.is_premium ? mockRows(history.history || [], cert.id) : premiumProgressGate()}</section><section class="v26-next-action"><div><p class="v26-kicker">Next Best Action</p><h2>${tasks.length ? "Review one task, then practice it again." : "Start with the diagnostic."}</h2></div><a class="v26-btn primary" href="${tasks.length ? `#/practice?track_id=${encodeURIComponent(cert.id)}&mode=drill&skill_id=${encodeURIComponent(tasks[0].skill_id)}` : `#/practice?track_id=${encodeURIComponent(cert.id)}&mode=diagnostic`}">${tasks.length ? "Start targeted drill" : "Take diagnostic"}</a></section></main></div>`;
}

function domainRows(cert, rows) {
  const byId = new Map(rows.map((row) => [row.domain_id, row]));
  return (cert.domains || []).map((domain, index) => { const row = byId.get(domain.id) || {}; const accuracy = Math.round(Number(row.accuracy_pct || 0)); return `<div><i style="--domain:${COLORS[index % 5]}"></i><span><strong>${escapeHtml(domain.title)}</strong><small>${Number(domain.weight || 0)}% exam weight</small></span><div class="v26-meter"><b style="width:${clamp(accuracy)}%"></b></div><em>${accuracy}%</em></div>`; }).join("");
}

function mockRows(rows, trackId) {
  if (!rows.length) return `<div class="v26-empty-copy">No completed mocks yet. <a href="#/mock?track_id=${encodeURIComponent(trackId)}">Take a mock →</a></div>`;
  return `<div class="v26-history-table">${rows.slice(0, 5).map((row) => `<a href="#/mock/result?session_id=${row.session_id}"><span>${row.finished_at || ""}</span><strong>${String(row.mode || "Mock").replaceAll("_", " ")}</strong><b>${row.scaled_score}</b><em>${row.ready ? "Ready" : "Review"}</em></a>`).join("")}</div>`;
}

function premiumProgressGate() { return `<div class="v26-progress-premium-gate"><strong>Full exam simulation and detailed exam analytics are included with Premium.</strong><p>Upgrade access adds mock history, question-by-question review, domain performance, and task-level exam evidence.</p><a class="v26-btn secondary" href="#/membership">View Premium</a></div>`; }

function sidebar(cert) {
  const domains = (cert.domains || []).map((domain, index) => `<a class="v26-side-domain" href="#/domain?track_id=${encodeURIComponent(cert.id)}&domain_id=${encodeURIComponent(domain.id)}"><i style="--domain:${COLORS[index % 5]}"></i><b>${index + 1}</b><span>${escapeHtml(domain.title)}</span><em>${Number(domain.weight || 0)}%</em></a>`).join("");
  return `<aside class="v26-study-nav" aria-label="Study navigation"><div class="v26-side-group"><small>Study Tools</small><a class="active" href="#/progress?track_id=${encodeURIComponent(cert.id)}">Progress Dashboard</a><a href="#/practice?track_id=${encodeURIComponent(cert.id)}&mode=drill">Drill Mode</a></div><div class="v26-side-group"><small>Curriculum</small><a href="#/curriculum?track_id=${encodeURIComponent(cert.id)}">Exam Domains</a>${domains}</div><div class="v26-side-group"><small>Practice</small><a href="#/exercises?track_id=${encodeURIComponent(cert.id)}">Build Exercises</a><a href="#/practice?track_id=${encodeURIComponent(cert.id)}&mode=diagnostic">Diagnostic Test</a></div><div class="v26-side-group"><small>Look Up</small><a href="#/quick-reference?track_id=${encodeURIComponent(cert.id)}">Quick Reference</a><a href="#/glossary?track_id=${encodeURIComponent(cert.id)}">Glossary</a></div></aside>`;
}
function clamp(value) { return Math.max(0, Math.min(100, Number(value || 0))); }
