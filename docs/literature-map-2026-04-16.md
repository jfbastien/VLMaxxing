# Literature Map — Post-CodecSight Repositioning

Date: 2026-04-16
Parent: [PLAN.md](../PLAN.md), [execution-plan-round-7.md](execution-plan-round-7.md)
Prior map: [literature-map.md](literature-map.md) (pre-CodecSight)

This document is the research-position map after CodecSight (2604.06036v3)
and CoPE-VideoLM (2602.13191) landed on arXiv. They fill the systems and
model slots in the video-VLM efficiency landscape that our project was
implicitly claiming. The plan is no longer "reproduce the whitepaper";
it is "a training-free, codec-guided temporal routing method that
improves the quality–compute Pareto on temporal reasoning benchmarks,
with real sparse execution."

## Four-axis taxonomy of video-VLM efficiency

Every efficiency method in this space reduces cost by one of four
mechanisms. Clean separation is what the paper needs.

| Axis | Prune layer | Signal | Training |
|---|---|---|---|
| **Temporal (across-frame)** — *our slot* | pre-ViT or post-ViT-pre-LLM | pixel/codec diff of frames | training-free |
| **Intra-frame visual token reduction** | post-ViT-pre-LLM or inside LLM layers | attention scores, CLS scores, dual importance | training-free (FastV/VisionZip/SparseVLM) or trained (FastVID) |
| **Long-horizon memory** | LLM KV cache | recency, importance, attention fading | training-free (StreamingLLM) or trained |
| **KV compression (bits/entry)** | LLM KV cache | quantization | training-free (TurboQuant/PolarQuant) |

The paper positions us exclusively in the first row, training-free,
benchmark-validated on temporal-reasoning tasks (not anomaly F1).

## Nearest neighbors and how we stack

### CodecSight (2604.06036v3) — nearest SYSTEMS neighbor

**Verified 2026-04-16** via direct paper read.

**Signal** (Eq. 1–4):

- `V_t^m = ||v_t^m||` — L2-norm of block-level motion vector for
  codec block m
- `R_t^m = Σ |B_t - B̂_t|` — residual energy (sum absolute difference)
- `M_t(i) = V_t(i) + α · R_t(i)` — patch-level motion mask aggregated
  from codec blocks overlapping ViT patch i
- `dynamic(i) = [M_t(i) ≥ τ]` — binary classification per patch
- **Default α=0**: NVDEC hardware decoders expose MVs but not
  residuals at runtime, so the production path is MV-only.

**Sticky-dynamic** (verbatim mechanism): a GOP-level accumulation
rule. Once patch i is marked dynamic in ANY P- or B-frame within a
GOP, it stays marked dynamic for ALL subsequent frames in that GOP.
Mask resets at the next I-frame. Purpose: prevent oscillation and
handle cases where a region in motion will likely still be relevant
in frame t+1 even if the codec momentarily assigns zero MV due to
quantization or reference-frame effects.

**Projector-group completion** (verbatim rule): if any ViT patch
within a projector spatial group is dynamic, ALL patches in that
group are retained for encoding. For Qwen 2.5-VL (2x2 spatial merge):
snap the dynamic mask to 2x2 aligned blocks. If any of the 4 patches
in a tile is dynamic, all 4 pass through ViT and the projector
multiply. Else the whole tile is skipped.

**Verified numbers** (UCF-Crime streaming anomaly, video F1):

| Configuration | Speedup | InternVL3 F1 |
|---|---|---|
| Baseline (no CodecSight) | 1.00× | 0.89 |
| Token pruning only | 2.61× | 0.87 (−0.02) |
| KVC refresh only | 1.64× | 0.79 (−0.10) |
| Combined (pruning + refresh) | 3.87× | 0.81 (−0.08) |
| End-to-end (incl. I/O) = **2.97×** headline | 2.97× | 0.81 |

Qwen3-VL: 0.81 → 0.81 with CodecSight (zero F1 drop at matched
operating point, likely because Qwen3-VL baseline is already weaker).

**Key design lesson for us**: ablation confirms *front-end pruning is
the safe lever, KV refresh is the risky lever*. Our work is on the
safe lever; we have deliberately avoided KV refresh. That positioning
is now a paper-framing point, not an accident.

**Motion vector extraction path in CodecSight**: NVDEC hardware
decoder only. "~600 lines of Python" around NVDEC. MV extraction cost
folded into ~50ms total system overhead (~3.9-4.5% of optimized
latency). MV extraction is essentially free on their platform.

**Does not cover**: TOMATO, TempCompass, or MVBench motion-heavy
temporal QA tasks. Our project sits exactly in this gap.

**Stacking**: policy stacking, not naive multiplicative speedup. Both
methods attack "decide what not to encode" around the ViT. The right
framing is: our planner could become a *better training-free policy*
inside a CodecSight-like harness, evaluated on temporal reasoning
rather than anomaly F1. Sticky-dynamic and projector-group completion
are direct borrowings we should implement.

**MLX parity problem**: CodecSight uses NVDEC; we're on Apple Silicon
MLX with no equivalent hardware-decoder-exposed MV API. Options:
(1) extract MVs via PyAV from the compressed H.264 container (slower
but works); (2) approximate MVs via optical flow (more expensive);
(3) keep pixel-diff proxy and sacrifice the deployability claim. Our
phase 1.29 will prototype PyAV MV extraction.

### CoPE-VideoLM (2602.13191) — nearest MODEL neighbor

- Learned codec-aware representation: I-frames go through frozen
  vision encoder; P-frames become compact 8 Δ-tokens (4 motion + 4
  residual) via a trained MLP + motion transformer + residual
  ResNet-18 + residual transformer (all jointly trained). Pre-training
  stage aligns Δ-tokens to the RGB encoder's embedding space.
- **Verified numbers (phase 1.23 research, 2026-04-16)**:
  - TTFT: 86.2% reduction (0.33s vs 2.39s) at 1 keyframe/GOP + 7
    P-frames/GOP vs 64-frame dense
  - Token reduction up to 93% at that operating point
  - **TOMATO: 28.3%** (CoPE) vs **24.9%** (LLaVA-Video-7B baseline)
    — +3.4pp gain with trained Δ-encoder
  - **MVBench overall: 61.9%** (CoPE) vs 58.6% baseline; no motion
    subset breakdown in accessible paper sections
  - TempCompass: 60.3% → 62.4% at 1 keyframe/GOP
  - Matched-keyframe table (not matched-token): 65.5% vs 60.4% on
    PerceptionTest at 1 keyframe/GOP (+5.1pp)
  - FPS coverage: 2 FPS still helps (+1.97% TempCompass, +1.87%
    MVBench); at 3 FPS both decline ~0.2pp (train/test mismatch)
- **Our comparison point**: our TOMATO motion holdout tie at 26.7%
  (4/15) is in the same ballpark as CoPE's TOMATO 28.3%. Achieving
  this **training-free, on MLX locally, without a codec encoder**
  is a credible positioning line. Caveat: N=15 vs CoPE's full
  TOMATO ≈1,484 items — accuracy is within CoPE's noise.
- **Training-free portability blocker**: phase 1.23 research
  confirms Δ-token construction falls apart without learned
  alignment weights. The motion/residual transformers' query
  tokens, ResNet-18, and pre-training stage are all learned; random
  or identity weights would produce tokens in an arbitrary space
  the LLM has never seen. You could extract raw MV/residual for
  frame selection or motion scoring signals, but not as additional
  LLM tokens without at minimum a learned linear alignment.
- **Stacking**: clean in principle, different layer. They change the
  representation; we change the routing/refresh policy. A future
  hybrid (I-frames dense, P-frames codec-tokens, cached between) is
  a legitimate model-paper direction but NOT the next experiment.
- **Contrast**: CoPE is *trained*; ours is *training-free*. That is
  the position we hold against them.
- **What CoPE does NOT give us**: an explicit iso-token-budget
  comparison table (N CoPE-frames vs M dense-frames at identical
  total token count). They report fixed-keyframe density matches, not
  fixed-total-token matches. So our phase 1.28 iso-token experiment
  is a contribution, not a reproduction.

### Intra-frame token reduction — verified 2026-04-16

Four-axis taxonomy (for the paper's related-work table):

| Method | Reduction stage | Signal source | MLX status |
|---|---|---|---|
| **FastV** (ECCV 2024 Oral) | Decoder-internal (layer K) | Intra-modal attention | Trivially portable logic, but mlx-vlm fused SDPA hides scores → needs fork to expose |
| **VisionZip** (CVPR 2025) | Post-encoder | CLS-attention | torch only, Qwen2-VL port exists, Qwen2.5-VL TBD |
| **SparseVLM** (ICML 2025) | Decoder-internal (every LLM layer) | Cross-modal (text-visual attention) | torch only (HF hooks per layer) |
| **FastVID** | Post-encoder, spans temporal groups | Density clustering | torch only (hardwired into lmms-eval fork of `modeling_qwen2_5_vl.py`) |
| **VScan** | Multi-stage (ViT + LLM mid-layer) | Intra-modal (ViT) + cross-modal | torch only, modifies both forward passes |
| **VLCache** | Encoder-cache + KV-cache reuse | Cross-request similarity | SGLang only |

All are training-free except FastVID's density-clustering heuristic
which is also training-free.

Our slot on the same axes:
`(Post-encoder, Pixel/frame-domain, Training-free, Cross-frame)` —
genuinely orthogonal to every method above on the signal-source axis
(they all use attention; we use frame-domain pixel statistics) and
orthogonal to FastV/SparseVLM/VScan/VLCache on the stage axis (we
prune before they see tokens).

Headline compute-reduction numbers (MVBench/TempCompass specific
figures are NOT publicly reported for any of these — all evaluated
on VideoMME, EgoSchema, LLaVA-1.5 image VQA):

- **FastV**: 45% FLOPs reduction on LLaVA-1.5-13B, minimal accuracy
  drop
- **VisionZip**: ≥5% SOTA gain over prior art (their setting)
- **SparseVLM**: 54% FLOPs, 37% CUDA latency reduction, 97% accuracy
  retained on LLaVA-1.5-13B
- **FastVID**: 90%+ token pruning, ~98% accuracy retained, 7.1x
  prefill speedup on LLaVA-OneVision-7B
- **VScan**: 2.91x prefill speedup, 10x FLOPs reduction, 95.4%
  accuracy on LLaVA-NeXT-7B
- **VLCache**: 1.2x–16x TTFT speedup, 2–5% of tokens computed,
  accuracy on par with full recomputation

**Composition priority**:

1. **FastV** is the first-choice composition partner. Justification:
   - *Signal orthogonality*: pixel-domain vs attention-score.
   - *Stage orthogonality*: encoder-side vs decoder-internal.
   - *Minimum integration surface*: a few lines of MLX index
     arithmetic once scores are exposed; does not require touching
     the ViT or the projector.
   - *Published composability*: FastV is ECCV 2024 Oral with clean
     code; composition with upstream encoder changes is explicitly
     in-scope per the paper.
2. **FastVID** is the video-specific token-reduction baseline we must
   compare against (not compose with at first). Blocker: it's wired
   into a lmms-eval torch harness; porting to MLX is non-trivial
   (density clustering hook needs reimplementation).
3. **VisionZip / SparseVLM / VScan** — defer. All require torch or
   HF hooks unavailable on MLX.

### StreamingVLM / StreamMem / LiveVLM / V-Rex — long-horizon memory

- Long-horizon KV management; orthogonal axis to front-end reduction.
- Stacks very naturally with us; front-end compression + long-horizon
  memory is the right decomposition for real streaming systems.
- Not a competitor — a future composition partner.

### TurboQuant / PolarQuant — KV compression

- Fewer bits per cache entry. Orthogonal to fewer entries (our axis).
- Stacks cleanly. Our whitepaper already gestured at this.

### Historical / conceptual ancestors

- **Déjà Vu** (2506.14107) — learned inter-frame reuse + GPU compaction.
  Useful as a systems baseline and for compaction ideas.
- **Eventful Transformers** (2308.13494) — conceptual ancestor for
  "recompute only changed tokens." Training-free but inside the
  transformer layer, not at the ViT front-end.
- **CoViAR** (1712.00636) — classical compressed-video representation
  lineage. Good for historical framing in the paper intro.
- **MPEG VCM / JPEG AI** — long-term machine-first codec framing.

## Our defensible paper slot

> **A training-free, codec-guided temporal routing method that improves
> the quality–compute Pareto frontier for video VLMs by combining
> concentration-aware change detection, bounded staleness, and
> projector-consistent sparse execution. Validated on TOMATO,
> TempCompass, and MVBench motion-heavy subsets at matched fresh-token
> budget. Composes with within-frame token reduction (FastVID /
> VisionZip) for multiplicative gain.**

Five claims the paper must support:

1. codec-derived proxies are valid routing signals (pixel diff is one;
   MV-only will be the deployable second).
2. naive mean-diff + no refresh is too blunt on TOMATO-style brief
   semantically-critical change patterns.
3. sticky-dynamic + age-bounded + projector-group-complete planners
   repair hard temporal failures.
4. the saved budget can be spent on more frames, not just less latency
   (CoPE framing adapted to training-free).
5. real sparse execution (Track B) converts the proxy gain into
   measured speedup.

## What's off-limits now

- "codec metadata helps VLMs" as a contribution — CodecSight owns it.
- "learned codec-native representation" — CoPE owns it.
- "attention-score token pruning" — FastV / VisionZip / SparseVLM
  own it.
- "long-horizon memory for streaming video" — StreamingVLM et al.
  own it.

We claim the intersection: *training-free*, *temporal-axis*, *temporal
reasoning benchmarks*, *Pareto frontier*, *real skipped compute*. The
plan (phases 1.25–1.33) is the set of experiments that prove or
reject each of the five claims above.

## References with stable URLs

All links confirmed reachable; full citations pending research
subagent returns.

- CodecSight: https://arxiv.org/abs/2604.06036
- CoPE-VideoLM: https://arxiv.org/abs/2602.13191
- FastVID: https://openreview.net/forum?id=2xS4VtpApy
- VisionZip: https://arxiv.org/abs/2412.04467
- SparseVLM: https://arxiv.org/abs/2410.04417
- FastV: https://arxiv.org/abs/2403.06764 (CVPR 2024)
- Déjà Vu: https://arxiv.org/abs/2506.14107
- Eventful Transformers: https://arxiv.org/abs/2308.13494
- CoViAR: https://arxiv.org/abs/1712.00636
- TempCompass: https://arxiv.org/abs/2403.00476
- TOMATO: https://arxiv.org/abs/2410.23266 (original spec)
- StreamingVLM: https://arxiv.org/abs/2510.09608
- TurboQuant: https://arxiv.org/abs/2504.19874
- VLCache: https://arxiv.org/abs/2512.12977
- MPEG VCM: https://mpeg.chiariglione.org/standards/exploration/video-coding-machines.html
