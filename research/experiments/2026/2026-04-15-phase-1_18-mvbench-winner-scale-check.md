# Phase 1.18: Scale Check on MVBench Winner — frame_count ∈ {4, 12, 16}

## Preregistration

Objective:

- check whether the MVBench winner's Pareto story depends on the
  specific frame_count=8 choice, or whether the same policy at higher
  frame counts continues to dominate matched dense frame-budget
- build a 3-point scaling curve showing how
  `effective_fresh_frames` and `cached_accuracy` behave as total frames
  rise under the same planner

Claim register targets:

- `WP-2.6`
- `WP-3.1` (Pareto scaling behavior)
- `WP-3.3` (fresh-frame proxy robustness)

Reproduction mode:

- generalized benchmark single-shot evaluation

Track:

- A

Gating:

- runs only after phase 1.11 completes and winner confirmed
- runs regardless of phase 1.12 outcome — this is a scaling-diagnostic
  experiment, not a dev-to-holdout pipeline

Hypotheses:

- H1 (monotonic fresh-frame): as frame_count rises, so does
  effective_fresh_frames under the same policy (more decisions to
  unmask)
- H2 (saturation): cached_accuracy saturates — going from 8 to 16
  frames improves accuracy by ≤ 1 item on N=15 because MVBench motion
  ground-truth labels are not scale-sensitive past some frame count
- H3 (budget efficiency): the ratio cached_fresh / dense_count falls
  monotonically (more compression at higher frame counts)

Acceptance band:

- 3 cells evaluate cleanly (reuse for the current 8-frame point = 4th)
- 4-point scaling curve published

Rejection band:

- non-monotonic accuracy, or a case where cached at higher frame_count
  is outperformed by dense at the matched fresh-frame budget

Inconclusive:

- harness instability at 16 frames (may hit Metal-timeout or VRAM
  limits on M3 Air)

Cells (all MVBench motion dev, N=15, policy `max_abs(8.0, 32.0)
static+shifted noage`):

1. `frame_count=4`
2. `frame_count=8` (existing from phase 1.11)
3. `frame_count=12`
4. `frame_count=16`

Each cell needs a matched-frame-count dense baseline; dense-4 and
dense-8 exist from phase 1.9. Dense-12 and dense-16 MUST be built
before the cached runs in this phase — otherwise the Pareto-matching
axis cannot be drawn at those frame counts. If dense-12 or dense-16
fails to run (Metal-timeout or VRAM pressure on M3 Air), the
corresponding cached cell is demoted to exploratory and the scale
finding caps at 8 frames.

Runtime estimate: 2 dense × ~12 min + 3 cached × ~16 min ≈ 1.3 hrs
GPU (conservative; replay helps the 4- and 8-frame cells).

## Execution

Pending phase 1.11 completion.

## Result

Pending.

## Interpretation

Pending.

## Links

- [phase 1.9 MVBench motion frame-budget](2026-04-14-phase-1_9-mvbench-motion-frame-budget-baselines.md)
- [phase 1.11 MVBench motion dev grid](2026-04-14-phase-1_11-planner-grid-mvbench-motion-dev.md)
- [experiment registry](../registry.md)
