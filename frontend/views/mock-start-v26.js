export const VIEW_ID = "v26-mock-start";

import { cancelMockSession, getActiveMockSession, getMockConfig, startMockSession } from "../api.js";
import { activeTrack } from "../ui.js";
import { candidate, refreshCandidate } from "../auth.js";

export default async function mount(container, params = {}) {
  const trackId = params.track_id || activeTrack();
  await refreshCandidate().catch(() => {});
  const account = candidate();
  if (!account) {
    container.innerHTML = `<main class="v26-page v26-sitting-page"><a class="v26-back" href="#/mock?track_id=${encodeURIComponent(trackId)}">← Mock Exam</a><section class="v26-route-gate"><p class="v26-kicker">Candidate access</p><h1>Sign in to start a timed mock</h1><p>Free membership includes one 20-question timed mock each week.</p><button class="v26-btn primary" type="button" data-auth-intent="login">Sign In</button><button class="v26-btn secondary" type="button" data-auth-intent="signup">Create Free Account</button></section></main>`;
    return;
  }
  const [config, active] = await Promise.all([getMockConfig({ track_id: trackId }), getActiveMockSession({ track_id: trackId }).catch(() => ({ session: null }))]);
  const planCode = account.plan_code || "free";
  const quick = config.quick_mock || {};
  const full = config.full_mock || {};
  const choices = planChoices(planCode, account, quick, full);
  let selected = choices.some((item) => item.mode === params.type && !item.disabled) ? params.type : choices.find((item) => !item.disabled)?.mode;
  container.innerHTML = `<main class="v26-page v26-sitting-page"><a class="v26-back" href="#/mock?track_id=${encodeURIComponent(trackId)}">← Mock Exam</a><header class="v26-mock-start-head"><p class="v26-kicker">SnowPro Core · COF-C03 · ${escape(account.plan)}</p><h1>Choose Your Timed Mock</h1><p>Your plan limits are enforced by the server and reset on the calendar shown on Membership.</p></header>${active.session ? interrupted(active.session, planCode) : ""}<section class="v26-sitting-section"><h2>Available Sittings</h2><div class="v26-sitting-choice">${choices.map(choice).join("")}</div></section><section class="v26-exam-info"><div><p class="v26-kicker">Exam Format</p><dl data-format></dl></div><div><p class="v26-kicker">Domain Weights</p><div class="v26-weight-list">${(config.domains || []).map((domain, index) => `<div><i data-domain="${index + 1}"></i><span>${escape(domain.title)}</span><strong>${domain.weight}%</strong></div>`).join("")}</div></div></section><section class="v26-before-start"><p class="v26-kicker">Before You Start</p><ul><li>The timer cannot be paused.</li><li>Answers and review flags save automatically.</li><li>Refreshing resumes the same sitting and deadline.</li><li>You must complete an active sitting before starting another.</li><li>Explanations appear only after submission.</li><li>The sitting submits automatically when time expires.</li></ul></section><button class="v26-start-wide" type="button" data-start ${selected ? "" : "disabled"}></button><p class="v26-scoring-note">${escape(config.scoring_note || "Practice scoring is a study readiness estimate.")}</p></main>`;
  const update = () => {
    container.querySelectorAll("[data-sitting]").forEach((node) => node.classList.toggle("selected", node.dataset.sitting === selected));
    const item = choices.find((entry) => entry.mode === selected);
    container.querySelector("[data-format]").innerHTML = item ? `<div><dt>Questions</dt><dd>${item.questions}</dd></div><div><dt>Time limit</dt><dd>${item.minutes} minutes</dd></div><div><dt>Question types</dt><dd>Single and multi-select</dd></div><div><dt>Allowance</dt><dd>${escape(item.allowance)}</dd></div>` : `<div><dt>Availability</dt><dd>No sitting is currently available</dd></div>`;
    const start = container.querySelector("[data-start]");
    start.textContent = item ? `Start ${item.title}` : "No Mock Available";
    start.disabled = !item || Boolean(active.session);
    container.querySelector(`[data-sitting='${selected}'] input`)?.setAttribute("checked", "checked");
  };
  container.querySelectorAll("[data-sitting]").forEach((node) => node.addEventListener("click", () => { if (node.dataset.disabled !== "true") { selected = node.dataset.sitting; update(); } }));
  container.querySelector("[data-discard]")?.addEventListener("click", async (event) => {
    event.currentTarget.disabled = true;
    event.currentTarget.textContent = "Discarding…";
    try { await cancelMockSession(active.session.session_id); container.querySelector("[data-interrupted]")?.remove(); container.querySelector("[data-start]").disabled = false; }
    catch (error) { event.currentTarget.disabled = false; event.currentTarget.textContent = error.message || "Unable to discard"; }
  });
  container.querySelector("[data-start]").addEventListener("click", async (event) => {
    event.currentTarget.disabled = true;
    try { const session = await startMockSession({ track_id: trackId, mode: selected }); window.location.hash = `#/mock/session?session_id=${session.session_id}`; }
    catch (error) { event.currentTarget.disabled = false; event.currentTarget.textContent = error.message || "Unable to start"; }
  });
  update();
}

function planChoices(planCode, account, quick, full) {
  const usage = account.membership?.usage || {};
  if (planCode === "free") {
    const remaining = usage.weekly_mocks?.remaining || 0;
    return [{ mode: "weekly-mock", title: "Weekly Mock", questions: 20, minutes: 30, allowance: remaining ? "1 weekly start available" : "Weekly start already used", disabled: !remaining, copy: "Your Free weekly timed check. Once started, it cannot be discarded." }];
  }
  if (planCode === "exam_pack_35") {
    const fullRemaining = usage.monthly_full_exams?.remaining || 0;
    return [
      { mode: "lifetime-practice", title: "100-Question Practice Mock", questions: full.question_count || 100, minutes: full.time_limit_minutes || 120, allowance: "Lifetime access", copy: "Repeat this practice mock whenever you need it." },
      { mode: "full-mock", title: "Included Full Exam", questions: full.question_count || 100, minutes: full.time_limit_minutes || 120, allowance: fullRemaining ? "1 attempt available within 30 days" : "Attempt used or window expired", disabled: !fullRemaining, copy: "Starting this sitting uses the one included Full Exam attempt." },
    ];
  }
  const daily = usage.daily_questions || {};
  const monthly = usage.monthly_full_exams || {};
  return [
    { mode: "quick-mock", title: "Quick Mock", questions: quick.question_count || 30, minutes: quick.time_limit_minutes || 45, allowance: `${daily.remaining ?? 0} daily questions remaining`, disabled: (daily.remaining ?? 0) < (quick.question_count || 30), copy: "A focused timed readiness check using your daily question allowance." },
    { mode: "full-mock", title: "Full-Length Mock", questions: full.question_count || 100, minutes: full.time_limit_minutes || 120, allowance: monthly.limit == null ? "Unlimited monthly starts" : `${monthly.remaining ?? 0} monthly starts remaining`, disabled: monthly.remaining === 0, copy: "The complete certification simulation using your monthly full-exam allowance." },
  ];
}

function choice(item) { return `<label data-sitting="${item.mode}" data-disabled="${Boolean(item.disabled)}" class="${item.disabled ? "disabled" : ""}"><input type="radio" name="sitting" value="${item.mode}" ${item.disabled ? "disabled" : ""}/><span>${escape(item.title)}</span><strong>${item.questions} questions</strong><em>${item.minutes} minutes</em><p>${escape(item.copy)} ${escape(item.allowance)}</p></label>`; }
function interrupted(session, planCode) { const discard = planCode === "free" ? `<span class="v26-plan-current">Free weekly mocks cannot be discarded</span>` : `<button class="v26-btn secondary" type="button" data-discard>Discard Sitting</button>`; return `<section class="v26-interrupted-sitting" data-interrupted><span>Active Sitting Found</span><strong>Resume your active mock</strong><p>${minutes(session.remaining_seconds)} remaining. Saved answers, flags, question order, and the deadline are still active.</p><div class="v26-interrupted-actions">${discard}<a class="v26-btn primary" href="#/mock/session?session_id=${session.session_id}">Resume Exam</a></div></section>`; }
function minutes(seconds) { const value = Math.max(0, Number(seconds || 0)); const h = Math.floor(value / 3600); const m = Math.floor((value % 3600) / 60); return h ? `${h}h ${m}m` : `${m} min`; }
function escape(value) { const node = document.createElement("span"); node.textContent = String(value ?? ""); return node.innerHTML; }
