export const VIEW_ID = "v26-exercises";

import { escapeHtml, getLabs, getSkillMap } from "../api.js";
import { activeTrack } from "../ui.js";
import { candidate, refreshCandidate } from "../auth.js";

const COLORS = ["#c87966", "#859db8", "#c49a62", "#7b9e91", "#b97b82"];

export default async function mount(container, params = {}) {
  const trackId = params.track_id || activeTrack();
  await refreshCandidate().catch(() => {});
  if (!candidate()) {
    container.innerHTML = `<main class="v26-page"><a class="v26-back" href="#/curriculum?track_id=${encodeURIComponent(trackId)}">← Curriculum</a><section class="v26-route-gate"><p class="v26-kicker">Free candidate feature</p><h1>Create a free account to continue.</h1><p>Build Exercises are included with Free membership and their completion state belongs to your candidate account.</p><button class="v26-btn primary" type="button" data-auth-intent="signup">Create Free Account</button><button class="v26-btn secondary" type="button" data-auth-intent="login">Sign In</button></section></main>`;
    return;
  }
  const [map, payload] = await Promise.all([getSkillMap(), getLabs({ track_id: trackId }).catch(() => ({ labs: [] }))]);
  const cert = (map.certifications || []).find((item) => item.id === trackId) || (map.certifications || [])[0];
  if (!cert) throw new Error("Certification is not configured");
  const labs = payload.labs || payload.challenges || [];
  container.innerHTML = `<div class="v26-study-layout">${sidebar(cert)}<main class="v26-study-content"><header class="v26-study-heading"><p class="v26-kicker">Hands-On Practice</p><h1>Build Exercises</h1><p>Turn exam concepts into implementation decisions with focused Snowflake challenges and local validation.</p></header><section class="v26-lab-grid">${labs.length ? labs.map((lab) => `<a href="#/labs?track_id=${encodeURIComponent(cert.id)}&lab_id=${encodeURIComponent(lab.id)}"><span>${escapeHtml(lab.difficulty || "Exercise")}</span><h2>${escapeHtml(lab.title || lab.name || "Snowflake exercise")}</h2><p>${escapeHtml(lab.scenario || lab.description || "Open the guided challenge workspace.")}</p><div><b>${lab.estimated_minutes || lab.minutes || 20} min</b><em>Open →</em></div></a>`).join("") : `<div class="v26-empty-copy"><strong>Task exercises are available inside every lesson.</strong><p>Dedicated validated lab workspaces will appear here as they are added.</p></div>`}</section></main></div>`;
}

function sidebar(cert) {
  const domains = (cert.domains || []).map((domain, index) => `<a class="v26-side-domain" href="#/domain?track_id=${encodeURIComponent(cert.id)}&domain_id=${encodeURIComponent(domain.id)}"><i style="--domain:${COLORS[index % 5]}"></i><b>${index + 1}</b><span>${escapeHtml(domain.title)}</span><em>${Number(domain.weight || 0)}%</em></a>`).join("");
  return `<aside class="v26-study-nav" aria-label="Study navigation"><div class="v26-side-group"><small>Study Tools</small><a href="#/progress?track_id=${encodeURIComponent(cert.id)}">Progress Dashboard</a><a href="#/practice?track_id=${encodeURIComponent(cert.id)}&mode=drill">Drill Mode</a></div><div class="v26-side-group"><small>Curriculum</small><a href="#/curriculum?track_id=${encodeURIComponent(cert.id)}">Exam Domains</a>${domains}</div><div class="v26-side-group"><small>Practice</small><a class="active" href="#/exercises?track_id=${encodeURIComponent(cert.id)}">Build Exercises</a><a href="#/practice?track_id=${encodeURIComponent(cert.id)}&mode=diagnostic">Diagnostic Test</a></div><div class="v26-side-group"><small>Look Up</small><a href="#/quick-reference?track_id=${encodeURIComponent(cert.id)}">Quick Reference</a><a href="#/glossary?track_id=${encodeURIComponent(cert.id)}">Glossary</a></div></aside>`;
}
