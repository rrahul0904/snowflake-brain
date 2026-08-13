import { activeTrack } from "../ui.js";

const STORAGE_KEY = "snowflake-certification.feedback.v26";

export function renderFeedback() {
  let root = document.querySelector("#feedback-root");
  if (!root) {
    root = document.createElement("div");
    root.id = "feedback-root";
    document.body.appendChild(root);
  }
  root.innerHTML = `
    <button class="feedback-fab" type="button" data-feedback-open aria-label="Send feedback">▱</button>
    <aside class="feedback-panel" data-feedback-panel aria-label="Send feedback" hidden>
      <div class="feedback-head">
        <strong>Send feedback</strong>
        <button type="button" data-feedback-close aria-label="Close feedback">×</button>
      </div>
      <form data-feedback-form>
        <label>Title <em>*</em><input name="title" required minlength="3" placeholder="Brief summary of the issue" /></label>
        <fieldset>
          <legend>Category</legend>
          <div class="feedback-categories">
            <label><input type="radio" name="category" value="bug" checked /><span>Bug</span></label>
            <label><input type="radio" name="category" value="feature" /><span>Feature Request</span></label>
            <label><input type="radio" name="category" value="content" /><span>Content Issue</span></label>
            <label><input type="radio" name="category" value="other" /><span>Other</span></label>
          </div>
        </fieldset>
        <label>Description<textarea name="description" rows="4" placeholder="Any additional details..."></textarea></label>
        <label>Email <small>(optional)</small><input name="contact" type="email" placeholder="you@email.com" /></label>
        <button class="feedback-submit" type="submit">Submit feedback</button>
        <p class="feedback-status" data-feedback-status hidden></p>
      </form>
    </aside>`;

  const panel = root.querySelector("[data-feedback-panel]");
  root.querySelector("[data-feedback-open]")?.addEventListener("click", () => {
    panel.hidden = false;
    panel.querySelector("input[name='title']")?.focus();
  });
  root.querySelector("[data-feedback-close]")?.addEventListener("click", () => { panel.hidden = true; });
  root.querySelector("[data-feedback-form]")?.addEventListener("submit", (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const item = {
      title: String(form.get("title") || "").trim(),
      category: String(form.get("category") || "bug"),
      description: String(form.get("description") || "").trim(),
      contact: String(form.get("contact") || "").trim(),
      route: window.location.hash || "#/home",
      track_id: activeTrack(),
      created_at: new Date().toISOString(),
    };
    const rows = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
    rows.push(item);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(rows.slice(-100)));
    const status = root.querySelector("[data-feedback-status]");
    status.textContent = "Thanks — your feedback was saved in this browser.";
    status.hidden = false;
    event.currentTarget.reset();
  });
}
