# Phase 1.15: Threshold Refinement Around TOMATO `max_abs` Winner

## Preregistration

Objective:

- same as phase 1.14 but on TOMATO motion dev — refine around
  `max_abs(8.0, 32.0) static+shifted age=4`, the current TOMATO motion
  dev Pareto-dominant point (cached_acc=0.400, fresh=3.99)

Claim register targets:

- `WP-2.5` (Track A quality at matched fresh-token-equivalent budget)
- `WP-3.1` (training-free temporal reuse traces a Pareto frontier)

Reproduction mode:

- method-development dev-only refinement grid; holdout eval defers to
  phase 1.12 (or a gated phase 1.15b)

Track:

- A

Gating:

- runs only after phase 1.12 outcome is known; if phase 1.12 TOMATO
  winner is rejected outright (every dev winner strictly dominated by
  holdout dense-N), skip this phase and pivot to Stage F composition
  (FastV + ours)
- runs if phase 1.12 TOMATO winner survives holdout on at least one slice

Hypotheses:

- H1 (thresholds): TOMATO's harder motion content means the sensitive
  threshold may be looser than MVBench's (8, 32) — tighter shifted
  threshold may improve direction-item recall
- H2 (max_age sensitivity): on TOMATO the max_age=4 was the binding
  gate; pair with max_age={2, 4, 6} on a single threshold pair to map
  age-accuracy curve

Acceptance band:

- 6 policies evaluate cleanly
- at least one policy matches or beats cached_accuracy=0.400 at
  fresh_frames < 3.99

Rejection band:

- all 6 policies dominated by the existing (8, 32, age=4) point

Inconclusive:

- harness instability

Policies (all TOMATO motion dev, frame_count=8, N=15):

1. `max_abs(6.0, 24.0) static+shifted age=4`
2. `max_abs(8.0, 24.0) static+shifted age=4`
3. `max_abs(8.0, 28.0) static+shifted age=4`
4. `max_abs(10.0, 40.0) static+shifted age=4`
5. `max_abs(8.0, 32.0) static+shifted age=2`
6. `max_abs(8.0, 32.0) static+shifted age=6`

Existing reference: `max_abs(8.0, 32.0) static+shifted age=4` at
cached_acc=0.400, fresh=3.99, reuse=0.573.

Runtime estimate: 6 policies × ~16 min ≈ 1.6 hrs GPU.

## Execution

Pending phase 1.12 TOMATO outcome.

## Result

Pending.

## Interpretation

Pending.

## Links

- [phase 1.10 TOMATO motion dev grid](2026-04-14-phase-1_10-planner-grid-tomato-motion-dev.md)
- [phase 1.12 holdout evaluation](2026-04-14-phase-1_12-grid-winners-holdout.md)
- [experiment registry](../registry.md)
