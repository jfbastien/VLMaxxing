# OneVision + VLMaxxing Preregistration

Date: 2026-05-08

## Preregistration

Question: Can OneVision-Encoder's codec patchification ideas improve
VLMaxxing's training-free anti-recomputation story without collapsing Track A,
Track B, and C-PERSIST denominators?

Primary hypothesis:

`hypothesis`: OneVision-style motion/residual Top-K allocation is useful as a
better fresh-evidence planner and visualization primitive. It may improve
Track A semantic substitution immediately. It becomes a Track B systems result
only if a sparse backend actually skips timed vision work and paired fidelity
gates pass.

Null hypothesis:

`hypothesis`: The trained OneVision gains do not transfer to frozen
Qwen/Gemma-style backends through patch allocation alone. If so, the result is
still scientifically useful because it identifies retraining/model-interface
requirements for codec-native sparse video.

Hard constraints:

- Do not run model or GPU-heavy work while the user's current experiments are
  running.
- Execute later model jobs sequentially. No concurrent model jobs.
- Preserve Track A, Track B, and C-PERSIST accounting.
- Label all imported OneVision claims as `imported result` until reproduced.
- Do not modify paper manuscript files until the editor-feedback phase.

## Feedback Validation Update

External review after the first commit changed the preregistration in four
ways.

1. Stage-output attribution:
   `FALSE POSITIVE` against this branch. The research note already placed
   `positions_thw.npy` in Stage 2, not Stage 1. The docs now make this explicit
   so future readers do not conflate Stage 1 visible indices with Stage 2 model
   patch positions.

2. Training scale:
   `FALSE POSITIVE` against this branch. arXiv v3 Section 4.1 states the
   reported full pretraining used 128 A800 GPUs. The public 8-GPU script is a
   runnable training recipe, not the full paper-training disclosure.

3. Residual-signal parity:
   `VALID`. Upstream Stage 1 uses `cv_reader` residual frames and measures luma
   deviation from a neutral residual value. This repo's
   `H264MetadataExtractor` uses PyAV motion vectors plus a reconstructed-Y
   motion-compensated residual proxy. Therefore OV parity must split:

   - allocator parity under identical score planes;
   - motion-only correlation under independent extraction;
   - residual-only correlation under independent extraction;
   - fused-score behavior as an empirical planner, not an exact upstream clone.

4. Existing decision-log:
   `VALID`. The repo has "Continuous H.264 spatial scoring as saliency oracle"
   marked `Deprioritized`, with reopen only if simple routing plateaus and a
   raw-artifact reread shows stronger-than-expected correlation. OneVision is
   new external evidence for a targeted reread, not local proof that codec
   scores are semantic saliency. OV-3 promotion must explicitly satisfy or
   reject that reopen condition.

## Current Local Setup

`reproduced here`: This branch has CPU-only patchification code, macroblock
motion/residual fusion projection, unit tests, fail-closed real-video
visualization plumbing, a CPU-only preflight script, Phase 1.29 score-source
CLI wiring, comparison-table scaffolding, and a generated schedule. No VLM
inference was run for this phase.

Existing visualization windows to reuse when raw videos are present:

- `tomato_0298_00`: `data/benchmarks/tomato/videos/object/0298-00.mp4`,
  0.00-2.00s.
- `videomme_380`: `data/benchmarks/videomme/videos/2Bns2m5Bg4M.mp4`,
  206.39-207.89s.
- `videomme_267`: `data/benchmarks/videomme/videos/Atf_Af1q_5w.mp4`,
  0.00-1.00s.

These are the same three windows used by the existing codec-through overlay
artifacts under
`research/experiments/2026/artifacts/codec_through_video_overlays_exploratory/`.
They are not new OneVision-specific examples and must not be used as tuning
items for OV-3.

## Before Kickoff: Asset Preflight

`reproduced here`: On this checkout, the benchmark source media are required
inputs, and generated overlays or developer synthetic figures are not accepted
as scientific substitutes. Run:

```bash
uv run python scripts/preflight_onevision_vlmaxxing.py --scope ov1
```

The preflight checks exactly which assets are present, what each is used for,
and how to restore it. If the sibling checkout
`/Users/jfb/s/codec-through` is present, it can restore the current-paper
visualization clips and metadata locally; otherwise use the repo fetchers.

Required source clips for OV-1:

- `data/benchmarks/tomato/videos/object/0298-00.mp4`:
  `tomato:rotation:0298-00`, existing high-reuse paper visualization.
- `data/benchmarks/videomme/videos/2Bns2m5Bg4M.mp4`:
  `videomme:medium:380-3`, existing VideoMME visual anchor.
- `data/benchmarks/videomme/videos/Atf_Af1q_5w.mp4`:
  `videomme:short:267-2`, existing lower-reuse boundary visualization.

Fetch/restore commands when local copies are absent:

```bash
uv run python scripts/fetch_benchmarks.py --dataset tomato --mode all --tomato-video-source auto
uv run python scripts/fetch_benchmarks.py --dataset videomme --mode metadata
uv run python scripts/fetch_videomme_subset.py --manifest research/benchmark_manifests/videomme_dev_v1.toml --manifest research/benchmark_manifests/videomme_holdout_v1.toml --cache-dir data/benchmarks/videomme/downloads/hf_cache
```

For OV-3's default dev tranche, run the broader gate and verify that every
video referenced by `research/benchmark_manifests/videomme_dev_v1_short_only.toml`
is present:

```bash
uv run python scripts/preflight_onevision_vlmaxxing.py --scope all
```

## Machine-Readable Schedule

Generate the current schedule with:

```bash
uv run python scripts/plan_onevision_vlmaxxing_experiments.py
```

It writes:

```text
research/experiments/2026/artifacts/onevision_vlmaxxing_plan/experiment_schedule.json
```

The schedule uses two compute flags:

- `uses_local_accelerator`: later Apple MLX/MPS/GPU-style local acceleration
  may be used; do not run these while current benchmarks are active.
- `requires_nvidia`: needs a Linux/NVIDIA/CUDA stack, not Apple Silicon.

## Revised Sequential Plan

### OV-0: Algorithmic Invariants

Track: reproduction-method

Hypothesis: A clean-room allocator can reproduce the visible-index contract
needed for local tests: fused motion/residual scores, fixed global Top-K
budget, full-frame anchors, deterministic THW metadata, and macroblock
score-grid projection.

Run now:

```bash
uv run pytest tests/codec/test_onevision_patchification.py tests/codec/test_continuous_score.py
```

Success gate: tests pass for anchors, budget overflow, stable tie-breaking,
toy score localization, score fusion, zero-weight motion/residual lanes,
temporal coverage, and spatial-bias diagnostics.

Skip rule: If OV-0 fails, skip every downstream OneVision integration.

ETA: under 10 minutes on M3 or M5.

### OV-1: Real-Video Allocation Visualization

Track: visualization-method

Hypothesis: A token-allocation-over-time view will reveal whether the fused
motion/residual score is sane before any model time is spent.

Current implementation:

```bash
uv run python scripts/preflight_onevision_vlmaxxing.py --scope ov1
uv run python scripts/render_onevision_vlmaxxing_visual.py
```

Still needed:

- review `allocation_summary.json`, `score_volumes.npz`,
  `token_allocation.csv`, `selected_patches.jsonl`, and
  `starvation_metrics.csv` for the three clips before model promotion.

Success gate: real-video allocation audits exist for all three existing paper
clips before OV-3 model runs.

Skip rule: If raw videos are absent, fail OV-1 and restore source assets before
continuing. Do not use synthetic figures or generated overlays as substitutes.

ETA: M3 3-6 hours with video extraction; M5 1-3 hours.

### OV-2: Track A Wiring

Track: implementation-wiring

Hypothesis: The safest first runnable integration is a continuous-score adapter
over existing H.264 metadata, not a new hard `BlockStatistic` label.

Already added:

- `project_fused_motion_residual_to_token_grid` in
  `codec_through.codec.continuous_score`;
- tests that zero residual weight matches motion-only and zero motion weight
  matches residual-only;
- lazy-runtime guards and tests for runner error paths, cache metadata
  mismatch, and windowed-item rejection.

Still needed before model inference:

- a same-item regression against current pixel `max_abs` and Phase 1.29 codec
  baselines;
- optional runner integration in `run_benchmark_track_a.py` only after the
  probe path is stable.

Success gate: the adapter reproduces existing Phase 1.29 behavior on small or
cached inputs and all algorithmic invariants pass.

Skip rule: If OV-2 fails, do not start OV-3 model inference.

ETA: implementation complete; under 1 hour for CPU checks and optional cached
input smoke. No model time.

### OV-3: Track A Dev Ablation

Track: Track A semantic substitution

Hypothesis: Continuous motion+residual scoring with per-item calibration beats
pixel `max_abs`, legacy `novel_coded`, and motion-only/residual-only ablations
on paired answer stability at matched fresh budgets.

Use existing baselines:

- current Track A dense/pixel planner baselines;
- Phase 1.29 continuous codec-score pilot and Phase 1.29B replication;
- VideoMME, MVBench, TOMATO manifests already used by the paper.

Ablations:

- pixel `max_abs`;
- legacy `novel_coded` (`intra_flag | cbf`) continuous codec score;
- motion-vector magnitude;
- residual energy from this repo's proxy;
- motion/residual weighted fusion;
- fusion plus bounded staleness;
- global clip-level budget versus per-frame budget.

Metrics:

- paired choice drift;
- paired correctness drift;
- parse/format failures;
- aggregate accuracy only as secondary context;
- fresh-frame/block budget;
- per-duration bucket results;
- decision-log reopen status for continuous H.264 saliency.

Success gate: no increase in parse failures, <= 1% paired-choice drift on
gated dev cells, and strict Pareto improvement over current Track A baselines.

Skip rule: If fused scoring underperforms pixel `max_abs` on the first dev
tranche, skip holdout promotion, external parity, Track B, and combined runtime
claims.

ETA after wiring: M3 24-40 hours sequential; M5 12-24 hours sequential. The
cache key intentionally includes `codec_score_source`, so the ablation grid
pays separate codec-score precompute per score source unless we later split
source-independent pixel/active-box caches from source-dependent codec-score
caches.

### OV-4: External Parity Oracle

Track: external-parity

Hypothesis: Upstream parity is most valuable after OV-3 dev passes. If the
planner signal is not promising, spending time on CUDA/cv_reader parity is
operational noise.

Required compute: Linux/NVIDIA environment or Lambda-style 1xH100/A100. M5 is
not recommended for the official stack because the public instructions target
CUDA, Docker `--gpus all`, CUDA PyTorch, and flash-attention-style components.
Also budget 2-4 hours for first-time `cv_reader` plus patched-FFmpeg setup
before counting the parity run itself.

Metrics:

- Jaccard overlap for selected THW positions under identical score planes;
- motion-only correlation under independent extraction;
- residual-only correlation under independent extraction;
- fused-score allocation comparison with residual-extractor caveat;
- per-frame allocation KL/EMD;
- visual overlay parity on 20-50 clips.

Success gate: identical-score Jaccard >= 0.90. Independent residual correlation
is diagnostic, not a hard fail, unless using `cv_reader` or an equivalent
codec-internal residual extractor.

Skip rule: Defer unless OV-3 dev passes or we explicitly want a small
credibility run before model promotion.

ETA: NVIDIA 2-4 hours setup plus 3-6 hours for a parity oracle; M3/M5 not
recommended.

### OV-5: Track A Holdout

Track: Track A semantic substitution

Hypothesis: If OneVision-style scoring is real rather than calibration noise,
it should survive duration buckets, benchmark splits, and at least one
cross-family check.

Success gate: holdout cells remain parse-clean, preserve paired correctness
within gate, and improve or match the current Track A Pareto frontier.

Skip rule: If holdout regresses, do not promote as a paper result; preserve as
a bounded diagnostic.

ETA after dev pass: M3 +12 hours Qwen/Gemma; M5 +6 hours Qwen/Gemma.

### OV-6: Track B Sparse Vision

Track: Track B real skipped work

Hypothesis: Within already-fresh VLMaxxing regions, OneVision-style Top-K patch
allocation may recover more task fidelity per token than current
`magnitude_norm` keep-rate policies, but frozen towers are likely brittle.

Success gate: At matched keep-rate, improve paired correctness/format over
Phase 1.63J Qwen and Phase 1.63G Gemma boundaries while preserving measured
vision-stage timing gains.

Skip rule: If the first Qwen dev tranche fails fidelity at all keep-rates,
skip Gemma and treat the result as evidence that trained sparse encoders are
needed.

ETA: M3 not recommended for broad sweeps; M5 16-28 hours Qwen, +12 hours Gemma
only if Qwen gates.

### OV-7: OV-Encoder Local Feasibility

Track: third-encoder feasibility

Hypothesis: OV-Encoder can be a third local vision-encoder probe, but it is not
a third VLM comparable to Qwen/Gemma until an LMM head or probe stack is
reproduced.

Questions to answer before running:

- Can the Hugging Face model run locally without `flash_attention_2`?
- Is PyTorch/MPS eager attention acceptable for image and sparse-video token
  counts?
- Is an MLX port worth the engineering time?
- Which paper question would encoder-only outputs answer: feature drift,
  sparse-token robustness, or cache-aware training labels?

MLX port assessment:

- Feasible for encoder-only work because the model is a ViT-like encoder with
  patch embedding, attention, MLP, normalization, and 3D RoPE.
- Nontrivial because safetensors conversion, exact 3D RoPE position handling,
  and PyTorch-vs-MLX parity tests are required.
- Not enough for answer-drift experiments without an LMM integration.

Skip rule: Defer while other benchmarks run. Do not run local PyTorch/MPS/MLX
smokes in this planning phase.

Patch-size caveat: Stage 1 selects 16-pixel source patches, while the released
encoder card reports a 14-pixel ViT patch size for Stage 2. Any local encoder
probe must preserve the Stage 2 packing/position conversion instead of feeding
our 16-pixel source grid directly as ViT positions.

ETA: 1 day for PyTorch/MPS feasibility, about 1 week for a careful MLX encoder
port with parity debugging if it becomes scientifically useful.

### OV-8: C-PERSIST Session Economics

Track: after-ingest C-PERSIST

Hypothesis: OneVision-like cold ingest and C-PERSIST follow-up reuse compose
only at the session level. The correct report is setup-inclusive speedup
versus number of same-video questions.

Design:

- first-query lane: dense baseline versus OneVision-style sparse ingest when
  OV-6 has a fidelity-clean cell;
- follow-up lane: existing repaired C-PERSIST policies;
- query counts: 1, 2, 5, 10, 50;
- report setup-inclusive and follow-up-only timings separately.

Success gate: paired-drift-clean session curves with stage-share accounting.

Skip rule: If OV-6 has no fidelity-clean sparse-vision cell, use only
stage-share ceilings and do not claim a working combined runtime.

ETA: M3 6-10 hours accounting only; M5 8-14 hours model-backed if OV-6 gates.

### OV-9: Comparison Table

Track: comparison-accounting

Hypothesis: A fixed comparison table will prevent denominator drift when
comparing imported OneVision patch/accuracy results, reproduced VLMaxxing
baselines, Track A fused scoring, Track B sparse timing, C-PERSIST, and
combined session accounting.

Run now:

```bash
uv run python scripts/build_onevision_vlmaxxing_comparison_table.py
```

Success gate: JSON/CSV/Markdown rows exist with `imported result`,
`reproduced here`, and `hypothesis` status labels, explicit denominator
columns, headline numeric values where known, and target-to-beat gates for
local hypotheses.

Skip rule: If model results are absent, emit the preregistered plan table only;
do not fill result cells speculatively.

ETA: under 1 minute.

### OV-10: Editor Feedback Packet

Track: paper-editor-feedback

Hypothesis: The paper impact depends on experiment outcome:

- If OV-3 improves but OV-6 fails, add OneVision as closest trained
  codec-aligned related work and report a boundary/diagnostic result.
- If OV-6 passes, add a new combined C-VISION result and keep C-PERSIST as a
  separate session denominator.
- If both fail, cite OneVision as evidence that model-native training is likely
  needed for codec-sparse inputs, strengthening the frozen-stack boundary.

Success gate: prepare an editor memo listing imported claims, reproduced local
claims, failed hypotheses, decision-log reopen status, and exact paper sections
that should change.

Skip rule: Do not edit manuscript prose until this memo is reviewed.

ETA: 1-3 hours after artifacts exist.

## Stop Conditions

- Stop all downstream work if patch-position invariants fail.
- Stop model work if real-video allocation is nonsensical or dominated by
  anchor-budget artifacts.
- Stop Track A promotion if first dev tranche is worse than current pixel
  planner at matched budget.
- Stop Track B promotion if sparse-vision timings are positive but fidelity
  fails; keep as C-CEILING/boundary evidence.
- Stop combined speedup claims if stage-share accounting cannot be measured.
- Stop any semantic-saliency language unless paired task evidence supports it.

## Expected Paper Outcomes

`hypothesis`: The most likely publishable addition is a related-work and
diagnostic-evidence update: OneVision is the trained codec-aligned encoder
counterpart; VLMaxxing remains runtime anti-recomputation.

`hypothesis`: The highest-upside result is a fidelity-clean Track B allocator
that improves frozen sparse vision enough to add a new C-VISION lane.

`hypothesis`: The highest-value negative result is showing that OneVision-style
allocation alone does not fix frozen dense vision towers, motivating a trained
cache-aware sparse-token interface as future work.

## Execution Log

Pending model work. This phase has run CPU-only tests and generated planning
artifacts only; no GPU/model experiment has been run.
