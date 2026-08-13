export const VIEW_ID = "v26-progress";

import { escapeHtml, getIntelligenceReadiness, getMockHistory, getSkillMap, getSkillSummary, getTaskProgress } from "../api.js";
import { activeTrack } from "../ui.js";

const COLORS = ["#e39a60", "#77a4d5", "#9b82cf", "#70af81", "#d16d68"];

export default async function mount(container, params = {}) {
  const trackId = params.track_id || activeTrack();
  const [map, progress, summary, readiness, history] = await Promise.all([
    getSkillMap(),
    getTaskProgress({ track_id: trackId }).catch(() => ({})),
    getSkillSummary({ track_id: trackId }).catch(() => ({ skills: [], domains: [] })),
    getIntelligenceReadiness({ track_id: trackId }).catch(() => ({})),
    getMockHistory({ track_id: trackId }).catch(() => ({ history: [] })),
  ]);
  const cert = (map.certifications || []).find((item) => item.id === trackId) || (map.certifications || [])[0];
  if (!cert) throw new Error("Certification is not configured");
  const score = Math.round(Number(readiness.readiness_score || 0));
  const tasks = [...(summary.skills || [])].sort((a, b) => Number(a.accuracy_pct || 0) - Number(b.accuracy_pct || 0)).slice(0, 6);
  container.innerHTML = `<div class="v26-study-layout">${sidebar(cert)}<main class="v26-study-content"><header class="v26-study-heading"><p class="v26-kicker">Progress · ${escapeHtml(cert.exam_code || "COF-C03")}</p><h1>Your readiness</h1><p>See what you have completed, how each exam domain is performing, and what to study next.</p></header><section class="v26-progress-hero"><div class="major"><span>Overall readiness</span><strong>${score}%</strong><div class="v26-meter"><i style="width:${clamp(score)}%"></i></div></div><div><span>Tasks complete</span><strong>${progress.completed_tasks || 0}/${progress.total_tasks || 19}</strong></div><div><span>Practice attempts</span><strong>${readiness.attempts || 0}</strong></div><div><span>Mock sittings</span><strong>${(history.history || []).length}</strong></div></section><section class="v26-progress-section"><div class="v26-section-heading"><p class="v26-kicker">Domain Performance</p><h2>Exam coverage</h2></div><div class="v26-domain-performance">${domainRows(cert, summary.domains || [])}</div></section><section class="v26-progress-section"><div class="v26-section-heading"><p class="v26-kicker">Review Next</p><h2>Tasks to revisit</h2></div>${tasks.length ? `<div class="v26-weak-list">${tasks.map((item) => `<a href="#/skill?track_id=${encodeURIComponent(cert.id)}&skill_id=${encodeURIComponent(item.skill_id)}"><div><strong>${escapeHtml(item.skill || item.skill_id)}</strong><span>${item.attempts || 0} attempts · ${item.accuracy_pct || 0}% accuracy</span></div><em>Review →</em></a>`).join("")}</div>` : `<p class="v26-empty-copy">Take the diagnostic to establish your first practice baseline.</p>`}</section><section class="v26-progress-section"><div class="v26-section-heading"><p class="v26-kicker">Recent Mocks</p><h2>Timed evidence</h2></div>${mockRows(history.history || [], cert.id)}</section><section class="v26-next-action"><div><p class="v26-kicker">Next Best Action</p><h2>${tasks.length ? "Review one task, then practice it again." : "Start with the diagnostic."}</h2></div><a class="v26-btn primary" href="${tasks.length ? `#/practice?track_id=${encodeURIComponent(cert.id)}&mode=drill&skill_id=${encodeURIComponent(tasks[0].skill_id)}` : `#/practice?track_id=${encodeURIComponent(cert.id)}&mode=diagnostic`}">${tasks.length ? "Start targeted drill" : "Take diagnostic"}</a></section></main></div>`;
}

function domainRows(cert, rows) {
  const byId = new Map(rows.map((row) => [row.domain_id, row]));
  return (cert.domains || []).map((domain, index) => { const row = byId.get(domain.id) || {}; const accuracy = Math.round(Number(row.accuracy_pct || 0)); return `<div><i style="--domain:${COLORS[index % 5]}"></i><span><strong>${escapeHtml(domain.title)}</strong><small>${Number(domain.weight || 0)}% exam weight</small></span><div class="v26-meter"><b style="width:${clamp(accuracy)}%"></b></div><em>${accuracy}%</em></div>`; }).join("");
}

function mockRows(rows, trackId) {
  if (!rows.length) return `<div class="v26-empty-copy">No completed mocks yet. <a href="#/mock?track_id=${encodeURIComponent(trackId)}">Take a mock →</a></div>`;
  return `<div class="v26-history-table">${rows.slice(0, 5).map((row) => `<a href="#/mock/result?session_id=${row.session_id}"><span>${row.finished_at || ""}</span><strong>${String(row.mode || "Mock").replaceAll("_", " ")}</strong><b>${row.scaled_score}</b><em>${row.ready ? "Ready" : "Review"}</em></a>`).join("")}</div>`;
}

function sidebar(cert) {
  const domains = (cert.domains || []).map((domain, index) => `<a class="v26-side-domain" href="#/domain?track_id=${encodeURIComponent(cert.id)}&domain_id=${encodeURIComponent(domain.id)}"><i style="--domain:${COLORS[index % 5]}"></i><b>${index + 1}</b><span>${escapeHtml(domain.title)}</span><em>${Number(domain.weight || 0)}%</em></a>`).join("");
  return `<aside class="v26-study-nav"><div class="v26-side-brand"><span>${escapeHtml(cert.exam_code || "COF-C03")}</span><strong>${escapeHtml(cert.title)}</strong></div><div class="v26-side-group"><small>Study Tools</small><a class="active" href="#/progress?track_id=${encodeURIComponent(cert.id)}">Progress Dashboard</a><a href="#/practice?track_id=${encodeURIComponent(cert.id)}&mode=drill">Drill Mode</a></div><div class="v26-side-group"><small>Curriculum</small><a href="#/curriculum?track_id=${encodeURIComponent(cert.id)}">Exam Domains</a>${domains}</div><div class="v26-side-group"><small>Practice</small><a href="#/exercises?track_id=${encodeURIComponent(cert.id)}">Build Exercises</a><a href="#/practice?track_id=${encodeURIComponent(cert.id)}&mode=diagnostic">Diagnostic Test</a></div><div class="v26-side-group"><small>Look Up</small><a href="#/quick-reference?track_id=${encodeURIComponent(cert.id)}">Quick Reference</a><a href="#/glossary?track_id=${encodeURIComponent(cert.id)}">Glossary</a></div></aside>`;
}
function clamp(value) { return Math.max(0, Math.min(100, Number(value || 0))); }
