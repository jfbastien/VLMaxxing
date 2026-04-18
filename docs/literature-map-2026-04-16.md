# Literature Map — Post-CodecSight Repositioning

Date: 2026-04-16
Parent: [PLAN.md](../PLAN.md)
Sibling: [research-strategy-post-codecsight.md](research-strategy-post-codecsight.md)
Prior map: [literature-map.md](literature-map.md) (pre-CodecSight)

This document updates the research-position map after CodecSight
(2604.06036v3) and CoPE-VideoLM (2602.13191). Whitepaper reproduction
remains the methodological foundation. The broader **candidate paper
slot**, if later phase work (phase 1.20 TOMATO N=30, phase 1.21 MVBench
N=30, Stage E Track B) lands, is a training-free, codec-guided
temporal routing method targeting a better quality–compute Pareto
frontier on temporal-reasoning benchmarks with real measured skipped
compute. Several axes of that claim (Track B, projector-consistent
sparse execution, composition) are currently **target claims, not
current evidence** — do not cite them as proven work.

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
- **Our comparison point** (directional only, not a paper-facing
  head-to-head claim): our TOMATO motion holdout result at 26.7%
  (4/15) is numerically near CoPE's reported TOMATO 28.3%, but
  this comparison comes from a tiny motion-focused slice vs CoPE's
  full-benchmark number on a different model family, and should
  not be cited as a method comparison. Audit caveat (codex,
  2026-04-16): the benchmark scope and method family differ too
  much for paper-grade equivalence.
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

Four-axis taxonomy (for the paper's related-work table; authoritative
table in [related-work-table.md](related-work-table.md)):

| Method | Reduction stage | Signal source | MLX status |
|---|---|---|---|
| **FastV** (ECCV 2024 Oral) | Decoder-internal (layer K) | Intra-modal attention | Algorithmically orthogonal; implementation on MLX is non-trivial because fused SDPA does not currently expose attention scores (requires mlx-vlm fork) |
| **FrameFusion** (2025) | Post-encoder; video-native | Similarity + importance (two-stage) | torch; MLX port TBD. Strongest video-native comparator |
| **VisionZip** (CVPR 2025) | Post-encoder | CLS-attention | torch only, Qwen2-VL port exists, Qwen2.5-VL TBD |
| **SparseVLM** (ICML 2025) | Decoder-internal (every LLM layer) | Cross-modal (text-visual attention) | torch only (HF hooks per layer) |
| **FastVID** | Post-encoder, spans temporal groups | Density clustering | torch only (hardwired into lmms-eval fork of `modeling_qwen2_5_vl.py`) |
| **VScan** (ICML 2025) | Two-stage: ViT token merge + LLM mid-layer prune | Intra-modal (ViT) + cross-modal | torch only, modifies both forward passes |
| **VLCache** | Encoder-cache + KV-cache reuse | Cross-request similarity | SGLang only |

**FrameFusion** (added 2026-04-16 per ChatGPT audit): the most
directly-adjacent *video-native* within-frame reduction method. It
combines similarity-based token merging with importance-based pruning
and reports 70% vision-token reduction with 1.6–1.9× end-to-end
speedup and small average performance loss across multiple LVLMs.
Because our method also addresses temporal redundancy (across frames),
FrameFusion partially overlaps our signal axis — we likely cannot
claim strict orthogonality. Include in the paper's related-work
comparison table.

All six listed methods run as training-free inference-time policies
on top of frozen VLMs. (FastVID adds dynamic density clustering at
inference time; no fine-tuning is required.) Verify per-paper before
citing in a paper table.

Our slot on the same axes:
`(Post-encoder, Pixel/frame-domain, Training-free, Cross-frame)` —
genuinely orthogonal to every method above on the signal-source axis
(they all use attention; we use frame-domain pixel statistics) and
orthogonal to FastV/SparseVLM/VScan/VLCache on the stage axis (we
prune before they see tokens).

Headline compute-reduction numbers (orientation only — numbers come
from heterogeneous model stacks and benchmarks, not a head-to-head
comparison; MVBench/TempCompass specific figures are NOT publicly
reported for any of these — all evaluated on VideoMME, EgoSchema,
LLaVA-1.5 image VQA):

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

## Candidate paper slot (target, not current claim) — round-17 reframe

> **Training-free multiplicative end-to-end speedup for video VLMs
> via temporal feature reuse composed with novelty-pruning, measured
> on VideoMME with Gemma 4-E4B-4bit, validated on temporal-reasoning
> benchmarks (TOMATO, MVBench) with Qwen 2.5-VL-7B-4bit. One paper,
> co-authored with Sam, results-first with method content in an
> appendix.**

The paper's SOTA-facing claim is the **multiplicative big-number
speedup** (lane B). The routing / bounded-staleness method content
(lane A) is supporting evidence that explains *why* the speedup
is correct and not a content-specific lucky shot.

Six **target claims** (NOT yet evidence):

1. Multiplicative end-to-end speedup ≥ 1.8× on VideoMME with Gemma
   via novelty-pruning alone (phase 1.51 pending). THE headline.
   **[REPRODUCTION TARGET, not a Sam whitepaper claim.]** Sam's
   whitepaper reports 5.4× prefill and 4.2× e2e (Qwen 32f talking-
   head) on larger models / different regimes; 1.8× was our
   internal preregistered e2e gate for "the mechanism delivers a
   real multiplicative win on our regime." Arithmetic-ceiling
   analysis shows 4B-class / 8-frame is bounded to ≤1.46× at
   kr=0.10 aggregate; 32-frame lifts the ceiling (short-32 earned
   1.663×, medium-32 1.565×, long-32 1.234× — all at Δacc=-0.10).
2. Multiplicative composition: temporal reuse + novelty-pruning
   compose as measured (phase 1.52 pending). Tests whether Sam's
   4–5× Gemma 4 26B composition transfers to Gemma 4 4B on M3 Air.
3. Routing quality: codec-derived pixel-diff proxies are valid
   routing signals (phase 1.36 oracle DONE — r=0.233 to r=0.504,
   content-conditional, weak-to-moderate).
4. Bounded-staleness + concentration-aware routing repairs
   temporal failures on TOMATO + MVBench (phase 1.20/1.21 DONE
   at N=30; phase 1.37B halo-veto RETIRED 2026-04-17 as
   preregistered null — NO-LIFT on TOMATO dev, HURTS on MVBench dev).
5. VideoMME validation on Qwen (phase 1.41 pending asset unpack).
6. Real sparse execution converts the proxy gain into measured
   speedup (Track B, claim 5 in the matrix). Prospective; the
   one-paper-gate requires at least one wall-clock measurement.

### Current evidence level (2026-04-16)

| Claim | Status |
|---|---|
| Training-free temporal reuse on MLX has a held-out Pareto signal | **Credible early signal** (phase 1.12.B + phase 1.12 TOMATO) |
| Base policy `max_abs(8,32) static+shifted age=4` beats dense-6 on MVBench motion holdout at N=30 | **PASSED** (phase 1.21: cached=0.600@4.06, Pareto win vs dense-6=0.567@6; clean tree) |
| Adding `sticky_window=4` ties dense-8 at N=30 | **PASSED** (phase 1.21: cached=0.633@4.49, 56% of dense-8 budget; dirty tree, supplementary) |
| TOMATO motion holdout cached ties dense-8 at 44% budget | **PASSED at N=30 (phase 1.20, clean tree commit 42b06eb, 0.333@3.55)** |
| Cross-benchmark policy transfer is asymmetric | **Real** (TOMATO→MVBench cell B is strong; MVBench→TOMATO is weak) |
| Sticky-dynamic is benchmark-conditional (hurts TOMATO dev, helps MVBench holdout) | **Real mechanism finding** (phase 1.26 + 1.26.B); supports budget-placement theory |
| Projector-group completion repairs failures | **Pending** — on our Qwen 2.5-VL stack, `BLOCK_SIZE=28` is already at projector granularity, so the mechanism semantics needs rescoping |
| "More frames at same budget" coverage benefit | **Rejected on off-budget probe** (phase 1.28 ran at higher budget than preregistered); true iso-budget test pending |
| Real skipped compute (wall-clock / FLOP) | **Not measured** — Track B unbuilt |
| Composition with FastV multiplies gains | **Not measured** — mlx-vlm fork required |

## What's off-limits now

- "codec metadata helps VLMs" as a contribution — CodecSight owns it.
- "learned codec-native representation" — CoPE owns it.
- "attention-score token pruning" — FastV / VisionZip / SparseVLM
  own it.
- "long-horizon memory for streaming video" — StreamingVLM et al.
  own it.

We target the intersection: *training-free*, *temporal-axis*, *temporal
reasoning benchmarks*, *Pareto frontier*, *real skipped compute*. The
plan (phases 1.25–1.33) is the set of experiments that prove or
reject each of the five claims above.

## References with stable URLs

All links confirmed reachable. Per-paper verified numbers are in
the machine-friendlier [`related-work-table.md`](related-work-table.md);
use that file as the authoritative reference for paper-facing
citations.

- CodecSight: https://arxiv.org/abs/2604.06036
- CoPE-VideoLM: https://arxiv.org/abs/2602.13191
- FastVID: https://arxiv.org/abs/2503.11187
- FlashVID: https://openreview.net/forum?id=H6rDX4w6Al
- FrameFusion: https://arxiv.org/abs/2501.01986
- VScan: https://arxiv.org/abs/2505.22654
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
- STTM: https://arxiv.org/abs/2507.07990 (ICCV 2025, training-free post-ViT temporal merge)
- T3S: https://arxiv.org/abs/2511.17945 (training-free temporal sampling wrapper)
- AdaCache: https://openreview.net/forum?id=DyyLUUVXJ5 (adaptive caching for video diffusion)
- VLCache: https://arxiv.org/abs/2512.12977
- MPEG VCM: https://mpeg.chiariglione.org/standards/exploration/video-coding-machines.html
