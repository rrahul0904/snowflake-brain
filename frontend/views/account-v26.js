export const VIEW_ID = "v26-account";

import { candidate, refreshCandidate } from "../auth.js";
import { api, escapeHtml, getAuthProviders, getCandidateSessions, revokeAllCandidateSessions, revokeCandidateSession } from "../api.js";

export default async function mount(container) {
  await refreshCandidate().catch(() => {});
  const account = candidate();
  if (!account) {
    container.innerHTML = `<main class="v26-page"><header class="v26-page-intro"><p class="v26-kicker">Account</p><h1>Sign in to manage your account.</h1><p>Your sign-in methods, verification, membership identity, and active sessions are private to your candidate account.</p><button class="v26-btn primary" type="button" data-auth-intent="login">Sign In</button></header></main>`;
    return;
  }

  const [sessions, status, providers] = await Promise.all([
    getCandidateSessions().catch(() => ({ sessions: [] })),
    api("/api/account/status").catch(() => ({ email_verified: account.email_verified, identities: [] })),
    getAuthProviders().catch(() => ({ google: { enabled: false } })),
  ]);
  const methods = (account.sign_in_methods || ["email"]).map((item) => item === "google" ? "Google" : "Email");
  const verified = status.email_verified !== false;
  const identities = status.identities || [];
  const googleLinked = methods.includes("Google") || identities.some((item) => item.provider === "google");
  const canLinkGoogle = Boolean(providers.google?.enabled && !googleLinked);

  container.innerHTML = `<main class="v26-page v26-account-page">
    <header class="v26-page-intro"><p class="v26-kicker">Account & security</p><h1>${escapeHtml(account.display_name)}</h1><p>${escapeHtml(account.email)}</p></header>
    ${verified ? verifiedBanner(account) : verificationBanner(account)}
    <section class="v26-account-banner signed-in"><div><p class="v26-kicker">Identity</p><h2>Signed in with ${escapeHtml(methods.join(" + "))}</h2><p>All linked sign-in methods resolve to candidate #${escapeHtml(account.id)}. Your ${escapeHtml(account.plan)} membership, progress, and mock history stay on this single account.</p></div><div>${canLinkGoogle ? `<button class="v26-btn secondary" type="button" data-link-google>Link Google</button>` : ""}<a class="v26-btn secondary" href="#/membership">Membership</a></div></section>
    <section class="v26-account-security-grid">
      <article><span>Email verification</span><strong>${verified ? "Verified" : "Action required"}</strong><p>${verified ? "This candidate email has been confirmed." : "Verify this email so account recovery and identity changes have a trusted destination."}</p>${verified ? "" : `<button type="button" data-resend-verification>Resend verification email</button><small data-verification-status aria-live="polite"></small>`}</article>
      <article><span>Google sign-in</span><strong>${googleLinked ? "Linked" : providers.google?.enabled ? "Available" : "Not configured here"}</strong><p>${googleLinked ? "Google can sign in to this same candidate account." : providers.google?.enabled ? "Link Google without creating a second progress history." : "The Google sign-in implementation is present, but this deployment has no Google OAuth client credentials."}</p>${canLinkGoogle ? `<button type="button" data-link-google>Link Google account</button>` : ""}</article>
      <article><span>Recovery & privacy</span><strong>Account controls</strong><p>Change your email or password, review linked identities, export your data, or permanently delete the account.</p><a href="/static/account-management.html">Open account management →</a></article>
    </section>
    <section class="v26-account-sessions"><div class="v26-section-heading"><div><p class="v26-kicker">Security</p><h2>Active sessions</h2></div><button class="v26-btn secondary" type="button" data-revoke-all-sessions>Sign out all devices</button></div>${sessionList(sessions.sessions || [])}</section>
  </main>`;

  container.querySelectorAll("[data-link-google]").forEach((button) => button.addEventListener("click", () => {
    button.disabled = true;
    window.location.assign("/api/auth/google/start");
  }));
  container.querySelector("[data-resend-verification]")?.addEventListener("click", async (event) => {
    const button = event.currentTarget;
    const message = container.querySelector("[data-verification-status]");
    button.disabled = true;
    if (message) message.textContent = "Sending a new secure link…";
    try {
      const result = await api("/api/account/email-verification/resend", { method: "POST", body: "{}" });
      if (message) message.textContent = result.delivery === "queued" ? "Verification link queued in the local development outbox." : "Verification email sent. Check your inbox.";
    } catch (error) {
      if (message) message.textContent = error.message || "Unable to resend verification.";
      button.disabled = false;
    }
  });
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

function verifiedBanner(account) {
  return `<section class="v26-verification-banner verified"><div><span>Verified email</span><strong>${escapeHtml(account.email)}</strong></div><p>Your candidate email is confirmed for account recovery and security actions.</p></section>`;
}

function verificationBanner(account) {
  return `<section class="v26-verification-banner required"><div><span>Verification required</span><strong>Confirm ${escapeHtml(account.email)}</strong></div><p>Your study access remains available, but the account is not fully verified yet. Open the secure verification link sent to this address or resend it below.</p></section>`;
}

function sessionList(sessions) {
  if (!sessions.length) return `<p>No active sessions were found.</p>`;
  return `<div class="v26-session-list">${sessions.map((session) => `<article><div><strong>${session.current ? "This device" : "Signed-in device"}</strong><span>Last active ${formatDate(session.last_seen_at)} · Expires ${formatDate(session.expires_at)}</span></div><button class="v26-btn secondary" type="button" data-revoke-session="${escapeHtml(session.id)}">${session.current ? "Sign out" : "Revoke"}</button></article>`).join("")}</div>`;
}

function formatDate(value) {
  if (!value) return "—";
  return new Intl.DateTimeFormat(undefined, { year: "numeric", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }).format(new Date(value));
}
