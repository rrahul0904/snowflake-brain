export const VIEW_ID = "v26-mock-landing";
import { getActiveMockSession, getMockConfig } from "../api.js";
import { activeTrack } from "../ui.js";
import { candidate, refreshCandidate } from "../auth.js";

export default async function mount(container) {
  const trackId = activeTrack();
  await refreshCandidate().catch(() => {});
  const account = candidate();
  const config = await getMockConfig({ track_id: trackId });
  const active = account ? await getActiveMockSession({ track_id: trackId }).catch(() => ({ session: null })) : { session: null };
  const full = config.full_mock || {};
  const session = active.session;
  container.innerHTML = `<main class="v26-page v26-mock-landing"><section class="v26-mock-center"><p class="v26-kicker">SnowPro Core · ${config.exam_code || "COF-C03"}</p><h1>Mock Exam</h1><p>Test your readiness under timed conditions using the current SnowPro Core blueprint.</p><div class="v26-mock-facts"><div><strong>${(config.domains || []).length || 5}</strong><span>Domains</span></div><div><strong>${full.question_count || 100}</strong><span>Full exam questions</span></div><div><strong>${full.time_limit_minutes || 120}</strong><span>Minutes</span></div><div><strong>${config.pass_scaled_score || 750}</strong><span>Practice threshold</span></div></div>${action(account, session, trackId)}<p class="v26-mock-note">Practice scoring is a study readiness estimate.</p><p class="v26-mock-alt">Need more access? <a href="#/membership">Compare memberships →</a></p></section></main>`;
}

function action(account, session, trackId) {
  if (!account) return `<div class="v26-mock-gate"><span>Candidate access</span><strong>Sign in to take a mock</strong><p>Free includes daily practice and one non-cancellable 20-question timed mock every week.</p><button class="v26-btn primary" type="button" data-auth-intent="login">Sign In</button><button class="v26-btn secondary" type="button" data-auth-intent="signup">Create Free Account</button></div>`;
  if (session) return `<div class="v26-interrupted"><span>Active sitting found</span><strong>Resume your timed mock</strong><p>Your saved sitting and timer remain active. Complete it before starting another.</p><a class="v26-btn primary" href="#/mock/session?session_id=${session.session_id}">Resume exam</a></div>`;
  const plan = account.plan_code || "free";
  const usage = account.membership?.usage || {};
  if (plan === "free") {
    const weekly = usage.weekly_mocks || {};
    return weekly.remaining > 0 ? `<div class="v26-mock-gate"><span>Free weekly mock</span><strong>1 timed 20-question mock available</strong><p>Once started, this sitting cannot be discarded and must be completed. The allowance resets Monday at 00:00 UTC.</p><a class="v26-btn primary" href="#/mock/start?track_id=${encodeURIComponent(trackId)}&type=weekly-mock">Start Weekly Mock</a></div>` : `<div class="v26-mock-gate"><span>Weekly allowance used</span><strong>Your next Free mock resets Monday</strong><p>Continue studying and use your daily question allowance, or choose a paid plan for more timed exam access.</p><a class="v26-btn primary" href="#/membership">Compare Plans</a></div>`;
  }
  if (plan === "exam_pack_35") {
    const fullExam = usage.monthly_full_exams || {};
    return `<div class="v26-mock-gate"><span>One-Time Exam Pack</span><strong>Lifetime Practice Mock access</strong><p>Your 100-question Practice Mock remains available for life. ${fullExam.remaining ? "One Full Exam attempt is also available within its 30-day window." : "The included Full Exam is no longer available."}</p><a class="v26-btn primary" href="#/mock/start?track_id=${encodeURIComponent(trackId)}&type=lifetime-practice">Open Exam Pack</a></div>`;
  }
  const monthly = usage.monthly_full_exams || {};
  const allowance = monthly.limit == null ? "Unlimited full exams this month" : `${monthly.remaining} of ${monthly.limit} full exams remaining this month`;
  return `<div class="v26-mock-gate"><span>${account.plan}</span><strong>${allowance}</strong><p>Quick Mock questions use your daily allowance. Full timed exams use your monthly allowance.</p><a class="v26-btn primary v26-start-mock" href="#/mock/start?track_id=${encodeURIComponent(trackId)}&type=full-mock">Choose a Mock</a></div>`;
}
