# Phase 1.29: Codec-Native H.264 Extractor (Sam Port)

**Status:** deferred preregistration — scheduled after 1.51R anchor-arm
comparison (Stage 5) completes. Supersedes the earlier "MV-only via
PyAV" framing (see history in git log; that prereg was pixel-diff
proxy science that this rewrite replaces). Updated 2026-04-18 per
Codex 2026-04-18 review identifying Sam's `experiments/h264_metadata.py`
as the single highest-value import from the whitepaper repo.

## Preregistration

### Objective

Port Sam's codec-native H.264 extractor from the whitepaper repo
(`experiments/h264_metadata.py`) into `codec_through` under
`src/codec_through/codec/h264_metadata.py`, surface the extractor
through a `BlockStatistic`-compatible adapter, and adjudicate
pixel-diff-proxy vs codec-native on a small local slice. This is the
deployability bridge that moves the paper from "pixel-diff proxy
science" to "real codec-guided system with a credible production
path."

### Why this is the priority Sam import

The Codex 2026-04-18 review named this as the single most important
Sam artifact codec-through does not yet have. Two concrete correctness
details Sam's implementation fixes that the pixel-diff path silently
gets wrong:

1. **Skip-MB default must be zero-MV inter, not intra.** In H.264,
   skip macroblocks have predicted MVs from neighbors and a zero
   residual — they are inherently "nothing changed" signals, not
   "codec refused to encode" signals. Treating them as intra inflates
   the motion signal on static regions.

2. **B-frames need bidirectional residuals + looser thresholds.**
   B-frames reference both past and future and their residual magnitude
   distribution is different from P-frame residuals. A single
   threshold tuned on P-frames flags too many (or too few) B-frame
   blocks as changed. Sam's implementation handles both reference
   directions and relaxes the decision threshold accordingly.

Both of these are trivial to get wrong in a scratch implementation
and non-trivial to diagnose without a ground-truth reference.

### Claim register targets

- Paper claim 1 ("codec-derived proxies are valid training-free
  routing signals") — moves from "proxy validated under pixel-diff"
  to "proxy validated under real codec metadata."
- Paper claim 5 ("real sparse execution converts proxy gain into
  measured speedup") — a codec-native extractor is the prerequisite
  for any streaming / live-decode path (see Sam's
  `exp_live_stream_demo.py` as the design target for Track B).
- `WP-3.3`.

### Reproduction mode

- method-development via port. Do **not** just cite Sam's extractor
  in a footnote — port it, test it against the whitepaper's reported
  behavior on a small slice, and keep it in-tree so future changes can
  be tracked against our regression suite.

### Track: A (same planner, swapped signal source)

### Gating

Runs after 1.51R Stage 5 (anchor-arm comparison at kr=0.50) lands
and after the claim-11 picture has crystallized. Independent of
benchmark GPU load (H.264 extraction is CPU).

### Hypotheses

- **H1 (codec-native correlates with pixel-diff)**: per-block,
  codec-native motion-vector magnitude and our pixel-diff
  MAX_ABS statistic are correlated at Pearson r > 0.5 across our
  TOMATO motion dev items. This is weaker than the old 1.29's r>0.7
  target because (a) codec metadata carries real encoder decisions
  that pixel-diff cannot replicate and (b) our pixel-diff is itself
  a proxy for latent feature change, so two proxies converging tightly
  would be surprising.
- **H2 (codec-native maintains TOMATO holdout Pareto tie)**: a
  codec-native planner tuned to the same effective_fresh_frames target
  (~3.4 on TOMATO holdout) maintains `cached_accuracy ≥ 0.267` (within
  1 item of the pixel-diff result 0.333@3.55).
- **H3 (codec-native is deployable)**: H.264 metadata extraction adds
  ≤ 100 ms per 8-frame clip on our M3 Air — acceptable overhead for a
  future streaming deployment. This matches Sam's reported numbers in
  whitepaper §3 but must be replicated locally.
- **H4 (skip-MB correctness matters)**: the corrected skip-MB handling
  reduces the fraction of false-positive "changed" blocks on static
  scenes (TOMATO direction items) by at least 30% relative to a naive
  implementation that treats skip-MB as intra.
- **H5 (B-frame correctness matters)**: B-frame-specific threshold
  handling changes the fresh-frame allocation on at least 3/15 dev
  items relative to treating B-frames identically to P-frames.

### Acceptance band

- H1: r ≥ 0.5 (we expect ~0.3–0.6 based on pixel-diff vs feature-diff
  r ranges from phase 1.36).
- H2: `cached_accuracy ≥ 0.267` on TOMATO holdout N=30.
- H3: extraction latency ≤ 100 ms / 8-frame clip.
- H4: ≥ 30% reduction in false-positive changed blocks on static
  TOMATO direction items.
- H5: ≥ 3/15 dev items change fresh-frame allocation when B-frame
  correctness is toggled.

### Rejection band

- H1: r < 0.15 (codec signal is nearly uncorrelated with pixel-diff —
  would force a reassessment of whether pixel-diff was ever a valid
  proxy).
- H2: `cached_accuracy < 0.200` on TOMATO holdout (2 items below
  pixel-diff result).
- H3: extraction latency > 500 ms / 8-frame clip (would rule out
  streaming deployability on M3-class hardware).
- H4: < 10% reduction (skip-MB correction is in the noise).
- H5: 0/15 items change (B-frame correction has no observable effect
  at this budget).

### Inconclusive

- Sam's `h264_metadata.py` is not portable as-is (e.g. depends on a
  vendored codec SDK we don't have). Fallback: port the skip-MB and
  B-frame logic manually over PyAV `EXPORT_MVS` side-data, flag any
  behavior differences from Sam's reference in the findings doc.
- Our TOMATO / MVBench corpus uses an H.264 profile or container
  variant that doesn't surface all the metadata the extractor
  expects. Document which items fail, fall back to pixel-diff for
  those items, report extraction coverage as a separate metric.

### Code change

1. New module `src/codec_through/codec/h264_metadata.py` — port from
   Sam's `experiments/h264_metadata.py` in the whitepaper repo. Keep
   variable names and function signatures close to the original so
   future diffs with Sam remain legible.
2. New `BlockStatistic` variant: `CODEC_NATIVE_MV_MAGNITUDE` — reads
   from the extractor, aggregates to our 28×28 block grid on the
   Qwen path (or 16×16 on the Gemma path via
   `compute_pixel_novelty` downstream adapter).
3. Regression tests under `tests/codec/test_h264_metadata.py`:
   - skip-MB on a synthetic black clip yields zero motion signal.
   - a clip with motion-only between I- and P-frames (no B-frames)
     yields expected MV magnitudes.
   - a clip with B-frames yields bidirectional residuals and the
     corrected threshold logic picks different blocks than a
     P-frame-only threshold.
4. Harness flag `--planner-signal=codec_native` wired through
   `scripts/run_benchmark_track_a.py`.

### Execution plan

1. Pilot: run extractor on 1 TOMATO direction clip + 1 MVBench object
   interaction clip. Verify side-data presence. Verify skip-MB and
   B-frame paths produce finite non-zero output.
2. Dev tranche: 15 TOMATO motion dev items, 15 MVBench object
   interaction dev items. Compute per-block correlation with
   pixel-diff MAX_ABS and publish a (r, n, scatter) figure.
3. Holdout: re-run TOMATO N=30 holdout with `CODEC_NATIVE_MV_MAGNITUDE`
   as the routing signal at the current promotion budget. No retune of
   the threshold — we want to measure portability of the existing
   routing policy to the new signal, not a fresh sweep.

### Runtime estimates (benchmark compute only)

| stage                  | scope            | ~wall-clock   | notes                                |
|------------------------|------------------|---------------|--------------------------------------|
| pilot                  | 2 items          | < 1 min       | CPU-only extractor smoke             |
| dev tranche            | 30 items × 2 bm  | ~15 min       | extractor + correlation computation  |
| holdout TOMATO N=30    | 30 items         | ~30 min       | full benchmark wall-clock            |

Total runtime: ~45 min benchmark wall-clock (excluding the 2-min
pilot).

### Links

- Sam whitepaper §3 (H.264 extractor)
- Sam whitepaper §3.2 (skip-MB correctness)
- Sam whitepaper §3.3 (B-frame bidirectional residuals)
- Sam's `experiments/h264_metadata.py` (port source)
- Sam's `experiments/codec_pipeline.py` — downstream design target
- Sam's `exp_live_stream_demo.py` — streaming deployment target
- CoViAR (arXiv 1712.00636) — classical MV-based video representation
- [docs/research-strategy-post-codecsight.md](../../../docs/research-strategy-post-codecsight.md)
- Project memory `project_sam_imports_2026-04-18.md` — Codex review
  that prioritized this rewrite over other Sam imports

### Result

Pending.

### Interpretation

Pending.
