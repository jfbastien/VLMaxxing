# Phase 1.37B — Planner 2.1A prereg (parent statistic + neighbor-halo concentration guard)

Date: 2026-04-17
State: running (dev tranche 9-cell shortlist × 2 benchmarks launched 2026-04-17, TOMATO then MVBench sequentially; holdout pending dev winner)
Parent: `paper/claim-matrix.md` claim #3 (concentration-aware routing)
Sibling: `research/experiments/2026/2026-04-16-phase-1_12b-crossbench-winner-mvbench-holdout.md`,
`research/experiments/2026/2026-04-16-planner-2_0-ablation.md`

> **Mechanism-rename note (2026-04-17).** This file was originally titled
> "Phase 1.37 — Planner 2.1 prereg (parent statistic + child concentration
> guard)". It described, and the harness implemented, a **neighbor-halo**
> veto — a scan over neighboring *parent* blocks — NOT the within-block
> 2×2 child-veto preregistered in
> `research/experiments/2026/2026-04-16-phase-1_37-child-veto-subtoken-guard.md`.
> Sam's feedback flagged this mismatch: "child-veto" was the name of a
> different mechanism (subtoken guard inside each merged-token block) and
> should not be reused for the halo variant. As a result:
>
> - **Phase 1.37** = within-block child-veto (subtoken guard). Preregistered
>   2026-04-16. Code path NOT YET IMPLEMENTED — lives in
>   `_mix_qwen_features` reshape, not in `apply_neighbor_halo_veto`.
> - **Phase 1.37B (this file)** = neighbor-halo veto. Preregistered and
>   implemented 2026-04-17. Code path:
>   `src/codec_through/temporal.py::apply_neighbor_halo_veto`
>   with `NeighborHaloVetoConfig(percentile, neighborhood)`.
>
> Both mechanisms are scientifically distinct and both are worth running;
> they answer different questions (within-block magnitude recovery vs.
> spatial-neighborhood context). The mechanism-name change was applied in
> commit `<pending-this-commit>` which renamed `ChildVetoConfig` →
> `NeighborHaloVetoConfig`, `apply_child_veto` → `apply_neighbor_halo_veto`,
> and the Track A CLI flags `--veto-percentile` / `--veto-neighborhood` →
> `--halo-veto-percentile` / `--halo-veto-neighborhood`. Old prereg wording
> referring to "child-veto" below has been corrected.

## Framing

Planner 2.0 settled two things:

- The best single routing statistic is **MAX_ABS** cross-benchmark
  (TOMATO + MVBench), but the pixel→feature oracle (phase 1.36)
  shows MAX_ABS is NOT the best point predictor. It wins routing
  because outlier-sensitivity is the right signal for top-k
  budget allocation on temporally-uniform content.
- **Bounded staleness (age=4) is essential.** The no-age variant
  collapsed on both benchmarks. Age-bounding is not a parameter —
  it is a load-bearing mechanism.

Planner 2.1A is NOT a replacement for Planner 2.0. It is a
**hybrid** that treats the Planner 2.0 winner as the parent
statistic and adds a **neighbor-halo** concentration guard on top.
The question is whether a block that individually *would* be marked
STATIC under MAX_ABS can be vetoed into NOVEL when a neighbor
parent-block's score is large enough that the region is likely in
a motion event.

This design is a direct response to the phase 1.36 + Planner 2.0
reconciliation: MAX_ABS is a good *ordering* signal but a poor
*magnitude* signal. A spatial neighbor-halo concentration guard is
one way to recover some of the spatial context signal without
changing the parent statistic. (The phase-1.37 within-block
child-veto addresses the same reconciliation from a different
angle — subdividing each block into 2×2 sub-children and checking
MEAN/CPF per child — and is separately worth running.)

## Hypothesis

H1: `max_abs(8,32) static+shifted age=4` **with** a neighbor-halo
veto (a STATIC block is forced NOVEL if any parent-block neighbor
within `neighborhood` ranks above the `halo_veto_percentile` of
MAX_ABS scores across the frame pair) will beat Planner 2.0 base
on TOMATO motion holdout N=30. Target: acc ≥ 0.400 at
effective_fresh_frames ≤ 4.0, a strict Pareto win vs dense-4
(0.133) and a tie-or-win vs dense-8 (0.333) at less than half its
budget.

H2: The same hybrid is neutral-to-positive on MVBench motion
holdout N=30. MVBench's higher pixel→feature correlation means
magnitude signal is more available, so a spatial neighbor-halo
guard has less leftover signal to recover. We predict ties with
Planner 2.0 base there, not a large improvement.

H3 (anti-claim): the hybrid does NOT work as a replacement for
bounded staleness. If we keep the halo-veto but remove age=4,
we predict the same collapse as Planner 2.0 no-age.

## Method

Harness extension: `src/codec_through/temporal.py` exposes a
`NeighborHaloVetoConfig` dataclass and `apply_neighbor_halo_veto`
pure function. Track A's `run_benchmark_track_a.py` gates it on
`--halo-veto-percentile` and `--halo-veto-neighborhood` (both or
neither).

```python
@dataclass(frozen=True, slots=True)
class NeighborHaloVetoConfig:
    percentile: float = 0.95   # e.g. 0.90
    neighborhood: int = 1      # 1 = 3x3 Moore window, 2 = 5x5
    # parent statistic is not re-selected here; the parent classifier runs
    # whatever PlannerConfig.statistic is set to (MAX_ABS per Planner 2.0).
```

Planner 2.1A runs the parent decision as in Planner 2.0, then
iterates a second pass: for every STATIC block, check the parent-
statistic values in its `neighborhood` parent-block neighbors; if
any neighbor's score exceeds the `percentile` of the frame-pair
score distribution, promote STATIC→NOVEL. SHIFTED blocks are left
alone (they already have a motion signal).

## Dev tranche grid (pre-selection only)

Axes:

- `percentile ∈ {0.75, 0.85, 0.90, 0.95}`
- `neighborhood ∈ {1, 2}`
- `max_age ∈ {2, 4, 8}` (sanity check: age=4 should still be best)
- `sticky_window ∈ {None, 4}` (orthogonal check against phase 1.26)
- `parent = max_abs` (fixed, per Planner 2.0 finding)
- `reuse_classes = static+shifted` (fixed)

Total: 4 × 2 × 3 × 2 = 48 dev cells per benchmark; feature-replay
keeps this cheap.

Selection rule: single winner on dev (tie-breakers: lower
effective_fresh_frames, then higher agreement), then single-shot
holdout. Top-K ≤ 3 allowed only if tied on primary metric; rationale
recorded in the note.

### Amendment 2026-04-17 — shortlisted dev grid rationale

The 48-cell grid is scientifically ideal but costs ≈ 55 s/item ×
N=30 × 48 cells × 2 benchmarks ≈ 44 h of contended MLX wall time
on the M3 Air, which would deadlock the Gemma (Arc B) and Track B
queues for two days. Amended dev grid for the first execution pass:

- `percentile ∈ {0.75, 0.85, 0.90, 0.95}` (kept; this is the **new**
  axis the phase is designed to test)
- `neighborhood ∈ {1, 2}` (kept; the other **new** axis)
- `max_age = 4` (FIXED; phase 1.20 no-age collapse established age=4
  as the load-bearing setting — the `max_age ∈ {2, 4, 8}` sanity
  sweep is a nice-to-have, not paper-blocking)
- `sticky_window = None` (FIXED for first pass; phase 1.26 already
  characterized sticky-window, and we test halo-veto orthogonally to
  sticky-window here. If a halo-veto cell wins dev, a follow-up
  `halo × sticky4` cross pass is preregistered below.)
- `parent = max_abs`, `reuse_classes = static+shifted` (fixed, per
  Planner 2.0)

**Shortlisted total: 8 halo-veto cells + 1 control (no halo) per
benchmark = 9 cells per benchmark.** At 55 s/item × N=30 × 9 ≈ 4 h
MLX wall time per benchmark. Two benchmarks sequentially ≈ 8 h.

Follow-up cross-pass (preregistered; runs only if the dev winner is
a halo-veto cell): re-run the dev winner's `(percentile,
neighborhood)` with `sticky_window = 4`. That tests the orthogonality
assumption: if halo-veto and sticky-window compose additively, a
sticky×halo cell should beat the best pure-halo cell; if they
saturate on the same failure mode, the cross cell should tie the
best pure-halo cell.

**Scientific cost of the shortlist**: we trade the `max_age ∈ {2,
8}` and the `sticky=4` axes. The `max_age` axis is already spoken
for by phase 1.20 and the `sticky_window` axis by phase 1.26; their
exclusion is a deliberate methodological economy, not a
simplification. The follow-up cross-pass recovers the sticky axis
information conditional on halo-veto winning dev.

Artifact directories for the shortlisted pass:

- `research/experiments/2026/artifacts/phase1_37B_tomato_motion_dev_v2_cached/{control,p0.75_n1,…,p0.95_n2}_summary.json`
- `research/experiments/2026/artifacts/phase1_37B_mvbench_motion_dev_v2_cached/{control,p0.75_n1,…,p0.95_n2}_summary.json`

## Accept / reject gates (preregistered)

- **TOMATO holdout N=30, accept:** cached_accuracy ≥ 0.400 at
  effective_fresh_frames ≤ 4.0 (would strictly Pareto-dominate
  Planner 2.0 base's 0.333 @ 3.55).
- **TOMATO holdout, reject:** cached_accuracy < 0.333 or
  effective_fresh_frames > 4.5. Either indicates the veto hurts.
- **MVBench holdout N=30, accept:** cached_accuracy ≥ 0.600 at
  effective_fresh_frames ≤ 4.5 (ties or narrowly beats Planner 2.0
  base 0.600 @ 4.06; within measurement band is acceptable).
- **MVBench holdout, reject:** cached_accuracy < 0.567 (clearly
  below Planner 2.0 base).

## Dev-winner promotion rule (FROZEN before results land 2026-04-17)

Written before the dev sweep completes to prevent post-hoc cell
selection. The analyzer script at `scripts/analyze_halo_dev_grid.py`
applies these rules mechanically.

**Primary metric (from prereg):** cached_accuracy (higher better).
**Tiebreakers in order:** effective_fresh_frames (lower better),
then agreement (higher better).

**Per-benchmark promotion decision:**

1. Rank the 9 dev cells (1 control + 8 halo-veto) by
   (cached_accuracy desc, effective_fresh_frames asc, agreement desc).
2. If the control cell (no-halo, == Planner 2.0 base) is rank 1 OR
   is within 0.034 (1 item/30) of rank 1 on cached_accuracy with
   the same fresh-frame budget, declare **NO-LIFT** and retire the
   halo-veto branch on that benchmark. No holdout.
3. Otherwise, the rank-1 halo-veto cell is the candidate winner.
   Run the single-shot holdout with that cell's `(percentile,
   neighborhood)` on the same benchmark's motion_holdout_v2 manifest.
4. Apply the §Accept/reject gates above to the holdout summary.

**Both benchmarks no-lift → full retirement.** Phase 1.37B closes as
"halo-veto does not add measurable lift over Planner 2.0 base" and
the paper cites this as a preregistered null. Refocus on Arc B
(Gemma novelty-pruning, phase 1.51) — the user's charter is big
numbers, not incremental routing refinements.

**One benchmark no-lift, one benchmark lift** → the lift benchmark
goes to holdout; the no-lift benchmark is reported as such. Claim 3
becomes "partial on one benchmark."

**Cross-pass trigger (halo × sticky4):** only if the halo-veto
winner on MVBench passes the holdout gate. Rationale: MVBench's
sticky4 lift is the only confirmed sticky-window benefit in the
repo (phase 1.21 sticky4 +0.033 over base at slightly higher fresh
budget), so the sticky × halo test is meaningful only on MVBench.
TOMATO sticky-window was demonstrated to hurt (phase 1.26), so
sticky × halo on TOMATO is not scientifically interesting unless
the halo mechanism fundamentally changes the sticky failure mode
— if that emerges in analysis, add a second cross-pass post-hoc
and label it exploratory, NOT preregistered.

**If no halo-veto cell ever reaches holdout** — the phase retires
in the "preregistered null" column of the paper's results table.
This is a publishable outcome: a preregistered mechanism that did
not deliver is meaningful scientific evidence.

## Placement instrumentation

Because phase 1.37B directly tests the "placement > quantity"
theory, the run MUST log the per-pair fresh histogram and longest-
stale-run (see `docs/methodology/temporal-coverage-metrics.md`),
even if the metric analysis waits for phase 1.31.

## Status

- 2026-04-17: code landed in commits `2ebf90d` (pure-numpy
  `_neighborhood_max` + (originally-named) `apply_child_veto` +
  `ChildVetoConfig` in `src/codec_through/temporal.py`; 10 unit tests)
  and `db10e12` (Track A harness + old `--veto-percentile` /
  `--veto-neighborhood` CLI flags). Mechanism-rename applied 2026-04-17
  in commit `0ea69fe`: identifiers are now `NeighborHaloVetoConfig`,
  `apply_neighbor_halo_veto`, and CLI flags are
  `--halo-veto-percentile` / `--halo-veto-neighborhood`.
- 2026-04-17: smoke test on 1 item (TOMATO direction 0231-04, warm
  feature cache) completed in 55 s wall clock; halo-veto present in
  summary.planner payload; `reuse_ratio_mean_active` dropped from
  0.650 raw to 0.476 after halo-veto, confirming the veto promotes
  STATIC→NOVEL as designed.
- 2026-04-17: **TOMATO dev shortlisted 9-cell sweep launched in
  background** via `/tmp/claude/run_halo_dev_tomato.sh`; expected
  wall time ≈ 4 h. MVBench dev 9-cell sweep queued sequentially.
- Paper-grade holdout run: preregistered gates above; awaits dev
  selection.

## Artifacts

Placeholder — will populate when the dev grid runs. Expected
outputs (NOTE: artifact-directory names below use `phase1_37B` to
match the new phase label; old pre-rename references to
`phase1_37_*` were superseded):

- `research/experiments/2026/artifacts/phase1_37B_tomato_motion_dev_v2_cached/*_summary.json`
  (48 cells)
- `research/experiments/2026/artifacts/phase1_37B_mvbench_motion_dev_v2_cached/*_summary.json`
  (48 cells)
- `research/experiments/2026/artifacts/phase1_37B_tomato_motion_holdout_v2_cached/*_summary.json`
  (single winner)
- `research/experiments/2026/artifacts/phase1_37B_mvbench_motion_holdout_v2_cached/*_summary.json`
  (single winner)

Code-only artifacts already committed:

- `src/codec_through/temporal.py` — `NeighborHaloVetoConfig`,
  `apply_neighbor_halo_veto`, `_neighborhood_max` (original code in
  commit 2ebf90d, renamed in the 2026-04-17 mechanism-rename commit)
- `tests/test_neighbor_halo_veto.py` — 10 unit tests (renamed from
  `tests/test_child_veto.py`)
- `scripts/run_benchmark_track_a.py` — CLI flags + subprocess
  passthrough (original in commit db10e12, flag-renamed in the
  2026-04-17 mechanism-rename commit)

## Why this is the next thing, not Planner 2.2

Planner 2.2 candidates (replacement-style: different parent
statistic, different reuse-class decomposition, or different
staleness bounds per class) are deferred because:

1. Planner 2.0 already settled the parent choice cross-benchmark.
2. Phase 1.36 shows point-prediction and routing are different
   objectives; a new parent statistic would need its own oracle
   pass to justify.
3. A hybrid with a cheap neighbor-halo guard is the natural next
   step and changes one axis at a time (methodology rule). The
   within-block child-veto (phase 1.37) is a separate axis and
   will run in parallel once that code path lands.
