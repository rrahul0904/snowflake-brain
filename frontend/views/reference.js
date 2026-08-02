export const VIEW_ID = "reference";

import { escapeHtml, getTrackCourses, searchBrain } from "../api.js?v=20260731-v21-editorial-replica";
import { activeTrack } from "../ui.js?v=20260731-v21-editorial-replica";

export default async function mount(container, params = {}) {
  const trackId = params.track_id || activeTrack();
  const data = await getTrackCourses(trackId);
  const courses = data.courses || [];
  container.innerHTML = `
    <div class="replica-page replica-enter">
      <section class="replica-page-heading compact-heading">
        <p class="replica-kicker">Reference</p>
        <h1>Resources for deeper study.</h1>
        <p>Search your local archive or continue with verified Snowflake documentation and owned course resources.</p>
      </section>

      <section class="replica-search-band">
        <label for="reference-search">Search the local archive</label>
        <div><input id="reference-search" type="search" placeholder="Search RBAC, Snowpipe, Cortex, warehouses..."><button id="reference-search-button" type="button">Search</button></div>
        <div id="reference-results" class="replica-search-results" aria-live="polite"></div>
      </section>

      <section class="replica-section">
        <div class="replica-section-heading"><div><p class="replica-kicker">Official</p><h2>Snowflake documentation</h2></div></div>
        <div class="replica-resource-grid">
          ${officialResources.map(resourceCard).join("")}
        </div>
      </section>

      <section class="replica-section">
        <div class="replica-section-heading"><div><p class="replica-kicker">Owned archive</p><h2>Course resources</h2></div><span>${courses.length} courses</span></div>
        <div class="replica-resource-grid">
          ${courses.slice(0, 12).map((course) => resourceCard({ title: course.title, description: `${course.lesson_count || 0} lessons · ${course.question_count || 0} questions`, href: course.source_url || `#/curriculum?track_id=${encodeURIComponent(trackId)}` })).join("")}
        </div>
      </section>
    </div>`;
  const input = container.querySelector("#reference-search");
  const button = container.querySelector("#reference-search-button");
  const run = () => search(container, input.value);
  button.addEventListener("click", run);
  input.addEventListener("keydown", (event) => { if (event.key === "Enter") run(); });
}

const officialResources = [
  { title: "Snowflake Documentation", description: "Platform concepts, SQL reference, administration, and product guides.", href: "https://docs.snowflake.com/" },
  { title: "Snowflake Architecture", description: "Storage, compute, cloud services, and the virtual warehouse model.", href: "https://docs.snowflake.com/en/user-guide/intro-key-concepts" },
  { title: "Snowflake Cortex AI", description: "LLM functions, Cortex Search, Analyst, and machine-learning features.", href: "https://docs.snowflake.com/en/guides-overview-ai-features" },
  { title: "Security & Access Control", description: "Roles, privileges, authentication, policies, and governance.", href: "https://docs.snowflake.com/en/user-guide/security-access-control-overview" },
];

function resourceCard(item) {
  const external = String(item.href || "").startsWith("http");
  return `<a class="replica-resource-card" href="${escapeHtml(item.href)}" ${external ? `target="_blank" rel="noreferrer"` : ""}><span>${external ? "External reference" : "Local resource"}</span><strong>${escapeHtml(item.title)}</strong><p>${escapeHtml(item.description || "")}</p><small>Open resource ↗</small></a>`;
}

async function search(container, query) {
  const target = container.querySelector("#reference-results");
  const q = String(query || "").trim();
  if (q.length < 2) {
    target.innerHTML = `<p>Enter at least two characters.</p>`;
    return;
  }
  target.innerHTML = `<p>Searching local sources...</p>`;
  try {
    const data = await searchBrain(q, 8);
    const rows = data.results || data.items || [];
    target.innerHTML = rows.length ? rows.map((item) => `<a href="${item.lesson_id ? `#/lesson?lesson_id=${encodeURIComponent(item.lesson_id)}` : "#/curriculum"}"><strong>${escapeHtml(item.title || item.question || "Result")}</strong><span>${escapeHtml(item.excerpt || item.text || item.course_title || "Local course source")}</span></a>`).join("") : `<p>No local matches found.</p>`;
  } catch (error) {
    target.innerHTML = `<p>${escapeHtml(error.message)}</p>`;
  }
}

