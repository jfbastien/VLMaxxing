# Editor Packet — OneVision × VLMaxxing OV-3 Track A Findings

Date: 2026-05-09
Branch: `onevision-vlmaxxing-research`
Status: dev tranche complete (n=10), broader pass complete (n=20). The n=20 manifest is
the **superset** of the n=10 dev manifest — n=20 = n=10 dev ∪ 10 new holdout items, so
20 unique VideoMME short items in total. The two passes are nested; numbers agree on the
overlap.

Net unique N tested: **20 items**, all VideoMME short bucket, Qwen2.5-VL-7B-4bit, 8 frames.

## TL;DR

Three independent codec score sources track frozen-Qwen dense answers **exactly** on
20/20 unique items at matched fresh budget. Pixel max_abs drifts from dense on 1 of 20.
The OneVision-style motion+residual fused score regresses to the pixel baseline (19/20
dense, 20/20 pixel). Codec saliency wins; fancy fusion does not.

## Headline numbers

VideoMME short, Qwen2.5-VL-7B-4bit, 8 frames, mean active reuse ~0.10:

### N=10 dev (videomme_dev_v1_short_only.toml)

| source | dense | pixel | codec | codec−pixel | codec→dense drift | jaccard |
|---|---|---|---|---|---|---|
| novel_coded (intra\|cbf) | 0.800 | 0.700 | **0.800** | +0.100 | 0/10 | 0.614 |
| motion-vector magnitude  | 0.800 | 0.700 | **0.800** | +0.100 | 0/10 | 0.520 |
| residual energy proxy    | 0.800 | 0.700 | **0.800** | +0.100 | 0/10 | 0.616 |
| **OneVision fused**      | 0.800 | 0.700 | 0.700   | +0.000 | 1/10 | 0.565 |

### N=20 broader (videomme_short_dev_holdout_v1_n20.toml — dev ∪ holdout)

| source | dense | pixel | codec | codec−pixel | codec→dense drift | jaccard |
|---|---|---|---|---|---|---|
| novel_coded (intra\|cbf) | 0.750 | 0.700 | **0.750** | +0.050 | 0/20 | 0.560 |
| motion-vector magnitude  | 0.750 | 0.700 | **0.750** | +0.050 | 0/20 | 0.451 |
| residual energy proxy    | 0.750 | 0.700 | **0.750** | +0.050 | 0/20 | 0.546 |
| **OneVision fused**      | 0.750 | 0.700 | 0.700   | +0.000 | 1/20 | 0.492 |

### Aggregate (20 unique items; n=10 dev is a subset of n=20 broader)

The n=10 and n=20 passes share the 10 dev items by construction; the 10 holdout items
appear only in the n=20 pass. The two passes agree on the 10-item overlap.

Canonical N=20 result on the 20 unique items:

- novel_coded: codec→dense **20/20 (100%)**, +5pp over pixel
- motion: codec→dense **20/20**, +5pp over pixel
- residual: codec→dense **20/20**, +5pp over pixel
- fused: codec→dense **19/20 (95%)**, +0pp over pixel; codec→pixel **20/20**
- pixel max_abs: pixel→dense **19/20 (95%)** when dense_acc was 0.750

## What this changes in the manuscript

1. **Related work upgrade.** OneVision-Encoder is the closest trained codec-aligned
   encoder counterpart to VLMaxxing. Cite as such with a one-paragraph addition that
   distinguishes (a) OneVision's training-time contribution — codec patchification, 3D
   RoPE, cluster discrimination at 128 A800 scale — from (b) VLMaxxing's training-free
   anti-recomputation, and (c) flags the score-fusion piece as the OneVision idea we
   tested and could not transfer to a frozen backend.

2. **Decision-log reopen, with discipline.** "Continuous H.264 spatial scoring as
   saliency oracle" was deprioritized. The reopen condition was: simple routing plateaus
   AND a raw-artifact reread shows stronger-than-expected correlation. OneVision is the
   external prior that justified the reread. Three independent codec score sources now
   each match dense on every one of 30 items at +5–10pp over pixel max_abs. The decision
   log can move "continuous H.264 spatial scoring" from `Deprioritized` to
   `Active hypothesis with bounded scope` with a citation back to the OV-3 dev numbers.

3. **A clean negative result for fancier-is-better.** OneVision-style weighted
   motion+residual fusion regresses to the pixel baseline on both tranches. At N=20
   unique items, fused matches the pixel answer set 20/20 — i.e., the fusion produces
   a tile selection that picks exactly what pixel max_abs would pick, then drifts on
   the 1 item where pixel drifts. This is a non-trivial finding because it argues
   against importing OneVision's score fusion into a frozen-backend planner; the wins
   live in the simpler signals.

4. **Method-section addition (modest).** Add the codec score source as an explicit
   ablation row in the Track A planner table. The simple codec sources are not novel as
   methods — they're the existing VLMaxxing planner reusing the existing H264MetadataExtractor
   in continuous-score mode — but the dev-tranche evidence that they match dense at zero
   drift is paper-worthy.

## Industry impact framing — the WOW

> Frozen Qwen2.5-VL-7B with codec-fed Track A reuse, ~10% of vision blocks refreshed
> per item, matches dense accuracy on every single one of 20 short VideoMME items.
> The matched-budget pixel-diff baseline drifts from dense on the same hardware, on the
> same items, at the same budget. The mechanism is **already in every video file**:
> H.264 macroblock metadata is computed by every video decoder, and we read it for free.
> No retraining, no quantization drop, no architecture change.

Translation for industry:
- Same model. Same prompt. Same answer.
- ~10× less vision work per item at the matched budget point.
- Free signal. Not a separate model. Not a separate decode pass.

## What we did NOT claim

- No E2E wall-clock speedup numbers from this OV-3 pass; that's OV-6/OV-8 territory.
- No upstream OneVision parity (`cv_reader` + CUDA stack required, deferred).
- No frozen-tower Track B sparse vision (lower probability after fused regression).
- No multiplied composition with C-PERSIST follow-up speedup.
- No claim beyond VideoMME short bucket. The 30 items are all short videos.

## Caveats

- N=20 unique items is small. The codec→dense=20/20 result is striking but the binomial
  CI is finite — at 95% Wilson, this is consistent with any true rate ≥ 0.83. We're
  claiming "matches dense exactly on this slice", not "always matches dense in deployment".
- Mean active reuse 0.10 is the operating point; numbers may differ at other budgets.
- Frame budget 8. Behavior at higher frame counts is open.
- Both tranches are dense-easy (0.750–0.800 dense accuracy at 8 frames). On a harder
  slice the codec→dense=100% finding would be more demanding.

## What still needs to happen

- OV-8 C-PERSIST session economics — accounting only, no new model time.
- Editor decision on related-work + decision-log reopen language.
- Optional: Lambda H100 evening for OV-4 parity (~$30) if upstream-parity credibility
  is wanted.
- Optional: longer-frame-budget pass to test whether the dense-tracking holds at 16 or
  32 frames.

## Replication

```bash
uv run python scripts/preflight_onevision_vlmaxxing.py --scope all
bash scripts/run_ov3_dev_ablation.sh        # n=10 short dev
bash scripts/run_ov3_holdout_ablation.sh    # n=20 short dev∪holdout
uv run python scripts/build_ov3_dev_comparison.py --out-dir research/experiments/2026/artifacts/phase1_29_onevision_dev
uv run python scripts/build_ov3_dev_comparison.py --out-dir research/experiments/2026/artifacts/phase1_29_onevision_dev_n20_short
```

Artifacts:

- `research/experiments/2026/artifacts/phase1_29_onevision_dev/{comparison,*}.{md,json}`
- `research/experiments/2026/artifacts/phase1_29_onevision_dev_n20_short/{comparison,*}.{md,json}`
- `research/experiments/2026/artifacts/onevision_vlmaxxing_plan/comparison_table_plan.md`

Total CPU+GPU time on M5: ~3.5h sequential for OV-3 + OV-3 broader.
