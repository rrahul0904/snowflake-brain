import { escapeHtml, formatNumber } from "./api.js?v=20260714-v20-ai-academy";

export const TRACK_STORAGE_KEY = "snowflake-brain.active-track.v10";
export const DEFAULT_TRACK = "snowpro-core";

export function trackFromHash() {
  try {
    const [, query = ""] = (window.location.hash || "").split("?");
    const params = new URLSearchParams(query);
    return params.get("track_id") || params.get("certification") || "";
  } catch {
    return "";
  }
}

export function normalizeTrack(trackId = "", certifications = []) {
  const ids = new Set((certifications || []).map((cert) => cert.id).filter(Boolean));
  if (ids.has(trackId)) return trackId;
  if (ids.has(DEFAULT_TRACK)) return DEFAULT_TRACK;
  return certifications?.[0]?.id || DEFAULT_TRACK;
}

export function activeTrack(defaultTrack = DEFAULT_TRACK) {
  const fromHash = trackFromHash();
  if (fromHash) {
    localStorage.setItem(TRACK_STORAGE_KEY, fromHash);
    return fromHash;
  }
  return localStorage.getItem(TRACK_STORAGE_KEY) || defaultTrack;
}

export function setActiveTrack(trackId) {
  if (trackId) localStorage.setItem(TRACK_STORAGE_KEY, trackId);
}

export function hashWithTrack(trackId, hash = window.location.hash || "#/command") {
  const [path, query = ""] = hash.split("?");
  const params = new URLSearchParams(query);
  params.set("track_id", trackId || activeTrack());
  params.delete("certification");
  const queryString = params.toString();
  return `${path || "#/command"}${queryString ? `?${queryString}` : ""}`;
}

export function navigateWithTrack(trackId, hash = window.location.hash || "#/command") {
  const next = hashWithTrack(trackId, hash);
  setActiveTrack(trackId);
  if (window.location.hash === next) {
    window.dispatchEvent(new CustomEvent("track-change", { detail: { track_id: trackId } }));
  } else {
    window.location.hash = next;
  }
}

export function qs(container, selector) {
  return container.querySelector(selector);
}

export function qsa(container, selector) {
  return [...container.querySelectorAll(selector)];
}

export function pct(value) {
  const number = Number(value || 0);
  return Math.max(0, Math.min(100, Math.round(number)));
}

export function statusLabel(value = "") {
  return String(value || "not_started").replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function trackOptions(certifications = [], selected = DEFAULT_TRACK) {
  return certifications
    .map((cert) => `<option value="${escapeHtml(cert.id)}" ${cert.id === selected ? "selected" : ""}>${escapeHtml(cert.title || cert.id)}</option>`)
    .join("");
}

export function metricCard(label, value, detail = "", tone = "") {
  return `<article class="metric-card ${tone}"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong>${detail ? `<small>${escapeHtml(detail)}</small>` : ""}</article>`;
}

export function progressBar(value, label = "") {
  const width = pct(value);
  return `<div class="progress-wrap" aria-label="${escapeHtml(label)}"><span style="width:${width}%"></span></div>`;
}

export function emptyState(title, detail = "", action = "") {
  return `<div class="empty-state premium-empty"><div class="empty-orb"></div><h3>${escapeHtml(title)}</h3>${detail ? `<p>${escapeHtml(detail)}</p>` : ""}${action || ""}</div>`;
}

export function skeleton(title = "Loading Data + AI Career Lab...") {
  return `<section class="page-shell"><div class="skeleton-hero"><div><span></span><strong>${escapeHtml(title)}</strong><p></p></div></div><div class="skeleton-grid"><i></i><i></i><i></i></div></section>`;
}

export function errorPanel(error, label = "View failed to load") {
  return `<section class="page-shell"><div class="error-panel premium-error"><strong>${escapeHtml(label)}</strong><p>${escapeHtml(error?.message || error || "Unknown error")}</p><button onclick="location.reload()">Reload</button></div></section>`;
}

export function certBadge(certId = DEFAULT_TRACK) {
  const short = String(certId || "SB").split("-").map((item) => item[0]).join("").slice(0, 3).toUpperCase();
  return `<span class="cert-badge">${escapeHtml(short)}</span>`;
}

export function statSentence(data = {}) {
  const q = formatNumber(data.questions || 0);
  const lessons = formatNumber(data.lessons || 0);
  const tests = formatNumber(data.practice_tests || 0);
  return `${q} questions · ${lessons} lessons · ${tests} tests`;
}
