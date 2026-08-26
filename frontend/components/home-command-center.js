import { escapeHtml, getDueToday, getIntelligenceReadiness, getMistakeNotebook, getSkillSummary, getStudyPlan } from "../api.js";

export async function renderHomeCommandCenter(container, trackId = "snowpro-core", account = null) {
  const main = container.querySelector("main");
  if (!main) return;

  if (!account) {
    main.insertAdjacentHTML("beforeend", publicTools(trackId));
    return;
  }

  const [due, mistakes, plan, summary, readiness] = await Promise.all([
    getDueToday({ track_id: trackId, limit: 1 }).catch(() => ({ due_count: 0 })),
    getMistakeNotebook({ track_id: trackId, status: "active", limit: 1 }).catch(() => ({ counts: {}, items: [] })),
    getStudyPlan({ track_id: trackId }).catch(() => ({ preferences: {} })),
    getSkillSummary({ track_id: trackId }).catch(() => ({ skills: [] })),
    account.is_premium ? getIntelligenceReadiness({ track_id: trackId }).catch(() => ({})) : Promise.resolve({}),
  ]);

  const skills = (summary.skills || []).filter((item) => Number(item.attempts || 0) > 0);
  const accuracy = skills.length
    ? Math.round(skills.reduce((sum, item) => sum + Number(item.accuracy_pct || 0), 0) / skills.length)
    : 0;
  const openMistakes = Number(mistakes.counts?.open || 0) + Number(mistakes.counts?.reviewing || 0);
  const readinessScore = Number(readiness.readiness_score || 0);
  const examDate = plan.preferences?.exam_date || "";
  const days = examDate ? daysUntil(examDate) : null;

  const root = document.createElement("div");
  root.className = "v26-home-command-wrap";
  root.innerHTML = `<section class="v26-section v26-home-command-section">
    <div class="v26-section-heading v26-command-heading">
      <div><p class="v26-kicker">Your prep command center</p><h2>Know exactly what to do next.</h2><p>Readiness, due reviews, mistakes, and exam pacing in one place — without changing the V26 home experience.</p></div>
      <a href="#/progress?track_id=${encodeURIComponent(trackId)}">Open full progress →</a>
    </div>
    <div class="v26-command-grid">
      ${metric("Exam readiness", readinessScore > 0 ? `${Math.round(readinessScore)}%` : "Building", readinessScore > 0 ? "Weighted evidence score" : "Complete practice to unlock", `#/adaptive?track_id=${encodeURIComponent(trackId)}`)}
      ${metric("Due today", String(Number(due.due_count || 0)), "Spaced-review questions", `#/practice?track_id=${encodeURIComponent(trackId)}&mode=srs`)}
      ${metric("Active mistakes", String(openMistakes), "Rules and traps to repair", `#/mistakes?track_id=${encodeURIComponent(trackId)}`)}
      ${metric("Practice accuracy", `${accuracy}%`, `${skills.length} attempted task${skills.length === 1 ? "" : "s"}`, `#/practice?track_id=${encodeURIComponent(trackId)}`)}
      ${metric("Target exam", days === null ? "Not set" : days >= 0 ? `${days} days` : "Update", examDate ? escapeHtml(examDate) : "Set your exam date", `#/progress?track_id=${encodeURIComponent(trackId)}`)}
    </div>
  </section>${toolGrid(trackId)}</div>`;

  main.appendChild(root);
}

function publicTools(trackId) {
  return `<section class="v26-section v26-home-command-section public">
    <div class="v26-section-heading v26-command-heading"><div><p class="v26-kicker">Everything in one preparation system</p><h2>Study, practise, repair mistakes, then prove readiness.</h2><p>Create a free candidate account to turn the guide into a persistent learning system.</p></div></div>
    ${toolGrid(trackId)}
  </section>`;
}

function toolGrid(trackId) {
  const id = encodeURIComponent(trackId);
  const tools = [
    ["Study Guide", "Domain → task → lesson progression mapped to COF-C03.", `#/curriculum?track_id=${id}`, "01"],
    ["Targeted Practice", "Diagnostic, spaced review, and task-focused drills.", `#/practice?track_id=${id}`, "02"],
    ["Mistake Collection", "Keep every recurring trap visible until it is mastered.", `#/mistakes?track_id=${id}`, "03"],
    ["Mock Exams", "Quick and full timed simulations with remediation.", `#/mock?track_id=${id}`, "04"],
    ["Quick Reference", "High-signal Snowflake comparisons and exam distinctions.", `#/reference?track_id=${id}`, "05"],
    ["Community Insights", "Study strategies, exam tips, common mistakes, and deep dives.", `#/community?track_id=${id}`, "06"],
  ];
  return `<section class="v26-section v26-home-tools"><div class="v26-section-heading"><p class="v26-kicker">Preparation tools</p><h2>One loop from learning to mastery.</h2></div><div class="v26-home-tool-grid">${tools.map(([title, body, href, number]) => `<a href="${href}"><span>${number}</span><h3>${title}</h3><p>${body}</p><em>Open →</em></a>`).join("")}</div></section>`;
}

function metric(label, value, detail, href) {
  return `<a class="v26-command-card" href="${href}"><span>${label}</span><strong>${value}</strong><small>${detail}</small><em>View →</em></a>`;
}

function daysUntil(value) {
  const target = new Date(`${value}T12:00:00`);
  const today = new Date();
  today.setHours(12, 0, 0, 0);
  return Math.ceil((target - today) / 86400000);
}
