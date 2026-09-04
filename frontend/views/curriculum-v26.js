export const VIEW_ID = "v26-curriculum";

import { escapeHtml, getSkillMap, getSkillSummary, getTaskProgress } from "../api.js";
import { activeTrack, setActiveTrack } from "../ui.js";
import { DOMAIN_COLORS, studyLayout } from "../components/study-shell.js";

export default async function mount(container, params = {}) {
  const trackId = params.track_id || activeTrack();
  const [map, progress, summary] = await Promise.all([
    getSkillMap(),
    getTaskProgress({ track_id: trackId }).catch(() => ({ completed_skill_ids: [] })),
    getSkillSummary({ track_id: trackId }).catch(() => ({ skills: [], domains: [] })),
  ]);
  const certs = map.certifications || [];
  const cert = certs.find((item) => item.id === trackId) || certs[0];
  if (!cert) throw new Error("Certification is not configured");
  setActiveTrack(cert.id);
  const completed = new Set(progress.completed_skill_ids || []);
  const domainEvidence = new Map((summary.domains || []).map((item) => [item.domain_id, item]));
  const skillEvidence = new Map((summary.skills || []).map((item) => [item.skill_id, item]));
  const path = (window.location.hash || "#/curriculum").split("?")[0];
  if (path === "#/domain") return renderDomain(container, cert, params.domain_id, completed, domainEvidence, skillEvidence);

  container.innerHTML = studyLayout(cert, "curriculum", `<a class="v26-study-back" href="#/home" aria-label="Back">‹</a><header class="v26-study-heading"><p class="v26-kicker">SnowPro Core · ${escapeHtml(cert.exam_code || "COF-C03")}</p><h1>SnowPro domain map</h1><p>Use the official blueprint as the syllabus, but let your own completion and practice evidence decide where to focus next. All nineteen task statements are visible here.</p></header><section class="v26-curriculum-list" aria-label="SnowPro Core exam domains">${(cert.domains || []).map((domain, index) => domainRow(cert, domain, index, completed, domainEvidence.get(domain.id) || {})).join("")}</section>`, "", completed);
  bindDomainRows(container);
}

function domainRow(cert, domain, index, completed, evidence) {
  const skills = domain.skills || [];
  const color = DOMAIN_COLORS[index % DOMAIN_COLORS.length];
  const indexLabel = String(index + 1).padStart(2, "0");
  const done = skills.filter((skill) => completed.has(skill.id)).length;
  const accuracy = Number(evidence.accuracy_pct || 0);
  const attempts = Number(evidence.attempts || 0);
  const next = done < skills.length ? "Continue lessons" : attempts && accuracy < 80 ? "Target weak tasks" : attempts ? "Maintain mastery" : "Add practice evidence";
  return `<section class="v26-domain-block" data-domain-row="${escapeHtml(domain.id)}"><header><div class="v26-domain-index"><i style="--domain:${color}"></i><strong>${indexLabel}</strong></div><div><span>${skills.length} task statement${skills.length === 1 ? "" : "s"} · ${attempts ? `${accuracy}% practice accuracy` : "no practice evidence"}</span><h2>${escapeHtml(domain.title)}</h2><p>${escapeHtml(domain.description || `Study the ${skills.length} task statements in this weighted exam domain.`)}</p><small>${escapeHtml(next)}</small></div><div class="v26-domain-progress"><strong>${Number(domain.weight || 0)}%</strong><span>${done}/${skills.length} complete</span><button type="button" data-domain-toggle aria-expanded="false" aria-label="Show tasks for ${escapeHtml(domain.title)}">⌄</button></div></header><div class="v26-task-rows" data-domain-tasks hidden>${skills.map((skill, skillIndex) => taskRow(cert, skill, index, skillIndex, completed)).join("")}</div></section>`;
}

function taskRow(cert, skill, domainIndex, skillIndex, completed) {
  const done = completed.has(skill.id);
  return `<a class="${done ? "completed" : ""}" href="#/skill?track_id=${encodeURIComponent(cert.id)}&skill_id=${encodeURIComponent(skill.id)}"><b>${escapeHtml(skill.task_code || `${domainIndex + 1}.${skillIndex + 1}`)}</b><span><strong>${escapeHtml(skill.title)}</strong><small>${done ? "Completed · open lesson or practise objective." : "Open written lesson and practise objective."}</small></span><em aria-label="${done ? "Completed" : "Study"}">${done ? "✓" : "Study →"}</em></a>`;
}

function bindDomainRows(container) {
  container.querySelectorAll("[data-domain-row]").forEach((row) => {
    const button = row.querySelector("[data-domain-toggle]");
    const tasks = row.querySelector("[data-domain-tasks]");
    button?.addEventListener("click", () => {
      const opening = tasks.hidden;
      tasks.hidden = !opening;
      button.setAttribute("aria-expanded", String(opening));
      button.textContent = opening ? "⌃" : "⌄";
    });
  });
}

function renderDomain(container, cert, domainId, completed, domainEvidence, skillEvidence) {
  const domains = cert.domains || [];
  let index = domains.findIndex((item) => item.id === domainId);
  if (index < 0) index = 0;
  const domain = domains[index];
  if (!domain) throw new Error("Domain not found");
  const skills = domain.skills || [];
  const done = skills.filter((skill) => completed.has(skill.id)).length;
  const evidence = domainEvidence.get(domain.id) || {};
  const accuracy = Number(evidence.accuracy_pct || 0);
  const attempts = Number(evidence.attempts || 0);
  const weak = skills.map((skill) => ({ skill, evidence: skillEvidence.get(skill.id) || {} })).filter((item) => Number(item.evidence.attempts || 0) > 0).sort((a, b) => Number(a.evidence.accuracy_pct || 0) - Number(b.evidence.accuracy_pct || 0))[0];
  const action = weak && Number(weak.evidence.accuracy_pct || 0) < 80
    ? { title: `Review ${weak.skill.task_code || "weak task"}: ${weak.skill.title}`, href: `#/skill?track_id=${encodeURIComponent(cert.id)}&skill_id=${encodeURIComponent(weak.skill.id)}`, detail: `${Number(weak.evidence.accuracy_pct || 0)}% accuracy across ${Number(weak.evidence.attempts || 0)} attempts` }
    : done < skills.length
      ? { title: "Continue the next incomplete lesson", href: `#/skill?track_id=${encodeURIComponent(cert.id)}&skill_id=${encodeURIComponent((skills.find((skill) => !completed.has(skill.id)) || skills[0]).id)}`, detail: `${done}/${skills.length} tasks complete` }
      : { title: "Validate this domain with targeted practice", href: `#/practice?track_id=${encodeURIComponent(cert.id)}&mode=drill&domain_id=${encodeURIComponent(domain.id)}`, detail: attempts ? `${accuracy}% current practice accuracy` : "No practice evidence yet" };

  container.innerHTML = studyLayout(cert, domain.id, `<a class="v26-study-back" href="#/curriculum?track_id=${encodeURIComponent(cert.id)}" aria-label="Back to Exam Domains">‹</a><header class="v26-domain-heading"><div class="v26-domain-eyebrow"><i style="--domain:${DOMAIN_COLORS[index % DOMAIN_COLORS.length]}"></i><span>Domain ${index + 1}</span><strong>${Number(domain.weight || 0)}%</strong></div><h1>${escapeHtml(domain.title)}</h1><p>${escapeHtml(domain.description || "Master every task statement in this exam domain.")}</p></header><section class="v26-learning-command"><div><span>Completion</span><strong>${done}/${skills.length}</strong><small>Task statements</small></div><div><span>Practice</span><strong>${attempts ? `${accuracy}%` : "—"}</strong><small>${attempts ? `${attempts} attempts` : "No evidence yet"}</small></div><div><span>Exam weight</span><strong>${Number(domain.weight || 0)}%</strong><small>Blueprint emphasis</small></div><div><span>Next action</span><strong>→</strong><a href="${action.href}">${escapeHtml(action.title)}</a></div></section><section class="v26-progress-section"><div class="v26-section-heading"><p class="v26-kicker">Recommended next action</p><h2>${escapeHtml(action.title)}</h2><p>${escapeHtml(action.detail)}</p></div><div class="v26-inline-actions"><a class="v26-btn primary" href="${action.href}">Start next action</a><a class="v26-btn secondary" href="#/practice?track_id=${encodeURIComponent(cert.id)}&mode=drill&domain_id=${encodeURIComponent(domain.id)}">Drill this domain</a><a class="v26-btn secondary" href="#/glossary?track_id=${encodeURIComponent(cert.id)}">Open glossary</a><a class="v26-btn secondary" href="#/exercises?track_id=${encodeURIComponent(cert.id)}">Build exercises</a></div></section><section class="v26-domain-task-section"><h2>Task Statements</h2><div class="v26-domain-task-rows">${skills.map((skill, skillIndex) => { const row = skillEvidence.get(skill.id) || {}; const practiced = Number(row.attempts || 0); return `<a class="${completed.has(skill.id) ? "completed" : ""}" href="#/skill?track_id=${encodeURIComponent(cert.id)}&skill_id=${encodeURIComponent(skill.id)}"><b>${escapeHtml(skill.task_code || `${index + 1}.${skillIndex + 1}`)}</b><span><strong>${escapeHtml(skill.title)}</strong><small>${practiced ? `${Number(row.accuracy_pct || 0)}% across ${practiced} attempts` : completed.has(skill.id) ? "Lesson complete · add practice evidence" : "Lesson incomplete"}</small></span><em aria-label="${completed.has(skill.id) ? "Completed" : "Open lesson"}">${completed.has(skill.id) ? "✓" : "→"}</em></a>`; }).join("")}</div></section>`, "", completed);
}
