export const VIEW_ID = "v26-practice";

import { escapeHtml, getDueToday, getMockConfig, getPracticeTests, getSkillMap, getSkillSummary, gradeQuiz, recordAttempt, startMockSession, startQuiz } from "../api.js";
import { activeTrack } from "../ui.js";
import { candidate, refreshCandidate } from "../auth.js";
import { DOMAIN_COLORS, studyLayout } from "../components/study-shell.js";

const state = { questions: [], answers: new Map(), confidences: new Map(), index: 0, mode: "", trackId: "snowpro-core", skillId: "", domainId: "", submitted: false, result: null, account: null };

export default async function mount(container, params = {}) {
  state.trackId = params.track_id || activeTrack();
  await refreshCandidate().catch(() => {});
  state.account = candidate();
  if (!state.account) throw new Error("Candidate session required");
  if (params.mode === "srs") return launchSrs(container, params);
  if (params.mode === "drill" && params.start !== "1") return drillSetup(container, params);
  if (params.mode === "diagnostic" && params.start !== "1") return diagnosticSetup(container, params);
  if (["diagnostic", "drill"].includes(params.mode || "")) return launch(container, params);
  return landing(container);
}

async function landing(container) {
  const [config, current, legacy, due] = await Promise.all([
    getMockConfig({ track_id: state.trackId }),
    getPracticeTests({ track_id: state.trackId, source_kind: "source" }).catch(() => ({ tests: [] })),
    getPracticeTests({ track_id: state.trackId, include_legacy: true, source_kind: "legacy" }).catch(() => ({ tests: [] })),
    getDueToday({ track_id: state.trackId, limit: 1 }).catch(() => ({ due_count: 0 })),
  ]);
  const quick = config.quick_mock || {};
  const full = config.full_mock || {};
  const dueCount = Number(due.due_count || 0);
  container.innerHTML = `<main class="v26-page v26-practice-page"><section class="v26-page-intro centered"><p class="v26-kicker">SnowPro Core · COF-C03</p><h1>Practice</h1><p>Find your gaps, repair a task, or rehearse the timed exam experience.</p></section><section class="v26-section"><div class="v26-practice-grid">${card("Due Today", "Spaced Review", "Revisit questions exactly when your review schedule says they are due.", `${dueCount} question${dueCount === 1 ? "" : "s"} due`, `#/practice?track_id=${state.trackId}&mode=srs`, dueCount > 0)}${card("Diagnostic", "Find weak areas", "A balanced untimed baseline across all current exam domains.", "20 questions", `#/practice?track_id=${state.trackId}&mode=diagnostic`, dueCount === 0)}${card("Targeted Drill", "Repair weak tasks", "Focused practice by domain or across your current weak areas.", "15 questions", `#/practice?track_id=${state.trackId}&mode=drill`)}${card("Quick Mock", "Timed readiness check", "A focused timed sitting using the persisted exam player.", `${quick.question_count || 30} questions · ${quick.time_limit_minutes || 45} min`, `#/mock/start?track_id=${state.trackId}&type=quick-mock`)}${card("Full Mock", "Complete simulation", "Flags, navigation, autosave, refresh/resume, timer, and post-exam review.", `${full.question_count || 100} questions · ${full.time_limit_minutes || 120} min`, `#/mock/start?track_id=${state.trackId}&type=full-mock`, false, true)}</div></section>${state.account?.is_premium ? sourceSection(current.tests || [], legacy.tests || []) : ""}</main>`;
  bindSource(container);
}

async function drillSetup(container, params) {
  const [map, summary] = await Promise.all([
    getSkillMap(),
    getSkillSummary({ track_id: state.trackId }).catch(() => ({ skills: [] })),
  ]);
  const cert = (map.certifications || []).find((item) => item.id === state.trackId) || (map.certifications || [])[0];
  if (!cert) throw new Error("Certification is not configured");
  const skills = summary.skills || [];
  const attempted = skills.reduce((sum, item) => sum + Number(item.attempts || 0), 0);
  const mastered = skills.filter((item) => Number(item.attempts || 0) > 0 && Number(item.accuracy_pct || 0) >= 80).length;
  const weak = skills.filter((item) => Number(item.attempts || 0) > 0 && Number(item.accuracy_pct || 0) < 70).length;
  state.domainId = params.domain_id || "";
  container.innerHTML = studyLayout(cert, "drill", `<section class="v26-practice-setup center"><h1>Drill Mode</h1><p class="lede">Up to 15 questions per session, focused on the domain you choose. Use short repeated sessions to repair weak areas without turning practice into another full mock.</p><div class="v26-drill-stats"><div><strong>${attempted}</strong><span>Attempted</span></div><div><strong>${mastered}</strong><span>Mastered tasks</span></div><div><strong>${weak}</strong><span>Weak tasks</span></div><div><strong>15</strong><span>Session length</span></div></div><div class="v26-domain-filter-box"><span>Domain filter</span><div class="v26-domain-filter-chips"><button class="${state.domainId ? "" : "active"}" type="button" data-domain-filter="">All Domains</button>${(cert.domains || []).map((domain, index) => `<button class="${state.domainId === domain.id ? "active" : ""}" type="button" data-domain-filter="${escapeHtml(domain.id)}"><i style="--domain:${DOMAIN_COLORS[index % DOMAIN_COLORS.length]}"></i>${index + 1}. ${escapeHtml(shortTitle(domain.title))}</button>`).join("")}</div></div><button class="v26-btn primary" type="button" data-start-drill>Start Session</button></section>`);
  container.querySelectorAll("[data-domain-filter]").forEach((button) => button.addEventListener("click", () => {
    state.domainId = button.dataset.domainFilter || "";
    container.querySelectorAll("[data-domain-filter]").forEach((item) => item.classList.toggle("active", item === button));
  }));
  container.querySelector("[data-start-drill]")?.addEventListener("click", () => {
    const domain = state.domainId ? `&domain_id=${encodeURIComponent(state.domainId)}` : "";
    window.location.hash = `#/practice?track_id=${encodeURIComponent(cert.id)}&mode=drill&start=1&count=15${domain}`;
  });
}

async function diagnosticSetup(container) {
  const map = await getSkillMap();
  const cert = (map.certifications || []).find((item) => item.id === state.trackId) || (map.certifications || [])[0];
  if (!cert) throw new Error("Certification is not configured");
  container.innerHTML = studyLayout(cert, "diagnostic", `<section class="v26-practice-setup"><p class="v26-kicker">Placement test</p><h1>Diagnostic Assessment</h1><p class="lede" style="margin-left:0">Identify your strongest and weakest SnowPro Core domains before deciding what to study next.</p><div class="v26-diagnostic-card"><h2>How It Works</h2><div class="v26-diagnostic-facts"><div><b>Questions</b><span>20 questions — balanced across all five exam domains</span></div><div><b>Time</b><span>About 12 minutes, no timer — work at your own pace</span></div><div><b>Difficulty</b><span>Recall, application, and scenario-analysis questions</span></div><div><b>Result</b><span>Domain evidence that helps prioritize your next study pass</span></div></div><div class="v26-diagnostic-domains"><h3>Domains Covered</h3>${(cert.domains || []).map((domain, index) => `<div><i style="--domain:${DOMAIN_COLORS[index % DOMAIN_COLORS.length]}"></i><span>${escapeHtml(domain.title)}</span><b>${Number(domain.weight || 0)}%</b></div>`).join("")}</div><div class="v26-diagnostic-expect"><strong>What to expect</strong><ul><li>No timer pressure — focus on the best answer, not speed.</li><li>Your results identify which domains need the most attention.</li><li>You can repeat the diagnostic later to measure improvement.</li></ul></div></div><button class="v26-btn primary" type="button" data-start-diagnostic>Start Diagnostic</button></section>`);
  container.querySelector("[data-start-diagnostic]")?.addEventListener("click", () => {
    window.location.hash = `#/practice?track_id=${encodeURIComponent(cert.id)}&mode=diagnostic&start=1&count=20`;
  });
}

function shortTitle(value = "") { return String(value).split(/[,&]/)[0].replace(/^Snowflake\s+/i, "").trim().slice(0, 18); }
function card(kicker, title, body, meta, href, featured = false, full = false) { return `<a class="v26-practice-card ${featured ? "featured" : ""} ${full ? "full" : ""}" href="${href}"><span>${kicker}</span><h2>${title}</h2><p>${body}</p><div><b>${meta}</b><em>Start →</em></div></a>`; }

function sourceSection(current, legacy) {
  if (!current.length && !legacy.length) return "";
  return `<section class="v26-section v26-source-practice"><div class="v26-section-heading"><p class="v26-kicker">Source Practice Exams</p><h2>Fixed imported sittings</h2></div>${current.length ? `<div class="v26-source-test-grid">${current.map((test) => sourceCard(test, false)).join("")}</div>` : `<p class="v26-empty-copy">No current COF-C03 source exams are imported.</p>`}${legacy.length ? `<details class="v26-legacy-tests"><summary>Legacy Practice · COF-C02 <span>${legacy.length}</span></summary><p>Legacy material is kept separate and does not contribute to current COF-C03 readiness.</p><div class="v26-source-test-grid">${legacy.map((test) => sourceCard(test, true)).join("")}</div></details>` : ""}</section>`;
}
function sourceCard(test, legacy) { return `<article><span>${legacy ? "Legacy" : "COF-C03"}</span><h3>${escapeHtml(test.title || "Practice Exam")}</h3><p>${test.actual_question_count || test.question_count || 0} questions</p><button type="button" data-source-test="${escapeHtml(test.id)}">Start Exam →</button></article>`; }
function bindSource(container) { container.querySelectorAll("[data-source-test]").forEach((button) => button.addEventListener("click", async () => { button.disabled = true; try { const session = await startMockSession({ track_id: state.trackId, mode: "source-exam", practice_test_id: button.dataset.sourceTest, randomize_options: true }); window.location.hash = `#/mock/session?session_id=${session.session_id}`; } catch (error) { button.disabled = false; button.textContent = error.message || "Unable to start"; } })); }

function resetSession(mode) {
  state.mode = mode;
  state.index = 0;
  state.answers = new Map();
  state.confidences = new Map();
  state.submitted = false;
  state.result = null;
}

async function launchSrs(container, params) {
  resetSession("srs");
  const limit = Number(params.count || 20);
  container.innerHTML = `<main class="v26-page"><div class="v26-loading">Preparing due reviews…</div></main>`;
  const data = await getDueToday({ track_id: state.trackId, limit });
  state.questions = (data.questions || []).map((row) => ({ ...row, id: row.question_id }));
  if (!state.questions.length) {
    container.innerHTML = `<main class="v26-page"><section class="v26-no-progress"><strong>Nothing due right now</strong><p>Your spaced-review queue is clear. New misses will appear here immediately; correct answers return when their interval matures.</p><a class="v26-btn primary" href="#/practice?track_id=${encodeURIComponent(state.trackId)}&mode=drill">Start a targeted drill</a></section></main>`;
    return;
  }
  drawSession(container);
}

async function launch(container, params) {
  const mode = params.mode || "drill";
  resetSession(mode);
  state.skillId = params.skill_id || "";
  state.domainId = params.domain_id || "";
  const count = Number(params.count || (mode === "diagnostic" ? 20 : 15));
  container.innerHTML = `<main class="v26-page"><div class="v26-loading">Preparing ${mode === "diagnostic" ? "diagnostic" : "drill"}…</div></main>`;
  const data = await startQuiz({ track_id: state.trackId, count, mode, skill_id: state.skillId || null, domain_id: state.domainId || null });
  state.questions = data.questions || [];
  if (!state.questions.length) throw new Error("No eligible questions are available for this practice session");
  drawSession(container);
}

function modeLabel() {
  if (state.mode === "diagnostic") return "Diagnostic Test";
  if (state.mode === "srs") return "Due Today";
  return "Targeted Drill";
}

function drawSession(container) {
  const q = state.questions[state.index];
  const selected = state.answers.get(q.id) || [];
  const confidence = Number(state.confidences.get(q.id) || 0);
  const answered = state.answers.size;
  container.innerHTML = `<main class="v26-practice-session"><header><a href="#/practice?track_id=${encodeURIComponent(state.trackId)}">← Practice</a><div><span>${modeLabel()}</span><strong>${answered}/${state.questions.length} answered</strong></div><button type="button" data-submit>Finish</button></header><div class="v26-practice-session-body"><aside><p>${state.mode === "srs" ? "Due" : state.mode === "diagnostic" ? "Diagnostic" : "Drill"}</p><div>${state.questions.map((item, index) => `<button class="${index === state.index ? "current" : ""} ${state.answers.has(item.id) ? "done" : ""}" data-jump="${index}">${index + 1}</button>`).join("")}</div></aside><section><p class="v26-kicker">Question ${state.index + 1} of ${state.questions.length}</p><h1>${escapeHtml(q.question)}</h1><fieldset>${(q.options || []).map((option, index) => answer(q, option, index, selected)).join("")}</fieldset><div class="v26-confidence-scale"><span>How confident are you?</span><div>${[1,2,3,4,5].map((level) => `<button type="button" class="${confidence === level ? "active" : ""}" data-confidence="${level}" aria-pressed="${confidence === level}">${level}</button>`).join("")}</div><small>1 = guessing · 5 = certain</small></div><footer><button type="button" data-prev ${state.index === 0 ? "disabled" : ""}>← Previous</button><button type="button" data-next ${state.index === state.questions.length - 1 ? "disabled" : ""}>Next →</button></footer></section></div></main>`;
  bindSession(container);
}

function answer(q, option, index, selected) { const type = q.multiple ? "checkbox" : "radio"; return `<label class="v26-practice-answer ${selected.includes(index) ? "selected" : ""}"><input type="${type}" name="practice-answer" value="${index}" ${selected.includes(index) ? "checked" : ""}/><span>${String.fromCharCode(65 + index)}</span><b>${escapeHtml(option)}</b></label>`; }
function bindSession(container) {
  container.querySelectorAll("[data-jump]").forEach((button) => button.addEventListener("click", () => { capture(container); state.index = Number(button.dataset.jump); drawSession(container); }));
  container.querySelectorAll("input[name='practice-answer']").forEach((input) => input.addEventListener("change", () => { capture(container); drawSession(container); }));
  container.querySelectorAll("[data-confidence]").forEach((button) => button.addEventListener("click", () => { state.confidences.set(state.questions[state.index].id, Number(button.dataset.confidence)); drawSession(container); }));
  container.querySelector("[data-prev]")?.addEventListener("click", () => { capture(container); state.index = Math.max(0, state.index - 1); drawSession(container); });
  container.querySelector("[data-next]")?.addEventListener("click", () => { capture(container); state.index = Math.min(state.questions.length - 1, state.index + 1); drawSession(container); });
  container.querySelector("[data-submit]")?.addEventListener("click", () => submit(container));
}
function capture(container) { const q = state.questions[state.index]; let selected = [...container.querySelectorAll("input[name='practice-answer']:checked")].map((input) => Number(input.value)); if (!q.multiple && selected.length > 1) selected = selected.slice(-1); selected.length ? state.answers.set(q.id, selected) : state.answers.delete(q.id); }

async function submit(container) {
  if (state.submitted) return;
  capture(container);
  state.submitted = true;
  const payload = state.questions.map((q) => ({ question_id: q.id, selected: state.answers.get(q.id) || [] }));
  const result = await gradeQuiz({ answers: payload });
  state.result = result;
  for (const row of result.results || []) {
    await recordAttempt(row.id || row.question_id, {
      selected: row.selected || [],
      correct: Boolean(row.is_correct),
      mode: state.mode,
      confidence: state.confidences.get(row.id || row.question_id) || null,
    }).catch(() => {});
  }
  renderResult(container, result);
}

function renderResult(container, result) {
  const total = Math.max(1, result.total || state.questions.length);
  const score = result.score || 0;
  const percent = Math.round(score / total * 100);
  const kicker = state.mode === "srs" ? "Spaced Review Result" : state.mode === "diagnostic" ? "Diagnostic Result" : "Drill Result";
  const continueHref = state.mode === "srs"
    ? `#/practice?track_id=${encodeURIComponent(state.trackId)}&mode=srs&refresh=${Date.now()}`
    : `#/practice?track_id=${encodeURIComponent(state.trackId)}&mode=${encodeURIComponent(state.mode)}`;
  container.innerHTML = `<main class="v26-page v26-practice-result"><a class="v26-back" href="#/practice?track_id=${encodeURIComponent(state.trackId)}">← Practice</a><header class="v26-page-intro centered"><p class="v26-kicker">${kicker}</p><h1>${percent}%</h1><p>${score}/${total} correct. Your answer history now updates the spaced-review queue, mistake notebook, and confidence calibration.</p></header><section class="v26-review-list">${(result.results || []).map((row, index) => review(row, index)).join("")}</section><div class="v26-result-actions"><a class="v26-btn primary" href="#/progress?track_id=${encodeURIComponent(state.trackId)}">Open Progress</a><a class="v26-btn secondary" href="${continueHref}">Continue</a></div></main>`;
}
function review(row, index) { const options = row.options || []; const selected = (row.selected || []).map((i) => options[i]).filter(Boolean).join("; ") || "No answer"; const correct = (row.correct || []).map((i) => options[i]).filter(Boolean).join("; ") || "Answer unavailable"; return `<details class="v26-review-card ${row.is_correct ? "correct" : "incorrect"}"><summary><span>${row.is_correct ? "✓" : "×"}</span><div><small>Question ${index + 1}</small><strong>${escapeHtml(row.question || "")}</strong></div></summary><div class="v26-review-body"><p><b>Your answer</b>${escapeHtml(selected)}</p><p><b>Correct answer</b>${escapeHtml(correct)}</p>${row.explanation ? `<p><b>Explanation</b>${escapeHtml(row.explanation)}</p>` : ""}</div></details>`; }
