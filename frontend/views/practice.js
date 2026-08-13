export const VIEW_ID = "v26-practice";

import { getMockConfig } from "../api.js";
import { activeTrack } from "../ui.js";

export default async function mount(container) {
  const trackId = activeTrack();
  const config = await getMockConfig({ track_id: trackId }).catch(() => ({ quick_mock: { question_count: 30, time_limit_minutes: 45 }, full_mock: { question_count: 100, time_limit_minutes: 120 } }));
  const quick = config.quick_mock || {};
  const full = config.full_mock || {};
  container.innerHTML = `<main class="v26-page v26-practice-page"><section class="v26-page-intro centered"><p class="v26-kicker">SnowPro Core · COF-C03</p><h1>Practice</h1><p>Choose the kind of evidence you need right now: find gaps, repair a weak task, or rehearse the timed exam experience.</p></section><section class="v26-section"><div class="v26-practice-grid">${card("Diagnostic", "Find weak areas", "A balanced untimed baseline across the current exam blueprint.", "25 questions", `#/quiz?track_id=${trackId}&mode=diagnostic&count=25`, true)}${card("Targeted Drill", "Repair weak tasks", "Short focused practice prioritizing the task or domain you need to reinforce.", "15 questions", `#/quiz?track_id=${trackId}&mode=drill&count=15`)}${card("Quick Mock", "Timed readiness check", "A shorter mock using the same persisted exam player as the full sitting.", `${quick.question_count || 30} questions · ${quick.time_limit_minutes || 45} min`, `#/mock/start?track_id=${trackId}&type=quick-mock`)}${card("Full Mock", "Complete simulation", "The full Snowflake Brain certification simulation with flags, autosave, resume, and results.", `${full.question_count || 100} questions · ${full.time_limit_minutes || 120} min`, `#/mock/start?track_id=${trackId}&type=full-mock`, false, true)}</div></section><section class="v26-section v26-practice-note"><div><p class="v26-kicker">Need exam conditions?</p><h2>Use the dedicated mock player.</h2><p>Timed sittings hide explanations until submission, preserve your answers and flags, and keep the server-based deadline running through refreshes.</p></div><a class="v26-btn primary" href="#/mock?track_id=${trackId}">Open Mock Exam</a></section></main>`;
}

function card(kicker, title, body, meta, href, featured = false, full = false) {
  return `<a class="v26-practice-card ${featured ? "featured" : ""} ${full ? "full" : ""}" href="${href}"><span>${kicker}</span><h2>${title}</h2><p>${body}</p><div><b>${meta}</b><em>Start →</em></div></a>`;
}
