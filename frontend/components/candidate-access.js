import { logIn, logOut, signUp } from "../auth.js";

let bound = false;

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
}

function openAuth(intent = "login") {
  const signup = intent === "signup";
  const root = document.querySelector("#candidate-access-root");
  root.innerHTML = `<div class="v26-modal-backdrop" data-auth-close></div><section class="v26-auth-modal" role="dialog" aria-modal="true" aria-labelledby="candidate-auth-title"><button class="v26-modal-close" type="button" data-auth-close aria-label="Close">×</button><p class="v26-kicker">Candidate account</p><h2 id="candidate-auth-title">${signup ? "Create account" : "Sign in"}</h2><p>${signup ? "Create a Free account to save progress and use diagnostic practice." : "Sign in to continue with your saved progress and membership."}</p><form data-auth-form data-intent="${intent}" novalidate>${signup ? `<label>Name<input name="display_name" autocomplete="name" minlength="2" maxlength="120" required /></label>` : ""}<label>Email<input name="email" type="email" autocomplete="email" maxlength="320" required /></label><label>Password<input name="password" type="password" autocomplete="${signup ? "new-password" : "current-password"}" minlength="8" maxlength="256" required /></label><button class="v26-btn primary" type="submit">${signup ? "Create Free Account" : "Sign In"}</button><p class="v26-form-status" data-auth-status aria-live="polite"></p></form><p class="v26-auth-switch">${signup ? "Already have an account?" : "Don't have an account?"} <button type="button" data-auth-intent="${signup ? "login" : "signup"}">${signup ? "Sign in →" : "Create account →"}</button></p></section>`;
  root.querySelector("input")?.focus();
  root.querySelector("[data-auth-form]")?.addEventListener("submit", submitAuth);
}

function openPremiumNotice() {
  const root = document.querySelector("#candidate-access-root");
  root.innerHTML = `<div class="v26-modal-backdrop" data-auth-close></div><section class="v26-auth-modal v26-plan-modal" role="dialog" aria-modal="true" aria-labelledby="membership-change-title"><button class="v26-modal-close" type="button" data-auth-close aria-label="Close">×</button><p class="v26-kicker">Paid access</p><h2 id="membership-change-title">Checkout is not enabled</h2><p>No membership change, payment, or tax charge has been made. When billing is connected, applicable taxes will be calculated at checkout based on location.</p><a class="v26-btn secondary" href="#/membership" data-auth-close>Back to Membership</a></section>`;
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
      await signUp({ display_name: values.display_name, email: values.email, password: values.password });
    } else {
      await logIn({ email: values.email, password: values.password });
    }
    closeModal();
  } catch (error) {
    status.textContent = error.message || "Unable to continue";
    button.disabled = false;
  }
}

async function handleClick(event) {
  const authIntent = event.target.closest("[data-auth-intent]");
  if (authIntent) {
    event.preventDefault();
    openAuth(authIntent.dataset.authIntent);
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
  const premium = event.target.closest("[data-premium-unavailable]");
  if (premium) {
    event.preventDefault();
    openPremiumNotice();
  }
}
