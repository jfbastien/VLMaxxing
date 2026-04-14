# Phase 1.46: Benchmark Path Identity and Pad-Masked Reuse

## Preregistration

Objective:

- validate the Qwen `7B` benchmark runner's dense-through-cache identity path
  directly on the benchmark-native code path
- add active-region reuse accounting so padded borders stop contaminating the
  main benchmark reuse number

Claim register targets:

- `WP-2.5`
- `WP-2.6`

Reproduction mode:

- generalized reproduction control

Track:

- A

Hypotheses:

- on the benchmark-native runner, dense-direct generation and unchanged
  dense-through-cache generation will remain exactly identical on smoke items
  from TOMATO and MVBench
- raw padded reuse will exceed active-region reuse on default benchmark items,
  confirming that square padding was inflating the descriptive reuse number

Acceptance band:

- dense text and dense-through-cache identity text match exactly on both smoke
  items
- active-region reuse is less than or equal to raw reuse on the default cached
  runs, with a strict gap on at least one item

Rejection band:

- the benchmark runner's identity path changes the answer relative to dense
- raw and active reuse stay identical on padded default items, suggesting the
  masking code is ineffective

Notes:

- this is a benchmark-path control, not a benchmark-quality claim
- identity mode does not run the planner, so reuse fields are recorded as
  `null` rather than as synthetic `1.0` placeholders

## Execution

Run date:

- 2026-04-14
- clean-tree summary rerun:
  - 2026-04-14 after the benchmark runner began failing closed on dirty trees

Artifact:

- [phase1_46_benchmark_controls.json](artifacts/phase1_46_benchmark_controls.json)
- clean rerun summaries:
  - [phase1_46_tomato_identity_summary.json](artifacts/phase1_46_tomato_identity_summary.json)
  - [phase1_46_tomato_default_summary.json](artifacts/phase1_46_tomato_default_summary.json)
  - [phase1_46_mvbench_identity_summary.json](artifacts/phase1_46_mvbench_identity_summary.json)
  - [phase1_46_mvbench_default_summary.json](artifacts/phase1_46_mvbench_default_summary.json)

Runner updates used:

- benchmark runner now records:
  - `reuse_ratio_mean_active`
  - `reuse_ratio_mean_raw`
  - `cache_mode`
- benchmark runner now supports `--cache-mode identity`

Smoke items:

- TOMATO:
  - `tomato:direction:0231-04`
- MVBench:
  - `mvbench:moving_direction:0`

## Result

Preregistration outcome:

- Accepted

Observed outcome:

- benchmark-path identity held exactly on both smoke items:
  - TOMATO identity smoke:
    - dense text `D`
    - cached text `D`
    - exact match `true`
  - MVBench identity smoke:
    - dense text `A`
    - cached text `A`
    - exact match `true`
- default cached runs exposed padding inflation in the raw reuse number:
  - TOMATO default smoke:
    - active reuse `0.8479`
    - raw reuse `0.9236`
    - raw minus active `0.0757`
  - MVBench default smoke:
    - active reuse `0.9470`
    - raw reuse `0.9654`
    - raw minus active `0.0183`
- the clean rerun removed a stale artifact inconsistency from the old summary
  JSONs:
  - earlier identity summaries were produced before identity-mode reuse was
    normalized to `null`
  - the current summary artifacts now record:
    - `git_dirty = false`
    - `reuse_ratio_mean = null`
    - `reuse_ratio_mean_active = null`
    - `reuse_ratio_mean_raw = null`

## Interpretation

Two benchmark-path controls are now in place.

First, the benchmark-native Qwen `7B` runner now has a direct identity smoke.

- dense-direct and dense-through-cache identity match exactly on both the TOMATO
  and MVBench smoke items
- that does not replace larger semantic evaluation, but it removes an important
  confound before the next targeted TOMATO diagnosis

Second, the benchmark runner now treats pad-masked reuse as the main reported
reuse number.

- square-padded `560 x 560` benchmark frames were indeed inflating the old raw
  reuse ratio
- the inflation was modest on the MVBench smoke item and large enough to matter
  on the TOMATO smoke item
- future cross-benchmark reuse analysis should therefore use
  `reuse_ratio_mean_active`, with `reuse_ratio_mean_raw` retained only as a
  descriptive auxiliary field

## Consequences

- benchmark-path identity no longer needs to stay hypothetical in the plan
- targeted TOMATO diagnosis can now focus on planner behavior rather than on an
  unchecked benchmark cache interface or padded-border reuse inflation

## Links

- [docs/benchmark-setup.md](../../../docs/benchmark-setup.md)
- [docs/reproduction-status.md](../../../docs/reproduction-status.md)
- [2026-04-13-phase-1_4-tomato-benchmark-subset.md](2026-04-13-phase-1_4-tomato-benchmark-subset.md)
- [2026-04-13-phase-1_5-mvbench-benchmark-subset.md](2026-04-13-phase-1_5-mvbench-benchmark-subset.md)
