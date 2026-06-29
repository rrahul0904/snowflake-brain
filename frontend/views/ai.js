import { escapeHtml, streamAi } from "../api.js";
import { showToast } from "../components/toast.js";

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
    <section class="ai-layout">
      <div class="panel chat-panel">
        <div class="panel-title"><div><p class="eyebrow">AI tutor</p><h1>Ask from your course context</h1></div></div>
        <div id="messages" class="messages"></div>
        <div class="suggestions">${prompts.map((prompt) => `<button data-prompt="${escapeHtml(prompt)}" type="button">${escapeHtml(prompt)}</button>`).join("")}</div>
        <div class="chat-input"><input id="question" placeholder="Ask a Snowflake exam question..." /><button id="ask" class="primary-btn">Ask</button></div>
      </div>
    </section>
  `;
  container.querySelector("#ask").addEventListener("click", () => ask(container));
  container.querySelector("#question").addEventListener("keydown", (event) => {
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
  messages.innerHTML += `<div class="message user">${escapeHtml(question)}</div><div class="message assistant" id="streaming"></div>`;
  input.value = "";
  const bubble = container.querySelector("#streaming");
  bubble.removeAttribute("id");
  try {
    await streamAi(
      question,
      (delta) => {
        bubble.textContent += delta;
        messages.scrollTop = messages.scrollHeight;
      },
      (sources) => {
        if (sources.length) {
          bubble.innerHTML += `<div class="source-list">${sources.map((source) => `<span>${escapeHtml(source.title)}</span>`).join("")}</div>`;
        }
      },
    );
  } catch (error) {
    showToast(error.message, "error");
  }
}
