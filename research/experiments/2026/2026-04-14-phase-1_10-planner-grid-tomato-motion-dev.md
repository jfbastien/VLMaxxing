# Phase 1.10: TOMATO Motion Dev Planner Grid Sweep

## Preregistration

Objective:

- search the (statistic × thresholds × reuse_classes × max_age) space far
  more thoroughly than phase 1.7 did, using feature replay to keep the
  per-policy cost cheap, and identify Pareto-dominant cached policies
  relative to the phase 1.8 TOMATO motion dev dense frame-budget curve

Claim register targets:

- `WP-2.5`
- `WP-3.1`
- `WP-3.3`

Reproduction mode:

- generalized benchmark search; this is method development, not a claim

Track:

- A (quality at matched fresh-token-equivalent budget)

Context the earlier phases left unanswered:

- phase 1.6 tested three policies (default mean, STATIC-only, mean+max_age=4)
- phase 1.7 tested three additional statistic variants at one threshold pair
  each
- none of these eight total points adequately cover the space this sweep
  targets: 4 statistics × ~5 threshold pairs each × 2 reuse classes ×
  4 max_age values = up to ~160 raw candidates before dedup

Hypotheses:

- H1: at least one cached policy in the searched grid achieves cached
  accuracy >= the best phase-1.8 TOMATO motion dev dense-frame-budget point
  (dense-6 = 0.400) at fresh-token-equivalent budget < dense-6's 2400 tokens
- H2: the Pareto frontier on dev is not a single-cell winner; multiple
  (statistic, max_age, reuse_classes) combinations approach or match the
  frontier, which would justify broader holdout validation
- H3: CHANGED_PIXEL_FRACTION and MAX_ABS at lower thresholds combined with
  max_age=4 will find policies competitive with mean+max_age=4 (dev-side
  cached 0.400 at 1247 fresh-token budget) but at different reuse levels

Acceptance band for this phase (method-search, not method-win):

- calibration + sweep both complete without runtime errors
- at least 15 distinct policies evaluated with valid cached_accuracy,
  agreement, reuse_ratio_mean_active, and effective_fresh_frames metrics
- the Pareto analysis produces at least one policy flagged as "candidate"
  (not dominated by any dense frame-budget point)

Rejection band:

- all searched policies are dominated by dense-N for some N ≤ 8; the method
  does not beat simple frame subsampling on the dev slice at any operating
  point. This outcome would be reported honestly and would redirect the
  project toward composition with token-pruning methods (FastV / SparseVLM)
  instead of cached-policy tuning.

Inconclusive:

- fewer than ~15 policies produce valid outputs (e.g. all-NOVEL
  classifications at aggressive thresholds cause chunked runner to choke)
- Metal timeout or harness instability forces reruns at different starting
  states mid-sweep

Notes:

- this is a DEV-only sweep. Holdout evaluation is deliberately gated on a
  separate commit so the DEV search doesn't tune against holdout.
- `--log-option-logprobs` is enabled so phase 1.11 can stratify items into
  confidence-limited vs staleness-limited without another run
- chunk_size remains 1 per the existing Metal-timeout operational constraint

## Execution

Run date:

- pending (awaits MVBench motion holdout frame-budget to finish using the
  GPU so this sweep has exclusive access)

Planned commands (recorded here so the preregistered intent is auditable):

```
# already completed:
uv run python scripts/planner_grid_search.py calibrate \
  --manifest research/benchmark_manifests/tomato_motion_dev_v1.toml \
  --frame-count 8 \
  --out research/experiments/2026/artifacts/phase1_10_tomato_motion_dev_calibration.json

# about to run:
uv run python scripts/planner_grid_search.py sweep \
  --calibration research/experiments/2026/artifacts/phase1_10_tomato_motion_dev_calibration.json \
  --frame-count 8 \
  --per-bin 1 \
  --output-dir research/experiments/2026/artifacts/phase1_10_tomato_motion_dev_grid \
  --out research/experiments/2026/artifacts/phase1_10_tomato_motion_dev_grid_summary.json \
  --log-option-logprobs \
  --allow-dirty
```

Planned analysis:

```
uv run python scripts/pareto_analysis.py analyze \
  --cached research/experiments/2026/artifacts/phase1_10_tomato_motion_dev_grid_summary.json \
  --dense research/experiments/2026/artifacts/phase1_8_motion_frame_budget_baselines.json \
  --total-frames 8 \
  --out research/experiments/2026/artifacts/phase1_10_tomato_motion_dev_pareto.json
```

Calibration summary (from the committed JSON):

- `144` candidate policies calibrated
- bin counts:
  - `0.50-0.70`: 4 policies
  - `0.70-0.85`: 80 policies
  - `0.85-0.95`: 60 policies
- no policies land at < 0.50 or >= 0.95 active reuse on this slice under the
  default candidate space — suggests the space is already well-suited to
  this content class

## Result

_Pending sweep run. Will be populated with:_

- count of policies evaluated
- top-5 Pareto candidates by cached_accuracy at matched budget
- per-group breakdown on the `direction` hard bucket
- summary of the `mean + max_age = 4` dev-side baseline vs newly-found
  policies at similar or lower fresh-token budget

## Interpretation

_To be written after the sweep completes._

## Links

- [phase 1.6 policy sweep](2026-04-14-phase-1_6-motion-policy-sweep.md)
- [phase 1.7 statistic sweep](2026-04-14-phase-1_7-motion-statistic-sweep.md)
- [phase 1.8 frame-budget baselines](2026-04-14-phase-1_8-motion-frame-budget-baselines.md)
- [execution plan round 7](../../../docs/execution-plan-round-7.md)
