const QUESTIONS = [
  { d:'D1 · Architecture', domain:'Architecture', q:'Which Snowflake architectural characteristic allows compute resources to scale independently from persisted table storage?', a:['Shared-disk warehouse nodes','Separation of storage and compute','A single cluster for all workloads','Local SSD storage on every virtual warehouse'], c:1, e:'Snowflake separates centralized storage from independently scalable virtual warehouse compute.' },
  { d:'D1 · Architecture', domain:'Architecture', q:'What is the primary purpose of a Snowflake virtual warehouse?', a:['Store micro-partitions permanently','Provide compute resources for queries and data operations','Manage account-level RBAC','Publish listings to Marketplace'], c:1, e:'A virtual warehouse supplies compute. Persisted table data is stored separately.' },
  { d:'D1 · Architecture', domain:'Architecture', q:'How does Snowflake physically organize table data in its storage layer?', a:['User-managed partitions','Micro-partitions managed automatically','One file per table','B-tree pages'], c:1, e:'Snowflake automatically stores table data in immutable micro-partitions and maintains metadata about them.' },
  { d:'D1 · Architecture', domain:'Architecture', q:'When an identical query can reuse a valid persisted result, which mechanism can avoid recomputing the query?', a:['Result cache','Resource monitor','Snowpipe','Fail-safe'], c:0, e:'The persisted query result cache can return a prior valid result when reuse conditions are satisfied.' },
  { d:'D2 · Governance', domain:'Governance', q:'Which design principle most directly supports limiting a role to only the privileges it needs?', a:['Data sharing','Least privilege','Auto-suspend','Clustering'], c:1, e:'Least privilege reduces unnecessary access by granting only what a role requires.' },
  { d:'D2 · Governance', domain:'Governance', q:'Which feature can dynamically obscure sensitive values based on policy logic?', a:['Masking policy','File format','Stream','Warehouse scaling policy'], c:0, e:'Dynamic data masking uses masking policies to control how values are presented.' },
  { d:'D2 · Governance', domain:'Governance', q:'What is a resource monitor primarily used to control?', a:['Role hierarchy depth','Virtual warehouse credit consumption','Data retention period','Stage encryption keys'], c:1, e:'Resource monitors help track and control credit usage for warehouses.' },
  { d:'D2 · Governance', domain:'Governance', q:'Which Snowflake capability is designed to access historical table states within the configured retention window?', a:['Time Travel','Search Optimization','Snowpipe','Secure Data Sharing'], c:0, e:'Time Travel provides historical data access and recovery capabilities within the retention period.' },
  { d:'D3 · Loading', domain:'Loading', q:'In Snowflake, what is a stage primarily used for?', a:['Holding files for data loading/unloading workflows','Assigning object ownership','Caching query results','Scaling clusters automatically'], c:0, e:'Stages are locations used to reference files for loading and unloading data.' },
  { d:'D3 · Loading', domain:'Loading', q:'Which command is commonly used to load staged files into a Snowflake table?', a:['COPY INTO','GRANT OWNERSHIP','ALTER WAREHOUSE','CREATE STREAM'], c:0, e:'COPY INTO <table> loads data from a stage into a target table.' },
  { d:'D3 · Loading', domain:'Loading', q:'Which feature supports continuous file ingestion when new files arrive in cloud storage?', a:['Snowpipe','Result cache','Time Travel','Materialized view'], c:0, e:'Snowpipe supports automated continuous ingestion of newly arriving files.' },
  { d:'D3 · Loading', domain:'Loading', q:'Why define a FILE FORMAT object?', a:['To centralize parsing rules for staged data files','To reserve warehouse credits','To define row access permissions','To cluster a table'], c:0, e:'FILE FORMAT objects capture reusable parsing settings such as type, delimiter, compression and header behavior.' },
  { d:'D3 · Loading', domain:'Loading', q:'What is a storage integration designed to improve?', a:['Secure access from Snowflake to external cloud storage','Query result caching','Role inheritance','Automatic clustering'], c:0, e:'Storage integrations provide a managed security model for access to external cloud storage.' },
  { d:'D4 · Performance', domain:'Performance', q:'When would a clustering key be most relevant?', a:['For every small table by default','When very large tables have selective filters and natural clustering is insufficient','To enable Time Travel','To create a role hierarchy'], c:1, e:'Clustering keys can help large tables when pruning on important access patterns is poor enough to justify maintenance cost.' },
  { d:'D4 · Performance', domain:'Performance', q:'Which interface is most useful for examining where a query spent time across operators?', a:['Query Profile','Marketplace','Resource monitor only','Network policy'], c:0, e:'Query Profile exposes execution operators and timing information useful for diagnosis.' },
  { d:'D4 · Performance', domain:'Performance', q:'What is the main reason to use a multi-cluster warehouse?', a:['Increase table retention','Handle higher concurrent query demand','Create database clones','Replace file formats'], c:1, e:'Multi-cluster warehouses scale out compute clusters primarily to address concurrency.' },
  { d:'D4 · Transformation', domain:'Performance', q:'What does a stream primarily track?', a:['Table change data for incremental processing','User login attempts','Warehouse credits','Stage file formats'], c:0, e:'Streams expose change tracking information that can be consumed by downstream incremental workflows.' },
  { d:'D4 · Transformation', domain:'Performance', q:'What does a task primarily provide?', a:['Scheduled or triggered SQL execution','Long-term table storage','Account authentication','Data marketplace listings'], c:0, e:'Tasks automate SQL execution on a schedule or through task graph dependencies/triggers.' },
  { d:'D5 · Collaboration', domain:'Collaboration', q:'What is a key characteristic of Secure Data Sharing?', a:['The consumer must copy all shared data into its account','Data can be shared without creating another stored copy for the consumer','Only CSV files can be shared','It requires the same virtual warehouse'], c:1, e:'Secure Data Sharing lets consumers query shared data without a traditional data-copy workflow.' },
  { d:'D5 · Collaboration', domain:'Collaboration', q:'What is Snowflake Marketplace used for?', a:['Discovering and accessing published data/apps/listings','Changing micro-partition size','Managing local passwords only','Replacing virtual warehouses'], c:0, e:'Marketplace is a discovery and distribution channel for listings such as data products and applications.' }
];

const GUIDE = [
  {id:'Architecture', code:'D1', weight:31, title:'Architecture & Core Concepts', tasks:[
    ['1.1','Snowflake architecture','Separate storage, compute, and cloud services. Know which layer owns each responsibility.','Exam cue: diagnose the layer involved before choosing a scaling or storage answer.'],
    ['1.2','Virtual warehouses','Understand warehouse sizing, auto-suspend/resume, scaling and workload isolation.','Exam cue: warehouses provide compute; they do not permanently store table data.'],
    ['1.3','Storage & micro-partitions','Snowflake automatically creates immutable micro-partitions and tracks metadata for pruning.','Exam cue: users do not manually create traditional table partitions.'],
    ['1.4','Caching & query results','Distinguish persisted result cache, warehouse cache, metadata pruning and cloud-services behavior.','Exam cue: identify whether the question is about avoiding compute, reducing scans, or reusing results.']
  ]},
  {id:'Governance', code:'D2', weight:20, title:'Account Management & Governance', tasks:[
    ['2.1','Roles & privileges','Use role hierarchy, ownership and least privilege to reason about object access.','Exam cue: ask who owns the object, what privilege is required, and through which role it is inherited.'],
    ['2.2','Authentication & network controls','Understand users, authentication options, network policies and secure account access.','Exam cue: separate identity controls from object authorization.'],
    ['2.3','Governance policies','Know masking, row access, tags, classification and policy-driven controls.','Exam cue: choose a policy when behavior should change dynamically by context.'],
    ['2.4','Cost & resource governance','Use resource monitors and warehouse configuration to control and observe compute consumption.','Exam cue: credit governance is usually a warehouse/account control, not a table-storage setting.']
  ]},
  {id:'Loading', code:'D3', weight:18, title:'Loading, Unloading & Connectivity', tasks:[
    ['3.1','Stages & file formats','Understand internal/external stages and reusable parsing rules.','Exam cue: a stage identifies where files live; a file format defines how to parse them.'],
    ['3.2','Bulk loading with COPY','Know COPY INTO patterns, validation, error handling and load history concepts.','Exam cue: COPY is the standard batch file-loading command.'],
    ['3.3','Continuous ingestion','Understand Snowpipe and event-driven ingestion patterns.','Exam cue: choose Snowpipe for continuous arrival of files rather than a one-time bulk load.'],
    ['3.4','Unloading data','Know COPY INTO location, file formats and common export considerations.','Exam cue: distinguish loading into a table from unloading to a stage.'],
    ['3.5','Integrations & connectivity','Understand storage integrations, external access patterns, drivers and connectors conceptually.','Exam cue: prefer managed integrations over embedded cloud credentials.']
  ]},
  {id:'Performance', code:'D4', weight:21, title:'Performance, Querying & Transformation', tasks:[
    ['4.1','Query Profile','Read operator evidence, scan behavior, spilling, joins and queueing.','Exam cue: use Query Profile when the question asks where execution time is being spent.'],
    ['4.2','Pruning & clustering','Understand natural clustering, pruning and when explicit clustering can justify its cost.','Exam cue: do not recommend clustering keys for every table.'],
    ['4.3','Warehouse performance','Reason about size, concurrency, multi-cluster warehouses and workload separation.','Exam cue: scale up for more compute per query; scale out primarily for concurrency.'],
    ['4.4','Streams & incremental change','Streams expose change tracking for incremental processing.','Exam cue: a stream tracks changes; it does not schedule work.'],
    ['4.5','Tasks & automation','Tasks schedule or trigger SQL and can form dependency graphs.','Exam cue: tasks execute work; streams provide the change data that work may consume.']
  ]},
  {id:'Collaboration', code:'D5', weight:10, title:'Data Collaboration', tasks:[
    ['5.1','Secure Data Sharing','Share governed data across accounts without a traditional consumer-side copy.','Exam cue: providers retain control while consumers query shared objects with their own compute.'],
    ['5.2','Listings & Marketplace','Understand discovery, distribution and access through listings and Marketplace.','Exam cue: Marketplace is a distribution/discovery layer, not a storage or compute feature.']
  ]}
];

const INSIGHTS = [
  {tag:'Architecture', title:'Compute problems are not storage problems', text:'A common SnowPro trap is treating a virtual warehouse as if it stores table data. Start by classifying the symptom: storage layout, compute capacity, concurrency, cache reuse, or cloud-services metadata. Once the layer is clear, the answer space becomes much smaller.', action:'Architecture'},
  {tag:'Performance', title:'Read Query Profile as evidence, not decoration', text:'When a question describes a slow query, look for the bottleneck implied by the evidence: excessive scanning, poor pruning, spilling, expensive joins, queueing, or concurrency. Query Profile is the diagnostic interface; warehouse changes should follow the observed bottleneck.', action:'Performance'},
  {tag:'Governance', title:'Roles, policies and ownership without confusion', text:'Authorization questions are easier when you separate three ideas: ownership controls the object, privileges define allowed actions, and role hierarchy determines how privileges are inherited. Policies add dynamic governance rather than replacing RBAC.', action:'Governance'},
  {tag:'Loading', title:'COPY, Snowpipe and stages: choose the pattern', text:'A stage points to files. A file format defines parsing. COPY INTO handles bulk loading or unloading. Snowpipe is for continuous file ingestion. Storage integrations provide managed cloud-storage access. Match the requirement before choosing the feature.', action:'Loading'},
  {tag:'Collaboration', title:'Secure sharing without moving the data', text:'Secure Data Sharing is about governed access rather than a traditional copy pipeline. The provider shares objects, the consumer uses its own compute, and the provider can control what remains available. That distinction is central to collaboration questions.', action:'Collaboration'},
  {tag:'Strategy', title:'Let blueprint weight set the baseline, then let evidence take over', text:'Start with the official weighting so Architecture and Performance receive proportionally more attention. After you have enough attempts, stop allocating time blindly: redirect study toward the domains where your own accuracy is lowest.', action:null}
];

const STORE_KEY = 'snowflake-beta-learning-v4';
function loadLearning(){
  try { return JSON.parse(localStorage.getItem(STORE_KEY) || '{}'); } catch { return {}; }
}
let saved = loadLearning();
let state = {
  i: 0,
  answers: Array(QUESTIONS.length).fill(null),
  score: 0,
  rating: 0,
  mock: saved.mock || null,
  practiceHistory: Array.isArray(saved.practiceHistory) ? saved.practiceHistory : []
};
function saveLearning(){
  localStorage.setItem(STORE_KEY, JSON.stringify({mock:state.mock, practiceHistory:state.practiceHistory.slice(-10)}));
}
function escapeHtml(v){ return String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

function renderQ(){
  const q = QUESTIONS[state.i];
  const qLabel = document.getElementById('qLabel');
  if(!qLabel) return;
  qLabel.textContent = `Question ${state.i+1} of ${QUESTIONS.length}`;
  document.getElementById('qDomain').textContent = q.d;
  document.getElementById('qText').textContent = q.q;
  document.getElementById('qProgress').style.width = `${((state.i+1)/QUESTIONS.length)*100}%`;
  const root=document.getElementById('answers'); root.innerHTML='';
  q.a.forEach((txt,idx)=>{
    const b=document.createElement('button'); b.className='answer'; b.type='button'; b.innerHTML=`<b>${String.fromCharCode(65+idx)}</b><span>${escapeHtml(txt)}</span>`;
    if(state.answers[state.i]!==null){ b.disabled=true; if(idx===q.c)b.classList.add('correct'); if(idx===state.answers[state.i]&&idx!==q.c)b.classList.add('wrong'); }
    b.addEventListener('click',()=>answer(idx)); root.appendChild(b);
  });
  const explain=document.getElementById('explain');
  if(state.answers[state.i]!==null){ explain.textContent=q.e; explain.classList.add('show'); } else { explain.textContent=''; explain.classList.remove('show'); }
  document.getElementById('prevQ').disabled=state.i===0;
  document.getElementById('nextQ').textContent=state.i===QUESTIONS.length-1?'Finish':'Next →';
  renderSide();
}
function answer(idx){
  if(state.answers[state.i]!==null)return;
  state.answers[state.i]=idx; if(idx===QUESTIONS[state.i].c)state.score++;
  renderQ(); renderAdaptive();
  if(state.answers.every(v=>v!==null)) completePractice();
}
function completePractice(){
  const row={at:new Date().toISOString(),answers:[...state.answers],score:state.score};
  const prior=state.practiceHistory[state.practiceHistory.length-1];
  if(!prior || JSON.stringify(prior.answers)!==JSON.stringify(row.answers)){ state.practiceHistory.push(row); saveLearning(); }
}
function renderSide(){
  const answeredCount=state.answers.filter(v=>v!==null).length;
  document.getElementById('score').textContent=state.score;
  document.getElementById('answered').textContent=answeredCount;
  document.getElementById('dashScore').textContent=`${state.score}/${QUESTIONS.length}`;
  document.getElementById('dashAnswered').textContent=answeredCount;
  const jump=document.getElementById('jump'); if(!jump)return; jump.innerHTML='';
  QUESTIONS.forEach((_,idx)=>{const b=document.createElement('button');b.type='button';b.textContent=idx+1;b.setAttribute('aria-label',`Go to question ${idx+1}`);if(idx===state.i)b.classList.add('current');else if(state.answers[idx]!==null)b.classList.add('done');b.addEventListener('click',()=>{state.i=idx;renderQ();document.querySelector('.question-card')?.scrollIntoView({behavior:'smooth',block:'start'});});jump.appendChild(b);});
}
document.getElementById('prevQ')?.addEventListener('click',()=>{if(state.i>0){state.i--;renderQ();}});
document.getElementById('nextQ')?.addEventListener('click',()=>{if(state.i<QUESTIONS.length-1){state.i++;renderQ();}else{completePractice();openFeedback('Finished 20-question practice');}});
document.getElementById('restart')?.addEventListener('click',()=>{state.i=0;state.answers=Array(QUESTIONS.length).fill(null);state.score=0;renderQ();renderAdaptive();});

function injectFunctionalStyles(){
  if(document.getElementById('functionalStyles'))return;
  const s=document.createElement('style');s.id='functionalStyles';s.textContent=`
  .interactive-shell{display:grid;grid-template-columns:minmax(0,1fr) 330px;gap:20px;margin-bottom:54px}.learning-panel,.lesson-panel,.mock-panel,.adaptive-panel,.insight-panel{border:1px solid var(--line);background:var(--panel);border-radius:20px;padding:22px}.domain-nav{display:grid;gap:10px}.domain-btn,.task-btn,.insight-open{width:100%;text-align:left;border:1px solid var(--line);background:var(--surface);color:var(--text);border-radius:14px;padding:14px;cursor:pointer}.domain-btn.active,.task-btn.active{border-color:var(--cyan);box-shadow:0 0 0 1px color-mix(in srgb,var(--cyan) 45%,transparent)}.domain-btn strong,.task-btn strong{display:block;margin-bottom:4px}.domain-btn small,.task-btn small{color:var(--muted)}.lesson-panel h2{margin:4px 0 10px}.lesson-panel .lesson-copy{font-size:17px;line-height:1.7;color:var(--muted)}.exam-cue{margin:18px 0;padding:15px;border-left:3px solid var(--cyan);background:color-mix(in srgb,var(--cyan) 8%,transparent);border-radius:0 12px 12px 0}.task-list{display:grid;gap:8px;margin-top:16px}.mock-controls{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.mock-timer{font-variant-numeric:tabular-nums;font-size:22px;font-weight:800}.mock-options{display:grid;gap:10px;margin:18px 0}.mock-option{display:flex;gap:12px;text-align:left;width:100%;padding:14px;border:1px solid var(--line);border-radius:14px;background:var(--surface);color:var(--text);cursor:pointer}.mock-option.selected{border-color:var(--cyan)}.mock-option.correct{border-color:#42d392}.mock-option.wrong{border-color:#ff7386}.mock-jump{display:grid;grid-template-columns:repeat(5,1fr);gap:7px;margin-top:16px}.mock-jump button{padding:9px 0;border:1px solid var(--line);border-radius:9px;background:var(--surface);color:var(--text)}.mock-jump button.current{border-color:var(--cyan)}.mock-jump button.done{background:color-mix(in srgb,var(--cyan) 12%,var(--surface))}.domain-bars{display:grid;gap:12px}.domain-bar{display:grid;grid-template-columns:120px 1fr 58px;gap:12px;align-items:center}.bar-track{height:9px;border-radius:999px;background:var(--surface);overflow:hidden}.bar-track i{display:block;height:100%;background:linear-gradient(90deg,var(--cyan),var(--violet));border-radius:999px}.adaptive-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.adaptive-card{border:1px solid var(--line);border-radius:16px;padding:18px;background:var(--surface)}.adaptive-card .rank{font-size:12px;color:var(--cyan);text-transform:uppercase;letter-spacing:.08em}.adaptive-card strong{display:block;font-size:21px;margin:8px 0}.insights-live{display:grid;grid-template-columns:repeat(2,1fr);gap:14px;margin-bottom:54px}.insight-open h3{margin:8px 0}.insight-open p{color:var(--muted);margin:0}.insight-detail{grid-column:1/-1}.insight-detail h2{margin-top:4px}.insight-detail p{font-size:17px;line-height:1.7;color:var(--muted)}.functional-status{color:var(--muted);font-size:13px}.result-big{font-size:46px;font-weight:850;letter-spacing:-.04em}.review-row{padding:14px 0;border-top:1px solid var(--line)}
  @media(max-width:850px){.interactive-shell{grid-template-columns:1fr}.adaptive-grid,.insights-live{grid-template-columns:1fr}.insight-detail{grid-column:auto}.domain-bar{grid-template-columns:95px 1fr 48px}.learning-panel{order:2}}
  `;document.head.appendChild(s);
}

function renderGuide(){
  const section=document.getElementById('guide'); if(!section)return;
  if(section.dataset.functional==='1')return; section.dataset.functional='1';
  const originalHero=section.querySelector('.page-hero')?.outerHTML||'';
  section.innerHTML=`${originalHero}<div class="wrap interactive-shell"><aside class="learning-panel"><span class="eyebrow">5 weighted domains · 19 tasks</span><div id="guideDomains" class="domain-nav"></div></aside><article class="lesson-panel" id="guideLesson"></article></div>`;
  const domains=section.querySelector('#guideDomains');
  GUIDE.forEach((d,idx)=>{const b=document.createElement('button');b.className='domain-btn';b.innerHTML=`<strong>${d.code} · ${escapeHtml(d.title)}</strong><small>${d.weight}% exam weight · ${d.tasks.length} tasks</small>`;b.onclick=()=>showGuideDomain(idx);domains.appendChild(b);});
  showGuideDomain(0);
}
function showGuideDomain(index){
  const d=GUIDE[index]; document.querySelectorAll('#guideDomains .domain-btn').forEach((b,i)=>b.classList.toggle('active',i===index));
  const lesson=document.getElementById('guideLesson'); if(!lesson)return;
  lesson.innerHTML=`<span class="eyebrow">${d.code} · ${d.weight}% exam weight</span><h2>${escapeHtml(d.title)}</h2><p class="lesson-copy">Choose a task below to open its exam-focused lesson.</p><div class="task-list" id="taskList"></div><div id="taskDetail"></div>`;
  const list=lesson.querySelector('#taskList');d.tasks.forEach((t,i)=>{const b=document.createElement('button');b.className='task-btn';b.innerHTML=`<strong>${t[0]} · ${escapeHtml(t[1])}</strong><small>Open lesson →</small>`;b.onclick=()=>showTask(d,i);list.appendChild(b);});showTask(d,0);
}
function showTask(domain,index){
  document.querySelectorAll('#taskList .task-btn').forEach((b,i)=>b.classList.toggle('active',i===index));const t=domain.tasks[index];const root=document.getElementById('taskDetail');if(!root)return;
  root.innerHTML=`<div style="margin-top:22px"><span class="eyebrow">Task ${t[0]}</span><h2>${escapeHtml(t[1])}</h2><p class="lesson-copy">${escapeHtml(t[2])}</p><div class="exam-cue"><strong>Exam-focused takeaway</strong><div>${escapeHtml(t[3])}</div></div><div class="mock-controls"><button class="btn primary" id="practiceDomain">Practice ${escapeHtml(domain.id)} →</button><button class="btn" onclick="openFeedback('Study guide · ${escapeHtml(t[0])}')">Give lesson feedback</button></div></div>`;
  root.querySelector('#practiceDomain')?.addEventListener('click',()=>{const first=QUESTIONS.findIndex(q=>q.domain===domain.id);if(first>=0){state.i=first;location.hash='#practice';setTimeout(renderQ,0);}});
}

let mockTimerHandle=null;
function newMock(){
  const indices=[...QUESTIONS.keys()];for(let i=indices.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[indices[i],indices[j]]=[indices[j],indices[i]];}
  state.mock={indices:indices.slice(0,10),answers:Array(10).fill(null),i:0,startedAt:Date.now(),secondsLeft:900,submitted:false,score:null};saveLearning();renderMock();startMockTimer();
}
function startMockTimer(){clearInterval(mockTimerHandle);if(!state.mock||state.mock.submitted)return;mockTimerHandle=setInterval(()=>{if(!state.mock||state.mock.submitted){clearInterval(mockTimerHandle);return;}const elapsed=Math.floor((Date.now()-state.mock.startedAt)/1000);state.mock.secondsLeft=Math.max(0,900-elapsed);if(state.mock.secondsLeft===0)submitMock();else updateTimer();},1000);}
function updateTimer(){const node=document.getElementById('mockTimer');if(!node||!state.mock)return;const m=Math.floor(state.mock.secondsLeft/60),s=state.mock.secondsLeft%60;node.textContent=`${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;}
function renderMock(){
  const section=document.getElementById('mock');if(!section)return;
  const hero=`<div class="wrap page-hero"><span class="eyebrow">Mock Exam</span><h1>Practice under pressure.</h1><p>This beta mock uses 10 original demo questions with a 15-minute timer. Answers and explanations stay hidden until submission.</p></div>`;
  if(!state.mock){section.innerHTML=`${hero}<div class="wrap"><article class="mock-panel"><span class="eyebrow">Beta simulation</span><h2>10 questions · 15 minutes</h2><p>Navigate freely, change answers before submission, then get a score and domain breakdown.</p><button class="btn primary" id="startMock">Start beta mock →</button></article></div>`;section.querySelector('#startMock')?.addEventListener('click',newMock);return;}
  const m=state.mock;
  if(m.submitted){
    const pct=Math.round((m.score/10)*100);const breakdown=domainStatsFromAnswers(m.indices,m.answers);
    section.innerHTML=`${hero}<div class="wrap"><article class="mock-panel"><span class="eyebrow">Completed</span><div class="result-big">${m.score}/10</div><p>${pct}% on this beta mock. This is a practice result, not an official Snowflake score.</p><div class="domain-bars">${Object.entries(breakdown).map(([d,v])=>`<div class="domain-bar"><span>${escapeHtml(d)}</span><div class="bar-track"><i style="width:${v.total?Math.round(v.correct/v.total*100):0}%"></i></div><strong>${v.correct}/${v.total}</strong></div>`).join('')}</div><div class="mock-controls" style="margin-top:20px"><button class="btn primary" id="restartMock">New mock</button><a class="btn" href="#adaptive">Open adaptive plan →</a></div><div style="margin-top:24px"><h3>Answer review</h3>${m.indices.map((qi,i)=>{const q=QUESTIONS[qi],ok=m.answers[i]===q.c;return `<div class="review-row"><strong>${i+1}. ${ok?'✓':'✕'} ${escapeHtml(q.q)}</strong><div class="functional-status">Your answer: ${m.answers[i]===null?'Unanswered':escapeHtml(q.a[m.answers[i]])}</div><div class="functional-status">Correct: ${escapeHtml(q.a[q.c])} · ${escapeHtml(q.e)}</div></div>`;}).join('')}</div></article></div>`;
    section.querySelector('#restartMock')?.addEventListener('click',newMock);renderAdaptive();return;
  }
  const q=QUESTIONS[m.indices[m.i]];
  section.innerHTML=`${hero}<div class="wrap interactive-shell"><article class="mock-panel"><div class="qmeta"><span>Question ${m.i+1} of 10 · ${escapeHtml(q.d)}</span><span id="mockTimer" class="mock-timer"></span></div><h2>${escapeHtml(q.q)}</h2><div class="mock-options" id="mockOptions"></div><div class="mock-controls"><button class="btn" id="mockPrev">← Previous</button><button class="btn" id="mockNext">Next →</button><button class="btn primary" id="submitMock">Submit mock</button></div></article><aside class="learning-panel"><span class="eyebrow">Navigator</span><div class="mock-jump" id="mockJump"></div><p class="functional-status"><span id="mockAnswered"></span>/10 answered. Explanations unlock only after submission.</p></aside></div>`;
  const options=section.querySelector('#mockOptions');q.a.forEach((txt,idx)=>{const b=document.createElement('button');b.className='mock-option'+(m.answers[m.i]===idx?' selected':'');b.innerHTML=`<b>${String.fromCharCode(65+idx)}</b><span>${escapeHtml(txt)}</span>`;b.onclick=()=>{m.answers[m.i]=idx;saveLearning();renderMock();};options.appendChild(b);});
  const jump=section.querySelector('#mockJump');m.indices.forEach((_,idx)=>{const b=document.createElement('button');b.textContent=idx+1;b.className=(idx===m.i?'current ':'')+(m.answers[idx]!==null?'done':'');b.onclick=()=>{m.i=idx;saveLearning();renderMock();};jump.appendChild(b);});
  section.querySelector('#mockAnswered').textContent=m.answers.filter(v=>v!==null).length;
  section.querySelector('#mockPrev').onclick=()=>{if(m.i>0){m.i--;saveLearning();renderMock();}};section.querySelector('#mockNext').onclick=()=>{if(m.i<9){m.i++;saveLearning();renderMock();}};section.querySelector('#submitMock').onclick=()=>{if(confirm(`Submit this mock with ${m.answers.filter(v=>v!==null).length}/10 answered?`))submitMock();};updateTimer();startMockTimer();
}
function submitMock(){if(!state.mock||state.mock.submitted)return;clearInterval(mockTimerHandle);state.mock.submitted=true;state.mock.score=state.mock.indices.reduce((n,qi,i)=>n+(state.mock.answers[i]===QUESTIONS[qi].c?1:0),0);saveLearning();renderMock();openFeedback('Completed beta mock');}

function domainStatsFromAnswers(indices,answers){const out={Architecture:{correct:0,total:0},Governance:{correct:0,total:0},Loading:{correct:0,total:0},Performance:{correct:0,total:0},Collaboration:{correct:0,total:0}};indices.forEach((qi,i)=>{const q=QUESTIONS[qi];out[q.domain].total++;if(answers[i]===q.c)out[q.domain].correct++;});return out;}
function aggregateStats(){const all=[];state.practiceHistory.forEach(h=>{QUESTIONS.forEach((_,i)=>{if(h.answers?.[i]!==null&&h.answers?.[i]!==undefined)all.push([i,h.answers[i]]);});});state.answers.forEach((a,i)=>{if(a!==null)all.push([i,a]);});if(state.mock?.submitted)state.mock.indices.forEach((qi,i)=>all.push([qi,state.mock.answers[i]]));const stats={Architecture:{correct:0,total:0,weight:31},Governance:{correct:0,total:0,weight:20},Loading:{correct:0,total:0,weight:18},Performance:{correct:0,total:0,weight:21},Collaboration:{correct:0,total:0,weight:10}};all.forEach(([qi,a])=>{const q=QUESTIONS[qi];stats[q.domain].total++;if(a===q.c)stats[q.domain].correct++;});return stats;}
function renderAdaptive(){
  const section=document.getElementById('adaptive');if(!section)return;const stats=aggregateStats();const rows=Object.entries(stats).map(([domain,v])=>{const accuracy=v.total?v.correct/v.total:null;const weakness=accuracy===null?0.55:1-accuracy;const priority=weakness*(v.weight/100);return{domain,...v,accuracy,priority};}).sort((a,b)=>b.priority-a.priority);
  section.innerHTML=`<div class="wrap page-hero"><span class="eyebrow">Adaptive Readiness</span><h1>Spend the next hour where it matters.</h1><p>Recommendations below are calculated from this browser's practice and submitted mock evidence, weighted by the COF-C03 blueprint.</p></div><div class="wrap"><div class="adaptive-grid">${rows.slice(0,3).map((r,i)=>`<article class="adaptive-card"><span class="rank">Priority ${i+1}</span><strong>${escapeHtml(r.domain)}</strong><p>${r.total?`${Math.round(r.accuracy*100)}% accuracy across ${r.total} recorded answers.`:'No attempt evidence yet — blueprint weight drives the initial priority.'}</p><button class="btn ${i===0?'primary':''}" data-adaptive-domain="${escapeHtml(r.domain)}">Practice this domain →</button></article>`).join('')}</div><article class="adaptive-panel" style="margin-top:18px"><span class="eyebrow">Evidence by domain</span><div class="domain-bars" style="margin-top:14px">${rows.map(r=>`<div class="domain-bar"><span>${escapeHtml(r.domain)}</span><div class="bar-track"><i style="width:${r.accuracy===null?0:Math.round(r.accuracy*100)}%"></i></div><strong>${r.total?r.correct+'/'+r.total:'—'}</strong></div>`).join('')}</div><p class="functional-status" style="margin-top:16px">Adaptive scores in this beta are local learning indicators only. The production engine uses a richer candidate history, confidence, due review and mastery model.</p></article></div>`;
  section.querySelectorAll('[data-adaptive-domain]').forEach(b=>b.addEventListener('click',()=>{const first=QUESTIONS.findIndex(q=>q.domain===b.dataset.adaptiveDomain);if(first>=0){state.i=first;location.hash='#practice';setTimeout(renderQ,0);}}));
}

function renderInsights(){
  const section=document.getElementById('insights');if(!section)return;section.innerHTML=`<div class="wrap page-hero"><span class="eyebrow">Exam Insights</span><h1>Short notes for better decisions.</h1><p>Open any insight for the full note, then jump directly into related practice.</p></div><div class="wrap insights-live" id="insightGrid"></div>`;const grid=section.querySelector('#insightGrid');INSIGHTS.forEach((item,i)=>{const b=document.createElement('button');b.className='insight-open';b.innerHTML=`<span class="eyebrow">${escapeHtml(item.tag)}</span><h3>${escapeHtml(item.title)}</h3><p>${escapeHtml(item.text.slice(0,115))}…</p>`;b.onclick=()=>showInsight(i);grid.appendChild(b);});const detail=document.createElement('article');detail.id='insightDetail';detail.className='insight-panel insight-detail';grid.appendChild(detail);showInsight(0);
}
function showInsight(index){const item=INSIGHTS[index],root=document.getElementById('insightDetail');if(!root)return;root.innerHTML=`<span class="eyebrow">${escapeHtml(item.tag)}</span><h2>${escapeHtml(item.title)}</h2><p>${escapeHtml(item.text)}</p><div class="mock-controls">${item.action?`<button class="btn primary" id="insightPractice">Practice ${escapeHtml(item.action)} →</button>`:''}<button class="btn" onclick="openFeedback('Insight · ${escapeHtml(item.title)}')">Give feedback on this note</button></div>`;root.querySelector('#insightPractice')?.addEventListener('click',()=>{const first=QUESTIONS.findIndex(q=>q.domain===item.action);if(first>=0){state.i=first;location.hash='#practice';setTimeout(renderQ,0);}});root.scrollIntoView({behavior:'smooth',block:'nearest'});}

function route(){
  const id=(location.hash||'#home').slice(1).split('?')[0];document.querySelectorAll('.route').forEach(node=>node.classList.toggle('active',node.id===id));document.querySelectorAll('.nav a, .mobile-nav a').forEach(a=>a.classList.toggle('active',a.getAttribute('href')===`#${id}`));
  if(id==='guide')renderGuide();if(id==='mock')renderMock();if(id==='adaptive')renderAdaptive();if(id==='insights')renderInsights();window.scrollTo(0,0);
}
window.addEventListener('hashchange',route);injectFunctionalStyles();renderGuide();renderMock();renderAdaptive();renderInsights();route();renderQ();

const themeBtn=document.getElementById('themeBtn');const savedTheme=localStorage.getItem('snowflake-beta-theme');if(savedTheme==='light'||savedTheme==='dark')document.documentElement.dataset.theme=savedTheme;themeBtn?.addEventListener('click',()=>{const next=document.documentElement.dataset.theme==='dark'?'light':'dark';document.documentElement.dataset.theme=next;localStorage.setItem('snowflake-beta-theme',next);drawGlobe();});
function openFeedback(context=''){document.getElementById('feedbackContext').value=context;document.getElementById('feedbackBack').classList.add('open');}
function closeFeedback(){document.getElementById('feedbackBack').classList.remove('open');}function openLauncher(){document.getElementById('launcherBack').classList.add('open');}function closeLauncher(){document.getElementById('launcherBack').classList.remove('open');}function go(id){closeLauncher();location.hash=id;}window.openFeedback=openFeedback;window.closeFeedback=closeFeedback;window.openLauncher=openLauncher;window.closeLauncher=closeLauncher;window.go=go;
document.querySelectorAll('#rating button').forEach(button=>button.addEventListener('click',()=>{state.rating=Number(button.dataset.v);document.querySelectorAll('#rating button').forEach(c=>c.classList.toggle('on',Number(c.dataset.v)<=state.rating));}));
document.getElementById('feedbackForm')?.addEventListener('submit',async event=>{event.preventDefault();const status=document.getElementById('feedbackStatus'),fd=new FormData(event.currentTarget);const payload={rating:state.rating||null,area:fd.get('area'),message:String(fd.get('message')||'').slice(0,3000),email:String(fd.get('email')||'').slice(0,320),context:fd.get('context'),route:location.hash||'#home',theme:document.documentElement.dataset.theme,viewport:`${innerWidth}x${innerHeight}`,created_at:new Date().toISOString()};status.textContent='Sending…';try{const response=await fetch('/api/feedback',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});if(!response.ok)throw new Error();status.textContent='Thank you — feedback received.';event.currentTarget.reset();state.rating=0;document.querySelectorAll('#rating button').forEach(b=>b.classList.remove('on'));}catch{const rows=JSON.parse(localStorage.getItem('snowflake-beta-feedback')||'[]');rows.push(payload);localStorage.setItem('snowflake-beta-feedback',JSON.stringify(rows.slice(-50)));status.textContent='Saved on this device. Please try again when online.';}});

const DEG=Math.PI/180,WORLD_GEOMETRY_URL='./world-major-land.geojson',ROTATION_PERIOD_MS=56000,AUTO_DEGREES_PER_MS=360/ROTATION_PERIOD_MS,canvas=document.getElementById('globe'),ctx=canvas?.getContext('2d');let globePolygons=[],globeLandDots=[],globeCenterLon=-24,globeCenterLat=12,globeSize=440,globeDpr=Math.min(window.devicePixelRatio||1,2),globeDragging=false,globePointerId=null,globeLastX=0,globeLastY=0,globeResumeAfter=0,globeLastFrame=performance.now();
function css(name,fallback){return getComputedStyle(document.documentElement).getPropertyValue(name).trim()||fallback;}function projectPoint(latDeg,lonDeg,radius,center){const lat=latDeg*DEG,lat0=globeCenterLat*DEG,delta=(lonDeg-globeCenterLon)*DEG,sinLat=Math.sin(lat),cosLat=Math.cos(lat),sin0=Math.sin(lat0),cos0=Math.cos(lat0),depth=sin0*sinLat+cos0*cosLat*Math.cos(delta);return{x:center+radius*cosLat*Math.sin(delta),y:center-radius*(cos0*sinLat-sin0*cosLat*Math.cos(delta)),depth,visible:depth>0};}
function polygonsFromGeometry(geometry){if(!geometry)return[];const raw=geometry.type==='Polygon'?[geometry.coordinates||[]]:geometry.type==='MultiPolygon'?geometry.coordinates||[]:[];return raw.map(rings=>{const outer=rings[0]||[],lons=outer.map(p=>p[0]),lats=outer.map(p=>p[1]);return{rings,minLon:Math.min(...lons),maxLon:Math.max(...lons),minLat:Math.min(...lats),maxLat:Math.max(...lats)};}).filter(p=>p.rings[0]?.length>2);}
function pointInRing(lon,lat,ring){let inside=false;for(let i=0,j=ring.length-1;i<ring.length;j=i++){const xi=ring[i][0],yi=ring[i][1],xj=ring[j][0],yj=ring[j][1],crosses=((yi>lat)!==(yj>lat))&&(lon<((xj-xi)*(lat-yi))/((yj-yi)||1e-12)+xi);if(crosses)inside=!inside;}return inside;}
function isLand(lon,lat,polygons){for(const p of polygons){if(lat<p.minLat||lat>p.maxLat||lon<p.minLon||lon>p.maxLon)continue;if(!pointInRing(lon,lat,p.rings[0]))continue;let hole=false;for(let h=1;h<p.rings.length;h++){if(pointInRing(lon,lat,p.rings[h])){hole=true;break;}}if(!hole)return true;}return false;}
function buildLandDots(polygons){const dots=[];for(let lat=-79;lat<=82;lat+=2.75){const step=2.75/Math.max(.72,Math.cos(lat*DEG));for(let lon=-180;lon<180;lon+=step)if(isLand(lon,lat,polygons))dots.push({lat,lon});}return dots;}
function colorMix(hex,alpha){if(!hex.startsWith('#'))return hex;const h=hex.slice(1),n=h.length===3?h.split('').map(c=>c+c).join(''):h,v=Number.parseInt(n,16);return`rgba(${(v>>16)&255},${(v>>8)&255},${v&255},${alpha})`;}
function drawProjectedLine(points,radius,center,strokeStyle,lineWidth=1){let segment=[];const flush=()=>{if(segment.length>=2){ctx.beginPath();ctx.moveTo(segment[0].x,segment[0].y);for(let i=1;i<segment.length;i++)ctx.lineTo(segment[i].x,segment[i].y);ctx.strokeStyle=strokeStyle;ctx.lineWidth=lineWidth;ctx.stroke();}segment=[];};for(const coord of points){const p=projectPoint(coord[1],coord[0],radius,center);if(p.visible)segment.push(p);else flush();}flush();}
function drawGraticule(radius,center){const grid=colorMix(css('--line','#233b57'),.42);for(let lat=-60;lat<=60;lat+=30){const pts=[];for(let lon=-180;lon<=180;lon+=4)pts.push([lon,lat]);drawProjectedLine(pts,radius,center,grid,.6);}for(let lon=-180;lon<180;lon+=30){const pts=[];for(let lat=-88;lat<=88;lat+=4)pts.push([lon,lat]);drawProjectedLine(pts,radius,center,grid,.6);}}
function resizeGlobe(){if(!canvas||!ctx)return;const rect=canvas.getBoundingClientRect();globeSize=Math.max(250,Math.round(rect.width||440));globeDpr=Math.min(window.devicePixelRatio||1,2);canvas.width=Math.round(globeSize*globeDpr);canvas.height=Math.round(globeSize*globeDpr);ctx.setTransform(globeDpr,0,0,globeDpr,0,0);drawGlobe();}
function drawGlobe(){if(!canvas||!ctx)return;const center=globeSize/2,radius=globeSize*.455;ctx.clearRect(0,0,globeSize,globeSize);const shade=ctx.createRadialGradient(center-radius*.34,center-radius*.34,radius*.05,center,center,radius),light=document.documentElement.dataset.theme==='light';shade.addColorStop(0,light?'rgba(255,255,255,.92)':'rgba(88,231,255,.075)');shade.addColorStop(.72,light?'rgba(8,127,210,.035)':'rgba(36,153,255,.025)');shade.addColorStop(1,light?'rgba(8,31,51,.12)':'rgba(0,0,0,.32)');ctx.beginPath();ctx.arc(center,center,radius,0,Math.PI*2);ctx.fillStyle=shade;ctx.fill();ctx.save();ctx.beginPath();ctx.arc(center,center,radius-.5,0,Math.PI*2);ctx.clip();drawGraticule(radius,center);const landDot=light?'rgba(8,127,210,.60)':'rgba(88,231,255,.66)',baseDot=Math.max(.85,Math.min(1.5,globeSize/360));for(const dot of globeLandDots){const p=projectPoint(dot.lat,dot.lon,radius,center);if(!p.visible||p.depth<.015)continue;ctx.globalAlpha=Math.min(1,.24+p.depth*.84);ctx.fillStyle=landDot;ctx.beginPath();ctx.arc(p.x,p.y,baseDot*(.74+p.depth*.34),0,Math.PI*2);ctx.fill();}ctx.globalAlpha=1;const coastline=light?'rgba(103,86,217,.24)':'rgba(139,124,255,.25)';for(const polygon of globePolygons)for(const ring of polygon.rings)drawProjectedLine(ring,radius,center,coastline,.48);ctx.restore();ctx.beginPath();ctx.arc(center,center,radius,0,Math.PI*2);ctx.strokeStyle=colorMix(css('--line','#233b57'),.75);ctx.lineWidth=.85;ctx.stroke();}
async function loadGlobeGeometry(){if(!canvas)return;try{const response=await fetch(WORLD_GEOMETRY_URL,{cache:'force-cache'});if(!response.ok)throw new Error();const world=await response.json();globePolygons=polygonsFromGeometry(world.geometry);globeLandDots=buildLandDots(globePolygons);drawGlobe();}catch(error){console.error('Unable to load world geometry',error);const label=document.querySelector('.globe-label');if(label)label.innerHTML='<i></i>World geometry unavailable';}}
function animateGlobe(now){const reduce=window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches===true,elapsed=Math.min(80,now-globeLastFrame);globeLastFrame=now;if(!reduce&&!document.hidden&&!globeDragging&&now>=globeResumeAfter){globeCenterLon=((globeCenterLon+elapsed*AUTO_DEGREES_PER_MS+540)%360)-180;drawGlobe();}requestAnimationFrame(animateGlobe);}
if(canvas){canvas.addEventListener('pointerdown',event=>{globeDragging=true;globePointerId=event.pointerId;globeLastX=event.clientX;globeLastY=event.clientY;globeResumeAfter=Infinity;canvas.setPointerCapture?.(globePointerId);});canvas.addEventListener('pointermove',event=>{if(!globeDragging||event.pointerId!==globePointerId)return;const dx=event.clientX-globeLastX,dy=event.clientY-globeLastY;globeCenterLon-=dx*.33;globeCenterLat=Math.max(-55,Math.min(55,globeCenterLat+dy*.20));globeLastX=event.clientX;globeLastY=event.clientY;drawGlobe();});const end=event=>{if(!globeDragging||(event.pointerId!=null&&event.pointerId!==globePointerId))return;globeDragging=false;globePointerId=null;globeResumeAfter=performance.now()+1800;};canvas.addEventListener('pointerup',end);canvas.addEventListener('pointercancel',end);new ResizeObserver(resizeGlobe).observe(canvas);resizeGlobe();loadGlobeGeometry();requestAnimationFrame(animateGlobe);}
