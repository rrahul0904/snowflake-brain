export const VIEW_ID = "v26-account-action";

import { api, escapeHtml } from "../api.js";

const PURPOSES = {
  verify_email: {
    title: "Verify your email",
    intro: "Confirm this email address for your Snowflake Certification Guide candidate account.",
    endpoint: "/api/auth/email-verification/confirm",
    success: "Your email is verified. Your account security status has been updated.",
  },
  change_email: {
    title: "Confirm your new email",
    intro: "Confirm the new email address for your candidate account.",
    endpoint: "/api/auth/change-email/confirm",
    success: "Your email has been changed. Existing sessions were signed out for security; sign in again with the new email.",
  },
};

export default async function mount(container, params = {}) {
  const purpose = String(params.purpose || "");
  const token = String(params.token || "");
  if (!token || !["verify_email", "password_reset", "change_email"].includes(purpose)) {
    renderMessage(container, "Invalid or incomplete link", "This secure account link is missing required information or is no longer valid.", "error");
    return;
  }
  if (purpose === "password_reset") {
    renderPasswordReset(container, token);
    return;
  }
  const config = PURPOSES[purpose];
  renderShell(container, config.title, config.intro, "Confirming your secure link…", "working");
  try {
    await api(config.endpoint, { method: "POST", body: JSON.stringify({ token }) });
    renderMessage(container, config.title, config.success, "success");
  } catch (error) {
    renderMessage(container, config.title, error.message || "This secure link could not be completed.", "error");
  }
}

function renderPasswordReset(container, token) {
  container.innerHTML = `<main class="v26-page v26-account-action-page"><section class="v26-account-action-card"><p class="v26-kicker">Account security</p><h1>Reset your password</h1><p>Choose a new password. Completing the reset signs out every existing session on the account.</p><form data-password-reset novalidate><label>New password<input name="password" type="password" autocomplete="new-password" minlength="8" maxlength="256" required /></label><label>Confirm new password<input name="confirm" type="password" autocomplete="new-password" minlength="8" maxlength="256" required /></label><button class="v26-btn primary" type="submit">Set new password</button><p class="v26-form-status" data-action-status role="status" aria-live="polite"></p></form><div class="v26-account-action-links"><a href="#/home">Return to guide</a><button type="button" data-auth-intent="login">Sign in</button></div></section></main>`;
  const form = container.querySelector("[data-password-reset]");
  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const status = form.querySelector("[data-action-status]");
    const button = form.querySelector("button[type=submit]");
    const values = Object.fromEntries(new FormData(form));
    const password = String(values.password || "");
    if (password.length < 8) {
      status.textContent = "Use at least 8 characters for your new password.";
      return;
    }
    if (password !== String(values.confirm || "")) {
      status.textContent = "The two password entries do not match.";
      return;
    }
    button.disabled = true;
    status.textContent = "Updating your password…";
    try {
      await api("/api/auth/password-reset/confirm", { method: "POST", body: JSON.stringify({ token, new_password: password }) });
      renderMessage(container, "Password updated", "Your password has been reset and all previous sessions were signed out. Sign in again with your new password.", "success", true);
    } catch (error) {
      status.textContent = error.message || "This reset link could not be completed.";
      button.disabled = false;
    }
  });
}

function renderShell(container, title, message, status, kind) {
  container.innerHTML = `<main class="v26-page v26-account-action-page"><section class="v26-account-action-card"><p class="v26-kicker">Account security</p><h1>${escapeHtml(title)}</h1><p>${escapeHtml(message)}</p><div class="v26-account-action-status ${escapeHtml(kind)}" role="status" aria-live="polite">${escapeHtml(status)}</div><div class="v26-account-action-links"><a href="#/home">Return to guide</a></div></section></main>`;
}

function renderMessage(container, title, message, kind = "neutral", signedOut = false) {
  container.innerHTML = `<main class="v26-page v26-account-action-page"><section class="v26-account-action-card"><p class="v26-kicker">Account security</p><h1>${escapeHtml(title)}</h1><div class="v26-account-action-status ${escapeHtml(kind)}" role="status" aria-live="polite">${escapeHtml(message)}</div><div class="v26-account-action-links"><a href="#/home">Return to guide</a>${signedOut ? `<button type="button" data-auth-intent="login">Sign in</button>` : `<a href="#/account">Account security</a>`}</div></section></main>`;
}
