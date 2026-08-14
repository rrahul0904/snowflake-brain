export const VIEW_ID = "v26-journal";

import base from "./journal.js";

export default async function mount(container, params = {}) {
  await base(container, params);
  const pageHeading = container.querySelector(".replica-page-heading");
  if (pageHeading) {
    const kicker = pageHeading.querySelector(".replica-kicker");
    const title = pageHeading.querySelector("h1");
    const intro = pageHeading.querySelector("p:last-child");
    if (kicker) kicker.textContent = "System Repository";
    if (title) title.textContent = "SnowPro Journal";
    if (intro) intro.textContent = "Articles, tutorials, and study notes for Snowflake certification — focused on exam distinctions, practical architecture decisions, and recurring traps.";
  }
  [...container.querySelectorAll(".replica-article-card")].forEach((card, index) => { card.dataset.journalTone = String(index % 4 + 1); });
  const article = container.querySelector(".replica-article");
  if (article) {
    const header = article.querySelector("header");
    header?.insertAdjacentHTML("beforeend", `<div class="v26-article-meta"><span>6 min read</span><span>August 2026</span></div>`);
  }
}
