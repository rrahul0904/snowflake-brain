import {
  escapeHtml,
  getDueToday,
  getIntelligenceReadiness,
  getMistakeNotebook,
  getMockHistory,
  getSkillMap,
  getSkillSummary,
  getStudyPlan,
  getTaskProgress,
} from "../api.js";

const DOMAIN_COLORS = ["#29B5E8", "#6366F1", "#10B981", "#F59E0B", "#8B5CF6"];

export async function renderHomeCommandCenter(container, trackId = "snowpro-core", account = null) {
  const main = container.querySelector("main");
  if (!main) return;

  if (!account) {
    main.insertAdjacentHTML("beforeend", publicPreview(trackId));
    return;
  }

  const fallback = [
    { due_count: 0, questions: [], task_reviews: [] },
    { counts: {}, items: [] },
    { preferences: {}, priority_skills: [], days: [] },
    { skills: [], domains: [] },
    { history: [] },
    { certifications: [] },
    { completed_skill_ids: [] },
    {},
  ];
  // The command center is a convenience aggregate, not a reason to hold the
  // learner's Home route hostage if one optional reporting request stalls.
  // The fallback deliberately reports no evidence; it never invents progress.
  const [due, mistakes, plan, summary, history, map, progress, readiness] = await Promise.race([Promise.all([
    getDueToday({ track_id: trackId, limit: 5 }).catch(() => ({ due_count: 0, questions: [], task_reviews: [] })),
    getMistakeNotebook({ track_id: trackId, status: "active", limit: 5 }).catch(() => ({ counts: {}, items: [] })),
    getStudyPlan({ track_id: trackId }).catch(() => ({ preferences: {}, priority_skills: [], days: [] })),
    getSkillSummary({ track_id: trackId }).catch(() => ({ skills: [], domains: [] })),
    getMockHistory({ track_id: trackId }).catch(() => ({ history: [] })),
    getSkillMap().catch(() => ({ certifications: [] })),
    getTaskProgress({ track_id: trackId }).catch(() => ({ completed_skill_ids: [] })),
    account.is_premium ? getIntelligenceReadiness({ track_id: trackId }).catch(() => ({})) : Promise.resolve({}),
  ]), new Promise((resolve) => window.setTimeout(() => resolve(fallback), 8000))]);

  const cert = (map.certifications || []).find((item) => item.id === trackId) || (map.certifications || [])[0] || { domains: [] };
  const skills = summary.skills || [];
  const attempted = skills.filter((item) => Number(item.attempts || 0) > 0);
  const accuracy = attempted.length
    ? Math.round(attempted.reduce((sum, item) => sum + Number(item.accuracy_pct || 0), 0) / attempted.length)
    : 0;
  const openMistakes = Number(mistakes.counts?.open || 0) + Number(mistakes.counts?.reviewing || 0);
  const computedReadiness = computeReadiness(progress, attempted, history.history || []);
  const readinessScore = Number(readiness.readiness_score || 0) || computedReadiness;
  const evidenceConfidence = evidenceConfidenceLabel(readiness.evidence_confidence, progress, attempted, history.history || [], summary.domains || []);
  const examDate = plan.preferences?.exam_date || "";
  const days = examDate ? daysUntil(examDate) : null;
  const latestMock = (history.history || [])[0] || null;
  const next = nextBestAction(trackId, due, mistakes, attempted, progress, latestMock, cert);
  const status = readinessLabel(readinessScore);

  const root = document.createElement("div");
  root.className = "v26-home-command-wrap";
  root.innerHTML = `<section class="v26-section v26-home-command-section">
    <div class="v26-section-heading v26-command-heading">
      <div><p class="v26-kicker">Your study command center</p><h2>Turn evidence into the next move.</h2><p>Readiness is based on Snowflake Brain study activity and practice evidence. It is not an official Snowflake exam prediction.</p></div>
      <a href="#/progress?track_id=${encodeURIComponent(trackId)}">Open full progress →</a>
    </div>
    <div class="v26-next-best-action">
      <article class="v26-next-best-primary"><p class="v26-kicker">Next best study action</p><h3>${escapeHtml(next.title)}</h3><p>${escapeHtml(next.detail)}</p>${next.reasons?.length ? `<div class="v26-why-now"><strong>Why now</strong><ul>${next.reasons.map((reason) => `<li>${escapeHtml(reason)}</li>`).join("")}</ul></div>` : ""}<footer><a class="v26-btn primary" href="${next.href}">${escapeHtml(next.cta)}</a>${next.secondaryHref ? `<a class="v26-btn secondary" href="${next.secondaryHref}">${escapeHtml(next.secondaryLabel)}</a>` : ""}</footer></article>
      <article class="v26-readiness-compact"><div class="v26-readiness-ring" style="--score:${Math.max(0, Math.min(100, Math.round(readinessScore)))}"><strong>${readinessScore ? Math.round(readinessScore) : "—"}</strong></div><div><p class="v26-kicker">Readiness</p><h3>${status}</h3><p>${readinessScore ? "Weighted study evidence" : "Complete a lesson or practice session to start the signal."}</p><dl class="v26-evidence-confidence"><dt>Evidence confidence</dt><dd data-evidence-confidence="${escapeHtml(evidenceConfidence.toLowerCase())}">${escapeHtml(evidenceConfidence)}</dd></dl></div></article>
    </div>
    <div class="v26-command-grid">
      ${metric("Due today", String(Number(due.due_count || 0)), `${Number(due.question_due_count || 0)} question · ${Number(due.task_due_count || 0)} concept`, `#/due?track_id=${encodeURIComponent(trackId)}`)}
      ${metric("Active mistakes", String(openMistakes), "Recurring concepts to repair", `#/mistakes?track_id=${encodeURIComponent(trackId)}`)}
      ${metric("Practice accuracy", attempted.length ? `${accuracy}%` : "—", attempted.length ? `${attempted.length} attempted tasks` : "No practice evidence yet", `#/practice?track_id=${encodeURIComponent(trackId)}`)}
      ${metric("Last mock", latestMock ? String(latestMock.scaled_score || "—") : "None", latestMock ? `${String(latestMock.mode || "mock").replaceAll("_", " ")}` : "Take a timed mock when ready", `#/mock?track_id=${encodeURIComponent(trackId)}`)}
      ${metric("Target exam", days === null ? "Not set" : days >= 0 ? `${days} days` : "Update", examDate ? escapeHtml(examDate) : "Set your exam date", `#/progress?track_id=${encodeURIComponent(trackId)}`)}
    </div>
  </section>
  ${domainMap(cert, summary, progress, trackId)}
  ${toolGrid(trackId)}</div>`;

  main.appendChild(root);
}

function publicPreview(trackId) {
  const id = encodeURIComponent(trackId);
  return `<section class="v26-section v26-home-command-section public">
    <div class="v26-section-heading v26-command-heading"><div><p class="v26-kicker">Snowflake Study Command Center</p><h2>One preparation loop from diagnosis to verified credential.</h2><p>Create a free candidate account to unlock persistent readiness, spaced review, mistakes, timed mocks, labs, and study planning. No learner statistics are fabricated for this preview.</p></div></div>
    <div class="v26-next-best-action"><article class="v26-next-best-primary"><p class="v26-kicker">How the system works</p><h3>Diagnose → study → drill → mock → remediate → repeat.</h3><p>Start with official exam facts, then use your own activity to decide what should come next.</p><footer><a class="v26-btn primary" href="#/certifications">Explore certifications</a><a class="v26-btn secondary" href="#/exam-guide?track_id=${id}">Read exam guide</a></footer></article><article class="v26-readiness-compact"><div class="v26-readiness-ring" style="--score:0"><strong>—</strong></div><div><p class="v26-kicker">Readiness</p><h3>Your evidence, not a fake score</h3><p>A readiness score appears only after candidate study activity exists.</p></div></article></div>
    ${toolGrid(trackId)}
  </section>`;
}

function domainMap(cert, summary, progress, trackId) {
  const summaries = new Map((summary.domains || []).map((item) => [item.domain_id, item]));
  const completed = new Set(progress.completed_skill_ids || []);
  const rows = (cert.domains || []).map((domain, index) => {
    const skills = domain.skills || [];
    const done = skills.filter((skill) => completed.has(skill.id)).length;
    const pct = Math.round(done / Math.max(1, skills.length) * 100);
    const evidence = summaries.get(domain.id) || {};
    const accuracy = Number(evidence.accuracy_pct || 0);
    return `<a class="v26-command-domain" style="--domain:${DOMAIN_COLORS[index % DOMAIN_COLORS.length]}" href="#/domain?track_id=${encodeURIComponent(trackId)}&domain_id=${encodeURIComponent(domain.id)}"><span>DOMAIN ${index + 1} · ${Number(domain.weight || 0)}%</span><h3>${escapeHtml(domain.title)}</h3><div class="bar"><i style="width:${pct}%"></i></div><dl><dt>Completion</dt><dd>${done}/${skills.length}</dd><dt>Practice</dt><dd>${Number(evidence.attempts || 0) ? `${accuracy}%` : "—"}</dd><dt>Next</dt><dd>${done < skills.length ? "Study" : accuracy && accuracy < 80 ? "Drill" : "Maintain"}</dd></dl></a>`;
  }).join("");
  if (!rows) return "";
  return `<section class="v26-section"><div class="v26-section-heading"><p class="v26-kicker">SnowPro domain map</p><h2>See where the exam weight meets your evidence.</h2><p>Completion and practice evidence stay separate so finishing a lesson never masquerades as mastery.</p></div><div class="v26-command-domain-map">${rows}</div></section>`;
}

function nextBestAction(trackId, due, mistakes, attempted, progress, latestMock, cert) {
  const id = encodeURIComponent(trackId);
  const questionDue = Number(due.question_due_count ?? due.questions?.length ?? 0);
  const taskDue = Number(due.task_due_count ?? due.task_reviews?.length ?? 0);
  if (questionDue > 0) return { title: `Clear ${questionDue} retrieval review${questionDue === 1 ? "" : "s"}`, detail: "Attempt-driven spaced review is already due and should be cleared before adding more new material.", reasons: ["The retrieval interval has matured", taskDue ? `${taskDue} manually scheduled concept review${taskDue === 1 ? " is" : "s are"} also waiting` : "No manual concept review is more urgent"], href: `#/due?track_id=${id}`, cta: "Open Due Today", secondaryHref: `#/study-plan?track_id=${id}`, secondaryLabel: "See study plan" };
  if (taskDue > 0) return { title: `Review ${taskDue} scheduled concept${taskDue === 1 ? "" : "s"}`, detail: "You explicitly asked Snowflake Brain to bring these lesson tasks back. Retrieve the decision rule before drilling it.", reasons: ["Scheduled concept review is due now", "No attempt-driven SRS item is currently ahead of it"], href: `#/due?track_id=${id}`, cta: "Review concepts", secondaryHref: `#/practice?track_id=${id}&mode=drill`, secondaryLabel: "Targeted drill" };
  const items = mistakes.items || [];
  const highConfidenceWrong = items.filter((item) => Number(item.last_confidence || 0) >= 4 && item.status !== "mastered").length;
  if (highConfidenceWrong > 0) return { title: `Repair ${highConfidenceWrong} high-confidence miss${highConfidenceWrong === 1 ? "" : "es"}`, detail: "Confidently wrong evidence is higher risk than an uncertain miss because the incorrect rule may feel settled.", reasons: [`${highConfidenceWrong} active mistake${highConfidenceWrong === 1 ? " has" : "s have"} high recorded confidence`, "No due review currently outranks this calibration risk"], href: `#/mistakes?track_id=${id}`, cta: "Classify and repair", secondaryHref: `#/confidence?track_id=${id}`, secondaryLabel: "Open calibration" };
  const openMistakes = Number(mistakes.counts?.open || 0) + Number(mistakes.counts?.reviewing || 0);
  if (openMistakes > 0) return { title: `Repair ${openMistakes} active mistake${openMistakes === 1 ? "" : "s"}`, detail: "Recurring misses are exam risk. Review the rule, then drill the related task until the pattern changes.", reasons: ["Mistake Notebook still has unresolved evidence", "No review item is due ahead of it"], href: `#/mistakes?track_id=${id}`, cta: "Open mistake notebook", secondaryHref: `#/practice?track_id=${id}&mode=drill`, secondaryLabel: "Targeted drill" };
  const weak = [...attempted].sort((a, b) => Number(a.accuracy_pct || 0) - Number(b.accuracy_pct || 0))[0];
  if (weak && Number(weak.accuracy_pct || 0) < 80) return { title: `Revisit ${weak.task_code || "your weakest task"}: ${weak.skill || weak.skill_id}`, detail: `${Number(weak.accuracy_pct || 0)}% accuracy across ${Number(weak.attempts || 0)} attempts makes this the clearest current weakness.`, reasons: [`Lowest measured task accuracy: ${Number(weak.accuracy_pct || 0)}%`, `${Number(weak.attempts || 0)} recorded attempt${Number(weak.attempts || 0) === 1 ? "" : "s"}`], href: `#/skill?track_id=${id}&skill_id=${encodeURIComponent(weak.skill_id)}`, cta: "Review lesson", secondaryHref: `#/practice?track_id=${id}&mode=drill&skill_id=${encodeURIComponent(weak.skill_id)}`, secondaryLabel: "Drill this task" };
  const completed = new Set(progress.completed_skill_ids || []);
  const unfinished = (cert.domains || []).flatMap((domain) => (domain.skills || []).filter((skill) => !completed.has(skill.id)).map((skill) => ({ ...skill, domain }))).sort((a, b) => Number(b.domain?.weight || 0) - Number(a.domain?.weight || 0))[0];
  if (unfinished) return { title: `Continue ${unfinished.task_code || "the curriculum"}: ${unfinished.title || unfinished.id}`, detail: "With no due reviews or measured weakness dominating the signal, continue coverage in the highest-weight unfinished domain.", reasons: [`Domain exam weight: ${Number(unfinished.domain?.weight || 0)}%`, "This task has not yet been marked complete"], href: `#/skill?track_id=${id}&skill_id=${encodeURIComponent(unfinished.id)}`, cta: "Open next lesson", secondaryHref: `#/curriculum?track_id=${id}`, secondaryLabel: "View curriculum" };
  if (!latestMock) return { title: "You have study evidence — add a timed benchmark", detail: "A mock gives you time-pressure and domain-performance evidence that lessons and drills cannot provide alone.", reasons: ["Curriculum coverage exists", "No completed mock benchmark is recorded"], href: `#/mock?track_id=${id}`, cta: "Choose a mock", secondaryHref: `#/practice?track_id=${id}`, secondaryLabel: "Practice first" };
  return { title: "Keep the loop moving with targeted practice", detail: "No urgent due reviews or active mistakes are dominating the signal. Use a focused drill to strengthen the lowest-confidence area before the next mock.", reasons: ["Review queue is clear", "No unresolved mistake currently outranks maintenance practice"], href: `#/practice?track_id=${id}&mode=drill`, cta: "Build a targeted drill", secondaryHref: `#/adaptive?track_id=${id}`, secondaryLabel: "Open adaptive readiness" };
}

function toolGrid(trackId) {
  const id = encodeURIComponent(trackId);
  const tools = [
    ["Curriculum", "Five weighted domains and nineteen task statements.", `#/curriculum?track_id=${id}`, "01"],
    ["Targeted Practice", "Diagnostic, spaced review, and task-focused drills.", `#/practice?track_id=${id}`, "02"],
    ["Mistake Notebook", "Keep recurring traps visible until they are mastered.", `#/mistakes?track_id=${id}`, "03"],
    ["Mock Exams", "Quick and full timed simulations with remediation.", `#/mock?track_id=${id}`, "04"],
    ["Build Exercises", "Hands-on Snowflake scenarios with deterministic checks.", `#/exercises?track_id=${id}`, "05"],
    ["Verified Credentials", "Verify a SnowPro credential after you pass.", `#/credentials?track_id=${id}`, "06"],
  ];
  return `<section class="v26-section v26-home-tools"><div class="v26-section-heading"><p class="v26-kicker">Preparation system</p><h2>Learn, prove, repair, repeat.</h2></div><div class="v26-home-tool-grid">${tools.map(([title, body, href, number]) => `<a href="${href}"><span>${number}</span><h3>${title}</h3><p>${body}</p><em>Open →</em></a>`).join("")}</div></section>`;
}

function metric(label, value, detail, href) {
  return `<a class="v26-command-card" href="${href}"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong><small>${escapeHtml(detail)}</small><em>View →</em></a>`;
}

function readinessLabel(score) {
  if (!score) return "Building evidence";
  if (score >= 82) return "Ready";
  if (score >= 70) return "Almost Ready";
  if (score >= 50) return "Needs Focus";
  return "At Risk";
}

function evidenceConfidenceLabel(serverValue, progress, attempted, history, domains) {
  const normalized = String(serverValue || "").toLowerCase();
  if (["high", "medium", "low"].includes(normalized)) return normalized[0].toUpperCase() + normalized.slice(1);
  const attempts = attempted.reduce((sum, row) => sum + Number(row.attempts || 0), 0);
  const domainEvidence = (domains || []).filter((row) => Number(row.attempts || 0) > 0).length;
  const lessonCoverage = Number(progress.completed_tasks || 0) / Math.max(1, Number(progress.total_tasks || 19));
  let points = 0;
  if (attempts >= 60) points += 2; else if (attempts >= 20) points += 1;
  if (domainEvidence >= 5) points += 2; else if (domainEvidence >= 3) points += 1;
  if ((history || []).length >= 2) points += 2; else if ((history || []).length >= 1) points += 1;
  if (lessonCoverage >= .75) points += 1;
  return points >= 6 ? "High" : points >= 3 ? "Medium" : "Low";
}

function computeReadiness(progress, attempted, history) {
  const lessonPct = Math.round(Number(progress.completed_tasks || 0) / Math.max(1, Number(progress.total_tasks || 19)) * 100);
  const practicePct = attempted.length ? attempted.reduce((sum, row) => sum + Number(row.accuracy_pct || 0), 0) / attempted.length : 0;
  const mock = history[0] ? Math.max(0, Math.min(100, Number(history[0].scaled_score || 0) / 10)) : 0;
  return Math.round(lessonPct * .3 + practicePct * .45 + mock * .25);
}

function daysUntil(value) {
  const target = new Date(`${value}T12:00:00`);
  const today = new Date();
  today.setHours(12, 0, 0, 0);
  return Math.ceil((target - today) / 86400000);
}
