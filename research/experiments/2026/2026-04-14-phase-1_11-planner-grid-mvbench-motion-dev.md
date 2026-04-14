# Phase 1.11: MVBench Motion Dev Planner Grid Sweep

## Preregistration

Objective:

- mirror phase 1.10 on MVBench motion dev: search the
  (statistic × thresholds × reuse_classes × max_age) space using the same
  calibration + sweep pipeline so cached policies on MVBench motion can be
  Pareto-checked against the phase 1.9 MVBench motion dev dense
  frame-budget curve

Claim register targets:

- `WP-2.6`
- `WP-3.1`
- `WP-3.3`

Reproduction mode:

- generalized benchmark search; method development on MVBench motion content

Track:

- A (quality at matched fresh-token-equivalent budget)

Hypotheses:

- H1 (transfer): Pareto-dominating policies on TOMATO motion dev (phase 1.10
  if any survive holdout) generalize to MVBench motion dev
- H2 (content-conditioned): MVBench motion dev's flatter dense-frame-budget
  curve (peak at 4 frames, plateaus rather than monotonically rising) means
  Pareto-dominance is HARDER to find on this slice — the dense baseline is
  already efficient at low frame counts
- H3 (calibration shape): MVBench motion dev calibration shows different bin
  occupancy than TOMATO (32/100/12 vs 4/80/60), so the same per-bin=1
  selection produces a different shape of grid coverage and may surface
  policies that TOMATO never examined

Acceptance band:

- calibration + sweep complete without runtime errors
- at least 15 distinct policies evaluated with valid metrics
- Pareto analysis produces at least one "candidate" policy

Rejection band:

- all searched policies dominated by some MVBench motion dense-N point;
  cached method does not beat dense frame subsampling on this slice at any
  operating point

Inconclusive:

- harness instability mid-sweep
- zero policies survive Pareto check on either dev or (later) holdout

Notes:

- DEV-only sweep, holdout gated to a separate commit
- no `--log-option-logprobs` initially (saves ~50% per-policy time); will
  be added in phase 1.13 stratification on selected winners only
- chunk_size=1 due to existing Metal-timeout operational constraint

## Execution

Run date: pending (awaits TOMATO motion dev sweep / phase 1.10 to free GPU)

Planned commands:

```
uv run python scripts/planner_grid_search.py sweep \
  --calibration research/experiments/2026/artifacts/phase1_10_mvbench_motion_dev_calibration.json \
  --frame-count 8 \
  --per-bin 1 \
  --max-policies 30 \
  --output-dir research/experiments/2026/artifacts/phase1_11_mvbench_motion_dev_grid \
  --out research/experiments/2026/artifacts/phase1_11_mvbench_motion_dev_grid_summary.json \
  --allow-dirty
```

Planned analysis:

```
uv run python scripts/pareto_analysis.py analyze \
  --cached research/experiments/2026/artifacts/phase1_11_mvbench_motion_dev_grid_summary.json \
  --dense research/experiments/2026/artifacts/phase1_9_mvbench_motion_frame_budget_dev.json \
  --total-frames 8 \
  --out research/experiments/2026/artifacts/phase1_11_mvbench_motion_dev_pareto.json
```

Calibration summary:

- `144` candidate policies calibrated
- bin counts: `0.50-0.70`: 32, `0.70-0.85`: 100, `0.85-0.95`: 12
- compared with TOMATO dev (4 / 80 / 60) the MVBench dev candidate space
  skews lower-reuse — most candidates land in the 0.50-0.85 range,
  reflecting that MVBench motion dev has more aggressive per-clip motion

## Result

Pending sweep run.

## Interpretation

Pending.

## Links

- [phase 1.9 MVBench motion frame-budget](2026-04-14-phase-1_9-mvbench-motion-frame-budget-baselines.md)
- [phase 1.10 TOMATO motion dev grid](2026-04-14-phase-1_10-planner-grid-tomato-motion-dev.md)
- [execution plan round 7](../../../docs/execution-plan-round-7.md)
