# Phase 1.7: Motion Statistic Comparison

## Preregistration

Objective:

- test whether concentration-sensitive per-block statistics recover the current
  motion-heavy TOMATO failures better than the mean-diff planner
- compare statistic-only policy changes against the existing motion dev
  baselines before spending more runtime budget on broader reruns

Claim register targets:

- `WP-2.5`
- `WP-3.1`
- `WP-3.3`

Reproduction mode:

- generalized benchmark diagnosis on a frozen motion-heavy dev slice

Track:

- A

Hypotheses:

- if block-mean dilution is the main current failure mode, then at least one
  concentration-sensitive statistic should beat the default mean planner on the
  TOMATO motion dev slice
- `top_k_mean` or `max_abs` at roughly the same active reuse budget as the
  default mean planner should improve cached accuracy or agreement without
  requiring bounded age
- if statistic choice alone is enough, the `direction` bucket should improve
  over the default mean planner

Acceptance band:

- at least one statistic-only policy materially improves agreement or cached
  accuracy over the default mean planner on the dev slice
- the improvement is not merely a budget effect already matched by the
  `mean + max_age = 4` baseline

Rejection band:

- statistic-only changes stay flat or worse than the default mean planner
- the `direction` bucket remains unrepaired under the tested statistic-only
  policies

Notes:

- this phase intentionally reuses the frozen TOMATO motion dev manifest
- all runs started from a clean tree and wrote to `/tmp` during execution, then
  the completed artifacts were copied back into the repo
- the existing motion dev baselines from Phase 1.6 are treated as controls:
  default mean, `STATIC`-only, and `mean + max_age = 4`

## Execution

Run date:

- 2026-04-14

Manifest:

- dev:
  [tomato_motion_dev_v1.toml](../benchmark_manifests/tomato_motion_dev_v1.toml)

Combined artifact:

- [phase1_7_statistic_sweep.json](artifacts/phase1_7_statistic_sweep.json)

Run artifacts:

- `top_k_mean (12, 36)`:
  [phase1_7_tomato_motion_topk12_36_summary.json](artifacts/phase1_7_tomato_motion_topk12_36_summary.json)
- `max_abs (24, 96)`:
  [phase1_7_tomato_motion_max24_96_summary.json](artifacts/phase1_7_tomato_motion_max24_96_summary.json)
- `max_abs (12, 48)`:
  [phase1_7_tomato_motion_max12_48_summary.json](artifacts/phase1_7_tomato_motion_max12_48_summary.json)

Existing dev baselines used for comparison:

- default mean:
  [phase1_6_tomato_motion_default_mean_summary.json](artifacts/phase1_6_tomato_motion_default_mean_summary.json)
- `STATIC`-only:
  [phase1_6_tomato_motion_mean_static_only_summary.json](artifacts/phase1_6_tomato_motion_mean_static_only_summary.json)
- `mean + max_age = 4`:
  [phase1_6_tomato_motion_mean_age4_summary.json](artifacts/phase1_6_tomato_motion_mean_age4_summary.json)

Policies tested:

- default mean control:
  - statistic `mean`
  - thresholds `(3, 8)`
  - reuse classes `static,shifted`
  - `max_age = none`
- `top_k_mean`:
  - statistic `top_k_mean`
  - thresholds `(12, 36)`
  - `top_k = 16`
  - reuse classes `static,shifted`
  - `max_age = none`
- `max_abs`, same-budget control:
  - statistic `max_abs`
  - thresholds `(24, 96)`
  - reuse classes `static,shifted`
  - `max_age = none`
- `max_abs`, lower-budget control:
  - statistic `max_abs`
  - thresholds `(12, 48)`
  - reuse classes `static,shifted`
  - `max_age = none`

CPU-only calibration pass before the model runs:

- active reuse estimates on the same dev manifest suggested:
  - default mean `(3, 8)`: `0.798`
  - `top_k_mean (12, 36)`: `0.707`
  - `max_abs (24, 96)`: `0.802`
  - `max_abs (12, 48)`: `0.703`

That is why these three statistic settings were chosen:

- `max_abs (24, 96)` is the same-budget control against default mean
- `top_k_mean (12, 36)` and `max_abs (12, 48)` sit near the lower active-reuse
  budget of the earlier `mean + max_age = 4` dev win

## Result

Preregistration outcome:

- Rejected

Observed outcome on the frozen `15`-item TOMATO motion dev slice:

- default mean:
  - dense `0.467`
  - cached `0.267`
  - agreement `0.733`
  - active reuse `0.798`
- `STATIC`-only:
  - dense `0.467`
  - cached `0.333`
  - agreement `0.800`
  - active reuse `0.635`
- `mean + max_age = 4`:
  - dense `0.467`
  - cached `0.400`
  - agreement `0.867`
  - active reuse `0.698`
- `top_k_mean (12, 36)`:
  - dense `0.467`
  - cached `0.333`
  - agreement `0.733`
  - active reuse `0.707`
- `max_abs (24, 96)`:
  - dense `0.467`
  - cached `0.267`
  - agreement `0.733`
  - active reuse `0.802`
- `max_abs (12, 48)`:
  - dense `0.467`
  - cached `0.333`
  - agreement `0.733`
  - active reuse `0.703`

Wilson `95%` intervals on the aggregate `15`-item agreement summaries:

- default mean `0.733`, CI `[0.480, 0.891]`
- `STATIC`-only `0.800`, CI `[0.548, 0.930]`
- `mean + max_age = 4` `0.867`, CI `[0.621, 0.963]`
- `top_k_mean (12, 36)` `0.733`, CI `[0.480, 0.891]`
- `max_abs (24, 96)` `0.733`, CI `[0.480, 0.891]`
- `max_abs (12, 48)` `0.733`, CI `[0.480, 0.891]`

By-group comparison:

- default mean:
  - `direction`: cached `0.2`, agreement `0.6`, reuse `0.8579`
  - `rotation`: cached `0.4`, agreement `0.8`, reuse `0.7571`
  - `shape_trend`: cached `0.2`, agreement `0.8`, reuse `0.7789`
- `top_k_mean (12, 36)`:
  - `direction`: cached `0.2`, agreement `0.6`, reuse `0.7481`
  - `rotation`: cached `0.4`, agreement `0.6`, reuse `0.6907`
  - `shape_trend`: cached `0.4`, agreement `1.0`, reuse `0.6829`
- `max_abs (24, 96)`:
  - `direction`: cached `0.2`, agreement `0.6`, reuse `0.8441`
  - `rotation`: cached `0.4`, agreement `0.8`, reuse `0.7926`
  - `shape_trend`: cached `0.2`, agreement `0.8`, reuse `0.7703`
- `max_abs (12, 48)`:
  - `direction`: cached `0.2`, agreement `0.6`, reuse `0.7424`
  - `rotation`: cached `0.4`, agreement `0.6`, reuse `0.6913`
  - `shape_trend`: cached `0.4`, agreement `1.0`, reuse `0.6746`
- `mean + max_age = 4`:
  - `direction`: cached `0.4`, agreement `0.8`, reuse `0.7469`
  - `rotation`: cached `0.4`, agreement `0.8`, reuse `0.6600`
  - `shape_trend`: cached `0.4`, agreement `1.0`, reuse `0.6861`

Exploratory effective-dense-frame approximation for `8` sampled frames:

- formula: `1 + 7 * (1 - active_reuse)`
- default mean: `2.414`
- `top_k_mean (12, 36)`: `3.049`
- `max_abs (24, 96)`: `2.384`
- `max_abs (12, 48)`: `3.081`
- `mean + max_age = 4`: `3.116`

This approximation is not a Track B timing claim. It is a budget-oriented
Track A heuristic used only to compare policies at roughly similar fresh-vision
budgets.

## Interpretation

The result is more decisive than the earlier CPF miss.

First, same-budget statistic swaps are a null result here.

- `max_abs (24, 96)` landed at effectively the same active reuse as the
  default mean planner
- it reproduced the same aggregate outcome exactly:
  dense `0.467`, cached `0.267`, agreement `0.733`
- that is a strong control against the idea that the mean planner is failing
  purely because the scalar summary is too smooth

Second, lower-budget concentration-sensitive statistics still do not beat the
bounded-age mean planner.

- both `top_k_mean (12, 36)` and `max_abs (12, 48)` spent about the same
  fresh-vision budget as `mean + max_age = 4`
- both improved cached accuracy over the default mean planner
- neither improved agreement over the default mean planner at all
- both stayed materially worse than the bounded-age mean policy

Third, the hard `direction` bucket remains unrepaired under all tested
statistic-only policies.

- default mean: cached `0.2`, agreement `0.6`
- `top_k_mean (12, 36)`: cached `0.2`, agreement `0.6`
- `max_abs (24, 96)`: cached `0.2`, agreement `0.6`
- `max_abs (12, 48)`: cached `0.2`, agreement `0.6`
- `mean + max_age = 4`: cached `0.4`, agreement `0.8`

That is the cleanest surviving signal in the experiment.

- simple concentration-sensitive statistics do help `shape_trend`
- they do not repair `direction`
- bounded staleness still looks like the stronger lever on this motion-heavy
  slice

So the current evidence no longer supports the strong version of the
block-mean-dilution hypothesis.

The narrower version that survives is:

- mean-diff dilution is part of the problem on some items
- but bounded age matters more than statistic choice on the current TOMATO
  motion slice
- the next missing variable is not another nearby statistic first; it is
  answer stability under matched fresh-vision budgets

## Consequences

- keep `max_age` in the search space as the strongest current dev-only lever
- treat `top_k_mean (12, 36)` and `max_abs (12, 48)` as negative-but-informative
  results, not as candidate policy winners
- treat `max_abs (24, 96)` as a same-budget null control against the default
  mean planner
- prioritize the next method loop toward:
  - matched dense frame-budget baselines
  - answer-margin or option-logprob logging on disagreement items
  - only then broader MVBench motion sweeps or more planner statistics

## Links

- [2026-04-14-phase-1_6-motion-policy-sweep.md](2026-04-14-phase-1_6-motion-policy-sweep.md)
- [2026-04-14-phase-1_49-tomato-direction-refresh-sweep.md](2026-04-14-phase-1_49-tomato-direction-refresh-sweep.md)
- [docs/methodology/planner-sweep.md](../../../docs/methodology/planner-sweep.md)
- [docs/methodology/pareto-reporting.md](../../../docs/methodology/pareto-reporting.md)
