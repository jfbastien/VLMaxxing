# Phase 1.51R Stage 6 — 32-frame short-bucket cross-validation (prereg)

**Status:** pre-registration. Predictions committed 2026-04-18 BEFORE
running short n=10 at 32 frames. If the ceiling model is correct at long-32
(1.6% error) and at 8-frame kr sweep (0.8–2.8% error), it should generalize
to short-32. This is the fourth independent quantitative test.

## Motivation

The 32-frame long pilot (n=10, kr=0.10, anchor=none) landed
aggregate e2e=1.234× with fixed_frac=0.762. H1 was falsified because
decode-bounded ceiling caps at 1.312×.

On short-bucket items, video decode time is much smaller (short items are
<60s while long items are 15+ minutes). Vision-encode and generate scale
with frame count (32 frames), not with video duration. Therefore fixed_frac
on short-32 should be **materially lower** than on long-32, and the
ceiling@s should be **materially higher**.

This run tests that prediction quantitatively.

## Pre-registered decomposition predictions (short-32)

Baseline: 8-frame short bucket observations (Stage 2b at kr=0.10, Task #88):
- short-8 fixed_frac ≈ 0.568, V/fixed ≈ 0.66, D/fixed ≈ 0.34 → short-8 D ≈ 0.19 (D/e2e ≈ 19%)
- short-8 G/e2e ≈ 0.43 (inverse of fixed_frac)

Under 32-frame regime:
- D scales with video duration, not frame count → **D absolute ≈ same** as 8-frame run
  - short-8 D ≈ D_per_video ≈ 20s typical (short video decode)
  - In practice 32-frame short may show slightly higher D due to more seek+decode
    overhead; conservative estimate 1.3× → D_short32 ≈ 26s
- V scales with frames → **V ≈ 4× the 8-frame V** in seconds
  - The smoke (long) showed V=23s at 32 frames; at 8 frames long had V≈8s
  - V/frame ≈ 0.7s, so V_short32 ≈ 32 × 0.7 = 22.4s
- G: prefill grows from 2048+text at 8 frames to 8192+text at 32 frames
  - Smoke + pilot long showed G_dense ≈ 30s at 32 frames
  - This is roughly constant across buckets at the same frame count
  - G_short32 ≈ 30s

Predicted short-32 absolute timings (dense):
- D: ~26s
- P: ~0.3s
- V: ~22s
- G: ~30s
- **e2e: ~78s** (vs long-32's 129s aggregate)

Predicted short-32 **fixed_frac = (26 + 0.3 + 22) / 78 = 0.619**.

Predicted ceiling at observed per-token s ≈ 6.78× (carrying over from long):

    ceiling@s = 1 / (0.619 + 0.381 / 6.78) = 1 / (0.619 + 0.056) = **1.481×**

Predicted **ceiling@∞ = 1 / 0.619 = 1.615×** — above H1 lower edge 1.5×.

## Hypotheses

- **H1' (short-32 e2e ∈ [1.40×, 1.55×])**: the ceiling-at-s model predicts
  1.48×, so the pre-registered band is ±0.07× around that point.
- **H2' (short-32 Δacc ∈ [-0.15, 0.05])**: same band as the Stage 2b short
  kr=0.10 finding (which was -0.100); no structural reason to expect a big
  shift under 32-frame regime.
- **H3' (RSS < 8 GB)**: smoke + long pilot stayed under 5.5 GB; short
  videos should be similar.

## Ablation: medium-32 (optional, enqueued only if short-32 completes)

Under medium-bucket assumption, D ≈ 2× short (medium videos are 60-300s vs
<60s) → D_med32 ≈ 50s → medium-32 e2e ≈ 102s → fixed_frac ≈ 0.71 → ceiling
≈ 1.32×.

Medium would be a gap-filler between short (1.48× pred) and long (1.25×
observed). If medium lands inside [1.28, 1.40], the ceiling model is
quantitatively validated across **all three duration buckets at 32 frames**.

## What this run would EARN

1. If short-32 e2e ∈ [1.40, 1.55], the ceiling model graduates to
   **cross-bucket + cross-regime quantitative prediction** (fourth
   validation, across two orthogonal regime shifts: frame count AND
   duration bucket).
2. If short-32 Δacc ≥ -0.10 AND e2e ≥ 1.40×, that's a **short-bucket
   earned-win at 32 frames** comparable in spirit to the 8-frame kr=0.33
   short-bucket Pareto-knee, at a higher operating point on speedup.
3. If the predictions land within 10% error across all buckets, the
   ceiling model is strong enough to publish as a **standalone
   analytical-ceiling result** independent of any specific SOTA claim.

## What this run would FALSIFY

- If short-32 aggregate fixed_frac ≫ 0.619, the D-scales-with-video-
  duration assumption is wrong — decode may actually scale with frame
  count too (e.g., seek-dominated decode).
- If short-32 e2e drops below 1.30×, either V/G ratio predictions are
  wrong or there's a regime-specific cost I haven't modeled.

## Run plan

```
uv run python scripts/run_novelty_pruning_gemma.py \
    --manifest research/benchmark_manifests/videomme_dev_v1_short_only.toml \
    --n-items 10 --frame-count 32 --anchor-arm none --keep-rate 0.1 \
    --max-tokens 32 \
    --output research/experiments/2026/artifacts/phase1_51R_32frame_short/short_kr010_n10_32frame.jsonl \
    --summary research/experiments/2026/artifacts/phase1_51R_32frame_short/short_kr010_n10_32frame_summary.json
```

Estimated wall-time: 10 items × 78s dense + 58s pruned ≈ **23 min** (same
ballpark as long pilot).

## Cross-references

- `2026-04-18-phase-1_51R-stage6-32frame-pilot-findings.md` — long pilot
  results (H1 falsified, H2 earned).
- `2026-04-18-arithmetic-ceiling-findings.md` — ceiling model v1.
- `2026-04-18-phase-1_51R-stage6-32frame-smoke-findings.md` — smoke
  predecessor.
