import { escapeHtml } from "../ui.js";
export const VIEW_ID="claude-certification-guide-hub";
async function api(path){const r=await fetch(path,{credentials:"same-origin"});if(!r.ok)throw new Error(`Request failed (${r.status})`);return r.json();}
export default async function render(root,params={}){
 const track=params.track_id||"snowpro-core";
 const map=await api("/api/skills/map");
 const cert=(map.certifications||[]).find(x=>x.id===track)||(map.certifications||[])[0];
 if(!cert) throw new Error("Certification track is not configured.");
 const domains=cert.domains||[];
 root.innerHTML=`<main class="v26-page">
 <section class="v26-page-intro centered"><p class="v26-kicker">Claude Certification Guide capability</p><h1>${escapeHtml(cert.title||"SnowPro Core")} Exam Guide</h1><p>Blueprint → domain → task → lesson → trap → concept check → exam simulation → build exercise, all inside the existing Snowflake Brain evidence model.</p></section>
 <section class="v26-section"><div class="v26-section-heading"><p class="v26-kicker">Trust & freshness</p><h2>Know what is verified</h2></div><div class="v26-diagnostic-card"><p><strong>Exam code:</strong> ${escapeHtml(cert.exam_code||"COF-C03")} · <strong>Domains:</strong> ${domains.length} · <strong>Source verification:</strong> ${escapeHtml(cert.source_verified_at||"See certification facts")}</p><p>Snowflake Brain keeps unverified exam facts explicit instead of guessing, and routes content changes through the existing freshness/content-integrity controls.</p><a class="v26-btn secondary" href="#/content-integrity">Content integrity</a></div></section>
 <section class="v26-section"><div class="v26-section-heading"><p class="v26-kicker">Task map</p><h2>Study at exam-objective granularity</h2></div>
 ${domains.map((d,di)=>`<article class="v26-diagnostic-card"><p class="v26-kicker">Domain ${di+1} · ${Number(d.weight||0)}%</p><h2>${escapeHtml(d.title)}</h2><p>${escapeHtml(d.description||"")}</p><div class="v26-review-list">${(d.skills||[]).map(s=>`<div class="v26-review-card"><div class="v26-review-body"><p><b>${escapeHtml(s.task_code||"Task")}</b>${escapeHtml(s.title)}</p><p>${escapeHtml(s.objective||"")}</p>${(s.exam_traps||[]).length?`<p><b>Exam trap</b>${escapeHtml(s.exam_traps[0])}</p>`:""}<div class="v26-result-actions"><a class="v26-btn secondary" href="#/skill?track_id=${encodeURIComponent(track)}&skill_id=${encodeURIComponent(s.id)}">Open lesson</a><a class="v26-btn secondary" href="#/practice?track_id=${encodeURIComponent(track)}&mode=drill&skill_id=${encodeURIComponent(s.id)}">Concept check</a><a class="v26-btn secondary" href="#/labs?track_id=${encodeURIComponent(track)}&skill_id=${encodeURIComponent(s.id)}">Build coach</a></div></div></div>`).join("")}</div></article>`).join("")}
 </section>
 <section class="v26-section"><div class="v26-practice-grid">
 <a class="v26-practice-card" href="#/exam-traps?track_id=${encodeURIComponent(track)}"><span>Review</span><h2>Exam Traps</h2><p>Repair adjacent-feature confusion before a timed sitting.</p><div><b>Task mapped</b><em>Open →</em></div></a>
 <a class="v26-practice-card" href="#/mock?track_id=${encodeURIComponent(track)}"><span>Exam Sim</span><h2>Timed simulation</h2><p>Use the authoritative mock player with flags, autosave, resume, timer and review.</p><div><b>Secure session</b><em>Open →</em></div></a>
 <a class="v26-practice-card" href="#/quick-reference?track_id=${encodeURIComponent(track)}"><span>Reference</span><h2>Quick Reference</h2><p>Condensed domain review and glossary-ready recall.</p><div><b>Blueprint aligned</b><em>Open →</em></div></a>
 </div></section></main>`;
}
