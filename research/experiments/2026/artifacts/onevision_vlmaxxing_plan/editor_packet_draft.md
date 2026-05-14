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

The codec arms have the lowest model-side end-to-end times among the pruners
(codec_motion 31.1 s/item, codec_novel_coded 31.1 s/item, vs dense 38.7 s/item),
but they bring 17-19 s/item of upstream PyAV metadata extraction overhead that the
magnitude / random arms do not pay. Net: codec is not a wall-clock win at this
configuration after counting extraction.

## OV-6 keep-rate sweep at layer=2 (N=10)

| source | kr=0.30 | kr=0.50 | kr=0.70 | kr=0.90 |
|---|---|---|---|---|
| magnitude_norm | 0.600 | 0.600 | **0.800** | 0.600 |
| codec_novel_coded | 0.500 | 0.400 | **0.800** | 0.600 |
| codec_motion | 0.500 | 0.400 | 0.700 | 0.600 |
| codec_residual | 0.500 | 0.500 | **0.800** | 0.700 |

**The accuracy curve is non-monotonic.** kr=0.7 is the sweet spot: at the kr=0.7
operating point, magnitude_norm, codec_novel_coded, and codec_residual all reach
0.800 (= N=10 dense). At kr=0.5 and kr=0.9 every arm regresses. Treat this as an
operating-point observation, not a mechanism proof: the promoted N=57 cells below
show that the kr=0.7 window survives better than the kr=0.5/layer=2 smoke, but the
curve remains model-, layer-, and benchmark-conditioned.

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
layer=8 magnitude remains a useful reference. The follow-up sweep below confirms
the kr=0.5/layer=2 random-over-magnitude inversion across four seeds.

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

At 8 frames on 57 VideoMME-short items, every codec source beats pixel
`max_abs` by point estimate at the same approximate active-refresh budget, and
scores at or above the local dense run on this slice. Dense itself showed
driver-to-driver instability in the overlap audit, so do not phrase this as
codec being inherently more accurate than dense.
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
- No broad generalization beyond the tested operating points. The follow-up sweep
  adds TOMATO and pooled-calibration evidence, but TOMATO is a boundary result and
  frame=16 remains a codec-to-pixel collapse.

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

## Remaining Experiments After This Packet

The four preregistered controls have now run; see the follow-up sweep below.
The remaining useful work is narrower and should run in this order. The
M3-versus-M5 split is doctrine: M3 is for implementation, extraction-sidecar
work, analysis, and small N=10 engineering smokes; M5 is for preregistered
confirmation runs where RAM, thermal stability, and runtime matter. Every new
run must have a gate and a falsifier; no open-ended sweeps on either machine.

1. **M3 sidecar equivalence gates** (cheap, unblocking)
   Build precomputed H.264 score sidecars and compare live-PyAV Track B arms
   against sidecar-loaded arms on small Qwen and Gemma slices. Acceptance is
   geometry / frame-budget specific: Qwen 8f, Qwen 16f, and Gemma 8f each
   require zero choice drift, zero correctness drift, zero kept-group drift,
   current manifest / commit / projection-version provenance, and sidecar load
   below one second / item *and* faster than live extraction. Scripts:
   `scripts/run_ov6_sidecar_equivalence.sh` (Qwen 8f),
   `OV6S_FRAME_COUNT=16 scripts/run_ov6_sidecar_equivalence.sh` (Qwen 16f),
   `scripts/run_ov6_gemma_sidecar_equivalence.sh` (Gemma 8f). Each gate
   produces `sidecar_equivalence.json` and is validated by
   `scripts/validate_ov6_sidecar_equivalence_gate.py`. The M5 launchers below
   refuse to run unless the matching gate has `gate_pass: true`.

2. **M3 TOMATO kr=0.9 / layer=2 / balanced N=9 boundary diagnostic**
   Disambiguate the Phase-3 collapse with the right direction of intervention:
   `kr=0.9` is a milder prune than the previous kr~0.69 operating point. Use a
   balanced 3/3/3 TOMATO motion slice so the smoke is not just "direction"
   items. Script: `scripts/run_ov6_tomato_kr090_boundary_smoke.sh`. Gate: best
   sparse arm is within one item of dense and above the prior sparse-floor band
   (>0.22 on N=9). If dense remains weak or all sparse arms stay at floor, do
   not spend M5 time on TOMATO in this branch. The older kr=0.5 script is only
   an aggressive-prune negative control.

3. **M5 confirmation runs, gated on the M3 equivalence artifacts**
   - `scripts/run_ov6_m5_qwen_parity.sh` -- Qwen kr=0.7 / layer=2 / N=57 with
     sidecar-loaded codec scores. Hypothesis: the M3 codec_novel_coded
     point-estimate ordering is hardware-stable when extraction is moved out
     of model timing.
   - `scripts/run_ov6_m5_gemma_n57_confirmation.sh` -- Gemma kr=0.7 / layer=2
     / N=57. Hypothesis: the N=10 Gemma codec-grid smoke was not a wiring
     artifact; codec_novel_coded remains competitive with magnitude_norm at
     the broader N.
   - `scripts/run_ov6_m5_qwen_frame16_boundary.sh` -- Qwen kr=0.7 / layer=2
     at frame=16 / N=57. Hypothesis: the kr=0.7 / layer=2 codec-grid window
     does not survive at 16 frames, matching the OV-3 Track A frame=16
     boundary.
   - `scripts/run_ov6_m5_gemma_kr05_inversion.sh` -- Gemma kr=0.5 / layer=2
     / N=57 random-vs-magnitude multi-seed (seeds {1, 7, 42, 100}).
     Hypothesis: the Phase-1 Qwen uniform_random > magnitude_norm inversion
     reproduces cross-family on Gemma at the same operating cell. This run
     does not use codec arms; the M3 sidecar gate is not required.
     Preregistered gate: >=3/4 seeds satisfy random >= magnitude by point
     estimate; falsifier: any seed where magnitude beats random by >=3 items,
     or <=1/4 seeds satisfy the gate. Analysis path:
     `scripts/analyze_ov6_qwen_random_multiseed.py --root <out_dir>
     --label Gemma --min-pass-seeds 3`.

4. **OV-8 composition policy** (still blocked)
   Artifact-level accounting exists, but first-query correctness drift is
   12/57 for the Qwen codec_novel_coded kr=0.7/layer=2 cell. A live
   C-PERSIST composition run needs either a fidelity-clean first-query cell
   or an explicit preregistered accuracy/speed trade-off. The OV-8 validator
   keeps live composition status pinned to "artifact-level accounting only".

5. **Dense determinism multi-seed**
   Useful but secondary. It tightens the dense instability caveat; it does
   not replace Track B or the codec extraction question.

6. **Open: Track A (OV-3) pooled calibration on Gemma** (not wired)
   Phase 4 established calibration-free refresh oracle on Qwen with Wilson
   lower 0.91 on codec->dense agreement. The OV-3 runner
   (`scripts/run_phase1_29_planner_accuracy_probe.py`) is hard-coupled to
   Qwen 2.5-VL geometry ("Qwen grid count mismatch" check, Qwen-only
   prefill/reuse plumbing). If the refresh oracle is truly
   vision-tower-family-agnostic, a Gemma OV-3 confirmation would widen the
   claim from "Qwen-specific calibration oracle" to "family-agnostic
   refresh oracle". This is a real implementation lift (Gemma SigLIP has
   different active-box semantics), not a few-hour wire-up. Recommended
   only after the M5 OV-6 confirmations land; otherwise it expands
   surface area without confirmed payoff. The query-aware synergy note
   already records that the sidecar contract makes this kind of
   cross-family experiment cheaper if/when it is undertaken.

Verification status of this packet: direct no-UV checks pass at the current
HEAD (`ruff format --check .`, `ruff check .`, `mypy src tests`,
`pytest` 327 passed, and artifact integrity). MLX-using tests now hard-fail
on Darwin instead of silently skipping (`599e303`); a mypy variance bug in
the sidecar test file was fixed in `a30aba5`.

## Follow-up Sweep (Preregistered, 4 Phases)

A 14-hour back-to-back MLX sweep ran the four preregistered controls on M3.
All four phases completed; their preregistered gates were met. Confidence-bound
summaries below are post-run robustness checks unless explicitly named in the
gate.

### Phase 1: Qwen random multi-seed (OV-6 robustness)

Setup: Qwen 2.5-VL-7B-4bit, VideoMME-short N=57, kr=0.5 / layer=2, frame=8.
Tests whether the OV-6 "uniform_random beats magnitude_norm" inversion is
seed-stable. Magnitude baseline: 24/57 = 0.421.

| seed | random acc | gap vs mag | paired b/c | McNemar exact p |
|---:|---:|---:|---:|---:|
| 1   | 0.544 (31/57) | +12.3 pp | 10/3 | 0.0923 |
| 7   | 0.509 (29/57) | +8.8 pp  | 8/3  | 0.2266 |
| 42  | 0.491 (28/57) | +7.0 pp  | 8/4  | 0.3877 |
| 100 | 0.509 (29/57) | +8.8 pp  | 9/4  | 0.2668 |
| mean| 0.513         | +9.2 pp  | -    | -      |

Preregistered gate (all tested seeds random >= magnitude): **4/4 satisfied**, no
falsifying seed. The inversion is seed-stable.

### Phase 2: Gemma cross-family codec-grid smoke

Setup: Gemma 4 E4B + SigLIP, VideoMME-short N=10, kr=0.70 / layer=2,
pre-pool 48x48 patch grid (encoder length 2520 with [-1,-1] padding
excluded from pruning). Paired vs magnitude_norm.

| arm | acc | kr | paired b/c |
|---|---:|---:|---:|
| dense              | 0.500 | 1.00 | -   |
| magnitude_norm     | 0.400 | 0.70 | -   |
| uniform_random     | 0.300 | 0.70 | 0/1 |
| codec_novel_coded  | 0.600 | 0.70 | 3/1 |
| codec_motion       | 0.600 | 0.70 | 3/1 |
| codec_residual     | 0.500 | 0.70 | 2/1 |

Preregistered smoke gate (codec_novel_coded >= magnitude on Gemma):
**satisfied**. All three codec sources at least match magnitude by point
estimate; novel_coded and motion both add 3 paired wins for 1 loss.
Cross-family codec-grid wiring works. N=10 yields no statistical claim;
contribution is qualitative transfer.

### Phase 3: TOMATO motion replication (boundary)

Setup: Qwen 2.5-VL-7B-4bit, TOMATO motion-dev v2 N=30, kr=0.70 / layer=2.
Cross-benchmark stress test on motion-heavy items where codec scores
should have the best chance to differentiate.

| arm | acc | vs mag b/c | vs dense b/c | E2E ms |
|---|---:|---:|---:|---:|
| dense              | 0.267 | 5/1 | -   | 46000 |
| magnitude_norm     | 0.133 | -   | 1/5 | 34676 |
| uniform_random     | 0.133 | 0/0 | 1/5 | 39991 |
| codec_novel_coded  | 0.167 | 2/1 | 1/4 | 45877 |
| codec_motion       | 0.167 | 2/1 | 2/5 | 40095 |
| codec_residual     | 0.133 | 0/0 | 1/5 | 39590 |

Magnitude prune halves dense accuracy (0.267 -> 0.133) on TOMATO motion at
kr=0.69. Codec_novel_coded and codec_motion edge magnitude by +1 item but
remain at chance floor. Honest boundary: codec scores do not rescue motion
at this prune rate / frame budget. Wall-clock with codec extract overhead
nearly cancels prune savings on novel_coded (45.9s vs dense 46.0s); the
codec story requires session-level amortization, not per-query savings.

### Phase 4: OV-3 pooled calibration sensitivity (Track A)

Setup: Qwen 2.5-VL-7B-4bit, VideoMME-short N=57, **pooled** (not per-item)
calibration thresholds. Tests whether the refresh oracle still tracks dense
without bespoke per-item threshold fitting.

| source | codec acc | dense acc | codec->dense | reuse_ratio |
|---|---:|---:|---:|---:|
| novel_coded | 0.6842 | 0.6667 | 0.9825 | 0.1062 |
| motion      | 0.6842 | 0.6667 | 0.9825 | 0.1076 |
| residual    | 0.6842 | 0.6667 | 0.9825 | 0.1065 |
| fused       | 0.6667 | 0.6667 | 0.9649 | 0.1093 |

Wilson 95% lower bound on codec_dense_agreement: 0.91 (single sources),
0.88 (fused). The preregistered gate was parse-clean execution plus
nonnegative codec-minus-pixel behavior under pooled calibration; that gate
passes. The Wilson lower bound is a post-run robustness summary. Three single
sources are bit-identical on accuracy and agreement -- pooled thresholds
collapse score-source choice. Use one simple source for future systems tests.
Fused trails by one item (55/57 vs 56/57) and is not preferred.

## Bottom Line After the Follow-up Sweep

The four-phase sweep tightens two claims and bounds a third:

1. **Track B OV-6 magnitude-prior failure is seed-stable at one Qwen operating
   point.** Random beats magnitude on 4/4 seeds at kr=0.5/layer=2 on Qwen, and
   codec_novel_coded beats magnitude on Gemma at the smoke gate. The "obvious
   heuristic" (magnitude_norm) is not a safe default at this Qwen kr=0.5/layer=2
   cell, and random must remain a required baseline. It remains useful at other
   tested cells.
2. **Track A refresh oracle is calibration-robust.** Pooled thresholds
   give Wilson-lower 0.91 codec->dense agreement, with ~10.6 - 10.9%
   active-frame reuse. On this VideoMME-short/Qwen/8f slice, deployment does not
   need per-item threshold fitting.
3. **Motion-heavy benchmarks at frame=8 / kr=0.69 are headroom-limited.**
   No prune scheme escapes the chance floor; codec scores edge magnitude
   by one item. The codec advantage does not generalize to TOMATO motion
   at this operating point.

## Artifact Pointers

Verification note: the completed OV-6 Track B artifacts were produced before the
Track B runner summaries recorded `git_commit` / `git_dirty` fields. The raw
summary and per-item rows are committed and the audits below validate their
counts and paired item sets. Future Track B and pooled-calibration runners now
record run provenance and refuse stale skip-if-exists reuse.

- N=57 comparison:
  `research/experiments/2026/artifacts/phase1_29_onevision_n57/comparison.json`
- N=57 statistical audit:
  `research/experiments/2026/artifacts/phase1_29_onevision_n57/statistical_audit.json`
- Frame=16 boundary:
  `research/experiments/2026/artifacts/phase1_29_onevision_dev_n20_short_f16/comparison.json`
- OV-1 visual artifacts:
  `research/experiments/2026/artifacts/onevision_vlmaxxing_visuals/`
  and `research/experiments/2026/artifacts/onevision_vlmaxxing_explainer_videos/`
- Phase 1 multi-seed audit:
  `research/experiments/2026/artifacts/phase1_51V_ov6_random_multiseed/random_multiseed_summary.md`
- Phase 2 Gemma smoke:
  `research/experiments/2026/artifacts/phase1_63G_ov6_gemma_codec_smoke/`
- Phase 3 TOMATO motion:
  `research/experiments/2026/artifacts/phase1_51V_ov6_tomato_motion_kr070_l2/`
  and `research/experiments/2026/artifacts/phase1_51V_ov6_tomato_motion_kr070_l2/statistical_audit.md`
- Phase 4 pooled calibration:
  `research/experiments/2026/artifacts/phase1_29_onevision_n57_pooled_calibration/`
