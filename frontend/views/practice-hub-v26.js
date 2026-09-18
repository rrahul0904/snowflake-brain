import { escapeHtml, getAdaptiveReadiness, getMockHistory, getSkillSummary } from "../api.js";
export const VIEW_ID="academyos-practice-hub";
function pct(value){const n=Number(value||0);return Number.isFinite(n)?Math.round(n):0;}
export default async function render(root,params={}){
 const track=params.track_id||"snowpro-core";
 const [readiness,mocks,skills]=await Promise.all([
   getAdaptiveReadiness({track_id:track}).catch(()=>({})),
   getMockHistory({track_id:track}).catch(()=>({sessions:[]})),
   getSkillSummary({track_id:track}).catch(()=>({skills:[]}))
 ]);
 const rows=skills.skills||[];
 const attempts=rows.reduce((s,r)=>s+Number(r.attempts||0),0);
 const weak=rows.filter(r=>Number(r.attempts||0)>0&&Number(r.accuracy_pct||0)<70).length;
 const mastered=rows.filter(r=>Number(r.attempts||0)>0&&Number(r.accuracy_pct||0)>=80).length;
 const readinessPct=pct(readiness.readiness_pct ?? readiness.score ?? readiness.readiness);
 const sessions=mocks.sessions||mocks.history||[];
 root.innerHTML=`<main class="v26-page">
 <section class="v26-page-intro centered"><p class="v26-kicker">AcademyOS capability · Snowflake-native</p><h1>Practice Hub</h1><p>One operational surface for practice, timed exams, domain evidence, Blitz recall, build work and persistent learning history.</p></section>
 <section class="v26-section"><div class="v26-drill-stats">
   <div><strong>${attempts}</strong><span>Practice attempts</span></div>
   <div><strong>${mastered}</strong><span>Mastered tasks</span></div>
   <div><strong>${weak}</strong><span>Weak tasks</span></div>
   <div><strong>${readinessPct}%</strong><span>Evidence readiness</span></div>
 </div></section>
 <section class="v26-section"><div class="v26-practice-grid">
   <a class="v26-practice-card featured" href="#/practice?track_id=${encodeURIComponent(track)}&mode=diagnostic"><span>Measure</span><h2>Diagnostic</h2><p>Balanced baseline across the current blueprint.</p><div><b>Evidence first</b><em>Start →</em></div></a>
   <a class="v26-practice-card" href="#/practice?track_id=${encodeURIComponent(track)}&mode=drill"><span>Repair</span><h2>Targeted Practice</h2><p>Filter by domain, task, difficulty and unanswered history.</p><div><b>Adaptive filters</b><em>Start →</em></div></a>
   <a class="v26-practice-card" href="#/mock/start?track_id=${encodeURIComponent(track)}&type=quick-mock"><span>Timed</span><h2>Quick Mock</h2><p>Persisted sitting with secure server-owned session state.</p><div><b>30 questions</b><em>Start →</em></div></a>
   <a class="v26-practice-card full" href="#/mock/start?track_id=${encodeURIComponent(track)}&type=full-mock"><span>Exam</span><h2>Full Mock</h2><p>Flags, autosave, resume, timer, grading and remediation.</p><div><b>Full simulation</b><em>Start →</em></div></a>
   <a class="v26-practice-card" href="#/daily-session?track_id=${encodeURIComponent(track)}"><span>Blitz</span><h2>Recall Session</h2><p>Fast active recall before recognition-based practice.</p><div><b>Daily loop</b><em>Open →</em></div></a>
   <a class="v26-practice-card" href="#/labs?track_id=${encodeURIComponent(track)}"><span>Build</span><h2>Architecture Builder</h2><p>Apply Snowflake concepts in deterministic labs.</p><div><b>Hands-on</b><em>Open →</em></div></a>
 </div></section>
 <section class="v26-section"><div class="v26-section-heading"><p class="v26-kicker">Domain scoring</p><h2>Persistent evidence by task</h2></div>
 <div class="v26-review-list">${rows.slice().sort((a,b)=>Number(a.accuracy_pct||0)-Number(b.accuracy_pct||0)).slice(0,12).map(r=>`<article class="v26-review-card"><div class="v26-review-body"><p><b>${escapeHtml(r.task_code||r.skill_id||"Task")}</b>${escapeHtml(r.title||r.skill_title||"")}</p><p><b>Accuracy</b>${pct(r.accuracy_pct)}% · <b>Attempts</b>${Number(r.attempts||0)}</p><div class="v26-result-actions"><a class="v26-btn secondary" href="#/practice?track_id=${encodeURIComponent(track)}&mode=drill&skill_id=${encodeURIComponent(r.skill_id||r.id||"")}">Practice</a></div></div></article>`).join("") || '<p>No practice evidence yet.</p>'}</div></section>
 <section class="v26-section"><div class="v26-section-heading"><p class="v26-kicker">Timed history</p><h2>Recent mock sittings</h2></div>
 <div class="v26-review-list">${sessions.slice(0,6).map(s=>`<article class="v26-review-card"><div class="v26-review-body"><p><b>${escapeHtml(s.mode||"Mock")}</b>${escapeHtml(s.status||"completed")}</p><p>${Number(s.score||0)}/${Number(s.total||0)} · ${pct(s.percent||s.score_pct)}%</p>${s.session_id?`<a class="v26-btn secondary" href="#/mock/result?session_id=${encodeURIComponent(s.session_id)}">Review result</a>`:""}</div></article>`).join("") || '<p>No mock history yet.</p>'}</div></section>
 <section class="v26-section"><div class="v26-result-actions"><a class="v26-btn primary" href="#/adaptive?track_id=${encodeURIComponent(track)}">Adaptive next action</a><a class="v26-btn secondary" href="#/progress?track_id=${encodeURIComponent(track)}">Progress dashboard</a><a class="v26-btn secondary" href="#/study-plan?track_id=${encodeURIComponent(track)}">Study plan</a></div></section>
 </main>`;
}
