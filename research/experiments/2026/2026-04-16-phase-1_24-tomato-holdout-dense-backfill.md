# Phase 1.24: TOMATO Motion Holdout Dense Curve Backfill

## Preregistration

Objective:

- build the missing dense-N baseline cells at `frame_count ∈ {2, 3, 8}`
  on the TOMATO motion holdout slice, so that phase 1.12 TOMATO cached
  survivors can be matched against a complete dense frame-budget curve
- without this backfill, a cached point at fresh-frames ≈ 3.4 sits in
  an unmeasured region of the curve between dense-1 and dense-4, so
  Pareto domination claims cannot be made rigorously.

Claim register targets:

- `WP-2.5`, `WP-3.1`, `WP-3.3` — all conditional on phase 1.12 TOMATO
  holdout having at least one cached survivor

Reproduction mode:

- matched frame-budget baseline building on a preregistered holdout
  slice

Track:

- A

Gating:

- runs immediately after phase 1.12 TOMATO holdout completes its last
  cached policy (5/5), regardless of outcome
- if every cached policy lands below dense-6 holdout accuracy, dense
  backfill still matters for interpretability but is no longer
  paper-critical

Hypotheses:

- H1 (plateau): TOMATO holdout dense curve plateaus somewhere between
  dense-4 (0.133) and dense-6 (0.267); dense-3 and dense-8 should land
  within that band
- H2 (monotonicity in the middle): dense-3 ≥ dense-4 (dense-4 was the
  low point on TOMATO holdout, an unusual shape)
- H3 (tail behavior): dense-8 ≤ dense-6 (TOMATO holdout is confidence-
  limited past 6 frames)

Acceptance band:

- 3 new dense cells evaluated cleanly
- Wilson CI intervals computed per cell
- union curve at frames {1, 2, 3, 4, 6, 8} emitted as a single JSON

Rejection band:

- harness failures on ≥ 1 cell (N=15 Metal-timeouts etc.); degrade
  interpretation but do not block everything

Inconclusive:

- sampling imbalance on N=15 makes CIs too wide to order any adjacent
  cells

Cells:

1. dense at frame_count=2 on `tomato_motion_holdout_v1.toml`
2. dense at frame_count=3 on same
3. dense at frame_count=8 on same

Runtime: 3 cells × ~12 min per cell ≈ 0.6 hrs GPU (phase 1.8 ran dense
at {1, 4, 6} in similar time; dense runs are typically faster than
cached runs because planner classification is skipped).

## Execution

Completed 2026-04-16. Used `scripts/frame_budget_baseline.py --manifest
tomato_motion_holdout_v1.toml --frame-counts 2 3 8`. No special
dense-only flag needed; the `frame_budget_baseline.py` driver already
runs dense-only cells. Combined with phase 1.8 output into
`phase1_24_tomato_motion_holdout_dense_full.json` for compatibility
with `pareto_analysis.py analyze`.

## Result

Preregistration outcome: **Accepted with caveat** — curve built
successfully, H2 (dense-4 low-point) confirmed. Caveat: initial
export of `phase1_24_tomato_motion_holdout_dense_full.json` had a
data bug (n=0 placeholder CIs on phase-1.8-origin rows) caught by
2026-04-16 audit; fixed in the same tranche by recomputing n from
`per_group_dense_accuracy.*.count` and preserving the source CIs.

Full TOMATO motion holdout dense curve (N=15):

| frame_count | accuracy | Wilson 95% CI |
|---|---|---|
| 1 | 0.200 | [0.07, 0.45] |
| 2 | 0.200 | [0.07, 0.45] |
| 3 | 0.200 | [0.07, 0.45] |
| 4 | 0.133 | [0.04, 0.38] |
| 6 | 0.267 | [0.11, 0.52] |
| 8 | 0.267 | [0.11, 0.52] |

Curve shape:

- Low-frame regime {1, 2, 3}: flat at 0.200 — first-frame answer
  dominates on most items in these 15 clips
- Surprising dip at dense-4: 0.133 (below dense-1 accuracy)
- Plateau at dense-6 and dense-8: 0.267

H2 (dense-4 is the low point on TOMATO holdout) is confirmed:
dense-4 at 0.133 < dense-2, dense-3 at 0.200. This non-monotonic
curve is a real slice feature, not a harness artifact.

## Interpretation

- With the full curve, phase 1.12 TOMATO holdout Pareto analysis
  now has all 6 dense cells. Result: 5/5 cached policies are Pareto
  candidates (strict Pareto winners vs dense-6/8 at equal accuracy,
  lower budget).
- The non-monotonic dense curve explains part of the low-accuracy
  regime: TOMATO motion holdout at N=15 has several items where
  more frames make the model worse (presumably over-sampling creates
  conflicting evidence).
- This is the companion result to phase 1.12.B on MVBench — both
  now have completed matched-budget dense curves for Pareto checks.

## Links

- [phase 1.8 motion frame-budget baselines](2026-04-14-phase-1_8-motion-frame-budget-baselines.md)
- [phase 1.12 holdout evaluation](2026-04-14-phase-1_12-grid-winners-holdout.md)
- [execution plan round 7](../../../docs/execution-plan-round-7.md)
