export const VIEW_ID = "v26-info";

const pages = {
  "#/about": {
    kicker: "About",
    title: "Built for deliberate SnowPro preparation.",
    body: [
      "Snowflake Certification Guide organizes study around the current certification blueprint instead of a course playlist.",
      "Learn task by task, practice the same objectives, rehearse timed sittings, and use progress evidence to decide what to review next."
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

export default async function mount(container) {
  const path = (window.location.hash || "#/about").split("?")[0];
  const page = pages[path] || pages["#/about"];
  container.innerHTML = `<main class="v26-page v26-info-page"><section class="v26-page-intro"><p class="v26-kicker">${page.kicker}</p><h1>${page.title}</h1></section><section class="v26-info-copy">${page.body.map((item) => `<p>${item}</p>`).join("")}</section></main>`;
}
