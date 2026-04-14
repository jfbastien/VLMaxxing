# Phase 1.6: Motion Policy Sweep

## Preregistration

Objective:

- test whether the current motion-heavy TOMATO failures are better explained by
  planner policy than by benchmark-path bugs
- compare three cheap policy moves on a frozen motion-focused dev slice:
  - drop `SHIFTED` reuse
  - bound token age with `max_age = 4`
  - replace block-mean diff with a first `changed_pixel_fraction` variant
- evaluate the strongest dev policy on a disjoint motion-focused holdout slice

Claim register targets:

- `WP-2.5`
- `WP-3.3`

Reproduction mode:

- generalized benchmark diagnosis with explicit dev versus holdout separation

Track:

- A

Hypotheses:

- on the motion-heavy TOMATO dev slice, at least one cheap policy change should
  improve cached agreement over the default `mean + static,shifted + no age`
  baseline
- `max_age = 4` should recover some of the earlier refresh-sweep benefit while
  retaining more reuse than `STATIC`-only
- a real policy win should survive on the disjoint holdout slice rather than
  disappearing once the slice changes

Acceptance band:

- a dev policy materially improves agreement or cached accuracy over the
  default baseline
- the promoted dev winner does not regress on the holdout slice

Rejection band:

- all tested policies are flat or worse than the default baseline on dev
- any apparent dev win disappears on the disjoint holdout slice

Notes:

- all runs used the benchmark-native Qwen `7B` MLX path with the new
  clean-tree provenance guard
- to keep the repo clean across multiple serial runs, the sweep wrote to `/tmp`
  during execution and the finished artifacts were moved back into the repo
  afterward

## Execution

Run date:

- 2026-04-14

Manifests:

- dev:
  [tomato_motion_dev_v1.toml](../benchmark_manifests/tomato_motion_dev_v1.toml)
- holdout:
  [tomato_motion_holdout_v1.toml](../benchmark_manifests/tomato_motion_holdout_v1.toml)

Combined artifact:

- [phase1_6_motion_policy_sweep.json](artifacts/phase1_6_motion_policy_sweep.json)

Run artifacts:

- dev default:
  [phase1_6_tomato_motion_default_mean_summary.json](artifacts/phase1_6_tomato_motion_default_mean_summary.json)
- dev `STATIC`-only:
  [phase1_6_tomato_motion_mean_static_only_summary.json](artifacts/phase1_6_tomato_motion_mean_static_only_summary.json)
- dev `max_age = 4`:
  [phase1_6_tomato_motion_mean_age4_summary.json](artifacts/phase1_6_tomato_motion_mean_age4_summary.json)
- dev `changed_pixel_fraction`:
  [phase1_6_tomato_motion_cpf_summary.json](artifacts/phase1_6_tomato_motion_cpf_summary.json)
- holdout default:
  [phase1_6_tomato_motion_holdout_default_mean_summary.json](artifacts/phase1_6_tomato_motion_holdout_default_mean_summary.json)
- holdout `max_age = 4`:
  [phase1_6_tomato_motion_holdout_mean_age4_summary.json](artifacts/phase1_6_tomato_motion_holdout_mean_age4_summary.json)

Policy settings tested:

- default mean:
  - statistic `mean`
  - thresholds `(3, 8)`
  - reuse classes `static,shifted`
  - `max_age = none`
- `STATIC`-only:
  - statistic `mean`
  - thresholds `(3, 8)`
  - reuse classes `static`
  - `max_age = none`
- bounded age:
  - statistic `mean`
  - thresholds `(3, 8)`
  - reuse classes `static,shifted`
  - `max_age = 4`
- first CPF attempt:
  - statistic `changed_pixel_fraction`
  - thresholds `(0.02, 0.08)`
  - `pixel_change_threshold = 8`
  - reuse classes `static,shifted`
  - `max_age = none`

## Result

Preregistration outcome:

- Mixed

Observed outcome:

Dev slice (`15` items: `direction`, `rotation`, `shape_trend`):

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
- `max_age = 4`:
  - dense `0.467`
  - cached `0.400`
  - agreement `0.867`
  - active reuse `0.698`
- `changed_pixel_fraction`:
  - dense `0.467`
  - cached `0.267`
  - agreement `0.667`
  - active reuse `0.681`

Dev by group:

- default mean:
  - `direction`: cached `0.2`, agreement `0.6`, reuse `0.8579`
  - `rotation`: cached `0.4`, agreement `0.8`, reuse `0.7571`
  - `shape_trend`: cached `0.2`, agreement `0.8`, reuse `0.7789`
- `max_age = 4`:
  - `direction`: cached `0.4`, agreement `0.8`, reuse `0.7469`
  - `rotation`: cached `0.4`, agreement `0.8`, reuse `0.6600`
  - `shape_trend`: cached `0.4`, agreement `1.0`, reuse `0.6861`

Holdout slice (`15` disjoint items from the same three groups):

- default mean:
  - dense `0.267`
  - cached `0.200`
  - agreement `0.867`
  - active reuse `0.832`
- `max_age = 4`:
  - dense `0.267`
  - cached `0.200`
  - agreement `0.800`
  - active reuse `0.726`

Holdout by group:

- default mean:
  - `direction`: cached `0.4`, agreement `0.8`, reuse `0.7157`
  - `rotation`: cached `0.2`, agreement `0.8`, reuse `0.8963`
  - `shape_trend`: cached `0.0`, agreement `1.0`, reuse `0.8850`
- `max_age = 4`:
  - `direction`: cached `0.4`, agreement `0.8`, reuse `0.6241`
  - `rotation`: cached `0.2`, agreement `0.6`, reuse `0.7759`
  - `shape_trend`: cached `0.0`, agreement `1.0`, reuse `0.7770`

Wilson `95%` intervals on the aggregate `15`-item summaries:

- dev default agreement `0.733`, CI `[0.480, 0.891]`
- dev `STATIC`-only agreement `0.800`, CI `[0.548, 0.930]`
- dev `max_age = 4` agreement `0.867`, CI `[0.621, 0.963]`
- dev CPF agreement `0.667`, CI `[0.417, 0.848]`
- holdout default agreement `0.867`, CI `[0.621, 0.963]`
- holdout `max_age = 4` agreement `0.800`, CI `[0.548, 0.930]`

## Interpretation

Two hypotheses survived and one failed.

First, the motion-heavy default policy is genuinely improvable on the current
dev slice.

- dropping `SHIFTED` reuse helps
- bounding token age helps more
- the best dev policy here was still the historical `mean` statistic, not the
  first CPF attempt

Second, the dev win does **not** carry cleanly to holdout.

- `max_age = 4` looked strong on dev
- on the disjoint holdout, cached accuracy did not improve at all
- agreement actually fell from `0.867` to `0.800` while reuse also dropped

This is the most important result in the tranche.

- the dev slice looked staleness-limited
- the holdout slice looks much more confidence-limited
- agreement alone is not enough: the holdout default already gets high
  agreement because both dense and cached are weak on several items

The by-group pattern supports that reading.

- on dev, `max_age = 4` helps `direction`, the known hard bucket
- on holdout, `direction` does not improve further and `rotation` gets worse
- the first CPF attempt did not recover the `direction` failures and even hurt
  `rotation` agreement

So the current evidence supports a narrower claim than "better planner found."

- bounded staleness is a real lever on some motion-heavy dev items
- but the first win is not robust enough yet for a holdout policy claim
- the next method step should add dense answer-margin or option-logprob
  reporting so we can separate staleness-limited from confidence-limited items

## Consequences

- keep `max_age` as a first-class policy variable
- do **not** promote `max_age = 4` to a default policy yet
- do **not** promote the first CPF thresholds; they were weaker than the mean
  baseline on this slice
- the next planner loop should add:
  - `top_k_mean`
  - `max_abs`
  - matched dense frame-budget baselines
  - dense answer-margin logging on disagreement items

## Links

- [docs/methodology/planner-sweep.md](../../../docs/methodology/planner-sweep.md)
- [docs/methodology/pareto-reporting.md](../../../docs/methodology/pareto-reporting.md)
- [2026-04-14-phase-1_49-tomato-direction-refresh-sweep.md](2026-04-14-phase-1_49-tomato-direction-refresh-sweep.md)
