export const VIEW_ID = "v26-verified-credentials";

import {
  deleteCredential,
  escapeHtml,
  getCredentials,
  getTalentProfile,
  reverifyCredential,
  updateTalentProfile,
  verifyCredlyCredential,
} from "../api.js";
import { showToast } from "../components/toast.js";


export default async function mount(container) {
  const [credentialResult, profile] = await Promise.all([
    getCredentials(),
    getTalentProfile(),
  ]);
  const credentials = credentialResult.credentials || [];
  const verifiedCount = Number(profile.verified_credential_count || credentialResult.verified_count || 0);

  container.innerHTML = `<main class="v26-page v26-credentials-page">
    <header class="v26-page-intro">
      <p class="v26-kicker">Professional profile</p>
      <h1>Licenses & certifications</h1>
      <p>Add the same public credential link you would use on LinkedIn. For SnowPro credentials, the platform checks the live Credly evidence instead of trusting an uploaded certificate image.</p>
    </header>

    <section class="v26-credential-trust">
      <div><span class="v26-trust-icon">✓</span><div><strong>Credly-backed verification</strong><p>A screenshot or PDF can support a manual review later, but it never creates a verified badge by itself.</p></div></div>
      <a href="https://www.credly.com/" target="_blank" rel="noopener noreferrer">Open Credly ↗</a>
    </section>

    <section class="v26-credential-layout">
      <div class="v26-credential-main">
        <article class="v26-credential-add-card">
          <div class="v26-section-heading"><div><p class="v26-kicker">Add credential</p><h2>Verify a SnowPro certification</h2></div></div>
          <form data-credential-form class="v26-credential-form">
            <label><span>Credential URL</span><input type="url" name="credential_url" required placeholder="https://www.credly.com/badges/.../public_url" autocomplete="url" /></label>
            <p>In Credly: open the badge → <b>Share</b> → <b>Public Link</b> → copy the URL. The recipient name on Credly must match your candidate profile for automatic verification.</p>
            <div class="v26-credential-form-actions"><button class="v26-btn primary" type="submit">Verify with Credly</button><span data-credential-form-status aria-live="polite"></span></div>
          </form>
        </article>

        <section class="v26-credential-list-section">
          <div class="v26-section-heading"><div><p class="v26-kicker">Your credentials</p><h2>${credentials.length ? `${credentials.length} added` : "No credentials yet"}</h2></div><span class="v26-verified-count">${verifiedCount} verified & active</span></div>
          <div class="v26-credential-list">${credentials.length ? credentials.map(credentialCard).join("") : emptyCredentials()}</div>
        </section>
      </div>

      <aside class="v26-talent-profile-card">
        <p class="v26-kicker">Talent profile</p>
        <h2>Recruiter visibility</h2>
        <p>Private by default. Your raw certificate files and preparation history are never shown to recruiters.</p>
        <form data-talent-form>
          <label><span>Professional headline</span><input name="headline" maxlength="160" value="${escapeHtml(profile.headline || "")}" placeholder="Senior Snowflake Data Engineer" /></label>
          <label><span>Location</span><input name="location" maxlength="160" value="${escapeHtml(profile.location || "")}" placeholder="Boston, MA · Remote" /></label>
          <label><span>Availability</span><select name="availability">${availabilityOptions(profile.availability)}</select></label>
          <label class="v26-toggle-row"><input type="checkbox" name="recruiter_discoverable" ${profile.recruiter_discoverable ? "checked" : ""} ${profile.can_be_discoverable ? "" : "disabled"}/><span><strong>Discoverable by verified recruiters</strong><small>Recruiters can find your profile by verified certifications and professional criteria.</small></span></label>
          <label class="v26-toggle-row"><input type="checkbox" name="public_profile" ${profile.public_profile ? "checked" : ""} ${profile.can_be_discoverable ? "" : "disabled"}/><span><strong>Public professional profile</strong><small>Off by default. Turning this on also enables recruiter discoverability.</small></span></label>
          ${profile.can_be_discoverable ? "" : `<div class="v26-profile-lock">Verify at least one active SnowPro credential to unlock discoverability.</div>`}
          <button class="v26-btn primary" type="submit">Save profile</button>
          <span data-talent-status aria-live="polite"></span>
        </form>
      </aside>
    </section>
  </main>`;

  bindCredentialForm(container);
  bindCredentialActions(container);
  bindTalentForm(container);
}


function credentialCard(item) {
  const status = item.verification_status || "pending";
  const title = item.credential_name || "SnowPro credential";
  const issuer = item.issuer_name || "Verification pending";
  const detail = statusDetail(item);
  return `<article class="v26-credential-card" data-credential="${escapeHtml(item.credential_uid)}">
    <div class="v26-credential-card-head">
      <div class="v26-credential-emblem">❄</div>
      <div><h3>${escapeHtml(title)}</h3><p>${escapeHtml(issuer)}</p></div>
      <span class="v26-credential-status ${escapeHtml(status)}">${escapeHtml(statusLabel(status))}</span>
    </div>
    <dl>
      <div><dt>Issued to</dt><dd>${escapeHtml(item.issued_to_name || "Not exposed by provider")}</dd></div>
      <div><dt>Issued</dt><dd>${formatDate(item.issued_at)}</dd></div>
      <div><dt>Expires</dt><dd>${formatDate(item.expires_at)}</dd></div>
      <div><dt>Credly badge ID</dt><dd>${escapeHtml(item.provider_badge_id || "—")}</dd></div>
    </dl>
    ${detail ? `<p class="v26-credential-detail ${escapeHtml(status)}">${escapeHtml(detail)}</p>` : ""}
    <div class="v26-credential-actions">
      <a class="v26-btn secondary" href="${escapeHtml(item.credential_url)}" target="_blank" rel="noopener noreferrer">View credential ↗</a>
      <button class="v26-btn secondary" type="button" data-reverify="${escapeHtml(item.credential_uid)}">Reverify</button>
      <button class="v26-btn ghost danger" type="button" data-delete-credential="${escapeHtml(item.credential_uid)}">Remove</button>
    </div>
  </article>`;
}


function emptyCredentials() {
  return `<article class="v26-credential-empty"><div class="v26-credential-emblem">❄</div><h3>Add your first verified SnowPro credential.</h3><p>Your badge stays tied to the official Credly verification page. Once verified, you can choose whether recruiters can discover you.</p></article>`;
}


function statusLabel(status) {
  return {
    verified: "Verified",
    expired: "Expired",
    needs_review: "Needs review",
    rejected: "Not verified",
    pending: "Pending",
  }[status] || "Pending";
}


function statusDetail(item) {
  if (item.verification_status === "verified") return "Verified against public Credly evidence: Snowflake issuer, SnowPro credential, and candidate name matched.";
  if (item.verification_status === "expired") return "The credential matched, but Credly reports it as expired. It will not qualify the profile for active recruiter discovery.";
  return item.verification_error || "Verification has not completed yet.";
}


function availabilityOptions(current) {
  const options = [
    ["not_looking", "Not looking"],
    ["open_to_work", "Open to full-time roles"],
    ["open_to_contract", "Open to consulting / contract"],
    ["available_now", "Available now"],
  ];
  return options.map(([value, label]) => `<option value="${value}" ${current === value ? "selected" : ""}>${label}</option>`).join("");
}


async function bindCredentialForm(container) {
  const form = container.querySelector("[data-credential-form]");
  if (!form) return;
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = form.querySelector("button[type=submit]");
    const status = form.querySelector("[data-credential-form-status]");
    const input = form.elements.credential_url;
    button.disabled = true;
    status.textContent = "Checking live Credly evidence…";
    try {
      const result = await verifyCredlyCredential(input.value);
      const state = result.credential?.verification_status || "pending";
      showToast(state === "verified" ? "SnowPro credential verified" : `Credential status: ${statusLabel(state)}`, state === "rejected" ? "error" : "success");
      await mount(container);
    } catch (error) {
      status.textContent = error.message || "Verification failed.";
      showToast(status.textContent, "error");
      button.disabled = false;
    }
  });
}


function bindCredentialActions(container) {
  container.querySelectorAll("[data-reverify]").forEach((button) => button.addEventListener("click", async () => {
    button.disabled = true;
    button.textContent = "Checking…";
    try {
      await reverifyCredential(button.dataset.reverify);
      showToast("Credential verification refreshed", "success");
      await mount(container);
    } catch (error) {
      showToast(error.message || "Unable to reverify credential", "error");
      button.disabled = false;
      button.textContent = "Reverify";
    }
  }));

  container.querySelectorAll("[data-delete-credential]").forEach((button) => button.addEventListener("click", async () => {
    if (!window.confirm("Remove this credential from your profile? Recruiter visibility will switch off if this is your last active verified credential.")) return;
    button.disabled = true;
    try {
      await deleteCredential(button.dataset.deleteCredential);
      showToast("Credential removed", "success");
      await mount(container);
    } catch (error) {
      showToast(error.message || "Unable to remove credential", "error");
      button.disabled = false;
    }
  }));
}


function bindTalentForm(container) {
  const form = container.querySelector("[data-talent-form]");
  if (!form) return;
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = form.querySelector("button[type=submit]");
    const status = form.querySelector("[data-talent-status]");
    button.disabled = true;
    status.textContent = "Saving…";
    const payload = {
      headline: form.elements.headline.value,
      location: form.elements.location.value,
      availability: form.elements.availability.value,
      recruiter_discoverable: Boolean(form.elements.recruiter_discoverable.checked),
      public_profile: Boolean(form.elements.public_profile.checked),
    };
    try {
      await updateTalentProfile(payload);
      status.textContent = "Saved.";
      showToast("Talent profile updated", "success");
      await mount(container);
    } catch (error) {
      status.textContent = error.message || "Unable to save profile.";
      showToast(status.textContent, "error");
      button.disabled = false;
    }
  });
}


function formatDate(value) {
  if (!value) return "—";
  const date = new Date(`${value}T00:00:00Z`);
  if (Number.isNaN(date.getTime())) return escapeHtml(value);
  return new Intl.DateTimeFormat(undefined, { year: "numeric", month: "short", day: "numeric" }).format(date);
}
