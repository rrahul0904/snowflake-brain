export const VIEW_ID = "v26-mock-start";

import { cancelMockSession, getActiveMockSession, getMockConfig, startMockSession } from "../api.js";
import { activeTrack } from "../ui.js";

export default async function mount(container, params = {}) {
  const trackId = params.track_id || activeTrack();
  const [config, active] = await Promise.all([getMockConfig({ track_id: trackId }), getActiveMockSession({ track_id: trackId }).catch(() => ({ session: null }))]);
  let selected = params.type === "quick-mock" ? "quick-mock" : "full-mock";
  const quick = config.quick_mock || {};
  const full = config.full_mock || {};
  container.innerHTML = `<main class="v26-page v26-sitting-page"><a class="v26-back" href="#/mock?track_id=${encodeURIComponent(trackId)}">← Mock Exam</a><header class="v26-mock-start-head"><p class="v26-kicker">SnowPro Core · COF-C03</p><h1>Mock Exam</h1><p>Simulate the SnowPro Core exam experience with a shorter readiness check or the full Snowflake Brain sitting.</p></header>${active.session ? `<section class="v26-interrupted-sitting" data-interrupted><span>Interrupted Sitting Found</span><strong>Resume your active mock</strong><p>${minutes(active.session.remaining_seconds)} remaining. Saved answers, flags, question order, and the deadline are still active.</p><div class="v26-interrupted-actions"><button class="v26-btn secondary" type="button" data-discard>Discard Sitting</button><a class="v26-btn primary" href="#/mock/session?session_id=${active.session.session_id}">Resume Exam</a></div></section>` : ""}<section class="v26-sitting-section"><h2>Choose Your Sitting</h2><div class="v26-sitting-choice"><label data-sitting="quick-mock"><input type="radio" name="sitting" value="quick-mock"/><span>Quick Mock</span><strong>${quick.question_count || 30} questions</strong><em>${quick.time_limit_minutes || 45} minutes</em><p>A focused timed readiness check between study sessions.</p></label><label data-sitting="full-mock"><input type="radio" name="sitting" value="full-mock"/><span>Full-Length Mock</span><strong>${full.question_count || 100} questions</strong><em>${full.time_limit_minutes || 120} minutes</em><p>The complete Snowflake Brain certification simulation.</p></label></div></section><section class="v26-exam-info"><div><p class="v26-kicker">Exam Format</p><dl data-format></dl></div><div><p class="v26-kicker">Domain Weights</p><div class="v26-weight-list">${(config.domains || []).map((domain, index) => `<div><i data-domain="${index + 1}"></i><span>${domain.title}</span><strong>${domain.weight}%</strong></div>`).join("")}</div></div></section><section class="v26-before-start"><p class="v26-kicker">Before You Start</p><ul><li>The timer cannot be paused.</li><li>Answers and review flags save automatically.</li><li>You can navigate freely between questions.</li><li>Refreshing resumes the same sitting and deadline.</li><li>Explanations appear only after submission.</li><li>The sitting submits automatically when time expires.</li></ul></section><button class="v26-start-wide" type="button" data-start></button><p class="v26-scoring-note">${config.scoring_note || "Practice scoring is a study readiness estimate."}</p></main>`;
  const update = () => {
    container.querySelectorAll("[data-sitting]").forEach((node) => node.classList.toggle("selected", node.dataset.sitting === selected));
    const setting = selected === "quick-mock" ? quick : full;
    container.querySelector("[data-format]").innerHTML = `<div><dt>Questions</dt><dd>${setting.question_count}</dd></div><div><dt>Time limit</dt><dd>${setting.time_limit_minutes} minutes</dd></div><div><dt>Question types</dt><dd>Single and multi-select</dd></div><div><dt>Practice threshold</dt><dd>${config.pass_scaled_score} / ${config.score_scale}</dd></div>`;
    container.querySelector("[data-start]").textContent = selected === "quick-mock" ? "Start Quick Mock" : "Start Full-Length Mock";
    container.querySelector(`[data-sitting='${selected}'] input`).checked = true;
  };
  container.querySelectorAll("[data-sitting]").forEach((node) => node.addEventListener("click", () => { selected = node.dataset.sitting; update(); }));
  container.querySelector("[data-discard]")?.addEventListener("click", async (event) => {
    event.currentTarget.disabled = true;
    event.currentTarget.textContent = "Discarding…";
    try {
      await cancelMockSession(active.session.session_id);
      container.querySelector("[data-interrupted]")?.remove();
    } catch (error) {
      event.currentTarget.disabled = false;
      event.currentTarget.textContent = error.message || "Unable to discard";
    }
  });
  container.querySelector("[data-start]").addEventListener("click", async (event) => {
    event.currentTarget.disabled = true;
    try { const session = await startMockSession({ track_id: trackId, mode: selected }); window.location.hash = `#/mock/session?session_id=${session.session_id}`; }
    catch (error) { event.currentTarget.disabled = false; event.currentTarget.textContent = error.message || "Unable to start"; }
  });
  update();
}

function minutes(seconds) { const value = Math.max(0, Number(seconds || 0)); const h = Math.floor(value / 3600); const m = Math.floor((value % 3600) / 60); return h ? `${h}h ${m}m` : `${m} min`; }
