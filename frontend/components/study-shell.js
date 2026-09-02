import { escapeHtml } from "../api.js";

export const DOMAIN_COLORS = ["#29B5E8", "#6366F1", "#10B981", "#F59E0B", "#8B5CF6"];

export function studyLayout(cert, active, body, activeSkillId = "", completedSkillIds = []) {
  return `<div class="v26-study-layout">${studySidebar(cert, active, activeSkillId, completedSkillIds)}<main class="v26-study-content">${body}</main></div>`;
}

export function studySidebar(cert, active = "", activeSkillId = "", completedSkillIds = []) {
  const completed = completedSkillIds instanceof Set ? completedSkillIds : new Set(completedSkillIds || []);
  const activeDomain = (cert.domains || []).find((domain) =>
    domain.id === active || (domain.skills || []).some((skill) => skill.id === activeSkillId)
  );
  const domains = (cert.domains || []).map((domain, index) => {
    const expanded = activeDomain?.id === domain.id;
    const done = (domain.skills || []).filter((skill) => completed.has(skill.id)).length;
    const tasks = expanded ? `<div class="v26-side-tasks">${(domain.skills || []).map((skill, skillIndex) => taskLink(cert, skill, index, skillIndex, activeSkillId, completed)).join("")}</div>` : "";
    return `<div class="v26-side-domain-wrap"><a class="v26-side-domain ${expanded ? "active" : ""}" href="#/domain?track_id=${encodeURIComponent(cert.id)}&domain_id=${encodeURIComponent(domain.id)}"><i style="--domain:${DOMAIN_COLORS[index % DOMAIN_COLORS.length]}"></i><b>${String(index + 1).padStart(2, "0")}</b><span>${escapeHtml(domain.title)}${done ? `<small>${done}/${(domain.skills || []).length} complete</small>` : ""}</span><em>${expanded ? "⌃" : "⌄"}</em></a>${tasks}</div>`;
  }).join("");
  return `<aside class="v26-study-nav" aria-label="Study navigation">
    <div class="v26-side-group"><small>Study Tools</small>
      ${side("#/progress", "Progress Dashboard", cert.id, active === "progress")}
      ${side("#/adaptive", "Adaptive Readiness", cert.id, active === "adaptive")}
      ${side("#/practice?mode=srs", "Due Today", cert.id, active === "due")}
      ${side("#/mistakes", "Mistake Notebook", cert.id, active === "mistakes")}
      ${side("#/progress?section=confidence", "Confidence Calibration", cert.id, active === "confidence")}
      ${side("#/progress?section=plan", "Study Plan", cert.id, active === "plan")}
    </div>
    <div class="v26-side-group"><small>Curriculum</small>${domains}</div>
    <div class="v26-side-group"><small>Practice</small>
      ${side("#/practice?mode=diagnostic", "Diagnostic Assessment", cert.id, active === "diagnostic")}
      ${side("#/practice?mode=drill", "Targeted Drill", cert.id, active === "drill")}
      ${side("#/mock/start?type=weekly-mock", "Quick Mock", cert.id, active === "quick-mock")}
      ${side("#/mock/start?type=full-mock", "Full Mock", cert.id, active === "full-mock")}
      ${side("#/exercises", "Build Exercises", cert.id, active === "exercises")}
    </div>
    <div class="v26-side-group"><small>Look Up</small>
      ${side("#/quick-reference", "Quick Reference", cert.id, active === "quick-reference")}
      ${side("#/glossary", "Glossary", cert.id, active === "glossary")}
      ${side("#/exam-guide", "Exam Guide", cert.id, active === "exam-guide")}
    </div>
  </aside>`;
}

function taskLink(cert, skill, domainIndex, skillIndex, activeSkillId, completed) {
  const done = completed.has(skill.id);
  const status = done ? `<em class="v26-task-complete" aria-label="Completed" title="Completed">✓<span class="sr-only"> Completed</span></em>` : "";
  return `<a class="${activeSkillId === skill.id ? "active" : ""} ${done ? "completed" : ""}" data-sidebar-skill="${escapeHtml(skill.id)}" data-completed="${String(done)}" href="#/skill?track_id=${encodeURIComponent(cert.id)}&skill_id=${encodeURIComponent(skill.id)}"><b>${escapeHtml(skill.task_code || `${domainIndex + 1}.${skillIndex + 1}`)}</b><span>${escapeHtml(skill.title)}</span>${status}</a>`;
}

function side(path, label, trackId, active) {
  const sep = path.includes("?") ? "&" : "?";
  return `<a class="${active ? "active" : ""}" href="${path}${sep}track_id=${encodeURIComponent(trackId)}">${escapeHtml(label)}</a>`;
}
