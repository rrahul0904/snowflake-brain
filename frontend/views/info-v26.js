export const VIEW_ID = "v26-info";

import { escapeHtml, getCertificationCatalog } from "../api.js";

const pages = {
  "#/about": {
    kicker: "About",
    title: "Built for deliberate SnowPro preparation.",
    body: [
      "Snowflake Certification Guide organizes study around the current certification blueprint instead of a course playlist.",
      "Learn task by task, practice the same objectives, rehearse timed sittings, and use progress evidence to decide what to review next.",
      "This is an independent preparation product. Snowflake and SnowPro identify the technology and certification programs we prepare for; they are not our brand or an endorsement."
    ]
  },
  "#/content-integrity": {
    kicker: "Content integrity",
    title: "Original preparation, traceable facts, no exam dumps.",
    body: [
      "The guide publishes independently authored certification-preparation material. We do not knowingly publish, solicit, buy, import, reconstruct, or train from live, leaked, stolen, recalled, or confidential certification exam questions or answer keys.",
      "Technical claims are grounded in lawful public sources, with Snowflake documentation and official certification pages preferred. Public facts are source-checked and unknown fields stay unknown rather than being inferred from third-party preparation sites.",
      "AI may assist drafting or quality checks, but generated text is not treated as provenance. Governed question releases preserve source references, structural QA, editorial review, version history, and a separate human SME approval boundary.",
      "Snowflake, SnowPro, and related marks belong to Snowflake Inc. or their respective owners. This independent service is not affiliated with, sponsored by, approved by, or endorsed by Snowflake Inc.",
      "Credible content, copyright, or factual-correction reports are reviewed against the relevant provenance and release record. Material may be quarantined or corrected while a report is investigated."
    ]
  },
  "#/terms": {
    kicker: "Terms",
    title: "Use the guide for legitimate certification preparation.",
    body: [
      "This service is an independent certification-preparation product. It is not Snowflake, is not endorsed by Snowflake, and does not provide real exam questions or guarantee certification results.",
      "Do not scrape, bulk-export, republish, resell, or use the private question bank to reconstruct assessment content. Automated access must respect authentication, entitlement, rate-limit, and security boundaries.",
      "Your account is for your own study use. Attempts to bypass access controls, share paid access, abuse the service, or upload malicious content may result in suspension."
    ]
  },
  "#/changelog": {
    kicker: "Changelog",
    title: "What changed in the guide.",
    body: [
      "V26 rebuilds the learner experience around a single curriculum, practice, reference, journal, and persisted mock-exam system.",
      "Production engineering adds PostgreSQL persistence, operational observability, account recovery and data controls, official-source freshness monitoring, version-bound editorial governance, evidence-based Adaptive Readiness, and a machine-verifiable reverse-engineering completeness gate."
    ]
  },
  "#/privacy": {
    kicker: "Privacy",
    title: "Your certification data stays under your control.",
    body: [
      "Your candidate account can store certification progress, practice attempts, mock-exam history, spaced-review state, mistake-notebook entries, study preferences, bookmarks, notes, and account activity in the configured application database.",
      "Signed-in candidates can export their portable study data and request permanent account deletion. Password material, action and session tokens, OAuth state, and provider payment identifiers are excluded from the candidate export.",
      "Permanent deletion removes candidate-linked attempts, exams, learning state, notes, feedback, and account records after required subscription checks. A random non-identifying deletion receipt may remain as operational proof that the request completed.",
      "Do not place credentials, secrets, payment data, or other sensitive information in free-text notes or feedback fields."
    ]
  }
};

export default async function mount(container, params = {}) {
  const path = params.__route || (window.location.hash || "#/about").split("?")[0];
  if (path === "#/exam-guide") {
    await examGuide(container, params.track_id || "snowpro-core");
    return;
  }
  const page = pages[path] || pages["#/about"];
  container.innerHTML = `<main class="v26-page v26-info-page"><section class="v26-page-intro"><p class="v26-kicker">${escapeHtml(page.kicker)}</p><h1>${escapeHtml(page.title)}</h1></section><section class="v26-info-copy">${page.body.map((item) => `<p>${escapeHtml(item)}</p>`).join("")}${path === "#/content-integrity" ? `<div class="v26-trust-actions"><a href="#/certifications">Review source-checked certification facts →</a><a href="#/privacy">Read privacy controls →</a></div>` : ""}</section></main>`;
}

async function examGuide(container, trackId) {
  const payload = await getCertificationCatalog().catch(() => ({ official_certifications: [] }));
  const rows = payload.official_certifications || [];
  const item = rows.find((row) => row.id === trackId || row.configured_track_id === trackId) || rows.find((row) => row.id === "snowpro-core") || {};
  const implemented = Boolean(item.implemented && item.launchable);
  const facts = [
    ["Exam code", item.exam_code],
    ["Level", item.level],
    ["Who it is for", item.audience || item.candidate_experience],
    ["Published items", item.item_count],
    ["Item formats", Array.isArray(item.item_formats) ? item.item_formats.join(", ") : item.item_formats],
    ["Time limit", item.duration_minutes ? `${item.duration_minutes} minutes` : null],
    ["Delivery", Array.isArray(item.delivery) ? item.delivery.join(" · ") : item.delivery],
    ["Fee", Number.isFinite(Number(item.fee_usd)) ? `$${Number(item.fee_usd)} per attempt` : null],
    ["Credential validity", item.credential_validity_months ? `${item.credential_validity_months} months` : null],
    ["Guide version", item.guide_version],
    ["Effective date", item.effective_date],
    ["Domain count", item.domain_count],
    ["Scoring", item.scoring],
  ].filter(([, value]) => value !== null && value !== undefined && value !== "");

  const policyFacts = [
    item.retake_wait_days ? `After a failed attempt, the verified policy requires a ${Number(item.retake_wait_days)}-day wait before retaking the same exam.` : null,
    item.retake_limit_per_12_months ? `The verified policy allows up to ${Number(item.retake_limit_per_12_months)} attempts of the same exam within a 12-month period.` : null,
    item.renewal_policy || null,
  ].filter(Boolean);

  const domains = item.exam_domains || [];
  const unknowns = Object.entries(item.source_status || {}).filter(([, value]) => value === "not_verified").map(([key]) => key.replaceAll("_", " "));
  const sourceUrl = item.official_exam_url || item.source_url || "https://learn.snowflake.com/en/certifications/";

  container.innerHTML = `<main class="v26-page v26-info-page v26-exam-guide-page">
    <section class="v26-page-intro">
      <p class="v26-kicker">${escapeHtml(item.exam_code || "SnowPro")} · Exam guide</p>
      <h1>${escapeHtml(item.official_title || item.title || "SnowPro certification")}</h1>
      <p>${escapeHtml((item.overview || []).slice(0, 2).join(" ") || "Review source-verified public exam facts before building your preparation plan.")}</p>
      <p class="v26-exam-guide-note">Official Snowflake sources remain authoritative for registration, accommodations, scheduling, policy changes, and any fact not explicitly verified here.</p>
    </section>
    <section class="v26-info-copy">
      <div class="v26-exam-fact-grid">${facts.map(([label, value]) => `<div><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`).join("")}</div>
      ${unknowns.length ? `<div class="v26-source-caveat"><strong>Not guessed</strong><p>These fields are intentionally omitted because they were not verified from the authoritative source used in this release: ${escapeHtml(unknowns.join(", "))}.</p></div>` : ""}
      ${domains.length ? `<section class="v26-exam-domain-outline"><p class="v26-kicker">Blueprint</p><h2>Weighted exam domains</h2>${domains.map((domain, index) => `<div class="v26-exam-domain-row"><span>${String(index + 1).padStart(2, "0")}</span><strong>${escapeHtml(domain.title)}</strong><em>${escapeHtml(domain.code || "")}</em><b>${Number(domain.weight || 0)}%</b></div>`).join("")}</section>` : ""}
      ${policyFacts.length ? `<section class="v26-exam-policy"><p class="v26-kicker">Program policy</p><h2>Retake and renewal facts</h2><ul>${policyFacts.map((fact) => `<li>${escapeHtml(fact)}</li>`).join("")}</ul>${item.policy_url ? `<a href="${escapeHtml(item.policy_url)}" target="_blank" rel="noopener noreferrer">Open official SnowPro policies ↗</a>` : ""}</section>` : ""}
      <section class="v26-how-to-prepare">
        <p class="v26-kicker">${implemented ? "Study guide available" : "Study guide coming soon"}</p>
        <h2>${implemented ? "Turn official facts into a study loop" : "Inspect the official exam now; study content remains separate"}</h2>
        <p>${implemented ? "Start with the diagnostic, study weak task lessons, validate the repair with targeted drills, and use timed mocks to build readiness evidence." : "This page can publish verified public certification facts before a Snowflake Brain curriculum is ready. It does not imply that lessons, practice questions, or a question bank exist for this track."}</p>
        <div class="v26-how-to-actions">${implemented ? `<a class="v26-btn primary" href="#/practice?track_id=${encodeURIComponent(item.configured_track_id)}&mode=diagnostic">Take the diagnostic</a><a class="v26-btn secondary" href="#/curriculum?track_id=${encodeURIComponent(item.configured_track_id)}">Browse curriculum</a>` : `<a class="v26-btn secondary" href="#/certifications">Compare certifications</a>`}<a class="v26-btn secondary" href="${escapeHtml(sourceUrl)}" target="_blank" rel="noopener noreferrer">Official Snowflake page ↗</a></div>
      </section>
      <p class="v26-fact-verification">Source verification: ${escapeHtml(item.source_verified_at || "not recorded")}. Facts without verified source evidence are not displayed.</p>
    </section>
  </main>`;
}
