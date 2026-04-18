# Phase 1.51R Stage 7 — 32-frame short-bucket, gemma_structural × kr=0.33 (prereg)

**Status:** pre-registration. Predictions committed 2026-04-18 BEFORE
running. Self-enqueued experiment after Stage 6 cross-bucket
ceiling-validation surface closed.

## Motivation

Today's best results at 32 frames all show Δacc=-0.100:
- short-32 kr=0.10 anchor=none: e2e=1.663×, Δacc=-0.100
- medium-32 kr=0.10 anchor=none: e2e=1.565×, Δacc=-0.100
- long-32 kr=0.10 anchor=none: e2e=1.234×, Δacc=-0.100

Today's only Δacc=0 earned-win is at **8 frames kr=0.33 gemma_structural
short-bucket** (Stage 6): Δacc=0.000, e2e=1.090×, per_tok=7.904×.

Open question: does the gemma_structural × kr=0.33 accuracy-preserving
recipe generalize to the 32-frame regime on short bucket?

If yes: SOTA-advancing operating point at Δacc=0 AND e2e > 1.3×.
If no: the 8-frame accuracy preservation is frame-count-specific and
the 32-frame regime requires a different accuracy-preserving mechanism.

## Pre-registered predictions

Baseline decompositions (observed in this autonomous run):
- short-32 kr=0.10 anchor=none: D=3.09s, V=26.1s, G=29.4s, e2e=58.9s,
  fixed_frac=0.500, per_tok=7.16×, e2e=1.663×, Δacc=-0.100

Scaling to kr=0.33 (keeps 33% tokens = 2704 tokens vs 800 at kr=0.10):
- G will be LONGER than at kr=0.10 because prefill sees more tokens —
  at 8 frames kr=0.33 per_tok was 7.90× (similar to kr=0.10 7.16×)
  because prefill is proportional to kept tokens.
  For 32 frames: predicted G_dense ≈ 29.4s (same prefill);
  G_pruned_kr033 ≈ 3.3 × G_pruned_kr010 = 3.3 × 4.12s = 13.6s (rough)
- D, V unchanged from anchor=none kr=0.10: D=3.1s, V=26.1s
- per_tok_s estimate: at 8 frames kr=0.33 gemma_structural/none ratio
  was 7.904/ (kr=0.10 reference per_tok unknown for 8f) — we'll
  estimate s ≈ 3.0 at kr=0.33 32f (less aggressive pruning → less
  per-token speedup)
- Predicted e2e_pruned ≈ 3.1 + 0.3 + 26.1 + 13.6 = 43.1s
- Predicted e2e_dense ≈ 58.9s
- **Predicted e2e speedup ≈ 58.9 / 43.1 = 1.366×**

Rough band: H1''' e2e ∈ [1.25, 1.50] (±0.12 around 1.37×, widened
consistent with short-32 prereg experience).

For Δacc: at 8 frames kr=0.33 gemma_structural preserved accuracy on
short bucket (Δacc=0.000). At 32 frames kr=0.10 anchor=none showed
Δacc=-0.100 uniformly. The question is which effect dominates:
- Anchor-informed (gemma_structural) reduces accuracy loss by ~0.07
  relative to none at 8-frame kr=0.50 (-0.033 vs -0.167).
- Higher kr (0.33 vs 0.10) preserves more context.

Best guess: at 32f kr=0.33 gemma_structural, Δacc ∈ [-0.10, 0.05]
with best-case 0.000 and worst-case -0.100. Band: H2''' Δacc ∈
[-0.15, 0.10].

H3''' peak RSS < 8 GB (Stage 6 32f runs all stayed under 5.5 GB).

## Hypotheses

- **H1''' (e2e ∈ [1.25, 1.50])**: broad band; 1.37× midpoint.
- **H2''' (Δacc ∈ [-0.15, 0.10])**: explicit band that would EARN at
  Δacc=0 AND FALSIFY the "32-frame regime uniformly loses accuracy"
  working hypothesis if observed > -0.05.
- **H3''' (RSS < 8 GB)**: operational guardrail.

## What this run would EARN

1. **If Δacc ≥ -0.05 AND e2e ≥ 1.30×**, that's a new **32-frame earned
   Pareto point at near-zero accuracy cost**. This would be the
   strongest SOTA-advancing individual arm in the project.
2. If the ceiling model holds to ≤5% error at this new (frame_count,
   kr, anchor) triple, that is a 7th independent validation across a
   new anchor dimension.
3. If per_token_s ≈ 3 as predicted, the paper can show an anchor ×
   kr × frame-count matrix with predicted-vs-observed ceiling for
   every cell.

## What this run would FALSIFY

- If Δacc < -0.15, the "gemma_structural preserves accuracy" story
  is frame-count-specific and doesn't generalize to 32 frames.
- If e2e < 1.20×, the kr=0.33 operating point on 32 frames loses too
  much generate-only speedup to pay for the higher kept-token count.
- If e2e > 1.60×, our G-scaling-with-kr estimate is off.

## Run plan

```
uv run python scripts/run_novelty_pruning_gemma.py \
    --manifest research/benchmark_manifests/videomme_dev_v1_short_only.toml \
    --n-items 10 --frame-count 32 --anchor-arm gemma_structural \
    --keep-rate 0.33 \
    --max-tokens 32 \
    --output research/experiments/2026/artifacts/phase1_51R_32frame_short_gemma_kr033/short_kr033_gemma_n10_32frame.jsonl \
    --summary research/experiments/2026/artifacts/phase1_51R_32frame_short_gemma_kr033/short_kr033_gemma_n10_32frame_summary.json
```

Estimated wall-time: 10 items × (58.9s dense + 43.1s pruned) ≈ **17 min**.

## Cross-references

- `2026-04-18-phase-1_51R-stage6-32frame-short-findings.md` — short-32
  anchor=none kr=0.10 reference decomposition.
- `2026-04-18-phase-1_51R-stage6-kr033-findings.md` — 8-frame kr=0.33
  gemma_structural results (Δacc=0 short-bucket at 1.09×).
- `2026-04-18-arithmetic-ceiling-findings.md` — ceiling model.
