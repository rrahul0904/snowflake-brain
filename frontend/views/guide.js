export const VIEW_ID = "certification-guide";

import {
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

const path = () => (window.location.hash || "#/home").split("?")[0];

export default async function mount(container, params = {}) {
  const trackId = params.track_id || activeTrack();
  setActiveTrack(trackId);
  const route = path();

  if (route === "#/home") return renderHome(container, trackId);
  if (route === "#/progress") return renderProgress(container, trackId);
  if (route === "#/domain") return renderDomain(container, trackId, params.domain_id);
  if (route === "#/skill") return renderSkill(container, trackId, params.skill_id);
  if (route === "#/diagnostic") return renderDiagnostic(container, trackId);
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

function toolbar(trackId, active = "") {
  const items = [
    ["curriculum", "Curriculum"],
    ["progress", "Progress"],
    ["diagnostic", "Diagnostic"],
    ["exercises", "Build Exercises"],
    ["quick-reference", "Quick Reference"],
    ["glossary", "Glossary"],
  ];
  return `<nav class="guide-toolbar" aria-label="Study tools">${items
    .map(([route, label]) => `<a class="${active === route ? "active" : ""}" href="#/${route}?track_id=${encodeURIComponent(trackId)}">${label}</a>`)
    .join("")}</nav>`;
}

function certificationDescription(cert) {
  const title = String(cert.title || "");
  if (/core/i.test(title)) return "Build practical command of Snowflake architecture, security, data movement, performance, collaboration, and platform operations.";
  if (/data engineer/i.test(title)) return "Prove advanced data engineering skills across ingestion, transformation, streaming, orchestration, scalability, and performance.";
  if (/architect/i.test(title)) return "Design secure, scalable end-to-end Snowflake architectures from source through consumption and data sharing.";
  if (/gen.?ai|cortex/i.test(title)) return "Prepare for Snowflake Gen AI capabilities, Cortex AI, LLM workloads, model operations, and production design patterns.";
  if (/snowpark/i.test(title)) return "Build and operate Snowpark applications with production-grade development, optimization, packaging, and deployment practices.";
  return "Study the mapped exam domains, prove skills through practice, and build evidence toward certification readiness.";
}

async function renderHome(container, trackId) {
  const { certs, cert } = await guideContext(trackId);
  let readiness = {};
  try { readiness = await getIntelligenceReadiness({ track_id: cert.id }); } catch { readiness = {}; }
  const domains = cert.domains || [];
  const skills = domains.reduce((sum, domain) => sum + (domain.skills || []).length, 0);

  container.innerHTML = `
    <main class="guide-page">
      <section class="guide-hero">
        <div>
          <p class="guide-kicker">Snowflake Certification Studio · ${escapeHtml(cert.exam_code || "Exam track")}</p>
          <h1>Practise until<br><em>you pass.</em></h1>
          <p class="guide-hero-copy">An exam-first Snowflake study system: learn the official skill blueprint, study your owned courses, drill weak areas, complete hands-on SQL challenges, and sit realistic mocks until the evidence says you are ready.</p>
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
            <div><span>Mapped skills</span><b>${skills}</b></div>
            <div><span>Readiness</span><b>${pct(readiness.readiness_score || 0)}%</b></div>
          </div>
        </aside>
      </section>

      <section class="guide-section">
        <div class="guide-section-head"><div><p class="guide-eyebrow">Choose your certification</p><h2>One studio. Every SnowPro path.</h2></div><p>Each certification has its own blueprint, skill graph, practice evidence, labs, readiness gate, and source content.</p></div>
        <div class="guide-cert-grid">
          ${certs.map((item) => {
            const skillCount = (item.domains || []).reduce((sum, domain) => sum + (domain.skills || []).length, 0);
            return `<a class="guide-cert-card" href="#/home?track_id=${encodeURIComponent(item.id)}">
              <div class="guide-card-top"><span class="guide-code">${escapeHtml(item.exam_code || "SnowPro")}</span><span>${item.id === cert.id ? "Selected" : "Open →"}</span></div>
              <h3>${escapeHtml(item.title || item.id)}</h3>
              <p>${escapeHtml(certificationDescription(item))}</p>
              <div class="guide-card-footer"><span>${(item.domains || []).length} domains</span><span>${skillCount} skills</span></div>
            </a>`;
          }).join("")}
        </div>
      </section>

      <section class="guide-section">
        <div class="guide-section-head"><div><p class="guide-eyebrow">Study system</p><h2>From baseline to exam-ready.</h2></div><p>Follow the same loop every time: diagnose, learn, practise, build, repair, simulate, and re-check readiness.</p></div>
        <div class="guide-tool-grid">
          ${toolCard("Diagnostic", "Find weak areas", "Balanced questions across the certification so you know where to start.", `#/diagnostic?track_id=${cert.id}`)}
          ${toolCard("Curriculum", "Study by exam domain", "Domains, task-level skills, source lessons, exam traps, and linked practice.", `#/curriculum?track_id=${cert.id}`)}
          ${toolCard("Drill", "Repair weak skills", "Short adaptive practice sessions with evidence flowing back into mastery.", `#/practice?track_id=${cert.id}`)}
          ${toolCard("Build", "Prove it hands-on", "Configuration-driven SQL and architecture challenges with check-by-check feedback.", `#/exercises?track_id=${cert.id}`)}
          ${toolCard("Mock Exam", "Rehearse exam conditions", "Timed exam behavior, review flags, navigation, deferred explanations, and scoring.", `#/practice?track_id=${cert.id}`)}
          ${toolCard("Progress", "Know when you are ready", "Readiness, domain blockers, repeated misses, labs, mock evidence, and next actions.", `#/progress?track_id=${cert.id}`)}
        </div>
      </section>
    </main>`;
}

function toolCard(kicker, title, body, href) {
  return `<a class="guide-tool-card" href="${href}"><span class="guide-code">${escapeHtml(kicker)}</span><h3>${escapeHtml(title)}</h3><p>${escapeHtml(body)}</p><div class="guide-card-footer"><span>Open workspace</span><span>→</span></div></a>`;
}

async function renderCurriculum(container, trackId) {
  const { cert } = await guideContext(trackId);
  const domains = cert.domains || [];
  container.innerHTML = `
    <main class="guide-page">
      <section class="guide-task-head">
        <p class="guide-eyebrow">Core syllabus · ${escapeHtml(cert.exam_code || "")}</p>
        <h1>Exam Domains</h1>
        <p>${escapeHtml(certificationDescription(cert))} Study time should follow domain importance, but readiness requires evidence across the whole blueprint.</p>
        ${toolbar(cert.id, "curriculum")}
      </section>
      <section class="guide-section">
        <div class="guide-domain-grid">
          ${domains.map((domain, index) => `<a class="guide-domain-card" href="#/domain?track_id=${encodeURIComponent(cert.id)}&domain_id=${encodeURIComponent(domain.id)}">
            <div class="guide-card-top"><span class="guide-weight">${Number(domain.weight || 0)}%</span><span>${String(index + 1).padStart(2, "0")}</span></div>
            <h3>${escapeHtml(domain.title)}</h3>
            <p>${escapeHtml(domain.description || `${(domain.skills || []).length} mapped exam skills and task statements.`)}</p>
            <div class="guide-card-footer"><span>${(domain.skills || []).length} task statements</span><span>Study domain →</span></div>
          </a>`).join("")}
        </div>
      </section>
      <section class="guide-section">
        <div class="guide-section-head"><div><p class="guide-eyebrow">Source archive</p><h2>Your owned courses remain available.</h2></div><p>The exam blueprint becomes the primary curriculum, while your local videos and transcripts remain the evidence-backed source material behind each skill.</p></div>
        <a class="guide-button secondary" href="#/archive?track_id=${encodeURIComponent(cert.id)}">Browse course archive</a>
      </section>
    </main>`;
}

async function renderDomain(container, trackId, domainId) {
  const { cert } = await guideContext(trackId);
  const domain = (cert.domains || []).find((item) => item.id === domainId) || (cert.domains || [])[0];
  if (!domain) return renderMissing(container, "Domain not found");
  container.innerHTML = `
    <main class="guide-page">
      <div class="guide-breadcrumbs"><a href="#/curriculum?track_id=${encodeURIComponent(cert.id)}">Curriculum</a> / ${escapeHtml(domain.title)}</div>
      <section class="guide-task-head">
        <p class="guide-eyebrow">Domain ${escapeHtml(domain.id)} · ${Number(domain.weight || 0)}%</p>
        <h1>${escapeHtml(domain.title)}</h1>
        <p>${escapeHtml(domain.description || `Master the task statements mapped to this ${Number(domain.weight || 0)}% portion of the certification blueprint.`)}</p>
        <div class="guide-actions"><a class="guide-button" href="#/practice?track_id=${encodeURIComponent(cert.id)}">Drill this certification</a><a class="guide-button secondary" href="#/quick-reference?track_id=${encodeURIComponent(cert.id)}&domain_id=${encodeURIComponent(domain.id)}">Quick reference</a></div>
      </section>
      <section class="guide-section">
        <div class="guide-section-head"><div><p class="guide-eyebrow">Task statements</p><h2>${(domain.skills || []).length} skills to prove</h2></div></div>
        <div class="guide-skill-list">${(domain.skills || []).map((skill, index) => `<a class="guide-skill-card" href="#/skill?track_id=${encodeURIComponent(cert.id)}&skill_id=${encodeURIComponent(skill.id)}">
          <span class="guide-skill-number">${String(index + 1).padStart(2, "0")}</span>
          <div><h3>${escapeHtml(skill.title)}</h3><p>${escapeHtml(skill.objective || "")}</p></div><span>Study →</span>
        </a>`).join("")}</div>
      </section>
    </main>`;
}

async function renderSkill(container, trackId, skillId) {
  const { cert } = await guideContext(trackId);
  const flat = (cert.domains || []).flatMap((domain) => (domain.skills || []).map((skill) => ({ ...skill, domain_id: domain.id, domain: domain.title, domain_weight: domain.weight })));
  const skill = flat.find((item) => item.id === skillId) || flat[0];
  if (!skill) return renderMissing(container, "Skill not found");
  const resources = await getSkillResources(skill.id, { track_id: cert.id, limit: 10 }).catch(() => ({ lessons: [], questions: [] }));
  const labsPayload = await getLabs({ track_id: cert.id }).catch(() => ({ labs: [] }));
  const labs = (labsPayload.labs || labsPayload.challenges || []).filter((lab) => !lab.skill_id || lab.skill_id === skill.id).slice(0, 5);
  const traps = skill.exam_traps || [];

  container.innerHTML = `
    <main class="guide-page">
      <div class="guide-breadcrumbs"><a href="#/curriculum?track_id=${encodeURIComponent(cert.id)}">Curriculum</a> / <a href="#/domain?track_id=${encodeURIComponent(cert.id)}&domain_id=${encodeURIComponent(skill.domain_id)}">${escapeHtml(skill.domain)}</a> / ${escapeHtml(skill.title)}</div>
      <section class="guide-task-head">
        <p class="guide-eyebrow">${escapeHtml(cert.exam_code || cert.id)} · ${escapeHtml(skill.domain)} · ${Number(skill.domain_weight || 0)}%</p>
        <h1>${escapeHtml(skill.title)}</h1>
        <p>${escapeHtml(skill.objective || "Study the concept, understand the decision rules, recognise exam traps, and prove it with practice evidence.")}</p>
        <div class="guide-actions"><a class="guide-button blue" href="#/practice?track_id=${encodeURIComponent(cert.id)}">Practise this track</a><a class="guide-button secondary" href="#/exercises?track_id=${encodeURIComponent(cert.id)}">Open labs</a></div>
      </section>
      <div class="guide-content-grid">
        <div>
          <section class="guide-content-block"><h2>What You Need to Know</h2><p class="guide-hero-copy">${escapeHtml(skill.objective || "")}</p></section>
          <section class="guide-content-block"><h2>Common Exam Traps</h2>${traps.length ? `<ul class="guide-trap-list">${traps.map((trap) => `<li>${escapeHtml(trap)}</li>`).join("")}</ul>` : `<div class="guide-empty">No explicit trap notes have been configured for this skill yet.</div>`}</section>
          <section class="guide-content-block"><h2>Source Lessons</h2>${(resources.lessons || []).length ? `<ul class="guide-link-list">${resources.lessons.map((lesson) => `<li><a href="#/lesson?track_id=${encodeURIComponent(cert.id)}&lesson_id=${encodeURIComponent(lesson.id)}"><strong>${escapeHtml(lesson.title)}</strong><br><small>${escapeHtml(lesson.course_title || "Local archive")}</small></a></li>`).join("")}</ul>` : `<div class="guide-empty">No source lesson is confidently linked to this skill yet.</div>`}</section>
          <section class="guide-content-block"><h2>Related Practice Evidence</h2>${(resources.questions || []).length ? `<ul class="guide-link-list">${resources.questions.slice(0, 6).map((question) => `<li><a href="#/practice?track_id=${encodeURIComponent(cert.id)}">${escapeHtml(question.question)}</a></li>`).join("")}</ul>` : `<div class="guide-empty">No mapped practice questions found yet.</div>`}</section>
        </div>
        <aside>
          <div class="guide-side-card"><h3>Exam context</h3><p>This task sits inside ${escapeHtml(skill.domain)}, weighted at ${Number(skill.domain_weight || 0)}% in the configured blueprint. Accuracy here contributes to domain and overall readiness evidence.</p></div>
          <div class="guide-side-card"><h3>Hands-on proof</h3>${labs.length ? `<ul class="guide-link-list">${labs.map((lab) => `<li><a href="#/exercises?track_id=${encodeURIComponent(cert.id)}">${escapeHtml(lab.title || lab.name || "Lab challenge")}</a></li>`).join("")}</ul>` : `<p>No dedicated lab is mapped yet. Use the SQL lab catalog for related practice.</p>`}</div>
          <div class="guide-side-card"><h3>Lookup terms</h3><p>${escapeHtml((skill.aliases || []).slice(0, 12).join(" · ") || skill.title)}</p></div>
        </aside>
      </div>
    </main>`;
}

async function renderProgress(container, trackId) {
  const { cert } = await guideContext(trackId);
  const [readiness, mastery, evidence] = await Promise.all([
    getIntelligenceReadiness({ track_id: cert.id }).catch(() => ({})),
    getSkillMastery({ track_id: cert.id }).catch(() => ({ domains: [], skills: [] })),
    getEvidenceAudit({ track_id: cert.id, limit: 10 }).catch(() => ({})),
  ]);
  const domainById = new Map((cert.domains || []).map((domain) => [domain.id, domain]));
  const domains = mastery.domains || [];
  container.innerHTML = `
    <main class="guide-page">
      <section class="guide-task-head"><p class="guide-eyebrow">${escapeHtml(cert.title)} · readiness dashboard</p><h1>Your Progress</h1><p>Readiness is based on demonstrated evidence, not page visits: question attempts, accuracy, mocks, labs, skill coverage, repeated mistakes, and the quality of the underlying skill mappings.</p>${toolbar(cert.id, "progress")}</section>
      <section class="guide-section guide-readiness">
        <div class="guide-score-card"><span>Exam readiness</span><div class="guide-score">${pct(readiness.readiness_score || 0)}</div><strong>${escapeHtml(statusLabel(readiness.status || "not_ready"))}</strong><p class="guide-score-status">Pass range ${escapeHtml((readiness.pass_probability_range || [0, 10]).join("–"))}%</p></div>
        <div class="guide-metric-grid">
          ${metric("Accuracy", `${pct(readiness.accuracy_pct || 0)}%`, `${readiness.attempts || 0} attempts`)}
          ${metric("Mock exams", `${readiness.mock_exam_attempts || 0}`, `Best ${readiness.best_mock_score || 0}%`)}
          ${metric("Labs proven", `${readiness.lab_passed || 0}/${readiness.lab_available || 0}`, "Hands-on evidence")}
          ${metric("Mapping trust", `${evidence.mapping_trust_score || 0}%`, evidence.mapping_trust_status || "Not audited")}
        </div>
      </section>
      <section class="guide-section"><div class="guide-section-head"><div><p class="guide-eyebrow">Domain progress</p><h2>Where the exam is strong or weak.</h2></div></div><div class="guide-domain-progress">
        ${domains.length ? domains.map((row) => {
          const domain = domainById.get(row.domain_id) || {};
          const masteryPct = pct((Number(row.avg_mastery || 0) / 7) * 100);
          return `<div class="guide-domain-row"><div><strong>${escapeHtml(row.domain || domain.title || row.domain_id)}</strong><br><small>${Number(domain.weight || 0)}% exam weight · ${row.blockers || 0} blockers</small></div><div class="guide-progress-bar"><i style="width:${masteryPct}%"></i></div><strong>${masteryPct}%</strong><small>${row.accuracy_pct || 0}% accuracy</small></div>`;
        }).join("") : `<div class="guide-empty">No mastery evidence yet. Start with the diagnostic.</div>`}
      </div></section>
      <section class="guide-section"><div class="guide-section-head"><div><p class="guide-eyebrow">Readiness blockers</p><h2>What keeps you from “ready”.</h2></div></div>${(readiness.blockers || []).length ? `<ul class="guide-blocker-list">${readiness.blockers.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>` : `<div class="guide-empty">No readiness blockers are currently reported.</div>`}</section>
      <section class="guide-section"><div class="guide-actions"><a class="guide-button blue" href="#/practice?track_id=${encodeURIComponent(cert.id)}">Continue practice</a><a class="guide-button secondary" href="#/diagnostic?track_id=${encodeURIComponent(cert.id)}">Retake diagnostic</a></div></section>
    </main>`;
}

function metric(label, value, detail) {
  return `<div class="guide-metric"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong><small>${escapeHtml(detail)}</small></div>`;
}

async function renderDiagnostic(container, trackId) {
  const { cert } = await guideContext(trackId);
  const plan = await getDiagnosticPlan({ track_id: cert.id, count: 30 }).catch(() => ({}));
  const questionCount = (plan.questions || plan.question_ids || []).length || Number(plan.count || 30);
  container.innerHTML = `
    <main class="guide-page">
      <section class="guide-task-head"><p class="guide-eyebrow">Placement test</p><h1>Diagnostic Assessment</h1><p>Identify strengths and weaknesses before studying. The diagnostic samples the certification broadly, then your mastery and readiness engines use the results to prioritize what to study next.</p>${toolbar(cert.id, "diagnostic")}</section>
      <section class="guide-section"><div class="guide-metric-grid">${metric("Questions", String(questionCount), "Across mapped domains")}${metric("Pressure", "Untimed", "Focus on honest answers")}${metric("Result", "By domain", "Weakest areas first")}${metric("Retakes", "Unlimited", "Track improvement")}</div></section>
      <section class="guide-section"><div class="guide-section-head"><div><p class="guide-eyebrow">Domains covered</p><h2>Balanced across the blueprint.</h2></div></div><div class="guide-domain-grid">${(cert.domains || []).map((domain) => `<div class="guide-domain-card"><span class="guide-weight">${Number(domain.weight || 0)}%</span><h3>${escapeHtml(domain.title)}</h3><p>${(domain.skills || []).length} mapped task statements</p></div>`).join("")}</div></section>
      <section class="guide-section"><a class="guide-button blue" href="#/practice?track_id=${encodeURIComponent(cert.id)}&mode=diagnostic">Start Diagnostic</a></section>
    </main>`;
}

async function renderExercises(container, trackId) {
  const { cert } = await guideContext(trackId);
  const payload = await getLabs({ track_id: cert.id }).catch(() => ({ labs: [] }));
  const labs = payload.labs || payload.challenges || [];
  const byDomain = new Map();
  for (const lab of labs) {
    const key = lab.domain_id || lab.domain || "Hands-on labs";
    if (!byDomain.has(key)) byDomain.set(key, []);
    byDomain.get(key).push(lab);
  }
  container.innerHTML = `
    <main class="guide-page">
      <section class="guide-task-head"><p class="guide-eyebrow">Hands-on practice</p><h1>Build Exercises</h1><p>Use Snowflake SQL and architecture challenges to turn conceptual knowledge into demonstrable skill evidence. The current runner validates locally and never sends SQL to a Snowflake account.</p>${toolbar(cert.id, "exercises")}</section>
      <section class="guide-section">${labs.length ? [...byDomain.entries()].map(([domain, items]) => `<div class="guide-content-block"><div class="guide-section-head"><div><p class="guide-eyebrow">${escapeHtml(domain)}</p><h2>${items.length} exercises</h2></div></div><div class="guide-reference-grid">${items.map((lab) => `<a class="guide-reference-card" href="#/reference?track_id=${encodeURIComponent(cert.id)}"><span class="guide-code">${escapeHtml(lab.difficulty || "Lab")}</span><h3>${escapeHtml(lab.title || lab.name || "Snowflake challenge")}</h3><p>${escapeHtml(lab.description || lab.instructions || "Open the lab workspace to complete this challenge.")}</p><div class="guide-card-footer"><span>${escapeHtml(lab.skill_id || "Skill practice")}</span><span>Open →</span></div></a>`).join("")}</div></div>`).join("") : `<div class="guide-empty">No configured labs were returned for this certification.</div>`}</section>
    </main>`;
}

async function renderQuickReference(container, trackId, domainId) {
  const { cert } = await guideContext(trackId);
  const domains = domainId ? (cert.domains || []).filter((domain) => domain.id === domainId) : (cert.domains || []);
  container.innerHTML = `
    <main class="guide-page">
      <section class="guide-task-head"><p class="guide-eyebrow">Final review</p><h1>Quick Reference</h1><p>Dense exam-review sheets generated from the certification skill map: core objectives, decision rules, aliases, and the exam traps you need to recognize quickly.</p>${toolbar(cert.id, "quick-reference")}</section>
      ${domains.map((domain) => `<section class="guide-section"><div class="guide-section-head"><div><p class="guide-eyebrow">${Number(domain.weight || 0)}% exam weight</p><h2>${escapeHtml(domain.title)}</h2></div></div><table class="guide-table"><thead><tr><th>Skill</th><th>What to know</th><th>Common exam traps</th></tr></thead><tbody>${(domain.skills || []).map((skill) => `<tr><td><a href="#/skill?track_id=${encodeURIComponent(cert.id)}&skill_id=${encodeURIComponent(skill.id)}"><strong>${escapeHtml(skill.title)}</strong></a></td><td>${escapeHtml(skill.objective || "")}</td><td>${escapeHtml((skill.exam_traps || []).join(" · ") || "No trap notes configured")}</td></tr>`).join("")}</tbody></table></section>`).join("")}
    </main>`;
}

async function renderGlossary(container, trackId, domainId) {
  const { cert } = await guideContext(trackId);
  const domains = domainId ? (cert.domains || []).filter((domain) => domain.id === domainId) : (cert.domains || []);
  container.innerHTML = `
    <main class="guide-page">
      <section class="guide-task-head"><p class="guide-eyebrow">Look up</p><h1>Glossary</h1><p>Key Snowflake concepts organised by certification domain. Each entry gives the exam-oriented definition, vocabulary aliases, and a direct path into the deeper skill page.</p>${toolbar(cert.id, "glossary")}</section>
      ${domains.map((domain) => `<section class="guide-section"><div class="guide-section-head"><div><p class="guide-eyebrow">Domain · ${Number(domain.weight || 0)}%</p><h2>${escapeHtml(domain.title)}</h2></div></div>${(domain.skills || []).map((skill) => `<div class="guide-content-block"><h2>${escapeHtml(skill.title)}</h2><p class="guide-hero-copy">${escapeHtml(skill.objective || "")}</p><p><strong>Exam context:</strong> ${escapeHtml((skill.exam_traps || ["Recognize the correct Snowflake feature, boundary, or decision rule in scenario questions."])[0])}</p><p><strong>See also:</strong> <a href="#/skill?track_id=${encodeURIComponent(cert.id)}&skill_id=${encodeURIComponent(skill.id)}">Study this skill</a>${(skill.aliases || []).length ? ` · ${escapeHtml((skill.aliases || []).slice(0, 8).join(", "))}` : ""}</p></div>`).join("")}</section>`).join("")}
    </main>`;
}

function renderMissing(container, title) {
  container.innerHTML = `<main class="guide-page"><div class="guide-empty"><strong>${escapeHtml(title)}</strong><p>Return to the curriculum and choose another item.</p></div></main>`;
}
