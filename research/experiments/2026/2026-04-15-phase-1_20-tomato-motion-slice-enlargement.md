# Phase 1.20: TOMATO Motion Slice Enlargement (15 → 30 Items)

## Preregistration

Objective:

- expand TOMATO motion dev from N=15 to N=30 and TOMATO motion
  holdout from N=15 to N=30, drawn with stratified random seed=42
  from the same motion groups (direction / rotation / shape_trend)
- re-run dense frame-budget baselines on the enlarged slices
- re-run the TOMATO motion dev winner `max_abs(8,32) static+shifted
  age=4` and the TOMATO motion holdout winners from phase 1.12 on
  the enlarged slices
- tighter Wilson CIs: at N=30, half-width around p=0.4 drops from
  ≈0.25 to ≈0.18.

Claim register targets:

- `WP-2.5`, `WP-3.1`, `WP-3.3`
- this phase either tightens or weakens the TOMATO dev Pareto claim
  depending on whether the observed accuracy survives the larger
  slice.

Reproduction mode:

- generalized benchmark rerun on a new manifest; maintains preregistered
  dev/holdout disjointness.

Track:

- A

Gating:

- runs after phase 1.12 holdout resolves. If phase 1.12 TOMATO winner
  is rejected on holdout (strictly dominated by dense-N), still run
  this phase to confirm whether that rejection was a sampling-noise
  artifact of N=15.

Hypotheses:

- H1 (stability): dev cached accuracy on N=30 stays within ±1/30 of
  the N=15 value (0.400 ± 0.033).
- H2 (holdout recovery): holdout cached accuracy on N=30 rises above
  the N=15 value of 0.200, because at N=15 the holdout was flat at a
  confidence-limited regime (dense itself was 0.267 at matched budget).
- H3 (Pareto stability): the dev-side frontier shape is robust —
  dense-6 and cached winner still intersect; dense-4 still underperforms
  cached winner.

Acceptance band:

- all new dense cells + winner cached cells evaluate cleanly
- Wilson half-width on cached_accuracy for each cell drops by at least
  20% vs N=15 evaluations
- dev cached vs dense-N story holds in qualitative direction (cached
  still Pareto-dominates OR clearly does not; no "uninterpretable")

Rejection band:

- dev cached accuracy drops below dense-6 accuracy on N=30 at matched
  budget → N=15 Pareto win was sampling noise.

Inconclusive:

- harness instability, Metal timeouts, or unreasonable slice
  imbalance in stratified sampling.

Slice build:

- write `research/benchmark_manifests/tomato_motion_dev_v2.toml` with 30
  items stratified from the full TOMATO motion corpus (10 direction,
  10 rotation, 10 shape_trend) using seed=42
- write `research/benchmark_manifests/tomato_motion_holdout_v2.toml`
  symmetrically, guaranteeing zero overlap with v2 dev by item_id.

Cells:

1. dense at {1, 2, 3, 4, 6, 8} on tomato_motion_dev_v2 (6 cells)
2. dense at {1, 2, 3, 4, 6, 8} on tomato_motion_holdout_v2 (6 cells)
3. cached `max_abs(8,32) static+shifted age=4` on both v2 slices (2
   cells)

Total cells: 14. Runtime: ~3 hrs GPU (dense runs are faster with replay
cache since items overlap the corpus; new items force fresh encodes).

## Execution

Pending phase 1.12 completion.

## Result

Pending.

## Interpretation

Pending.

## Links

- [phase 1.8 TOMATO motion frame-budget](2026-04-14-phase-1_8-motion-frame-budget-baselines.md)
- [phase 1.10 TOMATO motion dev grid](2026-04-14-phase-1_10-planner-grid-tomato-motion-dev.md)
- [phase 1.12 holdout evaluation](2026-04-14-phase-1_12-grid-winners-holdout.md)
- [execution plan round 7](../../../docs/execution-plan-round-7.md)
