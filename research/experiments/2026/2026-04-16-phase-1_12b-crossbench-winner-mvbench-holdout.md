# Phase 1.12.B: Cross-Benchmark-Discovered Winner → MVBench Holdout (single-shot)

## Preregistration

Objective:

- Phase 1.16 cell B produced an unexpected MVBench motion dev result:
  `max_abs(8,32) static+shifted age=4` achieves cached_accuracy = 0.800
  (12/15), fresh_frames = 3.78 — higher accuracy than the phase 1.11
  MVBench-native winner `max_abs(8,32) static+shifted noage` (0.733 at
  fresh=3.22). This specific policy was NOT in the phase 1.11 grid
  (which sampled noage + age=8 but not age=4 for this threshold set).
- The policy was selected by performance on the TOMATO motion dev
  slice. However, the full phase 1.16 cell-B workflow DID inspect
  MVBench dev accuracy before launching the holdout cell — so the
  correct framing is **transfer-discovered follow-up winner**,
  NOT **benchmark-blind clean holdout**. Codex audit 2026-04-16
  flagged an earlier draft of this note for using the stronger
  phrasing; corrected here. The result still stands as a credible
  early method signal; it just needs honest framing about how the
  policy got to this holdout cell.

Claim register targets:

- `WP-2.6`, `WP-3.1`, `WP-3.3` — if this holdout passes, MVBench
  motion is no longer a clean rejection; the paper story becomes
  content-conditioned across both benchmarks.

Reproduction mode:

- generalized benchmark, single-shot holdout evaluation, no further
  tuning allowed.

Track: A.

Gating:

- runs immediately; GPU free after phase 1.16 cell B completion.
- this is a one-shot evaluation. If it fails, no rerun.

Hypotheses:

- **H1 (transfer holds)**: `max_abs(8,32) static+shifted age=4` on
  MVBench motion holdout achieves cached_accuracy ≥ 0.600, matching
  or beating dense-3/4 holdout accuracy (both 0.600), at effective
  fresh_frames ≤ 4.
- **H2 (transfer fails)**: cached accuracy < 0.600 on MVBench holdout;
  the dev-side 0.800 was N=15 slice noise (same failure pattern as
  phase 1.12 MVBench rejection).
- **H3 (high-confidence discovery)**: at cached ≥ 0.667 on holdout,
  this is a genuine cross-benchmark Pareto winner and the paper
  story changes materially.

Acceptance band:

- H1 passes: cached_accuracy ≥ 0.600, matching matched-budget dense
  holdout point; inter-cached skyline winner on MVBench holdout.

Rejection band:

- cached_accuracy < 0.467 (worse than 7/15) on holdout → strict
  rejection; MVBench holdout is a confirmed null regardless of
  dev winner source.

Inconclusive:

- cached between 0.467 and 0.600 → ambiguous; needs N=30 (phase
  1.21 is demoted but can be re-activated for this specific
  winner).

## Execution

Command:

```
uv run python scripts/planner_grid_search.py run-explicit \
  --manifest research/benchmark_manifests/mvbench_motion_holdout_v1.toml \
  --policies research/experiments/2026/artifacts/phase1_16_tomato_winner_on_mvbench_policies.json \
  --frame-count 8 \
  --output-dir research/experiments/2026/artifacts/phase1_12b_crossbench_winner_mvbench_holdout \
  --out research/experiments/2026/artifacts/phase1_12b_crossbench_winner_mvbench_holdout_summary.json \
  --allow-dirty
```

## Result

Preregistration outcome: **Accepted with caveat** — H3 threshold
passed (cached_accuracy ≥ 0.667 on MVBench holdout). Caveat:
policy selection was informed by MVBench dev via phase 1.16 cell
B before launching this holdout cell, so this is a
"transfer-discovered follow-up" result rather than a
"benchmark-blind clean holdout." N=15 Wilson CI is wide.

**Cross-benchmark winner survives MVBench motion holdout.**

`max_abs(8,32) static+shifted age=4` on MVBench motion holdout:

| Metric | Value |
|---|---|
| cached_accuracy | **0.667** (10/15) |
| same-run dense_accuracy | 0.733 (11/15) |
| agreement | **0.933** (14/15 same answer as dense-8) |
| mean_active_reuse | 0.487 |
| effective_fresh_frames | 4.59 |

Pareto analysis with extended `pareto_analysis.py` (2D + 3D skylines):

- **Pareto candidate vs dense frontier**: 1/1 (not dominated by any
  dense-N holdout cell)
- **2-axis inter-cached skyline**: 1 point (itself; only one cached
  policy evaluated)

Key matched-budget comparisons against the full MVBench motion
holdout dense curve (1/2/3/4/6/8):

| vs dense-N | cached = 0.667 @ 4.59 | dense = ? @ N | cached verdict |
|---|---|---|---|
| dense-4 | 0.667 @ 4.59 | 0.600 @ 4 | cached +1 acc at +0.59 budget — NOT strict Pareto |
| dense-6 | 0.667 @ 4.59 | 0.667 @ 6 | cached EQUAL acc at 77% budget — **STRICT Pareto win** |
| dense-8 | 0.667 @ 4.59 | 0.733 @ 8 | dense +1 acc at higher budget — not dominated |

Per-group diff vs dense-6 (matched accuracy):

| group | both_right | both_wrong | cached_only | dense_only |
|---|---|---|---|---|
| action_localization | 1 | 1 | 0 | **1** |
| fine_grained_action | 1 | 1 | 0 | **1** |
| moving_attribute | 3 | 0 | 0 | 0 |
| moving_direction | 2 | 1 | 0 | 0 |
| object_interaction | 1 | 0 | **2** | 0 |

Cached and dense-6 have identical overall accuracy (10/15 each) but
disagree on 4 items in content-class-dependent ways: dense-6 wins on
action_localization + fine_grained_action; cached wins on
object_interaction. The accuracy match is not item-identical (unlike
phase 1.11 dev, which was 0-disagreement to dense-4); it is an
across-content-class specialization pattern.

Wilson 95% CI on cached_accuracy (10/15) = [0.41, 0.85]. Overlaps
dense-4 (0.600 @ [0.36, 0.80]) and dense-6 (0.667 @ [0.41, 0.85]).
The Pareto win is real but the N=15 CIs are wide; phase 1.21 N=30
MVBench enlargement is now re-activated to harden this result.

## Interpretation

**H1 passes**: cached_accuracy = 0.667 ≥ 0.600 at fresh_frames = 4.59,
and the policy is the inter-cached skyline winner (trivially, since
it's the only one evaluated here).

**H3 passes**: cached_accuracy = 0.667 ≥ 0.667 threshold — this is a
genuine cross-benchmark Pareto winner. Paper story changes
materially:

- **MVBench motion is no longer a clean rejection.** The phase 1.12
  rejection was of the phase 1.11-grid-discovered dev winners; the
  cross-benchmark (TOMATO-discovered) winner DOES survive MVBench
  holdout.
- Agreement = 0.933 is notable: cached disagrees with dense-8 on only
  1 of 15 items, yet achieves its 0.667 accuracy. Cached behaves
  like dense-8 on most items.
- Methodology lesson: the phase 1.11 grid had a gap on `max_abs(8,32)
  static+shifted age=4` — it sampled age=None and age=8 but not
  age=4 for this threshold set. The calibrate+select per-bin=1 cap
  missed this combination. Future phase 1.11-style sweeps should
  explicitly include the TOMATO-discovered policy family.

Paper implication (updated 2026-04-16):

- We now have Pareto candidates on BOTH TOMATO motion holdout (5/5
  at low-accuracy regime) AND MVBench motion holdout (1/1 via
  cross-benchmark transfer at high-accuracy regime).
- The MVBench holdout result is the stronger of the two: matches
  dense-6 at 77% budget, 93.3% dense-agreement, content-class
  specialization pattern.
- Methodology caveat remains: N=15 on both slices. Phase 1.20 (TOMATO
  N=30) + revived phase 1.21 (MVBench N=30) are the next gates.

## Links

- [phase 1.12 holdout evaluation (phase 1 of the discipline gate)](2026-04-14-phase-1_12-grid-winners-holdout.md)
- [phase 1.16 cross-benchmark transfer](2026-04-15-phase-1_16-cross-benchmark-winner-transfer.md)
- [phase 1.11 MVBench motion dev grid](2026-04-14-phase-1_11-planner-grid-mvbench-motion-dev.md)
- [docs/research-strategy-post-codecsight.md](../../../docs/research-strategy-post-codecsight.md)
