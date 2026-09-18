import { escapeHtml } from "../ui.js";

export const VIEW_ID = "leetquiz-question-studio";

async function api(path, options={}) {
  const response = await fetch(path, { credentials: "same-origin", headers: { "Content-Type": "application/json", ...(options.headers||{}) }, ...options });
  if (!response.ok) {
    const payload = await response.json().catch(()=>({}));
    throw new Error(payload?.detail?.message || payload?.detail || `Request failed (${response.status})`);
  }
  return response.json();
}

function option(value,label){return `<option value="${value}">${label}</option>`}

export default async function render(root, params={}) {
  const trackId = params.track_id || "snowpro-core";
  const map = await api("/api/skills/map");
  const cert = (map.certifications||[]).find(row=>row.id===trackId) || (map.certifications||[])[0];
  if (!cert) throw new Error("Certification track is not configured.");
  const domains = cert.domains || [];
  root.innerHTML = `
  <main class="v26-page">
    <section class="v26-page-intro centered">
      <p class="v26-kicker">LeetQuiz capability · Snowflake-native</p>
      <h1>Question Studio</h1>
      <p>Build a secure custom practice session without exposing the private question-bank inventory. Sessions still flow through Snowflake Brain entitlement, anti-leak, grading, and learning-intelligence controls.</p>
    </section>
    <section class="v26-section">
      <div class="v26-practice-setup">
        <h2>Custom quiz</h2>
        <div class="v26-drill-filter-grid">
          <label class="v26-drill-control"><span>Domain</span><select data-domain><option value="">All domains</option>${domains.map(d=>option(escapeHtml(d.id),escapeHtml(d.title))).join("")}</select></label>
          <label class="v26-drill-control"><span>Difficulty</span><select data-difficulty><option value="">Any difficulty</option>${option("easy","Easy")}${option("medium","Medium")}${option("hard","Hard")}</select></label>
          <label class="v26-drill-control"><span>Questions</span><select data-count>${[5,10,15,20].map(n=>option(String(n),String(n))).join("")}</select></label>
          <label class="v26-drill-checkbox"><input type="checkbox" data-unanswered/><span><strong>Unanswered only</strong><small>Exclude questions already attempted by you.</small></span></label>
        </div>
        <button class="v26-btn primary" type="button" data-start>Start custom quiz</button>
      </div>
    </section>
    <section class="v26-section">
      <div class="v26-section-heading"><p class="v26-kicker">Question Explorer</p><h2>Explore by blueprint, not by leaking bank contents</h2></div>
      <div class="v26-practice-grid">${domains.map((d,i)=>`<article class="v26-practice-card"><span>Domain ${i+1} · ${Number(d.weight||0)}%</span><h2>${escapeHtml(d.title)}</h2><p>${escapeHtml(d.description||"Practice the mapped COF-C03 tasks in this domain.")}</p><div><b>${(d.skills||[]).length} tasks</b><a href="#/practice?track_id=${encodeURIComponent(trackId)}&mode=drill&domain_id=${encodeURIComponent(d.id)}">Practice →</a></div></article>`).join("")}</div>
    </section>
    <section class="v26-section">
      <div class="v26-section-heading"><p class="v26-kicker">AI tutor pattern</p><h2>Socratic Coach</h2></div>
      <div class="v26-diagnostic-card">
        <p data-coach>Choose a topic below. The coach deliberately starts with a reasoning prompt instead of revealing an answer.</p>
        <div class="v26-domain-filter-chips">${domains.flatMap(d=>(d.skills||[]).slice(0,2)).map(s=>`<button type="button" data-coach-skill="${escapeHtml(s.id)}" data-title="${escapeHtml(s.title)}">${escapeHtml(s.task_code||"Task")} · ${escapeHtml(s.title)}</button>`).join("")}</div>
        <div class="v26-result-actions"><a class="v26-btn secondary" href="#/mistakes?track_id=${encodeURIComponent(trackId)}">Repair mistakes</a><a class="v26-btn secondary" href="#/adaptive?track_id=${encodeURIComponent(trackId)}">Adaptive next step</a></div>
      </div>
    </section>
    <section class="v26-section">
      <div class="v26-section-heading"><p class="v26-kicker">Editorial intake</p><h2>Private ingestion stays governed</h2></div>
      <div class="v26-diagnostic-card"><p>Raw text/PDF/image sources are never published directly. Normalize them into the private question-bank schema, run provenance/content QA, then use the governed QA → independent SME approval → staging → active release path. Candidate Question Studio never exposes raw source files, answer keys, pool labels, hashes, or bank-size metadata.</p><a class="v26-btn secondary" href="#/content-integrity">Content integrity policy</a></div>
    </section>
  </main>`;

  root.querySelector("[data-start]")?.addEventListener("click",()=>{
    const q=new URLSearchParams({track_id:trackId,mode:"drill",start:"1",count:root.querySelector("[data-count]").value||"10"});
    const domain=root.querySelector("[data-domain]").value;
    const difficulty=root.querySelector("[data-difficulty]").value;
    if(domain) q.set("domain_id",domain);
    if(difficulty) q.set("difficulty",difficulty);
    if(root.querySelector("[data-unanswered]").checked) q.set("unanswered_only","1");
    window.location.hash=`#/practice?${q}`;
  });
  root.querySelectorAll("[data-coach-skill]").forEach(button=>button.addEventListener("click",()=>{
    const title=button.dataset.title||"this task";
    const node=root.querySelector("[data-coach]");
    node.innerHTML=`<strong>${escapeHtml(title)}</strong><br/>Before looking up the rule: what requirement in the scenario tells you which Snowflake feature owns the problem? Name one tempting adjacent feature, then explain why it is not the best fit. When you can state that distinction, open the task lesson or start a targeted drill.`;
  }));
}
