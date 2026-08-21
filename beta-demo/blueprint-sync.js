// Keep the public beta aligned with the canonical COF-C03 blueprint used by the full platform.
// Loaded immediately after app.js so it can correct the demo controller's mutable data structures
// without duplicating the complete production runtime.

const CANONICAL_GUIDE = [
  {id:'Architecture', code:'D1', weight:31, title:'Snowflake AI Data Cloud Features and Architecture', tasks:[
    ['1.1','Outline key Snowflake AI Data Cloud features','Recognize the platform capabilities and design principles that distinguish Snowflake across data, applications, AI, collaboration, and governance.','Exam cue: do not reduce Snowflake to only a traditional data warehouse; identify the platform capability the scenario is testing.'],
    ['1.2','Outline Snowflake architecture','Explain the storage, compute, and cloud services layers and how their separation affects concurrency, scaling, management, and cost.','Exam cue: virtual warehouses provide compute; they do not create separate persistent copies of table data.'],
    ['1.3','Outline Snowflake interfaces and client tools','Choose among Snowsight, Snowflake CLI, SnowSQL, drivers, connectors, APIs, and developer tooling for a given access pattern.','Exam cue: distinguish a client driver from an ingestion connector and Snowflake CLI from legacy SnowSQL usage.'],
    ['1.4','Outline Snowflake editions','Differentiate Standard, Enterprise, Business Critical, and Virtual Private Snowflake by feature availability and workload requirements.','Exam cue: edition choice is driven by required capabilities and controls, not by warehouse size.'],
    ['1.5','Explain Snowflake storage concepts and object types','Understand micro-partitions, pruning, clustering, table types, Iceberg tables, dynamic tables, hybrid tables, external tables, and view types.','Exam cue: micro-partitions are Snowflake-managed; do not treat them like user-managed table partitions.'],
    ['1.6','Explain AI/ML and application-development features','Recognize Snowflake Notebooks, Streamlit, Snowpark, Cortex AI functions, Cortex Search, Cortex Analyst, Document AI, and Snowflake ML use cases.','Exam cue: match the AI/application feature to the workload rather than treating all Cortex capabilities as interchangeable.']
  ]},
  {id:'Governance', code:'D2', weight:20, title:'Account Management and Data Governance', tasks:[
    ['2.1','Explain Snowflake security model and access principles','Apply RBAC, MFA, SSO, OAuth, key-pair authentication, authentication/network policies, and security posture controls.','Exam cue: separate authentication, network restrictions, and role-based object authorization.'],
    ['2.2','Define and apply Snowflake data governance','Use masking policies, row access policies, tags, classification, lineage, and governance controls to protect and understand data.','Exam cue: masking changes values presented; row access policies filter rows; tags alone do not enforce protection.'],
    ['2.3','Explain monitoring and cost management','Use resource monitors, budgets, ACCOUNT_USAGE, warehouse metering, and cost-attribution concepts.','Exam cue: resource monitors govern consumption; they are not SQL-optimization tools.']
  ]},
  {id:'Loading', code:'D3', weight:18, title:'Data Loading, Unloading, and Connectivity', tasks:[
    ['3.1','Perform data loading and unloading','Use stages, file formats, COPY INTO, load validation, error handling, directory tables, and unload patterns for file-based data movement.','Exam cue: distinguish COPY INTO a table from COPY INTO a location, and a stage from a file format.'],
    ['3.2','Perform automated data ingestion','Choose Snowpipe, Snowpipe Streaming, streams, tasks, and dynamic tables appropriately for continuous ingestion and incremental processing.','Exam cue: Snowpipe Streaming is not staged-file ingestion; streams track change while tasks execute work.'],
    ['3.3','Identify Snowflake connectors and integrations','Recognize drivers, Kafka/Spark connectors, storage integrations, API integrations, external access integrations, and related connectivity boundaries.','Exam cue: prefer managed integrations over embedding long-lived cloud credentials.']
  ]},
  {id:'Performance', code:'D4', weight:21, title:'Performance Optimization, Querying, and Transformation', tasks:[
    ['4.1','Explain query performance concepts','Distinguish caching layers, micro-partition pruning, clustering, Query Profile signals, search optimization, and Query Acceleration Service.','Exam cue: diagnose the bottleneck before changing warehouse size; result cache and warehouse cache are not the same.'],
    ['4.2','Use warehouse sizing and scaling','Choose scale-up versus scale-out, configure auto-suspend/resume, use multi-cluster warehouses, and balance latency, concurrency, and credits.','Exam cue: scale out primarily for concurrency; do not assume multi-cluster speeds up one CPU-bound query.'],
    ['4.3','Use Snowflake query and transformation features','Apply QUALIFY, window functions, PIVOT/UNPIVOT, MERGE, UDFs, stored procedures, Snowpark, and SQL transformation patterns.','Exam cue: QUALIFY is designed for filtering window-function results; UDFs and stored procedures solve different problems.'],
    ['4.4','Use semi-structured and unstructured data','Work with VARIANT, OBJECT, ARRAY, JSON pathing, FLATTEN, staged unstructured files, directory tables, file URLs, and Document AI.','Exam cue: FLATTEN is a table function; file metadata is not the same as file contents.']
  ]},
  {id:'Collaboration', code:'D5', weight:10, title:'Data Collaboration', tasks:[
    ['5.1','Explain Time Travel and Fail-safe','Use AT/BEFORE and UNDROP during retention, understand retention differences, and distinguish user-accessible Time Travel from Snowflake-managed Fail-safe.','Exam cue: Fail-safe is not a normal historical-query feature; recovery guarantees differ by object type.'],
    ['5.2','Explain secure data sharing and collaboration','Understand direct shares, listings, reader accounts, Marketplace, Native Apps, and Data Clean Rooms as collaboration patterns without unnecessary copies.','Exam cue: secure sharing does not create a traditional consumer-side copy of provider data.'],
    ['5.3','Explain zero-copy cloning and replication','Use zero-copy cloning for fast writable copies and distinguish it from replication/failover across accounts or regions.','Exam cue: cloning is not cross-region disaster recovery, and diverging clones can consume additional storage.']
  ]}
];

// Correct demo-question domain evidence to the canonical five-domain blueprint.
if (typeof QUESTIONS !== 'undefined') {
  Object.assign(QUESTIONS[7], {d:'D5 · Collaboration', domain:'Collaboration'}); // Time Travel
  Object.assign(QUESTIONS[16], {d:'D3 · Loading', domain:'Loading'}); // Streams
  Object.assign(QUESTIONS[17], {d:'D3 · Loading', domain:'Loading'}); // Tasks
}

if (typeof GUIDE !== 'undefined') {
  GUIDE.splice(0, GUIDE.length, ...CANONICAL_GUIDE);
}

// Avoid double-counting a just-completed practice run after it has already been
// persisted into practiceHistory.
if (typeof aggregateStats === 'function' && typeof state !== 'undefined') {
  aggregateStats = function aggregateStatsCanonical() {
    const all=[];
    state.practiceHistory.forEach(h=>{
      QUESTIONS.forEach((_,i)=>{
        if(h.answers?.[i]!==null && h.answers?.[i]!==undefined) all.push([i,h.answers[i]]);
      });
    });
    const latest=state.practiceHistory[state.practiceHistory.length-1];
    const currentComplete=state.answers.every(a=>a!==null);
    const currentAlreadySaved=currentComplete && latest && JSON.stringify(latest.answers)===JSON.stringify(state.answers);
    if(!currentAlreadySaved){
      state.answers.forEach((a,i)=>{ if(a!==null) all.push([i,a]); });
    }
    if(state.mock?.submitted){
      state.mock.indices.forEach((qi,i)=>all.push([qi,state.mock.answers[i]]));
    }
    const stats={
      Architecture:{correct:0,total:0,weight:31},
      Governance:{correct:0,total:0,weight:20},
      Loading:{correct:0,total:0,weight:18},
      Performance:{correct:0,total:0,weight:21},
      Collaboration:{correct:0,total:0,weight:10}
    };
    all.forEach(([qi,a])=>{
      const q=QUESTIONS[qi];
      stats[q.domain].total++;
      if(a===q.c) stats[q.domain].correct++;
    });
    return stats;
  };
}

// Re-render the already-initialized beta views using the canonical data.
const guideSection=document.getElementById('guide');
if(guideSection){
  guideSection.dataset.functional='';
  if(typeof renderGuide==='function') renderGuide();
}
if(typeof renderQ==='function') renderQ();
if(typeof renderMock==='function') renderMock();
if(typeof renderAdaptive==='function') renderAdaptive();
