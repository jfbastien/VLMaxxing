# Related-Work Table (Verified References)

Date: 2026-04-16
Parent: [literature-map-2026-04-16.md](literature-map-2026-04-16.md)

Canonical table of methods we cite or compare against, with
verification state. The literature map is prose; this file is the
machine-friendlier state.

`verified` means we have read the abstract and at least one headline
table in the primary source as of the listed date. `placeholder`
means we cite the method but have not verified the specifics we cite.

## Columns

| column | meaning |
|---|---|
| method | paper name or nickname |
| train | `train-free` or `trained` |
| stage | reduction stage on the VLM pipeline |
| signal | signal the method uses for its decision |
| family | `encoder-side-temporal`, `intra-frame-token`, `kv-memory`, `systems`, `trained-representation`, or `historical` |
| headline_metric | representative result in a short form |
| portability_blocker | what prevents this running on our MLX stack |
| verified | YYYY-MM-DD of primary-source check |
| url | primary URL |

## Table

| method | train | stage | signal | family | headline_metric | portability_blocker | verified | url |
|---|---|---|---|---|---|---|---|---|
| CodecSight | train-free | pre-ViT patch + LLM KV | MV + residuals (α=0 default) | systems | 2.97× end-to-end, 87% FLOP, F1 drop 0.08 on UCF-Crime (InternVL3) | NVDEC dependency; no MLX path | 2026-04-16 | [arXiv 2604.06036](https://arxiv.org/abs/2604.06036) |
| CoPE-VideoLM | trained | learned codec-native encoder | MV + residuals via trained transformer | trained-representation | TTFT 86% reduction, token 93% reduction, TOMATO 28.3% | requires learned Δ-encoder + alignment | 2026-04-16 | [arXiv 2602.13191](https://arxiv.org/abs/2602.13191) |
| FastV | train-free | decoder-internal layer K | intra-modal attention | intra-frame-token | ~45% FLOP (LLaVA-1.5-13B) | mlx-vlm fused SDPA hides attention scores; fork required | 2026-04-16 | [arXiv 2403.06764](https://arxiv.org/abs/2403.06764) |
| FastVID | train-free | post-encoder + spans temporal groups | density clustering | intra-frame-token | 90%+ prune, 7.1× prefill (LLaVA-OV-7B) | torch-only; hardwired into lmms-eval fork | 2026-04-16 | [arXiv 2503.11187](https://arxiv.org/abs/2503.11187) |
| FrameFusion | train-free | post-encoder, video-native | similarity + importance | encoder-side-temporal + intra-frame-token | 70% vision-token reduction, 1.6–1.9× end-to-end | torch; MLX port TBD | 2026-04-16 (abstract only) | [arXiv 2501.01986](https://arxiv.org/abs/2501.01986) |
| VisionZip | train-free | post-encoder | CLS-attention | intra-frame-token | ≥5% SOTA gain over prior art (their setting) | torch-only (HF hooks) | 2026-04-16 (abstract only) | [arXiv 2412.04467](https://arxiv.org/abs/2412.04467) |
| SparseVLM | train-free | decoder-internal every layer | cross-modal (text-visual attention) | intra-frame-token | 54% FLOP, 37% CUDA latency, 97% retained | torch + per-layer HF hooks | 2026-04-16 | [arXiv 2410.04417](https://arxiv.org/abs/2410.04417) |
| VScan | train-free | multi-stage (ViT + LLM mid-layer) | intra-modal + cross-modal | intra-frame-token | 2.91× prefill, 10× FLOP, 95.4% retained (LLaVA-NeXT-7B) | torch; modifies both forward passes | 2026-04-16 (abstract + headline) | [arXiv 2505.22654](https://arxiv.org/abs/2505.22654) |
| VLCache | train-free | encoder-cache + KV-cache | cross-request similarity | kv-memory | 1.2–16× TTFT, 2–5% tokens computed | SGLang only | 2026-04-16 | [arXiv 2512.12977](https://arxiv.org/abs/2512.12977) |
| StreamingVLM | mixed | KV management | recency + attention fading | kv-memory | long-horizon streaming (different task) | not directly comparable | placeholder | [arXiv 2510.09608](https://arxiv.org/abs/2510.09608) |
| Déjà Vu | trained | QKV + FFN reuse | MV + attention (Gumbel-Softmax) | encoder-side-temporal | 1.81×/2.64×/2.54× (retrieval/QA/grounding) | requires training | 2026-04-16 | [arXiv 2506.14107](https://arxiv.org/abs/2506.14107) |
| Eventful Transformers | train-free | per-block token gating at each transformer block | frame-to-frame delta magnitude | intra-frame-token | 2–4× compute (ImageNet VID, EPIC-Kitchens) | port to MLX not attempted | 2026-04-16 | [arXiv 2308.13494](https://arxiv.org/abs/2308.13494) |
| CoViAR | trained | classical CNN per compressed stream | codec I / MV / residual | historical | 4.6× vs Res3D (UCF-101, HMDB-51) | CNN, not a VLM method | 2026-04-16 (abstract) | [arXiv 1712.00636](https://arxiv.org/abs/1712.00636) |
| TurboQuant / PolarQuant | train-free | KV quantization | quantization | kv-memory | compose with our axis | orthogonal; not yet exercised | placeholder | [arXiv 2504.19874](https://arxiv.org/abs/2504.19874) |

## Notes on verification

- "verified 2026-04-16" next to a row means a research subagent or
  direct read confirmed the headline metric we cite.
- "verified 2026-04-16 (abstract only)" means we've confirmed the
  paper exists and the headline claim from the abstract, but NOT
  every mechanism detail we might summarize. Before citing the
  method's internal mechanism (e.g., VisionZip's CLS-attention
  specifics), re-read the paper's method section.
- "placeholder" rows we have not yet verified; cite them cautiously.

## Composition matrix (speculative)

| us × them | stage overlap | signal overlap | composes? |
|---|---|---|---|
| us × CodecSight | partial (both pre-ViT) | different signal (pixel vs MV) | **policy stacking**, not multiplicative |
| us × CoPE-VideoLM | none (different representation layer) | different (we use pixel diff, they use learned Δ-tokens) | clean in principle; future work |
| us × FastV | none (encoder vs decoder) | none | **multiplicative in cost model**, measured TBD |
| us × FastVID | partial (we encoder-side, they post-encoder-temporal) | partial (both address temporal redundancy) | likely interacts; not cleanly multiplicative |
| us × VisionZip | none (encoder vs post-encoder-intra-frame) | none | clean composition |
| us × SparseVLM | none (encoder vs decoder) | none | clean composition |
| us × VLCache | complementary (we encoder-side, they KV-reuse) | none | clean composition |
| us × StreamingVLM | complementary (short-horizon vs long-horizon) | none | clean composition |
| us × TurboQuant | complementary (fewer entries vs fewer bits) | none | clean composition |

"Composes" claims are first-order hypotheses; only phase 1.32 FastV
measurement will turn one row from speculation into evidence.
