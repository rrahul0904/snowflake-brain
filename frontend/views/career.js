export const VIEW_ID = "career";
import { escapeHtml } from "../api.js?v=20260714-v20-ai-academy";

const STORAGE_KEY = "snowflake-brain.career-curriculum.v1";

const sprint = [
  { id: "s1", week: 1, title: "Career evidence inventory", focus: "Translate 14+ years of platform, reliability, product-data, and leadership outcomes into role evidence.", deliverable: "Evidence map, gap matrix, and two leadership stories" },
  { id: "s2", week: 2, title: "AI product telemetry", focus: "Design consumer, enterprise, coding, API, model, token, latency, cost, and tool-use events.", deliverable: "Event taxonomy, contracts, and metric tree" },
  { id: "s3", week: 3, title: "Canonical product data", focus: "Build dbt facts, dimensions, semantic metrics, data tests, and freshness SLAs.", deliverable: "Tested marts with lineage and ownership" },
  { id: "s4", week: 4, title: "LLM application foundations", focus: "Implement a provider-neutral gateway, structured outputs, traces, and token budgets.", deliverable: "Gateway slice with tested fallback behavior" },
  { id: "s5", week: 5, title: "Governed analytics copilot", focus: "Connect trusted marts to retrieval, citations, and authorization-aware answers.", deliverable: "Copilot with a 30-question evaluation set" },
  { id: "s6", week: 6, title: "Evaluations and AI security", focus: "Create regression gates, judge rubrics, threat models, and adversarial tests.", deliverable: "Quality and security gates enforced in CI" },
  { id: "s7", week: 7, title: "Executive architecture narrative", focus: "Turn the system into a decision-ready roadmap, cost model, and technical workshop.", deliverable: "10-slide executive deck and architecture review" },
  { id: "s8", week: 8, title: "Application package", focus: "Package the résumé, LinkedIn, portfolio, demos, and interview evidence by role lane.", deliverable: "Application-ready evidence index" },
];

const months = [
  { id: "m1", month: 1, title: "ML, statistics, and experimentation", skills: ["Bias and variance", "Calibration", "Experiment design"], artifact: "Baseline model and experiment review", tone: "green" },
  { id: "m2", month: 2, title: "Deep learning and PyTorch", skills: ["Autograd", "Training loops", "Profiling"], artifact: "Tested training harness", tone: "cyan" },
  { id: "m3", month: 3, title: "NLP, tokenization, and transformers", skills: ["Tokenizers", "Attention", "Decoding"], artifact: "Tokenizer and small transformer", tone: "violet" },
  { id: "m4", month: 4, title: "Training, post-training, and inference", skills: ["SFT and DPO", "LoRA", "Quantization"], artifact: "Quality-latency-cost benchmark", tone: "amber" },
  { id: "m5", month: 5, title: "RAG, retrieval, and context engineering", skills: ["Hybrid search", "Reranking", "GraphRAG"], artifact: "Retrieval evaluation report", tone: "green" },
  { id: "m6", month: 6, title: "Agents, deep research, MCP, and n8n", skills: ["Tool design", "MCP security", "Human approval"], artifact: "Secure enterprise agent slice", tone: "cyan" },
  { id: "m7", month: 7, title: "Evaluations, LLMOps, security, and governance", skills: ["Eval CI", "Tracing", "NIST and OWASP"], artifact: "Release gate and incident exercise", tone: "violet" },
  { id: "m8", month: 8, title: "Multimodal, RL, and interpretability", skills: ["Multimodal eval", "Policy learning", "Circuits"], artifact: "Three technical survey briefs", tone: "amber" },
  { id: "m9", month: 9, title: "Paper reproduction and integrated capstone", skills: ["Hypotheses", "Ablations", "Reproducibility"], artifact: "Reproduction report and capstone", tone: "green" },
];

const projects = [
  { id: "P1", title: "AI Product Data and Intelligence Platform", label: "Anchor-role evidence", detail: "Canonical product events, AI telemetry, dbt marts, semantic metrics, quality SLAs, dashboards, and a governed analytics copilot.", metric: "Trust + adoption" },
  { id: "P2", title: "Governed Enterprise Agent Platform", label: "Production AI evidence", detail: "Model gateway, provider routing, RAG, MCP tools, authorization, human approval, tracing, evaluations, cost, and reliability controls.", metric: "Quality + safety" },
  { id: "P3", title: "Language Model Research Laboratory", label: "Research-engineering evidence", detail: "Tokenizer, small transformer, pre-training, SFT, LoRA, quantization, profiling, paper reproduction, and ablation studies.", metric: "Rigor + systems" },
  { id: "P4", title: "Forward-Deployed AI Transformation", label: "Customer delivery evidence", detail: "Discovery, value hypothesis, prototype, evaluation, security review, target architecture, cost model, rollout, and executive workshop.", metric: "Value + adoption" },
];

const depth = [
  { label: "Expert depth", level: "5", items: "Data engineering · Product data · Reliability · Governance · Leadership" },
  { label: "Production depth", level: "4–5", items: "LLM apps · RAG · Evaluations · AI security · LLMOps" },
  { label: "Strong execution", level: "4", items: "Agents · MCP · Token/context engineering · Forward-deployed delivery" },
  { label: "Working literacy", level: "2–3", items: "Training · Multimodal · Reinforcement learning · Interpretability" },
];

let state = loadState();

export default async function mount(container) {
  render(container);
  bind(container);
}

function loadState() {
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
    return { completed: parsed.completed || {}, activeMonth: parsed.activeMonth || "m1" };
  } catch {
    return { completed: {}, activeMonth: "m1" };
  }
}

function persist() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function completion() {
  const completed = sprint.filter((item) => state.completed[item.id]).length;
  return { completed, pct: Math.round((completed / sprint.length) * 100) };
}

function render(container) {
  const progress = completion();
  const activeMonth = months.find((item) => item.id === state.activeMonth) || months[0];
  container.innerHTML = `
    <section class="page-shell career-page">
      <section class="career-hero">
        <div class="career-hero-copy">
          <div class="career-kicker"><span>DATA + AI LEADERSHIP</span><b>36-week evidence program</b></div>
          <h1>Turn senior data leadership into credible AI platform leadership.</h1>
          <div class="career-hero-actions">
            <a class="primary-btn xl" href="#/academy">Open AI Academy</a>
            <button class="secondary-btn xl" data-scroll="sprint">View the 8-week sprint</button>
            <a class="secondary-btn xl" href="/career-docs/README.md" target="_blank" rel="noreferrer">Open full curriculum</a>
          </div>
        </div>
        <div class="career-score-card">
          <div class="career-ring" style="--career-score:${progress.pct}"><strong>${progress.pct}%</strong><span>sprint</span></div>
          <div><span>Application readiness</span><strong>${progress.completed} of 8 weeks evidenced</strong><small>Progress is stored locally in this browser.</small></div>
        </div>
      </section>

      <section class="career-stat-strip" aria-label="Curriculum summary">
        ${stat("12", "hours / week", "Default sustainable cadence")}
        ${stat("8", "week sprint", "Immediate role readiness")}
        ${stat("9", "month roadmap", "Production and research depth")}
        ${stat("4", "portfolio systems", "Connected evidence, not demos")}
      </section>

      <section class="career-layout" id="sprint">
        <article class="panel career-sprint-panel">
          <div class="panel-header career-section-header">
            <div><p class="eyebrow">Application readiness</p><h2>Your first eight weeks</h2><p>Complete evidence, not content. Each week ends with a working artifact and a decision-ready explanation.</p></div>
            <span class="career-progress-label">${progress.completed}/8 complete</span>
          </div>
          <div class="career-sprint-list">
            ${sprint.map((item) => sprintItem(item)).join("")}
          </div>
        </article>

        <aside class="career-side-stack">
          <article class="panel career-position-card">
            <p class="eyebrow">Target position</p>
            <h2>Principal / Director Data + AI Platform Leader</h2>
            <p>Anchor role: Anthropic Data Engineering Manager, Product.</p>
            <div class="career-role-tags"><span>Product data</span><span>AI platforms</span><span>Applied AI</span><span>Forward deployed</span></div>
          </article>
          <article class="panel career-rule-card">
            <p class="eyebrow">Evidence rule</p>
            <blockquote>Every topic must produce code, a benchmark, an ADR, a review, a presentation, or an interview story.</blockquote>
            <a href="/career-docs/15-progress-tracker.md" target="_blank" rel="noreferrer">Open 36-week tracker →</a>
          </article>
        </aside>
      </section>

      <section class="panel career-roadmap-panel">
        <div class="panel-header career-section-header"><div><p class="eyebrow">Nine-month mastery roadmap</p><h2>Build breadth in sequence, depth by role</h2></div><a href="/career-docs/04-nine-month-ai-mastery-roadmap.md" target="_blank" rel="noreferrer">Detailed roadmap</a></div>
        <div class="career-month-tabs" role="tablist">
          ${months.map((item) => `<button class="${item.id === activeMonth.id ? "active" : ""}" data-month="${item.id}" role="tab" aria-selected="${item.id === activeMonth.id}"><span>${String(item.month).padStart(2, "0")}</span>${escapeHtml(item.title)}</button>`).join("")}
        </div>
        <div class="career-month-detail ${activeMonth.tone}">
          <div><p class="eyebrow">Month ${activeMonth.month}</p><h3>${escapeHtml(activeMonth.title)}</h3><div class="career-skill-pills">${activeMonth.skills.map((skill) => `<span>${escapeHtml(skill)}</span>`).join("")}</div></div>
          <div class="career-artifact"><span>Exit artifact</span><strong>${escapeHtml(activeMonth.artifact)}</strong><small>Advance only after code, measurement, an ADR, failure analysis, and a concise presentation.</small></div>
        </div>
      </section>

      <section class="career-two-column">
        <article class="panel">
          <div class="panel-header career-section-header"><div><p class="eyebrow">T-shaped skill strategy</p><h2>Where to lead versus where to learn</h2></div><a href="/career-docs/02-skill-matrix.md" target="_blank" rel="noreferrer">Full matrix</a></div>
          <div class="career-depth-list">${depth.map(depthItem).join("")}</div>
        </article>
        <article class="panel career-week-card">
          <p class="eyebrow">12-hour operating cadence</p><h2>A week that produces evidence</h2>
          <div class="career-time-grid">
            ${time("3h", "Theory", "Official docs")}${time("5h", "Build", "Implementation")}${time("2h", "Portfolio", "Writing + ADRs")}${time("1h", "Research", "Primary paper")}${time("1h", "Interview", "Communication")}
          </div>
          <a href="/career-docs/05-weekly-study-plan.md" target="_blank" rel="noreferrer">Open weekly operating plan →</a>
        </article>
      </section>

      <section class="career-project-section">
        <div class="career-section-header"><div><p class="eyebrow">Connected portfolio</p><h2>Four systems that prove the full position</h2><p>The projects share telemetry, controls, research assets, and customer evidence.</p></div><a href="/career-docs/07-portfolio-projects.md" target="_blank" rel="noreferrer">Project specifications</a></div>
        <div class="career-project-grid">${projects.map(projectCard).join("")}</div>
      </section>

      <section class="career-footer-cta">
        <div><p class="eyebrow">Start with leverage</p><h2>Do not begin with another course.</h2><p>Begin by inventorying the leadership and platform evidence you already have. Study only the gaps that block the next artifact or interview.</p></div>
        <div><a class="primary-btn xl" href="/career-docs/03-eight-week-role-readiness-sprint.md" target="_blank" rel="noreferrer">Open Week 1 brief</a><a class="secondary-btn xl" href="/career-docs/skill-assessment.csv" target="_blank" rel="noreferrer">Open skill assessment</a></div>
      </section>
    </section>`;
}

function stat(value, label, detail) {
  return `<article><strong>${value}</strong><span>${label}</span><small>${detail}</small></article>`;
}

function sprintItem(item) {
  const checked = Boolean(state.completed[item.id]);
  return `<label class="career-sprint-item ${checked ? "done" : ""}">
    <input type="checkbox" data-week="${item.id}" ${checked ? "checked" : ""} />
    <span class="career-check" aria-hidden="true">${checked ? "✓" : ""}</span>
    <span class="career-week-number">W${String(item.week).padStart(2, "0")}</span>
    <span class="career-sprint-copy"><strong>${escapeHtml(item.title)}</strong><small>${escapeHtml(item.focus)}</small><em>${escapeHtml(item.deliverable)}</em></span>
  </label>`;
}

function depthItem(item) {
  return `<div class="career-depth-row"><span><strong>${escapeHtml(item.label)}</strong><small>${escapeHtml(item.items)}</small></span><b>Level ${escapeHtml(item.level)}</b></div>`;
}

function time(hours, label, detail) {
  return `<div><strong>${hours}</strong><span>${label}</span><small>${detail}</small></div>`;
}

function projectCard(item) {
  return `<article class="career-project-card"><div><span>${item.id}</span><small>${escapeHtml(item.label)}</small></div><h3>${escapeHtml(item.title)}</h3><p>${escapeHtml(item.detail)}</p><footer><span>Primary signal</span><strong>${escapeHtml(item.metric)}</strong></footer></article>`;
}

function bind(container) {
  container.querySelectorAll("[data-week]").forEach((input) => {
    input.addEventListener("change", () => {
      state.completed[input.dataset.week] = input.checked;
      persist();
      render(container);
      bind(container);
      container.querySelector("#sprint")?.scrollIntoView({ block: "start" });
    });
  });
  container.querySelectorAll("[data-month]").forEach((button) => {
    button.addEventListener("click", () => {
      state.activeMonth = button.dataset.month;
      persist();
      render(container);
      bind(container);
      container.querySelector(".career-roadmap-panel")?.scrollIntoView({ block: "center" });
    });
  });
  container.querySelector("[data-scroll='sprint']")?.addEventListener("click", () => container.querySelector("#sprint")?.scrollIntoView({ behavior: "smooth" }));
}
