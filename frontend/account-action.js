const title = document.getElementById("title");
const intro = document.getElementById("intro");
const statusBox = document.getElementById("status");
const passwordForm = document.getElementById("password-form");
const resetButton = document.getElementById("reset-button");

function parameters() {
  const fragment = window.location.hash || "";
  const fragmentQuery = fragment.includes("?") ? fragment.split("?", 2)[1] : "";
  const source = fragmentQuery || window.location.search.replace(/^\?/, "");
  return new URLSearchParams(source);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  let payload = {};
  try { payload = await response.json(); } catch (_) { payload = {}; }
  if (!response.ok) {
    const detail = payload?.detail;
    const message = typeof detail === "string" ? detail : detail?.message || "This secure link could not be completed.";
    throw new Error(message);
  }
  return payload;
}

function setStatus(message, kind = "neutral") {
  statusBox.textContent = message;
  statusBox.dataset.kind = kind;
}

async function completeSimpleAction(purpose, token) {
  const endpoints = {
    verify_email: "/api/auth/email-verification/confirm",
    change_email: "/api/auth/change-email/confirm",
  };
  const labels = {
    verify_email: ["Verify your email", "We’re confirming this email address for your candidate account.", "Your email is verified. You can return to the guide."],
    change_email: ["Confirm your new email", "We’re securely updating your candidate account email.", "Your email has been changed. For security, existing sessions were signed out; sign in again with the new email."],
  };
  const label = labels[purpose];
  title.textContent = label[0];
  intro.textContent = label[1];
  setStatus("Confirming…");
  try {
    await api(endpoints[purpose], { method: "POST", body: JSON.stringify({ token }) });
    setStatus(label[2], "success");
  } catch (error) {
    setStatus(error.message, "error");
  }
}

function configurePasswordReset(token) {
  title.textContent = "Reset your password";
  intro.textContent = "Choose a new password. Completing the reset signs out all existing sessions.";
  setStatus("Your reset link is ready.");
  passwordForm.classList.remove("hidden");
  passwordForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const password = document.getElementById("new-password").value;
    const confirm = document.getElementById("confirm-password").value;
    if (password.length < 8) {
      setStatus("Use at least 8 characters for your new password.", "error");
      return;
    }
    if (password !== confirm) {
      setStatus("The two password entries do not match.", "error");
      return;
    }
    resetButton.disabled = true;
    setStatus("Updating your password…");
    try {
      await api("/api/auth/password-reset/confirm", {
        method: "POST",
        body: JSON.stringify({ token, new_password: password }),
      });
      passwordForm.classList.add("hidden");
      setStatus("Your password has been reset. All existing sessions were signed out; sign in again with your new password.", "success");
    } catch (error) {
      setStatus(error.message, "error");
      resetButton.disabled = false;
    }
  });
}

const params = parameters();
const purpose = params.get("purpose") || "";
const token = params.get("token") || "";

if (!token || !["verify_email", "password_reset", "change_email"].includes(purpose)) {
  title.textContent = "Invalid account link";
  intro.textContent = "This page requires a valid secure account-action link.";
  setStatus("The link is incomplete or invalid. Request a fresh link from account management or the sign-in screen.", "error");
} else if (purpose === "password_reset") {
  configurePasswordReset(token);
} else {
  completeSimpleAction(purpose, token);
}
