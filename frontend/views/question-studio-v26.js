import { escapeHtml, getSkillMap, getStudyLesson } from "../api.js";

export const VIEW_ID = "leetquiz-question-studio";

function option(value,label){return `<option value="${value}">${label}</option>`}

export default async function render(root, params={}) {
  const trackId = params.track_id || "snowpro-core";
  const map = await getSkillMap();
  const cert = (map.certifications||[]).find(row=>row.id===trackId) || (map.certifications||[])[0];
  if (!cert) throw new Error("Certification track is not configured.");
  const domains = cert.domains || [];
  const coachSkills = domains.flatMap(d=>(d.skills||[]).slice(0,2));

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
      <div class="v26-section-heading"><p class="v26-kicker">Contextual tutor</p><h2>Socratic Coach</h2></div>
      <div class="v26-diagnostic-card">
        <p>The coach uses governed Snowflake Brain lesson content and progressive hints. It never reads or reveals a private question answer key.</p>
        <div class="v26-domain-filter-chips">${coachSkills.map(s=>`<button type="button" data-coach-skill="${escapeHtml(s.id)}" data-title="${escapeHtml(s.title)}">${escapeHtml(s.task_code||"Task")} · ${escapeHtml(s.title)}</button>`).join("")}</div>
        <div data-coach-panel><p>Choose a task. Start by explaining which requirement owns the decision before opening a hint.</p></div>
        <div class="v26-result-actions"><a class="v26-btn secondary" href="#/mistakes?track_id=${encodeURIComponent(trackId)}">Repair mistakes</a><a class="v26-btn secondary" href="#/adaptive?track_id=${encodeURIComponent(trackId)}">Adaptive next step</a></div>
      </div>
    </section>
    <section class="v26-section">
      <div class="v26-section-heading"><p class="v26-kicker">Editorial intake</p><h2>Private ingestion stays governed</h2></div>
      <div class="v26-diagnostic-card"><p>Text, PDF, and image source material enters a private editorial intake pipeline. PDF/image files require reviewed normalized text, provenance is fingerprinted, and every intake remains review-only until the existing QA → independent SME approval → staging → active release path is completed.</p><a class="v26-btn secondary" href="#/content-integrity">Content integrity policy</a></div>
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

  root.querySelectorAll("[data-coach-skill]").forEach(button=>button.addEventListener("click",async()=>{
    const panel=root.querySelector("[data-coach-panel]");
    const skillId=button.dataset.coachSkill;
    panel.innerHTML="<p>Loading governed task guidance…</p>";
    try{
      const lesson=await getStudyLesson(skillId,{track_id:trackId});
      const content=lesson.content||{};
      const title=button.dataset.title||lesson.title||"Snowflake task";
      const summary=content.summary||lesson.objective||"State the requirement before choosing the feature.";
      const rule=(content.decision_rules||[])[0]||{};
      const trap=(content.trap_explanations||[])[0]||{};
      const anti=(content.anti_patterns||[])[0]||"";
      panel.innerHTML=`<article class="v26-review-card"><div class="v26-review-body"><p class="v26-kicker">Socratic prompt</p><h3>${escapeHtml(title)}</h3><p>Before opening a hint: what exact requirement tells you which Snowflake capability owns this problem? Name one adjacent feature that is tempting but solves a different layer.</p><details><summary>Hint 1 · concept boundary</summary><p>${escapeHtml(summary)}</p></details>${rule.when||rule.choose||rule.why?`<details><summary>Hint 2 · decision rule</summary><p><b>When</b> ${escapeHtml(rule.when||"Match the scenario requirement.")}</p><p><b>Choose</b> ${escapeHtml(rule.choose||title)}</p><p>${escapeHtml(rule.why||"Prefer the feature whose documented responsibility matches the requirement.")}</p></details>`:""}${trap.trap||anti?`<details><summary>Exam trap</summary><p>${escapeHtml(trap.trap||anti)}</p>${trap.correction?`<p><b>Correction</b> ${escapeHtml(trap.correction)}</p>`:""}</details>`:""}<div class="v26-result-actions"><a class="v26-btn secondary" href="#/skill?track_id=${encodeURIComponent(trackId)}&skill_id=${encodeURIComponent(skillId)}">Open full lesson</a><a class="v26-btn primary" href="#/practice?track_id=${encodeURIComponent(trackId)}&mode=drill&skill_id=${encodeURIComponent(skillId)}">Prove with a drill</a></div></div></article>`;
    }catch(error){
      panel.innerHTML=`<p>${escapeHtml(error.message||"Unable to load task guidance.")}</p>`;
    }
  }));
}
