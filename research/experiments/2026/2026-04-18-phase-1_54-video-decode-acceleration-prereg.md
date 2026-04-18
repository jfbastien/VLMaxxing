# Phase 1.54: Video-Decode Acceleration (Long-Item Lever)

**Status:** preregistration 2026-04-18, task #105. **Deferred** —
not on the ship-worthy critical path for the current paper. Recorded
so the idea is not re-derived later and so sequencing is obvious when
long-bucket results force the lever to open.

## Motivation

Arithmetic-ceiling analysis (task #88, 2026-04-18) decomposed 1.51R
end-to-end latency into D (video decode), P (processor / tokenization),
V (vision tower), and G (LLM prefill+generate). The per-bucket
breakdown revealed:

| bucket | D / e2e | P / e2e | V / e2e | G / e2e |
|--------|--------:|--------:|--------:|--------:|
| short  |    0.0% |   ~0.5% |   37.7% |   61.8% |
| medium |   48.0% |   ~0.2% |   10.8% |   41.0% |
| long   |   **85.7%** |  ~0.05% |   4.8% |    9.5% |

**D dominates long-bucket e2e (85.7%).** Neither 1.51R (touches G)
nor 1.51V (touches V) can lift long-bucket e2e beyond ~1.098×. Any
credible long-item speedup must touch D.

## Preregistration

### Objective

Replace the current CPU FFmpeg-based frame-extraction path with a
faster decode backend, measure its effect on D for long-bucket
VideoMME items, and re-run the full 1.51R Stage 2b + Stage 5
measurements with the new D to see how much headroom opens on the
long-item ceiling.

### Why this is deferred, not running now

1. **Accuracy gap is already better characterized than speed.**
   Long bucket at kr=0.10 anchor=none was -20pp (Stage 2b); at
   kr=0.50 gemma_structural is +10pp (Stage 5c). The paper already
   has a long-item earned story at kr=0.50, which does not require
   D reduction to land.
2. **1.51V is the higher-priority e2e lever for short/medium.** 1.54
   only helps long items. 1.51V helps short + medium, which is where
   our current accuracy-earned results sit.
3. **Decode optimization is a systems lift, not science.** There is
   no falsifiable hypothesis about *whether* faster decode reduces
   D; there's only "how much, and at what engineering cost". The
   paper does not need this phase to clear publication bar.
4. **Tracks Sam's codec-native extractor (phase 1.29) — unify
   later.** Sam's H.264 extractor is the likely long-term backend
   for this. Preregistering 1.54 now guarantees 1.29 completion
   flows directly into the long-item speedup story.

### Candidate decode backends

1. **PyAV / hardware-accelerated FFmpeg** (Metal `h264_videotoolbox`
   or `hevc_videotoolbox` on macOS). Least-effort replacement.
2. **Decord** (<https://github.com/dmlc/decord>). Widely used in
   video-VLM literature; supports seek without full-container decode.
3. **Sam's codec-native extractor** (phase 1.29). Bypass decode
   entirely: emit I-frame pixels + motion-vector sidecar without
   pixel reconstruction for intermediate frames. Most aggressive.

### Hypotheses

- **H1 (hardware decode reduces D).** `h264_videotoolbox` cuts
  long-bucket D by ≥ 3× vs CPU FFmpeg at 8 frames uniform sampling.
  Falsification: ≤ 1.5× speedup.
- **H2 (decode reduction lifts long-bucket e2e ceiling).** At Stage
  5c `gemma_structural kr=0.50` numbers, applying the H1 decode
  speedup to D predicts a long-bucket ceiling lift from 1.00× to
  ≥ 1.3×. Falsification: re-measured long-bucket e2e still below
  1.10×.
- **H3 (accuracy is unchanged).** Faster decode produces
  byte-identical frames (or within a JPEG-quant tolerance). 1.51R
  accuracy does not shift by more than ±0.03pp aggregate.
  Falsification: Δacc > 3pp from backend swap alone.

### Acceptance band

- H1 + H2 + H3 all earned → 1.54 lands, paper gains long-item e2e
  story, typically with a sparse execution ceiling chart that
  separates D-limited and G-limited regimes.

### Rejection band

- Any of H1/H2 fails → publishing 1.54 is not useful; keep 1.29 as
  the long-term decode replacement when codec-native lands.

### Execution plan (when un-deferred)

1. **Smoke**: swap to `h264_videotoolbox` on a single VideoMME long
   item, measure D vs CPU FFmpeg.
2. **Dev tranche**: full VideoMME dev (n=30) at Stage 5c operating
   point with the new decode path. Report per-bucket e2e/gen/per_tok
   + Δacc vs CPU baseline.
3. **Holdout**: one-shot run at the chosen operating point.

Runtime estimate: ~2h total (implementation + dev + holdout).

## Links

- Trigger condition: 1.51V results landed and the long-item
  accuracy story still leaves D as the binding constraint for e2e.
- Related: `research/experiments/2026/2026-04-18-arithmetic-ceiling-findings.md`
- Related: `research/experiments/2026/2026-04-17-phase-1_29-codec-native-prereg.md` (Sam's
  H.264 path; if that lands first, 1.54 collapses into 1.29).
- Paper claim: part of claim #5 (real sparse execution converts
  proxy gain into measured speedup) — specifically the "long-item"
  wall-clock narrative.
