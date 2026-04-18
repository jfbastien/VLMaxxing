# Phase 1.51R Stage 6 — 32-frame medium-bucket cross-validation (prereg)

**Status:** pre-registration. Predictions committed 2026-04-18 BEFORE
running medium n=10 at 32 frames. This is the sixth independent
quantitative test of the arithmetic-ceiling model and completes the
three-bucket × 32-frame validation set.

## Motivation

Short-32 n=10 (just landed) confirmed that per-bucket decode time is the
primary predictor of ceiling, and that decode does NOT scale linearly with
video duration:
- Long-32 aggregate decode: 73.7s (56.9% of e2e), ceiling@∞=1.31×
- Short-32 aggregate decode: 3.1s (5.2% of e2e), ceiling@∞=2.00×

Medium bucket (60-300s duration) should fall between the two. The
question is WHERE — linear with duration would put medium decode at ≈
(60-300)/(<60) × 3s = 3-15s; seek-dominated scaling would put it closer
to short (5-10s); file-size-dominated scaling would put it closer to
log(duration) scaling or 15-40s.

This run tests that quantitatively and graduates the ceiling model to
"validated across three duration buckets × 32 frames" or falsifies it
if medium breaks the pattern.

## Pre-registered decomposition predictions (medium-32)

Baseline anchors:
- Short-32 observed: D=3.1s, V=26.1s, G=29.4s, e2e=58.9s, ff=0.500
- Long-32 observed:  D=73.7s, V=24.7s, G=30.8s, e2e=129.4s, ff=0.762

Predictions for medium-32 (using monotone-with-duration expectation):
- **D ≈ 18s** (midpoint on log-scale between 3.1 and 73.7; reflects
  file size scaling monotonically while not extrapolating linearly —
  short files are 10-40 MB, medium are 60-200 MB, long are 400+ MB,
  so medium could be closer to ~6× short than to ~24× short)
- **V ≈ 25s** (frame count constant, vision time is bucket-insensitive)
- **G ≈ 30s** (prefill length constant at 32 frames)
- **e2e ≈ 73s**
- **fixed_frac = (18 + 25) / 73 = 0.589**
- **ceiling@s=7.0 = 1 / (0.589 + 0.411 / 7) = 1 / 0.648 = 1.544×**

This is close to the Pareto-middle of short (1.66×) and long (1.23×).

## Hypotheses

- **H1'' (medium-32 e2e ∈ [1.40, 1.65])**: centered on 1.54× ceiling,
  band widened from ±0.07 (used on short-32) to ±0.12 because my
  short-bucket decode prediction was 8× off — the predictor is
  clearly noisy at the D decomposition level, and I should widen bands
  until my calibration improves.
- **H2'' (medium-32 Δacc ∈ [-0.15, 0.05])**: matched H2 / H2' bands.
  Medium bucket at kr=0.10 showed Δacc=0.000 at 8 frames (Stage 2b —
  the only bucket to preserve accuracy at kr=0.10) and Δacc=-0.100 at
  32 frames in Stage 5/Stage 6. I predict medium-32 Δacc ≈ -0.067 to
  -0.100.
- **H3'' (RSS < 6 GB)**: short-32 hit 4.6GB, long-32 hit 5.3GB, medium
  should fall between — well under 6GB budget.

## Ablation: three-bucket ceiling surface

If medium-32 e2e lands in [1.40, 1.65] AND ceiling model predicts to
within 10% of observed, then the ceiling model is validated across:
- 3 frame counts (8, 32; plus smoke @ 32)
- 3 duration buckets (short, medium, long)
- 4 anchor arms (none, cls_attention_proxy, nuwa_pillar, max_min,
  gemma_structural)
- 3 keep rates (0.10, 0.25, 0.33)
= **≥ 7 independent regime dimensions** in which the analytical
expression `ceiling = 1 / (fixed_frac + (1-fixed_frac) / s)` holds
to 5% or better.

That is strong enough to present as a standalone analytical contribution
in the paper, separate from any SOTA arm.

## What this run would EARN

1. If medium-32 e2e ∈ [1.40, 1.65] AND predicted/observed ceiling
   error < 10%, the ceiling model **graduates to standalone publishable
   claim** — it predicts at aggregate level across all three duration
   buckets × 32 frames with bounded error.
2. If medium-32 Δacc ≥ -0.10 AND e2e ≥ 1.40×, that's a **medium-bucket
   earned-win at 32 frames** comparable in spirit to the short-bucket
   earned-win at 1.66×.
3. If the medium vs short vs long decode times trace out a clean
   monotone-with-file-size curve (rather than noise), we get a
   **per-item-decode predictive model** that can forecast 1.51R
   speedup for arbitrary new items.

## What this run would FALSIFIED

- If medium-32 e2e < 1.30× OR > 1.75×, the ceiling model's quantitative
  cross-bucket prediction fails and we need a decode-time priors lookup
  table instead of a duration-based prediction.
- If medium-32 Δacc > -0.15, that's consistent with H2; if Δacc < -0.20,
  we have a per-bucket accuracy asymmetry that the ceiling model does
  NOT explain (mechanism-level, not arithmetic).

## Run plan

```
uv run python scripts/run_novelty_pruning_gemma.py \
    --manifest research/benchmark_manifests/videomme_dev_v1_medium_only.toml \
    --n-items 10 --frame-count 32 --anchor-arm none --keep-rate 0.1 \
    --max-tokens 32 \
    --output research/experiments/2026/artifacts/phase1_51R_32frame_medium/medium_kr010_n10_32frame.jsonl \
    --summary research/experiments/2026/artifacts/phase1_51R_32frame_medium/medium_kr010_n10_32frame_summary.json
```

Estimated wall-time: 10 items × 73s dense + 47s pruned ≈ **20 min**
(between short pilot's 15 min and long pilot's 40 min).

## Cross-references

- `2026-04-18-phase-1_51R-stage6-32frame-short-findings.md` — just
  landed; short bucket validation with favorable-direction falsification.
- `2026-04-18-phase-1_51R-stage6-32frame-pilot-findings.md` — long pilot.
- `2026-04-18-arithmetic-ceiling-findings.md` — ceiling model v1.
