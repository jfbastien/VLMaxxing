# Phase 1.35: Event-Window Oracle Baseline

## Preregistration

Objective:

- Establish an UPPER BOUND on method headroom: for items where a
  critical event window is known (or inferrable), run a dense-only
  cell that spends 100% of its fresh budget inside the event
  window. The resulting accuracy caps what any frame-scheduling
  method can achieve on the same slice.
- Compare our current cached winner and matched dense-N against
  this oracle ceiling to quantify remaining headroom.

Claim register targets:

- Paper claim 3 (bounded staleness + sticky-dynamic + projector
  group repair hard failures): an oracle ceiling lets us say how
  much of the theoretical headroom our current mechanism captures.

Reproduction mode:

- Oracle-baseline construction; not a method claim.

Track: A.

Gating: depends on phase 1.20 TOMATO N=30 landing (need enough
items to both annotate event windows and evaluate stably), AND
depends on either manual event-window annotation OR inferrable
event windows (e.g., TOMATO direction items have implicit
direction-change frames).

Hypotheses:

- **H1 (real headroom)**: the event-window oracle accuracy on
  TOMATO motion dev is strictly higher than dense-6 accuracy
  (0.400 at N=15, likely similar at N=30). Magnitude: at least
  0.533 (8/15 or equivalent 16/30) expected.
- **H2 (current cached captures partial headroom)**: our cached
  winner captures somewhere between 50% and 100% of the gap between
  dense-N and the oracle. Lower-bound claim: at least 50% of the
  gap is captured by the current mechanism.
- **H3 (sticky-dynamic closes more of the gap)**: phase 1.26
  sticky-dynamic captures more of the oracle gap than the vanilla
  cached winner (if phase 1.26 results support this).

Acceptance band:

- H1: oracle accuracy ≥ dense-6 accuracy + 2/N items.
- H2: cached accuracy ≥ dense-6 + (oracle - dense-6) × 0.5.

Rejection band:

- H1 rejected: oracle accuracy within N=15 Wilson CI of dense-6 —
  means the frames themselves carry less information than expected
  on this slice; our method has no room to win.

Inconclusive: event-window annotation is imprecise; budget is
spent on approximately-correct frames.

## Event-window sources (in order of preference)

1. **Manual annotation for a small subset**: TOMATO direction, a
   handful of MVBench items. ~30 min annotation effort for 15 items.
2. **Dense-oracle proxy**: the frames where same-run dense changes
   its answer vs dense-1 are the "information frames." For items
   where dense-8 > dense-1, the additional information must live
   in frames 2..7; a 3-frame oracle can spend budget on the frames
   that maximize per-pair change.
3. **Held-out item label inference**: use the item's metadata
   (question type, ground-truth answer) to find the frames where
   the cue appears.

Start with option 2 (proxy) to keep scope bounded.

## Implementation sketch

New script `scripts/event_window_oracle.py`:

- For each item, compute per-frame-pair change scores (e.g.,
  max_abs).
- For a target budget of K frames: pick K frames centered on the
  highest-change frame-pair.
- Run dense at those K frames via `run_benchmark_track_a.py` with
  a new `--frame-indices` override.

## Execution

Pending phase 1.20 + manual/proxy event-window annotation.

## Result

Pending.

## Interpretation

Pending.

## Links

- Pre-release CodecSight strategy notes are preserved in git history; current
  release-facing positioning is in [paper/framing.md](../../../paper/framing.md)
  and [docs/related-work-table.md](../../../docs/related-work-table.md).
- [docs/methodology/temporal-coverage-metrics.md](../../../docs/methodology/temporal-coverage-metrics.md)
- ChatGPT 2026-04-16 audit recommendation.
