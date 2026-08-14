export const VIEW_ID = "v26-lookup";

import { escapeHtml, getSkillMap, getStudyLesson } from "../api.js";
import { activeTrack } from "../ui.js";
import { DOMAIN_COLORS, studyLayout } from "../components/study-shell.js";

export default async function mount(container, params = {}) {
  const trackId = params.track_id || activeTrack();
  const map = await getSkillMap();
  const cert = (map.certifications || []).find((item) => item.id === trackId) || (map.certifications || [])[0];
  if (!cert) throw new Error("Certification is not configured");
  const path = (window.location.hash || "#/quick-reference").split("?")[0];
  if (path === "#/glossary") return params.domain_id ? glossaryDomain(container, cert, params.domain_id) : glossaryLanding(container, cert);
  return params.domain_id ? quickReferenceDomain(container, cert, params.domain_id) : quickReferenceLanding(container, cert);
}

function quickReferenceLanding(container, cert) {
  container.innerHTML = studyLayout(cert, "quick-reference", `<a class="v26-study-back" href="#/curriculum?track_id=${encodeURIComponent(cert.id)}" aria-label="Back">‹</a><header class="v26-study-heading"><h1>Quick Reference Sheets</h1><p>Dense final-review sheets for each exam domain: core concepts, decision rules, common traps, and the terminology that matters most.</p></header><p class="v26-print-line">Print-friendly · use Ctrl+P / Cmd+P on any sheet</p><section class="v26-lookup-card-grid">${domainCards(cert, "quick-reference")}</section><section class="v26-lookup-note"><strong>How to use these sheets</strong><p>Review them after completing the lessons in a domain — they are summaries, not substitutes for the full content.</p><p>Focus on decision rules and exam traps during your final review.</p></section>`);
}

function glossaryLanding(container, cert) {
  container.innerHTML = studyLayout(cert, "glossary", `<a class="v26-study-back" href="#/curriculum?track_id=${encodeURIComponent(cert.id)}" aria-label="Back">‹</a><header class="v26-study-heading"><h1>Glossary</h1><p>Key Snowflake concepts for each exam domain. Each section keeps the definition close to the task where that concept is actually tested.</p></header><p class="v26-print-line">${(cert.domains || []).length} domains covered</p><section class="v26-lookup-card-grid">${domainCards(cert, "glossary")}</section><section class="v26-lookup-note"><strong>How to use this glossary</strong><p>Use the entries as a quick lookup while studying lessons or working through practice questions.</p><p>Then jump back into the relevant task when a term needs deeper context.</p></section>`);
}

function domainCards(cert, route) {
  return (cert.domains || []).map((domain, index) => `<a class="v26-lookup-card" href="#/${route}?track_id=${encodeURIComponent(cert.id)}&domain_id=${encodeURIComponent(domain.id)}"><div><i style="--domain:${DOMAIN_COLORS[index % DOMAIN_COLORS.length]}"></i><span>${Number(domain.weight || 0)}%</span></div><h2>Domain ${index + 1}: ${escapeHtml(domain.title)}</h2><p>${escapeHtml(domain.description || `${(domain.skills || []).length} exam tasks`)}</p></a>`).join("");
}

async function quickReferenceDomain(container, cert, domainId) {
  const domain = (cert.domains || []).find((item) => item.id === domainId) || (cert.domains || [])[0];
  if (!domain) throw new Error("Domain not found");
  const lessons = await Promise.all((domain.skills || []).map(async (skill) => [skill.id, (await getStudyLesson(skill.id, { track_id: cert.id }).catch(() => ({ content: {} }))).content || {}]));
  const bySkill = new Map(lessons);
  const index = (cert.domains || []).findIndex((item) => item.id === domain.id);
  container.innerHTML = studyLayout(cert, domain.id, `<a class="v26-study-back" href="#/quick-reference?track_id=${encodeURIComponent(cert.id)}" aria-label="Back to Quick Reference">‹</a><header class="v26-domain-heading"><div class="v26-domain-eyebrow"><i style="--domain:${DOMAIN_COLORS[index % DOMAIN_COLORS.length]}"></i><span>Domain ${index + 1}</span><strong>${Number(domain.weight || 0)}%</strong></div><h1>${escapeHtml(domain.title)}</h1><p>Final-review rules and traps distilled from the task lessons in this domain.</p></header><section class="v26-reference-sheet"><div>${(domain.skills || []).map((skill) => referenceRow(cert, skill, bySkill.get(skill.id) || {})).join("")}</div></section>`);
}

function referenceRow(cert, skill, content) {
  const decisions = (content.decision_rules || []).slice(0, 2).map((rule) => `${rule.when} → ${rule.choose}`).join(" · ");
  const traps = (content.trap_explanations || []).slice(0, 2).map((item) => item.trap).join(" · ") || (skill.exam_traps || []).slice(0, 2).join(" · ");
  return `<a href="#/skill?track_id=${encodeURIComponent(cert.id)}&skill_id=${encodeURIComponent(skill.id)}"><strong>${escapeHtml(skill.task_code || "Task")}</strong><span><b>${escapeHtml(skill.title)}</b><small>${escapeHtml(decisions || content.key_concept || skill.objective || "")}</small></span><em>${escapeHtml(traps)}</em></a>`;
}

function glossaryDomain(container, cert, domainId) {
  const domain = (cert.domains || []).find((item) => item.id === domainId) || (cert.domains || [])[0];
  if (!domain) throw new Error("Domain not found");
  const index = (cert.domains || []).findIndex((item) => item.id === domain.id);
  const entries = domain.skills || [];
  container.innerHTML = studyLayout(cert, domain.id, `<a class="v26-study-back" href="#/glossary?track_id=${encodeURIComponent(cert.id)}" aria-label="Back to Glossary">‹</a><header class="v26-domain-heading"><div class="v26-domain-eyebrow"><i style="--domain:${DOMAIN_COLORS[index % DOMAIN_COLORS.length]}"></i><span>Glossary · Domain ${index + 1}</span><strong>${Number(domain.weight || 0)}%</strong></div><h1>${escapeHtml(domain.title)}</h1><p>Exam-oriented terms and task context for this domain.</p></header><label class="v26-search"><span class="sr-only">Search glossary</span><input type="search" data-search placeholder="Search this domain..." /></label><section class="v26-glossary">${entries.map((item) => `<a data-entry data-searchtext="${escapeHtml([item.title, item.objective, ...(item.aliases || [])].join(" ").toLowerCase())}" href="#/skill?track_id=${encodeURIComponent(cert.id)}&skill_id=${encodeURIComponent(item.id)}"><span>${escapeHtml(item.task_code || "Task")}</span><h2>${escapeHtml(item.title)}</h2><p>${escapeHtml(item.objective || "")}</p><small>${escapeHtml((item.aliases || []).slice(0, 8).join(" · "))}</small></a>`).join("")}</section>`, "");
  container.querySelector("[data-search]")?.addEventListener("input", (event) => {
    const query = String(event.target.value || "").trim().toLowerCase();
    container.querySelectorAll("[data-entry]").forEach((entry) => { entry.hidden = Boolean(query) && !entry.dataset.searchtext.includes(query); });
  });
}
