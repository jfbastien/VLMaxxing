# Falsified Hypotheses Ledger

Date: 2026-04-16
Parent: [decision-log.md](decision-log.md), [PLAN.md](../PLAN.md)

This is the rejected-hypothesis companion to
[decision-log.md](decision-log.md). Decision-log rows are dated
status changes (adopted / weakened / killed / pending). This file
is the queryable ledger of hypotheses that the data **explicitly
rejected** — what was tested, what the rejection looks like, and
what the rejection rules out for future work.

The 2026-04-16 audit recommendation: "make negatives queryable by
agents" (borrowing from MLGym / MLE-bench process discipline). Each
entry should be self-contained enough that a future agent or reader
can understand what was tried and why it failed without reading
the full phase note.

## Schema

Each entry has:

- **id**: `falsified_YYYY-MM-DD_short-name`
- **hypothesis**: one-sentence statement of the tested hypothesis
- **rejected by**: phase id + metric + magnitude
- **rejection band**: what the prereg said would count as rejection
- **scope of rejection**: what future work this rules out vs
  what remains open
- **link**: primary phase note

## Entries

### falsified_2026-04-14_no-refresh-static-reuse-on-tomato

- **hypothesis**: default static-position reuse with no refresh and
  no max_age maintains TOMATO direction accuracy.
- **rejected by**: phase 1.49 TOMATO direction refresh sweep.
  Cached=0.2 at no-refresh vs dense=0.8 on 5-item subset.
- **rejection band**: holdout cached accuracy below dense-same-run.
- **scope of rejection**: rules out "naive no-refresh same-position
  reuse is sufficient for TOMATO motion." Does NOT rule out
  bounded-age or refresh-interval variants.
- **link**: [phase 1.49](experiments/2026/2026-04-14-phase-1_49-tomato-direction-refresh-sweep.md)

### falsified_2026-04-14_mean-planner-default-thresholds-on-motion

- **hypothesis**: default `mean` planner with static_threshold=3,
  shifted_threshold=8 is competitive on motion benchmarks.
- **rejected by**: phase 1.6 + phase 1.7 + phase 1.10 show that
  `mean` planner with default thresholds is dominated by `max_abs`
  at matched budget, on both TOMATO and MVBench motion dev.
- **rejection band**: cached accuracy lower than the best alternative
  statistic at matched effective_fresh_frames.
- **scope of rejection**: rules out `mean + defaults` as a SOTA
  target. Does NOT rule out `mean` with retuned thresholds.
- **link**: [phase 1.10](experiments/2026/2026-04-14-phase-1_10-planner-grid-tomato-motion-dev.md)

### falsified_2026-04-16_mvbench-phase1-11-grid-winners-on-holdout

- **hypothesis**: any of the 5 phase-1.11 MVBench motion dev Pareto
  winners (`max_abs(16,64)` noage/age4, `max_abs(8,32)` noage,
  `top_k_mean` noage, `cpf` noage) survives MVBench motion holdout
  at matched fresh-frame budget.
- **rejected by**: phase 1.12. All 5 cached policies strictly
  dominated by some dense-N baseline on holdout; pareto_candidate_count
  = 0.
- **rejection band**: per phase 1.12 preregistration — "every
  dev-selected policy is strictly dominated."
- **scope of rejection**: rules out these specific policies as
  MVBench holdout survivors. Does NOT rule out the broader
  statistic family; phase 1.12.B showed that a grid-hole policy
  (`max_abs(8,32) age=4`) does survive.
- **link**: [phase 1.12](experiments/2026/2026-04-14-phase-1_12-grid-winners-holdout.md)

### falsified_2026-04-16_iso-frame-coverage-on-mvbench-holdout

- **hypothesis** (phase 1.28 H1 on MVBench holdout): doubling frame
  count from 8 to 16 at the same policy improves cached_accuracy
  because the saved budget buys more temporal coverage.
- **rejected by**: phase 1.28 MVBench holdout cell. cached_accuracy
  at 16 frames = 0.667 (IDENTICAL to 8-frame result), fresh budget
  rises from 4.59 to 8.58. Pareto-dominated by dense-8 (0.733 at
  8 frames).
- **rejection band**: cached_accuracy at 16 frames is not higher
  than at 8 frames.
- **scope of rejection**: rules out "more frames always helps at
  matched policy" on MVBench motion holdout. Does NOT rule out
  "more frames helps with a more-aggressive policy at iso fresh
  budget." Phase 1.28 H1 at iso-budget (tighter thresholds at 16
  frames targeting fresh~4) is still open.
- **link**: [phase 1.28 MVBench holdout](experiments/2026/2026-04-15-phase-1_28-iso-token-budget-coverage.md)

### falsified_2026-04-14_static-position-same-position-reuse-matches-whitepaper

- **hypothesis**: naive same-position STATIC+SHIFTED reuse
  reproduces the whitepaper's 100% TOMATO and MVBench agreement
  claims on our local Qwen 7B MLX 4-bit stack.
- **rejected by**: phase 1.4 (TOMATO 30-item, 0.833 agreement) and
  phase 1.5 (MVBench 54-item, 0.870 agreement).
- **rejection band**: agreement ≥ 0.95 on the local slice.
- **scope of rejection**: rules out the imported "100% agreement"
  claim as a realistic local target. Does NOT rule out
  method-improvement claims at matched budget (which is now our
  path).
- **link**: [phase 1.5](experiments/2026/2026-04-13-phase-1_5-mvbench-benchmark-subset.md)

## Additions process

When a new phase registers a rejection:

1. Fill in the schema fields above.
2. Link to the phase note.
3. Link from the phase note back to this ledger if the phase
   produced a rejection (so readers can navigate both directions).
4. Don't delete entries when later evidence overturns them; add a
   new dated entry that notes the overturn and why.
