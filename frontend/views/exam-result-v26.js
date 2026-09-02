export const VIEW_ID = "v26-exam-result";

import { escapeHtml, getMockHistory, getMockResult } from "../api.js";
import { activeTrack } from "../ui.js";
import { candidate, refreshCandidate } from "../auth.js";
import { premiumGate } from "../components/entitlement-gates.js";
import { evidenceNotice } from "../components/learning-widgets.js";

const DOMAIN_COLORS = ["#29B5E8", "#6366F1", "#10B981", "#F59E0B", "#8B5CF6"];
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

function isUnanswered(row) { return !Array.isArray(row.selected) || row.selected.length === 0; }
function matchesReview(row) {
  if (reviewFilter === "all") return true;
  if (reviewFilter === "correct") return Boolean(row.is_correct);
  if (reviewFilter === "unanswered") return isUnanswered(row);
  if (reviewFilter === "incorrect") return !row.is_correct && !isUnanswered(row);
  if (reviewFilter === "flagged") return Boolean(row.flagged);
  return true;
}

function renderResult(container, result) {
  const reviews = (result.reviews || []).filter(matchesReview);
  const weakest = (result.weakest_tasks || []).filter((item) => Number(item.total || 0) > 0).slice(0, 3);
  const strongest = (result.strongest_tasks || []).slice(0, 3);
  const readiness = result.ready ? "Ready" : Number(result.scaled_score || 0) >= Math.max(0, Number(result.pass_scaled_score || 750) - 100) ? "Almost Ready" : "Needs Focus";
  container.innerHTML = `<main class="v26-page v26-result-page"><a class="v26-back" href="#/mock?track_id=${encodeURIComponent(result.track_id)}">← Mock Exam</a><header class="v26-result-hero"><p class="v26-kicker">SnowPro Core · COF-C03 · Snowflake Brain simulation</p><span>Mock Exam Result</span><strong>${result.scaled_score}</strong><small>/ ${result.score_scale}</small><h1>${escapeHtml(readiness)}</h1><p>${result.raw_correct} / ${result.total_questions} correct · ${formatTime(result.elapsed_seconds)} used</p><div><span>Practice threshold</span><b>${result.pass_scaled_score}</b></div></header>${evidenceNotice(result.scoring_note || "This is a Snowflake Brain practice score and readiness signal, not an official Snowflake exam result or pass prediction.")}<section class="v26-result-counts"><div><strong>${result.counts?.correct || 0}</strong><span>Correct</span></div><div><strong>${result.counts?.incorrect || 0}</strong><span>Incorrect</span></div><div><strong>${result.counts?.unanswered || 0}</strong><span>Unanswered</span></div><div><strong>${result.counts?.flagged || 0}</strong><span>Flagged</span></div></section><section class="v26-result-section"><div class="v26-section-heading"><p class="v26-kicker">Remediation plan</p><h2>Turn the score into the next study loop.</h2><p>Start with the weakest measured tasks, then review individual misses and validate the repair with a focused drill before the next timed sitting.</p></div>${weakest.length ? `<div class="v26-remediation-grid">${weakest.map((item, index) => remediationCard(item, index)).join("")}</div>` : `<p class="v26-empty-copy">No task-level weakness evidence is available for this sitting.</p>`}<div class="v26-result-actions"><a class="v26-btn primary" href="${weakest[0]?.drill_url || `#/practice?track_id=${encodeURIComponent(result.track_id)}&mode=drill`}">Drill weakest task</a><a class="v26-btn secondary" href="#/mistakes?track_id=${encodeURIComponent(result.track_id)}">Open Mistake Notebook</a><a class="v26-btn secondary" href="#/due?track_id=${encodeURIComponent(result.track_id)}">Review Due Today</a><a class="v26-btn secondary" href="#/adaptive?track_id=${encodeURIComponent(result.track_id)}">Update readiness</a></div></section><section class="v26-result-section"><div class="v26-section-heading"><p class="v26-kicker">Domain Performance</p><h2>Blueprint breakdown</h2></div><div class="v26-result-domains">${(result.domain_performance || []).map(domainRow).join("")}</div></section>${strongest.length ? `<section class="v26-result-section"><div class="v26-section-heading"><p class="v26-kicker">What held up</p><h2>Strongest measured tasks</h2></div><div class="v26-result-strengths">${strongest.map((item) => `<a href="${item.lesson_url}"><span>${escapeHtml(item.task_code || "Task")}</span><strong>${escapeHtml(item.title)}</strong><em>${Number(item.accuracy || 0)}%</em></a>`).join("")}</div></section>` : ""}<section class="v26-result-section"><div class="v26-result-review-head"><div><p class="v26-kicker">Question Review</p><h2>Review every answer.</h2><p>Separate wrong answers from unanswered items: they often represent different remediation problems.</p></div><div class="v26-review-filters">${filterButton("all", "All", result.reviews?.length || 0)}${filterButton("correct", "Correct", result.counts?.correct || 0)}${filterButton("incorrect", "Incorrect", result.counts?.incorrect || 0)}${filterButton("unanswered", "Unanswered", result.counts?.unanswered || 0)}${filterButton("flagged", "Flagged", result.counts?.flagged || 0)}</div></div><div class="v26-review-list">${reviews.map((row) => reviewCard(row, result.track_id)).join("") || `<p class="v26-empty-copy">No questions match this filter.</p>`}</div></section><section class="v26-result-actions"><a class="v26-btn primary" href="#/practice?track_id=${encodeURIComponent(result.track_id)}&mode=drill">Build targeted drill</a><a class="v26-btn secondary" href="#/mock/start?track_id=${encodeURIComponent(result.track_id)}&type=full-mock">Take another mock</a><a class="v26-btn secondary" href="#/study-plan?track_id=${encodeURIComponent(result.track_id)}">Open study plan</a></section></main>`;
  container.querySelectorAll("[data-review-filter]").forEach((button) => button.addEventListener("click", () => { reviewFilter = button.dataset.reviewFilter; renderResult(container, result); }));
}

function remediationCard(item, index) {
  const label = index === 0 ? "Highest priority" : `Priority ${index + 1}`;
  return `<article><span>${label}</span><h3>${escapeHtml(item.task_code ? `Task ${item.task_code} · ${item.title}` : item.title || "Weak task")}</h3><strong>${Number(item.accuracy || 0)}%</strong><p>${Number(item.correct || 0)}/${Number(item.total || 0)} correct in this sitting.</p><footer><a href="${item.lesson_url}">Review lesson →</a><a href="${item.drill_url}">Drill this task →</a></footer></article>`;
}

function domainRow(domain, index) { return `<div><i style="--domain:${color(index)}"></i><span><strong>${escapeHtml(domain.title)}</strong><small>${domain.correct}/${domain.total} correct · ${domain.weight}% exam weight</small></span><div><b style="width:${Math.max(0, Math.min(100, domain.accuracy))}%"></b></div><em>${domain.accuracy}%</em></div>`; }

function reviewCard(row, trackId) {
  const options = row.options || [];
  const selected = (row.selected || []).map((i) => `${String.fromCharCode(65 + i)}. ${options[i] || ""}`).join("; ") || "No answer";
  const correct = (row.correct || []).map((i) => `${String.fromCharCode(65 + i)}. ${options[i] || ""}`).join("; ");
  const stateClass = row.is_correct ? "correct" : isUnanswered(row) ? "unanswered" : "incorrect";
  const stateMark = row.is_correct ? "✓" : isUnanswered(row) ? "—" : "×";
  const stateLabel = row.is_correct ? "Correct" : isUnanswered(row) ? "Unanswered" : "Incorrect";
  return `<details class="v26-review-card ${stateClass}"><summary><span>${stateMark}</span><div><small>Question ${row.position} · ${escapeHtml(row.domain_title || "")}${row.task_code ? ` · Task ${escapeHtml(row.task_code)}` : ""}</small><strong>${escapeHtml(row.question)}</strong></div><em>${row.flagged ? "⚑" : ""}</em></summary><div class="v26-review-body"><div class="v26-review-state"><span>${stateLabel}</span>${row.flagged ? `<b>Flagged for review</b>` : ""}</div><p><b>Your answer</b>${escapeHtml(selected)}</p><p><b>Correct answer</b>${escapeHtml(correct)}</p>${row.explanation ? `<p><b>Correct reasoning</b>${escapeHtml(row.explanation)}</p>` : ""}<p class="v26-review-honesty"><b>Why this matters</b>${isUnanswered(row) ? "No answer was submitted. Review whether this was a knowledge gap, time-pressure decision, or uncertainty before drilling the task." : row.is_correct ? "The answer was correct. Use the explanation to verify the reasoning, not just the selected option." : "The stored explanation gives the correct reasoning. Classify your own root cause in the Mistake Notebook rather than assuming why the miss occurred."}</p><div><a href="${row.lesson_url}">Review task →</a><a href="${row.drill_url}">Drill similar →</a>${!row.is_correct ? `<a href="#/mistakes?track_id=${encodeURIComponent(trackId)}">Mistake Notebook →</a>` : ""}<a href="#/exam-traps?track_id=${encodeURIComponent(trackId)}&domain=${encodeURIComponent(row.domain_id || "")}">Exam traps →</a></div></div></details>`;
}

async function historyPage(container, trackId) {
  const payload = await getMockHistory({ track_id: trackId });
  const rows = payload.history || [];
  container.innerHTML = `<main class="v26-page v26-history-page"><a class="v26-back" href="#/mock?track_id=${encodeURIComponent(trackId)}">← Mock Exam</a><header class="v26-page-intro"><p class="v26-kicker">SnowPro Core · COF-C03</p><h1>Mock History</h1><p>Reopen previous timed sittings and use the weakest-domain evidence to decide what should happen before the next mock.</p></header><section class="v26-history-list">${rows.length ? rows.map((row) => `<a href="#/mock/result?session_id=${row.session_id}"><time>${formatDate(row.finished_at)}</time><strong>${String(row.mode || "Mock").replaceAll("_", " ")}</strong><b>${row.scaled_score}</b><span>${row.ready ? "Ready" : "Review"}</span><small>${row.weakest_domain ? `Weakest: ${escapeHtml(row.weakest_domain.title || row.weakest_domain.domain_id || "domain")} · ${Number(row.weakest_domain.accuracy || 0)}%` : formatTime(row.elapsed_seconds)}</small></a>`).join("") : `<p class="v26-empty-copy">No completed mock exams yet.</p>`}</section></main>`;
}

function filterButton(value, label, count) { return `<button class="${reviewFilter === value ? "active" : ""}" type="button" data-review-filter="${value}">${label}<span>${count}</span></button>`; }
function formatTime(seconds) { const s = Math.max(0, Number(seconds || 0)); const h = Math.floor(s / 3600); const m = Math.floor((s % 3600) / 60); return h ? `${h}h ${m}m` : `${m} min`; }
function formatDate(value) { if (!value) return "Completed mock"; const date = new Date(String(value).replace(" ", "T") + (String(value).includes("Z") ? "" : "Z")); return Number.isNaN(date.getTime()) ? escapeHtml(String(value)) : date.toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }); }
function color(index) { return DOMAIN_COLORS[index % DOMAIN_COLORS.length]; }
