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

  container.innerHTML = studyLayout(cert, "curriculum", `<a class="v26-study-back" href="#/home" aria-label="Back">‹</a><header class="v26-study-heading"><h1>Exam Domains</h1><p>The SnowPro Core blueprint is organized into five weighted domains. Each domain opens into the task statements you need to understand before moving into practice.</p></header><section class="v26-domain-card-grid">${(cert.domains || []).map((domain, index) => domainCard(cert, domain, index)).join("")}</section>`);
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

function domainCard(cert, domain, index) {
  return `<a class="v26-domain-card" href="#/domain?track_id=${encodeURIComponent(cert.id)}&domain_id=${encodeURIComponent(domain.id)}"><div><i style="--domain:${DOMAIN_COLORS[index % DOMAIN_COLORS.length]}"></i><span>${Number(domain.weight || 0)}%</span></div><h2>Domain ${index + 1}: ${escapeHtml(domain.title)}</h2><p>${escapeHtml(domain.description || `${(domain.skills || []).length} task statements in this domain.`)}</p></a>`;
}
