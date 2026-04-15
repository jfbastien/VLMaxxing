# Phase 1.12.B: Cross-Benchmark-Discovered Winner → MVBench Holdout (single-shot)

## Preregistration

Objective:

- Phase 1.16 cell B produced an unexpected MVBench motion dev result:
  `max_abs(8,32) static+shifted age=4` achieves cached_accuracy = 0.800
  (12/15), fresh_frames = 3.78 — higher accuracy than the phase 1.11
  MVBench-native winner `max_abs(8,32) static+shifted noage` (0.733 at
  fresh=3.22). This specific policy was NOT in the phase 1.11 grid
  (which sampled noage + age=8 but not age=4 for this threshold set).
- The policy was selected by performance on the TOMATO motion dev
  slice, NOT by MVBench dev tuning — so there is no
  dev-to-MVBench-holdout contamination. A single-shot MVBench holdout
  evaluation of this policy is methodologically clean.

Claim register targets:

- `WP-2.6`, `WP-3.1`, `WP-3.3` — if this holdout passes, MVBench
  motion is no longer a clean rejection; the paper story becomes
  content-conditioned across both benchmarks.

Reproduction mode:

- generalized benchmark, single-shot holdout evaluation, no further
  tuning allowed.

Track: A.

Gating:

- runs immediately; GPU free after phase 1.16 cell B completion.
- this is a one-shot evaluation. If it fails, no rerun.

Hypotheses:

- **H1 (transfer holds)**: `max_abs(8,32) static+shifted age=4` on
  MVBench motion holdout achieves cached_accuracy ≥ 0.600, matching
  or beating dense-3/4 holdout accuracy (both 0.600), at effective
  fresh_frames ≤ 4.
- **H2 (transfer fails)**: cached accuracy < 0.600 on MVBench holdout;
  the dev-side 0.800 was N=15 slice noise (same failure pattern as
  phase 1.12 MVBench rejection).
- **H3 (high-confidence discovery)**: at cached ≥ 0.667 on holdout,
  this is a genuine cross-benchmark Pareto winner and the paper
  story changes materially.

Acceptance band:

- H1 passes: cached_accuracy ≥ 0.600, matching matched-budget dense
  holdout point; inter-cached skyline winner on MVBench holdout.

Rejection band:

- cached_accuracy < 0.467 (worse than 7/15) on holdout → strict
  rejection; MVBench holdout is a confirmed null regardless of
  dev winner source.

Inconclusive:

- cached between 0.467 and 0.600 → ambiguous; needs N=30 (phase
  1.21 is demoted but can be re-activated for this specific
  winner).

## Execution

Command:

```
uv run python scripts/planner_grid_search.py run-explicit \
  --manifest research/benchmark_manifests/mvbench_motion_holdout_v1.toml \
  --policies research/experiments/2026/artifacts/phase1_16_tomato_winner_on_mvbench_policies.json \
  --frame-count 8 \
  --output-dir research/experiments/2026/artifacts/phase1_12b_crossbench_winner_mvbench_holdout \
  --out research/experiments/2026/artifacts/phase1_12b_crossbench_winner_mvbench_holdout_summary.json \
  --allow-dirty
```

## Result

Pending.

## Interpretation

Pending.

## Links

- [phase 1.12 holdout evaluation (phase 1 of the discipline gate)](2026-04-14-phase-1_12-grid-winners-holdout.md)
- [phase 1.16 cross-benchmark transfer](2026-04-15-phase-1_16-cross-benchmark-winner-transfer.md)
- [phase 1.11 MVBench motion dev grid](2026-04-14-phase-1_11-planner-grid-mvbench-motion-dev.md)
- [docs/research-strategy-post-codecsight.md](../../../docs/research-strategy-post-codecsight.md)
