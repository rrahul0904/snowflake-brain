export const VIEW_ID = "ai";
import { askBrain, escapeHtml, streamAi } from "../api.js?v=20260714-v20-ai-academy";
import { emptyState } from "../ui.js?v=20260714-v20-ai-academy";
import { showToast } from "../components/toast.js?v=20260714-v20-ai-academy";

const prompts = [
  "Explain micro-partitions",
  "How does Snowpipe work?",
  "Describe RBAC in Snowflake",
  "What is the Fail-safe period?",
  "Explain streams vs dynamic tables",
  "What does AUTO_SUSPEND do?",
];

export default async function mount(container) {
  container.innerHTML = `
    <section class="page-shell ai-page-v10">
      <header class="page-hero split-hero">
        <div><p class="eyebrow">Local Archive Tutor</p><h1>Ask from your downloaded course content.</h1><p>Answers are built from indexed lessons, transcript chunks, practice questions, explanations, and documents stored on this machine. No external AI key is required.</p></div>
        <div class="hero-control-card"><strong>Private local mode</strong><span>Transcripts · questions · explanations · documents</span></div>
      </header>
      <div class="panel chat-panel-v10">
        <div id="messages" class="messages-v10">${emptyState("Ask a Snowflake exam question", "The answer will come from your local course archive and show the strongest sources found.")}</div>
        <div class="suggestions">${prompts.map((prompt) => `<button data-prompt="${escapeHtml(prompt)}" type="button">${escapeHtml(prompt)}</button>`).join("")}</div>
        <div class="chat-input"><input id="question" placeholder="Ask a Snowflake exam question..." /><button id="ask" class="primary-btn">Ask</button></div>
      </div>
    </section>
  `;
  container.querySelector("#ask")?.addEventListener("click", () => ask(container));
  container.querySelector("#question")?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") ask(container);
  });
  container.querySelectorAll("[data-prompt]").forEach((button) => {
    button.addEventListener("click", () => {
      container.querySelector("#question").value = button.dataset.prompt;
      ask(container);
    });
  });
}

async function ask(container) {
  const input = container.querySelector("#question");
  const question = input.value.trim();
  if (!question) return;
  const messages = container.querySelector("#messages");
  if (messages.querySelector(".empty-state")) messages.innerHTML = "";
  messages.innerHTML += `<div class="message user">${escapeHtml(question)}</div><div class="message assistant" id="streaming"><span class="muted">Searching local lessons, transcripts, and questions...</span></div>`;
  input.value = "";
  const bubble = container.querySelector("#streaming");
  bubble.removeAttribute("id");
  bubble.innerHTML = "";
  try {
    await streamAi(
      question,
      (delta) => {
        bubble.textContent += delta;
        messages.scrollTop = messages.scrollHeight;
      },
      (sources) => {
        if (sources?.length) {
          bubble.innerHTML += `<div class="source-list">${sources.map((source) => `<span>${escapeHtml(source.title)}</span>`).join("")}</div>`;
        }
      },
    );
  } catch (error) {
    try {
      const local = await askBrain({ question, context_limit: 5 });
      bubble.textContent = local.answer || "No local answer available.";
      if (local.sources?.length) bubble.innerHTML += `<div class="source-list">${local.sources.map((source) => `<span>${escapeHtml(source.title)}</span>`).join("")}</div>`;
    } catch (fallbackError) {
      showToast(fallbackError.message || error.message, "error");
      bubble.textContent = `Local archive tutor unavailable: ${fallbackError.message || error.message}`;
    }
  }
}
