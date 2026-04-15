# Phase 1.14: Threshold Refinement Around MVBench `max_abs` Winner

## Preregistration

Objective:

- check whether `max_abs(8.0, 32.0) static+shifted noage` is a local
  Pareto optimum or just the nearest grid node to a better nearby policy
- extend the dev frontier if a neighbor-threshold policy reaches higher
  cached_accuracy at equal or lower effective_fresh_frames on MVBench
  motion dev

Claim register targets:

- `WP-2.6` (Track A quality at matched fresh-token-equivalent budget)
- `WP-3.1` (training-free temporal reuse traces a Pareto frontier)

Reproduction mode:

- method-development dev-only refinement grid; holdout defers to phase
  1.12 / phase 1.14b (not preregistered here)

Track:

- A

Gating:

- runs only after phase 1.11 full sweep completes AND
  `max_abs(8,32) static+shifted noage` is the MVBench motion dev winner
- skipped entirely if phase 1.11 surfaces a different primary winner
  (would need a different refinement grid)

Hypotheses:

- H1 (local optimum): none of the neighbor thresholds improve both
  cached_accuracy and fresh_frames simultaneously
- H2 (asymmetric): relaxing the static threshold (higher) is more
  tolerated than tightening it; the shifted threshold is the sensitive
  knob

Acceptance band:

- all five neighbor policies evaluate cleanly (no runtime errors, valid
  metrics for all 15 items)
- winner+neighbors together produce at least 3 Pareto-candidate points
  (superset of the current single winner) OR the analysis clearly
  establishes the winner as locally optimal

Rejection band:

- all neighbors dominated strictly by the existing winner AND no neighbor
  lies on the frontier → winner is a single point, not a frontier

Inconclusive:

- harness instability mid-sweep

Policies to evaluate (all on MVBench motion dev, frame_count=8, N=15):

1. `max_abs(6.0, 24.0) static+shifted noage`
2. `max_abs(8.0, 24.0) static+shifted noage`
3. `max_abs(8.0, 28.0) static+shifted noage`
4. `max_abs(10.0, 32.0) static+shifted noage`
5. `max_abs(10.0, 40.0) static+shifted noage`

Existing reference point (from phase 1.11):

- `max_abs(8.0, 32.0) static+shifted noage` — cached_acc=0.733,
  fresh=3.22, reuse=0.682

Runtime estimate: 5 policies × ~16 min per policy ≈ 1.3 hrs GPU.

## Execution

Pending phase 1.11 completion.

Planned command:

```
uv run python scripts/planner_grid_search.py sweep \
  --explicit-policies research/experiments/2026/artifacts/phase1_14_mvbench_refinement_policies.json \
  --frame-count 8 \
  --output-dir research/experiments/2026/artifacts/phase1_14_mvbench_refinement \
  --out research/experiments/2026/artifacts/phase1_14_mvbench_refinement_summary.json \
  --allow-dirty
```

(Assumes `--explicit-policies` mode exists or is added. Fallback: use
`--max-policies` with a calibration that matches these five; confirm at
launch time.)

## Result

Pending.

## Interpretation

Pending.

## Links

- [phase 1.11 MVBench motion dev grid](2026-04-14-phase-1_11-planner-grid-mvbench-motion-dev.md)
- [phase 1.12 holdout evaluation](2026-04-14-phase-1_12-grid-winners-holdout.md)
- [execution plan round 7](../../../docs/execution-plan-round-7.md)
