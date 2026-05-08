# OneVision-Encoder Research Note

Date: 2026-05-08

This note records primary-source research for using OneVision-Encoder ideas in
the VLMaxxing paper. It is not manuscript prose.

## Status Labels

- `imported result`: claims from OneVision-Encoder's public paper, project
  page, or repository.
- `reproduced here`: claims backed by code/tests/artifacts in this repository.
- `hypothesis`: proposed VLMaxxing integration that still needs experiments.

## Primary Sources

- OneVision project page:
  <https://www.lmms-lab.com/onevision-encoder/index.html>
- OneVision arXiv v3, submitted 2026-02-09 and revised 2026-02-26:
  <https://arxiv.org/abs/2602.08683>
- OneVision public repository:
  <https://github.com/EvolvingLMMs-Lab/OneVision-Encoder>
- OneVision README codec-input notes and reproduction commands:
  <https://raw.githubusercontent.com/EvolvingLMMs-Lab/OneVision-Encoder/main/README.md>
- OneVision preprocessing surface:
  <https://raw.githubusercontent.com/EvolvingLMMs-Lab/OneVision-Encoder/main/llava_next/Compressed_Video_Reader/tool/stage1.py>
  and
  <https://raw.githubusercontent.com/EvolvingLMMs-Lab/OneVision-Encoder/main/llava_next/Compressed_Video_Reader/tool/stage2.py>
- H.264/AVC overview:
  <https://www.microsoft.com/en-us/research/publication/overview-of-the-h-264-avc-video-coding-standard/>
- HEVC overview:
  <https://ieee-cas.org/media/overview-high-efficiency-video-coding-hevc-standard>
- Current cloud-price references for compute estimates:
  <https://lambda.ai/pricing> and
  <https://aws.amazon.com/ec2/capacityblocks/pricing/>

## Determination

`imported result`: OneVision-Encoder is a trained codec-aligned vision encoder.
It uses codec patchification, shared 3D RoPE for irregular THW token positions,
and large-scale cluster discrimination. The public page says it focuses on
3.1%-25% of patches, reports 75.0%-96.9% patch reduction relative to 64 dense
frames with 16,384 patches, and reports aggregate benchmark gains when used as
an LMM vision backbone.

`hypothesis`: The best paper fit is not "OneVision makes VLMaxxing faster" as a
single multiplied number. The useful scientific program is:

1. Reproduce OneVision-style codec patch allocation cleanly.
2. Test whether that allocation is a better freshness/uncertainty signal than
   the current pixel-diff and codec-score baselines.
3. If it helps, feed it into Track A planner substitution and Track B sparse
   vision separately.
4. Report C-PERSIST follow-up reuse as its own denominator.

This keeps the current VLMaxxing identity intact: training-free
anti-recomputation around frozen VLMs. OneVision is the strongest trained
codec-aligned counterpart and the best source of algorithmic ideas for a future
model-native sparse/update interface.

## Clean-Room Reproduction Target

`imported result`: The upstream stage-1 preprocessing contract is compact and
clear enough to reproduce without copying code:

- resize the longer side to 576;
- center-pad to 576 x 576;
- uniformly sample 64 frames on the original timeline;
- compute fused motion-vector and residual-energy scores per sampled frame;
- map scores to the square canvas;
- patchify with 16-pixel patches in the upstream preprocessing path; the
  resulting grid depends on the square size and patch size;
- globally rank valid THW patches;
- optionally force the first frame to remain fully visible;
- write `visidx_thw.npy`, `frame_ids.npy`, and metadata.

`imported result`: Stage 2 packs selected patches or mosaics and can emit
`positions_thw.npy`, which is the model-facing position metadata. The public
README also shows direct model calls with explicit `patch_positions`.
The patch sizes are stage-specific: upstream Stage 1 selects 16-pixel source
patches on a 576-square preprocessing canvas, while the released encoder model
card reports a 14-pixel ViT patch size for the Stage 2 encoder. Do not feed a
Stage 1 16-pixel selection grid directly into the encoder without the Stage 2
packing/position conversion.

`imported result`: In the released preprocessing code, Stage 1 depends on
`cv_reader` and computes residual energy from decoded residual frames as luma
deviation from the neutral residual value. That is not the same signal as this
repo's `H264MetadataExtractor`, which uses PyAV motion vectors plus a
motion-compensated reconstructed-Y residual proxy. Therefore, upstream parity
must treat residual extraction as a controlled variance source unless we use
`cv_reader` or an equivalent codec-internal residual extractor.

`reproduced here`: This branch adds a CPU-only clean-room primitive in
`src/codec_through/codec/onevision_patchification.py` that implements:

- percentile-normalized motion/residual fusion;
- fixed-budget global Top-K patch selection;
- mandatory full-frame anchors;
- deterministic THW tie-breaking;
- visible-index export;
- temporal coverage and spatial-bias diagnostics.

Unit tests cover anchor/budget invariants, toy motion localization, stable
tie-breaking, score fusion modes and errors, temporal coverage, runner wiring,
cache metadata guards, and center/boundary diagnostics.

## What We Can Reproduce Locally

`reproduced here`: On the M3 MacBook Air, we can reproduce algorithmic
patchification, score fusion, deterministic visible indices, fail-closed
real-video visualization plumbing, preflight checks, and scheduler artifacts
without model inference.

`hypothesis`: With benchmark assets present, the M3 can also run CPU codec
metadata allocation analysis over the three established visualization clips and
small manifest subsets. This should be hours, not days, for visualization and
small allocation studies. It is not a full OneVision reproduction.

`imported result`: OneVision's full benchmark claims are trained representation
claims. The paper's Section 4.1 reports a two-stage pretraining run on 128 A800
GPUs, with large-scale image/video/OCR data. That is not feasible on a 16 GB
M3 Air, and it is not the experiment we need for the current paper.

`imported result`: The public repository also includes a single-node
`ov_encoder_large_stage2_residual_8gpus.sh` training entrypoint. That script is
a released training recipe, not evidence that the paper's full pretraining
claim used only 8 GPUs; the arXiv v3 implementation section states 128 A800
GPUs.

`hypothesis`: A useful external parity run needs one NVIDIA environment, not
paper-scale training. The parity objective is to run upstream preprocessing on
20-50 clips and compare selected THW positions, not to retrain OV-Encoder.

## Compute Tiers

M3 16 GB Air:

- Good for CPU unit tests, schedule generation, preflight checks, and small
  metadata-only allocation audits. Developer-only synthetic smoke output may be
  used to test drawing code, but it is not scientific evidence and is not a
  fallback for OV-1.
- Not good for broad Qwen/Gemma sweeps while other experiments are running.
- Not suitable for upstream OneVision model evaluation or any full training.

M5 128 GB MBP:

- Good for sequential local MLX Track A/Track B experiments with the current
  repo's Qwen/Gemma lanes.
- Good for broad no-concurrent-GPU runs after the M3 algorithmic gates pass.
- Still not suitable for OneVision-scale pretraining.

Single NVIDIA box, A100/H100:

- Useful for upstream preprocessing parity, CUDA dependency compatibility, and
  small OV-Encoder inference probes.
- Science value: separates our implementation bugs from model/backend limits.
- Rough cost: Lambda lists 1x A100 at about $1.99/GPU-hour and 1x H100 PCIe at
  about $3.29/GPU-hour as of the current pricing page.
- Prefer this tier for upstream `cv_reader` / CUDA dependency checks. Apple
  Silicon is not the right target for the official OneVision Docker/CUDA stack.
- Budget 2-4 hours of first-time setup for `cv_reader` and its patched-FFmpeg
  dependency before counting the 3-6 hour parity run.

8-GPU or 16-node NVIDIA:

- Useful only if we decide to train a small cache-aware router/adaptor or do
  material OV-Encoder fine-tuning.
- Full OneVision-scale reproduction is likely tens of thousands of dollars per
  week. AWS capacity-block pricing lists p4d.24xlarge at $11.80/hour for
  8 x A100 and p5.48xlarge at roughly $31.46-$34.61/hour for 8 x H100,
  depending on region. Lambda lists 8 x H100 instances at $3.99/GPU-hour.
- Science value: tests whether a trained sparse-token interface fixes the
  frozen-backend fidelity boundary. It is not needed for the first paper
  decision.

## Comparison With The User-Provided ChatGPT Notes

Agreements:

- OneVision and VLMaxxing are close at the philosophy level and mostly
  orthogonal at the technical layer.
- OneVision is trained encoder work; VLMaxxing is runtime/cache policy around
  frozen VLMs.
- OneVision patch reductions are not timed end-to-end speedups.
- Combining cold-ingest sparsity with after-ingest reuse requires denominator
  discipline. The wins must not be multiplied.
- The strongest near-term adoption is the codec patch scorer and visible THW
  metadata, not a full model replacement.

Corrections and caution:

- Treat "semantically rich" codec patches as an `imported result`, not a local
  fact. In this repo, motion/residual scores are freshness/uncertainty signals
  until paired task tests show semantic value.
- A medium-depth "use OneVision's selector without replacing the VLM" can be a
  valid experiment, but it is Track A until the backend actually skips timed
  vision work.
- The current repo already has negative evidence for naive codec-native labels.
  We should build on continuous score calibration, not reintroduce hard MAX/OR
  H.264 labels as a default planner.

## Review Validation Update

External review in this branch raised several concrete issues. Verdicts:

- `FALSE POSITIVE`: the note did not claim `positions_thw.npy` is a Stage 1
  output. It already says Stage 1 writes `visidx_thw.npy`/`frame_ids.npy`/meta
  and Stage 2 can emit `positions_thw.npy`. This note now states that more
  explicitly.
- `FALSE POSITIVE`: the 128 A800 pretraining claim is primary-source backed by
  arXiv v3 Section 4.1. The public 8-GPU script is a recipe, not the full
  paper-training disclosure.
- `VALID`: residual-signal parity is a real caveat. Upstream Stage 1 uses
  `cv_reader` residual frames; this repo currently uses a reconstructed-Y
  motion-compensated residual proxy. Parity gates now separate identical-score
  allocator parity from independent-residual correlation.
- `VALID`: the initial implementation was a primitive, not a runnable Track A
  or Track B lane. A macroblock-to-token fused projection adapter now exists in
  `codec_through.codec.continuous_score`, and the Phase 1.29 probe now exposes
  motion-only, residual-only, fused-score, fusion-weight, and max-age controls
  with score-source metadata in artifacts.
- `VALID`: the prior decision-log entry for "Continuous H.264 spatial scoring
  as saliency oracle" must be explicitly reopened before promotion. OneVision
  is new external evidence for a targeted reread; it is not by itself local
  proof that codec scores are semantic saliency.

## OV Model Local Feasibility

`imported result`: The Hugging Face collection currently lists
`lmms-lab-encoder/onevision-encoder-large` and
`lmms-lab-encoder/onevision-encoder-large-lang`, both 0.3B-parameter vision
encoders. The model card reports BF16 safetensors around 631 MB for the base
large encoder, patch size 14, 24 ViT layers, hidden size 1024, 16 heads, and
3D RoPE.

`hypothesis`: The model is likely small enough to run encoder-only experiments
on the M3/M5 in memory, especially at image scale or sparse 2048-token video
budgets. It is not a third local VLM equivalent to Qwen/Gemma unless we also
wire an LMM head or run their LLaVA-NeXT probe stack.

Porting options:

- PyTorch/MPS smoke: probably the fastest local feasibility check, but the
  public examples target CUDA and `flash_attention_2`; we would need to force
  eager attention or patch the config. This should be tried only when the
  machine is free.
- MLX port: feasible for encoder-only science because the architecture is a
  straightforward ViT with Conv2d patch embedding, QKV attention, MLP, LayerNorm
  or RMSNorm, and explicit 3D RoPE. It is nontrivial because we must convert
  safetensors weights, implement patch-position RoPE exactly, and validate
  PyTorch-vs-MLX output parity on small inputs. Plan for about one week, not a
  two-day patch, if the result needs to support paper claims. It is useful if
  we want many local encoder probes without PyTorch/MPS overhead.
- Full LMM use: defer. The released encoder can support representation and
  feature-drift experiments locally, but answer-drift comparisons require a
  language-model integration path and should not be mixed with Qwen/Gemma VLM
  claims until that stack is reproduced.

## References And Ideas To Adopt

Adopt now:

- HEVC/H.264 language for I/P structure, motion vectors, residuals, and GOPs,
  grounded in standards/overview references.
- Visible THW indices as first-class metadata for every sparse patch.
- Global clip-level budget allocation as a separate ablation from per-frame
  keep rates.
- Spatial-bias audits: center share, boundary share, entropy, and edge/OCR
  starvation checks.
- Four-stage visualization: dense video, uniform sampling, score/freshness map,
  sparse selected patches.
- Denominator-separated comparison tables for imported OneVision results,
  reproduced VLMaxxing baselines, and OneVision+VLMaxxing hypotheses. The
  branch now emits a JSON/CSV/Markdown plan table under
  `research/experiments/2026/artifacts/onevision_vlmaxxing_plan/`.

Adopt only as future trained work:

- 3D RoPE interface for irregular sparse token geometry.
- Cluster-discrimination or cache-aware labels trained from dense-teacher and
  paired-drift traces.
- Codec-conditioned token types: anchor, P-frame selected, forced refresh,
  age-expired, reused.

Do not adopt without new evidence:

- A claim that codec-selected patches are task-salient for our frozen models.
- Any end-to-end speed claim from patch count alone.
- Full OneVision retraining as a prerequisite for this paper.

## Paper Impact Hypotheses

`hypothesis`: If Track A improves but Track B does not, the paper should cite
OneVision as closest trained codec-aligned related work and add a diagnostic
section showing codec allocation improves semantic substitution but does not
yet deliver frozen-backend skipped work.

`hypothesis`: If Track B gates pass, the paper can add a new combined result:
OneVision-style allocation improves C-VISION fidelity/timing at matched
keep-rate, while C-PERSIST remains the follow-up reuse mechanism.

`hypothesis`: If both fail, the paper still gets a stronger boundary claim:
trained codec-aligned encoders are complementary because frozen dense vision
towers do not reliably accept codec-sparse evidence without retraining.

In all cases, manuscript edits should wait for the editor-feedback phase in the
experiment plan. This branch intentionally does not modify paper prose.
