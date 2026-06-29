import { escapeHtml, searchBrain, streamAi } from "../api.js";
import { showToast } from "../components/toast.js";

let timer = null;

export default async function mount(container) {
  container.innerHTML = `
    <section class="page-heading">
      <div><p class="eyebrow">Brain search</p><h1>Search lessons and questions</h1><p>Find the exact training material behind a Snowflake concept.</p></div>
    </section>
    <section class="panel search-panel">
      <div class="search-bar"><input id="search-input" placeholder="Search Time Travel, RBAC, Snowpipe, micro-partitions..." autofocus /><button id="ask-ai" class="secondary-btn" type="button">Ask AI</button></div>
      <div id="ai-answer" class="ai-answer hidden"></div>
      <div id="results" class="result-grid empty-box">Start typing to search the local index.</div>
    </section>
  `;
  const input = container.querySelector("#search-input");
  input.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(() => runSearch(container, input.value), 300);
  });
  container.querySelector("#ask-ai").addEventListener("click", () => ask(container, input.value));
}

export function unmount() {
  clearTimeout(timer);
}

async function runSearch(container, q) {
  const results = container.querySelector("#results");
  if (!q.trim()) {
    results.className = "result-grid empty-box";
    results.textContent = "Start typing to search the local index.";
    return;
  }
  try {
    const data = await searchBrain(q.trim(), 24);
    results.className = "result-grid";
    if (!data.results.length) {
      results.className = "result-grid empty-box";
      results.textContent = "No matching local material found.";
      return;
    }
    results.innerHTML = data.results
      .map((item) => {
        const href = item.type === "lesson" ? `#/video?lesson_id=${encodeURIComponent(item.ref_id)}` : item.type === "question" ? `#/quiz` : `#/labs`;
        return `<a class="result-item" href="${href}">
          <span class="pill">${escapeHtml(item.type)}</span>
          <strong>${escapeHtml(item.title)}</strong>
          <p>${item.snippet || ""}</p>
        </a>`;
      })
      .join("");
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function ask(container, q) {
  if (!q.trim()) return;
  const panel = container.querySelector("#ai-answer");
  panel.classList.remove("hidden");
  panel.innerHTML = `<p class="eyebrow">AI tutor</p><div id="stream-text"></div><div id="sources"></div>`;
  const target = panel.querySelector("#stream-text");
  try {
    await streamAi(
      q,
      (delta) => {
        target.textContent += delta;
      },
      (sources) => {
        panel.querySelector("#sources").innerHTML = sources.length
          ? `<div class="source-list">${sources.map((source) => `<span>${escapeHtml(source.title)}</span>`).join("")}</div>`
          : "";
      },
    );
  } catch (error) {
    showToast(error.message, "error");
  }
}
