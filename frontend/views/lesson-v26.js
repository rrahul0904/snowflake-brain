export const VIEW_ID = "v26-lesson";

import { escapeHtml, getSkillMap, getStudyLesson, getTaskProgress, setTaskProgress } from "../api.js";
import { activeTrack, setActiveTrack } from "../ui.js";

const COLORS = ["#e39a60", "#77a4d5", "#9b82cf", "#70af81", "#d16d68"];

export default async function mount(container, params = {}) {
  const trackId = params.track_id || activeTrack();
  const map = await getSkillMap();
  const certs = map.certifications || [];
  const cert = certs.find((item) => item.id === trackId) || certs[0];
  if (!cert) throw new Error("Certification is not configured");
  setActiveTrack(cert.id);
  const flat = [];
  (cert.domains || []).forEach((domain, domainIndex) => (domain.skills || []).forEach((skill, skillIndex) => flat.push({ ...skill, domain, domainIndex, skillIndex })));
  let index = flat.findIndex((item) => item.id === params.skill_id);
  if (index < 0) index = 0;
  const item = flat[index];
  if (!item) throw new Error("Task not found");
  const [lesson, progress] = await Promise.all([
    getStudyLesson(item.id, { track_id: cert.id }),
    getTaskProgress({ track_id: cert.id }).catch(() => ({ completed_skill_ids: [] })),
  ]);
  const content = lesson.content || {};
  const completed = new Set(progress.completed_skill_ids || []);
  const taskCode = item.task_code || `${item.domainIndex + 1}.${item.skillIndex + 1}`;
  const prev = flat[index - 1];
  const next = flat[index + 1];
  const body = `<div class="v26-lesson"><div class="v26-breadcrumbs"><a href="#/curriculum?track_id=${encodeURIComponent(cert.id)}">Curriculum</a><span>/</span><a href="#/domain?track_id=${encodeURIComponent(cert.id)}&domain_id=${encodeURIComponent(item.domain.id)}">${escapeHtml(item.domain.title)}</a></div><header class="v26-lesson-head"><p class="v26-kicker">Task ${escapeHtml(taskCode)} · ${Number(item.domain.weight || 0)}%</p><h1>${escapeHtml(item.title)}</h1><p>${escapeHtml(item.objective || content.summary || "")}</p><div class="v26-inline-actions"><button class="v26-btn ${completed.has(item.id) ? "secondary" : "primary"}" type="button" data-complete>${completed.has(item.id) ? "✓ Completed" : "Mark Complete"}</button><a class="v26-btn secondary" href="#/practice?track_id=${encodeURIComponent(cert.id)}&mode=drill&skill_id=${encodeURIComponent(item.id)}">Drill this task</a></div></header>${textList("What You Need to Know", content.what_you_need_to_know || [content.summary])}${keyConcept(content.key_concept)}${decisionRules(content.decision_rules)}${trapCards(content.trap_explanations, content.anti_patterns)}${workedExample(content.worked_example)}${scenario(content.scenario)}${buildExercise(content.build_exercise)}${sources(content.sources)}<nav class="v26-lesson-nav">${prev ? `<a href="#/skill?track_id=${encodeURIComponent(cert.id)}&skill_id=${encodeURIComponent(prev.id)}"><span>Previous</span><strong>${escapeHtml(prev.title)}</strong></a>` : `<span></span>`}${next ? `<a class="next" href="#/skill?track_id=${encodeURIComponent(cert.id)}&skill_id=${encodeURIComponent(next.id)}"><span>Next</span><strong>${escapeHtml(next.title)}</strong></a>` : `<a class="next" href="#/practice?track_id=${encodeURIComponent(cert.id)}"><span>Next</span><strong>Practice what you learned</strong></a>`}</nav></div>`;
  container.innerHTML = `<div class="v26-study-layout">${sidebar(cert, item.domain.id)}<main class="v26-study-content">${body}</main></div>`;
  container.querySelector("[data-complete]")?.addEventListener("click", async (event) => {
    const nextState = !completed.has(item.id);
    event.currentTarget.disabled = true;
    await setTaskProgress({ track_id: cert.id, skill_id: item.id, completed: nextState });
    nextState ? completed.add(item.id) : completed.delete(item.id);
    event.currentTarget.className = `v26-btn ${nextState ? "secondary" : "primary"}`;
    event.currentTarget.textContent = nextState ? "✓ Completed" : "Mark Complete";
    event.currentTarget.disabled = false;
  });
  bindScenario(container);
}

function textList(title, items = []) {
  const rows = items.filter(Boolean);
  if (!rows.length) return "";
  return `<section class="v26-lesson-section"><h2>${title}</h2><ul>${rows.map((item) => `<li>${escapeHtml(typeof item === "string" ? item : item.text || "")}</li>`).join("")}</ul></section>`;
}

function keyConcept(value) {
  if (!value) return "";
  return `<section class="v26-lesson-section v26-key-concept"><span>Key Concept</span><p>${escapeHtml(typeof value === "string" ? value : value.text || "")}</p></section>`;
}

function decisionRules(rules = []) {
  if (!rules.length) return "";
  return `<section class="v26-lesson-section"><h2>Decision Rules</h2><div class="v26-decision-rules">${rules.map((rule) => `<article><span>When</span><h3>${escapeHtml(rule.when || "")}</h3><p><strong>Choose:</strong> ${escapeHtml(rule.choose || "")}</p><p>${escapeHtml(rule.why || "")}</p></article>`).join("")}</div></section>`;
}

function trapCards(explanations = [], anti = []) {
  const rows = explanations.length ? explanations : anti.map((item) => ({ trap: item, correction: "Use the task boundary and scenario requirement to choose the Snowflake feature." }));
  if (!rows.length) return "";
  return `<section class="v26-lesson-section"><h2>Exam Traps</h2><div class="v26-traps">${rows.map((row) => `<article><span>Trap</span><p>${escapeHtml(row.trap || row)}</p>${row.correction ? `<strong>${escapeHtml(row.correction)}</strong>` : ""}</article>`).join("")}</div></section>`;
}

function workedExample(example) {
  if (!example || (!example.prompt && !example.answer && !example.question)) return "";
  return `<section class="v26-lesson-section"><h2>Worked Example</h2><div class="v26-worked"><p>${escapeHtml(example.prompt || example.question || "")}</p>${example.answer ? `<strong>${escapeHtml(example.answer)}</strong>` : ""}${example.reasoning ? `<p>${escapeHtml(example.reasoning)}</p>` : ""}</div></section>`;
}

function scenario(item) {
  if (!item?.question) return "";
  const options = item.options || [];
  return `<section class="v26-lesson-section"><h2>Practice Scenario</h2><div class="v26-scenario" data-scenario data-correct="${Number(item.correct_index || 0)}" data-explanation="${escapeHtml(item.explanation || "")}"><p>${escapeHtml(item.question)}</p><div>${options.map((option, index) => `<label><input type="radio" name="lesson-scenario" value="${index}"/><span>${String.fromCharCode(65 + index)}</span><b>${escapeHtml(option)}</b></label>`).join("")}</div><button class="v26-btn secondary" type="button" data-check-scenario>Check Answer</button><p class="v26-scenario-result" data-scenario-result hidden></p></div></section>`;
}

function bindScenario(container) {
  container.querySelector("[data-check-scenario]")?.addEventListener("click", () => {
    const root = container.querySelector("[data-scenario]");
    const chosen = Number(root.querySelector("input:checked")?.value ?? -1);
    const correct = Number(root.dataset.correct || 0);
    const result = root.querySelector("[data-scenario-result]");
    result.hidden = false;
    result.classList.toggle("correct", chosen === correct);
    result.textContent = chosen < 0 ? "Choose an answer first." : `${chosen === correct ? "Correct." : `Not quite. The best answer is ${String.fromCharCode(65 + correct)}.`} ${root.dataset.explanation || ""}`;
  });
}

function buildExercise(exercise) {
  if (!exercise || (!exercise.prompt && !exercise.title && !exercise.description)) return "";
  const checks = exercise.checks || [];
  return `<section class="v26-lesson-section"><h2>Build Exercise</h2><div class="v26-build"><span>${escapeHtml(exercise.title || "Hands-on task")}</span><p>${escapeHtml(exercise.prompt || exercise.description || "")}</p>${checks.length ? `<ul>${checks.map((check) => `<li>${escapeHtml(check)}</li>`).join("")}</ul>` : ""}</div></section>`;
}

function sources(rows = []) {
  if (!rows.length) return "";
  return `<section class="v26-lesson-section"><h2>Sources</h2><div class="v26-source-list">${rows.map((source) => { if (typeof source === "string") return `<span>${escapeHtml(source)}</span>`; const href = source.url || source.href; return href ? `<a href="${escapeHtml(href)}" target="_blank" rel="noopener noreferrer">${escapeHtml(source.title || source.label || href)} ↗</a>` : `<span>${escapeHtml(source.title || source.label || "Source")}</span>`; }).join("")}</div></section>`;
}

function sidebar(cert, active) {
  const domains = (cert.domains || []).map((domain, index) => `<a class="v26-side-domain ${active === domain.id ? "active" : ""}" href="#/domain?track_id=${encodeURIComponent(cert.id)}&domain_id=${encodeURIComponent(domain.id)}"><i style="--domain:${COLORS[index % COLORS.length]}"></i><b>${index + 1}</b><span>${escapeHtml(domain.title)}</span><em>${Number(domain.weight || 0)}%</em></a>`).join("");
  return `<aside class="v26-study-nav"><div class="v26-side-brand"><span>${escapeHtml(cert.exam_code || "COF-C03")}</span><strong>${escapeHtml(cert.title || "SnowPro Core")}</strong></div><div class="v26-side-group"><small>Study Tools</small><a href="#/progress?track_id=${encodeURIComponent(cert.id)}">Progress Dashboard</a><a href="#/practice?track_id=${encodeURIComponent(cert.id)}&mode=drill">Drill Mode</a></div><div class="v26-side-group"><small>Curriculum</small><a href="#/curriculum?track_id=${encodeURIComponent(cert.id)}">Exam Domains</a>${domains}</div><div class="v26-side-group"><small>Practice</small><a href="#/exercises?track_id=${encodeURIComponent(cert.id)}">Build Exercises</a><a href="#/practice?track_id=${encodeURIComponent(cert.id)}&mode=diagnostic">Diagnostic Test</a></div><div class="v26-side-group"><small>Look Up</small><a href="#/quick-reference?track_id=${encodeURIComponent(cert.id)}">Quick Reference</a><a href="#/glossary?track_id=${encodeURIComponent(cert.id)}">Glossary</a></div></aside>`;
}
