export const VIEW_ID = "v26-mock-start-complete";

import { cancelMockSession } from "../api.js";
import mountBase from "./mock-start-v26.js";

export default async function mount(container, params = {}) {
  await mountBase(container, params);
  const card = container.querySelector(".v26-interrupted-sitting");
  const resume = card?.querySelector("a[href*='session_id=']");
  if (!card || !resume || card.querySelector("[data-discard-sitting]")) return;
  const sessionId = Number(new URLSearchParams((resume.getAttribute("href") || "").split("?")[1] || "").get("session_id") || 0);
  if (!sessionId) return;
  const button = document.createElement("button");
  button.type = "button";
  button.className = "v26-btn secondary";
  button.dataset.discardSitting = "true";
  button.textContent = "Discard sitting";
  card.appendChild(button);
  button.addEventListener("click", async () => {
    button.disabled = true;
    button.textContent = "Removing…";
    try {
      await cancelMockSession(sessionId);
      await mountBase(container, params);
    } catch (error) {
      button.disabled = false;
      button.textContent = error.message || "Discard sitting";
    }
  });
}
