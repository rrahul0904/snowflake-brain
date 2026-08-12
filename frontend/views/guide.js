export const VIEW_ID = "certification-guide";

import {
  api,
  escapeHtml,
  getDiagnosticPlan,
  getEvidenceAudit,
  getIntelligenceReadiness,
  getLabs,
  getSkillMap,
  getSkillMastery,
  getSkillResources,
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
  if (route === "#/drill") return renderDrill(container, trackId);
  if (route === "#/mock") return renderMock(container, trackId);
  if (route === "#/exercises") return renderExercises(container, trackId);
  if (route === "#/quick-reference") return renderQuickReference(container, trackId, params.domain_id);
  if (route === "#/glossary") return renderGlossary(container, trackId, params.domain_id);
  return renderCurriculum(container, trackId);
}

async function guideContext(trackId) {
  const map = await getSkillMap();
  const certs = map.certifications || [];
  const cert = certs.find((item) => item.id === trackId) || certs[0] || { id: trackId, title: trackId, domains: [] };
  return { map, certs, cert };
}

async function taskProgress(trackId) {
  return api(`/api/skills/task-progress?${new URLSearchParams({ track_id: trackId })}`).catch(() => ({
    total_tasks: 0,
    completed_tasks: 0,
    completed_skill_ids: [],
  }));
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
  return `<nav class="guide-toolbar" aria-label="Study tools">${items
    .map(([route, label]) => `<a class="${active === route ? "active" : ""}" href="#/${route}?track_id=${encodeURIComponent(trackId)}">${label}</a>`)
    .join("")}</nav>`;
}

function certificationDescription(cert) {
  const title = String(cert.title || "");
  if (/core/i.test(title)) return "Master the Snowflake platform fundamentals tested across architecture, security, data movement, performance, protection, and operations.";
  if (/data engineer/i.test(title)) return "Prepare for advanced Snowflake data engineering across ingestion, transformation, orchestration, streaming, scalability, and performance.";
  if (/architect/i.test(title)) return "Prepare to design secure, scalable end-to-end Snowflake architectures and make the right platform decisions under exam pressure.";
  if (/gen.?ai|cortex/i.test(title)) return "Prepare for Snowflake Gen AI, Cortex AI, retrieval, model use, governance, and production design decisions.";
  if (/snowpark/i.test(title)) return "Prepare for Snowpark development, optimization, packaging, deployment, and production application patterns.";
  return "Study the exam blueprint, practise the task statements, build hands-on confidence, and measure readiness until you are prepared to sit the exam.";
}

async function renderHome(container, trackId) {
  const { certs, cert } = await guideContext(trackId);
  const progress = await taskProgress(cert.id);
  const domains = cert.domains || [];
  const skills = domains.reduce((sum, domain) => sum + (domain.skills || []).length, 0);

  container.innerHTML = `
    <main class="guide-page">
      <section class="guide-hero">
        <div>
          <p class="guide-kicker">Snowflake Certified · ${escapeHtml(cert.exam_code || "Certification track")}</p>
          <h1>Practise until<br><em>you pass.</em></h1>
          <p class="guide-hero-copy">A complete Snowflake certification guide: learn every exam domain, complete task-level study lessons, drill weak areas, work through build exercises, sit timed mocks, and track your readiness.</p>
          <div class="guide-actions">
            <a class="guide-button blue" href="#/diagnostic?track_id=${encodeURIComponent(cert.id)}">Take diagnostic</a>
            <a class="guide-button secondary" href="#/curriculum?track_id=${encodeURIComponent(cert.id)}">Explore curriculum</a>
          </div>
          ${toolbar(cert.id)}
        </div>
        <aside class="guide-fact-card">
          <strong>${escapeHtml(cert.title || cert.id)}</strong>
          <div class="guide-facts">
            <div><span>Exam</span><b>${escapeHtml(cert.exam_code || "Configured")}</b></div>
            <div><span>Domains</span><b>${domains.length}</b></div>
            <div><span>Task statements</span><b>${skills}</b></div>
            <div><span>Completed</span><b>${progress.completed_tasks || 0}/${progress.total_tasks || skills}</b></div>
          </div>
        </aside>
      </section>

      <section class="guide-section">
        <div class="guide-section-head"><div><p class="guide-eyebrow">Choose your certification</p><h2>One guide. Every configured SnowPro path.</h2></div><p>Open a certification to see its exam blueprint, task statements, study tools, practice, and readiness tracking.</p></div>
        <div class="guide-cert-grid">
          ${certs.map((item) => {
            const skillCount = (item.domains || []).reduce((sum, domain) => sum + (domain.skills || []).length, 0);
            return `<a class="guide-cert-card" href="#/home?track_id=${encodeURIComponent(item.id)}">
              <div class="guide-card-top"><span class="guide-code">${escapeHtml(item.exam_code || "SnowPro")}</span><span>${item.id === cert.id ? "Selected" : "Open →"}</span></div>
              <h3>${escapeHtml(item.title || item.id)}</h3>
              <p>${escapeHtml(certificationDescription(item))}</p>
              <div class="guide-card-footer"><span>${(item.domains || []).length} domains</span><span>${skillCount} tasks</span></div>
            </a>`;
          }).join("")}
        </div>
      </section>

      <section class="guide-section">
        <div class="guide-section-head"><div><p class="guide-eyebrow">Study tools</p><h2>Everything needed to prepare.</h2></div><p>The workflow mirrors a serious certification guide: diagnose, learn, drill, build, simulate, review, repeat.</p></div>
        <div class="guide-tool-grid">
          ${toolCard("Diagnostic", "Find your weak areas", "A broad placement test with per-domain feedback before you begin studying.", `#/diagnostic?track_id=${cert.id}`)}
          ${toolCard("Curriculum", "Study every task statement", "Blueprint-driven written lessons, exam traps, scenarios, and exercises.", `#/curriculum?track_id=${cert.id}`)}
          ${toolCard("Drill", "Use spaced repetition", "Short repeated practice focused on the skills that still need work.", `#/drill?track_id=${cert.id}`)}
          ${toolCard("Build", "Apply the concepts", "Hands-on Snowflake SQL and architecture exercises with local validation.", `#/exercises?track_id=${cert.id}`)}
          ${toolCard("Mock Exam", "Rehearse the exam", "Quick and full-length timed sittings with flags, navigation, and post-submit review.", `#/mock?track_id=${cert.id}`)}
          ${toolCard("Reference", "Review before exam day", "Dense quick-reference sheets plus an exam-oriented glossary.", `#/quick-reference?track_id=${cert.id}`)}
        </div>
      </section>
    </main>`;
}

function toolCard(kicker, title, body, href) {
  return `<a class="guide-tool-card" href="${href}"><span class="guide-code">${escapeHtml(kicker)}</span><h3>${escapeHtml(title)}</h3><p>${escapeHtml(body)}</p><div class="guide-card-footer"><span>Open</span><span>→</span></div></a>`;
}

async function renderCurriculum(container, trackId) {
  const { cert } = await guideContext(trackId);
  const progress = await taskProgress(cert.id);
  const completed = new Set(progress.completed_skill_ids || []);
  const domains = cert.domains || [];
  container.innerHTML = `
    <main class="guide-page">
      <section class="guide-task-head">
        <p class="guide-eyebrow">Core syllabus · ${escapeHtml(cert.exam_code || "")}</p>
        <h1>Exam Domains</h1>
        <p>${escapeHtml(certificationDescription(cert))} The curriculum is organised by exam domain and task statement, not by source course.</p>
        ${toolbar(cert.id)}
      </section>
      <section class="guide-section">
        <div class="guide-domain-grid">
          ${domains.map((domain, index) => {
            const done = (domain.skills || []).filter((skill) => completed.has(skill.id)).length;
            return `<a class="guide-domain-card" href="#/domain?track_id=${encodeURIComponent(cert.id)}&domain_id=${encodeURIComponent(domain.id)}">
              <div class="guide-card-top"><span class="guide-weight">${Number(domain.weight || 0)}%</span><span>${String(index + 1).padStart(2, "0")}</span></div>
              <h3>${escapeHtml(domain.title)}</h3>
              <p>${escapeHtml(domain.description || `${(domain.skills || []).length} task statements covering this exam domain.`)}</p>
              <div class="guide-card-footer"><span>${done}/${(domain.skills || []).length} complete</span><span>Study domain →</span></div>
            </a>`;
          }).join("")}
        </div>
      </section>
    </main>`;
}

async function renderDomain(container, trackId, domainId) {
  const { cert } = await guideContext(trackId);
  const progress = await taskProgress(cert.id);
  const completed = new Set(progress.completed_skill_ids || []);
  const domains = cert.domains || [];
  const domainIndex = Math.max(0, domains.findIndex((item) => item.id === domainId));
  const domain = domains[domainIndex] || domains[0];
  if (!domain) return renderMissing(container, "Domain not found");
  container.innerHTML = `
    <main class="guide-page">
      <div class="guide-breadcrumbs"><a href="#/curriculum?track_id=${encodeURIComponent(cert.id)}">Learn</a> / ${escapeHtml(domain.title)}</div>
      <section class="guide-task-head">
        <p class="guide-eyebrow">Domain ${domainIndex + 1} · ${Number(domain.weight || 0)}%</p>
        <h1>${escapeHtml(domain.title)}</h1>
        <p>${escapeHtml(domain.description || `Master every task statement mapped to this ${Number(domain.weight || 0)}% portion of the certification blueprint.`)}</p>
        <div class="guide-actions"><a class="guide-button" href="#/drill?track_id=${encodeURIComponent(cert.id)}">Drill this track</a><a class="guide-button secondary" href="#/quick-reference?track_id=${encodeURIComponent(cert.id)}&domain_id=${encodeURIComponent(domain.id)}">Quick reference</a></div>
      </section>
      <section class="guide-section">
        <div class="guide-section-head"><div><p class="guide-eyebrow">Task Statements</p><h2>${(domain.skills || []).length} lessons</h2></div></div>
        <div class="guide-skill-list">${(domain.skills || []).map((skill, index) => `<a class="guide-skill-card" href="#/skill?track_id=${encodeURIComponent(cert.id)}&skill_id=${encodeURIComponent(skill.id)}">
          <span class="guide-skill-number">${domainIndex + 1}.${index + 1}</span>
          <div><h3>${escapeHtml(skill.title)}</h3><p>${escapeHtml(skill.objective || "")}</p></div><span>${completed.has(skill.id) ? "✓ Complete" : "Study →"}</span>
        </a>`).join("")}</div>
      </section>
    </main>`;
}

function parseJson(value, fallback = []) {
  try {
    const parsed = typeof value === "string" ? JSON.parse(value) : value;
    return parsed ?? fallback;
  } catch {
    return fallback;
  }
}

function optionText(option) {
  if (typeof option === "string") return option;
  if (option && typeof option === "object") return option.text || option.label || option.value || JSON.stringify(option);
  return String(option ?? "");
}

function practiceScenario(question) {
  if (!question?.question) return `<div class="guide-empty">No mapped scenario question is available for this task yet.</div>`;
  const options = parseJson(question.options_json, []);
  const correct = parseJson(question.correct_json, []);
  return `<div class="guide-scenario" data-scenario data-correct="${escapeHtml(JSON.stringify(correct))}">
    <p>${escapeHtml(question.question)}</p>
    <div class="guide-options">${options.map((option, index) => `<label><input type="radio" name="scenario-answer" value="${index}" /> <span>${String.fromCharCode(65 + index)}. ${escapeHtml(optionText(option))}</span></label>`).join("")}</div>
    <button class="guide-button secondary" type="button" data-check-scenario>Check Answer</button>
    <div class="guide-answer" data-scenario-result hidden>${escapeHtml(question.explanation || "Review the task concepts and choose the option that best matches Snowflake behavior.")}</div>
  </div>`;
}

function lessonNarrative(skill) {
  const aliases = (skill.aliases || []).slice(0, 6);
  const cue = aliases.length ? `Key terms to recognise in scenarios include ${aliases.join(", ")}.` : "Focus on the boundaries, responsibilities, and decision rules expressed in the objective.";
  return `${skill.objective || "Understand this Snowflake capability and how it appears in certification scenarios."} ${cue}`;
}

function keyConcept(skill) {
  const firstTrap = (skill.exam_traps || [])[0];
  if (firstTrap) return `Know the correct Snowflake behavior well enough to reject this common distractor: ${firstTrap}`;
  return `The exam is testing whether you can apply ${skill.title} correctly in a scenario, not simply recognise the term.`;
}

async function renderSkill(container, trackId, skillId) {
  const { cert } = await guideContext(trackId);
  const progress = await taskProgress(cert.id);
  const completed = new Set(progress.completed_skill_ids || []);
  const flat = [];
  (cert.domains || []).forEach((domain, domainIndex) => {
    (domain.skills || []).forEach((skill, skillIndex) => flat.push({ ...skill, domain_id: domain.id, domain: domain.title, domain_weight: domain.weight, domain_index: domainIndex, skill_index: skillIndex }));
  });
  const index = Math.max(0, flat.findIndex((item) => item.id === skillId));
  const skill = flat[index] || flat[0];
  if (!skill) return renderMissing(container, "Task not found");
  const next = flat[index + 1];
  const resources = await getSkillResources(skill.id, { track_id: cert.id, limit: 8 }).catch(() => ({ questions: [] }));
  const labsPayload = await getLabs({ track_id: cert.id }).catch(() => ({ labs: [] }));
  const allLabs = labsPayload.labs || labsPayload.challenges || [];
  const labs = allLabs.filter((lab) => !lab.skill_id || lab.skill_id === skill.id).slice(0, 3);
  const primaryLab = labs[0];
  const traps = skill.exam_traps || [];
  const isComplete = completed.has(skill.id);
  const taskNumber = `${skill.domain_index + 1}.${skill.skill_index + 1}`;

  container.innerHTML = `
    <main class="guide-page">
      <div class="guide-breadcrumbs"><a href="#/curriculum?track_id=${encodeURIComponent(cert.id)}">Learn</a> / <a href="#/domain?track_id=${encodeURIComponent(cert.id)}&domain_id=${encodeURIComponent(skill.domain_id)}">${escapeHtml(skill.domain)}</a> / ${taskNumber}</div>
      <section class="guide-task-head">
        <div class="guide-task-meta"><span>Domain ${skill.domain_index + 1}</span><span>Task ${taskNumber}</span><span>${Number(skill.domain_weight || 0)}% domain weight</span></div>
        <button class="guide-complete-button ${isComplete ? "complete" : ""}" type="button" data-complete-task data-skill-id="${escapeHtml(skill.id)}">${isComplete ? "✓ Completed" : "Mark Complete"}</button>
        <h1>${escapeHtml(skill.title)}</h1>
      </section>

      <section class="guide-content-block">
        <h2>What You Need to Know</h2>
        <p class="guide-hero-copy">${escapeHtml(lessonNarrative(skill))}</p>
        <div class="guide-key-concept"><strong>Key Concept</strong><p>${escapeHtml(keyConcept(skill))}</p></div>
      </section>

      <section class="guide-content-block">
        <h2>Exam Traps</h2>
        ${traps.length ? `<div class="guide-trap-cards">${traps.map((trap) => `<article><span>Exam Trap</span><p>${escapeHtml(trap)}</p></article>`).join("")}</div>` : `<div class="guide-empty">No explicit trap notes are configured yet for this task.</div>`}
      </section>

      <section class="guide-content-block">
        <h2>Practice Scenario</h2>
        ${practiceScenario((resources.questions || [])[0])}
      </section>

      <section class="guide-content-block">
        <h2>Build Exercise</h2>
        ${primaryLab ? `<div class="guide-build-exercise"><span class="guide-code">${escapeHtml(primaryLab.difficulty || "Exercise")}</span><h3>${escapeHtml(primaryLab.title || primaryLab.name || "Snowflake build exercise")}</h3><p>${escapeHtml(primaryLab.scenario || primaryLab.description || primaryLab.why_it_matters || "Complete the hands-on Snowflake challenge and satisfy the validation checks.")}</p><div class="guide-card-footer"><span>${primaryLab.estimated_minutes || primaryLab.minutes || 20} minutes</span><a href="#/labs?track_id=${encodeURIComponent(cert.id)}&lab_id=${encodeURIComponent(primaryLab.id)}">Open exercise →</a></div></div>` : `<div class="guide-empty">A dedicated build exercise has not been mapped to this task yet.</div>`}
      </section>

      <section class="guide-content-block">
        <h2>Sources & Review</h2>
        <ul class="guide-link-list">
          <li><a href="https://docs.snowflake.com/" target="_blank" rel="noreferrer">Snowflake Documentation <small>Official product reference</small></a></li>
          <li><a href="#/quick-reference?track_id=${encodeURIComponent(cert.id)}&domain_id=${encodeURIComponent(skill.domain_id)}">Quick Reference <small>Domain-level final review</small></a></li>
          <li><a href="#/glossary?track_id=${encodeURIComponent(cert.id)}&domain_id=${encodeURIComponent(skill.domain_id)}">Glossary <small>Key terms and exam context</small></a></li>
        </ul>
      </section>

      <section class="guide-section"><div class="guide-actions"><a class="guide-button blue" href="#/drill?track_id=${encodeURIComponent(cert.id)}">Drill This Domain</a><button class="guide-button secondary" type="button" data-complete-task data-skill-id="${escapeHtml(skill.id)}">${isComplete ? "✓ Completed" : "Mark Complete"}</button></div></section>
      ${next ? `<a class="guide-next-task" href="#/skill?track_id=${encodeURIComponent(cert.id)}&skill_id=${encodeURIComponent(next.id)}"><span>Next Lesson</span><strong>${escapeHtml(next.title)}</strong><b>→</b></a>` : `<a class="guide-next-task" href="#/progress?track_id=${encodeURIComponent(cert.id)}"><span>Curriculum complete</span><strong>Review your progress</strong><b>→</b></a>`}
    </main>`;

  bindTaskPage(container, cert.id, skill.id, isComplete);
}

function bindTaskPage(container, trackId, skillId, initialComplete) {
  let complete = initialComplete;
  container.querySelectorAll("[data-complete-task]").forEach((button) => {
    button.addEventListener("click", async () => {
      complete = !complete;
      await api("/api/skills/task-progress", {
        method: "POST",
        body: JSON.stringify({ track_id: trackId, skill_id: skillId, completed: complete }),
      });
      container.querySelectorAll("[data-complete-task]").forEach((node) => {
        node.textContent = complete ? "✓ Completed" : "Mark Complete";
        node.classList.toggle("complete", complete);
      });
    });
  });

  container.querySelector("[data-check-scenario]")?.addEventListener("click", () => {
    const scenario = container.querySelector("[data-scenario]");
    const selected = scenario?.querySelector("input[name='scenario-answer']:checked");
    const result = scenario?.querySelector("[data-scenario-result]");
    if (!result) return;
    if (!selected) {
      result.hidden = false;
      result.innerHTML = "Choose an answer before checking.";
      return;
    }
    const correctRaw = parseJson(scenario.dataset.correct, []);
    const selectedIndex = Number(selected.value);
    const normalized = Array.isArray(correctRaw) ? correctRaw : [correctRaw];
    const isCorrect = normalized.some((value) => Number(value) === selectedIndex || String(value).toUpperCase() === String.fromCharCode(65 + selectedIndex));
    const explanation = result.textContent;
    result.hidden = false;
    result.innerHTML = `<strong>${isCorrect ? "Correct." : "Not quite."}</strong> ${escapeHtml(explanation)}`;
  });
}

async function renderProgress(container, trackId) {
  const { cert } = await guideContext(trackId);
  const [readiness, mastery, evidence, progress] = await Promise.all([
    getIntelligenceReadiness({ track_id: cert.id }).catch(() => ({})),
    getSkillMastery({ track_id: cert.id }).catch(() => ({ domains: [], skills: [] })),
    getEvidenceAudit({ track_id: cert.id, limit: 10 }).catch(() => ({})),
    taskProgress(cert.id),
  ]);
  const completed = new Set(progress.completed_skill_ids || []);
  const skills = mastery.skills || [];
  const questionsSeen = skills.reduce((sum, item) => sum + Number(item.attempts || 0), 0);
  const mastered = skills.filter((item) => Number(item.mastery_level || 0) >= 4).length;
  const due = skills.filter((item) => Number(item.mastery_level || 0) < 4).length;
  const taskPct = pct(((progress.completed_tasks || 0) / Math.max(1, progress.total_tasks || 1)) * 100);

  container.innerHTML = `
    <main class="guide-page">
      <section class="guide-task-head"><p class="guide-eyebrow">${escapeHtml(cert.title)}</p><h1>Your Progress</h1><p>Track completion, practice evidence, domain performance, and exam readiness across the full certification blueprint.</p>${toolbar(cert.id, "progress")}</section>
      <section class="guide-section guide-readiness">
        <div class="guide-score-card"><span>Exam Readiness</span><div class="guide-score">${pct(readiness.readiness_score || 0)}</div><strong>${escapeHtml(statusLabel(readiness.status || "not_ready"))}</strong></div>
        <div class="guide-metric-grid">
          ${metric("Lessons", `${taskPct}%`, `${progress.completed_tasks || 0}/${progress.total_tasks || 0} complete`)}
          ${metric("Practice", `${pct(readiness.accuracy_pct || 0)}%`, `${readiness.attempts || 0} attempts`)}
          ${metric("Mock Exams", `${readiness.mock_exam_attempts || 0}`, `Best ${readiness.best_mock_score || 0}%`)}
          ${metric("Mapping Trust", `${evidence.mapping_trust_score || 0}%`, evidence.mapping_trust_status || "Not audited")}
        </div>
      </section>
      <section class="guide-section"><div class="guide-section-head"><div><p class="guide-eyebrow">Domain Progress</p><h2>Task completion by domain.</h2></div></div><div class="guide-domain-progress">
        ${(cert.domains || []).map((domain) => {
          const total = (domain.skills || []).length;
          const done = (domain.skills || []).filter((skill) => completed.has(skill.id)).length;
          const value = pct((done / Math.max(1, total)) * 100);
          return `<a class="guide-domain-row" href="#/domain?track_id=${encodeURIComponent(cert.id)}&domain_id=${encodeURIComponent(domain.id)}"><div><strong>${escapeHtml(domain.title)}</strong><br><small>${done}/${total} lessons · ${Number(domain.weight || 0)}% exam weight</small></div><div class="guide-progress-bar"><i style="width:${value}%"></i></div><strong>${value}%</strong></a>`;
        }).join("")}
      </div></section>
      <section class="guide-section"><div class="guide-section-head"><div><p class="guide-eyebrow">Drill Summary</p><h2>Spaced-repetition evidence.</h2></div></div><div class="guide-metric-grid">${metric("Questions Seen", String(questionsSeen), "Across mapped tasks")}${metric("Mastered", String(mastered), "Skills at accurate mastery")}${metric("Due Today", String(due), "Skills still below mastery")}</div><div class="guide-actions"><a class="guide-button blue" href="#/drill?track_id=${encodeURIComponent(cert.id)}">Start Drill</a></div></section>
      ${(readiness.blockers || []).length ? `<section class="guide-section"><div class="guide-section-head"><div><p class="guide-eyebrow">Readiness blockers</p><h2>What still needs work.</h2></div></div><ul class="guide-blocker-list">${readiness.blockers.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul></section>` : ""}
    </main>`;
}

function metric(label, value, detail) {
  return `<div class="guide-metric"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong><small>${escapeHtml(detail)}</small></div>`;
}

async function renderDiagnostic(container, trackId) {
  const { cert } = await guideContext(trackId);
  const desired = Math.max(25, (cert.domains || []).length * 5);
  const plan = await getDiagnosticPlan({ track_id: cert.id, count: desired }).catch(() => ({}));
  const questionCount = (plan.questions || plan.question_ids || []).length || desired;
  container.innerHTML = `
    <main class="guide-page">
      <section class="guide-task-head"><p class="guide-eyebrow">Placement Test</p><h1>Diagnostic Assessment</h1><p>Identify strengths and weaknesses before you start studying. There is no timer pressure; the goal is to get an honest baseline across the exam blueprint.</p>${toolbar(cert.id, "diagnostic")}</section>
      <section class="guide-section"><div class="guide-metric-grid">${metric("Questions", String(questionCount), "Balanced across domains")}${metric("Time", "Untimed", "Work at your own pace")}${metric("Difficulty", "Mixed", "Recall, application, scenarios")}${metric("Result", "Per domain", "Weakest areas first")}</div></section>
      <section class="guide-section"><div class="guide-section-head"><div><p class="guide-eyebrow">Domains Covered</p><h2>The entire blueprint.</h2></div></div><div class="guide-domain-grid">${(cert.domains || []).map((domain) => `<div class="guide-domain-card"><span class="guide-weight">${Number(domain.weight || 0)}%</span><h3>${escapeHtml(domain.title)}</h3><p>${(domain.skills || []).length} task statements</p></div>`).join("")}</div></section>
      <section class="guide-section"><div class="guide-content-block"><h2>What to expect</h2><ul class="guide-trap-list"><li>No timer pressure — focus on honest answers, not speed.</li><li>Results feed your domain mastery and readiness evidence.</li><li>Retake the diagnostic later to measure improvement.</li></ul></div><a class="guide-button blue" href="#/practice?track_id=${encodeURIComponent(cert.id)}&mode=diagnostic&count=${questionCount}">Start Diagnostic</a></section>
    </main>`;
}

async function renderDrill(container, trackId) {
  const { cert } = await guideContext(trackId);
  const mastery = await getSkillMastery({ track_id: cert.id }).catch(() => ({ skills: [] }));
  const skills = mastery.skills || [];
  const questionsSeen = skills.reduce((sum, item) => sum + Number(item.attempts || 0), 0);
  const mastered = skills.filter((item) => Number(item.mastery_level || 0) >= 4).length;
  const due = skills.filter((item) => Number(item.mastery_level || 0) < 4).length;
  container.innerHTML = `
    <main class="guide-page">
      <section class="guide-task-head"><p class="guide-eyebrow">Study Tool</p><h1>Drill Mode</h1><p>Use repeated short practice sessions to reinforce weak concepts and move task statements from recognition to reliable recall.</p>${toolbar(cert.id, "drill")}</section>
      <section class="guide-section"><div class="guide-metric-grid">${metric("Questions Seen", String(questionsSeen), "Recorded attempts")}${metric("Mastered", String(mastered), "Skills at accurate mastery")}${metric("Due Today", String(due), "Skills still below target")}${metric("Session", "15 questions", "Fast targeted practice")}</div></section>
      <section class="guide-section"><div class="guide-content-block"><h2>How it works</h2><ul class="guide-trap-list"><li>Questions are drawn from the selected certification.</li><li>Missed concepts return to your repair queue and readiness blockers.</li><li>Use short sessions repeatedly instead of one long cram session.</li></ul></div><a class="guide-button blue" href="#/practice?track_id=${encodeURIComponent(cert.id)}&mode=drill&count=15">Start Drill</a></section>
    </main>`;
}

async function renderMock(container, trackId) {
  const { cert } = await guideContext(trackId);
  container.innerHTML = `
    <main class="guide-page">
      <section class="guide-task-head"><p class="guide-eyebrow">Practice Examination · ${escapeHtml(cert.exam_code || "")}</p><h1>Mock Exam</h1><p>Rehearse exam behavior with timed sittings, randomized questions, review flags, free navigation, deferred explanations, and score reporting.</p></section>
      <section class="guide-section"><div class="guide-section-head"><div><p class="guide-eyebrow">Choose Your Sitting</p><h2>Quick check or full simulation.</h2></div></div><div class="guide-tool-grid">
        ${toolCard("Quick Mock", "Readiness check", "A shorter timed sitting at certification pace. Use it between study sessions.", `#/practice?track_id=${cert.id}&mode=quick-mock&count=30`)}
        ${toolCard("Full Mock", "Exam simulation", "A longer timed sitting intended to rehearse pacing, review behavior, and endurance.", `#/practice?track_id=${cert.id}&mode=full-mock&count=65`)}
      </div></section>
      <section class="guide-section"><div class="guide-content-block"><h2>Before you start</h2><ul class="guide-trap-list"><li>Question order is randomized each attempt.</li><li>You can flag questions for review and navigate freely.</li><li>Explanations stay hidden until you submit.</li><li>Treat the result as a readiness gauge, not an official score predictor.</li></ul></div></section>
    </main>`;
}

async function renderExercises(container, trackId) {
  const { cert } = await guideContext(trackId);
  const payload = await getLabs({ track_id: cert.id }).catch(() => ({ labs: [] }));
  const labs = payload.labs || payload.challenges || [];
  const byDomain = new Map();
  for (const lab of labs) {
    const key = lab.domain || lab.domain_id || "Snowflake Build Exercises";
    if (!byDomain.has(key)) byDomain.set(key, []);
    byDomain.get(key).push(lab);
  }
  container.innerHTML = `
    <main class="guide-page">
      <section class="guide-task-head"><p class="guide-eyebrow">Hands-On Practice</p><h1>Build Exercises</h1><p>Each exercise turns a certification concept into something you configure, write, or reason through in a Snowflake challenge workspace.</p>${toolbar(cert.id, "exercises")}</section>
      <section class="guide-section">${labs.length ? [...byDomain.entries()].map(([domain, items]) => `<div class="guide-content-block"><div class="guide-section-head"><div><p class="guide-eyebrow">${escapeHtml(domain)}</p><h2>${items.length} exercises</h2></div></div><div class="guide-reference-grid">${items.map((lab) => `<a class="guide-reference-card" href="#/labs?track_id=${encodeURIComponent(cert.id)}&lab_id=${encodeURIComponent(lab.id)}"><span class="guide-code">${escapeHtml(lab.difficulty || "Exercise")}</span><h3>${escapeHtml(lab.title || lab.name || "Snowflake challenge")}</h3><p>${escapeHtml(lab.scenario || lab.description || lab.why_it_matters || "Open the challenge and complete the required Snowflake task.")}</p><div class="guide-card-footer"><span>${lab.estimated_minutes || lab.minutes || 20} min</span><span>Open →</span></div></a>`).join("")}</div></div>`).join("") : `<div class="guide-empty">No build exercises are configured for this certification yet.</div>`}</section>
    </main>`;
}

async function renderQuickReference(container, trackId, domainId) {
  const { cert } = await guideContext(trackId);
  const domains = domainId ? (cert.domains || []).filter((domain) => domain.id === domainId) : (cert.domains || []);
  container.innerHTML = `
    <main class="guide-page quick-reference-page">
      <section class="guide-task-head"><p class="guide-eyebrow">Final Review</p><h1>Quick Reference Sheets</h1><p>Dense, print-friendly review sheets for each exam domain: core concepts, task objectives, terminology, and common traps.</p>${toolbar(cert.id, "quick-reference")}<div class="guide-actions"><button class="guide-button secondary" type="button" data-print-reference>Print / Save PDF</button></div></section>
      ${domains.map((domain) => `<section class="guide-section reference-sheet"><div class="guide-section-head"><div><p class="guide-eyebrow">${Number(domain.weight || 0)}% exam weight</p><h2>${escapeHtml(domain.title)}</h2></div></div><table class="guide-table"><thead><tr><th>Task</th><th>What to know</th><th>Exam traps</th></tr></thead><tbody>${(domain.skills || []).map((skill) => `<tr><td><a href="#/skill?track_id=${encodeURIComponent(cert.id)}&skill_id=${encodeURIComponent(skill.id)}"><strong>${escapeHtml(skill.title)}</strong></a></td><td>${escapeHtml(skill.objective || "")}</td><td>${escapeHtml((skill.exam_traps || []).join(" · ") || "Review the feature boundary and decision rule.")}</td></tr>`).join("")}</tbody></table></section>`).join("")}
    </main>`;
  container.querySelector("[data-print-reference]")?.addEventListener("click", () => window.print());
}

async function renderGlossary(container, trackId, domainId) {
  const { cert } = await guideContext(trackId);
  const domains = domainId ? (cert.domains || []).filter((domain) => domain.id === domainId) : (cert.domains || []);
  container.innerHTML = `
    <main class="guide-page">
      <section class="guide-task-head"><p class="guide-eyebrow">Look Up</p><h1>Glossary</h1><p>Key Snowflake terms and definitions for the selected certification. Each entry includes exam context and a link back to the relevant task lesson.</p>${toolbar(cert.id, "glossary")}<label class="guide-glossary-search"><span class="sr-only">Search glossary</span><input type="search" placeholder="Search glossary..." data-glossary-search /></label></section>
      <div data-glossary-list>${domains.map((domain) => `<section class="guide-section" data-glossary-domain><div class="guide-section-head"><div><p class="guide-eyebrow">${Number(domain.weight || 0)}%</p><h2>${escapeHtml(domain.title)}</h2></div></div>${(domain.skills || []).map((skill) => `<article class="guide-content-block" data-glossary-entry data-search="${escapeHtml([skill.title, skill.objective, ...(skill.aliases || [])].join(" ").toLowerCase())}"><h2>${escapeHtml(skill.title)}</h2><p class="guide-hero-copy">${escapeHtml(skill.objective || "")}</p><p><strong>Exam context:</strong> ${escapeHtml((skill.exam_traps || ["Know when this Snowflake capability is the correct choice in a scenario."])[0])}</p><p><strong>See also:</strong> <a href="#/skill?track_id=${encodeURIComponent(cert.id)}&skill_id=${encodeURIComponent(skill.id)}">Study this lesson</a>${(skill.aliases || []).length ? ` · ${escapeHtml((skill.aliases || []).slice(0, 8).join(", "))}` : ""}</p></article>`).join("")}</section>`).join("")}</div>
    </main>`;
  container.querySelector("[data-glossary-search]")?.addEventListener("input", (event) => {
    const query = String(event.target.value || "").trim().toLowerCase();
    container.querySelectorAll("[data-glossary-entry]").forEach((entry) => {
      entry.hidden = Boolean(query) && !String(entry.dataset.search || "").includes(query);
    });
  });
}

function renderMissing(container, title) {
  container.innerHTML = `<main class="guide-page"><div class="guide-empty"><strong>${escapeHtml(title)}</strong><p>Return to the curriculum and choose another item.</p></div></main>`;
}
