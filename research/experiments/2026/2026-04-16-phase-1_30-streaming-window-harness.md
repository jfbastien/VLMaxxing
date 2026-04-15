# Phase 1.30: Streaming-Window Harness (Track B groundwork)

## Preregistration

Objective:

- build a streaming-inference harness that runs our cached planner
  on overlapping sliding windows of a longer video (e.g., 40-second
  clip at 2 FPS, 20% stride per CodecSight's UCF-Crime setting).
- this is NOT our primary benchmark (TOMATO and MVBench are our
  temporal-reasoning focus) but is required for a CodecSight-comparable
  operating point in Track B.

Claim register targets:

- Paper claim 5: "real sparse execution converts proxy gain into
  measured speedup" — streaming is where the sticky-dynamic window
  overlap benefit materializes.

Reproduction mode:

- infrastructure (harness build); no new benchmark claims in this
  phase. Slice down to a small continuous-video pilot first.

Track: A + Track B prep.

Gating: depends on phase 1.26 + 1.27 landing and Track B timing
instrumentation (not yet designed). Low priority in the current
tranche.

Hypotheses:

- **H1 (harness works)**: a sliding-window harness over a 40-second
  video produces a sequence of cached inferences with reproducible
  wall-clock timings.
- **H2 (overlap cache helps)**: feature replay cache hits on
  overlapping window frames reduce per-window latency by ≥ 20%.
- **H3 (sticky-dynamic compounds with streaming)**: sticky-dynamic
  masks from phase 1.26, once they extend across window boundaries
  via feature-cache persistence, produce a larger compute reduction
  than either mechanism alone.

Acceptance band:

- harness runs end-to-end on 1 clip without error
- wall-clock per window is ≤ 110% of dense baseline (no net
  slowdown from bookkeeping)

Rejection band:

- harness adds > 50% wall-clock overhead for bookkeeping — the
  streaming axis isn't viable without deeper mlx-vlm integration.

Inconclusive:

- not enough continuous-video corpus to benchmark meaningfully.

## Corpus setup

- Pick 3 clips from UCF-Crime or a similar continuous-video source.
  Clips that don't require ethical review (no violent content for
  this pilot).
- Alternatively: concatenate 4 × 10-second TOMATO shape_trend items
  into a synthetic 40-second video as a controllable pilot.

## Harness design

- `scripts/streaming_harness.py`:
  - decode video, compute MVs (phase 1.29) or pixel-diff per frame
  - apply planner to produce dynamic mask
  - run cached ViT on dynamic tiles, feature-cache on static ones
  - emit per-window answer + timing
  - report aggregate wall-clock + FLOP count

## Execution

Pending phase 1.26/1.27/1.29 and Track B timing instrumentation.

## Result

Pending.

## Interpretation

Pending.

## Links

- CodecSight streaming setup (§4.1 UCF-Crime)
- [docs/research-strategy-post-codecsight.md](../../../docs/research-strategy-post-codecsight.md)
