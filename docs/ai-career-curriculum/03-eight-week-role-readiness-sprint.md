# Eight-Week Role-Readiness Sprint

Purpose: create credible application evidence immediately while deeper AI study continues. Default load: 12 hours/week.

| Week | Objective and topics | Deliverables | Portfolio milestone | Leadership/interview work | Completion criteria |
|---:|---|---|---|---|---|
| 1 | Evidence inventory; role scorecard; product-data/AI landscape | Evidence map, gap matrix, target-role résumé skeleton | P1/P2 repo briefs and ADR template | Draft stories: platform scale, incident leadership | 12 quantified outcomes; gaps mapped to artifacts |
| 2 | Product event and AI telemetry architecture | Event taxonomy, contracts, metric tree, token/latency/cost schema | P1 ingestion skeleton and architecture diagram | Product-metrics interview: activation/retention/cost | Contracts versioned; replay/idempotency tested |
| 3 | dbt and canonical product-data models | Facts/dimensions, tests, freshness SLAs, semantic metrics | P1 marts and CI checks | Story: cross-functional metric alignment | Tests pass; lineage and owner documented |
| 4 | Claude/OpenAI app foundations; token/context engineering | Provider-neutral gateway, structured outputs, traces, token budget | P2 model gateway slice | AI system-design walkthrough | Two providers or mock adapters; fallbacks tested |
| 5 | Governed analytics copilot; RAG | Retrieval pipeline, citations, RBAC filters, answer contract | P1 analytics copilot connected to marts | Story: governance without blocking delivery | 30-question eval set; source attribution measured |
| 6 | Evaluations and AI security | Regression harness, judge rubric, threat model, red-team cases | P2 release gate and security controls | Explain injection, exfiltration, excessive agency | Quality/security thresholds enforced in CI |
| 7 | Executive and architecture presentations | 10-slide executive deck, 30-minute workshop, cost/SLO model | P1/P2 recorded architecture demo | Mock director review and hostile Q&A | Decision, trade-offs, risk and ask clear in 10 minutes |
| 8 | Application package | Résumé, LinkedIn, portfolio index, role-specific cover notes | Two polished demos; evidence index | Two behavioral and two design mocks | Application-ready package reviewed against role matrix |

## Study Resources

- Weeks 2-3: dbt guides, dbt tests, Airflow docs, Great Expectations, Amplitude product analytics and Google SRE.
- Weeks 4-6: Anthropic/OpenAI docs, MCP architecture/security, MLflow evaluation/tracing, NIST AI RMF and OWASP GenAI/Agentic Top 10.
- Week 7: use architecture-review and executive-writing templates in `12-leadership-and-management.md`.

## Sprint Rules

1. Build the smallest vertical slice that demonstrates senior judgment; avoid feature breadth.
2. Log production failure modes: duplicate events, late data, schema drift, retrieval miss, unsafe tool call, provider timeout, prompt regression and cost spike.
3. Every week ends with a five-minute demo and a one-page decision record.
4. Application work begins in Week 4; completion of all eight weeks is not a prerequisite for applying.
