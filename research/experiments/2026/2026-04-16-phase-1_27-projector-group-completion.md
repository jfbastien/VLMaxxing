# Phase 1.27: Projector-Group Mask Completion (CodecSight-Borrowed)

## Preregistration

Objective:

- implement CodecSight's projector-group-completion rule in our
  planner: after the block-level dynamic mask is computed, snap it
  to the Qwen 2.5-VL 2×2 spatial-merge projector tiles. If any of
  the 4 sub-blocks in a tile is dynamic, all 4 are forwarded through
  ViT. If none is dynamic, the whole tile is skipped end-to-end.
- answer whether projector-group completion (which reduces the
  granularity of the dynamic mask) changes dev accuracy, holdout
  Pareto status, or just the compute profile.

Claim register targets:

- Paper claim 3 (projector-consistent sparse execution is needed for
  deployability), paper claim 5 (real skipped compute).
- `WP-3.3`

Reproduction mode:

- method-development; borrowed from CodecSight Section 3.3 "projector
  group completion".

Track: A (quality at matched budget) and groundwork for Track B
(projector multiplication is actually skippable when all 4 sub-blocks
are static).

Gating: depends on phase 1.26 or runs in parallel — the two mechanisms
compose, so they're evaluated separately first then together in
phase 1.26.B.

Hypotheses:

- **H1 (accuracy-neutral)**: projector-group completion is NOT expected
  to change cached_accuracy materially on our existing dev/holdout
  slices — its purpose is deployability, not accuracy. Delta ≤ ±0.067
  (1 item on N=15).
- **H2 (compute-measurable)**: in a Track B measurement (phase 1.30+),
  projector-group completion lets us skip a 2×2 block projector
  matmul for each fully-static tile, producing a measurable FLOP
  reduction beyond pure token-count reduction.
- **H3 (mask-coarsens)**: effective_fresh_frames rises slightly
  because small isolated dynamic blocks now force their whole tile to
  be dynamic. Expected rise 0.1–0.3 fresh frames on TOMATO motion.

Acceptance band:

- H1: |Δ cached_accuracy| ≤ 0.067 on each of TOMATO/MVBench dev runs
- H2: requires Track B harness; defer to phase 1.30.
- H3: 0.0 ≤ extra_fresh_frames ≤ 0.5.

Rejection band:

- H1: |Δ cached_accuracy| > 0.133 (2 items on N=15); projector-group
  completion is destroying information, not just coarsening masks.

Inconclusive:

- ties within Wilson CI.

Policies (Phase 1.27.A, dev only):

1. `max_abs(8,32) static+shifted age=4` + projector_group_completion
   on TOMATO motion dev.
2. `max_abs(16,64) static+shifted noage` + projector_group_completion
   on MVBench motion dev.

Runtime: 2 cells × 15 items × ~2 min ≈ 1 hr GPU. Cheap because feature
replay cache from phase 1.10 / 1.11 covers both slices.

## Code change

Add a `projector_group_completion: bool` field to `PolicyCandidate`.
In the benchmark runner's mask construction, after computing
`allowed_mask`, reshape to (H_blocks, W_blocks) where H/W correspond
to the 2×2 tile grid. Then OR into blocks of 2×2 sub-blocks. Reshape
back to flat. This is ~10 lines in
`run_benchmark_track_a.py::_mix_qwen_features`.

## Execution

Pending.

## Result

Pending.

## Interpretation

Pending.

## Links

- CodecSight §3.3 projector-group completion
- [phase 1.26 sticky-dynamic](2026-04-16-phase-1_26-sticky-dynamic-planner.md)
- [docs/literature-map-2026-04-16.md](../../../docs/literature-map-2026-04-16.md)
