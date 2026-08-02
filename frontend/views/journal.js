export const VIEW_ID = "journal";

import { escapeHtml } from "../api.js?v=20260731-v21-editorial-replica";

const articles = [
  {
    id: "architecture-foundations",
    tag: "SnowPro Core · Architecture",
    title: "How Snowflake separates storage, compute, and services",
    summary: "A practical mental model for the three architectural layers and why independent scaling matters on the exam.",
    body: [
      ["The architecture in one sentence", "Snowflake stores data centrally, processes it through independent virtual warehouses, and coordinates the platform through cloud services. The separation is the reason multiple workloads can share governed data without sharing the same compute cluster."],
      ["Storage", "Database storage manages compressed, columnar micro-partitions in cloud object storage. Snowflake controls file layout, metadata, encryption, and optimization; users interact with logical tables rather than physical files."],
      ["Query processing", "Virtual warehouses provide compute. Each warehouse can start, stop, resize, and run independently. A reporting warehouse does not need to compete with an ELT warehouse for CPU and memory."],
      ["Cloud services", "Cloud services coordinate authentication, metadata, query parsing, optimization, access control, and transaction management. This layer connects governed storage to independent compute."],
    ],
  },
  {
    id: "rag-in-snowflake",
    tag: "Data + AI · Retrieval",
    title: "A production RAG path with Cortex Search",
    summary: "From document ingestion to grounded answers: chunking, retrieval scope, citations, evaluation, and access control.",
    body: [
      ["Start with retrieval quality", "A useful retrieval-augmented generation system begins with documents that have stable ownership, good metadata, and a defined access boundary. Model quality cannot rescue missing or poorly scoped evidence."],
      ["Chunk with structure", "Chunk around headings, concepts, and complete procedures instead of arbitrary character counts. Keep source identifiers, timestamps, course names, and certification domains attached to every chunk."],
      ["Retrieve inside the user's scope", "Filter by certification, course, lesson, role, and source permissions before ranking semantic matches. The answer should cite the retrieved material and clearly say when evidence is insufficient."],
      ["Evaluate the whole system", "Measure retrieval recall, citation correctness, groundedness, latency, and task completion. A polished answer without supporting evidence is a failure, not a success."],
    ],
  },
  {
    id: "warehouse-costs",
    tag: "Performance · Cost",
    title: "Virtual warehouses: the cost questions that matter",
    summary: "Auto-suspend, minimum billing, resizing, cache behavior, concurrency, and when another cluster is justified.",
    body: [
      ["Cost follows running compute", "Virtual warehouses consume credits while running. Auto-suspend reduces idle time, while auto-resume keeps the user workflow simple. Choose a suspension interval that reflects workload cadence rather than applying one value everywhere."],
      ["Size for elapsed work", "A larger warehouse costs more per unit of time but can finish suitable workloads faster. The right comparison is total credits and service-level outcome, not hourly rate alone."],
      ["Separate workloads deliberately", "Independent warehouses isolate performance and cost attribution. Use multi-cluster warehouses for concurrency pressure, not as a substitute for inefficient queries or poor workload design."],
      ["Observe before changing", "Use query history, warehouse load, queueing, and resource monitors to establish evidence. Cost tuning should be an operational loop, not a one-time configuration exercise."],
    ],
  },
];

export default async function mount(container, params = {}) {
  const selected = articles.find((item) => item.id === params.id);
  if (selected) {
    container.innerHTML = articlePage(selected);
    return;
  }
  container.innerHTML = `
    <div class="replica-page replica-enter">
      <section class="replica-page-heading compact-heading">
        <p class="replica-kicker">Journal</p>
        <h1>Articles &amp; study guides.</h1>
        <p>Focused explanations for Snowflake certification, data engineering, production AI, and architecture decisions.</p>
      </section>
      <section class="replica-journal-grid">
        ${articles.map((item, index) => `
          <a class="replica-article-card accent-${index + 1}" href="#/article?id=${encodeURIComponent(item.id)}">
            <span>${escapeHtml(item.tag)}</span>
            <h2>${escapeHtml(item.title)}</h2>
            <p>${escapeHtml(item.summary)}</p>
            <small>Study guide · 6 min ↗</small>
          </a>`).join("")}
      </section>
    </div>`;
}

function articlePage(article) {
  return `
    <article class="replica-article replica-enter">
      <a class="replica-back-link" href="#/journal">← Journal</a>
      <header><p class="replica-kicker">${escapeHtml(article.tag)}</p><h1>${escapeHtml(article.title)}</h1><p>${escapeHtml(article.summary)}</p></header>
      ${article.body.map(([title, copy]) => `<section><h2>${escapeHtml(title)}</h2><p>${escapeHtml(copy)}</p></section>`).join("")}
      <footer><span>Generated English study guide</span><a href="#/practice">Practise this topic →</a></footer>
    </article>`;
}

