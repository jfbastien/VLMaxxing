# Phase 1.38: Temporal Placement Ablations

## Preregistration

Objective:

- run 6 dense-only ablation cells on TOMATO motion dev (N=15) to
  isolate which temporal window carries the decisive evidence for
  each item. This sharpens the "budget placement over time" theory.

Cells:

1. frame 0 only (1 frame)
2. middle frame only (frame 4, 1 frame)
3. last frame only (frame 7, 1 frame)
4. first + last (2 frames)
5. uniform 4 (frames 0, 2, 5, 7)
6. uniform 8 (existing dense-8 baseline, for reference)

Compare per-item accuracy across cells. Items where middle-only
beats first-only are "middle-event items" — exactly the items our
cached planner must not miss.

Claim register targets:

- Paper claim 2 (naive mean-diff is too blunt): placement ablations
  reveal which frames carry evidence.
- Methodology: sharpens the "budget placement" theory with causal
  evidence.

Reproduction mode: dense-only ablation (no cached policy).

Track: A (diagnostic).

Gating: can run any time. ~6 cells × 15 items × ~2 min = ~3 hrs GPU.

Hypotheses:

- **H1 (middle-event items exist)**: on TOMATO direction items,
  middle-only accuracy > first-only accuracy for at least 2/5 items.
- **H2 (uniform beats any single frame)**: uniform-4 accuracy >
  max(first, middle, last) on the full 15-item slice.
- **H3 (first+last is a strong 2-frame baseline)**: first+last
  accuracy matches or exceeds uniform-4 on MVBench motion dev (where
  endpoints carry action context), but not on TOMATO direction (where
  middle motion carries the cue).

Acceptance: H1 passes for TOMATO direction; H2 confirmed on both
slices.

## Execution

Pending scheduling. Requires a `--frame-indices` override flag in
the benchmark runner (or pre-computed frame extraction).

## Result

Pending.

## Interpretation

Pending.

## Links

- [docs/methodology/temporal-coverage-metrics.md](../../../docs/methodology/temporal-coverage-metrics.md)
- ChatGPT 2026-04-16 review: "temporal placement ablations"
