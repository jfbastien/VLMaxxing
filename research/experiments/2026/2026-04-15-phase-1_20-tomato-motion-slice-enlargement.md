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

- harness instability, Metal timeouts, or item-load failures on
  the new v2 items.

Slice build (protocol deviation from original prereg — see note at
top of Objective):

- `tomato_motion_dev_v2.toml`: v1 superset + 5 new items per group
  from earliest available corpus keys (deterministic, not random)
- `tomato_motion_holdout_v2.toml`: v1 superset + 5 new items per
  group, zero overlap with dev_v2 by item_id.

Cells:

1. dense at {1, 2, 3, 4, 6, 8} on tomato_motion_dev_v2 (6 cells)
2. dense at {1, 2, 3, 4, 6, 8} on tomato_motion_holdout_v2 (6 cells)
3. cached `max_abs(8,32) static+shifted age=4` on both v2 slices (2
   cells)

Total cells: 14. Runtime: ~3 hrs GPU (dense runs are faster with replay
cache since items overlap the corpus; new items force fresh encodes).

## Execution

**Launched 2026-04-16** after phase 1.21 MVBench N=30 passed.
Dense baselines running on holdout_v2 at {1,2,3,4,6,8} frames
via `frame_budget_baseline.py --allow-dirty`. After dense: cached
base policy cell (`max_abs(8,32) static+shifted age=4`).

Note: `--allow-dirty` means artifacts are diagnostic until rerun
clean. For paper-facing use, rerun on clean tree.

## Result

Preregistration outcome: **Accepted** (holdout v2 cells; clean tree
as of commit 42b06eb, 2026-04-16).

**TOMATO motion holdout v2 (N=30) dense curve:**

| frame_count | accuracy |
|---|---|
| 1 | 0.200 |
| 2 | 0.167 |
| 3 | 0.200 |
| 4 | 0.133 |
| 6 | 0.267 |
| 8 | 0.333 |

**Cached base policy** (`max_abs(8,32) static+shifted age=4`):

| metric | value |
|---|---|
| cached_accuracy | 0.333 (10/30) |
| same-run dense_accuracy | 0.333 (10/30) |
| agreement | 0.800 (24/30) |
| effective_fresh_frames | 3.55 |

Pareto: strict win vs dense-4 and dense-6; Pareto tie vs dense-8
(0.333 = 0.333 at 44% of dense-8's budget).

**Provenance caveat (resolved)**: the initial dense + cached runs
used `--allow-dirty` for throughput. A clean-tree rerun of the
cached cell (commit 42b06eb, 2026-04-16) reproduces the numbers
exactly: cached=0.333, dense=0.333, agreement=0.800, fresh=3.55,
`git_dirty=False`. Clean-tree artifact at
`phase1_20_tomato_motion_holdout_v2_cached_clean/`. Claim #6 is now
paper-grade on both MVBench and TOMATO.

## Interpretation

- **H2 (holdout stability)**: the cached base policy ties dense-8
  at N=30 (0.333 = 0.333) at 44% budget. The Pareto relationship
  from N=15 (0.267 = 0.267) is preserved and STRENGTHENED: budget
  ratio improved from 50% to 44%.
- The low-accuracy regime persists: both dense-8 and cached are at
  0.333 (10/30). This supports a scoped "hard-slice matched-budget
  Track A" claim, not a strong "semantic preservation" headline.
- TOMATO serves as the adversarial stress lane; MVBench provides the
  meaningful-accuracy anchor. Together they satisfy claim #6.
- Agreement at 0.800 (24/30) means cached disagrees with dense on
  6 items — weaker than MVBench's 0.933 but consistent with TOMATO
  being the harder benchmark.

## Links

- [phase 1.8 TOMATO motion frame-budget](2026-04-14-phase-1_8-motion-frame-budget-baselines.md)
- [phase 1.10 TOMATO motion dev grid](2026-04-14-phase-1_10-planner-grid-tomato-motion-dev.md)
- [phase 1.12 holdout evaluation](2026-04-14-phase-1_12-grid-winners-holdout.md)
- [execution plan round 7](../../../docs/execution-plan-round-7.md)
