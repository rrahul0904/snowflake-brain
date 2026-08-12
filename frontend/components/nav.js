const items = [
  ["#/curriculum", "Curriculum"],
  ["#/mock", "Practice"],
  ["#/quick-reference", "Reference"],
  ["#/journal", "Blog"],
];

const aliases = new Map([
  ["#/", "#/home"],
  ["#/command", "#/home"],
  ["#/today", "#/curriculum"],
  ["#/academy", "#/curriculum"],
  ["#/learn", "#/curriculum"],
  ["#/lessons", "#/curriculum"],
  ["#/archive", "#/curriculum"],
  ["#/domain", "#/curriculum"],
  ["#/skill", "#/curriculum"],
  ["#/lesson", "#/curriculum"],
  ["#/video", "#/curriculum"],
  ["#/quiz", "#/mock"],
  ["#/practice", "#/mock"],
  ["#/diagnostic", "#/mock"],
  ["#/drill", "#/mock"],
  ["#/exercises", "#/mock"],
  ["#/labs", "#/mock"],
  ["#/progress", "#/curriculum"],
  ["#/readiness", "#/curriculum"],
  ["#/intelligence", "#/curriculum"],
  ["#/analytics", "#/curriculum"],
  ["#/search", "#/quick-reference"],
  ["#/reference", "#/quick-reference"],
  ["#/glossary", "#/quick-reference"],
  ["#/ai", "#/quick-reference"],
  ["#/review", "#/mock"],
  ["#/career", "#/journal"],
]);

export async function renderNav() {
  const nav = document.querySelector("#sidebar");
  nav.className = "replica-header";
  nav.innerHTML = `
    <div class="replica-nav-inner">
      <a class="replica-brand" href="#/home" aria-label="Snowflake Certification Guide home">
        <span class="replica-brand-mark" aria-hidden="true">S</span>
        <span>Snowflake Certified</span>
      </a>
      <button class="replica-menu-toggle" id="replica-menu-toggle" type="button" aria-label="Open navigation" aria-expanded="false">Menu</button>
      <div class="replica-nav-links" id="replica-nav-links">
        ${items.map(([href, label]) => `<a href="${href}" data-href="${href}">${label}</a>`).join("")}
      </div>
      <div class="replica-nav-actions">
        <label class="replica-cert-control"><span class="sr-only">Certification</span><select id="replica-track-select" aria-label="Certification"><option>Loading certifications...</option></select></label>
        <a class="replica-primary-action" href="#/mock">Mock Exam</a>
      </div>
    </div>
  `;
  nav.querySelector("#replica-menu-toggle")?.addEventListener("click", (event) => {
    const open = document.body.classList.toggle("replica-menu-open");
    event.currentTarget.setAttribute("aria-expanded", String(open));
  });
  updateActiveNav();
}

export function updateActiveNav() {
  const raw = (window.location.hash || "#/home").split("?")[0];
  const active = aliases.get(raw) || raw;
  document.querySelectorAll(".replica-nav-links a").forEach((item) => {
    const selected = item.dataset.href === active;
    item.classList.toggle("active", selected);
    if (selected) item.setAttribute("aria-current", "page");
    else item.removeAttribute("aria-current");
  });
  document.body.classList.remove("replica-menu-open");
}
