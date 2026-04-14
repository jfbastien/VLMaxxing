# Planner Sweep Methodology

This document defines the current search space for training-free temporal
routing on the benchmark-native Track A runner.

## Goal

Search routing policies without silently changing the evaluation slice or
mixing semantic validation with Track B performance claims.

## Current Policy Axes

The benchmark runner exposes three first-class policy knobs:

- planner statistic:
  - `mean`
  - `max_abs`
  - `changed_pixel_fraction`
  - `top_k_mean`
- reuse classes:
  - `static`
  - `static,shifted`
- bounded token age:
  - `max_age = None`
  - positive integer caps such as `2`, `4`, or `8`

Optional fourth axis:

- frame refresh interval:
  - `0` means no forced refresh
  - positive `k` forces a dense refresh every `k` frames

## Reporting Contract

Every sweep note should state:

1. the exact manifest used
2. whether the manifest is `dev` or `holdout`
3. the policy grid searched
4. the default baseline used for comparison
5. the chosen selection rule for advancing a policy to holdout

Sweep artifacts should record, at minimum:

- dense accuracy
- cached accuracy
- dense-vs-cached agreement
- active reuse ratio
- raw reuse ratio
- planner config
- refresh interval
- manifest path

## Search Discipline

- search on `*_dev_v1.toml` only
- promote exactly one policy to the corresponding holdout
- if the holdout misses materially, record the miss and do not overwrite it
- do not cite dev-sweep best numbers as final evidence
- do not call a single threshold point per statistic a `sweep`; that is only a
  probe
- use dense feature replay to accelerate repeated Track A policy runs, but do
  not treat replay as systems evidence
- when comparing statistics, try to calibrate threshold grids into overlapping
  active-reuse bands before interpreting quality differences
- keep dense frame-budget baselines alongside planner sweeps so policy wins are
  not mistaken for wins over equally expensive dense alternatives

## Current Working Hypothesis

The default `mean` planner under-reports small-area, temporally concentrated
changes inside a `28 x 28` merged-token block. The first search is therefore a
comparison among `mean`, `max_abs`, `changed_pixel_fraction`, and
`top_k_mean`, with `reuse_classes` and `max_age` treated as co-equal policy
variables rather than as cleanup details.
