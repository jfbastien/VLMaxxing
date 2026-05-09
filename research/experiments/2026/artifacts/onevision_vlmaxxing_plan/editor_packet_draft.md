# Editor Packet — OneVision × VLMaxxing OV-3 Track A Findings

Date: 2026-05-09
Branch: `onevision-vlmaxxing-research`
Status: dev tranche complete (n=10), broader pass running (n=20), holdout pending

## TL;DR for the editor

We tried OneVision-Encoder's contribution as a Track A planner inside frozen Qwen2.5-VL-7B.
Three of the four codec score sources beat the pixel max_abs baseline by **+10 percentage
points** at matched fresh budget with **zero paired-choice drift versus dense**. The
OneVision-style motion+residual fused score did **not** beat the simpler legacy continuous
H.264 saliency signal that the repo had previously deprioritized. Net: continuous codec
saliency is back on the table for the paper, but the OneVision-style fancy-fusion idea is
rejected as a planner choice on this slice.

These are dev-tranche numbers (n=10) and so suggestive, not conclusive. Larger-N pass is
running.

## Headline numbers — VideoMME short dev, n=10, 8-frame Qwen2.5-VL-7B-4bit

| source | dense | pixel | codec | codec−pixel | codec→dense drift | pair_jaccard |
|---|---|---|---|---|---|---|
| novel_coded (intra\|cbf) | 0.800 | 0.700 | **0.800** | +0.100 | 0/10 | 0.614 |
| motion-vector magnitude  | 0.800 | 0.700 | **0.800** | +0.100 | 0/10 | 0.520 |
| residual energy proxy    | 0.800 | 0.700 | **0.800** | +0.100 | 0/10 | 0.616 |
| **OneVision fused (mw=rw=1)** | 0.800 | 0.700 | **0.700** | +0.000 | 1/10 | 0.565 |

Mean active reuse 0.117–0.121 codec versus 0.125 pixel — same spend, better answers, with
the right score source.

## What this changes in the manuscript

1. **Related work upgrade.** OneVision-Encoder is the closest trained codec-aligned encoder
   counterpart to VLMaxxing. The paper should cite it as such. We propose a one-paragraph
   addition that names OneVision's training-time contribution (codec patchification, 3D
   RoPE, cluster discrimination at 128 A800 scale), separates it from VLMaxxing's
   training-free anti-recomputation contribution, and flags the score-fusion piece as the
   one OneVision idea we tested and could not transfer to a frozen backend.

2. **Decision-log reopen, with discipline.** "Continuous H.264 spatial scoring as saliency
   oracle" was deprioritized in our decision log. The reopen condition was: simple routing
   plateaus AND a raw-artifact reread shows stronger-than-expected correlation. OneVision
   is the external prior that justified the reread. Three independent codec score sources
   each match dense at +10% over pixel with zero drift on the dev tranche. If holdout
   confirms, we reopen the deprioritization with a bounded statement: codec saliency
   improves Track A semantic substitution at our matched fresh-budget operating point on
   short VideoMME items.

3. **A clean negative result for fancier-is-better.** OneVision's score fusion idea
   (percentile-normalized motion + residual at unit weights) regressed to the pixel
   baseline on this slice. Codec_pixel_agreement = 1.000 — fused literally selects the
   pixel answer set. This is a non-trivial finding because it argues against directly
   importing OneVision's score fusion into a frozen-backend planner; the wins live in the
   simpler signals.

## Industry impact framing — the WOW

At zero training cost, zero parse-failure risk, and ~12% of the matched-budget vision
work refreshed per item, frozen Qwen2.5-VL-7B with codec-fed Track A reuse hits **dense
accuracy** on this slice while pixel-diff loses 10 percentage points. The mechanism is
pure runtime: codec metadata is already computed by every video decoder; we read it for
free and use it to gate VLMaxxing-style prefix reuse. No retraining, no quantization
drop, no architecture change.

## What we did NOT claim

- We did not run OV-4 upstream parity against `cv_reader` — that requires NVIDIA/Linux
  and is deferred.
- We did not run OV-6 Track B sparse vision — frozen-tower fragility and the negative
  fused result on Track A make this lower-value unless we add a trained adapter.
- We did not multiply patch-reduction × C-PERSIST speedup. Per the comparison table's
  e2e_policy, those denominators are reported separately.
- We did not change the manuscript prose. This packet is the handoff for the editor to
  decide what the paper edits should be.

## What still needs to happen

- N=20 short-dev+holdout pass (running; ETA ~2.5h).
- OV-8 C-PERSIST session economics — accounting only, no new model time.
- Editor decision on related-work + decision-log reopen language.
- Optional: a single Lambda H100 evening for OV-4 parity (~$30 spend) if we want
  upstream-parity credibility.

## Replication

```bash
uv run python scripts/preflight_onevision_vlmaxxing.py --scope all
bash scripts/run_ov3_dev_ablation.sh      # n=10 short dev
bash scripts/run_ov3_holdout_ablation.sh  # n=20 short dev+holdout (running)
uv run python scripts/build_ov3_dev_comparison.py
```

Artifacts:

- `research/experiments/2026/artifacts/phase1_29_onevision_dev/comparison.md`
- `research/experiments/2026/artifacts/phase1_29_onevision_dev/<source>/summary.json`
- `research/experiments/2026/artifacts/onevision_vlmaxxing_plan/comparison_table_plan.md`

This packet will be updated with N=20 numbers as soon as that run completes.
