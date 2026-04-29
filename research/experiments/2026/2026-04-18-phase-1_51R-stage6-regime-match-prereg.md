# Phase 1.51R Stage 6: 32-Frame Regime-Match Pilot

**Status:** preregistration 2026-04-18, task #106. Scheduled after
Stage 5 closes and the current Stage 6 kr-sweep at 8 frames
completes. Directly tests scale-out-regime-gap hypothesis from
`2026-04-18-scaleout-regime-gap-note.md`.

## Motivation

the pre-release source reports 1.8× e2e speedup on Gemma-3 27B at 32 frames. We measure
1.23× on Gemma 4-E4B at 8 frames. Arithmetic ceiling analysis says:
the gap is mostly regime, not mechanism. Specifically, 32 frames
shifts `G / (D+P+V+G)` upward, loosening the ceiling.

**Projection:** at 32 frames on our stack, with kr=0.10 and observed
s=6.83, aggregate ceiling lifts from 1.46× (our 8-frame number) to
~1.78× (close to the pre-release source's 1.8×).

Stage 6 regime-match tests this projection with a minimum-cost pilot.

## Preregistration

### Objective

Run 1.51R at 32 frames on a VideoMME long-bucket subset (n=10) at
the Stage 2b operating point (anchor=none, kr=0.10, max_tokens=32)
and measure aggregate + per-bucket e2e speedup. Compare the
observed ceiling against the projected 1.78×.

### Claim register targets

- Paper claim 11: direct test of "does 1.51R reproduce the pre-release source's 1.8×
  when regime matches."
- Paper claim 5: per-item wall-clock with the larger prefill
  dominates, provides a sparse-execution data point that is less
  decode-bound than our 8-frame numbers.

### Hypotheses

- **H1 (regime lifts ceiling to ~1.8×).** At 32 frames, aggregate
  e2e lands in [1.5×, 2.0×] on long-bucket items at kr=0.10.
  Falsification: aggregate e2e below 1.3× at the matched operating
  point.
- **H2 (accuracy behaves as at 8 frames).** Δacc vs dense at 32
  frames / kr=0.10 is within [-0.15, -0.05] on long bucket (our
  8-frame measurement was -0.20 on long). The 32-frame regime might
  *improve* long-bucket accuracy because frames cover more of the
  video content. Falsification: Δacc < -0.25 (worse than 8 frames)
  — would indicate the prune mechanism itself breaks at larger
  frame counts.
- **H3 (memory footprint stays inside budget).** Peak RSS on M3 Air
  16GB stays ≤ 12 GB. Falsification: OOM or page-storm.

### Acceptance band

- H1 + H2 both earned → paper gets the "the pre-release source 1.8× reproduces at
  matched regime" headline.
- H1 earned, H2 partial → still a publishable regime-match result;
  adjust the operating point.

### Rejection band

- H1 rejected (e2e < 1.3× at 32 frames) → mechanism is less effective
  at larger frame counts, or our per-token speedup measurement is
  different from the pre-release source's. Opens a new investigation: why does prefill
  shortening scale sublinearly with prefill length?

### Execution plan

1. **Feasibility smoke**: single VideoMME long item at 32 frames
   dense. Measure RSS peak, D, V, G. If peak < 12 GB and total wall
   clock < 180s, proceed. If not, abort Stage 6 until 1.54 (decode
   acceleration) lands — 32-frame decode alone may be too slow.
2. **Pilot tranche**: 10 long-bucket items at 32 frames, anchor=none
   kr=0.10. ~30 min wall time. Report aggregate + per-item e2e/gen/
   per_tok + Δacc.
3. **Decision point**: if H1 earned, extend to medium + short buckets
   (n=10 each, another 60 min). If rejected, write a findings doc
   and do not extend.

### Preregistered deviations

- Frame count 32 instead of 8 (the whole point).
- `anchor_arm=none` (matches Stage 2b which is the 8-frame reference
  for the 1.8× claim).
- `kr=0.10` (matches Stage 2b).
- Long bucket only for the pilot (most regime-lift expected there).

All other parameters identical to Stage 2b: max_tokens=32, Gemma
4-E4B-4bit, videomme_dev_v1 manifest.

### Required implementation check

- Driver (`scripts/run_novelty_pruning_gemma.py`) has
  `--frame-count` CLI flag; 32 should be a drop-in. Verify prefill
  doesn't hit the MLX max sequence length (2048 default might cap;
  32 frames × 256 tok = 8192 visual + ~30 text tokens = ~8224
  prefill).
- Novelty-pruning anchor arms compute O(T · frames · tokens_per_frame)
  — will need to confirm scaling at 32 frames doesn't OOM for
  `nuwa_pillar` or `max_min_diversity` before Stage 5-style sweeps.

## Links

- Trigger condition: current Stage 6 kr=0.33 / kr=0.25 sweep at 8
  frames completes, giving us full kr × anchor coverage at 8 frames.
- Related: `research/experiments/2026/2026-04-18-scaleout-regime-gap-note.md`
  has the projection math.
- Related: `research/experiments/2026/2026-04-18-arithmetic-ceiling-findings.md`
  has the ceiling calculation that motivates the 1.78× projection.
- Paper claim: #11 (novelty-pruning delivers e2e speedup on Gemma),
  if H1 earned, this closes the pre-release reproduction gap.
