# Related-Work Table (Verified References)

Date: 2026-05-10
Related prose map: [literature-map-2026-04-16.md](literature-map-2026-04-16.md)

Canonical table of methods we cite or compare against. The literature map is
prose; this file is the machine-friendlier state.

`verified` means we have read the abstract and at least one headline
table in the primary source as of the listed date. Seed-derived or unverified
methods do not belong in this table; keep them in private scratch notes until a
primary source check is complete.

Benchmark and runtime references used by the manuscript but not listed as
comparison methods: TOMATO is ICLR 2025 Poster on OpenReview and arXiv
2410.23266; Qwen2.5-VL is arXiv 2502.13923; Gemma 4 E4B is cited through the
Google Hugging Face model card plus the MLX-community 4-bit conversion; MLX-VLM
is cited through the project repository.

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
| CodecSight | train-free | pre-ViT patch + LLM KV | MV + residuals (α=0 default) | systems | up to 3× throughput, up to 87% GPU compute reduction, 0-8% F1 drop | NVDEC dependency; no MLX path | 2026-04-29 | [arXiv 2604.06036](https://arxiv.org/abs/2604.06036) |
| CoPE-VideoLM | trained | learned codec-native encoder | MV + residuals via trained transformer | trained-representation | TTFT 86% reduction, token 93% reduction, TOMATO 28.3% | requires learned Δ-encoder + alignment | 2026-04-16 | [arXiv 2602.13191](https://arxiv.org/abs/2602.13191) |
| SimpleStream | train-free | streaming-memory baseline | recent-frame recency window | systems | simple recency baseline matches or beats heavier streaming-memory methods on OVO-Bench and StreamingBench | benchmark / protocol baseline, not an MLX drop-in method | 2026-04-22 | [arXiv 2604.02317](https://arxiv.org/abs/2604.02317) |
| FastV | train-free | decoder-internal layer K | intra-modal attention | intra-frame-token | 45% FLOPs reduction (LLaVA-1.5-13B) | mlx-vlm fused SDPA hides attention scores; fork required | 2026-04-29 | [arXiv 2403.06764](https://arxiv.org/abs/2403.06764) |
| FastVID | train-free | post-encoder + spans temporal groups | density clustering | encoder-side-temporal + intra-frame-token | 90.3% token pruning, FLOPs to 8.3%, 7.1× LLM prefill speedup, 98.0% original accuracy on LLaVA-OneVision-7B | torch-only; hardwired into lmms-eval fork | 2026-04-29 | [arXiv 2503.11187](https://arxiv.org/abs/2503.11187); [OpenReview NeurIPS 2025](https://openreview.net/forum?id=2xS4VtpApy) |
| EVS | train-free / optional uptraining | post-encoder video-token pruning | temporally static patch pruning with positional identity preserved | encoder-side-temporal + intra-frame-token | up to 4× TTFT reduction with minimal accuracy loss; optional uptraining improves robustness under aggressive pruning | closest plug-and-play static-patch baseline; MLX C-VISION analog should be tested before claiming typed static-detail wins | 2026-05-15 | [arXiv 2510.14624](https://arxiv.org/abs/2510.14624) |
| FrameFusion | train-free | post-encoder, video-native | similarity + importance | encoder-side-temporal + intra-frame-token | 70% vision-token reduction, 1.6–3.6× end-to-end | torch; MLX port TBD | 2026-04-29 | [CVF ICCV 2025](https://openaccess.thecvf.com/content/ICCV2025/html/Fu_FrameFusion_Combining_Similarity_and_Importance_for_Video_Token_Reduction_on_ICCV_2025_paper.html); [arXiv 2501.01986](https://arxiv.org/abs/2501.01986) |
| VisionZip | train-free | post-encoder | encoder-dependent attention score: CLS-token attention for CLS encoders, average received attention otherwise | intra-frame-token | ≥5% SOTA gain over prior art (their setting) | torch-only (HF hooks) | 2026-04-29 | [CVF CVPR 2025](https://openaccess.thecvf.com/content/CVPR2025/html/Yang_VisionZip_Longer_is_Better_but_Not_Necessary_in_Vision_Language_CVPR_2025_paper.html); [arXiv 2412.04467](https://arxiv.org/abs/2412.04467) |
| EvoPrune | train-free | visual encoder, early-stage token pruning | layer-wise token similarity, diversity, and attention importance | intra-frame-token | 2× VideoMME inference speedup with less than 1% performance degradation | modifies visual-encoding internals; no MLX port | 2026-04-30 | [arXiv 2603.03681](https://arxiv.org/abs/2603.03681) |
| SparseVLM | train-free | decoder-internal every layer | cross-modal (text-visual attention) | intra-frame-token | 54% FLOPs reduction, 37% CUDA latency decrease, 97% original accuracy retained | torch + per-layer HF hooks | 2026-04-29 | [PMLR ICML 2025](https://proceedings.mlr.press/v267/zhang25s.html) |
| Token Pruning: Are We Solving the Right Problem? | analysis | evaluation critique | fixed/random coverage, attention-score critique, duplication-vs-importance tradeoff | intra-frame-token | shows many pruning methods underperform naive random token selection; makes random/fixed controls mandatory | critique paper, not a method | 2026-05-10 | [ACL Findings 2025](https://aclanthology.org/2025.findings-acl.802/) |
| DART | train-free | token pruning | duplication-aware token retention instead of importance ranking | intra-frame-token | reports 88.9% visual-token pruning with comparable performance and 1.99× total-time speedup | torch / attention-operator compatibility; MLX port TBD | 2026-05-10 | [EMNLP 2025](https://aclanthology.org/2025.emnlp-main.505/); [arXiv 2502.11494](https://arxiv.org/abs/2502.11494) |
| VScan | train-free | multi-stage (ViT + LLM mid-layer) | intra-modal + cross-modal | intra-frame-token | 2.91× prefill, 10× FLOPs reduction, 95.4% original performance retained (LLaVA-NeXT-7B) | torch; modifies both forward passes | 2026-04-29 | [arXiv 2505.22654](https://arxiv.org/abs/2505.22654); [OpenReview TMLR](https://openreview.net/forum?id=KZYhyilFnt) |
| VLCache | train-free | encoder-cache + KV-cache | cross-request similarity | kv-memory | 1.2–16× TTFT, 2–5% tokens computed | SGLang only | 2026-04-16 | [arXiv 2512.12977](https://arxiv.org/abs/2512.12977) |
| STTM | train-free | post-ViT (inside LLM layers) | spatio-temporal redundancy (directed pairwise matching) | intra-frame-token | 2× speedup at 0.5% acc drop, 50% tokens (LLaVA-Video-7B, 6 benchmarks) | torch (GitHub: HYUNJS/STTM); MLX port TBD | 2026-04-16 | [arXiv 2507.07990](https://arxiv.org/abs/2507.07990) |
| T3S | train-free | inference wrapper (temporal sampling) | diverse subsequence packing | encoder-side-temporal | +3.1% acc, 2.04× TTFT reduction (long-video MLLMs) | model-agnostic wrapper; MLX compat likely | 2026-04-16 (abstract) | [arXiv 2511.17945](https://arxiv.org/abs/2511.17945) |
| FlashVID | train-free | post-ViT: tree-based spatiotemporal merge | attention/diversity selection + tree-based spatiotemporal token merging | encoder-side-temporal + intra-frame-token | At 10% visual-token retention, preserves 99.1% of LLaVA-OneVision performance; on the LLaVA-OneVision VideoMME efficiency comparison, reports 6.3× prefill and 2.1× TTFT speedups versus FastVID; separately enables Qwen2.5-VL to process 10× more frames with +8.6% relative performance under matched budget | torch (ICLR 2026 Oral); MLX port possible but non-trivial | 2026-04-29 | [arXiv 2602.08024](https://arxiv.org/abs/2602.08024); [OpenReview ICLR 2026](https://openreview.net/forum?id=H6rDX4w6Al) |
| Déjà Vu | trained | QKV + FFN reuse | MV + attention (Gumbel-Softmax) | encoder-side-temporal | 1.81×/2.64×/2.54× (retrieval/QA/grounding) | requires training | 2026-04-16 | [arXiv 2506.14107](https://arxiv.org/abs/2506.14107) |
| Eventful Transformers | train-free | per-block token gating at each transformer block | frame-to-frame delta magnitude | encoder-side-temporal | 2–4× computational savings (ImageNet VID, EPIC-Kitchens) | port to MLX not attempted | 2026-04-29 | [arXiv 2308.13494](https://arxiv.org/abs/2308.13494) |
| CoViAR | trained | classical CNN per compressed stream | codec I / MV / residual | historical | 4.6× faster than Res3D (UCF-101, HMDB-51) | CNN, not a VLM method | 2026-04-29 | [arXiv 1712.00636](https://arxiv.org/abs/1712.00636) |
| FastVLM | trained | vision encoder architecture | FastViTHD hybrid encoder, fewer visual tokens, lower encoding latency | trained-representation | 3.2× TTFT improvement in LLaVA-1.5 setup; 85× faster TTFT than LLaVA-OneVision at 1152² in the paper setting | requires trained FastVLM/FastViTHD weights, not drop-in pruning | 2026-04-29 | [CVPR 2025](https://openaccess.thecvf.com/content/CVPR2025/html/Vasu_FastVLM_Efficient_Vision_Encoding_for_Vision_Language_Models_CVPR_2025_paper.html) |
| LLaVA-PruMerge | train-free | post-vision-encoder token pruning/merging | CLS-token attention sparsity + key-similarity clustering | intra-frame-token | 4× visual-token reduction on LLaVA-1.5 and Video-LLaVA with comparable or better performance | CLIP/LLaVA-specific token plumbing; MLX port TBD | 2026-04-29 | [ICCV 2025](https://openaccess.thecvf.com/content/ICCV2025/html/Shang_LLaVA-PruMerge_Adaptive_Token_Reduction_for_Efficient_Large_Multimodal_Models_ICCV_2025_paper.html) |
| SparseVILA | train-free | prefill pruning + decode-time retrieval | query-agnostic pruning + query-aware visual-token retrieval | kv-memory + intra-frame-token | 1.4× image-benchmark speedup; +5.9% average image accuracy; 3.6× prefill and 1.7× decoding speedup on long-context/generation tasks | AWQ/CUDA pipeline and retrieval path; no MLX path | 2026-04-29 | [ICCV 2025](https://openaccess.thecvf.com/content/ICCV2025/html/Khaki_SparseVILA_Decoupling_Visual_Sparsity_for_Efficient_VLM_Inference_ICCV_2025_paper.html) |
| HERMES | train-free | hierarchical KV memory for streaming video | cache hierarchy over streaming visual context | kv-memory | 10× faster TTFT than prior SOTA, up to 68% fewer video tokens than uniform sampling, and superior or comparable accuracy with up to 11.4% gains on streaming datasets | streaming/KV runtime design; not a drop-in frame-domain sparse-vision method | 2026-04-30 | [ACL 2026 Main / arXiv 2601.14724](https://arxiv.org/abs/2601.14724) |
| QuickVideo | train-free | system pipeline: decoding + LLM prefill | QuickCodec keyframe-aligned parallel CPU decoding + QuickPrefill KV-cache pruning + CPU/GPU overlap | systems | QuickCodec gives 2–3× decoding speedup; the full pipeline reduces long-video input processing time by about one minute | CPU/GPU pipeline integration and QuickPrefill; not MLX drop-in | 2026-04-29 | [arXiv 2505.16175](https://arxiv.org/abs/2505.16175); [OpenReview TMLR](https://openreview.net/forum?id=Rpcxgzcsuc) |

## Query-Aware Visual Routing Priors

These rows are primarily for the follow-on query-aware visual-routing paper,
not for the current VLMaxxing/RLT update. They define the novelty boundary:
query-aware selection already exists; our future contribution must be
operator-level visual evidence planning with full cost accounting.

| method | train | stage | signal | family | headline_metric | portability_blocker | verified | url |
|---|---|---|---|---|---|---|---|---|
| Static or Dynamic | train-free | video token allocation | query-aware static-keyframe vs delta-frame allocation | query-aware-video-routing | up to +5.8% on video-QA benchmarks by selecting static/dynamic token mix without model updates | method overlap; must compare conceptually and avoid claiming first static/dynamic query allocation | 2026-05-10 | [ACL Anthology EMNLP 2025](https://aclanthology.org/2025.emnlp-main.545/) |
| Active Video Perception | agentic / training-free at inference | iterative evidence seeking | planner-observer-reflector loop over what/when/where to observe | query-aware-video-routing | outperforms the best agentic method by 5.7% average accuracy while using 18.4% inference time and 12.4% input tokens | agentic loop and long-video protocol; closest high-level prior to evidence planning | 2026-05-10 | [arXiv 2512.05774](https://arxiv.org/abs/2512.05774) |
| QuoTA | train-free | ante-hoc visual token assignment | CoT query decomposition + query-oriented frame importance | query-aware-video-routing | +3.2% average performance across six benchmarks at identical visual token budget | uses LVLM/CoT query decomposition; scalar/budget assignment baseline, not typed operator menu | 2026-05-10 | [arXiv 2503.08689](https://arxiv.org/abs/2503.08689) |
| Q-Frame | train-free | frame selection + resolution adaptation | CLIP-like text-image matching + Gumbel-Max; multi-resolution scaling | query-aware-video-routing | improves Video-LLM performance on MLVU, LongVideoBench, and Video-MME while fitting compute budgets | frame-level, not token-level C-VISION; CLIP dependency if reproduced | 2026-05-10 | [ICCV 2025](https://iccv.thecvf.com/virtual/2025/poster/499); [arXiv 2506.22139](https://arxiv.org/abs/2506.22139) |
| Frame-Voyager | trained | frame-combination selection | query-conditioned learned policy supervised by Video-LLM loss ranking | query-aware-video-routing | improves four Video-QA benchmarks when plugged into two Video-LLMs | trained selector + frame-level policy; not training-free | 2026-05-10 | [arXiv 2410.03226](https://arxiv.org/abs/2410.03226) |
| M-LLM frame selection | trained | frame selection | spatial and temporal pseudo-labels from M-LLM/LLM prompts | query-aware-video-routing | improves medium/long-context video-QA benchmarks including ActivityNet, NExT-QA, EgoSchema, and LongVideoBench | trained frame selector and external pseudo-label pipeline | 2026-05-10 | [CVPR 2025](https://cvpr.thecvf.com/virtual/2025/poster/34303); [arXiv 2502.19680](https://arxiv.org/abs/2502.19680) |
| PruneVid | train-free | video visual-token pruning | temporal/static redundancy merge + query-irrelevant token pruning | query-aware-video-routing + intra-frame-token | prunes over 80% tokens while maintaining competitive performance across video benchmarks | post-encoding/LLM relevance plumbing; not a pre-vision C-VISION scorer | 2026-05-10 | [ACL Findings 2025](https://aclanthology.org/2025.findings-acl.1024/) |
| QTSplus | trained | visual token selector between encoder and LLM | cross-attention scoring + instance-specific retention budget + temporal re-encoder | query-aware-video-routing | reports up to 89% vision-stream compression and 28% E2E latency reduction on long videos | trained module; arXiv/preprint status | 2026-05-10 | [arXiv 2511.11910](https://arxiv.org/abs/2511.11910) |
| LongVU | trained / model-integrated | long-video spatiotemporal compression | DINOv2 frame redundancy + text-guided cross-modal query + inter-frame spatial reduction | query-aware-video-routing | processes long videos within context limits and reports strong VideoMME/MLVU long-video performance | model-integrated compression; not a drop-in C-VISION scorer | 2026-05-10 | [ICML 2025 / PMLR](https://collaborate.princeton.edu/en/publications/longvu-spatiotemporal-adaptive-compression-for-long-video-languag/); [arXiv 2410.17434](https://arxiv.org/abs/2410.17434) |
| FlashVLM | train-free | visual-token selection | text-guided cross-modal similarity + intrinsic saliency + diversity floor | query-aware-video-routing | reports strong compression/accuracy tradeoffs across image/video benchmarks | arXiv preprint; scalar token scorer, not structured evidence plan | 2026-05-10 | [arXiv 2512.20561](https://arxiv.org/abs/2512.20561) |
| Principles of Visual Tokens | analysis + trained lightweight model | video token-value analysis | oracle token value, random baseline, Pareto token-value distribution | query-aware-video-routing + intra-frame-token | argues most token-selection methods do not beat random discarding; proposes LITE for GFLOPs/accuracy tradeoff | benchmark family differs; primarily token-value theory and controls | 2026-05-10 | [arXiv 2411.13626](https://arxiv.org/abs/2411.13626) |
| Inference Compute-Optimal Video VLMs | analysis / trained sweeps | compute-allocation frontier | model size, frame count, visual tokens per frame under fixed inference compute | query-aware-video-routing | studies compute-optimal allocation across frame count and tokens per frame | frontier paper, not a drop-in method; required context for compute-allocation claims | 2026-05-10 | [ACL 2025](https://aclanthology.org/2025.acl-long.117/); [arXiv 2505.18855](https://arxiv.org/abs/2505.18855) |

## Notes on verification

- "verified 2026-04-16" next to a row means a research subagent or
  direct read confirmed the headline metric we cite.
- "verified 2026-04-16 (abstract only)" means we've confirmed the
  paper exists and the headline claim from the abstract, but NOT
  every mechanism detail we might summarize. Before citing a method's
  internal mechanism, re-read the paper's method section.
- Add a new row only after checking the primary source and recording the date.

## Composition matrix (speculative)

| us × them | stage overlap | signal overlap | composes? |
|---|---|---|---|
| us × CodecSight | partial (both pre-ViT) | different signal (pixel vs MV) | **policy stacking**, not multiplicative |
| us × CoPE-VideoLM | none (different representation layer) | different (we use pixel diff, they use learned Δ-tokens) | clean in principle; future work |
| us × FastV | none (encoder vs decoder) | none | **multiplicative in cost model**, measured TBD |
| us × EVS | partial (both exploit temporal patch redundancy) | partial (static-patch pruning vs raw-patch run-length redundancy) | comparator first; composition likely overlaps |
| us × FastVID | partial (we encoder-side, they post-encoder-temporal) | partial (both address temporal redundancy) | likely interacts; not cleanly multiplicative |
| us × VisionZip | none (encoder vs post-encoder-intra-frame) | none | clean composition |
| us × SparseVLM | none (encoder vs decoder) | none | clean composition |
| us × VLCache | complementary (we encoder-side, they KV-reuse) | none | clean composition |
| us × STTM | partial (both address temporal redundancy post-ViT) | partial (directed matching vs pixel-diff) | worth measuring; STTM handles remaining temporal redundancy we don't eliminate |
| us × T3S | complementary (we reduce per-frame cost, T3S packs more subsequences) | none | clean; T3S is a wrapping strategy, not a model change |

"Composes" claims are first-order hypotheses; only phase 1.32 FastV
measurement will turn one row from speculation into evidence.
