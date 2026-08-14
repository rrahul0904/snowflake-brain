export const VIEW_ID = "v26-membership";

import { candidate, membership, refreshCandidate } from "../auth.js";
import { escapeHtml, getBillingConfig } from "../api.js";

const plans = [
  { code: "free", name: "Free", price: "$0", cadence: "forever", label: "Build your foundation", copy: "Study materials stay open, with a daily question allowance and a weekly timed check.", features: ["All SnowPro Core study materials", "20 real practice questions every day", "One 20-question timed mock every week", "Weekly mock must be completed and cannot be discarded", "Progress, bookmarks, notes, drills, and exercises"] },
  { code: "premium_20", name: "Premium 100", price: "$20", cadence: "per month", label: "Consistent exam preparation", copy: "A daily 100-question allowance plus two full timed exam starts each month.", features: ["Everything in Free", "100 practice and Quick Mock questions per day", "2 full timed exams per month", "Saved sittings, history, results, and analytics"] },
  { code: "premium_40", name: "Premium 250", price: "$40", cadence: "per month", label: "High-volume preparation", copy: "More daily repetition and four full timed exam starts each month.", features: ["Everything in Free", "250 practice and Quick Mock questions per day", "4 full timed exams per month", "Saved sittings, history, results, and analytics"] },
  { code: "premium_100", name: "Premium 500", price: "$100", cadence: "per month", label: "Maximum preparation", copy: "The largest daily practice allowance with unrestricted full timed exam starts.", features: ["Everything in Free", "500 practice and Quick Mock questions per day", "Unlimited full timed exams each month", "Saved sittings, history, results, and analytics"] },
  { code: "exam_pack_35", name: "One-Time Exam Pack", price: "$35", cadence: "one-time", label: "No subscription", copy: "Keep the 100-question Practice Mock and use one Full Exam within the purchase window.", features: ["Lifetime access to a 100-question Practice Mock", "1 full timed exam attempt", "Full Exam must be started within 30 days of purchase", "Lifetime Practice Mock remains after the 30-day window"] },
];

export default async function mount(container) {
  await refreshCandidate().catch(() => {});
  const billing = await getBillingConfig().catch(() => ({ enabled: false, available_plans: [] }));
  const account = candidate();
  const current = membership();
  const checkoutState = new URLSearchParams((window.location.hash.split("?")[1] || "")).get("checkout");
  container.innerHTML = `<main class="v26-page v26-membership-page"><header class="v26-page-intro centered"><p class="v26-kicker">Membership</p><h1>Study freely.<br/>Choose the exam access you need.</h1><p>Every plan keeps the SnowPro Core study materials open. Server-side allowances control daily questions and timed exam starts.</p></header>${checkoutNotice(checkoutState)}${accountPanel(account, current)}${usagePanel(account, current)}<section class="v26-plan-grid" aria-label="Membership plans">${plans.map((plan) => planCard(plan, account, current, billing)).join("")}</section><p class="v26-billing-note">All paid prices are in USD plus applicable taxes. ${billing.enabled ? "Paid checkout is hosted by the billing provider. Returning from checkout does not grant Premium; access changes only after a verified server-to-server billing event." : "Checkout is not enabled in this environment, so no payment, tax charge, or plan change occurs here."} Every mock and Full Exam is an independent preparation simulation, not an official Snowflake certification exam.</p><section class="v26-membership-assurance"><div><span>Account-bound access</span><strong>Premium belongs to your candidate account whether you sign in with email or a linked Google identity. There is no transferable license key.</strong></div><div><span>Server enforcement</span><strong>Question and exam limits come from the private database, not browser state, URL flags, or editable cookies.</strong></div><div><span>Verified activation</span><strong>A paid plan activates only after a signed billing webhook maps the provider customer back to your candidate ID.</strong></div></section></main>`;
}

function checkoutNotice(state) {
  if (state === "success") return `<section class="v26-account-banner"><div><p class="v26-kicker">Checkout returned</p><h2>Confirming your membership…</h2><p>Payment return pages never grant Premium by themselves. Your account updates when the signed billing event is processed.</p></div></section>`;
  if (state === "cancelled") return `<section class="v26-account-banner"><div><p class="v26-kicker">Checkout cancelled</p><h2>No plan change was made</h2><p>Your current membership remains unchanged.</p></div></section>`;
  return "";
}

function accountPanel(account, current) {
  if (!account) return `<section class="v26-account-banner"><div><p class="v26-kicker">Your account</p><h2>Begin with Free membership</h2><p>Create a candidate account for study access, daily practice, and persistent progress.</p></div><div><button class="v26-btn secondary" type="button" data-auth-intent="login">Sign In</button><button class="v26-btn primary" type="button" data-auth-intent="signup">Create Free Account</button></div></section>`;
  const plan = current?.plan || { name: "Free" };
  const methods = (account.sign_in_methods || ["email"]).map((item) => item === "google" ? "Google" : "Email").join(" + ");
  return `<section class="v26-account-banner signed-in"><div><p class="v26-kicker">Signed in</p><h2>${escapeHtml(account.display_name)}</h2><p>${escapeHtml(account.email)} · <strong>${escapeHtml(plan.name)} membership</strong></p><p class="v26-account-methods">Signed in with: ${escapeHtml(methods)} · Entitlement version ${escapeHtml(current?.entitlement_version ?? 0)}</p></div><div><span class="v26-current-plan">${escapeHtml(plan.name)}</span><button class="v26-btn secondary" type="button" data-auth-logout>Sign Out</button></div></section>`;
}

function usagePanel(account, current) {
  if (!account || !current?.usage) return "";
  const daily = current.usage.daily_questions || {};
  const weekly = current.usage.weekly_mocks || {};
  const monthly = current.usage.monthly_full_exams || {};
  const planCode = current.plan_code || "free";
  const items = [];
  if (daily.limit != null) items.push(["Questions today", `${daily.remaining}/${daily.limit} remaining`]);
  if (planCode === "free") items.push(["Weekly mock", `${weekly.remaining}/${weekly.limit} remaining`]);
  if (planCode.startsWith("premium_")) items.push(["Full exams this month", monthly.limit == null ? "Unlimited" : `${monthly.remaining}/${monthly.limit} remaining`]);
  if (planCode === "exam_pack_35") items.push(["Included Full Exam", `${monthly.remaining}/1 remaining · starts by ${formatDate(monthly.access_expires_at)}`]);
  return `<section class="v26-entitlement-usage" aria-label="Current plan usage">${items.map(([label, value]) => `<div><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`).join("")}</section>`;
}

function planCard(plan, account, current, billing) {
  const active = current?.plan_code === plan.code && current?.status === "active";
  let action = active ? `<span class="v26-plan-current">Current Plan</span>` : "";
  if (!active && !account && plan.code === "free") action = `<button class="v26-btn secondary" type="button" data-auth-intent="signup">Create Free Account</button>`;
  if (!active && plan.code !== "free") {
    const configured = billing.enabled && (billing.available_plans || []).includes(plan.code);
    action = `<button class="v26-btn primary" type="button" data-plan-checkout="${escapeHtml(plan.code)}">${configured ? (plan.code === "exam_pack_35" ? "Buy Exam Pack" : `Choose ${escapeHtml(plan.name)}`) : "Checkout not enabled"}</button>`;
  }
  return `<article class="v26-plan-card ${plan.code !== "free" ? "featured" : ""} ${active ? "current" : ""}"><span class="v26-plan-label">${escapeHtml(plan.label)}</span><h2>${escapeHtml(plan.name)}</h2><div class="v26-plan-price"><strong>${escapeHtml(plan.price)}</strong><span>${escapeHtml(plan.cadence)}${plan.code === "free" ? "" : " + tax"}</span></div><p>${escapeHtml(plan.copy)}</p><h3>Included</h3><ul>${plan.features.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>${action}</article>`;
}

function formatDate(value) {
  if (!value) return "30 days after purchase";
  return new Intl.DateTimeFormat(undefined, { year: "numeric", month: "short", day: "numeric", timeZone: "UTC" }).format(new Date(value));
}
