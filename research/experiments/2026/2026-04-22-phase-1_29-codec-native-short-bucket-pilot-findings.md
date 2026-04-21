---
phase: 1.29
date: 2026-04-22
parent: research/experiments/2026/2026-04-22-phase-1_29-codec-native-integration-audit.md
prior:
  - research/experiments/2026/2026-04-19-phase-1_29-codec-native-integration-design.md
  - research/experiments/2026/artifacts/phase1_29_short_bucket_pilot/summary.json
status: CLOSED — hard falsification. Short-bucket pilot (n=5, all short VideoMME items) shows codec OR-aggregated class shares degenerate to **100% NOVEL on every sparse pair of every item**; mean |Δ| vs pixel-diff reference = 53.8pp (gate: 10pp). The "MAX over native-rate span" aggregation is unusable at 8-frame sparse sampling. Stages A/B/C integration as-designed is **infrastructure-falsified on aggregation choice**. Redesign required before paper-body codec-native run.
tracking: autonomous session 2026-04-21/22 dynamic-loop
---

# 1.29 Codec-native short-bucket pilot — findings (HARD FALSIFICATION)

## Headline

| item                 | total_fr | extract_s | pix S/X/N           | codec S/X/N        | Δ (codec−pix)              |
|----------------------|----------|-----------|---------------------|--------------------|----------------------------|
| videomme:short:037-2 |     3116 |      22.9 | 0.838 / 0.011 / 0.151 | 0.000 / 0.000 / 1.000 | −0.838 / −0.011 / **+0.849** |
| videomme:short:210-2 |     2669 |      20.6 | 0.400 / 0.003 / 0.597 | 0.000 / 0.000 / 1.000 | −0.400 / −0.003 / **+0.403** |
| videomme:short:282-2 |     2438 |      21.1 | 0.442 / 0.117 / 0.441 | 0.000 / 0.000 / 1.000 | −0.442 / −0.117 / **+0.559** |
| videomme:short:120-2 |     1541 |      13.0 | 0.402 / 0.060 / 0.538 | 0.000 / 0.000 / 1.000 | −0.402 / −0.060 / **+0.462** |
| videomme:short:158-3 |     1986 |      15.9 | 0.400 / 0.019 / 0.581 | 0.000 / 0.000 / 1.000 | −0.400 / −0.019 / **+0.419** |

**Aggregate (n=5):** pix mean = 0.496 / 0.042 / 0.462, codec mean = 0.000 / 0.000 / 1.000, Δ = **−0.496 / −0.042 / +0.538**, max|Δ| = **0.538**.

Pre-integration gate from audit: proceed if max|Δ| < 0.10. **Failed by 5×.** The codec OR-aggregate is not a drop-in for pixel-diff at sparse 8-frame sampling.

Runtime: 5 items × ~20 s extract = ~100 s total compute. Pilot completed end-to-end in ~5 min (including Python cold-start and parquet IO). Matches the audit's "30-60 min" budget estimate with significant headroom.

## Why every pair degenerates to 100% NOVEL

`classify_blocks_h264` labels a native-rate macroblock:

- **STATIC** if `skip_flag` is set (codec signals the MB is a verbatim copy of the corresponding MB in the reference).
- **NOVEL** if `intra_flag` OR any residual-CBF bit is set (MB has independent data — either I-coded or significant residual).
- **SHIFTED** otherwise (inter-coded with MVs but zero residual).

The OR-aggregation step upgrades class across the ~250-400 native-rate frames between each sparse-sampled frame (short clips at 30 fps, 8 sparse frames → ~150-250 ms of real time per pair → ~30-60 I-frames per span given typical ~1-2 s keyframe intervals). With that many frames in the aggregation window, **every** 16×16 macroblock position accumulates at least one `intra_flag` or CBF bit somewhere in the span — so the max-pool over span locks to NOVEL everywhere.

The SHIFTED class gets completely wiped out because it is strictly the "inter, no-residual, not-skip" leftover — the aggregation is dominated by the NOVEL hits elsewhere in the span.

This is not a bug in `H264MetadataExtractor` or `classify_blocks_h264`. Both functions work correctly at native-rate, per the regression tests that landed with task #114. It is an **aggregation-choice falsification**: MAX-over-span is the wrong reduction when the span dwarfs the typical keyframe interval.

## What this means for the paper

The 1.29 prereg (task #98, 2026-04-20) called for "a codec-native planner run on a 30-clip subset" as "the biggest single missing Sam bridge". That framing presupposed codec labels are a drop-in replacement for pixel-diff labels. This pilot falsifies that presupposition **at the aggregation design point**; the upstream extractor is fine.

Three design responses, in increasing order of paper-body payoff:

1. **Change the aggregation rule.** Instead of MAX-over-span, use
   `fraction_of_static_MBs >= threshold → STATIC` (a majority/threshold vote).
   Cheapest fix; keeps labels. But preserves the class-vs-class distribution
   mismatch observed in the Δ pattern — STATIC is systematically under-selected
   because the "single non-skip MB anywhere in 10s" condition is easy.

2. **Replace label-pass with continuous-score-then-rethreshold.** Emit a
   codec-score (e.g. `fraction_of_non_skip_MBs` per pair position, or
   `mean_residual_energy`), let `classify_blocks_with_planner` re-threshold it
   using the existing `static_threshold` / `shifted_threshold` machinery.
   This is the design-note's §Stage B alternative. Medium effort; preserves
   the planner's calibration story; aligned with how Sam's whitepaper actually
   uses codec metadata.

3. **Abandon the sparse-sampling retrofit; run codec-native at native rate.**
   This is the priority-doc's should-do #4 direction (Sam-streaming reproduction,
   task #155 prereg). Codec metadata is designed for contiguous frames; sparse-
   sampling breaks its semantic. Full re-framing; highest paper-body payoff;
   highest engineering cost; aligned with Sam's whitepaper claim space.

Recommendation: **pick option 2 for the paper-body row**, document option 3 as
the natural next-step follow-up. Option 1 is a false economy — it produces
numbers but the per-class distribution will still diverge from pixel-diff,
so the comparison claim "codec matches pixel-diff on the planner signal" won't
cleanly close.

## Claim-matrix / priority / registry edits

- `paper/priority.md` should-do #8 ("1.29 local codec-native benchmark slice"):
  update status from "PRE-INTEGRATION AUDIT 2026-04-22" to "**SHORT-BUCKET PILOT
  FALSIFIED 2026-04-22**: MAX-over-span aggregation degenerates to 100% NOVEL
  on every sparse pair (mean |Δ| = 53.8pp vs pixel-diff). Next: re-design
  aggregation per 2026-04-22-phase-1_29-codec-native-short-bucket-pilot-findings.md
  §'What this means' option 2."
- `paper/framing.md` Reviewer-Facing Limitations: keep current "codec-native
  local-benchmark slice is future work"; the pilot falsification does not alter
  the reviewer story — it sharpens *why* the slice is not yet submission-ready.
- `research/falsified-hypotheses.md`: add entry "codec OR-aggregated labels
  are a drop-in for pixel-diff at 8f sparse VideoMME — falsified 2026-04-22,
  max|Δ|=0.538 on n=5 short-bucket items".

## Reproduction

```
uv run python scripts/pilot_1_29_short_bucket.py
```

Reads `research/experiments/2026/artifacts/phase1_57/qwen_8f_dev30.json`
(1.57 pixel-diff reference) and VideoMME short-bucket video files under
`data/benchmarks/videomme/videos/`. Writes
`research/experiments/2026/artifacts/phase1_29_short_bucket_pilot/summary.json`.

Env: `mlx-vlm 0.4.4` / PyAV latest / macOS Darwin 25.3.0 / M3 16 GB.
Git SHA at run-time: `8150887` (clean on top of curation audits commit).

## Non-goals

- **No full-bucket (medium/long) re-run.** Short-bucket falsification is
  unambiguous; adding long-bucket items will produce an even more degenerate
  100%-NOVEL signal (longer spans → stronger aggregation lock).
- **No alternative-aggregation sweep.** The finding is about the "MAX over
  span" rule specifically; evaluating alternatives is a follow-up experiment
  requiring its own design note.
- **No Stages A/B/C implementation.** Blocked upstream on aggregation redesign.
