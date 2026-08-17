import { candidate, linkGoogle, logIn, logOut, signUp } from "../auth.js";
import { api, createBillingCheckout, createBillingPortal, getAuthProviders, getPendingGoogleLink } from "../api.js";

let bound = false;
let pendingChecked = false;
let providersPromise = null;

export function renderCandidateAccess() {
  let root = document.querySelector("#candidate-access-root");
  if (!root) {
    root = document.createElement("div");
    root.id = "candidate-access-root";
    document.body.appendChild(root);
  }
  if (!bound) {
    document.addEventListener("click", handleClick);
    bound = true;
  }
  if (!pendingChecked) {
    pendingChecked = true;
    maybeOpenPendingGoogleLink();
  }
}

function providers() {
  providersPromise ||= getAuthProviders().catch(() => ({ google: { enabled: false }, billing: { enabled: false } }));
  return providersPromise;
}

function modalShell(inner) {
  return `<div class="v26-modal-backdrop" data-auth-close></div><section class="v26-auth-modal" role="dialog" aria-modal="true"><button class="v26-modal-close" type="button" data-auth-close aria-label="Close">×</button>${inner}</section>`;
}

function openAuth(intent = "login") {
  const signup = intent === "signup";
  const root = document.querySelector("#candidate-access-root");
  root.innerHTML = modalShell(`<p class="v26-kicker">Candidate account</p><h2 id="candidate-auth-title">${signup ? "Create account" : "Sign in"}</h2><p>${signup ? "Create a Free account to save your SnowPro progress, practice history, and readiness evidence." : "Sign in to continue with your saved progress and membership."}</p><button class="v26-btn secondary v26-google-auth" type="button" data-google-auth disabled>G&nbsp;&nbsp;Continue with Google</button><p class="v26-google-status" data-google-status aria-live="polite"></p><div class="v26-auth-divider"><span>or</span></div><form data-auth-form data-intent="${intent}" novalidate>${signup ? `<label>Name<input name="display_name" autocomplete="name" minlength="2" maxlength="120" required /></label>` : ""}<label>Email<input name="email" type="email" autocomplete="email" maxlength="320" required /></label><label>Password<input name="password" type="password" autocomplete="${signup ? "new-password" : "current-password"}" minlength="8" maxlength="256" required /></label>${signup ? "" : `<button class="v26-text-action" type="button" data-password-reset>Forgot password?</button>`}<button class="v26-btn primary" type="submit">${signup ? "Create Free Account" : "Sign In"}</button><p class="v26-form-status" data-auth-status aria-live="polite"></p></form><p class="v26-auth-switch">${signup ? "Already have an account?" : "Don't have an account?"} <button type="button" data-auth-intent="${signup ? "login" : "signup"}">${signup ? "Sign in →" : "Create account →"}</button></p>`);
  hydrateGoogleButton(root);
  root.querySelector("input")?.focus();
  root.querySelector("[data-auth-form]")?.addEventListener("submit", submitAuth);
}

async function hydrateGoogleButton(root) {
  const button = root.querySelector("[data-google-auth]");
  const status = root.querySelector("[data-google-status]");
  if (!button) return;
  const config = await providers();
  if (!root.contains(button)) return;
  button.textContent = "G  Continue with Google";
  if (config.google?.enabled) {
    button.disabled = false;
    button.title = "Continue securely with Google";
    if (status) status.textContent = "";
  } else {
    button.disabled = true;
    button.title = "Google OAuth credentials are not configured in this environment.";
    if (status) status.textContent = "Google sign-in is ready in the product and turns on when this deployment has its Google OAuth client configured.";
  }
}

function openPasswordReset(prefill = "") {
  const root = document.querySelector("#candidate-access-root");
  root.innerHTML = modalShell(`<p class="v26-kicker">Account recovery</p><h2>Reset your password</h2><p>Enter the email on your candidate account. If it exists, we’ll send a secure, expiring reset link.</p><form data-reset-request novalidate><label>Email<input name="email" type="email" autocomplete="email" value="${escapeText(prefill)}" maxlength="320" required /></label><button class="v26-btn primary" type="submit">Send reset link</button><p class="v26-form-status" data-auth-status aria-live="polite"></p></form><p class="v26-auth-switch"><button type="button" data-auth-intent="login">← Back to sign in</button></p>`);
  const form = root.querySelector("[data-reset-request]");
  root.querySelector("input")?.focus();
  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const status = form.querySelector("[data-auth-status]");
    const button = form.querySelector("button[type=submit]");
    const email = String(new FormData(form).get("email") || "").trim();
    if (!email.includes("@")) {
      status.textContent = "Enter a valid email address.";
      return;
    }
    button.disabled = true;
    status.textContent = "Requesting a secure link…";
    try {
      await api("/api/auth/password-reset/request", { method: "POST", body: JSON.stringify({ email }) });
      status.textContent = "If an account exists for that email, a reset link has been sent. The link expires automatically.";
      button.textContent = "Reset link requested";
    } catch (error) {
      status.textContent = error.message || "Unable to request a reset link.";
      button.disabled = false;
    }
  });
}

function openVerificationNotice(account, delivery = "") {
  const root = document.querySelector("#candidate-access-root");
  const local = delivery === "queued";
  root.innerHTML = modalShell(`<p class="v26-kicker">Verify your email</p><h2>One quick security step</h2><p>We created your candidate account for <strong>${escapeText(account?.email || "your email")}</strong>.</p><div class="v26-verification-callout"><strong>Check your email and open the verification link.</strong><span>${local ? "This local development environment queued the message in its development outbox. A configured production mailer sends the same secure link to the candidate." : "The verification link is single-use and expires automatically."}</span></div><div class="v26-modal-actions"><a class="v26-btn secondary" href="#/account" data-auth-close>Account security</a><button class="v26-btn primary" type="button" data-auth-close>Continue to guide</button></div>`);
}

async function maybeOpenPendingGoogleLink() {
  try {
    const pending = await getPendingGoogleLink();
    if (pending?.pending) openGoogleLink(pending);
  } catch {}
}

function openGoogleLink(pending) {
  const root = document.querySelector("#candidate-access-root");
  if (!root) return;
  root.innerHTML = modalShell(`<p class="v26-kicker">Secure account linking</p><h2 id="google-link-title">Link Google to your existing account</h2><p>We found an existing Snowflake Certification Guide account for ${escapeText(pending.email || "this email")}. Sign in once with its password. Your membership, progress, and mock history stay on the same candidate account.</p><form data-google-link-form novalidate><label>Existing password<input name="password" type="password" autocomplete="current-password" minlength="8" maxlength="256" required /></label><button class="v26-btn primary" type="submit">Verify and Link Google</button><p class="v26-form-status" data-auth-status aria-live="polite"></p></form>`);
  root.querySelector("input")?.focus();
  root.querySelector("[data-google-link-form]")?.addEventListener("submit", submitGoogleLink);
}

async function submitGoogleLink(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const status = form.querySelector("[data-auth-status]");
  const button = form.querySelector("button[type=submit]");
  const password = String(new FormData(form).get("password") || "");
  if (password.length < 8) {
    status.textContent = "Enter the password for your existing account.";
    return;
  }
  button.disabled = true;
  status.textContent = "Linking securely…";
  try {
    await linkGoogle(password);
    closeModal();
    window.location.hash = "#/home";
  } catch (error) {
    status.textContent = error.message || "Unable to link Google";
    button.disabled = false;
  }
}

function openPremiumNotice(message = "Checkout is not enabled in this environment. No membership change, payment, or tax charge has been made.") {
  const root = document.querySelector("#candidate-access-root");
  root.innerHTML = modalShell(`<p class="v26-kicker">Paid access</p><h2 id="membership-change-title">Secure billing</h2><p>${escapeText(message)}</p><p>Premium access is activated only after a verified server-to-server billing event. A success URL, browser flag, edited cookie, or reusable license key can never grant paid access.</p><a class="v26-btn secondary" href="#/membership" data-auth-close>Back to Membership</a>`);
}

function closeModal() {
  const root = document.querySelector("#candidate-access-root");
  if (root) root.innerHTML = "";
}

async function submitAuth(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const button = form.querySelector("button[type=submit]");
  const status = form.querySelector("[data-auth-status]");
  const values = Object.fromEntries(new FormData(form));
  if (!String(values.email || "").includes("@")) {
    status.textContent = "Enter a valid email address.";
    return;
  }
  if (String(values.password || "").length < 8) {
    status.textContent = "Password must contain at least 8 characters.";
    return;
  }
  if (form.dataset.intent === "signup" && String(values.display_name || "").trim().length < 2) {
    status.textContent = "Name must contain at least 2 characters.";
    return;
  }
  button.disabled = true;
  status.textContent = "Working…";
  try {
    if (form.dataset.intent === "signup") {
      const result = await signUp({ display_name: values.display_name, email: values.email, password: values.password });
      openVerificationNotice(result.candidate, result.verification_delivery);
      return;
    }
    const result = await logIn({ email: values.email, password: values.password });
    if (result.candidate?.email_verified === false) {
      openVerificationNotice(result.candidate);
      return;
    }
    closeModal();
  } catch (error) {
    status.textContent = error.message || "Unable to continue";
    button.disabled = false;
  }
}

async function startPaidCheckout(planCode) {
  if (!candidate()) {
    openAuth("login");
    return;
  }
  try {
    const result = await createBillingCheckout(planCode);
    if (!result?.checkout_url) throw new Error("Checkout did not return a secure destination.");
    window.location.assign(result.checkout_url);
  } catch (error) {
    openPremiumNotice(error.message || "Checkout is not available.");
  }
}

async function openBillingPortal() {
  if (!candidate()) {
    openAuth("login");
    return;
  }
  try {
    const result = await createBillingPortal();
    if (!result?.portal_url) throw new Error("Billing management did not return a secure destination.");
    window.location.assign(result.portal_url);
  } catch (error) {
    openPremiumNotice(error.message || "Subscription management is not available.");
  }
}

async function handleClick(event) {
  const authIntent = event.target.closest("[data-auth-intent]");
  if (authIntent) {
    event.preventDefault();
    openAuth(authIntent.dataset.authIntent);
    return;
  }
  const reset = event.target.closest("[data-password-reset]");
  if (reset) {
    event.preventDefault();
    const email = reset.closest("form")?.querySelector("input[name=email]")?.value || "";
    openPasswordReset(email);
    return;
  }
  const google = event.target.closest("[data-google-auth]");
  if (google && !google.disabled) {
    event.preventDefault();
    window.location.assign("/api/auth/google/start");
    return;
  }
  if (event.target.closest("[data-auth-close]")) {
    closeModal();
    return;
  }
  const logout = event.target.closest("[data-auth-logout]");
  if (logout) {
    event.preventDefault();
    logout.disabled = true;
    await logOut().catch(() => {});
    window.location.hash = "#/home";
    return;
  }
  const portal = event.target.closest("[data-billing-portal]");
  if (portal) {
    event.preventDefault();
    await openBillingPortal();
    return;
  }
  const paid = event.target.closest("[data-plan-checkout]");
  if (paid) {
    event.preventDefault();
    await startPaidCheckout(paid.dataset.planCheckout);
    return;
  }
  const premium = event.target.closest("[data-premium-unavailable]");
  if (premium) {
    event.preventDefault();
    openPremiumNotice();
  }
}

function escapeText(value) {
  const node = document.createElement("div");
  node.textContent = String(value ?? "");
  return node.innerHTML;
}
