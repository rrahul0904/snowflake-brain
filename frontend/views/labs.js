import { escapeHtml, getLab, getLabs, submitLab } from "../api.js";
import { showToast } from "../components/toast.js";

let active = null;

export default async function mount(container) {
  container.innerHTML = `
    <section class="page-heading">
      <div><p class="eyebrow">SQL labs</p><h1>Command practice</h1><p>Write Snowflake SQL and validate the required clauses locally.</p></div>
    </section>
    <section class="labs-layout">
      <aside class="panel"><div id="lab-list" class="lab-list"></div></aside>
      <section class="panel" id="lab-detail"><div class="empty-box">Select a lab.</div></section>
    </section>
  `;
  try {
    const data = await getLabs();
    container.querySelector("#lab-list").innerHTML = data.labs
      .map((lab) => `<button class="lab-item" data-id="${lab.id}" type="button"><strong>${escapeHtml(lab.title)}</strong><span>${escapeHtml(lab.difficulty || lab.level || "core")}</span></button>`)
      .join("");
    container.querySelectorAll(".lab-item").forEach((button) => button.addEventListener("click", () => selectLab(container, button.dataset.id)));
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function selectLab(container, id) {
  active = await getLab(id);
  container.querySelector("#lab-detail").innerHTML = `
    <p class="eyebrow">${escapeHtml((active.tags || [active.domain || "lab"]).join(", "))}</p>
    <h2>${escapeHtml(active.title)}</h2>
    <p class="muted">${escapeHtml(active.description || active.setup || "")}</p>
    <details><summary>Hint</summary><p>${escapeHtml(active.hint || "Focus on the required Snowflake clauses.")}</p></details>
    <textarea id="sql" class="sql-editor" spellcheck="false">${escapeHtml(active.starter_sql || active.sql || "")}</textarea>
    <div class="action-row"><button id="run" class="primary-btn">Run / Submit</button></div>
    <div id="result"></div>
  `;
  const textarea = container.querySelector("#sql");
  textarea.addEventListener("keydown", (event) => {
    if (event.key === "Tab") {
      event.preventDefault();
      const start = textarea.selectionStart;
      textarea.value = textarea.value.slice(0, start) + "  " + textarea.value.slice(start);
      textarea.selectionStart = textarea.selectionEnd = start + 2;
    }
  });
  container.querySelector("#run").addEventListener("click", async () => {
    try {
      const result = await submitLab(active.id, textarea.value);
      container.querySelector("#result").innerHTML = `<div class="result-banner ${result.passed ? "correct" : "incorrect"}">${escapeHtml(result.feedback)}</div>`;
    } catch (error) {
      showToast(error.message, "error");
    }
  });
}
