import { getSkillMap } from "../api.js";
import { activeTrack, navigateWithTrack, normalizeTrack, setActiveTrack } from "../ui.js";

const certificationItems = [
  ["#/curriculum", "Curriculum"],
  ["#/practice", "Practice"],
  ["#/reference", "Reference"],
  ["#/journal", "Journal"],
];
const homeItems = certificationItems.filter(([href]) => href === "#/reference" || href === "#/journal");

const aliases = new Map([
  ["#/domain", "#/curriculum"], ["#/skill", "#/curriculum"],
  ["#/quick-reference", "#/reference"], ["#/glossary", "#/reference"],
  ["#/mock", "#/practice"], ["#/mock/start", "#/practice"], ["#/mock/session", "#/practice"], ["#/mock/result", "#/practice"], ["#/mock/history", "#/practice"],
  ["#/diagnostic", "#/practice"], ["#/drill", "#/practice"], ["#/quiz", "#/practice"],
  ["#/article", "#/journal"],
]);

export async function renderNav() {
  const nav = document.querySelector("#sidebar");
  if (!nav) return;
  let tracks = [];
  try { tracks = (await getSkillMap()).certifications || []; } catch {}
  const selected = normalizeTrack(activeTrack(), tracks);
  setActiveTrack(selected);
  const cert = tracks.find((item) => item.id === selected) || { id: "snowpro-core", title: "SnowPro Core", exam_code: "COF-C03" };
  const theme = document.documentElement.dataset.theme || "dark";
  const rawPath = (window.location.hash || "#/home").split("?")[0];
  const primaryItems = rawPath === "#/home" || rawPath === "#/" ? homeItems : certificationItems;

  nav.className = "v26-header";
  nav.innerHTML = `<div class="v26-nav-inner">
    <a class="v26-brand" href="#/home" aria-label="Snowflake Certified home"><span class="v26-brand-mark">S</span><span>Snowflake Certified</span></a>
    <button class="v26-mobile-menu" type="button" data-menu aria-label="Open navigation" aria-expanded="false">Menu</button>
    <nav class="v26-primary-nav" aria-label="Primary navigation">${primaryItems.map(([href, label]) => `<a href="${href}" data-href="${href}">${label}</a>`).join("")}</nav>
    <div class="v26-nav-actions">
      <div class="v26-cert-menu">
        <button class="v26-cert-trigger" type="button" data-cert-trigger aria-haspopup="menu" aria-expanded="false"><span>${cert.exam_code || "COF-C03"}</span><b>${cert.title || "SnowPro Core"}</b><i>⌄</i></button>
        <div class="v26-cert-popover" data-cert-popover role="menu" hidden>
          <a class="v26-cert-all" href="#/certifications" role="menuitem"><span>All certifications</span><b>View paths →</b></a>
          ${(tracks.length ? tracks : [cert]).map((item) => `<button type="button" role="menuitem" data-track="${item.id}" class="${item.id === selected ? "selected" : ""}"><span>${item.exam_code || "SnowPro"}</span><b>${item.title || item.id}</b>${item.id === selected ? `<em>Selected</em>` : ""}</button>`).join("")}
          <div class="v26-cert-soon"><span>Advanced & specialty paths</span><b>More guides coming soon</b></div>
        </div>
      </div>
      <button class="v26-theme-toggle" type="button" data-theme-toggle aria-label="Switch color theme">${theme === "dark" ? "☼" : "☾"}</button>
      <a class="v26-mock-cta" href="#/mock?track_id=${encodeURIComponent(selected)}">Take Mock Exam</a>
    </div>
  </div>`;

  nav.querySelector("[data-menu]")?.addEventListener("click", (event) => {
    const open = document.body.classList.toggle("v26-menu-open");
    event.currentTarget.setAttribute("aria-expanded", String(open));
  });
  const trigger = nav.querySelector("[data-cert-trigger]");
  const popover = nav.querySelector("[data-cert-popover]");
  trigger?.addEventListener("click", () => {
    const next = popover.hidden;
    popover.hidden = !next;
    trigger.setAttribute("aria-expanded", String(next));
  });
  nav.querySelectorAll("[data-track]").forEach((button) => button.addEventListener("click", () => navigateWithTrack(button.dataset.track, "#/home")));
  nav.querySelector("[data-theme-toggle]")?.addEventListener("click", () => {
    const next = (document.documentElement.dataset.theme || "dark") === "dark" ? "light" : "dark";
    window.dispatchEvent(new CustomEvent("theme-toggle", { detail: { theme: next } }));
    renderNav();
  });
  document.addEventListener("click", (event) => {
    if (popover && !popover.hidden && !nav.querySelector(".v26-cert-menu")?.contains(event.target)) {
      popover.hidden = true;
      trigger?.setAttribute("aria-expanded", "false");
    }
  }, { once: true });
  updateActiveNav();
}

export function updateActiveNav() {
  const raw = (window.location.hash || "#/home").split("?")[0];
  const active = aliases.get(raw) || raw;
  document.querySelectorAll(".v26-primary-nav a").forEach((item) => {
    const selected = item.dataset.href === active;
    item.classList.toggle("active", selected);
    selected ? item.setAttribute("aria-current", "page") : item.removeAttribute("aria-current");
  });
  document.body.classList.remove("v26-menu-open");
}
