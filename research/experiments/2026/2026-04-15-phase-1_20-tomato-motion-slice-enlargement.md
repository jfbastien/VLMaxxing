# Phase 1.20: TOMATO Motion Slice Enlargement (15 → 30 Items)

## Preregistration

Objective:

- expand TOMATO motion dev from N=15 to N=30 and TOMATO motion
  holdout from N=15 to N=30.

**Protocol note (2026-04-16)**: the original prereg said "stratified
random seed=42." The actual manifests are **deterministic supersets**:
v1 items kept, plus 5 new items per group selected from the
earliest available corpus keys that avoid dev/holdout overlap. This
is a protocol deviation from random stratification; the deviation is
documented here and in the manifest descriptions. The resulting v2
slices are still valid same-group enlargements of v1, just not
randomly sampled.

Groups: direction / rotation / shape_trend
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
- H2 (holdout stability): the current N=15 holdout result is
  cached_accuracy=0.267 (4/15) tying dense-6/8 at lower budget.
  At N=30, Wilson CI tightens from [0.11, 0.52] to roughly
  [0.13, 0.42]. Within that tighter CI, at least one cached policy
  still matches dense-6/8 accuracy at strictly lower fresh-frame
  budget. (Corrected 2026-04-16: an earlier draft claimed the N=15
  value was 0.200 — that was the dense-1/2/3 accuracy on holdout,
  not the cached accuracy. All 5 cached policies landed at 0.267
  per `phase1_12_tomato_motion_holdout_summary.json`.)
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

**Gating updated 2026-04-16**: phase 1.12 TOMATO holdout is
complete (5/5 cached policies landed at 0.267; see phase 1.12
note). This phase is now **pending scheduling**, not pending a
gate. Runs when GPU budget allows, ordered after phase 1.21
MVBench N=30 in the post-CodecSight strategy because MVBench N=30
is the primary paper-claim hardening gate.

## Result

Pending.

## Interpretation

Pending.

## Links

- [phase 1.8 TOMATO motion frame-budget](2026-04-14-phase-1_8-motion-frame-budget-baselines.md)
- [phase 1.10 TOMATO motion dev grid](2026-04-14-phase-1_10-planner-grid-tomato-motion-dev.md)
- [phase 1.12 holdout evaluation](2026-04-14-phase-1_12-grid-winners-holdout.md)
- [execution plan round 7](../../../docs/execution-plan-round-7.md)
