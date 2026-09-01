export const VIEW_ID = "v26-certifications";

import { escapeHtml, getCertificationCatalog } from "../api.js";
import { activeTrack } from "../ui.js";

export default async function mount(container) {
  const current = activeTrack();
  const payload = await getCertificationCatalog().catch(() => ({ official_certifications: [] }));
  const rows = payload.official_certifications || [];
  const currentRow = rows.find((item) => item.configured_track_id === current) || rows.find((item) => item.id === "snowpro-core");
  const featured = [];
  if (currentRow) featured.push(currentRow);
  for (const item of rows) {
    if (featured.some((row) => row.exam_code === item.exam_code)) continue;
    featured.push(item);
    if (featured.length === 4) break;
  }
  const featuredCodes = new Set(featured.map((item) => item.exam_code));
  const more = rows.filter((item) => !featuredCodes.has(item.exam_code));

  container.innerHTML = `<main class="v26-page v26-certifications-page"><section class="v26-page-intro centered"><p class="v26-kicker">Snowflake certifications</p><h1>Choose your certification</h1><p>Compare verified public exam facts first. A certification can be active at Snowflake even when this product's study guide is still being authored and reviewed.</p></section><section class="v26-section"><div class="v26-cert-grid v26-cert-fact-grid">${featured.map((item) => card(item, current)).join("") || fallback(current)}</div>${more.length ? `<details class="v26-more-paths"><summary>More SnowPro paths <span>${more.length}</span></summary><div class="v26-more-path-grid">${more.map((item) => morePath(item)).join("")}</div></details>` : ""}</section><section class="v26-section"><div class="v26-section-heading"><p class="v26-kicker">How to read this catalog</p><h2>Official exam facts and product availability are different.</h2></div><div class="v26-faq-list">${faq("Does Available mean the Snowflake Brain guide is ready?", "No. Official certification status comes from Snowflake. Study-guide availability is a separate product state and is only marked available after the curriculum and practice experience are implemented.")}${faq("Why are some facts missing?", "We omit facts that were not verified from an authoritative Snowflake source. We do not infer question count, duration, item format, scoring, or effective dates from third-party sites.")}${faq("Where should I start?", "SnowPro Core is the currently implemented preparation track. You can still inspect public official facts for other focused certifications before their study guides launch.")}</div></section></main>`;
  container.querySelectorAll(".v26-faq").forEach((item) => item.addEventListener("toggle", () => { const sign = item.querySelector("summary span"); if (sign) sign.textContent = item.open ? "−" : "+"; }));
}

function availability(item) {
  return Boolean(item.implemented && item.launchable && item.configured_track_id);
}

function factRows(item) {
  const rows = [
    ["Level", item.level],
    ["Audience", item.audience || item.candidate_experience],
    ["Published items", item.item_count],
    ["Duration", item.duration_minutes ? `${item.duration_minutes} min` : null],
    ["Domains", item.domain_count],
    ["Guide version", item.guide_version],
    ["Effective", item.effective_date],
    ["Fee", Number.isFinite(Number(item.fee_usd)) ? `$${Number(item.fee_usd)}` : null],
  ].filter(([, value]) => value !== null && value !== undefined && value !== "");
  return rows.map(([label, value]) => `<div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd></div>`).join("");
}

function card(item, current) {
  const available = availability(item);
  const selected = available && item.configured_track_id === current;
  const body = (item.overview || []).slice(0, 2).join(" ") || item.candidate_experience || "Snowflake certification path.";
  const studyHref = available ? `#/curriculum?track_id=${encodeURIComponent(item.configured_track_id)}` : "";
  const guideHref = `#/exam-guide?track_id=${encodeURIComponent(item.id || item.configured_track_id || "snowpro-core")}`;
  const verified = item.source_verified_at ? `<small class="v26-fact-source">Facts checked ${escapeHtml(item.source_verified_at)}</small>` : "";
  return `<article class="v26-cert-card v26-cert-fact-card ${selected ? "selected" : ""}"><div class="v26-card-top"><span>${escapeHtml(item.exam_code || "SnowPro")}</span><b>${available ? (selected ? "GUIDE CURRENT" : "GUIDE AVAILABLE") : "GUIDE COMING SOON"}</b></div><h2>${escapeHtml(item.title || "SnowPro Certification")}</h2><p>${escapeHtml(body)}</p><dl class="v26-cert-facts">${factRows(item)}</dl>${verified}<div class="v26-cert-actions"><a class="v26-card-action" href="${guideHref}">Exam guide <span>→</span></a>${available ? `<a class="v26-card-action primary" href="${studyHref}">${selected ? "Continue studying" : "Open study guide"}<span>→</span></a>` : `<span class="v26-card-action disabled">Study guide coming soon</span>`}</div></article>`;
}

function morePath(item) {
  const available = availability(item);
  const label = `<strong>${escapeHtml(item.title || "SnowPro Certification")}</strong><small>${escapeHtml(item.exam_code || "SnowPro")} · ${available ? "Study guide available" : "Official certification · guide coming soon"}</small>`;
  return `<a href="#/exam-guide?track_id=${encodeURIComponent(item.id || item.configured_track_id || "snowpro-core")}">${label}<em>→</em></a>`;
}

function fallback(current) {
  return `<article class="v26-cert-card selected"><div class="v26-card-top"><span>COF-C03</span><b>GUIDE CURRENT</b></div><h2>SnowPro Core Certification</h2><p>Foundational Snowflake architecture, governance, loading, performance, and collaboration.</p><div class="v26-cert-actions"><a class="v26-card-action" href="#/exam-guide?track_id=snowpro-core">Exam guide <span>→</span></a><a class="v26-card-action primary" href="#/curriculum?track_id=${encodeURIComponent(current || "snowpro-core")}">Continue studying <span>→</span></a></div></article>`;
}

function faq(question, answer) { return `<details class="v26-faq"><summary>${question}<span>+</span></summary><div><p>${answer}</p></div></details>`; }
