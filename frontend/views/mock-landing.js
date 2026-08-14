export const VIEW_ID = "v26-mock-landing";
import { getActiveMockSession, getMockConfig } from "../api.js";
import { activeTrack } from "../ui.js";
import { candidate, refreshCandidate } from "../auth.js";

export default async function mount(container) {
  const trackId = activeTrack();
  await refreshCandidate().catch(() => {});
  const account = candidate();
  if (!account) throw new Error("Candidate session required");
  const config = await getMockConfig({ track_id: trackId });
  const active = await getActiveMockSession({ track_id: trackId }).catch(() => ({ session: null }));
  const quick = config.quick_mock || {};
  const full = config.full_mock || {};
  container.innerHTML = `<main class="v26-page v26-mock-landing"><section class="v26-mock-center"><p class="v26-kicker">Technical certification</p><h1>Mock Exam</h1><p>Rehearse the SnowPro Core blueprint under timed conditions. Choose a shorter readiness sitting or the full practice simulation supported by your membership.</p><div class="v26-mock-facts"><div><strong>${(config.domains || []).length || 5}</strong><span>Domains</span></div><div><strong>${quick.question_count || 30}/${full.question_count || 100}</strong><span>Questions</span></div><div><strong>${quick.time_limit_minutes || 45}/${full.time_limit_minutes || 120}</strong><span>Minutes</span></div><div><strong>${config.pass_scaled_score || 750}</strong><span>Practice threshold</span></div></div>${action(account, active.session, trackId)}<p class="v26-mock-note">Practice scoring is a preparation estimate, not Snowflake's live exam scoring formula.</p><p class="v26-mock-alt">Not sure where to start? <a href="#/practice?track_id=${encodeURIComponent(trackId)}&mode=diagnostic">Take the diagnostic first.</a></p></section></main>`;
}

function action(account, session, trackId) {
  if (session) return `<p class="v26-mock-resume-note">An active timed sitting is already saved.</p><a class="v26-btn primary v26-start-mock" href="#/mock/session?session_id=${session.session_id}">Resume Mock Exam</a>`;
  const plan = account.plan_code || "free";
  const usage = account.membership?.usage || {};
  if (plan === "free") {
    const weekly = usage.weekly_mocks || {};
    return weekly.remaining > 0 ? `<a class="v26-btn primary v26-start-mock" href="#/mock/start?track_id=${encodeURIComponent(trackId)}&type=weekly-mock">Start Weekly Mock</a><p class="v26-mock-access-note">Free includes one non-cancellable 20-question timed mock each week.</p>` : `<a class="v26-btn primary v26-start-mock" href="#/membership">Compare Mock Access</a><p class="v26-mock-access-note">Your Free weekly mock has already been used for this reset period.</p>`;
  }
  if (plan === "exam_pack_35") return `<a class="v26-btn primary v26-start-mock" href="#/mock/start?track_id=${encodeURIComponent(trackId)}&type=lifetime-practice">Start Mock Exam</a><p class="v26-mock-access-note">Your Exam Pack includes lifetime Practice Mock access.</p>`;
  return `<a class="v26-btn primary v26-start-mock" href="#/mock/start?track_id=${encodeURIComponent(trackId)}&type=full-mock">Start Mock Exam</a>`;
}
