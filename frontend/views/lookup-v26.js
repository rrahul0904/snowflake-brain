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
  const entries = flatEntries(cert);
  container.innerHTML = studyLayout(cert, "quick-reference", `<a class="v26-study-back" href="#/curriculum?track_id=${encodeURIComponent(cert.id)}" aria-label="Back">‹</a><header class="v26-study-heading"><p class="v26-kicker">Fast lookup</p><h1>Quick Reference</h1><p>Search the SnowPro blueprint by task, concept, alias, or exam trap. Open a domain sheet when you need condensed decision rules and scenario reminders.</p></header><div class="v26-lookup-toolbar"><label><span class="sr-only">Search quick reference</span><input type="search" data-global-search placeholder="Search task, concept, or exam trap…" /></label><span>${entries.length} task references · ${(cert.domains || []).length} domains</span><a href="#/exam-traps?track_id=${encodeURIComponent(cert.id)}">Exam Trap Library →</a></div><section class="v26-lookup-card-grid" data-domain-grid>${domainCards(cert, "quick-reference")}</section><section class="v26-lookup-search-results" data-search-results hidden>${entries.map((entry) => searchResult(cert, entry, "quick-reference")).join("")}</section><section class="v26-lookup-note"><strong>Use reference after retrieval, not instead of it.</strong><p>Try to recall the rule first. Then use the sheet to verify the distinction and route back to a lesson or targeted drill if the concept is still fragile.</p></section>`, "", []);
  bindGlobalSearch(container);
}

function glossaryLanding(container, cert) {
  const entries = flatEntries(cert);
  container.innerHTML = studyLayout(cert, "glossary", `<a class="v26-study-back" href="#/curriculum?track_id=${encodeURIComponent(cert.id)}" aria-label="Back">‹</a><header class="v26-study-heading"><p class="v26-kicker">SnowPro terminology</p><h1>Glossary</h1><p>Search task vocabulary, aliases, and common confusions. Every result stays mapped to its domain and task so you can jump back into the lesson or practise the concept.</p></header><div class="v26-lookup-toolbar"><label><span class="sr-only">Search glossary</span><input type="search" data-global-search placeholder="Search Snowflake term or task…" /></label><span>${entries.length} task-centered entries</span><a href="#/quick-reference?track_id=${encodeURIComponent(cert.id)}">Quick Reference →</a></div><section class="v26-lookup-card-grid" data-domain-grid>${domainCards(cert, "glossary")}</section><section class="v26-lookup-search-results" data-search-results hidden>${entries.map((entry) => searchResult(cert, entry, "glossary")).join("")}</section><section class="v26-lookup-note"><strong>Exam-oriented definitions</strong><p>These entries use the configured certification task model. When a term needs deeper technical context, open the lesson and follow its source links.</p></section>`, "", []);
  bindGlobalSearch(container);
}

function flatEntries(cert) {
  return (cert.domains || []).flatMap((domain, domainIndex) => (domain.skills || []).map((skill) => ({
    ...skill,
    domain,
    domainIndex,
    search: [skill.title, skill.objective, ...(skill.aliases || []), ...(skill.exam_traps || [])].filter(Boolean).join(" ").toLowerCase(),
  })));
}

function searchResult(cert, entry, mode) {
  const confusion = (entry.exam_traps || [])[0] || "Review the task boundary and distinguish adjacent Snowflake capabilities.";
  return `<article data-global-entry data-searchtext="${escapeHtml(entry.search)}"><div><span style="--domain:${DOMAIN_COLORS[entry.domainIndex % DOMAIN_COLORS.length]}"></span><b>Domain ${entry.domainIndex + 1} · Task ${escapeHtml(entry.task_code || "")}</b><em>${Number(entry.domain.weight || 0)}%</em></div><h2>${escapeHtml(entry.title)}</h2><p>${escapeHtml(entry.objective || "Certification task concept")}</p><small><strong>Common confusion:</strong> ${escapeHtml(confusion)}</small><footer><a href="#/skill?track_id=${encodeURIComponent(cert.id)}&skill_id=${encodeURIComponent(entry.id)}">Lesson →</a><a href="#/practice?track_id=${encodeURIComponent(cert.id)}&mode=drill&skill_id=${encodeURIComponent(entry.id)}">Practice →</a><a href="#/${mode}?track_id=${encodeURIComponent(cert.id)}&domain_id=${encodeURIComponent(entry.domain.id)}">Domain ${mode === "glossary" ? "glossary" : "sheet"} →</a></footer></article>`;
}

function bindGlobalSearch(container) {
  const input = container.querySelector("[data-global-search]");
  const domainGrid = container.querySelector("[data-domain-grid]");
  const results = container.querySelector("[data-search-results]");
  input?.addEventListener("input", () => {
    const query = String(input.value || "").trim().toLowerCase();
    domainGrid.hidden = Boolean(query);
    results.hidden = !query;
    results.querySelectorAll("[data-global-entry]").forEach((entry) => { entry.hidden = !query || !entry.dataset.searchtext.includes(query); });
  });
}

function domainCards(cert, route) {
  return (cert.domains || []).map((domain, index) => `<a class="v26-lookup-card" href="#/${route}?track_id=${encodeURIComponent(cert.id)}&domain_id=${encodeURIComponent(domain.id)}"><div><i style="--domain:${DOMAIN_COLORS[index % DOMAIN_COLORS.length]}"></i><span>${Number(domain.weight || 0)}%</span></div><h2>Domain ${index + 1}: ${escapeHtml(domain.title)}</h2><p>${escapeHtml(domain.description || `${(domain.skills || []).length} exam tasks`)}</p><small>${(domain.skills || []).length} task references</small></a>`).join("");
}

async function quickReferenceDomain(container, cert, domainId) {
  const domain = (cert.domains || []).find((item) => item.id === domainId) || (cert.domains || [])[0];
  if (!domain) throw new Error("Domain not found");
  const lessons = await Promise.all((domain.skills || []).map(async (skill) => [skill.id, (await getStudyLesson(skill.id, { track_id: cert.id }).catch(() => ({ content: {} }))).content || {}]));
  const bySkill = new Map(lessons);
  const index = (cert.domains || []).findIndex((item) => item.id === domain.id);
  container.innerHTML = studyLayout(cert, domain.id, `<a class="v26-study-back" href="#/quick-reference?track_id=${encodeURIComponent(cert.id)}" aria-label="Back to Quick Reference">‹</a><header class="v26-domain-heading"><div class="v26-domain-eyebrow"><i style="--domain:${DOMAIN_COLORS[index % DOMAIN_COLORS.length]}"></i><span>Domain ${index + 1}</span><strong>${Number(domain.weight || 0)}%</strong></div><h1>${escapeHtml(domain.title)}</h1><p>Decision rules, exam traps, and task-level routes for fast review.</p></header><section class="v26-reference-sheet"><div>${(domain.skills || []).map((skill) => referenceRow(cert, skill, bySkill.get(skill.id) || {})).join("")}</div></section>`, "", []);
}

function referenceRow(cert, skill, content) {
  const decisions = (content.decision_rules || []).slice(0, 2).map((rule) => `${rule.when} → ${rule.choose}`).join(" · ");
  const traps = (content.trap_explanations || []).slice(0, 2).map((item) => item.trap).join(" · ") || (skill.exam_traps || []).slice(0, 2).join(" · ");
  return `<article class="v26-reference-row"><header><strong>${escapeHtml(skill.task_code || "Task")}</strong><span><b>${escapeHtml(skill.title)}</b><small>${escapeHtml(content.key_concept || skill.objective || "")}</small></span></header>${decisions ? `<p><b>Decision rule</b>${escapeHtml(decisions)}</p>` : ""}${traps ? `<p class="trap"><b>Exam trap</b>${escapeHtml(traps)}</p>` : ""}<footer><a href="#/skill?track_id=${encodeURIComponent(cert.id)}&skill_id=${encodeURIComponent(skill.id)}">Lesson →</a><a href="#/practice?track_id=${encodeURIComponent(cert.id)}&mode=drill&skill_id=${encodeURIComponent(skill.id)}">Practice →</a><a href="#/glossary?track_id=${encodeURIComponent(cert.id)}&domain_id=${encodeURIComponent(skill.domain_id || "")}">Glossary →</a></footer></article>`;
}

function glossaryDomain(container, cert, domainId) {
  const domain = (cert.domains || []).find((item) => item.id === domainId) || (cert.domains || [])[0];
  if (!domain) throw new Error("Domain not found");
  const index = (cert.domains || []).findIndex((item) => item.id === domain.id);
  const entries = domain.skills || [];
  container.innerHTML = studyLayout(cert, domain.id, `<a class="v26-study-back" href="#/glossary?track_id=${encodeURIComponent(cert.id)}" aria-label="Back to Glossary">‹</a><header class="v26-domain-heading"><div class="v26-domain-eyebrow"><i style="--domain:${DOMAIN_COLORS[index % DOMAIN_COLORS.length]}"></i><span>Glossary · Domain ${index + 1}</span><strong>${Number(domain.weight || 0)}%</strong></div><h1>${escapeHtml(domain.title)}</h1><p>Exam-oriented definitions, task context, and common confusion points.</p></header><label class="v26-search"><span class="sr-only">Search glossary</span><input type="search" data-search placeholder="Search this domain..." /></label><section class="v26-glossary">${entries.map((item) => glossaryEntry(cert, domain, item)).join("")}</section>`, "", []);
  container.querySelector("[data-search]")?.addEventListener("input", (event) => {
    const query = String(event.target.value || "").trim().toLowerCase();
    container.querySelectorAll("[data-entry]").forEach((entry) => { entry.hidden = Boolean(query) && !entry.dataset.searchtext.includes(query); });
  });
}

function glossaryEntry(cert, domain, item) {
  const aliases = item.aliases || [];
  const confusion = (item.exam_traps || [])[0] || "Distinguish this task from adjacent Snowflake capabilities by matching the exact scenario requirement.";
  const search = [item.title, item.objective, ...aliases, ...item.exam_traps || []].join(" ").toLowerCase();
  return `<article data-entry data-searchtext="${escapeHtml(search)}"><header><span>${escapeHtml(item.task_code || "Task")}</span><h2>${escapeHtml(item.title)}</h2></header><p><strong>Definition / exam context</strong>${escapeHtml(item.objective || "Task-aligned Snowflake concept")}</p><p><strong>Common confusion</strong>${escapeHtml(confusion)}</p>${aliases.length ? `<small><strong>Related terms:</strong> ${escapeHtml(aliases.slice(0, 8).join(" · "))}</small>` : ""}<footer><a href="#/skill?track_id=${encodeURIComponent(cert.id)}&skill_id=${encodeURIComponent(item.id)}">Related lesson →</a><a href="#/practice?track_id=${encodeURIComponent(cert.id)}&mode=drill&skill_id=${encodeURIComponent(item.id)}">Practice →</a><a href="#/exam-traps?track_id=${encodeURIComponent(cert.id)}&domain=${encodeURIComponent(domain.id)}">Exam traps →</a></footer></article>`;
}
