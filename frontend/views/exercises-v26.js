export const VIEW_ID = "v26-exercises";

import { escapeHtml, getLabs, getSkillMap } from "../api.js";
import { activeTrack } from "../ui.js";
import { DOMAIN_COLORS, studyLayout } from "../components/study-shell.js";
import { evidenceNotice } from "../components/learning-widgets.js";

export default async function mount(container, params = {}) {
  const trackId = params.track_id || activeTrack();
  const [map, payload] = await Promise.all([
    getSkillMap(),
    getLabs({ certification: trackId }).catch(() => ({ mode: "offline", labs: [] })),
  ]);
  const cert = (map.certifications || []).find((item) => item.id === trackId) || (map.certifications || [])[0];
  if (!cert) throw new Error("Certification is not configured");
  const labs = payload.labs || [];
  const completed = labs.filter((lab) => lab.completed).length;
  const mappedIds = new Set();

  const domainSections = (cert.domains || []).map((domain, index) => {
    const skillIds = new Set((domain.skills || []).map((skill) => skill.id));
    const matching = labs.filter((lab) => {
      const match = lab.domain_id === domain.id || skillIds.has(lab.skill_id);
      if (match) mappedIds.add(lab.id);
      return match;
    });
    return domainSection(cert, domain, index, matching);
  }).join("");
  const unmatched = labs.filter((lab) => !mappedIds.has(lab.id));

  container.innerHTML = studyLayout(cert, "exercises", `<a class="v26-study-back" href="#/curriculum?track_id=${encodeURIComponent(cert.id)}" aria-label="Back">‹</a><header class="v26-study-heading"><p class="v26-kicker">Hands-on workbook</p><h1>Build Exercises</h1><p>Apply every SnowPro domain through task-level build work. Where a deterministic standalone lab exists, open the full workspace; otherwise use the authored build exercise inside the mapped task lesson.</p>${evidenceNotice(payload.mode === "offline" ? "Standalone labs use deterministic offline validation. Snowflake Brain does not claim that SQL ran against a live Snowflake account." : `Lab mode: ${payload.mode}.`)}</header><section class="v26-learning-command"><div><span>Exam domains</span><strong>${(cert.domains || []).length}</strong><small>All remain represented</small></div><div><span>Standalone labs</span><strong>${labs.length}</strong><small>Deterministic challenges</small></div><div><span>Completed labs</span><strong>${completed}</strong><small>${labs.length ? `${Math.round(completed / labs.length * 100)}%` : "No standalone lab evidence yet"}</small></div><div><span>Validation</span><strong>${payload.mode === "offline" ? "Offline" : escapeHtml(payload.mode || "Configured")}</strong><small>Execution boundary is explicit</small></div></section><section class="v26-exercise-domain-list">${domainSections}</section>${unmatched.length ? `<section class="v26-progress-section v26-unmapped-labs"><div class="v26-section-heading"><p class="v26-kicker">Additional configured labs</p><h2>Not mapped to the current five-domain IDs.</h2><p>These challenges remain available, but the UI does not silently assign them to a current domain when the stored mapping no longer matches the active blueprint.</p></div><div class="v26-lab-card-grid">${unmatched.map((lab) => labCard(cert, lab)).join("")}</div></section>` : ""}`, "", []);
}

function domainSection(cert, domain, index, labs) {
  const tasks = domain.skills || [];
  return `<article class="v26-exercise-domain command-labs"><header><i style="--domain:${DOMAIN_COLORS[index % DOMAIN_COLORS.length]}"></i><h2>Domain ${index + 1}: ${escapeHtml(domain.title)}</h2><span>${labs.length ? `${labs.length} standalone lab${labs.length === 1 ? "" : "s"}` : `${tasks.length} task exercise${tasks.length === 1 ? "" : "s"}`}</span></header><div class="v26-lab-card-grid">${labs.length ? labs.map((lab) => labCard(cert, lab)).join("") : tasks.map((skill) => taskExerciseCard(cert, skill)).join("")}</div></article>`;
}

function labCard(cert, lab) {
  return `<a class="v26-build-lab-card ${lab.completed ? "completed" : ""}" href="#/labs?certification=${encodeURIComponent(cert.id)}&lab_id=${encodeURIComponent(lab.id)}"><div><span>${lab.completed ? "✓ Completed" : escapeHtml(lab.difficulty || "Lab")}</span><em>${Number(lab.estimated_minutes || lab.minutes || 20)} min</em></div><h3>${escapeHtml(lab.title || "Snowflake build challenge")}</h3><p>${escapeHtml(lab.scenario || lab.why_it_matters || "Apply this task in a guided Snowflake implementation scenario.")}</p><dl><dt>Task</dt><dd>${escapeHtml(lab.skill || lab.skill_id || "Mapped task")}</dd><dt>Checks</dt><dd>${(lab.validation_tests || []).length || "Configured"}</dd><dt>Mode</dt><dd>Guided validation</dd></dl><strong>Open lab workspace →</strong></a>`;
}

function taskExerciseCard(cert, skill) {
  return `<a class="v26-build-lab-card task-fallback" href="#/skill?track_id=${encodeURIComponent(cert.id)}&skill_id=${encodeURIComponent(skill.id)}"><div><span>Lesson build exercise</span><em>${escapeHtml(skill.task_code || "Task")}</em></div><h3>${escapeHtml(skill.title)}</h3><p>${escapeHtml(skill.objective || "Open the task lesson to work through its authored build exercise and validation checklist.")}</p><dl><dt>Execution</dt><dd>Guided/manual</dd><dt>Validation</dt><dd>Lesson checklist</dd><dt>Source</dt><dd>Current task lesson</dd></dl><strong>Open task build exercise →</strong></a>`;
}
