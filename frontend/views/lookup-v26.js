export const VIEW_ID = "v26-lookup";

import { escapeHtml, getSkillMap, getStudyLesson } from "../api.js";
import { activeTrack } from "../ui.js";

const COLORS = ["#c87966", "#859db8", "#c49a62", "#7b9e91", "#b97b82"];

export default async function mount(container, params = {}) {
  const trackId = params.track_id || activeTrack();
  const map = await getSkillMap();
  const cert = (map.certifications || []).find((item) => item.id === trackId) || (map.certifications || [])[0];
  if (!cert) throw new Error("Certification is not configured");
  const path = (window.location.hash || "#/quick-reference").split("?")[0];
  if (path === "#/glossary") return glossary(container, cert, params.domain_id);
  return quickReference(container, cert, params.domain_id);
}

async function quickReference(container, cert, domainId) {
  const domains = domainId ? (cert.domains || []).filter((domain) => domain.id === domainId) : cert.domains || [];
  const lessons = await Promise.all(domains.flatMap((domain) => (domain.skills || []).map(async (skill) => [skill.id, (await getStudyLesson(skill.id, { track_id: cert.id }).catch(() => ({ content: {} }))).content || {}])));
  const bySkill = new Map(lessons);
  container.innerHTML = `<div class="v26-study-layout">${sidebar(cert, "quick-reference")}<main class="v26-study-content"><header class="v26-study-heading"><p class="v26-kicker">Final Review</p><h1>Quick Reference</h1><p>Condensed decision rules, key concepts, and traps from the same task lessons you studied.</p><div class="v26-inline-actions"><button class="v26-btn secondary" type="button" data-print>Print / Save PDF</button></div></header>${domains.map((domain, index) => `<section class="v26-reference-sheet"><header><i style="--domain:${COLORS[index % 5]}"></i><div><span>${Number(domain.weight || 0)}% exam weight</span><h2>${escapeHtml(domain.title)}</h2></div></header><div>${(domain.skills || []).map((skill) => referenceRow(cert, skill, bySkill.get(skill.id) || {})).join("")}</div></section>`).join("")}</main></div>`;
  container.querySelector("[data-print]")?.addEventListener("click", () => window.print());
}

function referenceRow(cert, skill, content) {
  const decisions = (content.decision_rules || []).slice(0, 2).map((rule) => `${rule.when} → ${rule.choose}`).join(" · ");
  const traps = (content.trap_explanations || []).slice(0, 2).map((item) => item.trap).join(" · ") || (skill.exam_traps || []).slice(0, 2).join(" · ");
  return `<a href="#/skill?track_id=${encodeURIComponent(cert.id)}&skill_id=${encodeURIComponent(skill.id)}"><strong>${escapeHtml(skill.task_code || "Task")}</strong><span><b>${escapeHtml(skill.title)}</b><small>${escapeHtml(decisions || content.key_concept || skill.objective || "")}</small></span><em>${escapeHtml(traps)}</em></a>`;
}

async function glossary(container, cert, domainId) {
  const domains = domainId ? (cert.domains || []).filter((domain) => domain.id === domainId) : cert.domains || [];
  const entries = domains.flatMap((domain) => (domain.skills || []).map((skill) => ({ ...skill, domain_title: domain.title })));
  container.innerHTML = `<div class="v26-study-layout">${sidebar(cert, "glossary")}<main class="v26-study-content"><header class="v26-study-heading"><p class="v26-kicker">Look Up</p><h1>Glossary</h1><p>Search exam-oriented Snowflake concepts, then jump directly to the task that teaches them.</p><label class="v26-search"><span class="sr-only">Search glossary</span><input type="search" data-search placeholder="Search concepts, features, or tasks..." /></label></header><section class="v26-glossary">${entries.map((item) => `<a data-entry data-searchtext="${escapeHtml([item.title, item.objective, ...(item.aliases || [])].join(" ").toLowerCase())}" href="#/skill?track_id=${encodeURIComponent(cert.id)}&skill_id=${encodeURIComponent(item.id)}"><span>${escapeHtml(item.domain_title)}</span><h2>${escapeHtml(item.title)}</h2><p>${escapeHtml(item.objective || "")}</p><small>${escapeHtml((item.aliases || []).slice(0, 8).join(" · "))}</small></a>`).join("")}</section></main></div>`;
  container.querySelector("[data-search]")?.addEventListener("input", (event) => {
    const query = String(event.target.value || "").trim().toLowerCase();
    container.querySelectorAll("[data-entry]").forEach((entry) => { entry.hidden = Boolean(query) && !entry.dataset.searchtext.includes(query); });
  });
}

function sidebar(cert, active) {
  const domains = (cert.domains || []).map((domain, index) => `<a class="v26-side-domain" href="#/domain?track_id=${encodeURIComponent(cert.id)}&domain_id=${encodeURIComponent(domain.id)}"><i style="--domain:${COLORS[index % 5]}"></i><b>${index + 1}</b><span>${escapeHtml(domain.title)}</span><em>${Number(domain.weight || 0)}%</em></a>`).join("");
  return `<aside class="v26-study-nav" aria-label="Study navigation"><div class="v26-side-group"><small>Study Tools</small><a href="#/progress?track_id=${encodeURIComponent(cert.id)}">Progress Dashboard</a><a href="#/practice?track_id=${encodeURIComponent(cert.id)}&mode=drill">Drill Mode</a></div><div class="v26-side-group"><small>Curriculum</small><a href="#/curriculum?track_id=${encodeURIComponent(cert.id)}">Exam Domains</a>${domains}</div><div class="v26-side-group"><small>Practice</small><a href="#/exercises?track_id=${encodeURIComponent(cert.id)}">Build Exercises</a><a href="#/practice?track_id=${encodeURIComponent(cert.id)}&mode=diagnostic">Diagnostic Test</a></div><div class="v26-side-group"><small>Look Up</small><a class="${active === "quick-reference" ? "active" : ""}" href="#/quick-reference?track_id=${encodeURIComponent(cert.id)}">Quick Reference</a><a class="${active === "glossary" ? "active" : ""}" href="#/glossary?track_id=${encodeURIComponent(cert.id)}">Glossary</a></div></aside>`;
}
