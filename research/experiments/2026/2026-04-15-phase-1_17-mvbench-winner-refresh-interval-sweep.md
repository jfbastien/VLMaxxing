# Phase 1.17: Refresh-Interval Sweep on MVBench Winner

## Preregistration

Objective:

- trace a quality-vs-reuse curve from the single MVBench winner point by
  varying `refresh_interval` ∈ {1, 2, 4, 0 (=off)} so that the Pareto
  analysis has multiple operating points from the same policy, not a
  lone dot

Claim register targets:

- `WP-2.6`
- `WP-3.1` (Pareto frontier shape from one base policy)
- `WP-3.3` (refresh interval behaves monotonically on well-behaved
  planners)

Reproduction mode:

- generalized benchmark single-shot evaluation per cell

Track:

- A

Gating:

- runs only after phase 1.11 completes and `max_abs(8,32) static+shifted
  noage` is confirmed as the MVBench motion dev winner
- runs regardless of phase 1.12 outcome because the refresh sweep is
  diagnostic methodology, not a dev-to-holdout pipeline

Hypotheses:

- H1 (monotonicity): `refresh_interval=1` = dense (upper bound),
  `refresh_interval=2` reduces reuse but keeps accuracy near dense,
  higher intervals trade accuracy for reuse monotonically
- H2 (compression floor): the lowest-refresh-rate operating point
  (`refresh_interval=0`, the current phase 1.11 winner) sets the
  natural lower-bound on fresh_frames for this policy; more aggressive
  intervals cannot exceed it in compression without policy change
- H3 (item-identity scaling): the refresh-1 run will be near-identical
  to dense-8 (upper bound); refresh-4 will be somewhere between dense-4
  and the winner

Acceptance band:

- 4 cells evaluate cleanly
- the (refresh_interval, cached_acc, fresh_frames) points trace a
  monotonic curve when sorted by refresh_interval

Rejection band:

- non-monotonic curve (e.g. refresh-2 worse than both refresh-1 and
  refresh-4) → planner/refresh interaction has unexpected behavior;
  would require separate diagnosis

Inconclusive:

- harness instability

Cells (all MVBench motion dev, N=15, frame_count=8, policy
`max_abs(8.0, 32.0) static+shifted noage`):

1. `refresh_interval=1` (dense equivalent)
2. `refresh_interval=2`
3. `refresh_interval=4`
4. `refresh_interval=0` (already have this from phase 1.11; re-evaluate
   with replay for consistency)

Runtime: 3 new + 1 replay ≈ ~45 min GPU (replay cache should dominate).

## Execution

Pending phase 1.11 completion.

## Result

Pending.

## Interpretation

Pending.

## Links

- [phase 1.11 MVBench motion dev grid](2026-04-14-phase-1_11-planner-grid-mvbench-motion-dev.md)
- [phase 1.49 TOMATO refresh sweep](2026-04-14-phase-1_49-tomato-direction-refresh-sweep.md)
- [experiment registry](../registry.md)
