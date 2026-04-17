# Phase 1.37 — Planner 2.1 prereg (parent statistic + child concentration guard)

Date: 2026-04-17
Parent: `paper/claim-matrix.md` claim #3 (concentration-aware routing)
Sibling: `research/experiments/2026/2026-04-16-phase-1_12b-crossbench-winner-mvbench-holdout.md`,
`research/experiments/2026/2026-04-16-planner-2_0-ablation.md`

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

Planner 2.1 is NOT a replacement for Planner 2.0. It is a
**hybrid** that treats the Planner 2.0 winner as the parent
statistic and adds a per-child-block concentration guard on top.
The question is whether a block that individually *would* be marked
STATIC under MAX_ABS can be vetoed into NOVEL when a neighbor
block's score is large enough that the region is likely in a
motion event.

This design is a direct response to the phase 1.36 + Planner 2.0
reconciliation: MAX_ABS is a good *ordering* signal but a poor
*magnitude* signal. A spatial concentration guard is one way to
recover some of the magnitude signal without changing the parent
statistic.

## Hypothesis

H1: `max_abs(8,32) static+shifted age=4` **with** a child-veto
(a block is forced NOVEL if any of its 4 spatial neighbors ranks
above the `veto_percentile` of MAX_ABS scores across the frame
pair) will beat Planner 2.0 base on TOMATO motion holdout N=30.
Target: acc ≥ 0.400 at effective_fresh_frames ≤ 4.0, a strict
Pareto win vs dense-4 (0.133) and a tie-or-win vs dense-8 (0.333)
at less than half its budget.

H2: The same hybrid is neutral-to-positive on MVBench motion
holdout N=30. MVBench's higher pixel→feature correlation means
magnitude signal is more available, so a spatial concentration
guard has less leftover signal to recover. We predict ties with
Planner 2.0 base there, not a large improvement.

H3 (anti-claim): the hybrid does NOT work as a replacement for
bounded staleness. If we keep the child-veto but remove age=4,
we predict the same collapse as Planner 2.0 no-age.

## Method

Harness extension: `src/codec_through/planner/__init__.py` gets a
new optional `child_veto_config` dataclass on the planner config:

```python
@dataclass
class ChildVetoConfig:
    percentile: float       # e.g. 0.90
    neighborhood: int       # 1 = von Neumann (4 neighbors); 2 = Moore+ (8)
    parent_statistic: str   # "max_abs" (we are not reconsidering parent choice here)
```

Planner 2.1 runs the parent decision as in Planner 2.0, then
iterates a second pass: for every STATIC block, check the parent-
statistic values in its `neighborhood` neighbors; if any neighbor's
score exceeds the `percentile` of the frame-pair score distribution,
demote STATIC→NOVEL. SHIFTED blocks are left alone (they already
have a motion signal).

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

## Placement instrumentation

Because phase 1.37 directly tests the "placement > quantity"
theory, the run MUST log the per-pair fresh histogram and longest-
stale-run (see `docs/methodology/temporal-coverage-metrics.md`),
even if the metric analysis waits for phase 1.31.

## Status

NOT STARTED. Code change required in
`src/codec_through/planner/__init__.py`; harness flag in
`scripts/run_benchmark_track_a.py`. Pre-req: CI green, Planner 2.0
writeup unambiguous about parent-statistic choice (both landed
2026-04-17).

## Why this is the next thing, not Planner 2.2

Planner 2.2 candidates (replacement-style: different parent
statistic, different reuse-class decomposition, or different
staleness bounds per class) are deferred because:

1. Planner 2.0 already settled the parent choice cross-benchmark.
2. Phase 1.36 shows point-prediction and routing are different
   objectives; a new parent statistic would need its own oracle
   pass to justify.
3. A hybrid with a cheap child-guard is the natural next step
   and changes one axis at a time (methodology rule).
