# Nine-Month AI Mastery Roadmap

This is a production-and-research literacy program, not a claim of equal specialization across all fields.

## Month 1 - Classical ML, Statistics And Experimentation

- **Objectives:** refresh probabilistic reasoning; build baselines; design valid product experiments.
- **Concepts:** bias/variance, regularization, calibration, leakage, uncertainty, power, segmentation and causal caveats.
- **Labs:** train and compare linear/tree models; calibration/error analysis; design an AI-feature experiment.
- **Portfolio:** baseline model and experiment specification for P1.
- **Reading:** MIT 6.036/18.657; Penn State STAT 503; selected CS229 notes.
- **Interview relevance:** metric choice, offline-vs-online evidence, experiment failure modes.
- **Exit:** reproducible notebook, model card and experiment review defended live.

## Month 2 - Deep Learning And PyTorch

- **Objectives:** independently implement and debug training loops.
- **Concepts:** tensors, autograd, optimization, normalization, regularization, data loading and profiling.
- **Labs:** MLP/CNN, custom loss, checkpoint/resume, mixed precision, profiler analysis.
- **Portfolio:** P3 training harness with tests and experiment metadata.
- **Reading:** PyTorch tutorials and relevant CS336 prerequisites.
- **Interview relevance:** tensor shapes, gradient failures, overfitting and throughput.
- **Exit:** diagnose five injected training failures and explain memory/compute trade-offs.

## Month 3 - NLP, Tokenization And Transformers

- **Objectives:** understand language-model data flow from text to logits.
- **Concepts:** BPE/WordPiece/Unigram, embeddings, attention, masking, position, decoding and context limits.
- **Labs:** tokenizer from corpus; attention module; small decoder-only transformer.
- **Portfolio:** P3 tokenizer/model plus token quality-cost dashboard.
- **Reading:** Hugging Face LLM Course, CS336, *Attention Is All You Need*.
- **Interview relevance:** token/context/latency trade-offs and transformer internals.
- **Exit:** train a small model and explain every major tensor transformation.

## Month 4 - LLM Training, Post-Training, Fine-Tuning And Inference

- **Objectives:** gain working literacy across the model lifecycle.
- **Concepts:** data mixtures, scaling, SFT, preference data, RLHF, DPO/RLAIF, LoRA, quantization, distillation, batching and KV cache.
- **Labs:** SFT/LoRA on a small model; quantized inference; quality-latency-memory benchmark.
- **Portfolio:** P3 adaptation report and reproducible benchmark.
- **Reading:** CS336 and primary scaling/LoRA/DPO papers.
- **Interview relevance:** adapt-vs-RAG, data risks, inference economics.
- **Exit:** defend an adaptation decision using measured quality, cost and latency.

## Month 5 - RAG, Search, Knowledge And Context Engineering

- **Objectives:** build evidence-grounded systems with measurable retrieval quality.
- **Concepts:** lexical/vector/hybrid retrieval, chunking, reranking, metadata filters, citations, long context, graphs and cache design.
- **Labs:** retrieval benchmark; reranker; GraphRAG survey/prototype; adversarial corpus tests.
- **Portfolio:** P2 RAG service and retrieval eval dataset.
- **Reading:** primary RAG papers plus provider retrieval guidance.
- **Interview relevance:** retrieval failure isolation and context economics.
- **Exit:** report recall/precision/answer quality by corpus slice and failure class.

## Month 6 - Agents, Deep Research, MCP And n8n

- **Objectives:** safely connect models to tools and enterprise systems.
- **Concepts:** workflows vs agents, planning, state, delegation, HITL, retries, idempotency, MCP primitives/auth and source verification.
- **Labs:** MCP server/client; research agent; controlled multi-agent experiment; one n8n approval workflow.
- **Portfolio:** P2 tool registry, approvals and trace viewer.
- **Reading:** Anthropic agent/tool guidance, OpenAI Agents SDK, MCP specification/security, n8n docs.
- **Interview relevance:** agency boundaries, reliability and reusable integration.
- **Exit:** pass unsafe-tool, auth, replay and partial-failure tests.

## Month 7 - Evaluations, LLMOps, Security, Reliability And Governance

- **Objectives:** make AI releases observable, testable and governable.
- **Concepts:** eval datasets, rubrics, judges, human review, traces, drift, SLOs, canaries, rollback, NIST and OWASP.
- **Labs:** eval CI; online feedback loop; prompt/model canary; incident game day; threat model.
- **Portfolio:** P2 evaluation service and executive risk dashboard.
- **Reading:** MLflow eval/tracing, NIST AI RMF, OWASP GenAI/Agentic, Google SRE.
- **Interview relevance:** quality gates, incident response and governance mechanisms.
- **Exit:** release/rollback decision supported by quality, safety, latency and cost evidence.

## Month 8 - Multimodal AI, Reinforcement Learning And Interpretability Survey

- **Objectives:** establish working literacy and identify one optional specialization.
- **Concepts:** multimodal encoders/fusion, MDPs/policy optimization, attribution/probes/circuits and evaluation limits.
- **Labs:** small multimodal app; RL control task; interpretability replication.
- **Portfolio:** P3 survey notebook and limitations memo.
- **Reading:** PyTorch/Hugging Face examples, OpenAI Spinning Up, Distill circuits.
- **Interview relevance:** honest boundaries, method selection and safety.
- **Exit:** three technical briefs separating demonstrated results from inference.

## Month 9 - Paper Reproduction And Integrated Capstone

- **Objectives:** combine product data, AI platform controls and research discipline.
- **Concepts:** hypothesis, controls, ablations, uncertainty, reproducibility and technical narrative.
- **Labs:** reproduce one tractable paper result; run two ablations; integrate capstone eval and telemetry.
- **Portfolio:** connected P1-P4 demonstration, research report and executive presentation.
- **Required reading:** selected papers from `14-research-paper-roadmap.md`.
- **Interview relevance:** principal-level synthesis across product, system, research and organization.
- **Exit:** external reviewer can reproduce the result; executive audience can make a decision from the presentation.

## Monthly Gate

Each month closes only when code, measurements, an ADR, a failure analysis and a concise presentation are linked from the tracker. Course completion alone does not satisfy a gate.
