export const VIEW_ID = "v26-certifications";

import { escapeHtml, getCertificationCatalog } from "../api.js";
import { activeTrack } from "../ui.js";

export default async function mount(container) {
  const current = activeTrack();
  const payload = await getCertificationCatalog().catch(() => ({ official_certifications: [] }));
  const rows = payload.official_certifications || [];
  const currentRow = rows.find((item) => item.configured_track_id === current);
  const featured = [];
  if (currentRow) featured.push(currentRow);
  for (const item of rows) {
    if (featured.some((row) => row.exam_code === item.exam_code)) continue;
    featured.push(item);
    if (featured.length === 4) break;
  }
  const featuredCodes = new Set(featured.map((item) => item.exam_code));
  const more = rows.filter((item) => !featuredCodes.has(item.exam_code));

  container.innerHTML = `<main class="v26-page v26-certifications-page"><section class="v26-page-intro centered"><p class="v26-kicker">Snowflake certifications</p><h1>Choose your certification</h1><p>Pick the SnowPro path you are preparing for. Guides that are implemented here open immediately; every other official path remains clearly distinguished.</p></section><section class="v26-section"><div class="v26-cert-grid">${featured.map((item) => card(item, current)).join("") || fallback(current)}</div>${more.length ? `<details class="v26-more-paths"><summary>More SnowPro paths <span>${more.length}</span></summary><div class="v26-more-path-grid">${more.map((item) => morePath(item)).join("")}</div></details>` : ""}</section><section class="v26-section"><div class="v26-section-heading"><p class="v26-kicker">FAQ</p><h2>Choosing a SnowPro path</h2></div><div class="v26-faq-list">${faq("Where should I start?", "Start with SnowPro Core if you want the broad platform foundation before advanced or specialty preparation.")}${faq("Why are some paths marked coming soon?", "The certification may exist, but this product only marks a study guide available after its curriculum and practice experience are implemented.")}${faq("Can I switch later?", "Yes. The certification selector in the header keeps your active study track available across the site.")}</div></section></main>`;
  container.querySelectorAll(".v26-faq").forEach((item) => item.addEventListener("toggle", () => { const sign = item.querySelector("summary span"); if (sign) sign.textContent = item.open ? "−" : "+"; }));
}

function availability(item) {
  return Boolean(item.implemented && item.launchable && item.configured_track_id);
}

function card(item, current) {
  const available = availability(item);
  const selected = available && item.configured_track_id === current;
  const body = (item.overview || []).slice(0, 2).join(" ") || item.candidate_experience || "Snowflake certification study path.";
  const href = available ? `#/curriculum?track_id=${encodeURIComponent(item.configured_track_id)}` : "";
  return `<article class="v26-cert-card ${selected ? "selected" : ""}"><div class="v26-card-top"><span>${escapeHtml(item.exam_code || "SnowPro")}</span><b>${available ? (selected ? "CURRENT" : "AVAILABLE") : "SOON"}</b></div><h2>${escapeHtml(item.title || "SnowPro Certification")}</h2><p>${escapeHtml(body)}</p><dl><div><dt>Level</dt><dd>${escapeHtml(item.level || item.category || "Certification")}</dd></div><div><dt>Status</dt><dd>${available ? "Study guide available" : "Coming soon"}</dd></div></dl>${available ? `<a class="v26-card-action" href="${href}">${selected ? "Continue studying" : "Open certification"}<span>→</span></a>` : `<span class="v26-card-action disabled">Coming soon</span>`}</article>`;
}

function morePath(item) {
  const available = availability(item);
  const label = `<strong>${escapeHtml(item.title || "SnowPro Certification")}</strong><small>${escapeHtml(item.exam_code || "SnowPro")} · ${available ? "Guide available" : "Coming soon"}</small>`;
  return available ? `<a href="#/curriculum?track_id=${encodeURIComponent(item.configured_track_id)}">${label}<em>→</em></a>` : `<span>${label}<em>Soon</em></span>`;
}

function fallback(current) {
  return `<article class="v26-cert-card selected"><div class="v26-card-top"><span>COF-C03</span><b>CURRENT</b></div><h2>SnowPro Core Certification</h2><p>Foundational Snowflake architecture, governance, loading, performance, and collaboration.</p><a class="v26-card-action" href="#/curriculum?track_id=${encodeURIComponent(current || "snowpro-core")}">Continue studying <span>→</span></a></article>`;
}

function faq(question, answer) { return `<details class="v26-faq"><summary>${question}<span>+</span></summary><div><p>${answer}</p></div></details>`; }
