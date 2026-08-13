export const VIEW_ID = "certification-guide";

import {
  escapeHtml,
  getCertificationCatalog,
  getContentCoverage,
  getDiagnosticPlan,
  getEvidenceAudit,
  getIntelligenceReadiness,
  getLabs,
  getSkillMap,
  getSkillMastery,
  getSkillResources,
  getStudyLesson,
  getTaskProgress,
  setTaskProgress,
} from "../api.js?v=20260812-v23-cert-guide";
import { activeTrack, pct, setActiveTrack, statusLabel } from "../ui.js?v=20260731-v21-editorial-replica";

const routePath = () => (window.location.hash || "#/home").split("?")[0];

export default async function mount(container, params = {}) {
  const trackId = params.track_id || activeTrack();
  setActiveTrack(trackId);
  const route = routePath();
  if (route === "#/home") return renderHome(container, trackId);
  if (route === "#/progress") return renderProgress(container, trackId);
  if (route === "#/domain") return renderDomain(container, trackId, params.domain_id);
  if (route === "#/skill") return renderSkill(container, trackId, params.skill_id);
  if (route === "#/diagnostic") return renderDiagnostic(container, trackId);
  if (route === "#/drill") return renderDrill(container, trackId, params);
  if (route === "#/mock") return renderMock(container, trackId);
  if (route === "#/exercises") return renderExercises(container, trackId);
  if (route === "#/quick-reference") return renderQuickReference(container, trackId, params.domain_id);
  if (route === "#/glossary") return renderGlossary(container, trackId, params.domain_id);
  return renderCurriculum(container, trackId);
}

async function guideContext(trackId) {
  const [map, catalog] = await Promise.all([getSkillMap(), getCertificationCatalog().catch(() => ({ official_certifications: [], custom_tracks: [] }))]);
  const certs = map.certifications || [];
  const cert = certs.find((item) => item.id === trackId) || certs[0] || { id: trackId, title: trackId, domains: [] };
  return { map, catalog, certs, cert };
}

function toolbar(trackId, active = "") {
  const items = [
    ["progress", "Progress Dashboard"],
    ["drill", "Drill Mode"],
    ["exercises", "Build Exercises"],
    ["diagnostic", "Diagnostic Test"],
    ["quick-reference", "Quick Reference"],
    ["glossary", "Glossary"],
  ];
  return `<nav class="guide-toolbar" aria-label="Study tools">${items.map(([route, label]) => `<a class="${active === route ? "active" : ""}" href="#/${route}?track_id=${encodeURIComponent(trackId)}">${label}</a>`).join("")}</nav>`;
}

function certificationDescription(cert) {
  if ((cert.official_overview || []).length) return cert.official_overview.slice(0, 3).join(" · ");
  return "Study the exam blueprint, practise task statements, build hands-on confidence, and measure readiness until you are prepared to sit the exam.";
}

function catalogCard(item, currentTrack) {
  const implemented = Boolean(item.implemented && item.configured_track_id);
  const launchable = Boolean(item.launchable && implemented);
  const href = launchable ? `#/home?track_id=${encodeURIComponent(item.configured_track_id)}` : "";
  const label = launchable ? (item.configured_track_id === currentTrack ? "Selected" : "Open →") : "Curriculum coming soon";
  const body = (item.overview || []).slice(0, 3).join(" · ") || item.candidate_experience || "Official SnowPro certification track.";
  const inner = `<div class="guide-card-top"><span class="guide-code">${escapeHtml(item.exam_code || "SnowPro")}</span><span>${escapeHtml(label)}</span></div><h3>${escapeHtml(item.title)}</h3><p>${escapeHtml(body)}</p><div class="guide-card-footer"><span>${escapeHtml(item.level || "Certification")}</span><span>${escapeHtml(item.candidate_experience || "")}</span></div>`;
  return launchable ? `<a class="guide-cert-card" href="${href}">${inner}</a>` : `<article class="guide-cert-card muted-card">${inner}</article>`;
}

async function renderHome(container, trackId) {
  const { catalog, cert } = await guideContext(trackId);
  const [progress, coverage] = await Promise.all([
    getTaskProgress({ track_id: cert.id }).catch(() => ({ completed_tasks: 0, total_tasks: 0 })),
    getContentCoverage().catch(() => ({ usable_tasks: 0, curated_tasks: 0 })),
  ]);
  const domains = cert.domains || [];
  const skills = domains.reduce((sum, domain) => sum + (domain.skills || []).length, 0);
  container.innerHTML = `<main class="guide-page">
    <section class="guide-hero"><div>
      <p class="guide-kicker">Snowflake Certified · ${escapeHtml(cert.exam_code || "Certification")}</p>
      <h1>Practise until<br><em>you pass.</em></h1>
      <p class="guide-hero-copy">A complete written Snowflake certification guide: learn every exam domain, check scenarios, drill weak skills, complete build exercises, sit timed mocks, and track readiness.</p>
      <div class="guide-actions"><a class="guide-button blue" href="#/diagnostic?track_id=${encodeURIComponent(cert.id)}">Take diagnostic</a><a class="guide-button secondary" href="#/curriculum?track_id=${encodeURIComponent(cert.id)}">Start learning</a></div>
      ${toolbar(cert.id)}
    </div><aside class="guide-fact-card"><strong>${escapeHtml(cert.title || cert.id)}</strong><div class="guide-facts">
      <div><span>Exam</span><b>${escapeHtml(cert.exam_code || "Configured")}</b></div><div><span>Domains</span><b>${domains.length}</b></div><div><span>Task lessons</span><b>${skills}</b></div><div><span>Completed</span><b>${progress.completed_tasks || 0}/${progress.total_tasks || skills}</b></div>
    </div></aside></section>

    <section class="guide-section"><div class="guide-section-head"><div><p class="guide-eyebrow">Official catalog</p><h2>Choose a SnowPro certification.</h2></div><p>Implemented tracks open immediately. The rest remain visible as the official roadmap instead of pretending custom tracks are certifications.</p></div>
      <h3 class="guide-catalog-label">Core & Associate</h3><div class="guide-cert-grid">${(catalog.official_certifications || []).filter((x) => ["core", "associate"].includes(x.category)).map((x) => catalogCard(x, cert.id)).join("")}</div>
      <h3 class="guide-catalog-label">Specialty</h3><div class="guide-cert-grid">${(catalog.official_certifications || []).filter((x) => x.category === "specialty").map((x) => catalogCard(x, cert.id)).join("")}</div>
      <h3 class="guide-catalog-label">Advanced</h3><div class="guide-cert-grid">${(catalog.official_certifications || []).filter((x) => x.category === "advanced").map((x) => catalogCard(x, cert.id)).join("")}</div>
      ${(catalog.custom_tracks || []).length ? `<h3 class="guide-catalog-label">Custom learning tracks</h3><div class="guide-cert-grid">${catalog.custom_tracks.map((x) => catalogCard(x, cert.id)).join("")}</div>` : ""}
    </section>

    <section class="guide-section"><div class="guide-section-head"><div><p class="guide-eyebrow">Study system</p><h2>Everything needed to prepare.</h2></div><p>${coverage.usable_tasks || skills} task lessons are usable now; ${coverage.curated_tasks || 0} are fully authored editorial lessons.</p></div><div class="guide-tool-grid">
      ${toolCard("Diagnostic", "Find weak areas", "An untimed baseline across the exam blueprint.", `#/diagnostic?track_id=${cert.id}`)}
      ${toolCard("Learn", "Study task by task", "Written explanations, decision rules, traps, examples, scenarios and sources.", `#/curriculum?track_id=${cert.id}`)}
      ${toolCard("Drill", "Repair weak skills", "Targeted practice based on domain, skill and previous performance.", `#/drill?track_id=${cert.id}`)}
      ${toolCard("Build", "Apply it hands-on", "Snowflake SQL and architecture exercises with local validation.", `#/exercises?track_id=${cert.id}`)}
      ${toolCard("Mock", "Rehearse the exam", "Timed mock behavior with review flags, navigation and deferred explanations.", `#/mock?track_id=${cert.id}`)}
      ${toolCard("Review", "Final reference", "Printable quick-reference sheets and searchable glossary.", `#/quick-reference?track_id=${cert.id}`)}
    </div></section>
  </main>`;
}

function toolCard(kicker, title, body, href) {
  return `<a class="guide-tool-card" href="${href}"><span class="guide-code">${escapeHtml(kicker)}</span><h3>${escapeHtml(title)}</h3><p>${escapeHtml(body)}</p><div class="guide-card-footer"><span>Open</span><span>→</span></div></a>`;
}

async function renderCurriculum(container, trackId) {
  const { cert } = await guideContext(trackId);
  const progress = await getTaskProgress({ track_id: cert.id }).catch(() => ({ completed_skill_ids: [] }));
  const completed = new Set(progress.completed_skill_ids || []);
  container.innerHTML = `<main class="guide-page"><section class="guide-task-head"><p class="guide-eyebrow">Exam syllabus · ${escapeHtml(cert.exam_code || "")}</p><h1>Exam Domains</h1><p>${escapeHtml(certificationDescription(cert))}</p>${toolbar(cert.id)}</section><section class="guide-section"><div class="guide-domain-grid">${(cert.domains || []).map((domain, index) => {
    const done = (domain.skills || []).filter((skill) => completed.has(skill.id)).length;
    return `<a class="guide-domain-card" href="#/domain?track_id=${encodeURIComponent(cert.id)}&domain_id=${encodeURIComponent(domain.id)}"><div class="guide-card-top"><span class="guide-weight">${Number(domain.weight || 0)}%</span><span>${String(index + 1).padStart(2, "0")}</span></div><h3>${escapeHtml(domain.title)}</h3><p>${escapeHtml(domain.description || `${(domain.skills || []).length} task statements in this domain.`)}</p><div class="guide-card-footer"><span>${done}/${(domain.skills || []).length} complete</span><span>Study →</span></div></a>`;
  }).join("")}</div></section></main>`;
}

async function renderDomain(container, trackId, domainId) {
  const { cert } = await guideContext(trackId);
  const progress = await getTaskProgress({ track_id: cert.id }).catch(() => ({ completed_skill_ids: [] }));
  const completed = new Set(progress.completed_skill_ids || []);
  const domains = cert.domains || [];
  const domainIndex = Math.max(0, domains.findIndex((item) => item.id === domainId));
  const domain = domains[domainIndex] || domains[0];
  if (!domain) return renderMissing(container, "Domain not found");
  container.innerHTML = `<main class="guide-page"><div class="guide-breadcrumbs"><a href="#/curriculum?track_id=${encodeURIComponent(cert.id)}">Curriculum</a> / ${escapeHtml(domain.title)}</div><section class="guide-task-head"><p class="guide-eyebrow">Domain ${domainIndex + 1} · ${Number(domain.weight || 0)}%</p><h1>${escapeHtml(domain.title)}</h1><p>${escapeHtml(domain.description || "Master the task statements in this portion of the exam blueprint.")}</p><div class="guide-actions"><a class="guide-button blue" href="#/drill?track_id=${encodeURIComponent(cert.id)}&domain_id=${encodeURIComponent(domain.id)}">Drill this domain</a><a class="guide-button secondary" href="#/quick-reference?track_id=${encodeURIComponent(cert.id)}&domain_id=${encodeURIComponent(domain.id)}">Quick reference</a></div></section><section class="guide-section"><div class="guide-section-head"><div><p class="guide-eyebrow">Task Statements</p><h2>${(domain.skills || []).length} lessons</h2></div></div><div class="guide-skill-list">${(domain.skills || []).map((skill, index) => `<a class="guide-skill-card" href="#/skill?track_id=${encodeURIComponent(cert.id)}&skill_id=${encodeURIComponent(skill.id)}"><span class="guide-skill-number">${domainIndex + 1}.${index + 1}</span><div><h3>${escapeHtml(skill.title)}</h3><p>${escapeHtml(skill.objective || "")}</p></div><span>${completed.has(skill.id) ? "✓ Complete" : "Study →"}</span></a>`).join("")}</div></section></main>`;
}

function listHtml(items, variant = "") {
  return `<ul class="guide-lesson-list ${variant === "warning" ? "is-warning" : ""}">${(items || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
}

function decisionRules(rules) {
  return `<div class="guide-reference-grid">${(rules || []).map((rule) => `<article class="guide-reference-card"><span class="guide-code">When</span><h3>${escapeHtml(rule.when)}</h3><p><strong>Choose:</strong> ${escapeHtml(rule.choose)}</p><p>${escapeHtml(rule.why)}</p></article>`).join("")}</div>`;
}

function fallbackScenario(scenario) {
  if (!scenario?.question) return `<div class="guide-empty">No scenario is configured yet.</div>`;
  return `<div class="guide-scenario" data-scenario data-correct="${Number(scenario.correct_index || 0)}"><p>${escapeHtml(scenario.question)}</p><div class="guide-options">${(scenario.options || []).map((option, index) => `<label><input type="radio" name="scenario-answer" value="${index}"/><span>${String.fromCharCode(65 + index)}. ${escapeHtml(option)}</span></label>`).join("")}</div><button class="guide-button secondary" type="button" data-check-scenario>Check Answer</button><div class="guide-answer" data-scenario-result data-explanation="${escapeHtml(scenario.explanation || "")}" hidden></div></div>`;
}

function parseJson(value, fallback = []) {
  try { return (typeof value === "string" ? JSON.parse(value) : value) ?? fallback; } catch { return fallback; }
}

function mappedScenario(question, fallback) {
  if (!question?.question) return fallbackScenario(fallback);
  const options = parseJson(question.options_json, []);
  const correct = parseJson(question.correct_json, []);
  return `<div class="guide-scenario" data-scenario data-correct="${escapeHtml(JSON.stringify(correct))}"><p>${escapeHtml(question.question)}</p><div class="guide-options">${options.map((option, index) => `<label><input type="radio" name="scenario-answer" value="${index}"/><span>${String.fromCharCode(65 + index)}. ${escapeHtml(typeof option === "string" ? option : option?.text || String(option))}</span></label>`).join("")}</div><button class="guide-button secondary" type="button" data-check-scenario>Check Answer</button><div class="guide-answer" data-scenario-result data-explanation="${escapeHtml(question.explanation || fallback?.explanation || "")}" hidden></div></div>`;
}

async function renderSkill(container, trackId, skillId) {
  const { cert } = await guideContext(trackId);
  const progress = await getTaskProgress({ track_id: cert.id }).catch(() => ({ completed_skill_ids: [] }));
  const completed = new Set(progress.completed_skill_ids || []);
  const flat = [];
  (cert.domains || []).forEach((domain, domainIndex) => (domain.skills || []).forEach((skill, skillIndex) => flat.push({ ...skill, domain_id: domain.id, domain: domain.title, domain_weight: domain.weight, domain_index: domainIndex, skill_index: skillIndex })));
  const index = Math.max(0, flat.findIndex((item) => item.id === skillId));
  const skill = flat[index] || flat[0];
  if (!skill) return renderMissing(container, "Task not found");
  const next = flat[index + 1];
  const [lessonPayload, resources, labsPayload] = await Promise.all([
    getStudyLesson(skill.id, { track_id: cert.id }),
    getSkillResources(skill.id, { track_id: cert.id, limit: 8 }).catch(() => ({ questions: [] })),
    getLabs({ track_id: cert.id }).catch(() => ({ labs: [] })),
  ]);
  const content = lessonPayload.content || {};
  const allLabs = labsPayload.labs || labsPayload.challenges || [];
  const primaryLab = allLabs.find((lab) => lab.skill_id === skill.id) || null;
  const exercise = content.build_exercise || {};
  const taskNumber = `${skill.domain_index + 1}.${skill.skill_index + 1}`;
  const isComplete = completed.has(skill.id);
  const sourceLinks = (content.sources || []).map((source) => `<li><a href="${escapeHtml(source.url)}" target="_blank" rel="noreferrer"><strong>${escapeHtml(source.title)}</strong><small>Official/reference source</small></a></li>`).join("");
  container.innerHTML = `<main class="guide-page guide-lesson-page">
    <div class="guide-breadcrumbs"><a href="#/curriculum?track_id=${encodeURIComponent(cert.id)}">Learn</a> / <a href="#/domain?track_id=${encodeURIComponent(cert.id)}&domain_id=${encodeURIComponent(skill.domain_id)}">${escapeHtml(skill.domain)}</a> / ${taskNumber}</div>
    <section class="guide-task-head"><div class="guide-task-meta"><span>Domain ${skill.domain_index + 1}</span><span>Task ${taskNumber}</span><span>${Number(skill.domain_weight || 0)}% weight</span><span>${escapeHtml(lessonPayload.content_quality === "curated" ? "Editorial lesson" : "Curriculum lesson")}</span></div><button class="guide-complete-button ${isComplete ? "complete" : ""}" type="button" data-complete-task>${isComplete ? "✓ Completed" : "Mark Complete"}</button><h1>${escapeHtml(skill.title)}</h1><p>${escapeHtml(content.summary || skill.objective || "")}</p></section>
    <div class="guide-lesson-layout">
      <article class="guide-lesson-body">
        <section class="guide-content-block"><p class="guide-section-number">01 · Core knowledge</p><h2>What You Need to Know</h2>${listHtml(content.what_you_need_to_know || [skill.objective])}<div class="guide-key-concept"><strong>Key Concept</strong><p>${escapeHtml(content.key_concept || skill.objective || "")}</p></div></section>
        <section class="guide-content-block"><p class="guide-section-number">02 · Make the decision</p><h2>Decision Rules</h2>${decisionRules(content.decision_rules || [])}</section>
        <section class="guide-content-block"><p class="guide-section-number">03 · Avoid distractors</p><h2>Common Anti-Patterns</h2>${listHtml(content.anti_patterns || skill.exam_traps || [], "warning")}</section>
        <section class="guide-content-block"><h2>Exam Traps</h2><div class="guide-trap-cards">${(content.trap_explanations || []).map((item) => `<article><span>Exam Trap</span><p><strong>${escapeHtml(item.trap)}</strong></p><p>${escapeHtml(item.correction)}</p></article>`).join("") || (skill.exam_traps || []).map((trap) => `<article><span>Exam Trap</span><p>${escapeHtml(trap)}</p></article>`).join("")}</div></section>
        ${content.worked_example ? `<section class="guide-content-block"><p class="guide-section-number">04 · Apply it</p><h2>Worked Example</h2><p class="guide-hero-copy">${escapeHtml(content.worked_example.scenario || "")}</p>${listHtml(content.worked_example.reasoning || [])}<div class="guide-key-concept"><strong>Answer</strong><p>${escapeHtml(content.worked_example.answer || "")}</p></div></section>` : ""}
        <section class="guide-content-block"><p class="guide-section-number">05 · Check understanding</p><h2>Practice Scenario</h2>${mappedScenario((resources.questions || [])[0], content.scenario)}</section>
        <section class="guide-content-block"><p class="guide-section-number">06 · Build it</p><h2>Build Exercise</h2>${primaryLab ? `<div class="guide-build-exercise"><span class="guide-code">Validated Lab</span><h3>${escapeHtml(primaryLab.title || primaryLab.name)}</h3><p>${escapeHtml(primaryLab.scenario || primaryLab.description || "Complete the Snowflake challenge.")}</p><div class="guide-card-footer"><span>${primaryLab.estimated_minutes || primaryLab.minutes || 20} minutes</span><a href="#/labs?track_id=${encodeURIComponent(cert.id)}&lab_id=${encodeURIComponent(primaryLab.id)}">Open lab →</a></div></div>` : `<div class="guide-build-exercise"><span class="guide-code">Task Exercise</span><h3>${escapeHtml(exercise.title || `Apply ${skill.title}`)}</h3><p>${escapeHtml(exercise.prompt || "Apply the lesson to a Snowflake implementation.")}</p>${exercise.starter_sql ? `<pre><code>${escapeHtml(exercise.starter_sql)}</code></pre>` : ""}<h4>Completion checks</h4>${listHtml(exercise.checks || [])}</div>`}</section>
        <section class="guide-content-block"><p class="guide-section-number">07 · Go deeper</p><h2>Sources & Review</h2><ul class="guide-link-list">${sourceLinks}<li><a href="#/quick-reference?track_id=${encodeURIComponent(cert.id)}&domain_id=${encodeURIComponent(skill.domain_id)}"><strong>Quick Reference</strong><small>Domain-level final review</small></a></li><li><a href="#/glossary?track_id=${encodeURIComponent(cert.id)}&domain_id=${encodeURIComponent(skill.domain_id)}"><strong>Glossary</strong><small>Key terms and exam context</small></a></li></ul></section>
      </article>
      <aside class="guide-lesson-sidebar" aria-label="Task summary">
        <div class="guide-task-summary"><p>Task snapshot</p><dl><div><dt>Task</dt><dd>${taskNumber}</dd></div><div><dt>Domain weight</dt><dd>${Number(skill.domain_weight || 0)}%</dd></div><div><dt>Lesson type</dt><dd>${escapeHtml(lessonPayload.content_quality === "curated" ? "Editorial" : "Curriculum")}</dd></div></dl></div>
        <div class="guide-next-action"><p>Next best action</p><strong>Prove the concept under exam conditions.</strong><a href="#/drill?track_id=${encodeURIComponent(cert.id)}&skill_id=${encodeURIComponent(skill.id)}&domain_id=${encodeURIComponent(skill.domain_id)}">Drill this task →</a><a href="#/quick-reference?track_id=${encodeURIComponent(cert.id)}&domain_id=${encodeURIComponent(skill.domain_id)}">Open quick reference →</a></div>
      </aside>
    </div>
    <section class="guide-lesson-footer"><div><p class="guide-section-number">Lesson complete?</p><h2>Turn reading into evidence.</h2></div><div class="guide-actions"><a class="guide-button blue" href="#/drill?track_id=${encodeURIComponent(cert.id)}&skill_id=${encodeURIComponent(skill.id)}&domain_id=${encodeURIComponent(skill.domain_id)}">Drill This Task</a><button class="guide-button secondary" type="button" data-complete-task>${isComplete ? "✓ Completed" : "Mark Complete"}</button></div></section>
    ${next ? `<a class="guide-next-task" href="#/skill?track_id=${encodeURIComponent(cert.id)}&skill_id=${encodeURIComponent(next.id)}"><span>Next Lesson</span><strong>${escapeHtml(next.title)}</strong><b>→</b></a>` : `<a class="guide-next-task" href="#/progress?track_id=${encodeURIComponent(cert.id)}"><span>Curriculum complete</span><strong>Review your progress</strong><b>→</b></a>`}
  </main>`;
  bindTaskPage(container, cert.id, skill.id, isComplete);
}

function bindTaskPage(container, trackId, skillId, initialComplete) {
  let complete = initialComplete;
  container.querySelectorAll("[data-complete-task]").forEach((button) => button.addEventListener("click", async () => {
    complete = !complete;
    await setTaskProgress({ track_id: trackId, skill_id: skillId, completed: complete });
    container.querySelectorAll("[data-complete-task]").forEach((node) => { node.textContent = complete ? "✓ Completed" : "Mark Complete"; node.classList.toggle("complete", complete); });
  }));
  container.querySelector("[data-check-scenario]")?.addEventListener("click", () => {
    const scenario = container.querySelector("[data-scenario]");
    const selected = scenario?.querySelector("input[name='scenario-answer']:checked");
    const result = scenario?.querySelector("[data-scenario-result]");
    if (!result) return;
    if (!selected) { result.hidden = false; result.textContent = "Choose an answer before checking."; return; }
    const correctRaw = parseJson(scenario.dataset.correct, scenario.dataset.correct);
    const normalized = Array.isArray(correctRaw) ? correctRaw : [correctRaw];
    const selectedIndex = Number(selected.value);
    const isCorrect = normalized.some((value) => Number(value) === selectedIndex || String(value).toUpperCase() === String.fromCharCode(65 + selectedIndex));
    result.hidden = false;
    result.innerHTML = `<strong>${isCorrect ? "Correct." : "Not quite."}</strong> ${escapeHtml(result.dataset.explanation || "Review the decision rules above.")}`;
  });
}

async function renderProgress(container, trackId) {
  const { cert } = await guideContext(trackId);
  const [readiness, mastery, evidence, progress] = await Promise.all([
    getIntelligenceReadiness({ track_id: cert.id }).catch(() => ({})), getSkillMastery({ track_id: cert.id }).catch(() => ({ skills: [] })), getEvidenceAudit({ track_id: cert.id, limit: 10 }).catch(() => ({})), getTaskProgress({ track_id: cert.id }),
  ]);
  const completed = new Set(progress.completed_skill_ids || []);
  const skills = mastery.skills || [];
  const attempts = skills.reduce((sum, item) => sum + Number(item.attempts || 0), 0);
  const mastered = skills.filter((item) => Number(item.mastery_level || 0) >= 4).length;
  const due = skills.filter((item) => Number(item.mastery_level || 0) < 4).length;
  const taskPct = pct(((progress.completed_tasks || 0) / Math.max(1, progress.total_tasks || 1)) * 100);
  container.innerHTML = `<main class="guide-page"><section class="guide-task-head"><p class="guide-eyebrow">${escapeHtml(cert.title)}</p><h1>Your Progress</h1><p>Completion, practice, mocks and evidence quality are tracked separately so the readiness score never pretends thin evidence is certainty.</p>${toolbar(cert.id, "progress")}</section>
    <section class="guide-section guide-readiness"><div class="guide-score-card"><span>Exam Readiness</span><div class="guide-score">${pct(readiness.readiness_score || 0)}</div><strong>${escapeHtml(statusLabel(readiness.status || "not_ready"))}</strong><p>Confidence: ${pct(readiness.readiness_confidence || 0)}% · ${escapeHtml(readiness.readiness_confidence_status || "insufficient")}</p></div><div class="guide-metric-grid">${metric("Lessons", `${taskPct}%`, `${progress.completed_tasks || 0}/${progress.total_tasks || 0} complete`)}${metric("Practice", `${pct(readiness.accuracy_pct || 0)}%`, `${readiness.attempts || attempts} attempts`)}${metric("Mock Exams", `${readiness.mock_exam_attempts || 0}`, `Best ${readiness.best_mock_score || 0}%`)}${metric("Mapping Trust", `${evidence.mapping_trust_score || 0}%`, evidence.mapping_trust_status || "Not audited")}</div></section>
    <section class="guide-section"><div class="guide-section-head"><div><p class="guide-eyebrow">Domain Progress</p><h2>Task completion by domain.</h2></div></div><div class="guide-domain-progress">${(cert.domains || []).map((domain) => { const total = (domain.skills || []).length; const done = (domain.skills || []).filter((skill) => completed.has(skill.id)).length; const value = pct((done / Math.max(1, total)) * 100); return `<a class="guide-domain-row" href="#/domain?track_id=${encodeURIComponent(cert.id)}&domain_id=${encodeURIComponent(domain.id)}"><div><strong>${escapeHtml(domain.title)}</strong><br><small>${done}/${total} lessons · ${Number(domain.weight || 0)}% exam weight</small></div><div class="guide-progress-bar"><i style="width:${value}%"></i></div><strong>${value}%</strong></a>`; }).join("")}</div></section>
    <section class="guide-section"><div class="guide-section-head"><div><p class="guide-eyebrow">Drill Summary</p><h2>Practice evidence.</h2></div></div><div class="guide-metric-grid">${metric("Attempts", String(attempts), "Recorded question evidence")}${metric("Mastered", String(mastered), "Skills at accurate mastery")}${metric("Due", String(due), "Skills below target")}</div><div class="guide-actions"><a class="guide-button blue" href="#/drill?track_id=${encodeURIComponent(cert.id)}">Start Drill</a></div></section>
    ${(readiness.blockers || []).length ? `<section class="guide-section"><div class="guide-section-head"><div><p class="guide-eyebrow">Readiness blockers</p><h2>What still needs work.</h2></div></div>${listHtml(readiness.blockers)}</section>` : ""}
  </main>`;
}

function metric(label, value, detail) { return `<div class="guide-metric"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong><small>${escapeHtml(detail)}</small></div>`; }

async function renderDiagnostic(container, trackId) {
  const { cert } = await guideContext(trackId);
  const desired = Math.max(25, (cert.domains || []).length * 5);
  const plan = await getDiagnosticPlan({ track_id: cert.id, count: desired }).catch(() => ({}));
  const questionCount = (plan.questions || plan.question_ids || []).length || desired;
  container.innerHTML = `<main class="guide-page"><section class="guide-task-head"><p class="guide-eyebrow">Placement Test</p><h1>Diagnostic Assessment</h1><p>Get an honest baseline across the entire blueprint. Questions are balanced across domains instead of pulled as a single random bucket.</p>${toolbar(cert.id, "diagnostic")}</section><section class="guide-section"><div class="guide-metric-grid">${metric("Questions", String(questionCount), "Balanced across domains")}${metric("Time", "Untimed", "Accuracy before speed")}${metric("Coverage", `${(cert.domains || []).length} domains`, "Whole blueprint")}${metric("Result", "Per domain", "Weakest areas first")}</div></section><section class="guide-section"><div class="guide-domain-grid">${(cert.domains || []).map((domain) => `<div class="guide-domain-card"><span class="guide-weight">${Number(domain.weight || 0)}%</span><h3>${escapeHtml(domain.title)}</h3><p>${(domain.skills || []).length} task statements</p></div>`).join("")}</div></section><section class="guide-section"><a class="guide-button blue" href="#/practice?track_id=${encodeURIComponent(cert.id)}&mode=diagnostic&count=${questionCount}">Start Diagnostic</a></section></main>`;
}

async function renderDrill(container, trackId, params = {}) {
  const { cert } = await guideContext(trackId);
  const mastery = await getSkillMastery({ track_id: cert.id }).catch(() => ({ skills: [] }));
  const skills = mastery.skills || [];
  const target = params.skill_id ? skills.find((x) => x.skill_id === params.skill_id) : null;
  const due = skills.filter((item) => Number(item.mastery_level || 0) < 4).sort((a, b) => Number(a.mastery_level || 0) - Number(b.mastery_level || 0));
  const hrefParams = new URLSearchParams({ track_id: cert.id, mode: "drill", count: "15" });
  if (params.skill_id) hrefParams.set("skill_id", params.skill_id);
  if (params.domain_id) hrefParams.set("domain_id", params.domain_id);
  container.innerHTML = `<main class="guide-page"><section class="guide-task-head"><p class="guide-eyebrow">Targeted Practice</p><h1>Drill Mode</h1><p>${target ? `This session targets ${escapeHtml(target.skill || target.skill_id)}.` : params.domain_id ? "This session targets the selected exam domain." : "The engine prioritizes weak mapped skills, missed questions, and under-practised task statements."}</p>${toolbar(cert.id, "drill")}</section><section class="guide-section"><div class="guide-metric-grid">${metric("Mastered", String(skills.filter((x) => Number(x.mastery_level || 0) >= 4).length), "Skills at accurate mastery")}${metric("Due", String(due.length), "Skills below target")}${metric("Session", "15 questions", "Short focused practice")}${metric("Target", target ? target.skill : params.domain_id || "Adaptive", "Selection strategy")}</div></section>${due.length ? `<section class="guide-section"><div class="guide-section-head"><div><p class="guide-eyebrow">Weakest tasks</p><h2>Start where evidence is thinnest.</h2></div></div><div class="guide-skill-list">${due.slice(0, 8).map((item) => `<a class="guide-skill-card" href="#/drill?track_id=${encodeURIComponent(cert.id)}&skill_id=${encodeURIComponent(item.skill_id)}&domain_id=${encodeURIComponent(item.domain_id || "")}"><span class="guide-skill-number">${item.mastery_level || 0}/7</span><div><h3>${escapeHtml(item.skill)}</h3><p>${item.attempts || 0} attempts · ${item.accuracy_pct || 0}% accuracy</p></div><span>Drill →</span></a>`).join("")}</div></section>` : ""}<section class="guide-section"><a class="guide-button blue" href="#/practice?${hrefParams.toString()}">Start Drill</a></section></main>`;
}

async function renderMock(container, trackId) {
  const { cert } = await guideContext(trackId);
  const simulation = cert.simulation || { quick_questions: 30, full_questions: 65, seconds_per_question: 120 };
  const quickMinutes = Math.ceil((simulation.quick_questions * simulation.seconds_per_question) / 60);
  const fullMinutes = Math.ceil((simulation.full_questions * simulation.seconds_per_question) / 60);
  container.innerHTML = `<main class="guide-page"><section class="guide-task-head"><p class="guide-eyebrow">Practice Examination · ${escapeHtml(cert.exam_code || "")}</p><h1>Mock Exam</h1><p>Blueprint-weighted question selection, timed pacing, review flags, free navigation, deferred explanations and persistent mock evidence.</p></section><section class="guide-section"><div class="guide-tool-grid">${toolCard("Quick Mock", `${simulation.quick_questions} questions · ${quickMinutes} min`, "A shorter timed readiness check between study sessions.", `#/practice?track_id=${cert.id}&mode=quick-mock&count=${simulation.quick_questions}`)}${toolCard("Full Mock", `${simulation.full_questions} questions · ${fullMinutes} min`, "Full certification-style pacing with weighted domain coverage.", `#/practice?track_id=${cert.id}&mode=full-mock&count=${simulation.full_questions}`)}</div></section><section class="guide-section"><div class="guide-content-block"><h2>Exam behavior</h2>${listHtml(["Questions are sampled according to configured exam-domain weights.", "Flag questions and navigate freely before submitting.", "Explanations remain hidden until the sitting ends.", "Completed mocks persist as readiness evidence."])}</div></section></main>`;
}

async function renderExercises(container, trackId) {
  const { cert } = await guideContext(trackId);
  const payload = await getLabs({ track_id: cert.id }).catch(() => ({ labs: [] }));
  const labs = payload.labs || payload.challenges || [];
  container.innerHTML = `<main class="guide-page"><section class="guide-task-head"><p class="guide-eyebrow">Hands-On Practice</p><h1>Build Exercises</h1><p>Validated labs appear here. Every written task also carries a built-in exercise even when a dedicated validator has not been authored yet.</p>${toolbar(cert.id, "exercises")}</section><section class="guide-section">${labs.length ? `<div class="guide-reference-grid">${labs.map((lab) => `<a class="guide-reference-card" href="#/labs?track_id=${encodeURIComponent(cert.id)}&lab_id=${encodeURIComponent(lab.id)}"><span class="guide-code">${escapeHtml(lab.difficulty || "Exercise")}</span><h3>${escapeHtml(lab.title || lab.name)}</h3><p>${escapeHtml(lab.scenario || lab.description || "Open the challenge workspace.")}</p><div class="guide-card-footer"><span>${lab.estimated_minutes || lab.minutes || 20} min</span><span>Open →</span></div></a>`).join("")}</div>` : `<div class="guide-empty">Use the Build Exercise section inside each task lesson; validated labs will appear here as they are added.</div>`}</section></main>`;
}

async function renderQuickReference(container, trackId, domainId) {
  const { cert } = await guideContext(trackId);
  const domains = domainId ? (cert.domains || []).filter((domain) => domain.id === domainId) : cert.domains || [];
  const lessons = await Promise.all(domains.flatMap((domain) => (domain.skills || []).map((skill) => getStudyLesson(skill.id, { track_id: cert.id }).catch(() => null))));
  const bySkill = new Map(lessons.filter(Boolean).map((item) => [item.skill.id, item.content]));
  container.innerHTML = `<main class="guide-page quick-reference-page"><section class="guide-task-head"><p class="guide-eyebrow">Final Review</p><h1>Quick Reference Sheets</h1><p>Print-friendly decision rules, key concepts and traps generated from the same canonical lessons you studied.</p>${toolbar(cert.id, "quick-reference")}<div class="guide-actions"><button class="guide-button secondary" type="button" data-print-reference>Print / Save PDF</button></div></section>${domains.map((domain) => `<section class="guide-section reference-sheet"><div class="guide-section-head"><div><p class="guide-eyebrow">${Number(domain.weight || 0)}% exam weight</p><h2>${escapeHtml(domain.title)}</h2></div></div><table class="guide-table"><thead><tr><th>Task</th><th>Key concept / decision</th><th>Exam traps</th></tr></thead><tbody>${(domain.skills || []).map((skill) => { const c = bySkill.get(skill.id) || {}; const decisions = (c.decision_rules || []).slice(0, 2).map((x) => `${x.when} → ${x.choose}`).join(" · "); return `<tr><td><a href="#/skill?track_id=${encodeURIComponent(cert.id)}&skill_id=${encodeURIComponent(skill.id)}"><strong>${escapeHtml(skill.title)}</strong></a></td><td>${escapeHtml(decisions || c.key_concept || skill.objective || "")}</td><td>${escapeHtml((c.trap_explanations || []).map((x) => x.trap).join(" · ") || (skill.exam_traps || []).join(" · "))}</td></tr>`; }).join("")}</tbody></table></section>`).join("")}</main>`;
  container.querySelector("[data-print-reference]")?.addEventListener("click", () => window.print());
}

async function renderGlossary(container, trackId, domainId) {
  const { cert } = await guideContext(trackId);
  const domains = domainId ? (cert.domains || []).filter((domain) => domain.id === domainId) : cert.domains || [];
  container.innerHTML = `<main class="guide-page"><section class="guide-task-head"><p class="guide-eyebrow">Look Up</p><h1>Glossary</h1><p>Search exam-oriented definitions and vocabulary, then jump directly to the task that teaches the concept.</p>${toolbar(cert.id, "glossary")}<label class="guide-glossary-search"><span class="sr-only">Search glossary</span><input type="search" placeholder="Search glossary..." data-glossary-search /></label></section><div data-glossary-list>${domains.map((domain) => `<section class="guide-section"><div class="guide-section-head"><div><p class="guide-eyebrow">${Number(domain.weight || 0)}%</p><h2>${escapeHtml(domain.title)}</h2></div></div>${(domain.skills || []).map((skill) => `<article class="guide-content-block" data-glossary-entry data-search="${escapeHtml([skill.title, skill.objective, ...(skill.aliases || [])].join(" ").toLowerCase())}"><h2>${escapeHtml(skill.title)}</h2><p class="guide-hero-copy">${escapeHtml(skill.objective || "")}</p><p><strong>Exam context:</strong> ${escapeHtml((skill.exam_traps || ["Know when this capability is the correct choice."])[0])}</p><p><strong>Terms:</strong> ${escapeHtml((skill.aliases || []).slice(0, 10).join(", "))}</p><p><a href="#/skill?track_id=${encodeURIComponent(cert.id)}&skill_id=${encodeURIComponent(skill.id)}">Study this lesson →</a></p></article>`).join("")}</section>`).join("")}</div></main>`;
  container.querySelector("[data-glossary-search]")?.addEventListener("input", (event) => { const query = String(event.target.value || "").trim().toLowerCase(); container.querySelectorAll("[data-glossary-entry]").forEach((entry) => { entry.hidden = Boolean(query) && !String(entry.dataset.search || "").includes(query); }); });
}

function renderMissing(container, title) { container.innerHTML = `<main class="guide-page"><div class="guide-empty"><strong>${escapeHtml(title)}</strong><p>Return to the curriculum and choose another item.</p></div></main>`; }
