import { escapeHtml, getCertificationCatalog } from "../api.js";

export const VIEW_ID = "claude-certification-guide-hub";

export default async function render(root, params = {}) {
  const track = params.track_id || "snowpro-core";
  const catalog = await getCertificationCatalog();
  const rows = catalog.official_certifications || [];
  const cert = rows.find((row) => row.id === track || row.configured_track_id === track)
    || rows.find((row) => row.id === "snowpro-core")
    || {};
  const domains = cert.exam_domains || [];
  const implemented = Boolean(cert.implemented && cert.launchable);
  const configuredTrack = cert.configured_track_id || cert.id || track;
  const sourceUrl = cert.official_exam_url || cert.source_url || "https://learn.snowflake.com/en/certifications/";
  const facts = [
    ["Exam code", cert.exam_code],
    ["Level", cert.level],
    ["Who it is for", cert.audience || cert.candidate_experience],
    ["Published items", cert.item_count],
    ["Item formats", Array.isArray(cert.item_formats) ? cert.item_formats.join(", ") : cert.item_formats],
    ["Time limit", cert.duration_minutes ? `${cert.duration_minutes} minutes` : null],
    ["Delivery", Array.isArray(cert.delivery) ? cert.delivery.join(" · ") : cert.delivery],
    ["Fee", Number.isFinite(Number(cert.fee_usd)) ? `$${Number(cert.fee_usd)} per attempt` : null],
    ["Credential validity", cert.credential_validity_months ? `${cert.credential_validity_months} months` : null],
    ["Guide version", cert.guide_version],
    ["Effective date", cert.effective_date],
    ["Domain count", cert.domain_count],
    ["Scoring", cert.scoring],
  ].filter(([, value]) => value !== null && value !== undefined && value !== "");
  const unknowns = Object.entries(cert.source_status || {})
    .filter(([, value]) => value === "not_verified")
    .map(([key]) => key.replaceAll("_", " "));

  root.innerHTML = `<main class="v26-page v26-info-page v26-exam-guide-page">
    <section class="v26-page-intro">
      <p class="v26-kicker">${escapeHtml(cert.exam_code || "SnowPro")} · Exam guide</p>
      <h1>${escapeHtml(cert.official_title || cert.title || "SnowPro certification")}</h1>
      <p>${escapeHtml((cert.overview || []).slice(0, 2).join(" ") || "Review source-verified public exam facts before building your preparation plan.")}</p>
      <p class="v26-exam-guide-note">Official Snowflake sources remain authoritative for registration, accommodations, scheduling, policy changes, and any fact not explicitly verified here.</p>
    </section>

    <section class="v26-info-copy">
      <div class="v26-exam-fact-grid">${facts.map(([label, value]) => `<div><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`).join("")}</div>
      ${unknowns.length ? `<div class="v26-source-caveat"><strong>Not guessed</strong><p>These fields are intentionally omitted because they were not verified from the authoritative source used in this release: ${escapeHtml(unknowns.join(", "))}.</p></div>` : ""}
      ${domains.length ? `<section class="v26-exam-domain-outline"><p class="v26-kicker">Blueprint map</p><h2>Weighted exam domains</h2>${domains.map((domain, index) => `<div class="v26-exam-domain-row"><span>${String(index + 1).padStart(2, "0")}</span><strong>${escapeHtml(domain.title || domain.name || "Exam domain")}</strong><em>${escapeHtml(domain.code || "")}</em><b>${Number(domain.weight || 0)}%</b></div>`).join("")}</section>` : ""}

      <section class="v26-how-to-prepare">
        <p class="v26-kicker">${implemented ? "Claude Certification Guide capability" : "Study guide coming soon"}</p>
        <h2>${implemented ? "Blueprint → task → lesson → trap → concept check → exam sim → build coach" : "Verified exam facts now; preparation content stays separate"}</h2>
        <p>${implemented ? "Snowflake Brain preserves the source-verified public exam guide, then hands authenticated candidates into the existing task lessons, exam traps, secure practice allocator, deterministic labs, timed mock player, quick reference, glossary, and freshness controls." : "Publishing verified public certification facts does not imply that a Snowflake Brain curriculum or private question bank exists for this certification."}</p>
        <div class="v26-how-to-actions">
          ${implemented ? `<a class="v26-btn primary" href="#/curriculum?track_id=${encodeURIComponent(configuredTrack)}">Open mapped tasks</a><a class="v26-btn secondary" href="#/practice?track_id=${encodeURIComponent(configuredTrack)}&mode=drill">Concept check</a><a class="v26-btn secondary" href="#/labs?track_id=${encodeURIComponent(configuredTrack)}">Build coach</a><a class="v26-btn secondary" href="#/mock?track_id=${encodeURIComponent(configuredTrack)}">Exam Sim</a><a class="v26-btn secondary" href="#/exam-traps?track_id=${encodeURIComponent(configuredTrack)}">Exam Traps</a><a class="v26-btn secondary" href="#/quick-reference?track_id=${encodeURIComponent(configuredTrack)}">Quick Reference</a><a class="v26-btn secondary" href="#/glossary?track_id=${encodeURIComponent(configuredTrack)}">Glossary</a>` : `<a class="v26-btn secondary" href="#/certifications">Compare certifications</a>`}
          <a class="v26-btn secondary" href="${escapeHtml(sourceUrl)}" target="_blank" rel="noopener noreferrer">Official Snowflake page ↗</a>
        </div>
      </section>

      <section class="v26-diagnostic-card">
        <p class="v26-kicker">Trust & freshness</p>
        <h2>Verified facts stay separate from authored preparation content.</h2>
        <p>Snowflake Brain keeps unknown exam facts unknown, monitors registered official-source freshness, and requires governed editorial review before private question releases can advance.</p>
        <a class="v26-btn secondary" href="#/content-integrity">Content integrity</a>
      </section>
      <p class="v26-fact-verification">Source verification: ${escapeHtml(cert.source_verified_at || "not recorded")}. Facts without verified source evidence are not displayed.</p>
    </section>
  </main>`;
}
