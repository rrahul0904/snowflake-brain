# Interview Preparation

## STAR+L Framework

**Situation** and stakes; **Task** and personal accountability; **Actions** and decisions; **Result** with measures; **Learning/organizational change**. State alternatives rejected and why.

## Likely Questions

1. How would you design product telemetry for consumer, enterprise, coding and API surfaces?
2. How do you establish canonical metrics across Product and Data Science?
3. Describe a data-platform roadmap you led and how priorities were chosen.
4. Tell me about a severe incident you led.
5. How do you set data-quality and freshness SLOs?
6. How would you model token, latency, model, cost and tool-use telemetry?
7. Design a multi-tenant governed analytics copilot.
8. When should a team use RAG, fine-tuning or long context?
9. How do you evaluate retrieval separately from generation?
10. Design an agent allowed to update enterprise systems safely.
11. What controls mitigate prompt injection and tool abuse?
12. How would you implement an MCP server for sensitive data?
13. How do you compare AI providers and avoid lock-in?
14. Define SLOs and incident response for an AI application.
15. How do you detect a quality regression when infrastructure is healthy?
16. Tell me about a metric conflict you resolved.
17. How have you hired and developed senior engineers?
18. How do you manage disagreement with a principal engineer or executive?
19. Describe a customer discovery process for an ambiguous AI request.
20. How do you convert a custom delivery into reusable product capability?
21. Explain transformer attention to a senior engineer.
22. Explain tokenization trade-offs and their product impact.
23. Walk through a paper reproduction and a failed hypothesis.
24. What would your first 90 days in the anchor role look like?

## Eight Leadership Stories

Prepare the eight stories listed in `08-anthropic-role-alignment.md`, each in 2-minute, 5-minute and deep-dive forms.

## System-Design Exercises

1. Global AI-product telemetry platform.
2. Enterprise RAG with tenant isolation and freshness guarantees.
3. Governed agent platform with MCP and approval.
4. Evaluation/observability platform for prompts, models and agents.
5. Small-model training and inference platform under a fixed compute budget.

For each cover requirements, scale, APIs/data, reliability, security, evaluation, cost, rollout and organizational ownership.

## Product-Metric Exercises

1. Define activation and retention for a coding assistant.
2. Measure enterprise team adoption without vanity metrics.
3. Diagnose falling API retention while calls increase.
4. Design an experiment for an agentic workflow.
5. Balance answer quality, latency, cost and safety in one scorecard.

## AI-Evaluation Exercises

1. Build a retrieval benchmark by query slice.
2. Design a groundedness rubric and validate judge agreement.
3. Evaluate a tool-using agent with partial failures.
4. Create a red-team suite for injection/exfiltration.
5. Define canary and rollback thresholds for a model migration.

## Research Discussions

1. Attention architecture and its computational trade-offs.
2. Scaling laws and compute-optimal implications.
3. LoRA versus full fine-tuning.
4. DPO/RLHF assumptions and evaluation limits.
5. A reproduction with negative or ambiguous results.

## Mock Presentations

- **10 minutes:** executive investment decision.
- **30 minutes:** architecture review with hostile questions.
- **45 minutes:** customer discovery/workshop.
- **20 minutes:** research reproduction and limitations.
- **15 minutes:** incident review and prevention plan.

Record each, cut setup time, lead with the decision, and preserve technical depth for questions.
