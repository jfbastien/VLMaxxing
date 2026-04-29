# Phase 1.16: Cross-Benchmark Winner Transfer

## Preregistration

Objective:

- test whether the MVBench-winning `max_abs(8,32) static+shifted noage`
  policy generalizes to TOMATO motion dev at the same operating point
- test whether the TOMATO-winning `max_abs(8,32) static+shifted age=4`
  policy generalizes to MVBench motion dev at the same operating point
- map the degree of benchmark-conditioned specialization

Claim register targets:

- `WP-2.5`, `WP-2.6`
- `WP-3.3` (cross-benchmark transferability of the best policy)

Reproduction mode:

- generalized benchmark single-shot evaluation per cell

Track:

- A

Gating:

- runs regardless of phase 1.12 outcome; even if both winners fail
  holdout, cross-benchmark transfer on dev is informative methodology
  evidence (does the statistic family help the other benchmark?)

Hypotheses:

- H1 (statistic portability): the `max_abs(8,32) static+shifted` family
  transfers across both benchmarks even with different `max_age` tuning
- H2 (content specialization): MVBench's item-identity result does not
  reproduce on TOMATO because TOMATO's motion content is harder
- H3 (age asymmetry): TOMATO winner with age=4 on MVBench reduces reuse
  below MVBench's noage point but preserves or improves accuracy

Acceptance band:

- both transfer evaluations complete cleanly
- at least one cross-benchmark evaluation matches within 0.067 of its
  native-benchmark cached_accuracy (≤1 item drop on N=15)

Rejection band:

- both transfers drop cached_accuracy by ≥2 items vs native

Inconclusive:

- calibrations not reusable across benchmarks (should NOT happen — the
  policy is pure threshold + reuse-class + max_age)

Policies and slices:

1. `max_abs(8.0, 32.0) static+shifted noage` on TOMATO motion dev
2. `max_abs(8.0, 32.0) static+shifted age=4` on MVBench motion dev

Reference points:

- MVBench winner on MVBench: cached_acc=0.733, fresh=3.22
- TOMATO winner on TOMATO: cached_acc=0.400, fresh=3.99

Runtime: 2 policies × ~16 min ≈ 0.5 hrs GPU (faster with replay cache
hits).

## Execution

Pending phase 1.11 completion (MVBench winner confirmed final).

Planned commands (one per cell):

```
uv run python scripts/run_benchmark_track_a.py \
  --manifest research/benchmark_manifests/tomato_motion_dev_v1.toml \
  --planner-config '{"statistic": "max_abs", "static_threshold": 8.0, "shifted_threshold": 32.0, "reuse_classes": ["static", "shifted"]}' \
  --frame-count 8 --cache-mode on --chunk-size 1 \
  --out research/experiments/2026/artifacts/phase1_16_mvbench_winner_on_tomato.jsonl \
  --allow-dirty
```

(Mirror for the TOMATO winner on MVBench.)

## Result

Preregistration outcome: **Accepted with caveat** — both cells ran
cleanly; results support the preregistered hypotheses on
asymmetric transfer. Caveat: cell B's 0.800 dev-accuracy finding
was informed by MVBench dev artifact inspection before the holdout
follow-up (phase 1.12.B) was launched; the correct framing is
"transfer-discovered follow-up," not "clean blinded cross-benchmark
holdout."

Both cells executed 2026-04-16 via `planner_grid_search.py run-explicit`.

**Cell A — MVBench winner on TOMATO motion dev** (`max_abs(8,32)
static+shifted noage`):

| metric | value |
|---|---|
| cached_accuracy | 0.333 (5/15) |
| same-run dense_accuracy | 0.467 (7/15) |
| agreement | 0.800 |
| reuse_active | 0.657 |
| effective_fresh_frames | 3.40 |

TOMATO-native winner at same budget: `max_abs(8,32) static+shifted
age=4` gave cached=0.400 @ fresh=3.99. Transfer to TOMATO LOSES 1
item (6.7pp accuracy) while saving ~0.6 fresh frames. Interpretation:
TOMATO favors age-bounded staleness; the MVBench winner lacks that
constraint.

**Cell B — TOMATO winner on MVBench motion dev** (`max_abs(8,32)
static+shifted age=4`):

| metric | value |
|---|---|
| cached_accuracy | 0.800 (12/15) |
| same-run dense_accuracy | 0.600 (9/15) |
| agreement | 0.733 |
| reuse_active | 0.603 |
| effective_fresh_frames | 3.78 |

Cached **beats same-run dense-8** on this slice (12/15 > 9/15) and
**beats the phase 1.11 MVBench-native winner** (0.733 @ fresh=3.22).
The combination `max_abs(8,32) static+shifted age=4` was NOT in the
phase 1.11 grid — calibrate-then-select with per-bin=1 picked the
noage and age=8 variants for this threshold set, leaving age=4 as a
grid hole. This is a scientifically important negative finding about
our search strategy.

## Interpretation

- **Transfer is asymmetric, not uniformly weak.** TOMATO→MVBench is
  strong (cell B); MVBench→TOMATO is a small loss (cell A).
- **Age=4 is the critical hyperparameter** that the phase 1.11
  MVBench grid missed. Going forward, policy search should be
  factorized (coarse-over-statistic-and-thresholds, then fine
  age-sweep in promising regions), not dense-grid-per-bin.
- **Paper implication**: the cross-benchmark-discovered winner was
  promoted to a single-shot MVBench holdout (phase 1.12.B), which
  also passed. That defines the strongest current method signal.
- **Audit caveat (codex, 2026-04-16)**: the phase 1.12.B holdout
  test was *informed by* MVBench dev evidence (the cell B result
  above), not a benchmark-blind predeclared winner. The right
  framing is "transfer-discovered follow-up winner," NOT "clean
  blinded holdout." This caveat is now propagated to
  `phase-1_12b-crossbench-winner-mvbench-holdout.md`.

## Links

- [phase 1.10 TOMATO motion dev](2026-04-14-phase-1_10-planner-grid-tomato-motion-dev.md)
- [phase 1.11 MVBench motion dev](2026-04-14-phase-1_11-planner-grid-mvbench-motion-dev.md)
- [phase 1.12 holdout evaluation](2026-04-14-phase-1_12-grid-winners-holdout.md)
- [experiment registry](../registry.md)
