import { submitFeedback } from "../api.js";
import { activeTrack } from "../ui.js";

const STORAGE_KEY = "snowflake-certification.feedback.v26";

function focusables(root) {
  return [...root.querySelectorAll("button:not([disabled]), input:not([disabled]), textarea:not([disabled]), a[href]")]
    .filter((node) => !node.hidden && node.offsetParent !== null);
}

export function renderFeedback() {
  let root = document.querySelector("#feedback-root");
  if (!root) {
    root = document.createElement("div");
    root.id = "feedback-root";
    document.body.appendChild(root);
  }
  root.innerHTML = `
    <button class="feedback-fab" type="button" data-feedback-open aria-label="Send feedback" aria-expanded="false">✦</button>
    <div class="feedback-backdrop" data-feedback-backdrop hidden></div>
    <aside class="feedback-panel" data-feedback-panel aria-label="Send feedback" aria-modal="true" role="dialog" hidden>
      <div class="feedback-head">
        <div><span>Feedback</span><strong>Send feedback</strong></div>
        <button type="button" data-feedback-close aria-label="Close feedback">×</button>
      </div>
      <p class="feedback-intro">Found a problem or have an idea for the guide? Send it directly to the project.</p>
      <form data-feedback-form>
        <label>Title <em>*</em><input name="title" required minlength="3" placeholder="Brief summary" /></label>
        <fieldset>
          <legend>Category</legend>
          <div class="feedback-categories">
            <label><input type="radio" name="category" value="bug" checked /><span>Bug</span></label>
            <label><input type="radio" name="category" value="feature" /><span>Feature Request</span></label>
            <label><input type="radio" name="category" value="content" /><span>Content Issue</span></label>
            <label><input type="radio" name="category" value="other" /><span>Other</span></label>
          </div>
        </fieldset>
        <label>Description<textarea name="description" rows="7" placeholder="Tell us what happened or what you would like to see..."></textarea></label>
        <label>Email <small>(optional)</small><input name="contact" type="email" placeholder="you@email.com" /></label>
        <button class="feedback-submit" type="submit">Submit feedback</button>
        <p class="feedback-status" data-feedback-status hidden aria-live="polite"></p>
      </form>
    </aside>`;

  const trigger = root.querySelector("[data-feedback-open]");
  const panel = root.querySelector("[data-feedback-panel]");
  const backdrop = root.querySelector("[data-feedback-backdrop]");
  let previousFocus = null;

  const open = () => {
    previousFocus = document.activeElement;
    panel.hidden = false;
    backdrop.hidden = false;
    requestAnimationFrame(() => {
      root.classList.add("feedback-open");
      trigger.setAttribute("aria-expanded", "true");
      panel.querySelector("input[name='title']")?.focus();
    });
  };

  const close = () => {
    root.classList.remove("feedback-open");
    trigger.setAttribute("aria-expanded", "false");
    window.setTimeout(() => {
      panel.hidden = true;
      backdrop.hidden = true;
    }, window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches ? 0 : 180);
    previousFocus?.focus?.();
  };

  trigger?.addEventListener("click", open);
  root.querySelector("[data-feedback-close]")?.addEventListener("click", close);
  backdrop?.addEventListener("click", close);
  panel?.addEventListener("keydown", (event) => {
    if (event.key === "Escape") { event.preventDefault(); close(); return; }
    if (event.key !== "Tab") return;
    const items = focusables(panel);
    if (!items.length) return;
    const first = items[0];
    const last = items[items.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  });

  root.querySelector("[data-feedback-form]")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = event.currentTarget.querySelector(".feedback-submit");
    const status = root.querySelector("[data-feedback-status]");
    const form = new FormData(event.currentTarget);
    const item = {
      title: String(form.get("title") || "").trim(),
      category: String(form.get("category") || "bug"),
      description: String(form.get("description") || "").trim(),
      contact: String(form.get("contact") || "").trim(),
      route: window.location.hash || "#/home",
      track_id: activeTrack(),
    };
    button.disabled = true;
    button.textContent = "Sending…";
    try {
      await submitFeedback(item);
      status.textContent = "Thanks — your feedback was submitted.";
      event.currentTarget.reset();
    } catch {
      const rows = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
      rows.push({ ...item, created_at: new Date().toISOString() });
      localStorage.setItem(STORAGE_KEY, JSON.stringify(rows.slice(-100)));
      status.textContent = "Saved locally. It can be submitted when the app is online again.";
    } finally {
      button.disabled = false;
      button.textContent = "Submit feedback";
      status.hidden = false;
    }
  });
}
