const primaryItems = [
  ["#/today", "Today"],
  ["#/learn", "Learn"],
  ["#/practice", "Practice"],
  ["#/review", "Review"],
  ["#/readiness", "Readiness"],
];

const aliases = new Map([
  ["#/", "#/today"],
  ["#/setup", "#/today"],
  ["#/video", "#/learn"],
  ["#/lessons", "#/learn"],
  ["#/quiz", "#/practice"],
  ["#/analytics", "#/review"],
]);

export async function renderNav() {
  const nav = document.querySelector("#sidebar");
  nav.innerHTML = `
    <a class="brand-block brand-compact coach-brand" href="#/today">
      <span class="brand-mark">S</span>
      <span><strong>Snowflake Brain</strong><small>Certification coach</small></span>
    </a>
    <div class="nav-list nav-list-clean coach-nav-list">
      ${primaryItems
        .map(([href, label]) => `<a href="${href}" class="nav-item nav-item-clean" data-href="${href}"><strong>${label}</strong></a>`)
        .join("")}
    </div>
    <div class="nav-secondary-links coach-secondary-links">
      <a href="#/search">Search</a>
      <a href="#/flashcards">Cards</a>
      <a href="#/labs">Labs</a>
      <a href="#/plan">Plan</a>
    </div>
  `;
  updateActiveNav();
}

export function updateActiveNav() {
  const raw = (window.location.hash || "#/today").split("?")[0];
  const active = aliases.get(raw) || raw;
  document.querySelectorAll(".nav-item").forEach((item) => {
    item.classList.toggle("active", item.dataset.href === active);
  });
}
