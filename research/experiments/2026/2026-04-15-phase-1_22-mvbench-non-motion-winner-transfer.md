# Phase 1.22: MVBench Non-Motion Transfer of `max_abs` Winner

## Preregistration

Objective:

- evaluate whether the MVBench motion-dev winner `max_abs(8,32)
  static+shifted noage` transfers to an MVBench NON-motion slice,
  where the task structure does not favor temporal change statistics
- if the winner holds on non-motion slices, that's evidence for a
  general-purpose policy; if it fails, the result is motion-content
  specialized.

Claim register targets:

- `WP-3.3` (cross-content generalization of a single policy)

Reproduction mode:

- generalized benchmark single-shot evaluation on a new slice

Track:

- A

Gating:

- runs after phase 1.11 completes and winner confirmed; independent of
  phase 1.12 holdout outcome

Hypotheses:

- H1 (motion-specific): the winner underperforms dense-4 on non-motion
  slices; accuracy drops ≥ 2 items out of 15 vs dense-8.
- H2 (general-purpose): the winner matches or beats dense-4 agreement
  on non-motion slices, supporting a single-policy Pareto claim.
- H3 (reuse reshaping): `mean_active_reuse` on non-motion slices
  differs from motion slice (expected higher — less change per
  frame-pair) so fresh-frame budget shrinks.

Acceptance band:

- non-motion slice cells evaluate cleanly (dense at {1,2,3,4,6,8} +
  cached winner = 7 cells)
- per-item diff vs dense-4 either supports H1 or H2 unambiguously

Rejection band:

- cells fail to execute (video path resolution or manifest load
  failure)

Inconclusive:

- harness instability

Non-motion slice selection:

- Pick `mvbench_non_motion_dev_v1.toml`, a new stratified sample of 15
  items drawn from MVBench hosted groups that are NOT motion-heavy:
  - `fine_grained_action`
  - `object_existence`
  - `object_interaction`
  - `character_order`
  - `counterfactual_inference`
- seed=42 stratified 3 per group = 15 items

Cells:

1. dense at {1, 2, 3, 4, 6, 8} on mvbench_non_motion_dev_v1 (6 cells)
2. cached `max_abs(8,32) static+shifted noage` on same slice (1 cell)

Total: 7 cells. Runtime: ~1.5 hrs GPU (shorter because many MVBench
videos are already in feature cache).

## Execution

Pending phase 1.11 completion.

## Result

Pending.

## Interpretation

Pending.

## Links

- [phase 1.11 MVBench motion dev grid](2026-04-14-phase-1_11-planner-grid-mvbench-motion-dev.md)
- [phase 1.16 cross-benchmark transfer](2026-04-15-phase-1_16-cross-benchmark-winner-transfer.md)
- [experiment registry](../registry.md)
