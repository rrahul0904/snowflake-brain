(() => {
  const D = window.DEMO_DATA;
  if (!D?.questions?.length) return;

  let session = null;
  let timer = null;
  const STORE = 'snowflake-demo-mock-history-v1';
  const $ = (s,r=document) => r.querySelector(s);
  const $$ = (s,r=document) => [...r.querySelectorAll(s)];

  function history(){ try{return JSON.parse(localStorage.getItem(STORE)||'[]')}catch{return[]} }
  function saveHistory(item){ const h=history(); h.unshift(item); localStorage.setItem(STORE,JSON.stringify(h.slice(0,8))); }
  function domain(id){ return D.certification.domains.find(d=>d.id===id); }
  function fmt(sec){ const m=Math.floor(sec/60),s=sec%60; return `${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`; }

  function enhanceMockPage(){
    const buttons=$$('.demo-mock');
    if(!buttons.length) return;
    buttons.forEach((b,i)=>{
      if(b.dataset.mockEnhanced) return;
      b.dataset.mockEnhanced='1';
      b.textContent=i===0?'Preview quick mock →':'Preview full mock →';
      b.addEventListener('click',e=>{e.preventDefault();e.stopImmediatePropagation();openIntro(i===0?'quick':'full')},{capture:true});
    });
    const grid=buttons[0]?.closest('.grid-2');
    if(grid && !grid.nextElementSibling?.classList.contains('mock-preview-note')){
      const n=document.createElement('div'); n.className='mock-preview-note';
      n.innerHTML='<strong>Interactive demo sample</strong><span>The preview uses the independently authored sample set in this fresh demo. Production formats remain 30 questions / 45 minutes and 100 questions / 120 minutes.</span>';
      grid.insertAdjacentElement('afterend',n);
    }
  }

  function overlay(html){
    closeOverlay();
    const el=document.createElement('div');
    el.className='mock-overlay'; el.id='mockOverlay'; el.innerHTML=html;
    document.body.appendChild(el); document.body.classList.add('mock-open');
    return el;
  }
  function closeOverlay(){ clearInterval(timer); timer=null; $('#mockOverlay')?.remove(); document.body.classList.remove('mock-open'); }

  function openIntro(mode){
    const full=mode==='full';
    const count=Math.min(full?8:5,D.questions.length);
    const mins=full?12:8;
    const label=full?'Full mock preview':'Quick mock preview';
    overlay(`<div class="mock-modal mock-intro"><div class="mock-modal-head"><div><span class="eyebrow">Exam simulation</span><h2>${label}</h2></div><button class="mock-close" aria-label="Close mock">×</button></div><div class="mock-intro-grid"><div class="mock-intro-copy"><h1>Simulate the decision pressure, then turn the result into a study plan.</h1><p>This interactive preview uses ${count} independently authored sample questions across the COF-C03 domains. The production engine uses the full weighted bank.</p><div class="mock-rules"><div><strong>${count}</strong><span>demo questions</span></div><div><strong>${mins}</strong><span>minutes</span></div><div><strong>75%</strong><span>demo pass mark</span></div></div></div><div class="mock-checklist"><strong>Before you begin</strong><label><input type="checkbox" checked disabled> Timer runs continuously</label><label><input type="checkbox" checked disabled> Flag and revisit questions</label><label><input type="checkbox" checked disabled> Domain breakdown on submit</label><label><input type="checkbox" checked disabled> Missed concepts become remediation</label></div></div><div class="mock-intro-actions"><button class="button" id="mockCancel">Cancel</button><button class="button primary" id="mockBegin">Begin preview →</button></div></div>`);
    $('.mock-close').onclick=closeOverlay; $('#mockCancel').onclick=closeOverlay;
    $('#mockBegin').onclick=()=>start(mode,count,mins*60);
  }

  function start(mode,count,duration){
    const ordered=[...D.questions];
    // Deterministic domain-spread ordering for a repeatable demo.
    const wanted=['architecture','governance','loading','performance','collaboration'];
    ordered.sort((a,b)=>wanted.indexOf(a.domain)-wanted.indexOf(b.domain));
    const picked=[];
    wanted.forEach(id=>{const q=ordered.find(x=>x.domain===id); if(q&&picked.length<count)picked.push(q)});
    ordered.forEach(q=>{if(!picked.includes(q)&&picked.length<count)picked.push(q)});
    session={mode,questions:picked,index:0,answers:{},flags:{},remaining:duration,startedAt:Date.now()};
    renderSession();
    timer=setInterval(()=>{if(!session)return;session.remaining--;const t=$('#mockTimer');if(t)t.textContent=fmt(Math.max(0,session.remaining));if(session.remaining<=0)submit(true)},1000);
  }

  function renderSession(){
    const q=session.questions[session.index],d=domain(q.domain),answered=Object.keys(session.answers).length;
    overlay(`<div class="mock-workspace"><header class="mock-workbar"><div class="mock-brand"><span class="brand-mark mini" aria-hidden="true">✣</span><div><strong>${session.mode==='full'?'Full mock preview':'Quick mock preview'}</strong><span>COF-C03 interactive sample</span></div></div><div class="mock-workstats"><span>Answered <strong>${answered}/${session.questions.length}</strong></span><span>Flagged <strong>${Object.keys(session.flags).length}</strong></span><span class="mock-timer" id="mockTimer">${fmt(session.remaining)}</span><button class="button small" id="mockExit">Exit</button></div></header><div class="mock-layout"><aside class="mock-palette"><span class="eyebrow">Question map</span><div class="mock-palette-grid">${session.questions.map((x,i)=>`<button data-jump="${i}" class="${i===session.index?'current ':''}${session.answers[x.id]!==undefined?'answered ':''}${session.flags[x.id]?'flagged':''}">${i+1}</button>`).join('')}</div><div class="mock-palette-key"><span><i class="answered"></i>Answered</span><span><i class="flagged"></i>Flagged</span></div><button class="button primary" id="mockSubmit">Submit mock</button></aside><main class="mock-question"><div class="mock-qmeta"><span class="chip brand">${d.short}</span><span class="chip">Task ${q.task}</span><span class="chip">${q.difficulty}</span><span>Question ${session.index+1} of ${session.questions.length}</span></div><h2>${q.stem}</h2><div class="option-list">${q.options.map((o,i)=>`<button class="option mock-option ${session.answers[q.id]===i?'selected':''}" data-answer="${i}"><span class="option-letter">${String.fromCharCode(65+i)}</span><span>${o}</span></button>`).join('')}</div><div class="mock-qactions"><button class="button" id="mockPrev" ${session.index===0?'disabled':''}>← Previous</button><button class="button ${session.flags[q.id]?'warning':''}" id="mockFlag">${session.flags[q.id]?'⚑ Flagged':'⚐ Flag for review'}</button><button class="button primary" id="mockNext">${session.index===session.questions.length-1?'Review & submit':'Next →'}</button></div></main></div></div>`);
    $('#mockExit').onclick=()=>openExitConfirm();
    $('#mockSubmit').onclick=()=>submit(false);
    $('#mockPrev').onclick=()=>{if(session.index>0){session.index--;renderSession()}};
    $('#mockNext').onclick=()=>{if(session.index<session.questions.length-1){session.index++;renderSession()}else openReview()};
    $('#mockFlag').onclick=()=>{session.flags[q.id]?delete session.flags[q.id]:session.flags[q.id]=true;renderSession()};
    $$('.mock-option').forEach(b=>b.onclick=()=>{session.answers[q.id]=Number(b.dataset.answer);renderSession()});
    $$('[data-jump]').forEach(b=>b.onclick=()=>{session.index=Number(b.dataset.jump);renderSession()});
  }

  function openReview(){
    const unanswered=session.questions.filter(q=>session.answers[q.id]===undefined).length;
    const flagged=Object.keys(session.flags).length;
    const pane=document.createElement('div');pane.className='mock-confirm';pane.id='mockConfirm';
    pane.innerHTML=`<div class="mock-confirm-card"><span class="eyebrow">Review checkpoint</span><h2>Ready to submit?</h2><p><strong>${unanswered}</strong> unanswered · <strong>${flagged}</strong> flagged for review.</p><div class="mock-confirm-actions"><button class="button" id="reviewBack">Keep reviewing</button><button class="button primary" id="reviewSubmit">Submit mock</button></div></div>`;
    $('#mockOverlay').appendChild(pane); $('#reviewBack').onclick=()=>pane.remove(); $('#reviewSubmit').onclick=()=>submit(false);
  }
  function openExitConfirm(){
    const pane=document.createElement('div');pane.className='mock-confirm';pane.id='mockConfirm';
    pane.innerHTML='<div class="mock-confirm-card"><span class="eyebrow">Exit simulation</span><h2>End this preview?</h2><p>Your in-progress mock answers will not be scored if you exit.</p><div class="mock-confirm-actions"><button class="button" id="exitBack">Continue mock</button><button class="button danger" id="exitNow">Exit preview</button></div></div>';
    $('#mockOverlay').appendChild(pane); $('#exitBack').onclick=()=>pane.remove(); $('#exitNow').onclick=closeOverlay;
  }

  function submit(auto){
    if(!session)return; clearInterval(timer);timer=null;
    const total=session.questions.length;
    const correct=session.questions.filter(q=>session.answers[q.id]===q.answer).length;
    const score=Math.round(correct/total*100),pass=score>=75;
    const byDomain=D.certification.domains.map(d=>{
      const qs=session.questions.filter(q=>q.domain===d.id); if(!qs.length)return null;
      const c=qs.filter(q=>session.answers[q.id]===q.answer).length;
      return {d,total:qs.length,correct:c,score:Math.round(c/qs.length*100)};
    }).filter(Boolean);
    const missed=session.questions.filter(q=>session.answers[q.id]!==q.answer);
    const result={at:new Date().toISOString(),mode:session.mode,score,correct,total,duration:Math.round((Date.now()-session.startedAt)/1000)};
    saveHistory(result);
    overlay(`<div class="mock-modal mock-results"><div class="mock-modal-head"><div><span class="eyebrow">Mock result</span><h2>${auto?'Time expired · ':''}${pass?'Checkpoint passed':'Remediation recommended'}</h2></div><button class="mock-close" aria-label="Close results">×</button></div><div class="mock-result-hero"><div class="mock-score ${pass?'pass':'review'}"><strong>${score}%</strong><span>${correct}/${total} correct</span></div><div><h1>${pass?'Strong sample performance.':'Use the misses to drive the next study block.'}</h1><p>This score is for the interactive demo sample, not a predictor of official SnowPro exam results.</p></div></div><div class="mock-domain-results">${byDomain.map(x=>`<div><span>${x.d.short}</span><div class="progress-track"><div class="progress-fill" style="width:${x.score}%"></div></div><strong>${x.score}%</strong></div>`).join('')}</div><section class="mock-remediation"><div><span class="eyebrow">Remediation queue</span><h3>${missed.length?`${missed.length} concept${missed.length===1?'':'s'} to revisit`:'No missed concepts in this sample'}</h3></div>${missed.length?missed.map(q=>`<a href="#domain/${q.domain}?task=${q.task}" class="mock-remediation-row"><span class="chip brand">${domain(q.domain).short}</span><strong>Task ${q.task}</strong><span>${q.stem}</span><b>Review →</b></a>`).join(''):'<div class="mock-perfect">Take the full production mock after broader practice coverage.</div>'}</section><div class="mock-intro-actions"><button class="button" id="mockAgain">Retake preview</button><button class="button primary" id="mockDone">Return to Mock Exams →</button></div></div>`);
    const mode=session.mode;session=null;
    $('.mock-close').onclick=closeOverlay; $('#mockDone').onclick=closeOverlay; $('#mockAgain').onclick=()=>openIntro(mode);
  }

  const observer=new MutationObserver(enhanceMockPage);
  const route=$('#routeView'); if(route) observer.observe(route,{childList:true});
  window.addEventListener('hashchange',()=>setTimeout(enhanceMockPage,0));
  document.addEventListener('DOMContentLoaded',enhanceMockPage);
  enhanceMockPage();
})();
