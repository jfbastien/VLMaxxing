# Phase 1.12: Pareto-Winner Holdout Evaluation

## Preregistration

Objective:

- one-shot evaluate dev-selected Pareto-dominating policies on the disjoint
  motion holdout slices for both TOMATO and MVBench, so the dev-side
  Pareto findings are validated as generalizing or rejected as dev-only

Claim register targets:

- `WP-2.5`
- `WP-2.6`
- `WP-3.1`
- `WP-3.3`

Reproduction mode:

- generalized benchmark, single-shot holdout (no further tuning)

Track:

- A (quality at matched fresh-token-equivalent budget on holdout)

Hypotheses:

- H1 (dev-to-holdout transfer): the cached policies that Pareto-dominate
  the dense frame-budget curve on dev also Pareto-dominate the dense
  frame-budget curve on holdout
- H2 (per-content): TOMATO motion holdout transfer differs from MVBench
  motion holdout transfer because their dense baselines have qualitatively
  different shapes (TOMATO holdout drops at higher frames; MVBench holdout
  is monotonic)

Acceptance band (per slice):

- at least one dev-selected policy survives Pareto-domination check on
  holdout (i.e. the holdout dense frame-budget curve does NOT strictly
  dominate the cached policy's holdout-evaluated point)

Rejection band (per slice):

- every dev-selected policy is strictly dominated by some holdout dense-N
  point on the same slice

Inconclusive:

- harness instability mid-evaluation
- dev-selected winners list is empty (no Pareto candidates from phases 1.10
  or 1.11)

Selection protocol:

- read `phase1_10_tomato_motion_dev_pareto.json` and select up to the top
  `5` candidates by cached_accuracy at lowest effective_fresh_frames
- read `phase1_11_mvbench_motion_dev_pareto.json` and apply the same
  selection
- record the selected policy labels in this note BEFORE the holdout runs

Selection-policy justification (reconciling with `docs/methodology/pareto-reporting.md`
which reads as single-winner promotion):

- Choosing top-5 rather than top-1 widens the holdout evidence but also
  inflates the multiple-comparison risk. With 5 independent holdout
  evaluations, the chance that at least one point survives by noise alone
  at N=15 (Wilson 95% CI width ~0.4) is non-negligible.
- We accept that risk explicitly because on TOMATO motion dev the top-5
  are all tied at cached_acc=0.400 — there is no principled way to pick
  "the" winner from {max_abs(8,32) static+shifted age=4, mean(2,6)
  static+shifted age=2, ...} without tuning on holdout, which is forbidden.
- Phase 1.12 will report per-policy holdout results separately and never
  aggregate them. A single policy surviving holdout at matched budget
  would be the citable finding; five surviving would be stronger but
  should be reported with the explicit "selected from top-5 dev ties"
  caveat.
- Methodology doc will be updated to allow top-K holdout selection with
  this explicit-tie rationale, post-commit.

Pareto evaluation on holdout:

- for each selected policy, run benchmark with the policy's exact
  configuration on the corresponding holdout manifest
- run `pareto_analysis.py analyze` against the holdout dense
  frame-budget summary (already complete in phase 1.9)

Notes:

- this phase is the discipline gate: dev cannot be tuned against holdout,
  and holdout cannot be retried after seeing the result
- if both TOMATO and MVBench holdout reject every dev winner, the project
  pivots to composition with FastV (orthogonal token pruning) per the
  round-7 execution plan strategic pivot points

## Execution

Launched 2026-04-15 after phase 1.11 completion. Selection protocol:
`select_holdout_winners.py` was run on the 30-policy phase 1.11 pareto
output for MVBench and on the 30-policy phase 1.10 pareto output for
TOMATO; top-5 by `(cached_accuracy, effective_fresh_frames)` was
extracted per slice and dedupe collapsed non-binding-age equivalents.
Launch lists are in `phase1_12_mvbench_holdout_policies.json` and
`phase1_12_tomato_holdout_policies.json`.

Protocol deviation (codex audit 2026-04-16): the top-5 MVBench list
included three points tied at 0.733 AND two points tied at 0.667 —
i.e. two different accuracy tiers — so the "K>1 only when tied on
primary metric" rule (`docs/methodology/pareto-reporting.md`) was
stretched. The holdout outcome did not inflate a positive claim
(all five failed), so this did not affect results. Future tranches
must separate "primary (tied at top metric)" from "diagnostic extras"
in the launch spec.

## Result

**MVBench motion holdout: REJECTION.** All 5 dev-selected policies
strictly dominated by dense-N on the disjoint holdout slice. Raw
numbers in `phase1_12_mvbench_motion_holdout_pareto.json`
(pareto_candidate_count = 0). Each cached point's dominator:

| policy | cached | effective_fresh_frames | dominated_by |
|---|---|---|---|
| max_abs(16,64) static+shifted noage | 0.533 | 3.27 | dense-2 (0.533 @ 2) |
| max_abs(16,64) static+shifted age=4 | 0.600 | 3.81 | dense-3 (0.600 @ 3) |
| max_abs(8,32) static+shifted noage | 0.600 | 4.21 | dense-3 (0.600 @ 3) |
| top_k_mean(k=64, 4, 12) noage | 0.600 | 4.55 | dense-3 (0.600 @ 3) |
| cpf(px8, 0.02, 0.08) noage | 0.600 | 4.67 | dense-3 (0.600 @ 3) |

**TOMATO motion holdout: in-flight (2/5 complete as of 2026-04-16).**
Committed points so far:

| policy | cached | effective_fresh_frames | notes |
|---|---|---|---|
| max_abs(8,32) static+shifted age=4 | 0.267 | 3.39 | matches dense-6 (0.267) at lower budget |
| mean(2,6) static+shifted age=2 | 0.267 | 3.89 | matches dense-6 at lower budget |

**Important caveat**: the committed TOMATO motion holdout dense curve
from phase 1.8 only has frames {1, 4, 6}. Dense-2, dense-3, and dense-8
were not built there. A cached point at fresh ≈ 3.4 may be strictly
dominated by (as-yet-unmeasured) dense-3 if dense-3 holdout is stronger
than 0.267. Phase 1.24 preregisters the backfill; no TOMATO "pass"
claim can be made before that backfill lands.

## Interpretation

- MVBench dev's item-identity-to-dense-4 property at lower budget did
  NOT generalize to holdout. The discipline gate held: a strong dev
  signal that turned out to be an N=15 slice coincidence was cleanly
  rejected without any dev-to-holdout tuning.
- TOMATO holdout interpretation is deferred until phase 1.24 dense
  backfill completes.
- Broader framing: even if TOMATO holdout survives a proper
  matched-budget test, the right paper claim would be content-conditioned
  ("cached temporal reuse matches dense frame-budget on TOMATO motion at
  a specific operating point; fails on MVBench motion holdout"),
  not a general SOTA claim.

## Links

- [phase 1.10 TOMATO motion dev grid](2026-04-14-phase-1_10-planner-grid-tomato-motion-dev.md)
- [phase 1.11 MVBench motion dev grid](2026-04-14-phase-1_11-planner-grid-mvbench-motion-dev.md)
- [phase 1.9 TOMATO motion frame-budget](2026-04-14-phase-1_8-motion-frame-budget-baselines.md)
- [phase 1.9 MVBench motion frame-budget](2026-04-14-phase-1_9-mvbench-motion-frame-budget-baselines.md)
- [execution plan round 7](../../../docs/execution-plan-round-7.md)
