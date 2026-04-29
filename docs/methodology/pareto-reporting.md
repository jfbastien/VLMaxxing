# Pareto Reporting

Last updated: 2026-04-17. Prior version preserved in git history;
this rewrite reflects the methodology upgrade landed in phases 1.8,
1.9, 1.10, 1.11, 1.12, 1.12.B, 1.19, 1.24, 1.50 (Track B dense
baseline), and the 2026-04-16 / 2026-04-17 audit tranches.

## What changed relative to the previous version

The previous rule said "until Track B lands, reuse is the primary
x-axis." That rule served as a guardrail against mislabeling reuse
as compute savings, but the project has since adopted a stronger
comparison: **matched fresh-token-equivalent dense frame-budget
baselines**. Those are the fair primary x-axis, not reuse.

Reuse remains a useful descriptive axis, but it is no longer the
primary Pareto axis.

## Required axes (updated)

### Primary axes (Pareto is computed on these)

- `cached_accuracy` (maximize)
- `effective_fresh_frames` (minimize) = `1 + (N-1) × (1 - mean_active_reuse)`
- `dense_accuracy` at matched `frame_count` (the dense curve we
  compare cached against)

### Secondary axes (report alongside; do not compute Pareto on these
alone)

- `agreement` with same-run dense — cheap distributional check
- `mean_active_reuse` — descriptive of mechanism, not compute cost
- per-frame fresh-token distribution — see
  [temporal-coverage-metrics.md](temporal-coverage-metrics.md)

### Policy metadata (record on every cell)

- planner statistic (mean / max_abs / changed_pixel_fraction / top_k_mean)
- thresholds (static, shifted, pixel_change, top_k)
- reuse_classes (static / static+shifted / ...)
- max_age
- sticky_window (since phase 1.26)
- refresh_interval (if used)

## Primary comparison rule

A cached point is **Pareto-dominated by dense** iff there exists a
dense-N baseline cell on the same slice with
`dense_accuracy >= cached_accuracy` AND `dense_frame_count <=
effective_fresh_frames` AND at least one of those is strict. This
is the analyzer's current rule (see
`scripts/pareto_analysis.py::_dominates`).

A cached point is **inter-cached Pareto skyline**-surviving iff no
other cached point dominates it on the chosen objective set. We
compute two skylines by default:

- 2-axis skyline `(cached_accuracy, effective_fresh_frames)`
- 3-axis skyline adding `agreement`

Both are emitted by `pareto_analysis.py::_inter_cached_skyline` and
reported in the JSON output.

## Reporting rules

When a paper-facing plot or table is produced:

1. The plot's x-axis MUST be `effective_fresh_frames`, not
   `mean_active_reuse`.
2. A dense-N curve at matching `frame_count`s MUST be on the same
   axes (the fair baseline).
3. Wilson 95% CI bars MUST be shown on every cell.
4. When reporting per-group results, the CI width depends on the
   group size; at N=15 the per-group CI bars are too wide to
   separate adjacent groups. Flag this as a caveat.
5. When citing a cross-benchmark-discovered result (e.g., phase
   1.12.B), the prose MUST say "transfer-discovered follow-up,"
   NOT "clean blinded holdout."
6. Do not relabel reuse as speedup, compression, or FLOP reduction
   unless same-stack Track B skipped-compute evidence exists. This
   guardrail from the previous version is preserved.

Feature replay does not change any of these rules. Replay reduces
repeated experiment cost; it is not a Track B win.

## Holdout rule (unchanged from prior version, clarified)

If a sweep is used to choose a policy:

1. Search on the dev manifest.
2. Choose one policy, OR up to K tied policies (see below).
3. Evaluate each chosen policy once on the holdout manifest.
4. Keep both dev and holdout numbers in the note.
5. Never combine holdout evaluations across policies; always report
   per-policy holdout separately so multiple-comparison risk is
   visible.

Top-K allowance:

- Preferred mode is K=1 (pick a single winner and gate on holdout).
- K>1 is allowed when the top-K dev points are tied on the primary
  metric (cached_accuracy) — there is no principled way to pick
  "the" winner without implicit tuning on holdout.
- K should not exceed 5; report the rationale for the chosen K in
  the note.
- Acknowledge that "at least one survived" under K>1 inflates the
  chance of a noise-driven pass and therefore requires tighter CI
  framing in any paper-facing claim.

### Integer dense-k baseline reporting (NEW, 2026-04-17)

Effective-fresh-frames is the fair Pareto x-axis, but reviewers
often parse the method against *integer* dense-k cells (dense-4,
dense-6, dense-8) because that is what ships. Every Pareto report
MUST therefore include BOTH representations side-by-side:

1. `effective_fresh_frames` (continuous, our policy's actual cost)
2. Nearest integer dense-k cells that bracket the policy

Example (from phase 1.20 TOMATO holdout): base policy at
`effective_fresh_frames=3.55` with `accuracy=0.333`. Report as:

> Cached: 0.333 @ 3.55 fresh frames (between dense-3 at 0.267 and
> dense-4 at 0.133). Pareto-ties dense-8 (0.333 at 8.0 fresh frames)
> at 44% of the integer budget.

This avoids the reviewer misreading a real-valued fresh-frame
number as a floor or ceiling. The integer brackets make the
effective-fresh-frame axis legible without losing the continuous
comparison.

### Cross-benchmark-discovered winners (NEW, 2026-04-16)

Phase 1.12.B introduced a new pattern: a dev-selected winner on
benchmark A gets applied to benchmark B's holdout as a single-shot
test. Rules:

- The winner's selection MUST have been dev-only on benchmark A;
  it must NOT have been informed by B's holdout.
- The single-shot holdout test on B is preregistered as a separate
  phase (e.g., 1.12.B) with explicit accept/reject bands.
- In prose, the result is framed as "transfer-discovered follow-up
  winner," NOT "benchmark-blind holdout". The second framing is
  stronger and we haven't earned it.
- If both B-dev and B-holdout are passed in the same tranche, that
  is standard holdout, not transfer.

## Wall-clock extensions

Measured sparse-vision evidence now exists, but the original Pareto frontier
notation is still about answer quality versus effective fresh-frame budget.
When adding wall-clock rows, keep them in a separate denominator regime and
report:

- latency (wall-clock prefill + generation)
- peak memory
- measured vision-encode FLOP skip
- measured cross-axis composition gain (e.g., our method × FastV)

Do not cite Track B numbers as semantic Pareto wins. Cite them only as
measured wall-clock evidence with setup, thermal pairing, and component-share
denominators visible.

## Related

- [planner-sweep.md](planner-sweep.md) — how to search policies
- [temporal-coverage-metrics.md](temporal-coverage-metrics.md) —
  budget placement axes
- [feature-replay.md](feature-replay.md) — why replay is not a
  Track B substitute
