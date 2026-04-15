# Phase 1.21: MVBench Motion Slice Enlargement (15 → 30 Items)

## Preregistration

Objective:

- expand the EXISTING MVBench motion dev slice from N=15 to N=30
  (same five groups as `mvbench_motion_dev_v1.toml`:
  `action_localization`, `fine_grained_action`, `object_interaction`,
  `moving_direction`, `moving_attribute` — 6 items per group instead of
  3) and symmetrically expand `mvbench_motion_holdout_v1.toml` to N=30
  with 6 per group. This is a genuine same-slice enlargement, NOT a
  broader-slice experiment.

- Codex audit 2026-04-16 caught an earlier draft that listed different
  groups (`action_sequence`, `unexpected_action`, `action_antonym`)
  which would have been a DIFFERENT slice, not an N=30 enlargement.
  That draft has been corrected to use the same groups as v1.
- re-run dense frame-budget baselines on the enlarged slices
- re-run the MVBench motion dev winner `max_abs(8,32) static+shifted
  noage` and the CPF shoulder `cpf(px8, 0.02/0.08) static+shifted
  noage` on the enlarged slices
- tighter Wilson CIs at N=30, same justification as phase 1.20

Claim register targets:

- `WP-2.6`, `WP-3.1`, `WP-3.3`

Reproduction mode:

- generalized benchmark rerun on a new manifest; maintains preregistered
  dev/holdout disjointness.

Track:

- A

Gating:

- runs after phase 1.12 holdout resolves. Highest priority of the N=30
  enlargement phases because the MVBench winner is the strongest
  point in the repo.

Hypotheses:

- H1 (identity-at-N30): if the N=15 result was "cached equals
  dense-4 item-by-item", on N=30 the per-item diff against dense-4
  will show ≤2 disagreements out of 30.
- H2 (shoulder stability): the CPF shoulder's accuracy holds at
  ~0.65–0.70 on N=30 and stays above the matched dense-3 baseline.
- H3 (budget scaling): the cached winner's effective_fresh_frames
  stays within ±0.2 of the N=15 value (3.22) because the underlying
  motion content is similar across the enlarged slice.

Acceptance band:

- all new dense + cached cells evaluate cleanly
- Wilson half-width shrinks by at least 20%
- per-item diff against dense-4 still shows zero or near-zero
  disagreements on the enlarged slice

Rejection band:

- cached-vs-dense-4 disagreements rise to ≥ 5/30 → the item-identity
  story was slice-specific, not policy-robust.

Inconclusive:

- harness instability or sampling imbalance.

Slice build:

- write `research/benchmark_manifests/mvbench_motion_dev_v2.toml`: the
  existing v1 15 items PLUS 15 more items stratified seed=42 from the
  SAME five hosted groups, so dev_v2 is a superset of dev_v1
- write `research/benchmark_manifests/mvbench_motion_holdout_v2.toml`
  symmetrically: v1 holdout superset, same five groups, zero overlap
  with dev_v2 by item_id.

Cells:

1. dense at {1, 2, 3, 4, 6, 8} on mvbench_motion_dev_v2 (6 cells)
2. dense at {1, 2, 3, 4, 6, 8} on mvbench_motion_holdout_v2 (6 cells)
3. cached `max_abs(8,32) static+shifted noage` on both v2 slices (2
   cells)
4. cached `cpf(px8, 0.02/0.08) static+shifted noage` on both v2 slices
   (2 cells)

Total cells: 16. Runtime: ~3.5 hrs GPU (MVBench videos are shorter;
feature replay helps if items overlap current slice corpus).

## Execution

Pending phase 1.12 completion.

## Result

Pending.

## Interpretation

Pending.

## Links

- [phase 1.9 MVBench motion frame-budget](2026-04-14-phase-1_9-mvbench-motion-frame-budget-baselines.md)
- [phase 1.11 MVBench motion dev grid](2026-04-14-phase-1_11-planner-grid-mvbench-motion-dev.md)
- [phase 1.12 holdout evaluation](2026-04-14-phase-1_12-grid-winners-holdout.md)
- [execution plan round 7](../../../docs/execution-plan-round-7.md)
