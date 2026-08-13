export const VIEW_ID = "v26-curriculum";

import { escapeHtml, getSkillMap, getTaskProgress } from "../api.js";
import { activeTrack, setActiveTrack } from "../ui.js";

const COLORS = ["#e39a60", "#77a4d5", "#9b82cf", "#70af81", "#d16d68"];

export default async function mount(container, params = {}) {
  const trackId = params.track_id || activeTrack();
  const map = await getSkillMap();
  const certs = map.certifications || [];
  const cert = certs.find((item) => item.id === trackId) || certs[0];
  if (!cert) throw new Error("Certification is not configured");
  setActiveTrack(cert.id);
  const progress = await getTaskProgress({ track_id: cert.id }).catch(() => ({ completed_skill_ids: [] }));
  const complete = new Set(progress.completed_skill_ids || []);
  const path = (window.location.hash || "#/curriculum").split("?")[0];
  if (path === "#/domain") return renderDomain(container, cert, params.domain_id, complete);
  container.innerHTML = layout(cert, "curriculum", `<header class="v26-study-heading"><p class="v26-kicker">Exam syllabus · ${escapeHtml(cert.exam_code || "COF-C03")}</p><h1>Exam Domains</h1><p>The current certification blueprint is the study contract. Work through every task statement, then use practice evidence to decide what deserves another pass.</p></header><section class="v26-curriculum-list">${(cert.domains || []).map((domain, index) => domainBlock(cert, domain, index, complete)).join("")}</section>`);
  bindToggles(container);
}

function renderDomain(container, cert, domainId, complete) {
  const domains = cert.domains || [];
  let index = domains.findIndex((item) => item.id === domainId);
  if (index < 0) index = 0;
  const domain = domains[index];
  if (!domain) throw new Error("Domain not found");
  const skills = domain.skills || [];
  container.innerHTML = layout(cert, domain.id, `<a class="v26-back" href="#/curriculum?track_id=${encodeURIComponent(cert.id)}">← Exam Domains</a><header class="v26-study-heading"><p class="v26-kicker">Domain ${index + 1} · ${Number(domain.weight || 0)}%</p><h1>${escapeHtml(domain.title)}</h1><p>${escapeHtml(domain.description || "Master every task statement in this exam domain.")}</p><div class="v26-inline-actions"><a class="v26-btn primary" href="#/practice?track_id=${encodeURIComponent(cert.id)}&mode=drill&domain_id=${encodeURIComponent(domain.id)}">Drill this domain</a><a class="v26-btn secondary" href="#/quick-reference?track_id=${encodeURIComponent(cert.id)}&domain_id=${encodeURIComponent(domain.id)}">Quick reference</a></div></header><section class="v26-task-list">${skills.map((skill, skillIndex) => `<a href="#/skill?track_id=${encodeURIComponent(cert.id)}&skill_id=${encodeURIComponent(skill.id)}"><span>${index + 1}.${skillIndex + 1}</span><div><h2>${escapeHtml(skill.title)}</h2><p>${escapeHtml(skill.objective || "")}</p></div><em>${complete.has(skill.id) ? "✓ Complete" : "Study →"}</em></a>`).join("")}</section>`);
}

function domainBlock(cert, domain, index, complete) {
  const skills = domain.skills || [];
  const done = skills.filter((skill) => complete.has(skill.id)).length;
  const id = `v26-domain-${index}`;
  return `<article class="v26-domain-block"><header><div class="v26-domain-index" style="--domain:${COLORS[index % COLORS.length]}"><i></i><strong>${String(index + 1).padStart(2, "0")}</strong></div><div><span>${Number(domain.weight || 0)}% of exam</span><h2>${escapeHtml(domain.title)}</h2><p>${escapeHtml(domain.description || `${skills.length} task statements in this domain.`)}</p></div><div class="v26-domain-progress"><strong>${done}/${skills.length}</strong><span>complete</span><button type="button" data-domain-toggle="${id}" aria-expanded="true"><span>−</span></button></div></header><div class="v26-task-rows" id="${id}">${skills.map((skill, skillIndex) => `<a href="#/skill?track_id=${encodeURIComponent(cert.id)}&skill_id=${encodeURIComponent(skill.id)}"><b>${index + 1}.${skillIndex + 1}</b><span><strong>${escapeHtml(skill.title)}</strong><small>${escapeHtml(skill.objective || "")}</small></span><em>${complete.has(skill.id) ? "✓ Complete" : "Study →"}</em></a>`).join("")}</div></article>`;
}

function bindToggles(container) {
  container.querySelectorAll("[data-domain-toggle]").forEach((button) => button.addEventListener("click", () => {
    const target = container.querySelector(`#${button.dataset.domainToggle}`);
    const open = target.hidden;
    target.hidden = !open;
    button.setAttribute("aria-expanded", String(open));
    button.querySelector("span").textContent = open ? "−" : "+";
  }));
}

function layout(cert, active, body) {
  return `<div class="v26-study-layout">${sidebar(cert, active)}<main class="v26-study-content">${body}</main></div>`;
}

function sidebar(cert, active) {
  const domains = (cert.domains || []).map((domain, index) => `<a class="v26-side-domain ${active === domain.id ? "active" : ""}" href="#/domain?track_id=${encodeURIComponent(cert.id)}&domain_id=${encodeURIComponent(domain.id)}"><i style="--domain:${COLORS[index % COLORS.length]}"></i><b>${index + 1}</b><span>${escapeHtml(domain.title)}</span><em>${Number(domain.weight || 0)}%</em></a>`).join("");
  return `<aside class="v26-study-nav"><div class="v26-side-brand"><span>${escapeHtml(cert.exam_code || "COF-C03")}</span><strong>${escapeHtml(cert.title || "SnowPro Core")}</strong></div><div class="v26-side-group"><small>Study Tools</small>${side("#/progress", "Progress Dashboard", cert.id, active === "progress")}${side("#/practice?mode=drill", "Drill Mode", cert.id, false)}</div><div class="v26-side-group"><small>Curriculum</small>${side("#/curriculum", "Exam Domains", cert.id, active === "curriculum")}${domains}</div><div class="v26-side-group"><small>Practice</small>${side("#/exercises", "Build Exercises", cert.id, active === "exercises")}${side("#/practice?mode=diagnostic", "Diagnostic Test", cert.id, false)}</div><div class="v26-side-group"><small>Look Up</small>${side("#/quick-reference", "Quick Reference", cert.id, active === "quick-reference")}${side("#/glossary", "Glossary", cert.id, active === "glossary")}</div></aside>`;
}

function side(path, label, trackId, active) {
  const sep = path.includes("?") ? "&" : "?";
  return `<a class="${active ? "active" : ""}" href="${path}${sep}track_id=${encodeURIComponent(trackId)}">${escapeHtml(label)}</a>`;
}
