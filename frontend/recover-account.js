const form = document.getElementById("recovery-form");
const email = document.getElementById("email");
const statusBox = document.getElementById("status");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = event.submitter;
  button.disabled = true;
  statusBox.textContent = "Submitting your recovery request…";
  try {
    await fetch("/api/auth/password-reset/request", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email.value }),
    });
    // Deliberately generic to preserve account-enumeration resistance even if
    // the server/provider behavior differs for an unknown address.
    statusBox.textContent = "If an active account matches that email, a password reset link has been sent. Check your inbox and spam folder.";
    email.value = "";
  } catch (_) {
    statusBox.textContent = "If an active account matches that email, a password reset link has been sent. Check your inbox and spam folder.";
  } finally {
    button.disabled = false;
  }
});
