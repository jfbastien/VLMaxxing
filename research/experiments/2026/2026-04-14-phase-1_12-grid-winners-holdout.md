# Phase 1.12: Pareto-Winner Holdout Evaluation

## Preregistration

Objective:

- one-shot evaluate dev-selected Pareto-dominating policies on the disjoint
  motion holdout slices for both TOMATO and MVBench, so the dev-side
  Pareto findings are validated as generalizing or rejected as dev-only

Claim register targets:

- `WP-2.5`
- `WP-2.6`
- `WP-3.1`
- `WP-3.3`

Reproduction mode:

- generalized benchmark, single-shot holdout (no further tuning)

Track:

- A (quality at matched fresh-token-equivalent budget on holdout)

Hypotheses:

- H1 (dev-to-holdout transfer): the cached policies that Pareto-dominate
  the dense frame-budget curve on dev also Pareto-dominate the dense
  frame-budget curve on holdout
- H2 (per-content): TOMATO motion holdout transfer differs from MVBench
  motion holdout transfer because their dense baselines have qualitatively
  different shapes (TOMATO holdout drops at higher frames; MVBench holdout
  is monotonic)

Acceptance band (per slice):

- at least one dev-selected policy survives Pareto-domination check on
  holdout (i.e. the holdout dense frame-budget curve does NOT strictly
  dominate the cached policy's holdout-evaluated point)

Rejection band (per slice):

- every dev-selected policy is strictly dominated by some holdout dense-N
  point on the same slice

Inconclusive:

- harness instability mid-evaluation
- dev-selected winners list is empty (no Pareto candidates from phases 1.10
  or 1.11)

Selection protocol:

- read `phase1_10_tomato_motion_dev_pareto.json` and select up to the top
  `5` candidates by cached_accuracy at lowest effective_fresh_frames
- read `phase1_11_mvbench_motion_dev_pareto.json` and apply the same
  selection
- record the selected policy labels in this note BEFORE the holdout runs

Pareto evaluation on holdout:

- for each selected policy, run benchmark with the policy's exact
  configuration on the corresponding holdout manifest
- run `pareto_analysis.py analyze` against the holdout dense
  frame-budget summary (already complete in phase 1.9)

Notes:

- this phase is the discipline gate: dev cannot be tuned against holdout,
  and holdout cannot be retried after seeing the result
- if both TOMATO and MVBench holdout reject every dev winner, the project
  pivots to composition with FastV (orthogonal token pruning) per the
  round-7 execution plan strategic pivot points

## Execution

Pending phase 1.10 + 1.11 completion.

## Result

Pending.

## Interpretation

Pending.

## Links

- [phase 1.10 TOMATO motion dev grid](2026-04-14-phase-1_10-planner-grid-tomato-motion-dev.md)
- [phase 1.11 MVBench motion dev grid](2026-04-14-phase-1_11-planner-grid-mvbench-motion-dev.md)
- [phase 1.9 TOMATO motion frame-budget](2026-04-14-phase-1_8-motion-frame-budget-baselines.md)
- [phase 1.9 MVBench motion frame-budget](2026-04-14-phase-1_9-mvbench-motion-frame-budget-baselines.md)
- [execution plan round 7](../../../docs/execution-plan-round-7.md)
