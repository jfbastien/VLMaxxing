# Phase 1.49: TOMATO Direction Refresh Sweep

## Preregistration

Objective:

- determine whether the current TOMATO `direction` failures are caused by
  long-lived reuse under the default no-refresh policy

Claim register targets:

- `WP-2.5`
- `WP-3.3`

Reproduction mode:

- generalized benchmark diagnosis

Track:

- A

Hypotheses:

- if the current `direction` failures are genuinely caching-induced, shorter
  refresh intervals should recover cached accuracy and agreement toward the
  dense baseline
- a full refresh every frame should collapse the cached path back to exact dense
  behavior

Acceptance band:

- `refresh_interval = 1` recovers exact dense agreement on the `direction`
  subset
- at least one intermediate refresh interval improves materially over the
  no-refresh default

Rejection band:

- cached accuracy stays weak even when `refresh_interval = 1`, which would
  imply a deeper benchmark-path or baseline issue rather than a refresh-policy
  issue

Notes:

- this sweep stays on the existing five `direction` items from the local
  TOMATO subset
- the benchmark runner uses the new pad-masked reuse accounting

## Execution

Run date:

- 2026-04-14

Artifacts:

- no-refresh summary:
  [phase1_49_tomato_direction_refresh0_summary.json](artifacts/phase1_49_tomato_direction_refresh0_summary.json)
- refresh-`1` summary:
  [phase1_49_tomato_direction_refresh1_summary.json](artifacts/phase1_49_tomato_direction_refresh1_summary.json)
- refresh-`2` summary:
  [phase1_49_tomato_direction_refresh2_summary.json](artifacts/phase1_49_tomato_direction_refresh2_summary.json)
- refresh-`4` summary:
  [phase1_49_tomato_direction_refresh4_summary.json](artifacts/phase1_49_tomato_direction_refresh4_summary.json)
- combined comparison:
  [phase1_49_tomato_direction_refresh_sweep.json](artifacts/phase1_49_tomato_direction_refresh_sweep.json)

Command pattern:

```bash
uv run python scripts/run_benchmark_track_a.py run \
  --benchmark tomato \
  --groups direction \
  --per-group 5 \
  --chunk-size 1 \
  --frame-count 8 \
  --max-tokens 32 \
  --cache-mode default \
  --refresh-interval <0|1|2|4> \
  --output-path research/experiments/2026/artifacts/phase1_49_tomato_direction_refresh<k>.jsonl \
  --summary-path research/experiments/2026/artifacts/phase1_49_tomato_direction_refresh<k>_summary.json
```

## Result

Preregistration outcome:

- Accepted

Observed outcome:

- no refresh (`0`):
  - dense accuracy `0.6`
  - cached accuracy `0.2`
  - agreement `0.6`
  - active reuse `0.8579`
- refresh `1`:
  - dense accuracy `0.6`
  - cached accuracy `0.6`
  - agreement `1.0`
  - active reuse `0.0`
- refresh `2`:
  - dense accuracy `0.6`
  - cached accuracy `0.6`
  - agreement `1.0`
  - active reuse `0.4866`
- refresh `4`:
  - dense accuracy `0.6`
  - cached accuracy `0.6`
  - agreement `1.0`
  - active reuse `0.7324`

## Interpretation

This five-item refresh comparison makes policy staleness the leading
explanation for the current TOMATO `direction` weakness on this subset, rather
than an obvious benchmark-path breakage.

What it shows:

- no-refresh same-position reuse is too aggressive for this five-item
  `direction` subset at the default `(3, 8)` thresholds
- even a modest refresh policy repairs the failure on this subset
- the strongest result is `refresh_interval = 4`:
  - cached recovers to exact dense agreement
  - active reuse stays high at `0.7324`

What it does not show:

- that `refresh_interval = 4` will generalize across all TOMATO splits
- that the current pixel-diff statistic is already optimal
- that refresh alone is enough for the broader benchmark lane

## Consequences

- the next TOMATO work should treat refresh policy as a first-class variable,
  not as a cleanup detail
- the current planner story is now sharper:
  same-position reuse has a real temporal "there there," but the no-refresh
  default is too brittle on motion-heavy temporal-direction items
- this is exactly the kind of leverage we need before pushing toward a stronger
  training-free planner or a later Track B path

## Links

- [2026-04-13-phase-1_4-tomato-benchmark-subset.md](2026-04-13-phase-1_4-tomato-benchmark-subset.md)
- [2026-04-14-phase-1_46-benchmark-path-controls.md](2026-04-14-phase-1_46-benchmark-path-controls.md)
- [2026-04-14-phase-1_47-benchmark-first-frame-ablation.md](2026-04-14-phase-1_47-benchmark-first-frame-ablation.md)
