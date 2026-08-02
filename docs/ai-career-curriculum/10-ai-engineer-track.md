# AI Engineer Track

Production readiness means owning behavior in failure, not merely producing a successful demo.

## Expectations

| Area | Production expectation | Failure modes to test |
|---|---|---|
| Python/TypeScript | Typed, testable services and SDK integrations | timeouts, malformed payloads, concurrency |
| APIs | Auth, rate limits, idempotency, streaming and versioning | retry storms, duplicate actions, backpressure |
| LLM applications | Structured outputs, context budgets, provider abstraction | truncation, drift, refusal, hallucination |
| RAG | Hybrid retrieval, reranking, citations and access filters | stale/poisoned corpus, misses, leakage |
| Agents | Bounded tools, state, approval, recovery and audit | loops, excessive agency, partial tool failure |
| Evaluations | Versioned datasets, rubrics, CI gates and human review | judge bias, contamination, metric gaming |
| Model serving | batching, caching, autoscaling and fallback | cold starts, OOM, overload, provider outage |
| Cloud/Kubernetes | deployment, secrets, networking, SLOs and rollback | bad rollout, node loss, config drift |
| Security | threat model, least privilege, input/output controls | injection, exfiltration, confused deputy |
| Observability | traces, logs, quality/latency/cost telemetry | missing correlation, PII in logs |
| Cost | token budgets, caching, routing and unit economics | runaway context, retry cost, model misuse |
| Multimodal | modality validation and task-specific eval | unsafe files, OCR errors, modality mismatch |
| Incident response | alert, triage, mitigate, learn and prevent | quality regression without infrastructure alarm |

## Readiness Checklist

- [ ] Build and load-test a provider-neutral LLM API.
- [ ] Implement RAG with retrieval and answer-quality evals.
- [ ] Build one MCP tool integration with auth and audit.
- [ ] Demonstrate human approval and safe retry semantics.
- [ ] Enforce quality/security/latency/cost release gates.
- [ ] Deploy with dashboards, SLOs, canary and rollback.
- [ ] Run an incident exercise and publish a postmortem.
- [ ] Explain measured build-vs-buy and model-selection trade-offs.

## Interview Exercises

1. Design a tenant-isolated enterprise knowledge assistant.
2. Debug a 30% groundedness regression after a corpus update.
3. Implement a streaming structured-output endpoint with cancellation.
4. Design a safe agent that can modify customer records.
5. Reduce p95 latency and cost without violating a quality gate.
6. Define an eval set and rollout for a new model snapshot.
7. Respond to suspected prompt-injection data exfiltration.
