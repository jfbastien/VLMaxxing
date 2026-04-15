# Phase 1.24: TOMATO Motion Holdout Dense Curve Backfill

## Preregistration

Objective:

- build the missing dense-N baseline cells at `frame_count ∈ {2, 3, 8}`
  on the TOMATO motion holdout slice, so that phase 1.12 TOMATO cached
  survivors can be matched against a complete dense frame-budget curve
- without this backfill, a cached point at fresh-frames ≈ 3.4 sits in
  an unmeasured region of the curve between dense-1 and dense-4, so
  Pareto domination claims cannot be made rigorously.

Claim register targets:

- `WP-2.5`, `WP-3.1`, `WP-3.3` — all conditional on phase 1.12 TOMATO
  holdout having at least one cached survivor

Reproduction mode:

- matched frame-budget baseline building on a preregistered holdout
  slice

Track:

- A

Gating:

- runs immediately after phase 1.12 TOMATO holdout completes its last
  cached policy (5/5), regardless of outcome
- if every cached policy lands below dense-6 holdout accuracy, dense
  backfill still matters for interpretability but is no longer
  paper-critical

Hypotheses:

- H1 (plateau): TOMATO holdout dense curve plateaus somewhere between
  dense-4 (0.133) and dense-6 (0.267); dense-3 and dense-8 should land
  within that band
- H2 (monotonicity in the middle): dense-3 ≥ dense-4 (dense-4 was the
  low point on TOMATO holdout, an unusual shape)
- H3 (tail behavior): dense-8 ≤ dense-6 (TOMATO holdout is confidence-
  limited past 6 frames)

Acceptance band:

- 3 new dense cells evaluated cleanly
- Wilson CI intervals computed per cell
- union curve at frames {1, 2, 3, 4, 6, 8} emitted as a single JSON

Rejection band:

- harness failures on ≥ 1 cell (N=15 Metal-timeouts etc.); degrade
  interpretation but do not block everything

Inconclusive:

- sampling imbalance on N=15 makes CIs too wide to order any adjacent
  cells

Cells:

1. dense at frame_count=2 on `tomato_motion_holdout_v1.toml`
2. dense at frame_count=3 on same
3. dense at frame_count=8 on same

Runtime: 3 cells × ~12 min per cell ≈ 0.6 hrs GPU (phase 1.8 ran dense
at {1, 4, 6} in similar time; dense runs are typically faster than
cached runs because planner classification is skipped).

## Execution

Pending phase 1.12 TOMATO holdout completion.

Planned commands (one per cell, using the existing
`scripts/run_benchmark_track_a.py run` path with `--cache-mode off` or
equivalent dense-only flag; confirm correct flag at launch):

```
uv run python scripts/run_benchmark_track_a.py run \
  --benchmark tomato \
  --manifest research/benchmark_manifests/tomato_motion_holdout_v1.toml \
  --frame-count <N> \
  --chunk-size 1 \
  --cache-mode off \
  --output-path research/experiments/2026/artifacts/phase1_24_tomato_motion_holdout_dense_<N>.jsonl \
  --summary-path research/experiments/2026/artifacts/phase1_24_tomato_motion_holdout_dense_<N>_summary.json \
  --allow-dirty
```

Then merge into a single `phase1_24_tomato_motion_holdout_dense_full.json`
compatible with `pareto_analysis.py analyze`.

## Result

Pending.

## Interpretation

Pending.

## Links

- [phase 1.8 motion frame-budget baselines](2026-04-14-phase-1_8-motion-frame-budget-baselines.md)
- [phase 1.12 holdout evaluation](2026-04-14-phase-1_12-grid-winners-holdout.md)
- [execution plan round 7](../../../docs/execution-plan-round-7.md)
