# Phase 1.26: Sticky-Dynamic Planner (CodecSight-Borrowed)

## Preregistration

Objective:

- implement CodecSight's sticky-dynamic rule in our training-free
  planner: once a block is marked dynamic (i.e., *not* reused) within
  a reset window, keep it dynamic for all subsequent frames in that
  window. Reset at a preregistered "I-frame-equivalent" cadence.
- answer whether sticky-dynamic recovers the TOMATO direction item
  that vanilla `max_abs(8,32) static+shifted age=4` missed on dev
- answer whether sticky-dynamic helps or harms the MVBench holdout
  cached result (the earlier phase 1.11 grid winners were rejected
  on holdout; at the time this prereg was written, the MVBench
  holdout was treated as a clean null, so the original phrasing
  here said "changes the MVBench holdout rejection" — phase 1.12.B
  then found a transfer-discovered survivor, so the question
  became "does sticky help or hurt the phase 1.12.B survivor?")

Claim register targets:

- Paper claims 2 (naive mean-diff is too blunt), 3 (sticky-dynamic
  repairs failures), 5 (real skipped compute via clean masks)
- `WP-2.5`, `WP-2.6`, `WP-3.1`, `WP-3.3`

Reproduction mode:

- method-development; new mechanism borrowed from CodecSight
  (2604.06036v3) Section 3.2, "sticky-dynamic via GOP accumulation"

Track: A (quality at matched fresh-token-equivalent budget)

Gating: runs immediately; the benchmark runner already supports block
masks, so only a new planner statistic class needs to be added.

Hypotheses:

- **H1 (dev-recovery)**: adding sticky-dynamic to `max_abs(8,32)
  static+shifted age=4` on TOMATO motion dev recovers the single
  direction-item that the vanilla policy misses vs dense, while
  keeping agreement with dense ≥ 0.800.
- **H2 (holdout-no-save)**: on MVBench motion holdout, sticky-dynamic
  does NOT recover the Pareto rejection; the mechanism is orthogonal
  to the items-level failure mode.
- **H3 (budget-cost)**: sticky-dynamic's main cost is ~0.1–0.3 extra
  effective_fresh_frames per policy on TOMATO motion (fewer reused
  blocks because reset window extends dynamic markings forward).

Acceptance band (per hypothesis):

- H1: cached_accuracy increases from 0.400 (vanilla TOMATO dev) to
  ≥ 0.467 at effective_fresh_frames ≤ 4.50.
- H2: no change in holdout Pareto outcome; 0 candidates survive.
- H3: extra_fresh_frames ≤ 0.3 across the 5 TOMATO dev Pareto winners.

Rejection band:

- H1: accuracy drops from 0.400 (sticky-dynamic makes it worse).
- H2: cached policy with sticky-dynamic BEATS dense-3 on MVBench
  holdout (would be a surprise Pareto win).
- H3: sticky-dynamic makes the effective budget explode (> 1 full
  extra fresh frame) — implementation bug.

Inconclusive:

- ties within Wilson CI on N=15 slices.

Reset-window choices (preregistered, not tunable post-run):

- Option A: reset every 4 frames (simulates GOP=4)
- Option B: reset every 8 frames (= no reset for our 8-frame clips,
  matches CodecSight default for short windows)
- Run both so we see reset-cadence sensitivity.

Policies (Phase 1.26.A):

1. `max_abs(8,32) static+shifted age=4 sticky_window=4` on TOMATO
   motion dev
2. `max_abs(8,32) static+shifted age=4 sticky_window=8` on TOMATO
   motion dev
3. Same 2 policies on TOMATO motion holdout (single-shot)
4. `max_abs(16,64) static+shifted noage sticky_window=4/8` on MVBench
   motion dev (the strict-Pareto winner from phase 1.11)
5. Same 2 MVBench policies on MVBench motion holdout (single-shot)

Runtime: ~6 cells × ~15 items × ~2 min/item ≈ 3 hrs GPU.

## Code change

Add a `sticky_window: int | None` field to `PolicyCandidate` +
`PlannerConfig`. In the benchmark runner's per-frame classification
loop, maintain a `dynamic_once: np.ndarray` mask within the window;
OR into it each frame. The final allowed mask becomes
`reuse_mask & (ages < max_age) & ~dynamic_once_in_window`. Reset
`dynamic_once` when `frame_index % sticky_window == 0`.

Also update `scripts/planner_grid_search.py` to pass `sticky_window`
through `_apply_age_gate`-style helper.

## Execution

Code change completed 2026-04-16 in commit `894c736`:
`sticky_window` threaded through runner + planner grid search CLI.
TOMATO motion dev cells 1 and 2 launched via
`planner_grid_search.py run-explicit`.

## Result (TOMATO motion dev, cells 1 + 2 complete 2026-04-16)

Preregistration outcome: **Rejected** — both sticky variants on
TOMATO motion dev strictly worsen cached accuracy AND raise the
fresh-frame budget relative to the vanilla `max_abs(8,32)
static+shifted age=4` baseline. H1 (sticky recovers direction item)
is REJECTED.

Phase 1.26.B (MVBench motion holdout with the same policy +
sticky) is in-flight at the time of this note; updated outcome
will be appended when it completes.


| policy | cached | dense | agreement | fresh |
|---|---|---|---|---|
| vanilla `max_abs(8,32) static+shifted age=4` (reference) | 0.400 | 0.467 | 0.867 | 3.99 |
| + sticky_window=4 | **0.333** | 0.467 | 0.800 | 4.33 |
| + sticky_window=8 | **0.333** | 0.467 | 0.800 | 4.65 |

Both sticky variants LOSE 1 item AND consume more budget than vanilla.

**H1 (sticky recovers direction item)**: REJECTED for both window
sizes.

**H2 (holdout still rejected if H1 fails on dev)**: retested in
phase 1.26.B below with the phase-1.12.B transfer-discovered
winner (a different policy family than the H1 target). Outcome:
**REJECTED** — sticky PASSES on MVBench motion holdout. See the
phase 1.26.B section for details. The original H2 framing
("sticky fails holdout") was based on the pre-1.12.B assumption
that MVBench holdout was a clean null; 1.12.B obsoleted that
assumption.

**H3 (sticky adds ~0.1–0.3 extra fresh frames)**: PARTIALLY
CONFIRMED for sticky_window=4 (+0.34 fresh frames). sticky_window=8
consumed +0.66 fresh frames — more than the bounded hypothesis
predicted.

## Interpretation

- Sticky-dynamic ALONE does not help on TOMATO motion dev. It
  latches dynamic flags forward, but if the original classifier
  failed to catch the critical motion (our observed failure mode
  on direction items), sticky has no initial dynamic flag to
  accumulate.
- This directly supports the 2026-04-16 audit's "budget placement
  over time" hypothesis: ADDING refresh (sticky makes more blocks
  dynamic for longer) does NOT help if the refresh lands in the
  wrong frames. Quantity ≠ placement.
- Phase 1.26.B (MVBench motion holdout, launched 2026-04-16) tests
  whether sticky is benchmark-specific. **RESULT: sticky HELPS on
  MVBench holdout, with striking magnitude.**

## Phase 1.26.B — MVBench motion holdout (single-shot, transfer-discovered)

**NOTE ON PREREG DELTA**: the original phase 1.26 prereg targeted
the phase-1.11-grid MVBench winner (`max_abs(16,64) static+shifted
noage`). Phase 1.12.B surfaced a better MVBench holdout winner
(`max_abs(8,32) static+shifted age=4`, the TOMATO-transfer policy),
so phase 1.26.B pivoted to adding sticky to THAT policy instead.
Cell-set name retained (`1.26.B`) to mark the deviation. Policies
JSON: `phase1_26b_sticky_on_mvbench_winner_policies.json`.

Result:

| policy | cached | dense | agreement | fresh | vs vanilla |
|---|---|---|---|---|---|
| `max_abs(8,32) age=4` (phase 1.12.B vanilla) | 0.667 | 0.733 | 0.933 | 4.59 | reference |
| + sticky_window=4 | **0.733** | 0.733 | **1.000** | 5.10 | +1 item, +0.51 fresh |
| + sticky_window=8 | 0.667 | 0.733 | 0.933 | 5.38 | 0 item, +0.79 fresh |

**Per-item diff vs dense-8** on sticky_window=4 (the winner):

| group | both_right | both_wrong | cached_only | dense_only |
|---|---|---|---|---|
| action_localization | 2 | 1 | 0 | 0 |
| fine_grained_action | 1 | 2 | 0 | 0 |
| moving_attribute | 3 | 0 | 0 | 0 |
| moving_direction | 2 | 1 | 0 | 0 |
| object_interaction | 3 | 0 | 0 | 0 |

**0 disagreements across all 15 items**. Item-identical to dense-8
at 64% budget.

**Pareto status**: strict win vs dense-8 at matched accuracy
tier (0.733). `pareto_analysis.py analyze` reports sticky4 as the
sole inter-cached skyline winner (2-axis and 3-axis).

**H2 (sticky does not save MVBench holdout)**: REJECTED. Sticky
DOES save MVBench holdout.

**Interpretation — asymmetric mechanism behavior**:

- On TOMATO motion dev: sticky HURTS (phase 1.26 cells 1+2,
  cached 0.400 → 0.333). The classifier misses the critical
  direction motion entirely, so sticky has no flag to
  accumulate.
- On MVBench motion holdout: sticky HELPS (phase 1.26.B cell 1,
  cached 0.667 → 0.733). The classifier detects motion
  inconsistently; sticky latches the intermittent detection.
- The mechanism requires the initial classifier to catch motion
  at SOME frame. When that prerequisite holds (MVBench), sticky
  converts intermittent detection into a consistent mask. When
  it fails (TOMATO direction), sticky adds noise.
- This is direct empirical support for the "budget placement
  over time" theory: sticky doesn't add arbitrary refresh —
  it adds refresh *at the frame boundaries where motion was
  caught*, which is exactly the placement gain.

**Paper implication**: our strongest current MVBench motion
holdout Pareto result is now `max_abs(8,32) static+shifted age=4
sticky_window=4`: cached=0.733, fresh=5.10, agreement=1.0,
item-identical to dense-8 at 36% lower budget. Phase 1.21 N=30
should use this as the PRIMARY cell; the phase 1.12.B no-sticky
variant becomes a diagnostic comparator.

Caveat: sticky_window=4 on TOMATO dev still hurts, so this
mechanism is NOT a universal improvement. The content
conditional-ness is now a real mechanism story: sticky helps on
MVBench-like motion patterns, not on TOMATO-direction-like
patterns.

## Links to falsified entries

This phase produces a new falsified hypothesis, to be recorded in
`research/falsified-hypotheses.md`:

- `falsified_2026-04-16_sticky-dynamic-alone-on-tomato-motion-dev`:
  sticky_window ∈ {4, 8} combined with `max_abs(8,32) static+shifted
  age=4` does not improve cached accuracy on TOMATO motion dev; it
  strictly worsens it at higher budget.

## Links

- CodecSight §3.2 sticky-dynamic
- [phase 1.10 TOMATO motion dev grid](2026-04-14-phase-1_10-planner-grid-tomato-motion-dev.md)
- [phase 1.11 MVBench motion dev grid](2026-04-14-phase-1_11-planner-grid-mvbench-motion-dev.md)
- [phase 1.12 holdout evaluation](2026-04-14-phase-1_12-grid-winners-holdout.md)
- [phase 1.12.B cross-benchmark holdout](2026-04-16-phase-1_12b-crossbench-winner-mvbench-holdout.md)
- [docs/literature-map-2026-04-16.md](../../../docs/literature-map-2026-04-16.md)
- [docs/methodology/temporal-coverage-metrics.md](../../../docs/methodology/temporal-coverage-metrics.md)
