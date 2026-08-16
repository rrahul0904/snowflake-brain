const statusBox = document.getElementById("page-status");
const content = document.getElementById("content");
let account = null;

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
    const message = typeof detail === "string" ? detail : detail?.message || "The account request could not be completed.";
    const error = new Error(message);
    error.status = response.status;
    error.code = detail?.code || "request_failed";
    throw error;
  }
  return { payload, response };
}

function setStatus(message, kind = "neutral") {
  statusBox.textContent = message;
  statusBox.dataset.kind = kind;
}

function text(value) {
  return value == null || value === "" ? "—" : String(value);
}

function formatDate(value) {
  if (!value) return "—";
  const parsed = new Date(String(value).replace(" ", "T").replace(/Z?$/, "Z"));
  return Number.isNaN(parsed.getTime()) ? String(value) : parsed.toLocaleString();
}

function renderEmail() {
  const summary = document.getElementById("email-summary");
  summary.innerHTML = "";
  const email = document.createElement("div");
  email.className = "row";
  const left = document.createElement("div");
  left.innerHTML = `<strong>${text(account.email)}</strong><div class="muted">Account email</div>`;
  const badge = document.createElement("span");
  badge.className = "badge";
  badge.textContent = account.email_verified ? "Verified" : "Verification needed";
  email.append(left, badge);
  summary.appendChild(email);

  const actions = document.getElementById("verification-actions");
  actions.innerHTML = "";
  if (!account.email_verified) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = "Resend verification email";
    button.addEventListener("click", async () => {
      button.disabled = true;
      setStatus("Sending a fresh verification link…");
      try {
        await api("/api/account/email-verification/resend", { method: "POST", body: "{}" });
        setStatus("A fresh verification link has been queued for your account email.", "success");
      } catch (error) {
        setStatus(error.message, "error");
      } finally {
        button.disabled = false;
      }
    });
    actions.appendChild(button);
  }
}

function renderPassword() {
  document.getElementById("password-summary").textContent = account.password_login_enabled
    ? "Password sign-in is enabled. Updating it signs out every existing session."
    : "This account currently relies on a linked identity. Add a password before unlinking your only external sign-in method.";
  document.getElementById("current-password-wrap").classList.toggle("hidden", !account.password_login_enabled);
  document.getElementById("delete-password-wrap").classList.toggle("hidden", !account.password_login_enabled);
}

function renderIdentities() {
  const root = document.getElementById("identities");
  root.innerHTML = "";
  if (!account.identities?.length) {
    root.innerHTML = '<p class="muted">No external identities are linked.</p>';
    return;
  }
  account.identities.forEach((identity) => {
    const row = document.createElement("div");
    row.className = "row";
    const info = document.createElement("div");
    info.innerHTML = `<strong>${text(identity.provider)}</strong><div class="muted">${text(identity.provider_email)} · linked ${formatDate(identity.created_at)}</div>`;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "secondary";
    button.textContent = "Unlink";
    button.addEventListener("click", async () => {
      if (!window.confirm(`Unlink ${identity.provider}?`)) return;
      button.disabled = true;
      try {
        await api(`/api/account/identities/${identity.id}`, { method: "DELETE" });
        setStatus(`${identity.provider} was unlinked.`, "success");
        await load();
      } catch (error) {
        setStatus(error.message, "error");
        button.disabled = false;
      }
    });
    row.append(info, button);
    root.appendChild(row);
  });
}

async function renderSessions() {
  const root = document.getElementById("sessions");
  root.innerHTML = '<p class="muted">Loading sessions…</p>';
  try {
    const { payload } = await api("/api/auth/sessions");
    const sessions = payload.sessions || [];
    root.innerHTML = "";
    if (!sessions.length) {
      root.innerHTML = '<p class="muted">No active sessions.</p>';
      return;
    }
    sessions.forEach((session) => {
      const row = document.createElement("div");
      row.className = "row";
      const info = document.createElement("div");
      const current = session.current ? " · current browser" : "";
      info.innerHTML = `<strong>Session ${text(session.id)}${current}</strong><div class="muted">Created ${formatDate(session.created_at)} · last seen ${formatDate(session.last_seen_at)}</div>`;
      const button = document.createElement("button");
      button.type = "button";
      button.className = "secondary";
      button.textContent = "Revoke";
      button.addEventListener("click", async () => {
        button.disabled = true;
        try {
          await api("/api/auth/sessions/revoke", {
            method: "POST",
            body: JSON.stringify({ session_id: session.id }),
          });
          setStatus("Session revoked.", "success");
          await renderSessions();
        } catch (error) {
          setStatus(error.message, "error");
          button.disabled = false;
        }
      });
      row.append(info, button);
      root.appendChild(row);
    });
  } catch (error) {
    root.innerHTML = `<p class="muted">${error.message}</p>`;
  }
}

function renderAudit() {
  const root = document.getElementById("audit");
  root.innerHTML = "";
  const rows = account.audit || [];
  if (!rows.length) {
    root.innerHTML = '<p class="muted">No account lifecycle activity yet.</p>';
    return;
  }
  rows.forEach((event) => {
    const row = document.createElement("div");
    row.className = "row";
    const label = document.createElement("div");
    label.innerHTML = `<strong>${String(event.action || "account event").replaceAll("_", " ")}</strong><div class="muted">${formatDate(event.created_at)}</div>`;
    row.appendChild(label);
    root.appendChild(row);
  });
}

function renderDeletion() {
  const blocker = document.getElementById("deletion-blocker");
  const button = document.getElementById("delete-button");
  if (account.can_delete) {
    blocker.classList.add("hidden");
    button.disabled = false;
  } else {
    blocker.textContent = "Account deletion is blocked while a recurring paid subscription is active. Cancel it and wait for the paid period to end before deleting your account.";
    blocker.classList.remove("hidden");
    button.disabled = true;
  }
}

async function load() {
  try {
    const { payload } = await api("/api/account/status");
    account = payload;
    renderEmail();
    renderPassword();
    renderIdentities();
    renderAudit();
    renderDeletion();
    await renderSessions();
    content.classList.remove("hidden");
    setStatus(`Signed in as ${account.email}.`, "success");
  } catch (error) {
    content.classList.add("hidden");
    if (error.status === 401) {
      setStatus("Sign in to manage your candidate account.", "error");
    } else {
      setStatus(error.message, "error");
    }
  }
}

document.getElementById("change-email-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = document.getElementById("new-email");
  const button = event.submitter;
  button.disabled = true;
  try {
    await api("/api/account/change-email/request", {
      method: "POST",
      body: JSON.stringify({ new_email: input.value }),
    });
    input.value = "";
    setStatus("A confirmation link has been sent to the new email address. Your email changes only after that link is confirmed.", "success");
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    button.disabled = false;
  }
});

document.getElementById("change-password-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = event.submitter;
  button.disabled = true;
  const current = document.getElementById("current-password").value;
  const next = document.getElementById("new-password").value;
  try {
    await api("/api/account/change-password", {
      method: "POST",
      body: JSON.stringify({ current_password: current || null, new_password: next }),
    });
    setStatus("Password updated. All sessions were signed out; sign in again with your new password.", "success");
    window.setTimeout(() => { window.location.href = "/#/home"; }, 1000);
  } catch (error) {
    setStatus(error.message, "error");
    button.disabled = false;
  }
});

document.getElementById("revoke-all").addEventListener("click", async () => {
  if (!window.confirm("Sign out every device, including this browser?")) return;
  try {
    await api("/api/auth/sessions/revoke-all", { method: "POST", body: "{}" });
    setStatus("All sessions were revoked. Sign in again to continue.", "success");
    window.setTimeout(() => { window.location.href = "/#/home"; }, 800);
  } catch (error) {
    setStatus(error.message, "error");
  }
});

document.getElementById("export-data").addEventListener("click", async (event) => {
  const button = event.currentTarget;
  button.disabled = true;
  setStatus("Preparing your portable data export…");
  try {
    const response = await fetch("/api/account/export", { credentials: "include" });
    if (!response.ok) throw new Error("Your data export could not be created.");
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "snowflake-certification-account-export.json";
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
    setStatus("Your data export was created.", "success");
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    button.disabled = false;
  }
});

document.getElementById("delete-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!account?.can_delete) return;
  const confirmation = document.getElementById("delete-confirmation").value;
  const password = document.getElementById("delete-password").value;
  if (confirmation !== "DELETE") {
    setStatus("Type DELETE exactly to confirm permanent deletion.", "error");
    return;
  }
  if (!window.confirm("Permanently delete this candidate account and its application data? This cannot be undone.")) return;
  const button = document.getElementById("delete-button");
  button.disabled = true;
  try {
    const { payload } = await api("/api/account", {
      method: "DELETE",
      body: JSON.stringify({ confirmation, password: password || null }),
    });
    setStatus(`Account deleted. Deletion receipt: ${payload.receipt_id}`, "success");
    content.classList.add("hidden");
    window.setTimeout(() => { window.location.href = "/#/home"; }, 1600);
  } catch (error) {
    setStatus(error.message, "error");
    button.disabled = false;
  }
});

load();
