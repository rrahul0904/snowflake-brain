export const VIEW_ID = "v26-account";

import { candidate, refreshCandidate } from "../auth.js";
import { escapeHtml, getCandidateSessions, revokeAllCandidateSessions, revokeCandidateSession } from "../api.js";

export default async function mount(container) {
  await refreshCandidate().catch(() => {});
  const account = candidate();
  if (!account) {
    container.innerHTML = `<main class="v26-page"><header class="v26-page-intro"><p class="v26-kicker">Account</p><h1>Sign in to manage your account.</h1><p>Your sign-in methods, membership identity, and active sessions are private to your candidate account.</p><button class="v26-btn primary" type="button" data-auth-intent="login">Sign In</button></header></main>`;
    return;
  }
  const sessions = await getCandidateSessions().catch(() => ({ sessions: [] }));
  const methods = (account.sign_in_methods || ["email"]).map((item) => item === "google" ? "Google" : "Email");
  container.innerHTML = `<main class="v26-page v26-account-page"><header class="v26-page-intro"><p class="v26-kicker">Account</p><h1>${escapeHtml(account.display_name)}</h1><p>${escapeHtml(account.email)}</p></header><section class="v26-account-banner signed-in"><div><p class="v26-kicker">Identity</p><h2>Signed in with ${escapeHtml(methods.join(" + "))}</h2><p>All linked sign-in methods resolve to candidate #${escapeHtml(account.id)}. Your ${escapeHtml(account.plan)} membership, progress, and mock history stay on this single account.</p></div><div><a class="v26-btn secondary" href="#/membership">Membership</a></div></section><section class="v26-account-sessions"><div class="v26-section-heading"><div><p class="v26-kicker">Security</p><h2>Active sessions</h2></div><button class="v26-btn secondary" type="button" data-revoke-all-sessions>Sign out all devices</button></div>${sessionList(sessions.sessions || [])}</section></main>`;
  container.querySelectorAll("[data-revoke-session]").forEach((button) => button.addEventListener("click", async () => {
    button.disabled = true;
    try {
      await revokeCandidateSession(button.dataset.revokeSession);
      await mount(container);
    } catch (error) {
      button.disabled = false;
      window.dispatchEvent(new CustomEvent("app-error", { detail: error }));
    }
  }));
  container.querySelector("[data-revoke-all-sessions]")?.addEventListener("click", async (event) => {
    event.currentTarget.disabled = true;
    await revokeAllCandidateSessions().catch(() => {});
    window.location.hash = "#/home";
    window.location.reload();
  });
}

function sessionList(sessions) {
  if (!sessions.length) return `<p>No active sessions were found.</p>`;
  return `<div class="v26-session-list">${sessions.map((session) => `<article><div><strong>${session.current ? "This device" : "Signed-in device"}</strong><span>Last active ${formatDate(session.last_seen_at)} · Expires ${formatDate(session.expires_at)}</span></div><button class="v26-btn secondary" type="button" data-revoke-session="${escapeHtml(session.id)}">${session.current ? "Sign out" : "Revoke"}</button></article>`).join("")}</div>`;
}

function formatDate(value) {
  if (!value) return "—";
  return new Intl.DateTimeFormat(undefined, { year: "numeric", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }).format(new Date(value));
}
