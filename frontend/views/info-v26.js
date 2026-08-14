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
      "The current release adds the activity globe, certification chooser, study sidebar, unified practice gateway, interrupted-sitting recovery, dedicated exam navigator, results review, themes, reference library, journal presentation, and feedback flow."
    ]
  },
  "#/privacy": {
    kicker: "Privacy",
    title: "Local-first study data.",
    body: [
      "This development application stores study progress, practice attempts, mock sessions, notes, and feedback in its configured application database.",
      "Do not place credentials, secrets, or sensitive personal information in notes or feedback fields."
    ]
  }
};

export default async function mount(container) {
  const path = (window.location.hash || "#/about").split("?")[0];
  const page = pages[path] || pages["#/about"];
  container.innerHTML = `<main class="v26-page v26-info-page"><section class="v26-page-intro"><p class="v26-kicker">${page.kicker}</p><h1>${page.title}</h1></section><section class="v26-info-copy">${page.body.map((item) => `<p>${item}</p>`).join("")}</section></main>`;
}
