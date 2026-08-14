export const VIEW_ID = "v26-mock-landing";
import { getActiveMockSession, getMockConfig } from "../api.js";
import { activeTrack } from "../ui.js";

export default async function mount(container) {
  const trackId = activeTrack();
  const config = await getMockConfig({ track_id: trackId });
  const active = await getActiveMockSession({ track_id: trackId }).catch(() => ({ session: null }));
  const full = config.full_mock || {};
  const session = active.session;
  container.innerHTML = `<main class="v26-page v26-mock-landing"><section class="v26-mock-center"><p class="v26-kicker">SnowPro Core · ${config.exam_code || "COF-C03"}</p><h1>Mock Exam</h1><p>Test your readiness under timed conditions using the current SnowPro Core blueprint.</p><div class="v26-mock-facts"><div><strong>${(config.domains || []).length || 5}</strong><span>Domains</span></div><div><strong>${full.question_count || 100}</strong><span>Questions</span></div><div><strong>${full.time_limit_minutes || 120}</strong><span>Minutes</span></div><div><strong>${config.pass_scaled_score || 750}</strong><span>Practice threshold</span></div></div>${session ? `<div class="v26-interrupted"><span>Interrupted sitting found</span><strong>Resume your active mock</strong><p>Your saved sitting and timer are still active.</p><a class="v26-btn primary" href="#/mock/session?session_id=${session.session_id}">Resume exam</a></div>` : `<a class="v26-btn primary v26-start-mock" href="#/mock/start?type=full-mock">Start Mock Exam</a>`}<p class="v26-mock-note">Practice scoring is a study readiness estimate.</p><p class="v26-mock-alt">Not sure you're ready? <a href="#/practice">Start with practice →</a></p></section></main>`;
}
