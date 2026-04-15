# Phase 1.29: Motion-Vector-Only Signal Path (Deployability)

## Preregistration

Objective:

- prototype H.264 motion-vector extraction via PyAV for our TOMATO /
  MVBench corpora. Produce per-frame per-block MV statistics
  compatible with our `BlockStatistic` API.
- answer whether an MV-only planner correlates strongly with our
  pixel-diff planner and whether MV-only maintains the TOMATO
  holdout Pareto tie.

Claim register targets:

- Paper claim 1: "codec-derived proxies are valid training-free
  routing signals" — MV-only is the deployable version of that
  claim.
- `WP-3.3`

Reproduction mode:

- method-development; signal source swap from pixel-diff to
  MV-only; borrows CodecSight's α=0 default (§3.1, Eq. 3).

Track: A (same planner with a different signal)

Gating: runs after 1.26/1.27 if time allows. Independent GPU load.

Hypotheses:

- **H1 (MV correlates with pixel-diff)**: per-block, MV magnitude and
  our pixel-diff statistic are correlated at Pearson r > 0.7 across
  the 15 TOMATO motion dev items.
- **H2 (MV-only reaches dense-6 tie on TOMATO holdout)**: an MV-only
  planner tuned to the same effective_fresh_frames target (~3.4 on
  TOMATO holdout) maintains cached_accuracy = 0.267.
- **H3 (MV-only is deployable)**: PyAV MV extraction adds ≤ 100 ms
  per item on our M3 Air — acceptable overhead for a future
  streaming deployment.

Acceptance band:

- H1: r ≥ 0.7
- H2: cached_accuracy ≥ 0.200 (within 1 item of pixel-diff result)
- H3: MV extraction latency ≤ 100 ms/item

Rejection band:

- H1: r < 0.3 (MV signal is nearly uncorrelated with pixel-diff)
- H2: cached_accuracy < 0.133 on TOMATO holdout (2 items below
  current pixel-diff tie)
- H3: extraction latency > 500 ms/item

Inconclusive:

- PyAV fails to surface MVs for our specific H.264 profile (old
  videos sometimes lack side-data). Drop to flow-based proxy.

## Code change

New helper `src/codec_through/codec/mv_extract.py`:

- `extract_motion_vectors(video_path: Path) -> np.ndarray`
- Uses `av.open(video_path).decode(video=0)` with
  `stream.codec_context.flags2 |= av.codec.context.Flags2.EXPORT_MVS`
  to enable MV side-data export
- Returns per-frame MV arrays of shape `(H, W, 2)` for the video's
  native resolution
- Aggregates to block level: mean MV magnitude per our 28×28 block

New `BlockStatistic` variant:
`MV_MAGNITUDE_MEAN` — uses extracted MVs instead of pixel diff.

## Execution

Pending phase 1.26/1.27 completion.

Planned pilot: run MV extraction on 1 TOMATO direction clip. Verify
side-data presence. If fail, try `flags2 |= 0x00040000` (raw bit for
ff_export_mvs).

## Result

Pending.

## Interpretation

Pending.

## Links

- CodecSight §3.1 MV extraction via NVDEC (we use PyAV instead)
- CoViAR (arXiv 1712.00636) — classical MV-based video
  representation
- [docs/research-strategy-post-codecsight.md](../../../docs/research-strategy-post-codecsight.md)
