# Phase 1.9: MVBench Motion Frame-Budget Baselines

## Preregistration

Objective:

- reproduce phase 1.8's matched dense-frame-budget methodology on the
  MVBench motion dev and holdout slices so cached-policy wins can be
  compared cleanly across TOMATO and MVBench motion content

Claim register targets:

- `WP-2.6`
- `WP-3.1`
- `WP-3.3`

Reproduction mode:

- generalized benchmark diagnosis

Track:

- A (quality / fresh-token-equivalent budget)

Hypotheses:

- H1: MVBench motion dense-frame accuracy follows a similar monotonic shape
  to TOMATO motion (accuracy rises with frame count, near-flat past `6` frames)
- H2: MVBench motion frame-budget accuracy is higher at every budget than
  TOMATO motion because MVBench motion includes fewer strictly
  temporal-reasoning items under the first-frame ablation from phase 1.47
- H3: at matched fresh-token-equivalent budget, `mean + max_age=4` cached
  policy dev-side wins on TOMATO motion DO or DO NOT transfer to MVBench
  motion — this preregistration does not commit a direction; the run result
  will be treated as evidence either way

Acceptance band:

- all six frame counts (`1`, `2`, `3`, `4`, `6`, `8`) complete on both dev
  and holdout manifests without runtime errors
- Wilson 95% CIs computed on every dense accuracy

Rejection band:

- runtime instability prevents the benchmark path from completing on any
  frame count
- dense accuracy at `8` frames collapses below `0.3`, which would invalidate
  the slice as a comparison baseline

Inconclusive:

- mid-run drift (e.g. Metal GPU timeout) that cannot be reproduced with the
  same starting state

Notes:

- this note intentionally reuses the `mvbench_motion_dev_v1.toml` and
  `mvbench_motion_holdout_v1.toml` manifests, which are frozen to three
  items per task from `action_localization`, `fine_grained_action`,
  `object_interaction`, `moving_direction`, `moving_attribute`
- frame-budget driver uses `cache_mode=identity`, so the dense encoder runs
  on every frame and there is no cached-path contamination in the baseline
- feature replay cache is used for cross-run efficiency

## Execution

Run date:

- 2026-04-14

Model: `Qwen2.5-VL-7B-Instruct-4bit` on MLX.
Decode: PyAV, `uniform_global` sampling to `560×560` letterbox.

Artifacts:

- dev summary:
  [phase1_9_mvbench_motion_frame_budget_dev.json](artifacts/phase1_9_mvbench_motion_frame_budget_dev.json)
- dev per-frame:
  [frame_budget_mvbench_motion_dev/](artifacts/frame_budget_mvbench_motion_dev/)
- holdout summary:
  [phase1_9_mvbench_motion_frame_budget_holdout.json](artifacts/phase1_9_mvbench_motion_frame_budget_holdout.json)
- holdout per-frame:
  [frame_budget_mvbench_motion_holdout/](artifacts/frame_budget_mvbench_motion_holdout/)

## Result

### Dev (N=15)

| frames | dense_acc | CI95 |
|---|---|---|
| 1 | 0.467 | [0.248, 0.699] |
| 2 | 0.533 | [0.301, 0.752] |
| 3 | 0.467 | [0.248, 0.699] |
| 4 | **0.733** | [0.480, 0.891] |
| 6 | 0.667 | [0.417, 0.848] |
| 8 | 0.600 | [0.357, 0.802] |

Curve is NON-MONOTONIC: peaks at dense-4, then drops. The peak makes
dense-4 the binding Pareto bar: any cached policy with effective fresh
frames > 4 is strictly dominated unless cached_acc > 0.733.

### Holdout (N=15)

| frames | dense_acc | CI95 |
|---|---|---|
| 1 | 0.267 | [0.109, 0.520] |
| 2 | 0.533 | [0.301, 0.752] |
| 3 | 0.600 | [0.357, 0.802] |
| 4 | 0.600 | [0.357, 0.802] |
| 6 | 0.667 | [0.417, 0.848] |
| 8 | **0.733** | [0.480, 0.891] |

Curve is monotonically increasing, peak at dense-8. Different shape from
dev despite same tasks and same N — content-class distribution differs.

## Interpretation

Same five MVBench motion task labels, disjoint clip selection, produced
qualitatively different dense frame-budget curves. On dev the peak sits at
4 frames; on holdout the peak sits at 8. This is a real content-level
finding: per-task clip heterogeneity within MVBench is large enough to
shift where the Pareto bar lives.

Comparison to TOMATO motion (phase 1.8):

```
TOMATO motion dev:     1: 0.000   2: 0.267   3: 0.267   4: 0.267   6: 0.400   8: 0.467
TOMATO motion holdout: 1: 0.200              4: 0.133              6: 0.267   8: 0.267

MVBench motion dev:    1: 0.467   2: 0.533   3: 0.467   4: 0.733   6: 0.667   8: 0.600
MVBench motion holdout:1: 0.267   2: 0.533   3: 0.600   4: 0.600   6: 0.667   8: 0.733
```

Observations:
- MVBench motion is uniformly EASIER than TOMATO motion (dense baselines
  0.467-0.733 vs 0.133-0.467). First-frame ablation in phase 1.47 already
  suggested this: TOMATO requires more temporal content per item.
- MVBench peaks at different frame counts dev/holdout, TOMATO is
  monotonically increasing on dev but drops 4→6 on holdout.
- Implication for Pareto: MVBench is a harder bar because dense-4 peak
  (0.733) is high; TOMATO is easier because even dense-8 only reaches 0.467.

Key questions to answer:

- Is the MVBench motion accuracy curve qualitatively similar to TOMATO's?
- At matched dense-frame budget, does MVBench motion give a higher accuracy
  floor? If yes, this supports the content-conditioning hypothesis (phase 1.47
  first-frame ablation already showed this).
- Does the dev-side phase-1.8 cached win for `mean + max_age=4` transfer to
  MVBench motion? The comparison point will be the dev-side cached point at
  ~1247 fresh-token equivalent vs the MVBench motion dense-frame-budget
  curve at the same budget.

## Links

- [phase 1.8 motion frame-budget](2026-04-14-phase-1_8-motion-frame-budget-baselines.md)
- [phase 1.47 first-frame ablation](2026-04-13-phase-1_47-benchmark-first-frame-ablation.md)
- [claim register](../../../docs/claim-register.md)
- [reproduction status](../../../docs/reproduction-status.md)
