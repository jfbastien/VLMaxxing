# Phase 1.28: Iso-Token-Budget Coverage Experiment (CoPE-Framing)

## Preregistration

Objective:

- answer the central question from CoPE-VideoLM (2602.13191): if the
  cached method lets us process MORE frames at the SAME
  fresh-token-equivalent budget, does temporal reasoning accuracy
  improve?
- pit `dense-N frames` against `cached-M frames` at equal
  effective_fresh_frames. Concretely: compare dense-4 (4 frames of
  fresh tokens) against cached-8-frames with reuse tuned to produce
  ≈4 effective_fresh_frames, and cached-16-frames with reuse tuned
  to produce ≈4 effective_fresh_frames.

Claim register targets:

- Paper claim 4: "the saved budget can be spent on more frames, not
  just less latency."
- `WP-3.1`, `WP-3.3`

Reproduction mode:

- method-development; framing borrowed from CoPE Table 1 + Appendix
  H.4, but applied to our training-free method at iso-fresh-token
  budget rather than iso-keyframe-density.

Track: A (Pareto frontier at matched budget)

Gating: runs immediately; the benchmark runner already supports
arbitrary frame counts; we just need to pick a cached policy that
produces ~4 effective_fresh_frames at 16 total frames.

Hypotheses:

- **H1 (16-frame coverage wins)**: at iso-budget of 4
  effective_fresh_frames, cached-16 accuracy > cached-8 accuracy >
  dense-4 accuracy on TOMATO motion dev. Directional ordering is
  the claim; magnitudes can be small.
- **H2 (16-frame coverage wins on MVBench motion holdout too)**: if
  H1 is confirmed on TOMATO, reuse the cached-16 policy on MVBench
  holdout — the holdout rejection may have been specific to 8-frame
  clipping, not cached reuse itself.
- **H3 (saturation beyond 16)**: cached-32-frames at 4
  effective_fresh_frames does NOT improve over cached-16 (mirrors
  CoPE's 2 FPS → 3 FPS train/test mismatch finding).

Acceptance band (cached-16 result on TOMATO dev):

- cached-16 cached_accuracy ≥ cached-8 cached_accuracy + 0.067
  (1 more item correct on N=15)
- cached-16 cached_accuracy ≥ dense-4 cached_accuracy on the same
  slice (matched fresh-token budget).

Rejection band:

- cached-16 accuracy < dense-4 accuracy at matched budget (extra
  coverage didn't help).

Inconclusive:

- within Wilson CI; rerun at N=30 (phase 1.20).

Cells (TOMATO motion dev + holdout):

1. cached `max_abs(8,32) static+shifted age=4` at frame_count=16,
   reuse calibrated to ≈0.8 (= effective_fresh_frames ≈ 4)
2. cached same policy at frame_count=32 with reuse ≈0.90 (≈ 4 fresh
   frames)
3. dense baseline at frame_count=4 (already in phase 1.8)

Extend to MVBench motion holdout only if TOMATO H1 passes.

Runtime budget: ~2 cells × ~15 items × ~2 min ≈ 1 hr GPU on TOMATO.
Extra 1 hr if MVBench extension runs.

## Code change

Only plumbing: the benchmark runner already accepts `--frame-count`.
We need to verify that our policy's reuse ratio at `frame_count=16`
produces ~0.8 so `effective_fresh_frames ≈ 4`. Run one calibration
pass first (CPU) to confirm.

## Execution

Pending. Plan:
1. Run phase 1.19-style calibration at frame_count=16 on TOMATO
   motion dev to pick the right threshold pair.
2. Launch the 2 cached-16 and cached-32 cells.
3. Compare to dense-4 (already on disk from phase 1.8).

## Result

Pending.

## Interpretation

Pending.

## Links

- CoPE-VideoLM Appendix H.4 FPS-coverage story
- [phase 1.8 TOMATO motion frame-budget](2026-04-14-phase-1_8-motion-frame-budget-baselines.md)
- [phase 1.10 TOMATO motion dev grid](2026-04-14-phase-1_10-planner-grid-tomato-motion-dev.md)
- [docs/literature-map-2026-04-16.md](../../../docs/literature-map-2026-04-16.md)
- [docs/research-strategy-post-codecsight.md](../../../docs/research-strategy-post-codecsight.md)
