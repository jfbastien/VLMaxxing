# Stage 6 kr-sweep — pre-registered e2e ceiling predictions

**Purpose.** Stage 6 extends the 1.51R anchor=gemma_structural kr-sweep at 8
frames to kr=0.33 and kr=0.25. Scientific methodology requires the
prediction **before** the observation. This note records the expected
aggregate + per-bucket e2e ceilings so the landed result can be compared
as a hypothesis test, not a post-hoc rationalization.

Written 2026-04-18 while Stage 6 kr=0.33 is in flight at 14/30 items
(no aggregate yet visible).

## Method

Arithmetic-ceiling formula (task #88):

    e2e_speedup ≤ (fixed + G_dense) / (fixed + G_dense / s)

where `fixed = D + P + V` is invariant under 1.51R, and `s` is the
per-token generate speedup.

Inputs:

- Per-bucket fixed fractions from Stage 2b n=30 (`ceiling_summary.json`):
  - short: 0.568, medium: 0.663, long: 0.912, aggregate: 0.714.
- Per-token speedup projection at each kr × gemma_structural anchor:
  - Use Stage 3 anchor=none per-token speedup as the upper reference
    (kr=0.10: 3.97×, kr=0.25: 2.27×, kr=0.50: 1.74×, linear-interp at
    kr=0.33 ≈ 2.10×).
  - Apply the measured gemma_structural / none ratio at kr=0.50 where we
    have both: 1.116 / 1.740 ≈ **0.641**. This captures the structural
    anchor's reduced per-token speedup (it keeps a different token set;
    higher agreement, less aggressive compute reduction).
  - **Projected per-token speedup for gemma_structural at kr=0.33:
    2.10 × 0.641 ≈ 1.35×. At kr=0.25: 2.27 × 0.641 ≈ 1.46×.**
- Ceiling is then computed bucket-by-bucket and aggregate.

Caveat: the 0.641 ratio is estimated from a single point (kr=0.50 n=30).
If the ratio is non-constant in kr, actual per-token speedups could
deviate by ±30%; predicted ceilings would move accordingly. Record the
actual ratio when kr=0.33 lands and revise kr=0.25 prediction.

## Predictions

### kr=0.33, gemma_structural (projected s = 1.35×)

| bucket    | fixed_frac | projected e2e ceiling |
|-----------|-----------:|----------------------:|
| short     |      0.568 |            **1.126×** |
| medium    |      0.663 |            **1.096×** |
| long      |      0.912 |            **1.023×** |
| aggregate |      0.714 |            **1.080×** |

### kr=0.25, gemma_structural (projected s = 1.46×)

| bucket    | fixed_frac | projected e2e ceiling |
|-----------|-----------:|----------------------:|
| short     |      0.568 |            **1.157×** |
| medium    |      0.663 |            **1.119×** |
| long      |      0.912 |            **1.029×** |
| aggregate |      0.714 |            **1.099×** |

### Reference — kr=0.50, gemma_structural (observed s = 1.116×, n=30)

| bucket    | observed e2e |
|-----------|-------------:|
| aggregate |       0.992× |

(Observed 0.992× vs predicted ceiling of 1.033× at the same s — runs
inside the ceiling but with measurement slack from tokenization/novelty
overhead.)

## Hypotheses

- **H1 (kr=0.33 aggregate ≤ 1.10×).** The arithmetic ceiling bounds
  aggregate e2e to ≈ 1.08×; observed can undershoot this by a few
  percent due to mask + novelty overhead. Falsification: observed
  aggregate ≥ 1.15×. (Would imply either the projected per-token
  speedup is too conservative or the anchor changes `fixed` — unlikely,
  but worth checking.)
- **H2 (kr=0.33 accuracy degrades monotonically from kr=0.50 toward
  kr=0.10).** Stage 5c kr=0.50 Δacc=-0.033; Stage 2b kr=0.10
  Δacc=-0.100 (aggregate, anchor=none). Prediction at kr=0.33 with
  gemma_structural: Δacc in [-0.10, -0.033]. Falsification: Δacc worse
  than -0.15.
- **H3 (long-bucket ceiling stays bound by D).** Long-bucket e2e
  ceiling at kr=0.33 is 1.023×, essentially flat vs kr=0.50. Any
  speedup on long items must come from decode (1.54), not from tighter
  kr at the same frame count. Falsification: long-bucket e2e > 1.05×
  at kr=0.33.

## Decision table

Interpretations of the landed aggregate e2e at kr=0.33:

| observed e2e       | interpretation                                         |
|--------------------|--------------------------------------------------------|
| ≥ 1.15×            | projection underestimated `s` — re-examine Stage 3 vs Stage 5c anchor scaling |
| 1.07× – 1.12×      | ceiling prediction confirmed (expected range)          |
| 0.98× – 1.06×      | within ceiling but mask/overhead erodes gain — consistent |
| < 0.98×            | overhead dominates — publish only with explanation     |

## If H1 holds at kr=0.33

Then Stage 6 kr=0.25 is likely to land at aggregate ≈ 1.10× (same
story, slightly higher ceiling). The useful conclusion is that **no
8-frame operating point with gemma_structural can clear 1.10× e2e at
ceiling-worthy accuracy**. That is the regime-honest narrative. It
motivates:

1. Stage 6 32-frame regime-match pilot (the ceiling rises to ≈ 1.78×).
2. Phase 1.51V (touches V, independent lever on short/medium).
3. Phase 1.54 (touches D, only lever for long bucket).

## If H1 falsified at kr=0.33

Then the projected per-token speedup was too low. Update the
gemma_structural/none ratio from the landed kr=0.33 run, re-predict
kr=0.25, and proceed.

## Links

- `research/experiments/2026/artifacts/arithmetic_ceiling/compute_ceiling.py`
  (per-item decomposition, authoritative formula).
- `research/experiments/2026/2026-04-18-arithmetic-ceiling-findings.md`
  (original ceiling analysis).
- `research/experiments/2026/2026-04-18-phase-1_51R-stage5-cross-arm-synthesis.md`
  (kr=0.50 gemma_structural observed numbers).
- Paper claim: #11 (novelty-pruning delivers e2e speedup on Gemma).
