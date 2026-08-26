export const VIEW_ID = "v26-community";

import { escapeHtml, getSkillMap } from "../api.js";
import { activeTrack } from "../ui.js";
import { studyLayout } from "../components/study-shell.js";

const INSIGHTS = [
  { type: "Study Strategy", domain: "All", title: "Use the blueprint as your study queue", body: "Spend time in proportion to domain weight, but let weak-task evidence override a rigid calendar when practice shows a recurring gap.", action: "Open curriculum", href: "#/curriculum" },
  { type: "Common Mistake", domain: "Architecture", title: "Do not confuse storage, compute, and cloud services", body: "Many exam distractors swap responsibilities between Snowflake layers. Be precise about what persists data, what executes queries, and what coordinates platform services.", action: "Review architecture", href: "#/curriculum" },
  { type: "Exam Tip", domain: "Governance", title: "Look for least-privilege wording", body: "When two answers both technically work, the exam often favors the option that grants only the privileges required by the scenario.", action: "Practice governance", href: "#/practice" },
  { type: "Deep Dive", domain: "Loading", title: "Treat ingestion choices as a decision tree", body: "Batch COPY, automated file ingestion, and streaming solve different arrival patterns. Read the scenario for latency, file arrival behavior, and operational control.", action: "Study loading", href: "#/curriculum" },
  { type: "Common Mistake", domain: "Performance", title: "Bigger warehouses do not solve every performance issue", body: "First identify whether the problem is scan efficiency, query design, concurrency, or insufficient compute. Scale-up and scale-out answer different bottlenecks.", action: "Start a drill", href: "#/practice" },
  { type: "Exam Tip", domain: "Collaboration", title: "Separate sharing from copying", body: "Secure Data Sharing is about governed access without traditional export copies. Cloning, replication, and marketplace listings solve different collaboration needs.", action: "Review collaboration", href: "#/curriculum" },
  { type: "Study Strategy", domain: "Performance", title: "Use Query Profile to explain, not guess", body: "When a scenario asks why a query behaves badly, prefer evidence from Query Profile and pruning behavior before jumping to a platform feature.", action: "Practice performance", href: "#/practice" },
  { type: "Success Story", domain: "All", title: "Master the recurring distinctions before chasing volume", body: "Candidates improve faster when they write down the rule behind each miss, revisit it on schedule, and then prove the distinction again in a timed mock.", action: "Open mistakes", href: "#/mistakes" },
];

export default async function mount(container, params = {}) {
  const trackId = params.track_id || activeTrack();
  const map = await getSkillMap();
  const cert = (map.certifications || []).find((item) => item.id === trackId) || (map.certifications || [])[0];
  if (!cert) throw new Error("Certification is not configured");

  const types = ["All", ...new Set(INSIGHTS.map((item) => item.type))];
  const domains = ["All", "Architecture", "Governance", "Loading", "Performance", "Collaboration"];

  container.innerHTML = studyLayout(cert, "community", `<a class="v26-study-back" href="#/home" aria-label="Back">‹</a>
    <header class="v26-recording-progress-head v26-community-head"><p class="v26-kicker">Community Insights</p><h1>Learn from the patterns candidates keep missing.</h1><p>Study strategies, exam tips, common mistakes, and technical deep dives — curated for SnowPro Core and tied back to the learning system.</p></header>
    <section class="v26-community-toolbar"><div><span>Type</span>${types.map((value) => `<button type="button" class="${value === "All" ? "active" : ""}" data-community-type="${escapeHtml(value)}">${escapeHtml(value)}</button>`).join("")}</div><div><span>Domain</span>${domains.map((value) => `<button type="button" class="${value === "All" ? "active" : ""}" data-community-domain="${escapeHtml(value)}">${escapeHtml(value)}</button>`).join("")}</div></section>
    <section class="v26-community-grid" data-community-grid>${INSIGHTS.map((item) => card(item, trackId)).join("")}</section>
    <section class="v26-community-guideline"><div><p class="v26-kicker">How to use this</p><h2>Turn an insight into evidence.</h2><p>Do not stop at reading the tip. Open the related lesson, answer questions, capture any miss in Mistake Collection, and validate the distinction in a timed mock.</p></div><a class="v26-btn primary" href="#/practice?track_id=${encodeURIComponent(trackId)}">Start practice</a></section>`);

  bindFilters(container);
}

function card(item, trackId) {
  const base = item.href.includes("?") ? item.href : `${item.href}?track_id=${encodeURIComponent(trackId)}`;
  return `<article class="v26-community-card" data-type="${escapeHtml(item.type)}" data-domain="${escapeHtml(item.domain)}"><div><span>${escapeHtml(item.type)}</span><em>${escapeHtml(item.domain)}</em></div><h2>${escapeHtml(item.title)}</h2><p>${escapeHtml(item.body)}</p><a href="${base}">${escapeHtml(item.action)} →</a></article>`;
}

function bindFilters(container) {
  let type = "All";
  let domain = "All";
  const apply = () => {
    container.querySelectorAll(".v26-community-card").forEach((card) => {
      const typeMatch = type === "All" || card.dataset.type === type;
      const domainMatch = domain === "All" || card.dataset.domain === domain || card.dataset.domain === "All";
      card.hidden = !(typeMatch && domainMatch);
    });
  };
  container.querySelectorAll("[data-community-type]").forEach((button) => button.addEventListener("click", () => {
    type = button.dataset.communityType;
    container.querySelectorAll("[data-community-type]").forEach((item) => item.classList.toggle("active", item === button));
    apply();
  }));
  container.querySelectorAll("[data-community-domain]").forEach((button) => button.addEventListener("click", () => {
    domain = button.dataset.communityDomain;
    container.querySelectorAll("[data-community-domain]").forEach((item) => item.classList.toggle("active", item === button));
    apply();
  }));
}
