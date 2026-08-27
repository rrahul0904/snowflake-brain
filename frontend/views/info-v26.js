export const VIEW_ID = "v26-info";

const domains = [
  ["01", "Snowflake AI Data Cloud Features & Architecture", "31%", "6 tasks"],
  ["02", "Account Management & Data Governance", "20%", "3 tasks"],
  ["03", "Data Loading, Unloading & Connectivity", "18%", "3 tasks"],
  ["04", "Performance Optimization, Querying & Transformation", "21%", "4 tasks"],
  ["05", "Data Collaboration", "10%", "3 tasks"],
];

const pages = {
  "#/about": {
    kicker: "About",
    title: "Built for deliberate SnowPro preparation.",
    body: [
      "Snowflake Certification Guide organizes study around the current certification blueprint instead of a course playlist.",
      "Learn task by task, practice the same objectives, rehearse timed sittings, and use progress evidence to decide what to review next."
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
      "The production roadmap adds PostgreSQL persistence, operational observability, account recovery and data controls, official-source freshness monitoring, version-bound editorial governance, and evidence-based Adaptive Readiness."
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
    container.innerHTML = examGuide();
    return;
  }
  const page = pages[path] || pages["#/about"];
  container.innerHTML = `<main class="v26-page v26-info-page"><section class="v26-page-intro"><p class="v26-kicker">${page.kicker}</p><h1>${page.title}</h1></section><section class="v26-info-copy">${page.body.map((item) => `<p>${item}</p>`).join("")}</section></main>`;
}

function examGuide() {
  return `<main class="v26-page v26-info-page v26-exam-guide-page">
    <section class="v26-page-intro">
      <p class="v26-kicker">COF-C03 · Exam guide</p>
      <h1>Know the blueprint before you start drilling.</h1>
      <p>SnowPro Core preparation in this guide is organized into five weighted domains and nineteen task statements. Domain weights help you allocate study time; the authenticated curriculum contains the detailed lessons and task-level practice.</p>
      <p class="v26-exam-guide-note">For current registration, delivery, pricing, accommodations, and official policy details, always use Snowflake's official certification pages.</p>
    </section>
    <section class="v26-info-copy v26-exam-domain-outline">
      <p class="v26-kicker">What is covered</p>
      ${domains.map(([number, title, weight, count]) => `<div class="v26-exam-domain-row"><span>${number}</span><strong>${title}</strong><em>${count}</em><b>${weight}</b></div>`).join("")}
      <article class="v26-how-to-prepare">
        <p class="v26-kicker">Available now</p>
        <h2>How to prepare here</h2>
        <p>Take the diagnostic first. Use the result to identify the weighted domains that deserve the most attention, work through those task lessons, then validate the repair with drills and timed mocks.</p>
        <div class="v26-how-to-actions"><a class="v26-btn primary" href="#/practice?mode=diagnostic">Take the diagnostic</a><a class="v26-btn secondary" href="#/curriculum">Browse the curriculum</a><a class="v26-btn secondary" href="#/quick-reference">Quick reference</a></div>
      </article>
    </section>
  </main>`;
}
