# Phase 1.47: Benchmark First-Frame Ablation

## Preregistration

Objective:

- determine how much of the current TOMATO and MVBench benchmark behavior
  survives when the model sees only frame `0`

Claim register targets:

- `WP-2.5`
- `WP-2.6`

Reproduction mode:

- generalized benchmark diagnosis

Track:

- A

Hypotheses:

- if the current TOMATO slice genuinely depends on temporal information, a
  first-frame-only dense run will collapse relative to the `8`-frame dense
  baseline
- if the current hosted MVBench slice is more endpoint- or scene-supported, a
  first-frame-only dense run will degrade less than TOMATO

Acceptance band:

- TOMATO first-frame dense accuracy is materially below the `8`-frame dense
  baseline on the same `30` items
- MVBench first-frame dense accuracy drops less than TOMATO on the same hosted
  subset

Rejection band:

- first-frame-only accuracy stays near the full `8`-frame dense baselines on
  both benchmarks, which would imply that the current contrast is not really
  about temporal information

Notes:

- the runner uses `cache_mode = identity` with `frame_count = 1`
- in this setup dense and cached are intentionally identical; the experiment is
  about temporal necessity, not cache-path differences

## Execution

Run date:

- 2026-04-14

Artifacts:

- TOMATO first-frame run:
  [phase1_47_tomato_first_frame.jsonl](artifacts/phase1_47_tomato_first_frame.jsonl)
- TOMATO first-frame summary:
  [phase1_47_tomato_first_frame_summary.json](artifacts/phase1_47_tomato_first_frame_summary.json)
- MVBench first-frame run:
  [phase1_48_mvbench_first_frame.jsonl](artifacts/phase1_48_mvbench_first_frame.jsonl)
- MVBench first-frame summary:
  [phase1_48_mvbench_first_frame_summary.json](artifacts/phase1_48_mvbench_first_frame_summary.json)
- Combined comparison:
  [phase1_47_benchmark_first_frame_ablation.json](artifacts/phase1_47_benchmark_first_frame_ablation.json)

Commands:

```bash
uv run python scripts/run_benchmark_track_a.py run \
  --benchmark tomato \
  --per-group 5 \
  --chunk-size 1 \
  --frame-count 1 \
  --max-tokens 32 \
  --cache-mode identity \
  --output-path research/experiments/2026/artifacts/phase1_47_tomato_first_frame.jsonl \
  --summary-path research/experiments/2026/artifacts/phase1_47_tomato_first_frame_summary.json \
  --stop-file /tmp/phase1_47_stop

uv run python scripts/run_benchmark_track_a.py run \
  --benchmark mvbench \
  --per-group 3 \
  --chunk-size 1 \
  --frame-count 1 \
  --max-tokens 32 \
  --cache-mode identity \
  --output-path research/experiments/2026/artifacts/phase1_48_mvbench_first_frame.jsonl \
  --summary-path research/experiments/2026/artifacts/phase1_48_mvbench_first_frame_summary.json \
  --stop-file /tmp/phase1_48_stop
```

## Result

Preregistration outcome:

- Accepted

Observed outcome:

- TOMATO first-frame-only dense accuracy collapsed from `9/30 = 0.300` to
  `2/30 = 0.067`
- MVBench first-frame-only dense accuracy dropped from `34/54 = 0.630` to
  `28/54 = 0.519`
- relative drops:
  - TOMATO delta: `-0.233`
  - MVBench delta: `-0.111`

TOMATO by split:

- full `8`-frame dense:
  - `count`: `0.2`
  - `direction`: `0.6`
  - `rotation`: `0.4`
  - `shape_trend`: `0.4`
  - `velocity_frequency`: `0.0`
  - `visual_cues`: `0.2`
- first-frame dense:
  - `count`: `0.0`
  - `direction`: `0.0`
  - `rotation`: `0.0`
  - `shape_trend`: `0.0`
  - `velocity_frequency`: `0.0`
  - `visual_cues`: `0.4`

Most important TOMATO detail:

- only the `visual_cues` split retained any first-frame solvability
- all five `direction` items dropped from `3/5` correct to `0/5`

MVBench hosted slice:

- several hosted tasks remained partly or strongly solvable from frame `0`:
  - `moving_count`: `1.0`
  - `unexpected_action`: `1.0`
  - `scene_transition`: `0.667`
  - `object_interaction`: `0.667`
  - `moving_attribute`: `0.667`
- several others degraded, but not enough to collapse the aggregate slice:
  - `action_antonym`: `1.0` to `0.333`
  - `action_prediction`: `1.0` to `0.333`
  - `character_order`: `1.0` to `0.667`

## Interpretation

This is the strongest current evidence that the TOMATO versus MVBench contrast
is content-driven rather than parser-driven.

What the first-frame ablation now establishes:

- the current TOMATO `30`-item slice is genuinely temporal on this stack
  - frame `0` alone recovers only `2/30`
  - the earlier `0.833` dense-versus-cached agreement is therefore not a
    prompt-prior artifact disguised as temporal reasoning
- the current hosted MVBench `54`-item slice is less temporally concentrated
  than TOMATO
  - frame `0` alone still recovers `28/54`
  - that helps explain why same-position cached reuse can remain competitive on
    MVBench while weakening on TOMATO

What this does not yet establish:

- that the entire TOMATO versus MVBench gap is caused by temporal concentration
  alone
- that the current planner is optimal once content class is held fixed
- that refresh policy or block statistic no longer matter

## Consequences

- targeted TOMATO diagnosis should stay ahead of any larger blind TOMATO rerun
- the next high-value benchmark step is now a planner and refresh study on the
  TOMATO disagreement items, especially `direction`
- the current paper story should describe the benchmark contrast as
  content-conditioned until stronger matched-content evidence says otherwise

## Links

- [2026-04-13-phase-1_4-tomato-benchmark-subset.md](2026-04-13-phase-1_4-tomato-benchmark-subset.md)
- [2026-04-13-phase-1_5-mvbench-benchmark-subset.md](2026-04-13-phase-1_5-mvbench-benchmark-subset.md)
- [2026-04-14-phase-1_45-benchmark-diagnostics.md](2026-04-14-phase-1_45-benchmark-diagnostics.md)
- [2026-04-14-phase-1_46-benchmark-path-controls.md](2026-04-14-phase-1_46-benchmark-path-controls.md)
