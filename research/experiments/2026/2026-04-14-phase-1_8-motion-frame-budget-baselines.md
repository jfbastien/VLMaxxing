# Phase 1.8: Motion Frame-Budget Baselines

## Preregistration

Objective:

- compare the current cached motion policies against matched dense frame-budget
  baselines instead of comparing cached policies only against one another
- test whether the best current cached motion policy still has a quality
  advantage once dense baselines are given a comparable fresh-vision budget

Claim register targets:

- `WP-2.5`
- `WP-3.3`

Reproduction mode:

- generalized benchmark diagnosis on frozen TOMATO motion dev and holdout
  manifests

Track:

- A

Hypotheses:

- on the motion dev slice, dense `1` to `4` frame baselines will remain much
  weaker than the dense `8`-frame path
- on the dev slice, `mean + max_age = 4` should stay competitive with the
  dense curve at a lower fresh-vision budget than dense `6`
- the holdout slice may weaken or overturn that apparent dev advantage

Acceptance band:

- at least one cached dev policy remains competitive with a denser baseline at
  a lower fresh-vision token-equivalent budget
- the holdout slice materially clarifies whether that dev result generalizes

Rejection band:

- dense baselines dominate the cached policies cleanly at similar or lower
  fresh-vision budgets on both dev and holdout

Notes:

- dense frame-budget baselines are run through benchmark-path identity mode so
  the benchmark runner, prompt formatting, and answer extraction stay aligned
  with the cached-policy path
- `fresh_vision_token_equivalent` is a Track A budget heuristic on these
  fixed-size benchmark inputs, not a Track B speedup claim
- the dense `8`-frame baselines were already available from Phase 1.6; this
  phase reruns the dev endpoint so the full dev curve lives in one artifact and
  samples only the informative holdout points (`1`, `4`, `6`)

## Execution

Run date:

- 2026-04-14

Manifests:

- dev:
  [tomato_motion_dev_v1.toml](../../benchmark_manifests/tomato_motion_dev_v1.toml)
- holdout:
  [tomato_motion_holdout_v1.toml](../../benchmark_manifests/tomato_motion_holdout_v1.toml)

Artifact:

- [phase1_8_motion_frame_budget_baselines.json](artifacts/phase1_8_motion_frame_budget_baselines.json)

Command pattern:

```bash
uv run python scripts/frame_budget_baseline.py \
  --manifest <manifest> \
  --frame-counts <counts...> \
  --output-dir /tmp/<run-dir> \
  --summary-path /tmp/<run>.json
```

Executed runs:

- dev: `1 2 3 4 6 8`
- holdout: `1 4 6`

## Result

Preregistration outcome:

- Mixed

Observed dense frame-budget curves:

Dev slice (`15` items):

- dense `1`: `0.000`, CI `[0.000, 0.204]`, fresh tokens `400`
- dense `2`: `0.267`, CI `[0.109, 0.520]`, fresh tokens `800`
- dense `3`: `0.267`, CI `[0.109, 0.520]`, fresh tokens `1200`
- dense `4`: `0.267`, CI `[0.109, 0.520]`, fresh tokens `1600`
- dense `6`: `0.400`, CI `[0.198, 0.643]`, fresh tokens `2400`
- dense `8`: `0.467`, CI `[0.248, 0.699]`, fresh tokens `3200`

Holdout slice (`15` items):

- dense `1`: `0.200`, CI `[0.070, 0.452]`, fresh tokens `400`
- dense `4`: `0.133`, CI `[0.037, 0.379]`, fresh tokens `1600`
- dense `6`: `0.267`, CI `[0.109, 0.520]`, fresh tokens `2400`
- dense `8` control from Phase 1.6: `0.267`

Matched cached-policy comparisons:

Dev slice:

- default mean:
  - cached accuracy `0.267`
  - agreement `0.733`
  - active reuse `0.798`
  - fresh-frame equivalent `2.414`
  - fresh tokens `965.7`
- `mean + max_age = 4`:
  - cached accuracy `0.400`
  - agreement `0.867`
  - active reuse `0.698`
  - fresh-frame equivalent `3.116`
  - fresh tokens `1246.5`
- `STATIC`-only:
  - cached accuracy `0.333`
  - agreement `0.800`
  - active reuse `0.635`
  - fresh-frame equivalent `3.554`
  - fresh tokens `1421.5`

Holdout slice:

- default mean:
  - cached accuracy `0.200`
  - agreement `0.867`
  - active reuse `0.832`
  - fresh-frame equivalent `2.174`
  - fresh tokens `869.5`
- `mean + max_age = 4`:
  - cached accuracy `0.200`
  - agreement `0.800`
  - active reuse `0.726`
  - fresh-frame equivalent `2.920`
  - fresh tokens `1168.1`

## Interpretation

The dev and holdout curves say different things, and both matter.

Dev slice:

- dense baselines plateaued at `0.267` all the way from `2` through `4`
  frames
- the first real dense recovery did not happen until `6` frames, where dense
  reached `0.400`
- `mean + max_age = 4` reached the same `0.400` cached accuracy at a much
  lower fresh-vision budget:
  `1246.5` token-equivalent versus dense `6` at `2400`

That is the strongest positive result in the tranche.

- on this motion-heavy dev slice, bounded-age cached reuse is not just better
  than the default cached policy
- it also matches the dense `6`-frame baseline while spending about half the
  fresh-vision token budget

Holdout slice:

- the dense curve is much less smooth
- dense `4` is actually worse than dense `1`
- dense `6` only recovers to the same `0.267` accuracy as the existing dense
  `8`-frame holdout baseline
- neither cached holdout policy beats that holdout dense `6`/`8` level; both
  stay at cached `0.200`

That is the main negative result.

- the dev budget win is real
- but it does not yet generalize cleanly to the disjoint holdout
- the holdout slice appears to load a different failure regime, especially in
  `shape_trend`, where dense `6` still stays at `0.0`

So the combined reading is:

- there is now a genuine quality-versus-fresh-budget signal on the motion dev
  slice
- the signal is promising enough to justify more method work
- but it is not yet broad enough for a paper claim without better
  stratification and more holdout evidence

## Consequences

- future cached-policy notes should compare against matched dense frame-budget
  baselines, not just against the default cached policy
- the next high-value diagnostic is answer-margin or option-logprob logging so
  dev-versus-holdout differences can be separated into model-uncertainty versus
  cache-staleness effects
- the next benchmark comparison should extend this same budget analysis to
  matched MVBench motion-heavy tasks
- the baseline driver itself should eventually gain a dense-only fast path so
  future budget controls do not pay an unnecessary second identity generation

## Links

- [2026-04-14-phase-1_6-motion-policy-sweep.md](2026-04-14-phase-1_6-motion-policy-sweep.md)
- [2026-04-14-phase-1_7-motion-statistic-comparison.md](2026-04-14-phase-1_7-motion-statistic-comparison.md)
- [docs/methodology/pareto-reporting.md](../../../docs/methodology/pareto-reporting.md)
