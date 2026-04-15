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
- dense baseline:
  - matched frame-budget baselines such as dense `1/2/4/8` frames when the
    comparison is about Track A quality at a bounded fresh-vision budget

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

Feature replay does not change this rule. Replay reduces repeated experiment
cost; it is not a Track B win.

## Holdout Rule

If a sweep is used to choose a policy:

1. search on the dev manifest
2. choose one policy, OR up to K tied policies (see below)
3. evaluate each chosen policy once on the holdout manifest
4. keep both dev and holdout numbers in the note
5. never combine holdout evaluations across policies; always report
   per-policy holdout separately so multiple-comparison risk is visible

Top-K allowance:

- preferred mode is K=1 (pick a single winner and gate on holdout)
- K>1 is allowed when the top-K dev points are tied on the primary metric
  (cached_accuracy) — there is no principled way to pick "the" winner
  without implicit tuning on holdout
- K should not exceed 5; report the rationale for the chosen K in the
  note; acknowledge that "at least one survived" under K>1 inflates the
  chance of a noise-driven pass and therefore requires tighter CI framing
  in any paper-facing claim

## Forward Link

When Track B exists, this document can be extended to add:

- latency
- peak memory
- fresh-token-equivalent budget
- matched dense frame-budget baselines
