# Skill Matrix

Scale: **0** no exposure; **1** awareness; **2** implement with guidance; **3** independent practitioner; **4** architect and defend trade-offs; **5** lead teams and organizational adoption. Current proficiency is intentionally left for evidence-based self-assessment.

| Domain | Subskill | Description | Target | Current | Priority | Why it matters | Required evidence | Suggested project | Free resource category |
|---|---|---|---:|---:|---|---|---|---|---|
| Data engineering | Batch/stream architecture | Reliable ingestion, processing and replay | 5 |  | P0 | Foundation for product and AI telemetry | SLOs, replay test, cost model | P1 | Airflow/SRE |
| Data architecture | Contracts and canonical models | Stable events, facts, dimensions and semantics | 5 |  | P0 | Prevents metric and training-data drift | Versioned contract and lineage | P1 | dbt |
| Product data | Event design and metrics | Consumer, enterprise, coding and API behavior | 5 |  | P0 | Anchor-role requirement | Event taxonomy and metric tree | P1 | Product analytics |
| Data quality | Tests, freshness and observability | Detect correctness, schema and delay failures | 5 |  | P0 | Trust and incident control | Test suite, SLA dashboard, postmortem | P1 | dbt/GX/SRE |
| Governance | Ownership, access and retention | Policy translated into platform controls | 5 |  | P0 | Enterprise adoption | RACI, policy-as-code sample | P1/P2 | NIST |
| Reliability | SLOs and incident leadership | Error budgets, response and learning | 5 |  | P0 | Senior operational credibility | SLOs, game day, incident review | P1/P2 | Google SRE |
| Leadership | Team and operating model | Hiring, coaching, roadmap and architecture governance | 5 |  | P0 | Principal/Director scope | Team charter and scorecards | All | Management |
| Mathematics | Linear algebra/calculus | Matrices, gradients and optimization intuition | 3 |  | P2 | Read model and training code | Derivation notebook | P3 | MIT OCW |
| Statistics | Inference and experimentation | Uncertainty, power, A/B tests and causal caveats | 4 |  | P1 | Product decisions and evals | Experiment design and analysis | P1/P3 | PSU/MIT |
| Classical ML | Supervised/unsupervised learning | Features, generalization, calibration and error analysis | 3 |  | P1 | Baseline and evaluation literacy | Reproducible baseline report | P3 | MIT/Stanford |
| Deep learning | Neural nets and optimization | Backprop, regularization and architecture choices | 3 |  | P1 | Foundation for transformers | PyTorch training notebook | P3 | PyTorch |
| PyTorch | Training and profiling | Datasets, modules, autograd, AMP and profiling | 4 |  | P1 | Research-engineering execution | Tested training loop and profile | P3 | PyTorch/CS336 |
| NLP | Language modeling fundamentals | Representations, objectives and sequence tasks | 3 |  | P1 | Grounding for LLM systems | Task comparison note | P3 | Hugging Face |
| Transformers | Attention and architecture | MHA, residuals, normalization and decoding | 4 |  | P1 | Defend model behavior trade-offs | Transformer from scratch | P3 | CS336/papers |
| Token intelligence | Token/context economics | Tokenization, truncation, quality, latency and cost | 4 |  | P0 | Production AI economics | Token profiler and budget policy | P2/P3 | HF/CS336 |
| Pre-training | Data/objectives/scaling | Data mix, compute allocation and scaling concepts | 3 |  | P2 | Research literacy | Scaling experiment note | P3 | CS336/papers |
| Post-training | SFT, RLHF, DPO, RLAIF | Preference data and alignment objectives | 3 |  | P2 | Understand model adaptation | SFT/DPO comparison lab | P3 | Papers/HF |
| Adaptation | LoRA, quantization, distillation | Efficient tuning and serving trade-offs | 3 |  | P1 | Practical model customization | Adapter benchmark | P3 | HF/PyTorch |
| Prompt/context | Instruction and context design | Structured prompts, examples, caching and context selection | 4 |  | P0 | Controls quality and cost | Prompt regression suite | P2 | Anthropic/OpenAI |
| Retrieval | Search and RAG | Chunking, embeddings, hybrid search, reranking and citations | 5 |  | P0 | Core production pattern | Retrieval eval set and failure analysis | P2 | HF/OpenAI |
| Knowledge systems | Knowledge graphs and GraphRAG | Entity/relation modeling and graph-assisted retrieval | 3 |  | P2 | Complex enterprise knowledge | Graph retrieval prototype | P2 | Open source/papers |
| LLM apps | API and application design | Structured output, streaming, caching and fallbacks | 5 |  | P0 | Production depth | Load-tested service with SLO | P2 | Anthropic/OpenAI |
| Agents | Tool-using control loops | Planning, state, delegation, recovery and HITL | 4 |  | P0 | Forward-deployed systems | Agent trace/eval suite | P2 | Anthropic/OpenAI |
| Deep research | Iterative search and synthesis | Source planning, verification and citation | 3 |  | P1 | High-value knowledge workflows | Source-grounded research agent | P2 | Agents/IR |
| MCP | Clients, servers, primitives and security | Tools/resources/prompts, auth and isolation | 4 |  | P0 | Enterprise integration standard | Secure MCP server and threat model | P2 | MCP official |
| Workflow automation | n8n | Tactical orchestration, approvals and prototypes | 2 |  | P2 | Fast integration validation | One governed workflow | P2 | n8n docs |
| Evaluations | Offline/online quality systems | Datasets, rubrics, judges, human review and CI | 5 |  | P0 | Release gate for AI | Versioned eval harness and scorecard | P2 | Anthropic/OpenAI/MLflow |
| LLMOps/MLOps | Lifecycle and observability | Versioning, tracing, drift, rollout and rollback | 5 |  | P0 | Platform ownership | Trace model and deployment runbook | P2 | MLflow/Kubernetes |
| Distributed training | Parallelism and checkpointing | DDP/FSDP, data/tensor/pipeline parallel concepts | 3 |  | P2 | Research systems literacy | Two-GPU or simulated benchmark | P3 | PyTorch/CS336 |
| GPU systems | Compute and memory | FLOPs, bandwidth, kernels, batching and KV cache | 3 |  | P2 | Cost/performance reasoning | Profiling report | P3 | CS336/PyTorch |
| Inference | Serving and optimization | Quantization, batching, caching and autoscaling | 4 |  | P1 | Production cost and latency | Load/cost benchmark | P2/P3 | PyTorch/Kubernetes |
| AI security | LLM/agent threat modeling | Injection, exfiltration, tool abuse and supply chain | 5 |  | P0 | Enterprise trust | Threat model, red-team suite, controls | P2 | OWASP/MCP |
| AI governance | Risk and accountability | Inventory, impact, measurement and oversight | 5 |  | P0 | Executive adoption | NIST-based control map | P2 | NIST |
| Multimodal AI | Text/image/audio systems | Encoders, fusion, eval and safety | 3 |  | P2 | Expanding product surface | Multimodal prototype | P3 | PyTorch/HF |
| Reinforcement learning | MDPs and policy optimization | Policies, value, reward and exploration | 2 |  | P3 | Research/post-training literacy | Small RL experiment | P3 | OpenAI Spinning Up |
| Interpretability | Attribution, probes and circuits | Investigate internal behavior and limits | 2 |  | P3 | Research/safety literacy | Replicated analysis | P3 | Distill/papers |
| Research methods | Reproduction and ablation | Hypotheses, controls, uncertainty and technical writing | 3 |  | P1 | Research-engineering credibility | Reproduction report | P3 | Primary papers |
| Product analytics | Funnels, cohorts and telemetry | Adoption, retention and experiment metrics | 5 |  | P0 | Product-data leadership | Metric tree and dashboard | P1 | Amplitude |
| Forward deployed | Discovery and delivery | Scope ambiguity, prototype, integration and adoption | 4 |  | P0 | Target adjacent roles | Discovery log and case study | P4 | SA practice |
| Executive communication | Decisions and narratives | Concise trade-offs, risk and investment asks | 5 |  | P0 | Director-level influence | 10-slide architecture/roadmap | All | Writing/presentations |

## Evidence Standard

Level 4 requires a working system plus a documented trade-off. Level 5 requires repeatable organizational mechanisms: standards, operating cadence, adoption, measurable outcomes and evidence that other engineers can execute through the system.
