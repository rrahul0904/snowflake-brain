export const VIEW_ID = "journal";

import { escapeHtml } from "../api.js?v=20260812-v24-cert-native";
import { activeTrack } from "../ui.js?v=20260731-v21-editorial-replica";

const articles = [
  {
    id: "snowpro-core-c03-guide",
    tag: "SnowPro Core · COF-C03",
    title: "How to prepare for SnowPro Core COF-C03",
    summary: "Use the exam blueprint as the curriculum, then prove every domain with written lessons, targeted drills, build exercises, and timed mocks.",
    skill: "ai-data-cloud-features",
    body: [
      ["Start with the blueprint", "Treat the five weighted domains and nineteen task statements as the study contract. Learn task by task instead of collecting unrelated Snowflake facts."],
      ["Build evidence, not page views", "A written lesson establishes the concept. Mapped practice, build exercises, and timed mocks show whether the concept survives under exam pressure."],
      ["Prioritize weak domains", "Use the diagnostic to establish a baseline, then drill current-task weaknesses and repeated misses before spending time on already-strong areas."],
      ["Finish with exam behavior", "Use timed mocks to validate pacing, navigation, review discipline, and score consistency across the blueprint."],
    ],
  },
  {
    id: "snowflake-access-control",
    tag: "Domain 2 · Security",
    title: "Snowflake access control: the exam distinctions that matter",
    summary: "Separate role hierarchy, ownership, authentication, network controls, and least privilege instead of treating security as one feature.",
    skill: "security-access-principles",
    body: [
      ["Think in roles", "Privileges are granted to roles and roles are granted through a hierarchy. Keep the requested authority narrow and reusable."],
      ["Ownership is different", "OWNERSHIP controls an object and its grant management. It is not interchangeable with ordinary object privileges such as SELECT or USAGE."],
      ["Authentication is another layer", "SSO, MFA, key-pair authentication, authentication policies, and network policies solve identity and connection-control requirements rather than object authorization."],
      ["Least privilege wins", "When multiple options technically work, identify the choice that satisfies the requirement without unnecessary administrative authority."],
    ],
  },
  {
    id: "warehouse-sizing-scaling",
    tag: "Domain 4 · Performance",
    title: "Scale up vs scale out: the warehouse decision rule",
    summary: "Separate single-query performance, concurrency pressure, and idle spend before changing compute.",
    skill: "warehouse-sizing-scaling",
    body: [
      ["Scale up", "Resize a warehouse when an individual workload needs more compute capacity."],
      ["Scale out", "Use multi-cluster capacity when concurrency creates queueing while individual queries are otherwise healthy."],
      ["Control idle cost", "AUTO_SUSPEND and AUTO_RESUME address idle compute, which is a different problem from query speed or concurrency."],
      ["Measure the right symptom", "Read queueing, spilling, pruning, and query profile evidence before assuming a larger warehouse is the answer."],
    ],
  },
  {
    id: "query-performance",
    tag: "Domain 4 · Query Performance",
    title: "Result reuse, warehouse cache, pruning, and Query Profile",
    summary: "The exam often tests which performance mechanism solves which symptom.",
    skill: "query-performance-optimization",
    body: [
      ["Persisted results", "Eligible repeated queries can reuse persisted results without re-executing the full plan."],
      ["Warehouse-local cache", "A running warehouse can retain locally cached data. Suspending the warehouse discards that local cache."],
      ["Pruning", "Micro-partition metadata lets Snowflake avoid scanning irrelevant partitions when predicates are selective."],
      ["Use Query Profile", "Spilling, poor pruning, expensive operators, and queueing point to different remedies; diagnose before resizing."],
    ],
  },
  {
    id: "copy-stage-file-format",
    tag: "Domain 3 · Data Loading",
    title: "Stage vs file format vs COPY INTO",
    summary: "Three responsibilities: location, parsing rules, and load execution.",
    skill: "bulk-load-unload",
    body: [
      ["Stage", "A stage identifies a location for files, either Snowflake-managed or external cloud storage."],
      ["File format", "A file format stores reusable parsing or serialization options. It does not hold the files themselves."],
      ["COPY INTO", "COPY INTO loads staged data into tables or unloads query/table results to files."],
      ["Exam shortcut", "Location suggests stage; parsing suggests file format; movement between staged files and tables suggests COPY INTO."],
    ],
  },
  {
    id: "automated-ingestion",
    tag: "Domain 3 · Automated Ingestion",
    title: "Snowpipe, Snowpipe Streaming, streams, tasks, and dynamic tables",
    summary: "Choose the automation mechanism from the ingestion and transformation requirement, not from a familiar product name.",
    skill: "automated-ingestion-pipelines",
    body: [
      ["Snowpipe", "Snowpipe automates file ingestion using Snowflake-managed serverless compute."],
      ["Snowpipe Streaming", "Streaming ingestion addresses low-latency row-oriented ingestion without staged files as the central unit."],
      ["Streams and tasks", "Streams expose change data while tasks schedule or trigger processing logic."],
      ["Dynamic tables", "Dynamic tables express a target query and freshness objective so Snowflake manages refresh work."],
    ],
  },
  {
    id: "semi-structured",
    tag: "Domain 4 · Semi-Structured",
    title: "VARIANT, pathing, and FLATTEN",
    summary: "A compact mental model for questions that combine nested storage, navigation, casting, and row expansion.",
    skill: "semi-unstructured-data",
    body: [
      ["Store flexibly", "VARIANT stores semi-structured values such as parsed JSON while preserving nested structure."],
      ["Navigate", "Path expressions retrieve nested fields and may require casts when values participate in typed SQL operations."],
      ["Expand", "FLATTEN turns nested collections into rows and is commonly paired with LATERAL."],
      ["Keep unstructured data separate", "Directory tables and file-access functions address files and unstructured objects rather than JSON traversal inside VARIANT."],
    ],
  },
  {
    id: "time-travel-failsafe",
    tag: "Domain 5 · Protection",
    title: "Time Travel and Fail-safe are not the same thing",
    summary: "Historical access and Snowflake-managed recovery solve different recovery requirements.",
    skill: "time-travel-failsafe",
    body: [
      ["Time Travel", "Time Travel provides user-accessible historical querying and recovery within configured retention."],
      ["UNDROP", "Eligible dropped objects can be restored while their Time Travel retention makes them recoverable."],
      ["Fail-safe", "Fail-safe is a separate Snowflake-managed recovery period for eligible permanent data; it is not a longer queryable Time Travel window."],
      ["Table type matters", "Permanent, transient, and temporary tables have different retention and Fail-safe characteristics."],
    ],
  },
  {
    id: "secure-sharing",
    tag: "Domain 5 · Collaboration",
    title: "Secure sharing, listings, Marketplace, and reader accounts",
    summary: "Choose the collaboration mechanism by provider/consumer relationship and access model.",
    skill: "secure-sharing-collaboration",
    body: [
      ["Secure sharing", "Direct secure sharing gives consumers governed access without copying provider data into a separate export pipeline."],
      ["Listings", "Listings package data products for discovery and controlled access across collaboration scenarios."],
      ["Reader accounts", "Reader accounts support consumers that do not maintain their own Snowflake account."],
      ["Govern the shared product", "Sharing answers distribution. Masking and row access policies still control what a consumer is allowed to see."],
    ],
  },
  {
    id: "cloning-replication",
    tag: "Domain 5 · Cloning & Replication",
    title: "Zero-copy cloning vs replication and failover",
    summary: "A metadata-based writable copy and a cross-account continuity mechanism are different architectural tools.",
    skill: "cloning-replication",
    body: [
      ["Zero-copy clone", "A clone initially references existing micro-partitions, so creating it does not copy all table data."],
      ["Divergence", "Source and clone become independent; changed data creates new storage as they diverge."],
      ["Replication", "Replication moves supported account/database state across accounts or regions for continuity requirements."],
      ["Failover", "Failover/failback is about business continuity, not simply creating a local development copy."],
    ],
  },
];

export default async function mount(container, params = {}) {
  const trackId = params.track_id || activeTrack();
  const selected = articles.find((item) => item.id === params.id);
  if (selected) {
    container.innerHTML = articlePage(selected, trackId);
    return;
  }
  container.innerHTML = `<div class="replica-page replica-enter"><section class="replica-page-heading compact-heading"><p class="replica-kicker">Snowflake Certification Blog</p><h1>Exam guides &amp; technical deep dives.</h1><p>Original Snowflake explanations organized around the current COF-C03 task blueprint.</p></section><section class="replica-journal-grid">${articles.map((item, index) => `<a class="replica-article-card accent-${(index % 3) + 1}" href="#/article?id=${encodeURIComponent(item.id)}&track_id=${encodeURIComponent(trackId)}"><span>${escapeHtml(item.tag)}</span><h2>${escapeHtml(item.title)}</h2><p>${escapeHtml(item.summary)}</p><small>Certification guide · Read →</small></a>`).join("")}</section></div>`;
}

function articlePage(article, trackId) {
  const selectedTrack = trackId || "snowpro-core";
  return `<article class="replica-article replica-enter"><a class="replica-back-link" href="#/journal?track_id=${encodeURIComponent(selectedTrack)}">← Blog</a><header><p class="replica-kicker">${escapeHtml(article.tag)}</p><h1>${escapeHtml(article.title)}</h1><p>${escapeHtml(article.summary)}</p></header>${article.body.map(([title, copy]) => `<section><h2>${escapeHtml(title)}</h2><p>${escapeHtml(copy)}</p></section>`).join("")}<footer><span>Snowflake certification editorial</span><a href="#/skill?track_id=snowpro-core&skill_id=${encodeURIComponent(article.skill)}">Study the linked task →</a></footer></article>`;
}
