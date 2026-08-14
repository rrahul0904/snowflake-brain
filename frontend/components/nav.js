import { escapeHtml, getCertificationCatalog, getSkillMap } from "../api.js";
import { candidate } from "../auth.js";
import { activeTrack, navigateWithTrack, normalizeTrack, setActiveTrack } from "../ui.js";

const certificationItems = [
  ["#/curriculum", "Curriculum"],
  ["#/practice", "Practice"],
  ["#/reference", "Reference"],
  ["#/journal", "Journal"],
  ["#/membership", "Membership"],
];
const homeItems = certificationItems.filter(([href]) => ["#/reference", "#/journal", "#/membership"].includes(href));

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
  let catalog = [];
  try {
    const [map, catalogPayload] = await Promise.all([getSkillMap(), getCertificationCatalog()]);
    tracks = map.certifications || [];
    catalog = catalogPayload.official_certifications || [];
  } catch {}
  const selected = normalizeTrack(activeTrack(), tracks);
  setActiveTrack(selected);
  const cert = tracks.find((item) => item.id === selected) || { id: "snowpro-core", title: "SnowPro Core", exam_code: "COF-C03" };
  const theme = document.documentElement.dataset.theme || "dark";
  const rawPath = (window.location.hash || "#/home").split("?")[0];
  const primaryItems = rawPath === "#/home" || rawPath === "#/" ? homeItems : certificationItems;
  const account = candidate();
  const initials = account?.display_name?.split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase() || "";

  nav.className = "v26-header";
  nav.innerHTML = `<div class="v26-nav-inner">
    <a class="v26-brand" href="#/home" aria-label="Snowflake Certified home"><span class="v26-brand-mark">S</span><span>Snowflake Certified</span></a>
    <button class="v26-mobile-menu" type="button" data-menu aria-label="Open navigation" aria-expanded="false">Menu</button>
    <nav class="v26-primary-nav" aria-label="Primary navigation">${primaryItems.map(([href, label]) => `<a href="${href}" data-href="${href}">${label}</a>`).join("")}${account ? "" : `<button class="v26-mobile-auth" type="button" data-auth-intent="login">Sign In</button><button class="v26-mobile-auth" type="button" data-auth-intent="signup">Create Account</button>`}</nav>
    <div class="v26-nav-actions">
      <div class="v26-cert-menu">
        <button class="v26-cert-trigger" type="button" data-cert-trigger aria-haspopup="menu" aria-expanded="false"><span>${cert.exam_code || "COF-C03"}</span><b>${cert.title || "SnowPro Core"}</b><i>⌄</i></button>
        <div class="v26-cert-popover" data-cert-popover role="menu" hidden>
          <a class="v26-cert-all" href="#/certifications" role="menuitem"><span>All certifications</span><b>View paths →</b></a>
          ${(catalog.length ? catalog : [cert]).map((item) => item.id === "snowpro-core" ? `<button type="button" role="menuitem" data-track="snowpro-core" class="selected"><span>${escapeHtml(item.exam_code || "COF-C03")}</span><b>${escapeHtml(item.title || "SnowPro Core")}</b><em>Current</em></button>` : `<div class="v26-cert-option-soon" role="menuitem" aria-disabled="true"><span>${escapeHtml(item.exam_code || "SnowPro")}</span><b>${escapeHtml(item.title || "Advanced certification")}</b><em>Coming Soon</em></div>`).join("")}
        </div>
      </div>
      <button class="v26-theme-toggle" type="button" data-theme-toggle aria-label="Switch color theme">${theme === "dark" ? "☼" : "☾"}</button>
      ${account ? `<div class="v26-account-menu"><button class="v26-account-link" type="button" data-account-trigger aria-label="${escapeHtml(account.display_name)} account menu, ${escapeHtml(account.plan)}" aria-haspopup="menu" aria-expanded="false"><span>${escapeHtml(initials)}</span><b>${escapeHtml(account.display_name)} ▾</b><em>${escapeHtml(account.plan)}</em></button><div class="v26-account-popover" data-account-popover role="menu" hidden><div><strong>${escapeHtml(account.display_name)}</strong><span>${escapeHtml(account.email)}</span><em>${escapeHtml(account.plan)}</em></div><a href="#/progress?track_id=${encodeURIComponent(selected)}" role="menuitem">My Progress</a><a href="#/membership" role="menuitem">Membership</a><button type="button" data-auth-logout role="menuitem">Sign Out</button></div></div>` : `<button class="v26-login-link" type="button" data-auth-intent="login">Sign In</button><button class="v26-signup-link" type="button" data-auth-intent="signup">Create Account</button>`}
      <a class="v26-mock-cta" href="#/mock?track_id=${encodeURIComponent(selected)}">${account?.plan_code === "free" ? "Weekly Mock" : "Take Mock Exam"}</a>
    </div>
  </div>`;

  nav.querySelector("[data-menu]")?.addEventListener("click", (event) => {
    const open = document.body.classList.toggle("v26-menu-open");
    event.currentTarget.setAttribute("aria-expanded", String(open));
  });
  const trigger = nav.querySelector("[data-cert-trigger]");
  const popover = nav.querySelector("[data-cert-popover]");
  const accountTrigger = nav.querySelector("[data-account-trigger]");
  const accountPopover = nav.querySelector("[data-account-popover]");
  trigger?.addEventListener("click", () => {
    const next = popover.hidden;
    popover.hidden = !next;
    trigger.setAttribute("aria-expanded", String(next));
  });
  nav.querySelectorAll("[data-track]").forEach((button) => button.addEventListener("click", () => navigateWithTrack(button.dataset.track, "#/home")));
  accountTrigger?.addEventListener("click", () => {
    const next = accountPopover.hidden;
    accountPopover.hidden = !next;
    accountTrigger.setAttribute("aria-expanded", String(next));
  });
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
    if (accountPopover && !accountPopover.hidden && !nav.querySelector(".v26-account-menu")?.contains(event.target)) {
      accountPopover.hidden = true;
      accountTrigger?.setAttribute("aria-expanded", "false");
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
