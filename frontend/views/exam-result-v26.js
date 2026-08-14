export const VIEW_ID = "v26-exam-result";

import { escapeHtml, getMockHistory, getMockResult } from "../api.js";
import { activeTrack } from "../ui.js";
import { candidate, refreshCandidate } from "../auth.js";
import { premiumGate } from "../components/entitlement-gates.js";

const DOMAIN_COLORS = ["#c87966", "#859db8", "#c49a62", "#7b9e91", "#b97b82"];
let reviewFilter = "all";

export default async function mount(container, params = {}) {
  await refreshCandidate().catch(() => {});
  const account = candidate();
  if (!account) {
    container.innerHTML = premiumGate(account);
    return;
  }
  const path = (window.location.hash || "#/mock/result").split("?")[0];
  if (path === "#/mock/history") return historyPage(container, params.track_id || activeTrack());
  const sessionId = Number(params.session_id || 0);
  if (!sessionId) throw new Error("A result session is required");
  const result = await getMockResult(sessionId);
  reviewFilter = "all";
  renderResult(container, result);
}

function renderResult(container, result) {
  const reviews = (result.reviews || []).filter((row) => reviewFilter === "all" || (reviewFilter === "correct" && row.is_correct) || (reviewFilter === "incorrect" && !row.is_correct) || (reviewFilter === "flagged" && row.flagged));
  container.innerHTML = `<main class="v26-page v26-result-page"><a class="v26-back" href="#/mock?track_id=${encodeURIComponent(result.track_id)}">← Mock Exam</a><header class="v26-result-hero"><p class="v26-kicker">SnowPro Core · COF-C03</p><span>Mock Exam Result</span><strong>${result.scaled_score}</strong><small>/ ${result.score_scale}</small><h1>${result.ready ? "Ready" : "Needs Review"}</h1><p>${result.raw_correct} / ${result.total_questions} correct · ${formatTime(result.elapsed_seconds)} used</p><div><span>Practice threshold</span><b>${result.pass_scaled_score}</b></div></header><section class="v26-result-counts"><div><strong>${result.counts?.correct || 0}</strong><span>Correct</span></div><div><strong>${result.counts?.incorrect || 0}</strong><span>Incorrect</span></div><div><strong>${result.counts?.unanswered || 0}</strong><span>Unanswered</span></div><div><strong>${result.counts?.flagged || 0}</strong><span>Flagged</span></div></section><section class="v26-result-section"><div class="v26-section-heading"><p class="v26-kicker">Domain Performance</p><h2>Blueprint breakdown</h2></div><div class="v26-result-domains">${(result.domain_performance || []).map(domainRow).join("")}</div></section><section class="v26-result-section"><div class="v26-result-review-head"><div><p class="v26-kicker">Question Review</p><h2>Review every answer.</h2></div><div class="v26-review-filters">${filterButton("all", "All", result.reviews?.length || 0)}${filterButton("correct", "Correct", result.counts?.correct || 0)}${filterButton("incorrect", "Incorrect", (result.counts?.incorrect || 0) + (result.counts?.unanswered || 0))}${filterButton("flagged", "Flagged", result.counts?.flagged || 0)}</div></div><div class="v26-review-list">${reviews.map(reviewCard).join("") || `<p class="v26-empty-copy">No questions match this filter.</p>`}</div></section><section class="v26-result-actions"><a class="v26-btn primary" href="#/practice?track_id=${encodeURIComponent(result.track_id)}&mode=drill">Start targeted drill</a><a class="v26-btn secondary" href="#/mock/start?track_id=${encodeURIComponent(result.track_id)}&type=full-mock">Take another mock</a><a class="v26-btn secondary" href="#/progress?track_id=${encodeURIComponent(result.track_id)}">Open progress</a></section><p class="v26-scoring-note">${escapeHtml(result.scoring_note || "Practice scoring is a readiness estimate.")}</p></main>`;
  container.querySelectorAll("[data-review-filter]").forEach((button) => button.addEventListener("click", () => { reviewFilter = button.dataset.reviewFilter; renderResult(container, result); }));
}

function domainRow(domain, index) { return `<div><i style="--domain:${color(index)}"></i><span><strong>${escapeHtml(domain.title)}</strong><small>${domain.correct}/${domain.total} correct · ${domain.weight}% exam weight</small></span><div><b style="width:${Math.max(0, Math.min(100, domain.accuracy))}%"></b></div><em>${domain.accuracy}%</em></div>`; }

function reviewCard(row) {
  const options = row.options || [];
  const selected = (row.selected || []).map((i) => `${String.fromCharCode(65 + i)}. ${options[i] || ""}`).join("; ") || "No answer";
  const correct = (row.correct || []).map((i) => `${String.fromCharCode(65 + i)}. ${options[i] || ""}`).join("; ");
  return `<details class="v26-review-card ${row.is_correct ? "correct" : "incorrect"}"><summary><span>${row.is_correct ? "✓" : "×"}</span><div><small>Question ${row.position} · ${escapeHtml(row.domain_title || "")}${row.task_code ? ` · Task ${escapeHtml(row.task_code)}` : ""}</small><strong>${escapeHtml(row.question)}</strong></div><em>${row.flagged ? "⚑" : ""}</em></summary><div class="v26-review-body"><p><b>Your answer</b>${escapeHtml(selected)}</p><p><b>Correct answer</b>${escapeHtml(correct)}</p>${row.explanation ? `<p><b>Explanation</b>${escapeHtml(row.explanation)}</p>` : ""}<div><a href="${row.lesson_url}">Review task →</a><a href="${row.drill_url}">Drill task →</a></div></div></details>`;
}

async function historyPage(container, trackId) {
  const payload = await getMockHistory({ track_id: trackId });
  const rows = payload.history || [];
  container.innerHTML = `<main class="v26-page v26-history-page"><a class="v26-back" href="#/mock?track_id=${encodeURIComponent(trackId)}">← Mock Exam</a><header class="v26-page-intro"><p class="v26-kicker">SnowPro Core · COF-C03</p><h1>Mock History</h1><p>Reopen previous timed sittings and their detailed score reports.</p></header><section class="v26-history-list">${rows.length ? rows.map((row) => `<a href="#/mock/result?session_id=${row.session_id}"><time>${row.finished_at || ""}</time><strong>${String(row.mode || "Mock").replaceAll("_", " ")}</strong><b>${row.scaled_score}</b><span>${row.ready ? "Ready" : "Review"}</span><small>${formatTime(row.elapsed_seconds)}</small></a>`).join("") : `<p class="v26-empty-copy">No completed mock exams yet.</p>`}</section></main>`;
}

function filterButton(value, label, count) { return `<button class="${reviewFilter === value ? "active" : ""}" type="button" data-review-filter="${value}">${label}<span>${count}</span></button>`; }
function formatTime(seconds) { const s = Math.max(0, Number(seconds || 0)); const h = Math.floor(s / 3600); const m = Math.floor((s % 3600) / 60); return h ? `${h}h ${m}m` : `${m} min`; }
function color(index) { return DOMAIN_COLORS[index % DOMAIN_COLORS.length]; }
