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

**TOMATO motion holdout: 5/5 cached policies COMPLETE**, phase 1.24
dense-2/3/8 backfill also complete. Full holdout dense curve (N=15,
frames {1,2,3,4,6,8}):

| dense-N | accuracy | Wilson 95% CI |
|---|---|---|
| 1 | 0.200 | [0.07, 0.45] |
| 2 | 0.200 | [0.07, 0.45] |
| 3 | 0.200 | [0.07, 0.45] |
| 4 | 0.133 | [0.04, 0.38] |
| 6 | 0.267 | [0.11, 0.52] |
| 8 | 0.267 | [0.11, 0.52] |

All 5 cached policies landed at cached_accuracy = 0.267 (4/15 correct,
Wilson 95% CI [0.11, 0.52]). `pareto_analysis.py analyze` reports all 5
as candidates vs dense (no dense-N strictly dominates any of them).

2-axis inter-cached skyline (cached_accuracy, effective_fresh_frames):

| policy | cached | fresh | agreement | observation |
|---|---|---|---|---|
| max_abs(8,32) static+shifted age=4 | 0.267 | 3.39 | 0.800 | sole 2-axis Pareto winner; lowest fresh-frame budget |

3-axis inter-cached skyline (add `agreement`):

| policy | cached | fresh | agreement |
|---|---|---|---|
| max_abs(8,32) static+shifted age=4 | 0.267 | 3.39 | 0.800 |
| mean(2,6) static+shifted age=2 | 0.267 | 3.89 | 0.867 |

Interpretation vs dense frontier:

- Cached at fresh ≈ 3.39 with acc = 0.267 strictly dominates dense-4
  (0.133 @ 4), dense-6 (0.267 @ 6), dense-8 (0.267 @ 8). Same accuracy
  as dense-6 and dense-8 at 43% and 58% lower fresh-frame budget
  respectively.
- Cached does NOT strictly dominate dense-1/2/3 — those have lower
  accuracy AND lower budget, so they occupy a different Pareto region.

**HEAVY caveats on the positive result**:

1. **Low absolute accuracy regime.** 0.267 means 4/15 correct. Wilson
   95% CI is [0.11, 0.52] — overlaps with dense-2/3 CI [0.07, 0.45].
   This is a "confidence-limited" Pareto win: cached ties dense-6 on a
   slice where all methods score low, so the comparison is less
   informative than a high-accuracy Pareto win would be.
2. **N=15 is too small to separate ties from method wins.** Phase
   1.20 N=30 TOMATO enlargement is now top priority: if cached still
   ties or beats dense-6 at N=30, the result hardens; if not, the N=15
   tie was likely sampling noise.
3. **Dirty-tree artifact per codex audit.** The 5 cached holdout
   summaries were produced with `--allow-dirty`. For paper-grade
   claims, rerun on a clean tree. Phase 1.25 will preregister the
   clean rerun after a pending refactor settles.
4. **Agreement ≠ reproduction.** `max_abs(8,32)` at agreement=0.800
   means cached disagrees with dense on 20% of items — different 20%
   from dense's misses. The accuracy tie masks real divergence.

This is a very different story from MVBench holdout. On MVBench,
cached policies were strictly dominated at every matched-budget cell.
On TOMATO, they match or beat dense at matched budget — but on a
confidence-limited 15-item slice where the signal-to-noise ratio
is poor.

## Interpretation

- MVBench dev's item-identity-to-dense-4 property at lower budget did
  NOT generalize to holdout. The discipline gate held: a strong dev
  signal that turned out to be an N=15 slice coincidence was cleanly
  rejected without any dev-to-holdout tuning.
- TOMATO holdout: 5 cached policies tied dense-6/8 accuracy (0.267) at
  lower fresh-frame budget. Honest Pareto win at low absolute accuracy
  and N=15 — needs phase 1.20 N=30 enlargement + clean-tree rerun before
  it can be promoted to a paper claim.
- Content-conditioned story so far: TOMATO motion matches cached
  methods at low-accuracy regime; MVBench motion rejects every cached
  policy at higher-accuracy matched-budget regime. The right paper
  framing is "training-free temporal feature reuse matches dense
  frame-budget quality on TOMATO motion at one operating point and on
  a confidence-limited slice; fails on MVBench motion holdout; the
  composition axis (temporal × token pruning, phase 1.23) is the more
  credible path to SOTA."

## Links

- [phase 1.10 TOMATO motion dev grid](2026-04-14-phase-1_10-planner-grid-tomato-motion-dev.md)
- [phase 1.11 MVBench motion dev grid](2026-04-14-phase-1_11-planner-grid-mvbench-motion-dev.md)
- [phase 1.9 TOMATO motion frame-budget](2026-04-14-phase-1_8-motion-frame-budget-baselines.md)
- [phase 1.9 MVBench motion frame-budget](2026-04-14-phase-1_9-mvbench-motion-frame-budget-baselines.md)
- [execution plan round 7](../../../docs/execution-plan-round-7.md)
