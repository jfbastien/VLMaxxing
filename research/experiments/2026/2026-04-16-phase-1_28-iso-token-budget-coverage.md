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

**Protocol deviation** (2026-04-16): the preregistered plan called
for calibrating a threshold pair at frame_count=16 so
`effective_fresh_frames ≈ 4` (iso-budget vs dense-4). That
calibration step was NOT run. Instead, the existing
`max_abs(8,32) static+shifted age=4` policy was launched at
frame_count=16 **without re-tuning thresholds for iso-budget**.
Result: the 16-frame runs landed at substantially higher than
4 effective fresh frames.

- TOMATO motion dev @ 16 frames:
  reuse_ratio_mean_active = 0.606 → fresh ≈ **6.90** (not 4)
- MVBench motion holdout @ 16 frames:
  reuse_ratio_mean_active = 0.495 → fresh ≈ **8.58** (not 4)

So this is NOT a clean iso-budget test. It is an off-budget probe
of "same policy at higher frame count," documented honestly below.

## Result (off-budget probe, not iso-budget)

**TOMATO motion dev @ 16 frames** (vs 8 frames reference):

| metric | @ 8 frames (phase 1.10 winner) | @ 16 frames |
|---|---|---|
| cached_accuracy | 0.400 | 0.467 (+1 item on N=15) |
| effective_fresh_frames | 3.99 | 6.90 (+73% budget) |
| agreement | 0.867 | 0.867 |

Interpretation: more frames at the same threshold policy added 1
item of accuracy at 73% more budget. Not Pareto-better than
dense-6 (which was 0.400 at 6 frames) at comparable budget. NOT a
coverage win.

**MVBench motion holdout @ 16 frames** (vs 8 frames reference):

| metric | @ 8 frames (phase 1.12.B) | @ 16 frames |
|---|---|---|
| cached_accuracy | 0.667 | 0.667 (same) |
| effective_fresh_frames | 4.59 | 8.58 (+87% budget) |
| agreement | 0.933 | 0.933 |

Interpretation: accuracy saturates at 0.667 going from 8 → 16
frames on this slice at this policy. Pareto-dominated by dense-8
(0.733 at 8 frames, same agreement). **REJECTION** of the
preregistered H1 on MVBench holdout — more frames without iso-
budget calibration did not buy additional accuracy.

## Interpretation

**Preregistration outcome: Inconclusive (protocol deviation).**

The preregistered iso-budget test (16 frames at fresh ≈ 4 via
tighter thresholds) was not run. The 16-frame probes that DID
run consumed roughly 2× the preregistered budget and therefore
test a different question: "does the same policy help with more
frames at higher budget?" Answer from the committed artifacts:

- TOMATO: marginally (+1 item accuracy at +73% budget)
- MVBench holdout: no (accuracy saturated, budget doubled)

For the true iso-budget test, a follow-up cell with calibrated
higher thresholds at frame_count=16 is still required. Tracked as
phase 1.28.B in the todo queue.

Important live-citation caveat: `paper/framing.md`,
`docs/literature-map-2026-04-16.md`, and decision-log cite these
16-frame numbers as evidence that "more frames at this policy does
not help." That interpretation is still valid (and is consistent
with the budget-placement theory). But those numbers should NOT
be cited as "phase 1.28 iso-budget result" — they are off-budget
probes at higher frame counts.

## Links

- CoPE-VideoLM Appendix H.4 FPS-coverage story
- [phase 1.8 TOMATO motion frame-budget](2026-04-14-phase-1_8-motion-frame-budget-baselines.md)
- [phase 1.10 TOMATO motion dev grid](2026-04-14-phase-1_10-planner-grid-tomato-motion-dev.md)
- [docs/literature-map-2026-04-16.md](../../../docs/literature-map-2026-04-16.md)
- Pre-release CodecSight strategy notes are preserved in git history; current
  release-facing positioning is in [paper/framing.md](../../../paper/framing.md)
  and [docs/related-work-table.md](../../../docs/related-work-table.md).
