import { escapeHtml } from "../api.js";
export const VIEW_ID="clouding-academy-daily";
async function api(path){const r=await fetch(path,{credentials:"same-origin"});if(!r.ok)throw new Error(`Request failed (${r.status})`);return r.json();}
function streakKey(track){return `snowflake-brain.blitz-streak.${track}`;}
export default async function render(root,params={}){
 const track=params.track_id||"snowpro-core";
 const map=await api("/api/skills/map");
 const cert=(map.certifications||[]).find(x=>x.id===track)||(map.certifications||[])[0];
 if(!cert) throw new Error("Certification track is not configured.");
 const skills=(cert.domains||[]).flatMap(d=>(d.skills||[]).map(s=>({...s,domain:d.title,weight:d.weight})));
 const today=new Date().toISOString().slice(0,10);
 const seed=[...today].reduce((a,c)=>a+c.charCodeAt(0),0);
 const daily=skills.length?skills[seed%skills.length]:null;
 const streak=JSON.parse(localStorage.getItem(streakKey(track))||'{"count":0,"date":""}');
 root.innerHTML=`<main class="v26-page">
 <section class="v26-page-intro centered"><p class="v26-kicker">Clouding Academy capability</p><h1>Daily Certification Session</h1><p>A small daily loop: recall → reason → practice → build → record evidence.</p></section>
 <section class="v26-section"><div class="v26-practice-grid">
   <article class="v26-practice-card featured"><span>Today</span><h2>${escapeHtml(daily?.title||"SnowPro task")}</h2><p>${escapeHtml(daily?.objective||"Review one exam objective, then prove it with practice.")}</p><div><b>${escapeHtml(daily?.task_code||"Task")}</b><a href="#/skill?track_id=${encodeURIComponent(track)}&skill_id=${encodeURIComponent(daily?.id||"")}">Study →</a></div></article>
   <article class="v26-practice-card"><span>Streak</span><h2><span data-streak>${Number(streak.count||0)}</span> day Blitz</h2><p>Complete one recall card today to extend the local daily recall streak.</p><div><b>Fast recall</b><em>5–10 min</em></div></article>
 </div></section>
 <section class="v26-section"><div class="v26-section-heading"><p class="v26-kicker">Blitz recall</p><h2>Recall before recognition</h2></div>
 <div class="v26-review-list">${skills.slice(0,8).map((s,i)=>`<details class="v26-review-card" data-blitz><summary><span>${i+1}</span><div><small>${escapeHtml(s.task_code||"Task")}</small><strong>${escapeHtml(s.title)}</strong></div></summary><div class="v26-review-body"><p><b>Recall prompt</b>Without notes, explain when this capability is the best fit and name one nearby Snowflake feature that is easy to confuse with it.</p><p><b>Anchor</b>${escapeHtml(s.objective||"")}</p><button class="v26-btn secondary" type="button" data-complete-blitz>Mark recalled</button></div></details>`).join("")}</div></section>
 <section class="v26-section"><div class="v26-section-heading"><p class="v26-kicker">Architecture Builder</p><h2>Choose the owning Snowflake capability</h2></div>
 <div class="v26-diagnostic-card"><p data-arch-prompt>A workload has a requirement. First identify whether the requirement is primarily architecture, governance, ingestion, performance/transformation, or collaboration. Then choose the Snowflake capability that owns that requirement before optimizing implementation details.</p><div class="v26-domain-filter-chips">${(cert.domains||[]).map((d,i)=>`<button type="button" data-arch="${i}" data-title="${escapeHtml(d.title)}">${i+1}. ${escapeHtml(d.title)}</button>`).join("")}</div><div class="v26-result-actions"><a class="v26-btn primary" href="#/labs?track_id=${encodeURIComponent(track)}">Open build labs</a><a class="v26-btn secondary" href="#/practice?track_id=${encodeURIComponent(track)}&mode=drill">Prove with practice</a></div></div></section>
 <section class="v26-section"><div class="v26-result-actions"><a class="v26-btn primary" href="#/adaptive?track_id=${encodeURIComponent(track)}">Use readiness next action</a><a class="v26-btn secondary" href="#/mock?track_id=${encodeURIComponent(track)}">Timed rehearsal</a><a class="v26-btn secondary" href="#/progress?track_id=${encodeURIComponent(track)}">Progress</a></div></section>
 </main>`;
 root.querySelectorAll("[data-complete-blitz]").forEach(button=>button.addEventListener("click",()=>{
   const current=JSON.parse(localStorage.getItem(streakKey(track))||'{"count":0,"date":""}');
   if(current.date!==today){current.count=Number(current.count||0)+1;current.date=today;localStorage.setItem(streakKey(track),JSON.stringify(current));root.querySelector("[data-streak]").textContent=String(current.count);}
   button.textContent="Recalled today ✓";button.disabled=true;
 }));
 root.querySelectorAll("[data-arch]").forEach(button=>button.addEventListener("click",()=>{
   const d=cert.domains[Number(button.dataset.arch)];
   root.querySelector("[data-arch-prompt]").innerHTML=`<strong>${escapeHtml(d.title)}</strong><br/>${escapeHtml(d.description||"")} Before choosing a service, state the requirement, the owning Snowflake layer, and the trade-off you are optimizing. Then validate it in a build lab or targeted drill.`;
 }));
}
