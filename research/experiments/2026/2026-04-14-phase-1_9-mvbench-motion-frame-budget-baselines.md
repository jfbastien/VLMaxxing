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

### Dev

_Pending completion of background run. Fill exact numbers here after the
artifact lands._

### Holdout

_Pending run — planned to start immediately after dev completes._

## Interpretation

_To be completed once both runs are in._

Comparison template (to fill after runs):

```
TOMATO motion dev (phase 1.8):
  1: 0.000   2: 0.267   3: 0.267   4: 0.267   6: 0.400   8: 0.467
TOMATO motion holdout (phase 1.8):
  1: 0.200   4: 0.133   6: 0.267   8: 0.267

MVBench motion dev (this phase):   <filled from artifact>
MVBench motion holdout (this phase): <filled from artifact>
```

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
