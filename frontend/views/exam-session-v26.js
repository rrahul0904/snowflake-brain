export const VIEW_ID = "v26-exam-session";

import { getMockConfig, getMockSession, saveMockAnswer, saveMockFlag, submitMockSession } from "../api.js";

const state = { session: null, config: null, index: 0, filter: "all", timer: null, loadedAt: 0, remaining: 0, saving: false };

export function unmount() { if (state.timer) clearInterval(state.timer); state.timer = null; document.body.classList.remove("v26-exam-active", "v26-exam-nav-open"); }

export default async function mount(container, params = {}) {
  unmount();
  const sessionId = Number(params.session_id || 0);
  if (!sessionId) throw new Error("A mock session is required");
  const session = await getMockSession(sessionId);
  if (session.status !== "in_progress") { window.location.hash = `#/mock/result?session_id=${sessionId}`; return; }
  const config = await getMockConfig({ track_id: session.track_id });
  state.session = session;
  state.config = config;
  state.loadedAt = Date.now();
  state.remaining = Number(session.remaining_seconds || 0);
  state.index = 0;
  state.filter = "all";
  document.body.classList.add("v26-exam-active");
  draw(container);
  startTimer(container);
  window.addEventListener("keydown", keyboard);
}

function keyboard(event) {
  if (!state.session || event.target?.matches?.("input,textarea,select,button")) return;
  if (event.key === "ArrowRight") { state.index = Math.min(state.session.questions.length - 1, state.index + 1); draw(document.querySelector("#view-root")); }
  if (event.key === "ArrowLeft") { state.index = Math.max(0, state.index - 1); draw(document.querySelector("#view-root")); }
}

function draw(container) {
  const session = state.session;
  const questions = session.questions || [];
  const q = questions[state.index];
  if (!q) throw new Error("This sitting has no questions");
  const answered = questions.filter((item) => item.selected?.length).length;
  const flagged = questions.filter((item) => item.flagged).length;
  const domainMap = new Map((state.config.domains || []).map((d, i) => [d.id, { ...d, index: i }]));
  const domain = domainMap.get(q.domain_id) || { title: "Exam objective", index: 0 };
  const parts = String(q.question || "").split(/\n\s*\n/).filter(Boolean);
  const context = parts.length > 1 ? parts.slice(0, -1).join("\n\n") : "";
  const stem = parts.length > 1 ? parts.at(-1) : q.question;
  container.innerHTML = `<main class="v26-exam-shell"><header class="v26-exam-top"><div><span>SnowPro Core · COF-C03</span><strong>${modeName(session.mode)}</strong></div><div class="v26-exam-status"><span data-save-state>${state.saving ? "Saving…" : "Saved"}</span><strong data-timer>${clock(remaining())}</strong></div><button type="button" data-submit>Submit Exam</button></header><div class="v26-exam-body"><aside class="v26-exam-nav"><div class="v26-exam-nav-head"><div><span>Exam Navigator</span><strong>${questions.length - answered} remaining</strong></div><button type="button" data-close-nav aria-label="Close exam navigator">×</button></div><div class="v26-nav-filters">${filter("all", "Overview", questions.length)}${filter("flagged", "Flagged", flagged)}${(state.config.domains || []).map((d, i) => domainFilter(d, i)).join("")}</div><div class="v26-question-grid">${filteredQuestions().map((item) => questionButton(item, questions.indexOf(item))).join("") || `<p>No questions in this view.</p>`}</div><div class="v26-exam-legend"><span><i class="done"></i>Answered</span><span><i class="flag"></i>Flagged</span></div><button class="v26-submit-side" type="button" data-submit>Submit Exam</button></aside><section class="v26-question-pane"><button class="v26-open-nav" type="button" data-open-nav>Exam Navigator</button><div class="v26-question-meta"><div><span>Question ${String(q.position).padStart(2, "0")} of ${questions.length}</span><strong><i style="--domain:${domainColor(domain.index)}"></i>${escape(domain.title)}${q.skill_id && q.skill_id !== "unmapped" ? ` · ${escape(q.skill_id.replaceAll("-", " "))}` : ""}</strong></div><button class="v26-flag-btn ${q.flagged ? "active" : ""}" type="button" data-flag>${q.flagged ? "⚑ Flagged" : "⚐ Flag"}</button></div><article class="v26-question-card"><div class="v26-question-watermark">${String(q.position).padStart(3, "0")}</div><p class="v26-question-kind">${q.multiple ? "Select all that apply." : "Select one answer."}</p>${context ? `<div class="v26-question-context"><span>Scenario</span><p>${escape(context)}</p></div>` : ""}<h1>${escape(stem)}</h1><fieldset>${(q.options || []).map((option, index) => answer(q, option, index)).join("")}</fieldset></article><footer class="v26-exam-footer"><button type="button" data-prev ${state.index === 0 ? "disabled" : ""}>← Previous</button><div class="v26-progress-dots">${questions.map((item, index) => `<button type="button" class="${index === state.index ? "current" : ""} ${item.selected?.length ? "done" : ""} ${item.flagged ? "flagged" : ""}" data-jump="${index}" aria-label="Question ${index + 1}"></button>`).join("")}</div><button type="button" data-next ${state.index === questions.length - 1 ? "disabled" : ""}>Next →</button></footer></section></div><dialog class="v26-submit-dialog" data-dialog><div><p class="v26-kicker">Finish sitting</p><h2>Submit exam?</h2><div class="v26-submit-stats"><span><strong>${answered}</strong>Answered</span><span><strong>${questions.length - answered}</strong>Unanswered</span><span><strong>${flagged}</strong>Flagged</span></div><p>${questions.length - answered ? "Unanswered questions will be scored as incorrect." : "You answered every question."}</p><footer><button type="button" data-cancel>Continue Exam</button><button type="button" class="primary" data-confirm>Submit Exam</button></footer></div></dialog></main>`;
  bind(container);
}

function bind(container) {
  container.querySelectorAll("[data-filter]").forEach((button) => button.addEventListener("click", () => { state.filter = button.dataset.filter; draw(container); }));
  container.querySelectorAll("[data-jump]").forEach((button) => button.addEventListener("click", () => { state.index = Number(button.dataset.jump); draw(container); }));
  container.querySelectorAll("[data-question-index]").forEach((button) => button.addEventListener("click", () => { state.index = Number(button.dataset.questionIndex); draw(container); }));
  container.querySelectorAll("input[name='answer']").forEach((input) => input.addEventListener("change", () => saveAnswer(container)));
  container.querySelector("[data-prev]")?.addEventListener("click", () => { state.index = Math.max(0, state.index - 1); draw(container); });
  container.querySelector("[data-next]")?.addEventListener("click", () => { state.index = Math.min(state.session.questions.length - 1, state.index + 1); draw(container); });
  container.querySelector("[data-flag]")?.addEventListener("click", () => toggleFlag(container));
  container.querySelectorAll("[data-submit]").forEach((button) => button.addEventListener("click", () => container.querySelector("[data-dialog]")?.showModal()));
  container.querySelector("[data-cancel]")?.addEventListener("click", () => container.querySelector("[data-dialog]")?.close());
  container.querySelector("[data-confirm]")?.addEventListener("click", () => finish(container, "learner"));
  container.querySelector("[data-open-nav]")?.addEventListener("click", () => document.body.classList.add("v26-exam-nav-open"));
  container.querySelector("[data-close-nav]")?.addEventListener("click", () => document.body.classList.remove("v26-exam-nav-open"));
}

async function saveAnswer(container) {
  const q = state.session.questions[state.index];
  let selected = [...container.querySelectorAll("input[name='answer']:checked")].map((input) => Number(input.value));
  if (!q.multiple && selected.length > 1) selected = selected.slice(-1);
  q.selected = selected;
  state.saving = true;
  container.querySelector("[data-save-state]").textContent = "Saving…";
  try { await saveMockAnswer(state.session.session_id, q.id, selected); container.querySelector("[data-save-state]").textContent = "Saved"; }
  catch { container.querySelector("[data-save-state]").textContent = "Retrying…"; setTimeout(() => saveMockAnswer(state.session.session_id, q.id, selected).catch(() => {}), 1200); }
  finally { state.saving = false; }
  draw(container);
}

async function toggleFlag(container) {
  const q = state.session.questions[state.index];
  q.flagged = !q.flagged;
  await saveMockFlag(state.session.session_id, q.id, q.flagged).catch(() => { q.flagged = !q.flagged; });
  draw(container);
}

function startTimer(container) {
  state.timer = setInterval(() => {
    const node = container.querySelector("[data-timer]");
    if (node) node.textContent = clock(remaining());
    if (remaining() <= 0) finish(container, "timer");
  }, 1000);
}

function remaining() { return Math.max(0, state.remaining - Math.floor((Date.now() - state.loadedAt) / 1000)); }
async function finish(container, reason) { if (state.timer) clearInterval(state.timer); const button = container.querySelector("[data-confirm]"); if (button) { button.disabled = true; button.textContent = "Submitting…"; } const result = await submitMockSession(state.session.session_id, reason); window.location.hash = `#/mock/result?session_id=${result.session_id || state.session.session_id}`; }
function filteredQuestions() { if (state.filter === "flagged") return state.session.questions.filter((q) => q.flagged); if (state.filter.startsWith("domain:")) return state.session.questions.filter((q) => q.domain_id === state.filter.slice(7)); return state.session.questions; }
function filter(value, label, count) { return `<button class="${state.filter === value ? "active" : ""}" type="button" data-filter="${value}"><span>${label}</span><b>${count}</b></button>`; }
function domainFilter(domain, index) { const count = state.session.questions.filter((q) => q.domain_id === domain.id).length; return `<button class="${state.filter === `domain:${domain.id}` ? "active" : ""}" type="button" data-filter="domain:${domain.id}"><i style="--domain:${domainColor(index)}"></i><span>${domain.title}</span><b>${count}</b></button>`; }
function questionButton(q, index) { return `<button class="${index === state.index ? "current" : ""} ${q.selected?.length ? "done" : ""} ${q.flagged ? "flagged" : ""}" type="button" data-question-index="${index}">${q.position}</button>`; }
function answer(q, option, index) { const type = q.multiple ? "checkbox" : "radio"; const checked = q.selected?.includes(index); return `<label class="v26-answer ${checked ? "selected" : ""}"><input type="${type}" name="answer" value="${index}" ${checked ? "checked" : ""}/><span>${String.fromCharCode(65 + index)}</span><b>${escape(option)}</b></label>`; }
function domainColor(index) { return ["#e39a60", "#77a4d5", "#9b82cf", "#70af81", "#d16d68"][index % 5]; }
function modeName(value = "") { return String(value).replace("exam_", "").replaceAll("_", " ").replace(/\b\w/g, (m) => m.toUpperCase()); }
function clock(total) { const s = Math.max(0, Number(total || 0)); const h = Math.floor(s / 3600); const m = Math.floor((s % 3600) / 60); const sec = s % 60; return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`; }
function escape(value) { return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;"); }
