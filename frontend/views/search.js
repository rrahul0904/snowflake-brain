export const VIEW_ID = "search";
import { escapeHtml, searchBrain, streamAi } from "../api.js?v=20260714-v20-ai-academy";
import { emptyState } from "../ui.js?v=20260714-v20-ai-academy";
import { showToast } from "../components/toast.js?v=20260714-v20-ai-academy";

export default async function mount(container, params = {}) {
  const initial = params.q || "";
  container.innerHTML = `
    <section class="page-shell search-page-v8">
      <header class="page-hero search-hero-v8"><div><p class="eyebrow">Brain Search</p><h1>Find the exact source behind any Snowflake concept.</h1><p>Search lessons, transcripts, practice questions, and lab challenges. Ask the local tutor only when you need a synthesized explanation.</p></div></header>
      <section class="search-console panel">
        <div class="search-bar-v8"><input id="query" value="${escapeHtml(initial)}" placeholder="Search RBAC, Time Travel, micro-partitions, dynamic tables..." /><button id="search" class="primary-btn">Search</button><button id="ask" class="secondary-btn">Ask tutor</button></div>
        <div id="ai-answer" class="ai-answer-v8 hidden"></div>
        <div id="results" class="search-results-v8">${emptyState("Start with a Snowflake concept", "The local index will return lessons and questions from your archive.")}</div>
      </section>
    </section>
  `;
  container.querySelector("#search")?.addEventListener("click", () => runSearch(container));
  container.querySelector("#ask")?.addEventListener("click", () => ask(container));
  container.querySelector("#query")?.addEventListener("keydown", (event) => { if (event.key === "Enter") runSearch(container); });
  if (initial) runSearch(container);
}

async function runSearch(container) {
  const q = container.querySelector("#query")?.value.trim();
  const host = container.querySelector("#results");
  if (!q) return;
  host.innerHTML = `<div class="loading-panel">Searching local archive...</div>`;
  try {
    const data = await searchBrain(q, 30);
    const rows = data.results || [];
    host.innerHTML = rows.length ? rows.map(resultCard).join("") : emptyState("No local matches", "Try a broader Snowflake keyword.");
  } catch (error) {
    showToast(error.message, "error");
  }
}

function resultCard(item) {
  const href = item.type === "lesson" ? `#/learn?lesson_id=${encodeURIComponent(item.ref_id || "")}` : item.type === "question" ? `#/practice` : `#/labs`;
  return `<a class="search-result-card" href="${href}"><span>${escapeHtml(item.type || "result")}</span><strong>${escapeHtml(item.title || "Untitled")}</strong><p>${escapeHtml(item.snippet || "")}</p></a>`;
}

async function ask(container) {
  const q = container.querySelector("#query")?.value.trim();
  if (!q) return;
  const panel = container.querySelector("#ai-answer");
  panel.classList.remove("hidden");
  panel.innerHTML = `<strong>Context tutor</strong><div id="stream"></div><div id="sources"></div>`;
  const stream = panel.querySelector("#stream");
  try {
    await streamAi(q, (delta) => { stream.textContent += delta; }, (sources) => {
      panel.querySelector("#sources").innerHTML = sources?.length ? `<div class="source-list">${sources.map((source) => `<span>${escapeHtml(source.title)}</span>`).join("")}</div>` : "";
    });
  } catch (error) {
    panel.innerHTML = `<strong>AI tutor unavailable</strong><p>${escapeHtml(error.message)}</p><small>Search still works locally without an API key.</small>`;
  }
}
