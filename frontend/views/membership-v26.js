export const VIEW_ID = "v26-membership";

import { candidate, membership, refreshCandidate } from "../auth.js";
import { escapeHtml } from "../api.js";

const plans = [
  { code: "free", name: "Free", price: "$0", cadence: "forever", label: "Build your foundation", copy: "Study materials stay open, with a daily question allowance and a weekly timed check.", features: ["All SnowPro Core study materials", "20 real practice questions every day", "One 20-question timed mock every week", "Weekly mock must be completed and cannot be discarded", "Progress, bookmarks, notes, drills, and exercises"] },
  { code: "premium_20", name: "Premium 100", price: "$20", cadence: "per month", label: "Consistent exam preparation", copy: "A daily 100-question allowance plus two full timed exam starts each month.", features: ["Everything in Free", "100 practice and Quick Mock questions per day", "2 full timed exams per month", "Saved sittings, history, results, and analytics"] },
  { code: "premium_40", name: "Premium 250", price: "$40", cadence: "per month", label: "High-volume preparation", copy: "More daily repetition and four full timed exam starts each month.", features: ["Everything in Free", "250 practice and Quick Mock questions per day", "4 full timed exams per month", "Saved sittings, history, results, and analytics"] },
  { code: "premium_100", name: "Premium 500", price: "$100", cadence: "per month", label: "Maximum preparation", copy: "The largest daily practice allowance with unrestricted full timed exam starts.", features: ["Everything in Free", "500 practice and Quick Mock questions per day", "Unlimited full timed exams each month", "Saved sittings, history, results, and analytics"] },
  { code: "exam_pack_35", name: "One-Time Exam Pack", price: "$35", cadence: "one-time", label: "No subscription", copy: "Keep the 100-question Practice Mock and use one Full Exam within the purchase window.", features: ["Lifetime access to a 100-question Practice Mock", "1 full timed exam attempt", "Full Exam must be started within 30 days of purchase", "Lifetime Practice Mock remains after the 30-day window"] },
];

export default async function mount(container) {
  await refreshCandidate().catch(() => {});
  const account = candidate();
  const current = membership();
  container.innerHTML = `<main class="v26-page v26-membership-page"><header class="v26-page-intro centered"><p class="v26-kicker">Membership</p><h1>Study freely.<br/>Choose the exam access you need.</h1><p>Every plan keeps the SnowPro Core study materials open. Server-side allowances control daily questions and timed exam starts.</p></header>${accountPanel(account, current)}${usagePanel(account, current)}<section class="v26-plan-grid" aria-label="Membership plans">${plans.map((plan) => planCard(plan, account, current)).join("")}</section><p class="v26-billing-note">All paid prices are in USD plus applicable taxes. Taxes will be calculated by the billing provider at checkout based on location. Checkout is not enabled yet, so no payment, tax charge, or plan change occurs here. Every mock and Full Exam is an independent preparation simulation, not an official Snowflake certification exam.</p><section class="v26-membership-assurance"><div><span>Calendar resets</span><strong>Daily allowances reset at 00:00 UTC, weekly access Monday at 00:00 UTC, and monthly access on the first day at 00:00 UTC.</strong></div><div><span>Server enforcement</span><strong>Question and exam limits come from the private database, not browser state.</strong></div><div><span>Product truthfulness</span><strong>Paid activation remains unavailable until a real billing and tax workflow is connected.</strong></div></section></main>`;
}

function accountPanel(account, current) {
  if (!account) return `<section class="v26-account-banner"><div><p class="v26-kicker">Your account</p><h2>Begin with Free membership</h2><p>Create a candidate account for study access, daily practice, and persistent progress.</p></div><div><button class="v26-btn secondary" type="button" data-auth-intent="login">Sign In</button><button class="v26-btn primary" type="button" data-auth-intent="signup">Create Free Account</button></div></section>`;
  const plan = current?.plan || { name: "Free" };
  return `<section class="v26-account-banner signed-in"><div><p class="v26-kicker">Signed in</p><h2>${escapeHtml(account.display_name)}</h2><p>${escapeHtml(account.email)} · <strong>${escapeHtml(plan.name)} membership</strong></p></div><div><span class="v26-current-plan">${escapeHtml(plan.name)}</span><button class="v26-btn secondary" type="button" data-auth-logout>Sign Out</button></div></section>`;
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

function planCard(plan, account, current) {
  const active = current?.plan_code === plan.code && current?.status === "active";
  let action = active ? `<span class="v26-plan-current">Current Plan</span>` : "";
  if (!active && !account && plan.code === "free") action = `<button class="v26-btn secondary" type="button" data-auth-intent="signup">Create Free Account</button>`;
  if (!active && plan.code !== "free") action = `<button class="v26-btn primary" type="button" data-premium-unavailable>${plan.code === "exam_pack_35" ? "Buy Exam Pack" : `Choose ${plan.name}`}</button>`;
  return `<article class="v26-plan-card ${plan.code !== "free" ? "featured" : ""} ${active ? "current" : ""}"><span class="v26-plan-label">${escapeHtml(plan.label)}</span><h2>${escapeHtml(plan.name)}</h2><div class="v26-plan-price"><strong>${escapeHtml(plan.price)}</strong><span>${escapeHtml(plan.cadence)}${plan.code === "free" ? "" : " + tax"}</span></div><p>${escapeHtml(plan.copy)}</p><h3>Included</h3><ul>${plan.features.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>${action}</article>`;
}

function formatDate(value) {
  if (!value) return "30 days after purchase";
  return new Intl.DateTimeFormat(undefined, { year: "numeric", month: "short", day: "numeric", timeZone: "UTC" }).format(new Date(value));
}
