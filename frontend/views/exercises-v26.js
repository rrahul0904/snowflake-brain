export const VIEW_ID = "v26-exercises";

import { escapeHtml, getSkillMap } from "../api.js";
import { activeTrack } from "../ui.js";
import { DOMAIN_COLORS, studyLayout } from "../components/study-shell.js";

export default async function mount(container, params = {}) {
  const trackId = params.track_id || activeTrack();
  const map = await getSkillMap();
  const cert = (map.certifications || []).find((item) => item.id === trackId) || (map.certifications || [])[0];
  if (!cert) throw new Error("Certification is not configured");

  container.innerHTML = studyLayout(cert, "exercises", `<a class="v26-study-back" href="#/curriculum?track_id=${encodeURIComponent(cert.id)}" aria-label="Back">‹</a><header class="v26-study-heading"><h1>Build Exercises</h1><p>Each task lesson includes a hands-on Snowflake exercise. Use these as small implementation projects to cement the concept behind each blueprint statement.</p></header><section class="v26-exercise-domain-list">${(cert.domains || []).map((domain, index) => domainSection(cert, domain, index)).join("")}</section>`);
}

function domainSection(cert, domain, index) {
  const skills = domain.skills || [];
  return `<article class="v26-exercise-domain"><header><i style="--domain:${DOMAIN_COLORS[index % DOMAIN_COLORS.length]}"></i><h2>Domain ${index + 1}: ${escapeHtml(domain.title)}</h2><span>${skills.length} exercises</span></header><div>${skills.map((skill, skillIndex) => `<a href="#/skill?track_id=${encodeURIComponent(cert.id)}&skill_id=${encodeURIComponent(skill.id)}">${escapeHtml(skill.task_code || `${index + 1}.${skillIndex + 1}`)} ${escapeHtml(skill.title)}</a>`).join("")}</div></article>`;
}
