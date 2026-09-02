export const VIEW_ID = "v26-exercises";

import { escapeHtml, getLabs, getSkillMap } from "../api.js";
import { activeTrack } from "../ui.js";
import { DOMAIN_COLORS, studyLayout } from "../components/study-shell.js";
import { emptyState, evidenceNotice } from "../components/learning-widgets.js";

export default async function mount(container, params = {}) {
  const trackId = params.track_id || activeTrack();
  const [map, payload] = await Promise.all([
    getSkillMap(),
    getLabs({ certification: trackId }).catch(() => ({ mode: "offline", labs: [] })),
  ]);
  const cert = (map.certifications || []).find((item) => item.id === trackId) || (map.certifications || [])[0];
  if (!cert) throw new Error("Certification is not configured");
  const labs = payload.labs || [];
  const byDomain = new Map();
  labs.forEach((lab) => {
    const key = lab.domain_id || "other";
    const rows = byDomain.get(key) || [];
    rows.push(lab);
    byDomain.set(key, rows);
  });
  const completed = labs.filter((lab) => lab.completed).length;

  container.innerHTML = studyLayout(cert, "exercises", `<a class="v26-study-back" href="#/curriculum?track_id=${encodeURIComponent(cert.id)}" aria-label="Back">‹</a><header class="v26-study-heading"><p class="v26-kicker">Hands-on workbook</p><h1>Build Exercises</h1><p>Apply SnowPro concepts in realistic Snowflake scenarios with starter SQL, progressive hints, deterministic checks, expected outcomes, reference solutions, and cleanup guidance.</p>${evidenceNotice(payload.mode === "offline" ? "Labs use deterministic offline validation. Snowflake Brain does not claim that SQL ran against a live Snowflake account." : `Lab mode: ${payload.mode}.`)}</header><section class="v26-learning-command"><div><span>Configured labs</span><strong>${labs.length}</strong><small>Hands-on challenges</small></div><div><span>Completed</span><strong>${completed}</strong><small>${labs.length ? `${Math.round(completed / labs.length * 100)}%` : "No labs configured"}</small></div><div><span>Validation</span><strong>${payload.mode === "offline" ? "Offline" : escapeHtml(payload.mode || "Configured")}</strong><small>Honest execution boundary</small></div><div><span>Workflow</span><strong>SQL</strong><small>Scenario → hints → checks → solution</small></div></section>${labs.length ? `<section class="v26-exercise-domain-list">${(cert.domains || []).map((domain, index) => domainSection(cert, domain, index, byDomain.get(domain.id) || [])).join("")}</section>` : emptyState("No lab challenges configured", "Task lessons still include build exercises, but no standalone deterministic lab challenges are configured for this certification.", `#/curriculum?track_id=${encodeURIComponent(cert.id)}`, "Return to curriculum")}`, "", []);
}

function domainSection(cert, domain, index, labs) {
  if (!labs.length) return "";
  return `<article class="v26-exercise-domain command-labs"><header><i style="--domain:${DOMAIN_COLORS[index % DOMAIN_COLORS.length]}"></i><h2>Domain ${index + 1}: ${escapeHtml(domain.title)}</h2><span>${labs.length} lab${labs.length === 1 ? "" : "s"}</span></header><div class="v26-lab-card-grid">${labs.map((lab) => labCard(cert, lab)).join("")}</div></article>`;
}

function labCard(cert, lab) {
  return `<a class="v26-build-lab-card ${lab.completed ? "completed" : ""}" href="#/labs?certification=${encodeURIComponent(cert.id)}&lab_id=${encodeURIComponent(lab.id)}"><div><span>${lab.completed ? "✓ Completed" : escapeHtml(lab.difficulty || "Lab")}</span><em>${Number(lab.estimated_minutes || lab.minutes || 20)} min</em></div><h3>${escapeHtml(lab.title || "Snowflake build challenge")}</h3><p>${escapeHtml(lab.scenario || lab.why_it_matters || "Apply this task in a guided Snowflake implementation scenario.")}</p><dl><dt>Task</dt><dd>${escapeHtml(lab.skill || lab.skill_id || "Mapped task")}</dd><dt>Checks</dt><dd>${(lab.validation_tests || []).length || "Configured"}</dd><dt>Mode</dt><dd>Guided validation</dd></dl><strong>Open lab workspace →</strong></a>`;
}
