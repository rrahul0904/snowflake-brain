export const VIEW_ID = "v26-curriculum";

import { escapeHtml, getSkillMap } from "../api.js";
import { activeTrack, setActiveTrack } from "../ui.js";
import { DOMAIN_COLORS, studyLayout } from "../components/study-shell.js";

export default async function mount(container, params = {}) {
  const trackId = params.track_id || activeTrack();
  const map = await getSkillMap();
  const certs = map.certifications || [];
  const cert = certs.find((item) => item.id === trackId) || certs[0];
  if (!cert) throw new Error("Certification is not configured");
  setActiveTrack(cert.id);
  const path = (window.location.hash || "#/curriculum").split("?")[0];
  if (path === "#/domain") return renderDomain(container, cert, params.domain_id);

  container.innerHTML = studyLayout(cert, "curriculum", `<a class="v26-study-back" href="#/home" aria-label="Back">‹</a><header class="v26-study-heading"><p class="v26-kicker">SnowPro Core · ${escapeHtml(cert.exam_code || "COF-C03")}</p><h1>Exam Domains</h1><p>Follow the blueprint as a syllabus. Open a domain to reveal its task statements, then move into the written lesson when you are ready to study the objective in depth.</p></header><section class="v26-curriculum-list" aria-label="SnowPro Core exam domains">${(cert.domains || []).map((domain, index) => domainRow(cert, domain, index)).join("")}</section>`);
  bindDomainRows(container);
}

function domainRow(cert, domain, index) {
  const skills = domain.skills || [];
  const color = DOMAIN_COLORS[index % DOMAIN_COLORS.length];
  const indexLabel = String(index + 1).padStart(2, "0");
  return `<section class="v26-domain-block" data-domain-row="${escapeHtml(domain.id)}"><header><div class="v26-domain-index"><i style="--domain:${color}"></i><strong>${indexLabel}</strong></div><div><span>${skills.length} task statement${skills.length === 1 ? "" : "s"}</span><h2>${escapeHtml(domain.title)}</h2><p>${escapeHtml(domain.description || `Study the ${skills.length} task statements in this weighted exam domain.`)}</p></div><div class="v26-domain-progress"><strong>${Number(domain.weight || 0)}%</strong><span>Exam weight</span><button type="button" data-domain-toggle aria-expanded="false" aria-label="Show tasks for ${escapeHtml(domain.title)}">⌄</button></div></header><div class="v26-task-rows" data-domain-tasks hidden>${skills.map((skill, skillIndex) => `<a href="#/skill?track_id=${encodeURIComponent(cert.id)}&skill_id=${encodeURIComponent(skill.id)}"><b>${escapeHtml(skill.task_code || `${index + 1}.${skillIndex + 1}`)}</b><span><strong>${escapeHtml(skill.title)}</strong><small>Open written lesson and practice objective.</small></span><em>Study →</em></a>`).join("")}</div></section>`;
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

function renderDomain(container, cert, domainId) {
  const domains = cert.domains || [];
  let index = domains.findIndex((item) => item.id === domainId);
  if (index < 0) index = 0;
  const domain = domains[index];
  if (!domain) throw new Error("Domain not found");
  const skills = domain.skills || [];
  container.innerHTML = studyLayout(cert, domain.id, `<a class="v26-study-back" href="#/curriculum?track_id=${encodeURIComponent(cert.id)}" aria-label="Back to Exam Domains">‹</a><header class="v26-domain-heading"><div class="v26-domain-eyebrow"><i style="--domain:${DOMAIN_COLORS[index % DOMAIN_COLORS.length]}"></i><span>Domain ${index + 1}</span><strong>${Number(domain.weight || 0)}%</strong></div><h1>${escapeHtml(domain.title)}</h1><p>${escapeHtml(domain.description || "Master every task statement in this exam domain.")}</p></header><section class="v26-domain-task-section"><h2>Task Statements</h2><div class="v26-domain-task-rows">${skills.map((skill, skillIndex) => `<a href="#/skill?track_id=${encodeURIComponent(cert.id)}&skill_id=${encodeURIComponent(skill.id)}"><b>${escapeHtml(skill.task_code || `${index + 1}.${skillIndex + 1}`)}</b><span>${escapeHtml(skill.title)}</span><em>→</em></a>`).join("")}</div></section>`, "");
}
