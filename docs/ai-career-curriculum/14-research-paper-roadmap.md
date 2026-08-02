# Research Paper Roadmap

Read primary papers actively: claim, assumptions, method, baseline, data, metric, result, limitations, reproduction plan and product implication.

| Category | Representative primary papers / reading order | Questions | Suggested reproduction or ablation | Target depth |
|---|---|---|---|---|
| Attention/transformers | [Attention Is All You Need](https://arxiv.org/abs/1706.03762) -> architecture variants | Why attention, residuals, normalization and masking? | Small transformer; remove position/normalization | 4 |
| Scaling laws | [Scaling Laws for Neural Language Models](https://arxiv.org/abs/2001.08361) -> [Chinchilla](https://arxiv.org/abs/2203.15556) | What is held fixed? When do laws extrapolate poorly? | Fit a small compute/data scaling curve | 3 |
| Tokenization | [BPE](https://aclanthology.org/P16-1162/) -> [SentencePiece](https://arxiv.org/abs/1808.06226) | How do vocabulary/domain choices affect length and quality? | Train two tokenizers; compare fertility/cost | 4 |
| Retrieval/long context | [RAG](https://arxiv.org/abs/2005.11401) -> [RETRO](https://arxiv.org/abs/2112.04426) | Where does retrieval improve or introduce error? | Chunking/reranking ablation by query type | 4 |
| PEFT | [LoRA](https://arxiv.org/abs/2106.09685) | Which matrices/ranks matter and why? | Rank/data-size/quantization ablation | 3 |
| Preference optimization | [InstructGPT](https://arxiv.org/abs/2203.02155) -> [Constitutional AI](https://arxiv.org/abs/2212.08073) -> [DPO](https://arxiv.org/abs/2305.18290) | What supervision and reward assumptions apply? | Small SFT vs DPO comparison | 3 |
| Tool use | [Toolformer](https://arxiv.org/abs/2302.04761) -> [ReAct](https://arxiv.org/abs/2210.03629) | How are calls selected and evaluated? | Tool description/error-recovery ablation | 4 |
| Agents | [Generative Agents](https://arxiv.org/abs/2304.03442) plus current provider engineering guidance | What requires agency versus workflow? | Workflow vs agent on same task | 4 production / 3 research |
| Evaluation | [HELM](https://arxiv.org/abs/2211.09110) -> [MT-Bench/Judge](https://arxiv.org/abs/2306.05685) | Coverage, contamination, judge bias, validity? | Human-vs-judge agreement by slice | 5 production |
| Interpretability | [Distill Circuits](https://distill.pub/2020/circuits/zoom-in/) -> [Toy Models of Superposition](https://arxiv.org/abs/2209.10652) | What does the method establish versus suggest? | Replicate a small feature/circuit result | 2-3 |
| Multimodal | [CLIP](https://arxiv.org/abs/2103.00020) -> [Flamingo](https://arxiv.org/abs/2204.14198) | Alignment, fusion, data and evaluation limits? | Zero-shot classification/error slices | 2-3 |
| Inference optimization | [FlashAttention](https://arxiv.org/abs/2205.14135) -> [vLLM/PagedAttention](https://arxiv.org/abs/2309.06180) | Which bottleneck is compute, memory or scheduling? | Profile baseline vs optimized attention/serving | 3 |
| Safety/alignment | [Constitutional AI](https://arxiv.org/abs/2212.08073) and NIST/OWASP operational guidance | How do model and system controls interact? | Red-team/control ablation with residual risk | 4 production |

## Reading Order

1. Months 3-4: attention, tokenization, scaling, PEFT and preference optimization.
2. Months 5-7: retrieval, tool use, agents, evaluation, inference and safety.
3. Month 8: multimodal and interpretability survey.
4. Month 9: select one tractable result with available code/data/compute; preregister reproduction tolerance and ablations.

## Reproduction Standard

Pin environment and data; establish baseline; log seeds/compute; declare deviations; report uncertainty and negative results; separate replication from novel extension; make cost and limitations explicit.
