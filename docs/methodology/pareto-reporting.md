# Pareto Reporting

This document fixes how quality-versus-reuse trade-offs should be reported once
planner and refresh sweeps move beyond pure diagnosis.

## Required Axes

Report trade-offs over:

- quality:
  - dense accuracy
  - cached accuracy
  - dense-vs-cached agreement
- reuse:
  - active reuse ratio
  - raw reuse ratio
- policy:
  - planner statistic
  - reuse classes
  - max age
  - refresh interval

## Current Rule

Until Track B lands, reuse is the primary x-axis. Do not relabel reuse as
speedup, compression, or FLOP reduction.

Track A plots and tables should therefore say:

- `agreement versus active reuse`
- `cached accuracy versus active reuse`

and not:

- `speedup`
- `compression ratio`

unless same-stack skipped-compute evidence exists.

## Holdout Rule

If a sweep is used to choose a policy:

1. search on the dev manifest
2. choose one policy
3. evaluate that policy once on the holdout manifest
4. keep both dev and holdout numbers in the note

## Forward Link

When Track B exists, this document can be extended to add:

- latency
- peak memory
- fresh-token-equivalent budget
- matched dense frame-budget baselines
