# OV-3 Full Analysis: What We Found, What Remains

Date: 2026-05-10
Hardware: M3 16GB MBA, MLX unified GPU, ~5h cumulative GPU time so far.

## What we know firmly

After 60 inference passes across n=10 dev, n=20 dev∪holdout, and n=10 holdout-disjoint
on Qwen2.5-VL-7B-4bit at 8 frames:

1. **Three independent codec score sources track frozen-Qwen dense answers exactly on
   20/20 unique items**: novel_coded (`intra | cbf`), motion-vector magnitude, residual
   energy. Each codec source picks materially different tile sets (Jaccard 0.014 to
   1.0) but the model produces the same final answer on every item.

2. **OneVision-style weighted motion+residual fusion regresses to the pixel baseline.**
   On all 30 codec-cached inferences across the three passes, fused matches the pixel
   answer set on every item. The fancier signal is strictly worse than its components
   here.

3. **The codec planner is deterministic across driver invocations; the dense baseline
   is not.** On the 10 holdout items run twice (n=20 session and disjoint session),
   pixel and codec answers were byte-identical in both runs on every item. Dense
   flipped on item 066-3 between sessions (3 → 2). Codec_cached forward passes are
   more stable than dense.

4. **Pixel max_abs drifts from dense on a fixed share of items, codec does not.** On
   item 037-2 in the dev tranche (ground truth 2): dense says 2, pixel says 0, three
   simple codec sources say 2. Codec rescues the answer pixel loses.

5. **H.264 metadata extraction overhead via PyAV: ~19s/item median on M3.** This is
   ~80% of codec-cached inference time, not orders of magnitude smaller. The "free
   signal" framing is principled (every video decoder computes this metadata anyway)
   but our PyAV-based extraction re-decodes separately. A decoder-integrated
   implementation would amortize this; the measured cost is an upper bound.

## What we discovered that wasn't obvious going in

### Dense's run-to-run instability

I expected the dense baseline to be a fixed reference. It isn't. Item 066-3 flipped
its dense answer between two driver sessions on the same model, same prompt, same
input. The cached forward passes (pixel-cached, codec-cached) didn't move. This means:

- "codec→dense agreement" as a metric is bottlenecked by dense's variance, not the
  codec planner.
- The planner-quality story is *understated* by codec→dense numbers. The codec
  planner is producing a *more stable* answer than dense.
- Implication for the paper: report codec→dense, but also report codec→ground-truth
  directly, and measure dense→dense across re-runs. Otherwise the planner-quality
  metric is confounded.

### Pair-jaccard is a misleading proxy

Motion-only at jaccard 0.014 (essentially zero overlap with pixel's tile selection)
still hits codec→dense on every item. Selection overlap does not predict downstream
agreement on this slice. The model is robust to *which* tiles are kept fresh, as long
as the planner keeps a "right enough" set. This argues against using Jaccard as a
quality signal in any future ablation.

### Fused fails by mimicking pixel, not by being noisy

The OneVision fusion picks tile selections that, after threshold calibration, end up
producing the **same final answer set as pixel max_abs on every item**. Fused
codec→pixel = 20/20. This is a structural failure mode of fusion-then-threshold, not
a noise problem. The threshold calibration is share-based (picks thresholds to hit
target static/shifted shares), so the fusion's percentile-normalized magnitude
distribution converges with pixel's high-magnitude regions because both end up
triggering on similar high-energy zones. The fix would be either (a) absolute
thresholds tied to physical units, or (b) a less-collapsing fusion (e.g., max
instead of weighted mean), or (c) the fancy fusion is just the wrong intervention
for a frozen-backend planner.

## What remains to be done

### Running now: frame=16 robustness on 20-item manifest

ETA ~3-4h on M3. Tests whether codec→dense=20/20 holds at 2x frame budget. The
8-frame result might depend on the specific budget; 16-frame is a natural deployment
point and shifts the keep-rate operating point.

### Highest-value next experiments, in order

**1. Wire codec scores into Track B (OV-6) — 2-4h coding + smoke**

This is the actual industry-impact lane. Track A (semantic substitution) preserves
answers; Track B (real vision-stage work skipped) gives wall-clock E2E speedup.

Wiring plan, ~80-150 LoC:
- `QwenVisionPruneConfig` (`src/codec_through/qwen_pruned_vision_tower.py:38-50`):
  add `codec_score_grid: np.ndarray | None = None` field.
- `_group_scores` (line 65): add `"codec_grid"` mode that returns the precomputed
  per-group score array directly.
- Call site (line 197): pass `config.codec_score_grid` through.
- `scripts/run_phase1_51V.py`: add `--codec-score-source` CLI flag, compute per-item
  codec score (same path as Phase 1.29), pool to merged-group level via
  `qwen_groups_per_frame`, attach to config.
- Smoke on 7-item C-PERSIST video set or 10-item short dev (~1h GPU on M3).

Memory: Phase 1.51V peaks ~6.7GB on M3 16GB. Tight but feasible.

**2. Direct ground-truth analysis on existing data — 30 min CPU only**

We have answer_index in every results.jsonl row. Recompute codec_correct,
pixel_correct, dense_correct directly without depending on dense as the reference.
This separates "did codec match dense" (planner quality) from "did codec produce the
correct answer" (deployment quality). Probably tells a sharper story than what we
have now.

**3. Multi-seed dense characterization — 2.5h GPU**

Run the n=20 driver a second time on the same manifest. Compare dense answers across
the two driver sessions. Quantify the dense-flip rate (we observed 1 in 10 in our
single overlap; a clean re-run gives us a tighter rate estimate). This directly
addresses the dense-non-determinism finding.

**4. Threshold sensitivity sweep — 4h GPU**

The current thresholds are calibrated per-item from pixel-derived target_shares. Try
absolute thresholds (e.g., motion_magnitude > 1.0 px) and a higher static_share
(0.50, 0.70) to see if codec→dense holds across the operating space or only at the
share-matched point.

**5. TOMATO motion-heavy benchmark — 4h GPU**

We've only tested VideoMME short. TOMATO's motion-heavy items would stress-test the
codec saliency claim. Manifest exists: `tomato_motion_dev_v2.toml` and similar.
Different bucket, different bias.

**6. Frame=32 budget — 6-8h GPU**

If frame=16 holds the codec→dense=20/20 line, frame=32 tests the upper bound. Memory
may push 14GB peak; M3 16GB is tight here.

### Not feasible without significant work

- **OV-4 NVIDIA parity oracle**: requires `cv_reader` + CUDA + Linux. ~$30 Lambda
  H100 evening. Worth it for upstream-parity credibility, optional otherwise.
- **OV-6 Track B + C-PERSIST composition**: needs OV-6 wiring done first. Then ~3-4h
  to plumb session-level timings into `build_c_persist_setup_inclusive.py`.
- **Cross-family Gemma OV-3**: the runner hardcodes Qwen feature replay. Would need
  a Gemma-aware wrapper (~100-200 LoC). Not urgent given the cross-source replication
  on Qwen.

## What this looks like to the paper editor

The current evidence supports:

1. **Strong claim, narrowly bounded**: at matched ~10% mean active reuse on VideoMME
   short with Qwen2.5-VL-7B-4bit at 8 frames, codec saliency (any of three simple
   sources) preserves dense answers on 20/20 unique items while pixel max_abs drifts
   on 1/20.

2. **Negative result, reproducible**: OneVision-style weighted motion+residual fusion
   does not transfer to a frozen-backend Track A planner; it converges to pixel-
   baseline behavior on every item tested.

3. **Methodological caveat, important**: dense's run-to-run instability means
   codec→dense is a *lower bound* on planner quality. The codec planner is more
   stable than dense.

4. **Decision-log reopen**: continuous H.264 spatial scoring is empirically reopened
   for VideoMME short / Qwen / 8-frame, with bounded scope.

What the paper still needs (in order of impact):

- Wall-clock E2E speedup numbers from Track B (OV-6) at the codec-validated operating
  point. This is the "WOW for industry" the framing claims and we don't have it yet.
- Frame budget robustness (frame=16 running; frame=32 if M3 holds).
- Cross-benchmark replication (TOMATO motion).
- Either multi-seed dense characterization, or a switch to ground-truth-direct
  reporting that doesn't depend on dense's stability.

## Honest assessment

We did good Track A science. The negative result on fusion is publishable as a
boundary claim. The positive result on simple codec sources is publishable conditional
on the dense-determinism caveat.

We have NOT yet done the industry-impact lane (Track B E2E timing). Without that, the
WOW framing is aspirational. The next 3-5h on M3 should produce frame=16 robustness;
the next 5-8h after that should produce a Track B smoke. That's the work to commit
to before the paper draft moves.
