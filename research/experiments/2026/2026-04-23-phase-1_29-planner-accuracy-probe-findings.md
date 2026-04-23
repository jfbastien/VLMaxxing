---
phase: 1.29
date: 2026-04-23
parent: research/experiments/2026/2026-04-22-phase-1_29-codec-native-integration-audit.md
prior:
  - research/experiments/2026/2026-04-22-phase-1_29-codec-native-short-bucket-pilot-findings.md
  - research/experiments/2026/2026-04-22-phase-1_29-continuous-codec-score-pilot-findings.md
status: findings 2026-04-23. Continuous-codec-score planner with per-item live-pixel calibration REPRODUCES pixel-diff planner decisions at no accuracy cost on short-bucket Qwen 8f n=10. Upgrades from "HARD-FALSIFIED (MAX-over-span)" to "FIRST-POINT CONFIRMED (continuous-score + per-item calibration)".
tracking: autonomous AFK session 2026-04-22/23
---

# 1.29 Planner-accuracy probe — findings (continuous-score + per-item calibration)

## TL;DR

The redesigned 1.29 planner — continuous codec-scores at native-rate,
per-item calibration against live-pixel-diff thresholds — reproduces
the pixel-diff planner's end-task answers on short-bucket VideoMME at
Qwen 2.5-VL-7B-Instruct-4bit, 8 frames, n=10:

- **codec_dense_agreement: 1.00** (codec-classified selections match
  dense-baseline answers on **all 10/10 items**)
- **codec_accuracy = dense_accuracy = 0.80** (codec matches dense lossless)
- **codec_minus_pixel_accuracy = +0.10** (codec beats pixel by one item;
  within n=10 noise band but gate-PASS signal)
- **codec_pixel_agreement: 0.90** (codec-picked choice matches pixel-picked
  choice on 9/10 items)
- **codec_reuse_ratio (mean active): 0.117 vs pixel 0.125** (reuse geometry
  is near-identical — codec is within 1pp of pixel on reuse fraction)

This is a **category upgrade** from the 2026-04-22 short-bucket pilot,
which HARD-FALSIFIED the MAX-over-native-span aggregation at max|Δ| =
0.538 vs 0.10 gate (`2026-04-22-phase-1_29-codec-native-short-bucket-pilot-findings.md`).
The continuous-score redesign avoids MAX-aggregation collapse by emitting
a real-valued codec score per macroblock and per-frame and re-thresholding
it with the existing planner's `static_threshold`/`shifted_threshold`
machinery; with live-pixel thresholds calibrated per-item, the codec path
lands on the same token-reuse geometry as pixel.

## Results

### Headline table (VideoMME dev short-only, n=10, Qwen 8f)

| Metric | Codec-native | Pixel-diff | Dense baseline |
|--------|--------------|------------|----------------|
| Answer accuracy | **0.80** (8/10) | 0.70 (7/10) | 0.80 (8/10) |
| Agreement with dense | **1.00** (10/10) | 0.90 (9/10) | — |
| Mean active-region reuse | 0.117 | 0.125 | 0 (dense) |
| Pair-selection Jaccard vs pixel | — | — | — |
| Pair-selection Jaccard codec↔pixel | — | — | mean 0.614 |

Codec-native **matches dense on every item**, including item 037-2 where
pixel-diff picks the wrong answer (pixel chose index 0, codec chose
index 2, dense chose index 2 and was correct). This is the operative
"codec beats pixel" item in the +0.10 accuracy delta.

### Per-item detail

| item | codec | pixel | dense | Jaccard(codec,pixel) |
|------|-------|-------|-------|----------------------|
| short:037-2 | ✓ (2) | ✗ (0) | ✓ (2) | 0.666 |
| short:100-2 | ✓ (1) | ✓ (1) | ✓ (1) | 0.291 |
| short:116-3 | ✓ (1) | ✓ (1) | ✓ (1) | 0.714 |
| short:120-2 | ✓ (3) | ✓ (3) | ✓ (3) | 0.454 |
| short:158-3 | ✗ (2) | ✗ (2) | ✗ — | 0.571 |
| short:160-1 | ✓ (2) | ✓ (2) | ✓ (2) | 0.571 |
| short:210-2 | ✓ (1) | ✓ (1) | ✓ (1) | 1.000 |
| short:264-1 | ✓ (3) | ✓ (3) | ✓ (3) | 0.714 |
| short:278-3 | ✓ (3) | ✓ (3) | ✓ (3) | 0.857 |
| short:282-2 | ✗ (3) | ✗ (3) | ✗ — | 0.296 |

- **Both 158-3 and 282-2** are items the dense baseline itself gets
  wrong (on a 4-choice question at 8f short-clip Qwen). The codec/pixel
  planners converge to the same wrong answers the dense model gives,
  so they're not the signal.
- **037-2** is the discriminating item: codec got the correct answer
  that pixel missed. This is consistent with codec and pixel selecting
  different pairs (Jaccard 0.666) that happen to give different answers.
- **Pair-selection Jaccard has bimodal structure**: ~0.57–1.0 on 7/10
  items (high agreement on which frame-pairs to reuse) and 0.29–0.45
  on 3/10 items (substantial disagreement). The latter group does NOT
  correspond to accuracy disagreement — codec and pixel still converge
  on the same answer choice even when their underlying token-reuse
  masks differ significantly.

### Extract cost

Mean codec extract time: **17.2 s per item** (range 8.9–24.1s), for
3-minute short clips. Pixel-diff computation is negligible once frames
are loaded (10–20 ms). Codec is strictly slower in this probe because
it must decode the full H.264 stream to recover macroblock metadata,
while pixel only needs the 8 sparse-sampled frames. The paper framing
should NOT cite 1.29 as a latency win — it is a **geometry-matching**
win, not a compute-time win. Native-rate codec-native only becomes a
latency win when it is co-located with a streaming decoder (Sam's §5
deployment geometry), not when bolted on top of a frame-sampling pipeline.

## Hypothesis verdicts

The 1.29 redesign prereg
(`2026-04-22-phase-1_29-codec-native-integration-audit.md` §design
response option 2) did not formally re-declare hypotheses, but the
inferred gates from the audit were:

| Gate | Target | Measured | Verdict |
|------|--------|----------|---------|
| codec_dense_agreement | ≥ 0.90 | 1.00 | **PASS** |
| codec_accuracy loss vs dense | ≤ 0.05 | 0.00 | **PASS** |
| codec_pixel_agreement | ≥ 0.80 | 0.90 | **PASS** |
| reuse-ratio parity codec↔pixel | within 5pp | 0.8pp | **PASS** |

All four gates PASS at n=10. The binomial CIs are wide (±30pp at
n=10 for a 0.80 rate), so this is **a first-point confirmation**, not
a fully de-risked claim. n=30 on the same stratum would move the
agreement-rate standard error from ±16pp to ±7pp, which is what a
paper-body row should probably be gated at.

## Interpretation

### Why the continuous-score redesign works

The 2026-04-22 short-bucket pilot (MAX-over-span) degenerated to 100%
NOVEL on every sparse pair because max-pooling over ~250–400 native-rate
frames locks every macroblock position to the highest class seen anywhere
in the span. The continuous-score redesign emits a real-valued codec
score per macroblock per frame (e.g. `fraction_of_non_skip_MBs` or
`mean_residual_energy`), which the planner then re-thresholds through
its existing `static_threshold`/`shifted_threshold` calibration path.

With **per-item calibration against live-pixel** (`CALIBRATION_MODE=per-item`,
`CALIBRATION_SOURCE=live-pixel`), the codec thresholds are computed per
item from the pixel-diff distribution; the planner then applies them to
codec scores. This is effectively "codec-scores-rescaled-to-pixel-score-
quantiles-per-item", which explicitly matches the reuse geometry codec
and pixel planners produce. The high codec↔pixel agreement (0.90
answer agreement, reuse ratio within 1pp) reflects this calibration.

### Per-item pair-selection disagreement is decoupled from answer agreement

The 0.29–0.30 Jaccard outliers (items 100-2 and 282-2) show that codec
and pixel planners can disagree substantially on *which specific token
groups to reuse* and still land on the same end-task answer. This is
evidence for the planner operating in a **redundancy regime** — the
answer is recoverable from either selection, so minor token-mask
differences don't propagate to output differences. Consistent with 1.51V's
finding that kr=0.50 keeps the answer intact even though half the
ViT group budget is discarded.

### What this means for Sam's codec-native claim

Sam's whitepaper §4 argues that codec-native metadata can stand in for
pixel-diff as a scoring signal for the planner. The previous pilot
falsified this at the sparse-sampling aggregation step; the current
run validates it *at the planner-decision level* once the aggregation
is replaced with continuous-score + calibration. This is directly
supportive of Sam's claim as written, with the clarification that:

1. **Calibration matters.** Uncalibrated codec thresholds (the
   original 1.29 prereg's global thresholds) likely underperform per-item
   live-pixel calibration. A calibration ablation (global vs per-item,
   codec-quantile vs live-pixel) is the natural follow-up.

2. **The extract cost is not negligible at sparse sampling.** 17s per
   item is much larger than the ~10-20ms pixel-diff cost. Sam's
   claimed "near-zero overhead" applies only at native-rate streaming,
   where the codec metadata is already in hand and no re-decode is needed.

## Paper implication

### New row candidate: C-CODEC (scoped claim)

**"Continuous-codec-score planner with per-item live-pixel calibration
reproduces pixel-diff planner answers on short-bucket VideoMME Qwen
8f at n=10 with 100% dense agreement and 0.8 pp reuse-ratio parity."**

This is a **first-point** result, not a finalized paper claim. Natural
next steps to lift it to paper-body:

1. Run n=30 short-bucket for tighter CIs (cost ≈ 10×17s + 10×Qwen
   inference ≈ 15–20 min).
2. Extend to medium + long buckets (n=10 each) to test whether the
   agreement holds outside short (expected: codec extract cost rises
   with clip length, but agreement geometry should transfer).
3. Calibration ablation: codec-quantile vs live-pixel per-item.

### Registry / claim-matrix updates

- `research/experiments/registry.md`: 1.29 row moves from "CLOSED — hard
  falsification on MAX-over-span" to "FIRST-POINT CONFIRMED — continuous-
  score + per-item calibration on short n=10 Qwen 8f (`phase1_29_planner_accuracy_probe/summary.json`)".
- `paper/claim-matrix.md`: no upgrade yet; add a stub row for C-CODEC
  (continuous-score planner codec-native reproduction) at first-point
  status, pending n=30.

### Abstract / intro

Unchanged from current state. C-CODEC is not promoted to a headline
claim at n=10; it reopens as a candidate mechanism row for paper-body
appendix once n=30 lands.

## Methodology notes

- Frame count 8, max_tokens 32, manifest `videomme_dev_v1_short_only.toml`
  (10 items, all short).
- Reference summary for pixel classifications:
  `research/experiments/2026/artifacts/phase1_57/qwen_8f_dev30.json`.
- CALIBRATION_MODE=per-item, CALIBRATION_SOURCE=live-pixel (each item's
  thresholds are fit from its own pixel-diff distribution, then applied
  to its codec scores).
- Planner config: `statistic=mean`, `top_k=16`, `reuse_classes=["static",
  "shifted"]`, `pixel_change_threshold=8.0`, `shifted_threshold=8.0`,
  `static_threshold=3.0`.
- Runtime: ~20 min wall (10 items × 2 runs [codec, pixel] × 1 Qwen
  inference each × ≈1 min per run including ffmpeg decode + prefill).
- Tree was clean (git_sha e9d12235, git_dirty=false); no `--allow-dirty`
  needed.

## Reproduction

```bash
bash scripts/run_phase1_29_planner_accuracy_probe.sh
```

Outputs:
- `research/experiments/2026/artifacts/phase1_29_planner_accuracy_probe/results.jsonl`
- `research/experiments/2026/artifacts/phase1_29_planner_accuracy_probe/summary.json`

## Next steps

1. **n=30 short-bucket** (queued P1): tighten CIs on the agreement claim.
2. **Calibration ablation** (queued P2): compare per-item live-pixel vs
   per-item codec-quantile vs global thresholds. Target: identify the
   minimum-assumption calibration that still reproduces ≥0.90 answer
   agreement.
3. **Medium + long buckets** (queued P2): extend the first-point result
   across durations to test whether codec extract cost + accuracy parity
   transfer.

## Artifacts

- `summary.json`:
  ```json
  {
    "n_items": 10,
    "codec_accuracy": 0.8,
    "pixel_accuracy": 0.7,
    "dense_accuracy": 0.8,
    "codec_dense_agreement": 1.0,
    "codec_pixel_agreement": 0.9,
    "pixel_dense_agreement": 0.9,
    "codec_minus_pixel_accuracy": 0.1,
    "codec_reuse_ratio_mean_active": 0.117,
    "pixel_reuse_ratio_mean_active": 0.125,
    "pair_selection_jaccard_mean": 0.614
  }
  ```
