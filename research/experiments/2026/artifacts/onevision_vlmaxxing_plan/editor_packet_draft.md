# Editor Packet — OneVision x VLMaxxing OV-3 / OV-6 Findings

Date: 2026-05-11
Branch: `onevision-vlmaxxing-research`
Hardware: M3 16GB MacBook Air, MLX unified GPU
Status: OV-3 Track A complete (dev, N=20, holdout-disjoint, frame=16, N=57 replication).
OV-6 Track B complete (smoke + N=57 replication + keep-rate sweep + layer sweep).

## OV-6 Track B at the canonical N=57 scale (kr=0.5, layer=2)

| arm | accuracy | vision_ms | e2e_ms | codec_extract_s/item |
|---|---|---|---|---|
| dense (no prune) | **0.684** | 9669 | 38711 | — |
| uniform_random kr=0.5 | 0.491 | 5226 | 33261 | — |
| codec_motion kr=0.5 | 0.456 | 4893 | 31092 | 17.87 |
| codec_novel_coded kr=0.5 | 0.439 | 4900 | 31146 | 17.63 |
| magnitude_norm kr=0.5 | 0.421 | 5415 | 33838 | — |
| codec_residual kr=0.5 | 0.386 | 5298 | 33729 | 19.30 |

**At N=57, the ordering inverted from the N=10 smoke.** Uniform_random is now the
best pruner by point estimate (0.491), magnitude_norm drops below random to 0.421,
and codec_residual is the worst at 0.386. None of the importance scorers exceeds
random by point estimate at kr=0.5 / layer=2 on the broader N. The "structured
magnitude pruning earns its keep over random"
narrative does not survive the broader manifest.

The codec arms are the FASTEST pruners by end-to-end (codec_motion 31.1 s/item,
codec_novel_coded 31.1 s/item, vs dense 38.7 s/item) — about 20% E2E speedup over
dense, but they bring 17-19 s/item of upstream PyAV metadata extraction overhead
that the magnitude / random arms don't pay. Net: codec is not a wall-clock win at
this configuration after counting extraction.

## OV-6 keep-rate sweep at layer=2 (N=10)

| source | kr=0.30 | kr=0.50 | kr=0.70 | kr=0.90 |
|---|---|---|---|---|
| magnitude_norm | 0.600 | 0.600 | **0.800** | 0.600 |
| codec_novel_coded | 0.500 | 0.400 | **0.800** | 0.600 |
| codec_motion | 0.500 | 0.400 | 0.700 | 0.600 |
| codec_residual | 0.500 | 0.500 | **0.800** | 0.700 |

**The accuracy curve is non-monotonic.** kr=0.7 is the sweet spot: at the kr=0.7
operating point, magnitude_norm, codec_novel_coded, and codec_residual all reach
0.800 (= N=10 dense). At kr=0.5 and kr=0.9 every arm regresses. The window-aligned
pruner's quota rounding produces a configuration at kr=0.7 the model can recover
from gracefully; at other keep-rates the systematic mistakes of any non-random
scorer cost more than its signal is worth.

## OV-6 layer sweep at kr=0.5 (N=10)

| source | layer=1 | layer=2 | layer=4 | layer=8 |
|---|---|---|---|---|
| magnitude_norm | 0.600 | 0.600 | 0.700 | 0.700 |
| codec_novel_coded | 0.600 | 0.400 | 0.600 | 0.400 |
| codec_motion | 0.400 | 0.400 | 0.400 | 0.400 |
| codec_residual | 0.400 | 0.500 | 0.600 | **0.700** |

**codec_residual scales monotonically with prune depth and ties magnitude_norm at
layer=8.** The deeper the prune point, the better residual-energy codec scores
become as an importance proxy. codec_motion is stuck at 0.400 everywhere — pure
motion magnitude does not predict importance at any depth. magnitude_norm
plateaus at 0.700 by layer 4.

## OV-6 N=57 promotion of the two N=10 sweet-spot cells

Both N=10 sweet-spot cells were promoted to N=57:

### Cell 1: kr=0.7 / layer=2 / N=57

| arm | acc | gap vs magnitude_norm |
|---|---|---|
| dense | 0.684 | — |
| **codec_novel_coded** | **0.614** | **+7.0pp** |
| codec_residual | 0.579 | +3.5pp |
| codec_motion | 0.561 | +1.7pp |
| magnitude_norm | 0.544 | — |

**All three codec sources beat magnitude_norm by point estimate at the broader N.**
The strongest cell is `codec_novel_coded`: 35/57 versus 31/57 for magnitude_norm
(+7.0pp; Wilson 95% CI for codec accuracy `[0.484, 0.729]`). The paired test is
still inconclusive: codec fixes five magnitude-wrong rows and breaks one
magnitude-correct row, exact McNemar `p=0.2188`. The "free lunch" interpretation
from N=10 (0.800 = dense) does not replicate at N=57, but the operating-point
ordering is useful enough to promote as a bounded Track B candidate.

Timing caveat: model-side E2E for `codec_novel_coded` is 33.3 s/item versus
34.4 s/item for magnitude_norm, but this excludes the current separate PyAV
metadata extraction path. Counting that repo-local extraction overhead gives
52.1 s/item, so this is not a net wall-clock win until metadata is decoder-integrated
or precomputed.

### Cell 2: kr=0.5 / layer=8 / N=57

| arm | acc | gap vs magnitude_norm |
|---|---|---|
| dense | 0.684 | — |
| **codec_residual** | **0.544** | **+0.0pp** (exact tie) |
| magnitude_norm | 0.544 | — |
| codec_motion | 0.421 | -12.3pp |
| codec_novel_coded | 0.404 | -14.0pp |

**codec_residual at deep prune layer exactly ties magnitude_norm at the broader N.**
Both land 31/57 = 0.544, with balanced paired discordants (6 fixes / 6 breaks,
McNemar `p=1.0`). The N=10 layer sweep suggested a monotonic residual-with-depth
curve; the N=57 promotion supports the layer-8 endpoint tie, not the full curve.

## OV-6 bottom line

**Codec planning is a bounded Track B candidate at specific operating points on
Qwen2.5-VL-7B-4bit / VideoMME short / 8 frames.**

The strongest claim, confirmed at N=57:

1. At kr=0.7 / layer=2 / N=57, `codec_novel_coded` is the best tested sparse arm
   by point estimate: 0.614 versus 0.544 for magnitude_norm and 0.684 for dense.
   All three codec sources exceed magnitude_norm by point estimate, but paired
   tests remain inconclusive. This is the concrete deployment hook: decoder-native
   H.264 metadata is a plausible sparse-vision ranking signal, but the current
   PyAV side path costs about 19 s/item and must be precomputed or integrated into
   the decoder before this becomes an end-to-end wall-clock win.

2. At kr=0.5 / layer=8 / N=57, **codec_residual exactly ties magnitude_norm**
   (both at 0.544), supporting the promoted layer-8 endpoint from the N=10 sweep
   but not independently confirming the full monotonic-with-depth curve.

The kr=0.5 / layer=2 smoke claim "codec doesn't transfer to Track B" was
operating-point-specific. The fuller picture:

- At aggressive pruning (kr=0.5 / layer=2), magnitude_norm is not a robust baseline:
  uniform_random, codec_motion, and codec_novel_coded all exceed it by point
  estimate at N=57, but none earns a paired significance gate.
- At kr=0.7 all three codec arms exceed magnitude_norm by point estimate;
  codec_novel_coded by 7pp.
- At deep prune layer (l=8) codec_residual climbs to tie magnitude_norm.
- The right codec source is operating-point-dependent: novel_coded works at mild
  prune, residual works at deep layer, motion is consistently the worst codec
  arm.

The N=57 replication says the magnitude_norm ranking from the existing 1.51V
framing also depends on the operating point: at kr=0.5 / layer=2 uniform_random
beats magnitude_norm by point estimate, while at kr=0.7 / layer=2 and kr=0.5 /
layer=8 magnitude remains a useful reference. Multi-seed random is required
before turning the random result into a paper claim.

Mechanism: codec metadata reports pixel-space novelty — *which regions changed* —
not *which regions carry the answer*. The vision tower has already abstracted away
from raw pixels by layer 2; whether codec signal aligns with model-internal
importance depends on prune depth and keep-rate. Track A wins were about
preserving the answer when reusing stable state. Track B wins require importance
information the codec sometimes carries (residual at deep layer, novel_coded at
mild prune) and sometimes does not.

The frozen-backend boundary identified here motivates a trained sparse-token
interface: this is the gap OneVision-Encoder's training-time contribution targets
and VLMaxxing's runtime-only framing intentionally leaves open.

## OV-3 Bottom Line

The final OV-3 result is a bounded positive Track A signal, not an end-to-end
systems result.

At 8 frames on 57 VideoMME-short items, every codec source beats both pixel
`max_abs` and dense by point estimate at the same approximate active-refresh budget.
The per-source McNemar tests are inconclusive, but all discordant correctness pairs
favor codec over pixel:

| source | dense | pixel | codec | codec - pixel | codec->dense | codec->pixel | McNemar fixes/breaks | p |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| novel_coded | 38/57 = 0.667 | 37/57 = 0.649 | 40/57 = 0.702 | +3/57 | 55/57 | 54/57 | 3 / 0 | 0.250 |
| motion | 38/57 = 0.667 | 37/57 = 0.649 | 39/57 = 0.684 | +2/57 | 54/57 | 55/57 | 2 / 0 | 0.500 |
| residual | 38/57 = 0.667 | 37/57 = 0.649 | 39/57 = 0.684 | +2/57 | 56/57 | 55/57 | 2 / 0 | 0.500 |
| fused | 38/57 = 0.667 | 37/57 = 0.649 | 39/57 = 0.684 | +2/57 | 54/57 | 55/57 | 2 / 0 | 0.500 |

Wilson 95% CIs on codec accuracy are wide: novel_coded `[0.573, 0.805]`, the other
three sources `[0.555, 0.790]`. This is not enough to claim codec beats pixel with
per-cell statistical significance. It is enough to reopen continuous H.264 spatial
scoring as a bounded Track A hypothesis because four independently computed codec
sources all move in the same direction and none breaks a pixel-correct row.

## Claims We Can Make

`reproduced here`: At N=57, VideoMME short, Qwen2.5-VL-7B-4bit, 8 frames, codec
Track A saliency has positive point estimates over pixel `max_abs` at matched budget.
The best source is `novel_coded` (`intra | cbf`): 0.702 codec accuracy versus 0.649
pixel and 0.667 dense.

`reproduced here`: Codec-to-dense agreement is high but not perfect: 54/57 to 56/57
depending on source. The Wilson 95% lower bound is 0.856 for motion/fused, 0.881 for
novel_coded, and 0.907 for residual.

`reproduced here`: Dense is not a perfectly stable oracle on this local stack. Across
two driver-session overlaps, dense flipped 1/20 answers; pixel and codec did not flip
in those same overlaps. Treat this as a measured caveat, not a broad determinism
claim.

`reproduced here`: Frame-count transfer is bounded. At frame_count=16 on the N=20
manifest, all four codec sources collapse to the pixel answer set: codec=0.750,
pixel=0.750, dense=0.700, codec->pixel=20/20, codec->dense=19/20. The frame=8 codec
advantage over pixel does not automatically generalize to frame=16.

`reproduced here`: The OneVision-style fused score is not the preferred frozen-backend
planner. The earlier N=20 "fused fails" conclusion was too strong because that manifest
did not contain the later N=57 fused-rescue rows. Separately, frame=16 is an operating
point where fused and all other codec sources collapse to the pixel answer set.

## What We Should Not Claim

- No E2E speedup from OV-3. This is Track A semantic substitution, not measured work
  skipped in the vision tower.
- No "10x less vision work" claim yet. The active-refresh budget is around 10%, but
  actual wall-clock savings require OV-6 Track B sparse execution.
- No upstream OneVision reproduction. We reproduced the algorithmic surface and local
  codec-source ablations, not their trained-encoder accuracy claims or cv_reader
  residual extractor.
- No statistically significant codec-over-pixel superiority per source. The point
  estimates favor codec, but McNemar p-values are 0.25 to 0.50 at N=57.
- No generalization beyond VideoMME short / Qwen / 8 frames until TOMATO, threshold,
  and frame-budget tests land.

## Paper Narrative

Recommended wording:

> OneVision-Encoder is the closest trained codec-aligned counterpart to VLMaxxing.
> It validates codec structure as a representation-learning prior. We tested the
> analogous frozen-runtime question: can codec-derived H.264 metadata act as a
> refresh oracle for VLMaxxing without retraining? On VideoMME short at 8 frames,
> four codec score sources produce positive point estimates over pixel `max_abs` at
> matched budget, while frame=16 shows the operating window is bounded.

This should be framed as a diagnostic Track A result and a motivation for Track B,
not as a new headline speedup.

The decision log should change from `continuous H.264 spatial scoring as saliency
oracle = deprioritized` to `bounded active hypothesis`. The scope is narrow:
VideoMME short, Qwen2.5-VL-7B-4bit, frame=8, matched-budget Track A.

## Industry Framing

Use a sober version:

> H.264 macroblock metadata already computed by video decoders is a plausible refresh
> signal for frozen VLM reuse. In local Track A tests on 57 short VideoMME items, it
> improved point-estimate accuracy over pixel difference at the same active-refresh
> budget without retraining. In Track B, the same metadata produces a bounded
> sparse-vision candidate: `codec_novel_coded` is the best tested arm at
> kr=0.7/layer=2 by point estimate, but the paired test is inconclusive and
> current PyAV extraction erases model-side wall-clock savings.

The results are the story: codec metadata helps as a refresh oracle in Track A,
is a bounded ranking candidate in Track B, and composes with C-PERSIST only as
setup-inclusive session accounting unless a live combined protocol is run. The
denominator discipline keeps those results honest; it is not the headline by
itself.

Avoid stronger language:

- Do not say "free" without qualifying that our PyAV path re-decodes and costs about
  19 seconds/item median on M3.
- Do not say "codec significantly beats magnitude_norm" for OV-6; the best N=57
  Track B cell is +4/57 with McNemar `p=0.2188`.
- Do not multiply OneVision patch reduction by C-PERSIST follow-up speedups.

## Extraction Cost

`reproduced here`: H.264 metadata extraction via the current PyAV helper is not free.
Across the N=57 audit, median extraction time is about 19.4 seconds/item, p95 about
28.1 seconds/item. This is a repo-local implementation cost from separate metadata
extraction and decoding. A decoder-integrated implementation could surface the same
signals more cheaply, but that is a systems hypothesis until measured.

## Next Experiments

1. **Gemma OV-6 codec-grid cross-family check**
   Hypothesis: if codec-grid sparse vision is model-family robust, Gemma should
   preserve paired sparse-vs-dense fidelity at the same operating-point family.
   The CPU wiring is now present: Gemma accepts external codec grids on the
   768-canvas / 48x48 pre-pool patch grid, pads scores to the local encoder
   length, excludes padded positions from Top-K, and has placeholder-count and
   score-shape guards. The next scientific step is the N=10 GPU smoke via
   `scripts/run_ov6_gemma_codec_smoke.sh`.

2. **OV-8 C-PERSIST composition after OV-6**
   Artifact-level accounting is now available at
   `research/experiments/2026/artifacts/onevision_cpersist_session/accounting.json`.
   It uses two denominators: model-side first-query E2E excluding extraction, and
   conservative first-query E2E including current PyAV extraction. The accounting
   now records 12/57 first-query choice/correctness drift versus dense, so treat it
   as accounting only; a fresh model-backed session run needs either a fidelity-clean
   first-query cell or an explicit preregistered accuracy/speed trade-off.

3. **TOMATO motion replication**
   Tests whether the codec signal survives outside VideoMME short.

4. **Threshold sensitivity at frame=8**
   Tests whether the N=57 signal is an operating-point artifact of share-matched
   calibration.

5. **Dense determinism multi-seed**
   Useful but secondary. It tightens the dense instability caveat; it does not replace
   Track B.

## Artifact Pointers

- N=57 comparison:
  `research/experiments/2026/artifacts/phase1_29_onevision_n57/comparison.json`
- N=57 statistical audit:
  `research/experiments/2026/artifacts/phase1_29_onevision_n57/statistical_audit.json`
- Frame=16 boundary:
  `research/experiments/2026/artifacts/phase1_29_onevision_dev_n20_short_f16/comparison.json`
- OV-1 visual artifacts:
  `research/experiments/2026/artifacts/onevision_vlmaxxing_visuals/`
  and `research/experiments/2026/artifacts/onevision_vlmaxxing_explainer_videos/`
