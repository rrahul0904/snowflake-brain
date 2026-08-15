import { escapeHtml } from "../api.js";

export const DOMAIN_COLORS = ["#4b8fe8", "#2dbf8b", "#8057e8", "#f39a0a", "#e72765"];

export function studyLayout(cert, active, body, activeSkillId = "") {
  return `<div class="v26-study-layout">${studySidebar(cert, active, activeSkillId)}<main class="v26-study-content">${body}</main></div>`;
}

export function studySidebar(cert, active = "", activeSkillId = "") {
  const activeDomain = (cert.domains || []).find((domain) =>
    domain.id === active || (domain.skills || []).some((skill) => skill.id === activeSkillId)
  );
  const domains = (cert.domains || []).map((domain, index) => {
    const expanded = activeDomain?.id === domain.id;
    const tasks = expanded ? `<div class="v26-side-tasks">${(domain.skills || []).map((skill, skillIndex) => `<a class="${activeSkillId === skill.id ? "active" : ""}" href="#/skill?track_id=${encodeURIComponent(cert.id)}&skill_id=${encodeURIComponent(skill.id)}"><b>${escapeHtml(skill.task_code || `${index + 1}.${skillIndex + 1}`)}</b><span>${escapeHtml(skill.title)}</span></a>`).join("")}</div>` : "";
    return `<div class="v26-side-domain-wrap"><a class="v26-side-domain ${expanded ? "active" : ""}" href="#/domain?track_id=${encodeURIComponent(cert.id)}&domain_id=${encodeURIComponent(domain.id)}"><i style="--domain:${DOMAIN_COLORS[index % DOMAIN_COLORS.length]}"></i><b>${String(index + 1).padStart(2, "0")}</b><span>${escapeHtml(domain.title)}</span><em>${expanded ? "⌃" : "⌄"}</em></a>${tasks}</div>`;
  }).join("");
  return `<aside class="v26-study-nav" aria-label="Study navigation"><div class="v26-side-group"><small>Study Tools</small>${side("#/progress", "Progress Dashboard", cert.id, active === "progress")}${side("#/practice?mode=drill", "Drill Mode", cert.id, active === "drill")}</div><div class="v26-side-group"><small>Curriculum</small>${domains}</div><div class="v26-side-group"><small>Practice</small>${side("#/exercises", "Build Exercises", cert.id, active === "exercises")}${side("#/practice?mode=diagnostic", "Diagnostic Test", cert.id, active === "diagnostic")}</div><div class="v26-side-group"><small>Look Up</small>${side("#/quick-reference", "Quick Reference", cert.id, active === "quick-reference")}${side("#/glossary", "Glossary", cert.id, active === "glossary")}</div></aside>`;
}

function side(path, label, trackId, active) {
  const sep = path.includes("?") ? "&" : "?";
  return `<a class="${active ? "active" : ""}" href="${path}${sep}track_id=${encodeURIComponent(trackId)}">${escapeHtml(label)}</a>`;
}
