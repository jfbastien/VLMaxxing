# Phase 1.30: Streaming-Window Harness (Track B groundwork)

> **Status update 2026-04-19 (Codex round-21 reframe).** This phase
> is reframed from "Track-B streaming-window harness" to "composition
> lever for Phase 1.55 (persistent KV-cache) and Phase 1.56 (VLM-
> signaled refresh)." Priority lowered to **P2** until 1.55/1.56
> upstream gates clear. The original Track-B framing (CodecSight-
> comparable UCF-Crime setting) is retained as a long-term goal but
> is no longer load-bearing for the next-round paper. See
> `2026-04-19-codex-round-21-scaleout-imports.md` §1 for full rationale.

> **Status update 2026-04-21 (Codex round-24 rescope pending).**
> Round-24 codex review calls for this phase to be rewritten against
> **the pre-release source's actual streaming/deployment protocol** rather than the
> abstract infrastructure harness below. Target protocol from the pre-release source's
> pre-release source §2.13.3 + §5 (deployment): (1) pre-prefill queue —
> frames arrive into a rolling buffer; (2) persistent KV-cache reuse
> across consecutive queries on the same clip; (3) selective re-
> prefill only at attention-context-drift boundaries (NOT every
> frame); (4) decoder co-location with the client to avoid the
> frame-upload round-trip. The paper narrative wants **a local
> reproduction of the pre-release source's N=60 streaming line** (biggest bridge gap
> round-24 identified). Design changes from the original harness:
> - Drop UCF-Crime entirely — use VideoMME dev+holdout 60-item
>   aggregation paired with persistent-KV replay, to match the
>   benchmark we already report on.
> - Preregister the same "clean / mixed / degenerate" bucket
>   structure the pre-release source uses so the reproduction is side-by-side comparable.
> - Runtime target: ~90 min at 8f L=2 kr_V=0.50 (C-VISION best cell)
>   with persistent-KV reuse, thermally paired unpatched baseline.
> The rewrite is deferred to a separate prereg
> `2026-04-2?-phase-1_30-streaming-the pre-release source-reproduction-prereg.md` rather
> than an in-place edit, so this file stays as the historical
> Track-B-streaming lineage. See `paper/priority.md` should-do #4 for
> paper-time prioritization.

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
- Pre-release CodecSight strategy notes are preserved in git history; current
  release-facing positioning is in [paper/framing.md](../../../paper/framing.md)
  and [docs/related-work-table.md](../../../docs/related-work-table.md).
