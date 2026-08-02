# Research Engineer Track

## Role Boundaries

| Role | Primary output | Typical depth |
|---|---|---|
| AI Engineer | Reliable AI product and services | Application/system depth |
| ML Engineer | Training/serving pipelines and model lifecycle | ML + platform depth |
| Research Engineer | Experiments, training systems, reproductions and research code | Model + systems + experimental depth |
| Research Scientist | Novel hypotheses and externally credible original research | Deep specialty and mathematical research depth |

Research-scientist readiness cannot be established through courses alone. It generally requires sustained original research evidence, strong specialization and peer-visible contributions.

## Staged Path

1. **Mathematics:** linear algebra, probability, optimization and gradients; derive and implement core operations.
2. **PyTorch:** custom modules, training loops, checkpointing, mixed precision and profiler-driven debugging.
3. **Transformers from scratch:** tokenizer, attention, decoder, optimizer and generation.
4. **Data preparation:** provenance, deduplication, filtering, mixture design and contamination controls.
5. **Training systems:** reproducibility, distributed data parallel, sharding, checkpoint recovery and experiment tracking.
6. **GPU/inference:** memory accounting, kernels, batching, KV cache, quantization and throughput/latency trade-offs.
7. **Post-training:** SFT, LoRA, preference optimization and evaluation.
8. **Research method:** hypothesis, baseline, controls, ablations, uncertainty and limitations.
9. **Communication:** research logs, paper-style reports, code releases and technical talks.
10. **External evidence:** issue/PR contributions, reproducibility fixes, benchmark additions or open-source tooling.

## Readiness Gate

- [ ] Implement and train a small transformer without high-level model classes.
- [ ] Profile and improve a measurable bottleneck.
- [ ] Reproduce one paper result within a declared tolerance.
- [ ] Run at least two meaningful ablations.
- [ ] Demonstrate checkpoint recovery and deterministic controls.
- [ ] Explain divergence, instability, contamination and invalid comparison risks.
- [ ] Publish code, environment, data provenance, results and limitations.

## Interview Focus

Tensor operations; autograd; attention; optimization; data quality; distributed failure; GPU memory; experiment design; interpreting negative results; reading a paper under time pressure; designing a reproduction under constrained compute.
