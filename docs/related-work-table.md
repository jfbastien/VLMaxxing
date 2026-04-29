# Related-Work Table (Verified References)

Date: 2026-04-16
Parent: [literature-map-2026-04-16.md](literature-map-2026-04-16.md)

Canonical table of methods we cite or compare against. The literature map is
prose; this file is the machine-friendlier state.

`verified` means we have read the abstract and at least one headline
table in the primary source as of the listed date. Seed-derived or unverified
methods do not belong in this table; keep them in private scratch notes until a
primary source check is complete.

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
| SimpleStream | train-free | streaming-memory baseline | recent-frame recency window | systems | simple recency baseline matches or beats heavier streaming-memory methods on OVO-Bench and StreamingBench | benchmark / protocol baseline, not an MLX drop-in method | 2026-04-22 | [arXiv 2604.02317](https://arxiv.org/abs/2604.02317) |
| FastV | train-free | decoder-internal layer K | intra-modal attention | intra-frame-token | ~45% FLOP (LLaVA-1.5-13B) | mlx-vlm fused SDPA hides attention scores; fork required | 2026-04-16 | [arXiv 2403.06764](https://arxiv.org/abs/2403.06764) |
| FastVID | train-free | post-encoder + spans temporal groups | density clustering | intra-frame-token | 90%+ prune, 7.1× prefill (LLaVA-OV-7B) | torch-only; hardwired into lmms-eval fork | 2026-04-16 | [arXiv 2503.11187](https://arxiv.org/abs/2503.11187) |
| FrameFusion | train-free | post-encoder, video-native | similarity + importance | encoder-side-temporal + intra-frame-token | 70% vision-token reduction, 1.6–3.6× end-to-end | torch; MLX port TBD | 2026-04-29 (abstract) | [arXiv 2501.01986](https://arxiv.org/abs/2501.01986) |
| VisionZip | train-free | post-encoder | CLS-attention | intra-frame-token | ≥5% SOTA gain over prior art (their setting) | torch-only (HF hooks) | 2026-04-16 (abstract only) | [arXiv 2412.04467](https://arxiv.org/abs/2412.04467) |
| SparseVLM | train-free | decoder-internal every layer | cross-modal (text-visual attention) | intra-frame-token | 54% FLOP, 37% CUDA latency, 97% retained | torch + per-layer HF hooks | 2026-04-16 | [arXiv 2410.04417](https://arxiv.org/abs/2410.04417) |
| VScan | train-free | multi-stage (ViT + LLM mid-layer) | intra-modal + cross-modal | intra-frame-token | 2.91× prefill, 10× FLOP, 95.4% retained (LLaVA-NeXT-7B) | torch; modifies both forward passes | 2026-04-16 (abstract + headline) | [arXiv 2505.22654](https://arxiv.org/abs/2505.22654) |
| VLCache | train-free | encoder-cache + KV-cache | cross-request similarity | kv-memory | 1.2–16× TTFT, 2–5% tokens computed | SGLang only | 2026-04-16 | [arXiv 2512.12977](https://arxiv.org/abs/2512.12977) |
| STTM | train-free | post-ViT (inside LLM layers) | spatio-temporal redundancy (directed pairwise matching) | intra-frame-token | 2× speedup at 0.5% acc drop, 50% tokens (LLaVA-Video-7B, 6 benchmarks) | torch (GitHub: HYUNJS/STTM); MLX port TBD | 2026-04-16 | [arXiv 2507.07990](https://arxiv.org/abs/2507.07990) |
| T3S | train-free | inference wrapper (temporal sampling) | diverse subsequence packing | encoder-side-temporal | +3.1% acc, 2.04× TTFT reduction (long-video MLLMs) | model-agnostic wrapper; MLX compat likely | 2026-04-16 (abstract) | [arXiv 2511.17945](https://arxiv.org/abs/2511.17945) |
| FlashVID | train-free | post-ViT: tree-based spatiotemporal merge | attention/diversity selection + tree-based spatiotemporal token merging | intra-frame-token | 99.1% LLaVA-OV performance at 10% token retention; 6.3× prefill / 2.1× TTFT on the LLaVA-OV efficiency table; 10× Qwen2.5-VL frame input with +8.6% relative gain under the same budget | torch (ICLR 2026 Oral); MLX port possible but non-trivial | 2026-04-29 (OpenReview + arXiv) | [OpenReview ICLR 2026](https://openreview.net/forum?id=H6rDX4w6Al) |
| Déjà Vu | trained | QKV + FFN reuse | MV + attention (Gumbel-Softmax) | encoder-side-temporal | 1.81×/2.64×/2.54× (retrieval/QA/grounding) | requires training | 2026-04-16 | [arXiv 2506.14107](https://arxiv.org/abs/2506.14107) |
| Eventful Transformers | train-free | per-block token gating at each transformer block | frame-to-frame delta magnitude | intra-frame-token | 2–4× compute (ImageNet VID, EPIC-Kitchens) | port to MLX not attempted | 2026-04-16 | [arXiv 2308.13494](https://arxiv.org/abs/2308.13494) |
| CoViAR | trained | classical CNN per compressed stream | codec I / MV / residual | historical | 4.6× vs Res3D (UCF-101, HMDB-51) | CNN, not a VLM method | 2026-04-16 (abstract) | [arXiv 1712.00636](https://arxiv.org/abs/1712.00636) |

## Notes on verification

- "verified 2026-04-16" next to a row means a research subagent or
  direct read confirmed the headline metric we cite.
- "verified 2026-04-16 (abstract only)" means we've confirmed the
  paper exists and the headline claim from the abstract, but NOT
  every mechanism detail we might summarize. Before citing the
  method's internal mechanism (e.g., VisionZip's CLS-attention
  specifics), re-read the paper's method section.
- Add a new row only after checking the primary source and recording the date.

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
| us × STTM | partial (both address temporal redundancy post-ViT) | partial (directed matching vs pixel-diff) | worth measuring; STTM handles remaining temporal redundancy we don't eliminate |
| us × T3S | complementary (we reduce per-frame cost, T3S packs more subsequences) | none | clean; T3S is a wrapping strategy, not a model change |

"Composes" claims are first-order hypotheses; only phase 1.32 FastV
measurement will turn one row from speculation into evidence.
