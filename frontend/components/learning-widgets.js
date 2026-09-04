import { escapeHtml } from "../api.js";

export function readinessBand(score = 0) {
  const value = Number(score || 0);
  if (!value) return { label: "Building evidence", tone: "neutral" };
  if (value >= 82) return { label: "Ready", tone: "success" };
  if (value >= 70) return { label: "Almost Ready", tone: "info" };
  if (value >= 50) return { label: "Needs Focus", tone: "warning" };
  return { label: "At Risk", tone: "danger" };
}

export function readinessRing(score = 0, label = "Readiness") {
  const value = Math.max(0, Math.min(100, Math.round(Number(score || 0))));
  const band = readinessBand(value);
  return `<div class="v26-readiness-widget"><div class="v26-readiness-ring" style="--score:${value}"><strong>${value || "—"}</strong></div><div><span>${escapeHtml(label)}</span><b data-tone="${band.tone}">${escapeHtml(band.label)}</b><small>Snowflake Brain evidence · not an official exam prediction</small></div></div>`;
}

export function readinessRadar(values = {}) {
  const axes = [
    ["Mastery", clamp(values.mastery)],
    ["Retention", clamp(values.retention)],
    ["Calibration", clamp(values.calibration)],
    ["Mock", clamp(values.mock)],
    ["Coverage", clamp(values.coverage)],
    ["Pace", clamp(values.pace)],
  ];
  const center = 110;
  const radius = 82;
  const polygon = axes.map(([, value], index) => point(index, axes.length, center, radius * value / 100)).join(" ");
  const grid = [25, 50, 75, 100].map((pct) => `<polygon points="${axes.map((_, index) => point(index, axes.length, center, radius * pct / 100)).join(" ")}"/>`).join("");
  const labels = axes.map(([label, value], index) => {
    const [x, y] = pointPair(index, axes.length, center, radius + 22);
    return `<text x="${x}" y="${y}" text-anchor="middle">${escapeHtml(label)} ${Math.round(value)}</text>`;
  }).join("");
  return `<figure class="v26-readiness-radar"><svg viewBox="0 0 220 220" role="img" aria-label="Readiness radar across mastery, retention, calibration, mock, coverage, and pace"><g class="radar-grid">${grid}</g><polygon class="radar-value" points="${polygon}"/>${labels}</svg><figcaption>Weighted evidence profile</figcaption></figure>`;
}

export function decisionRuleCard(rule = {}) {
  return `<article class="v26-decision-rule-card"><span>When you see</span><h3>${escapeHtml(rule.when || "Scenario signal")}</h3><dl><dt>Choose</dt><dd>${escapeHtml(rule.choose || "The feature that directly matches the requirement")}</dd><dt>Because</dt><dd>${escapeHtml(rule.why || "Match the documented responsibility, not just a familiar keyword.")}</dd></dl></article>`;
}

export function examTrapCard(row = {}) {
  return `<article class="v26-exam-trap-card"><span>Exam Trap</span><p>${escapeHtml(row.trap || row.text || row || "Common misconception")}</p>${row.correction ? `<strong>${escapeHtml(row.correction)}</strong>` : ""}</article>`;
}

export function evidenceNotice(text) {
  return `<p class="v26-evidence-notice"><strong>Data honesty:</strong> ${escapeHtml(text)}</p>`;
}

export function emptyState(title, body, href = "", cta = "") {
  return `<section class="v26-empty-state" data-empty-state><span>○</span><h3>${escapeHtml(title)}</h3><p>${escapeHtml(body)}</p>${href && cta ? `<a class="v26-btn secondary" href="${href}">${escapeHtml(cta)}</a>` : ""}</section>`;
}

function clamp(value) { return Math.max(0, Math.min(100, Number(value || 0))); }
function point(index, count, center, radius) { const [x, y] = pointPair(index, count, center, radius); return `${x.toFixed(1)},${y.toFixed(1)}`; }
function pointPair(index, count, center, radius) { const angle = -Math.PI / 2 + (Math.PI * 2 * index / count); return [center + Math.cos(angle) * radius, center + Math.sin(angle) * radius]; }
