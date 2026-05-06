---
date: 2026-05-07
status: design/preregistration draft
related:
  - /Users/jfb/Downloads/2411.05222v1.pdf
  - rlt/
  - paper/claim-matrix.md
  - docs/methodology/performance.md
  - docs/methodology/timing-harness.md
  - research/experiments/2026/2026-04-27-phase-1_63-track-b-sparse-vit-prereg.md
  - research/experiments/2026/2026-04-27-phase-1_63G-gemma-track-b-prereg.md
---

# RLT x VLMaxxing Composition Design

## Preregistration

### Question

Can Run-Length Tokenization (RLT) and VLMaxxing produce a larger measured
training-free video-VLM anti-recomputation system than either strategy alone,
and if so which denominator does the combined system actually reduce?

### Source Status

- **RLT paper/code numbers:** imported result. The local PDF is
  `/Users/jfb/Downloads/2411.05222v1.pdf`; the local clone is `rlt/`.
- **VLMaxxing paper/repo numbers:** reproduced here or bounded local evidence
  only where already recorded in `paper/claim-matrix.md` and
  `docs/reproduction-status.md`.
- **This note's composition claims:** hypothesis until the experiments below
  run and land checked artifacts.

### Comparison Summary

RLT and VLMaxxing share the same core observation: video has temporal
redundancy, and repeated visual evidence should not be paid for repeatedly.
They differ in where they intervene.

RLT is an input tokenization method for video transformers. It compares
same-position temporal tubelets before the model runs, drops repeated patch
tokens, and can expose the surviving token's run length to the transformer.
Its main reported wins are first-pass token, training, and inference throughput
gains on action-recognition/retrieval-style workloads.

VLMaxxing is a runtime/system decomposition for frozen video VLM serving. It
separates denominator regimes: first-pass vision work, after-ingest
same-video follow-up reuse, selective re-prefill, and candidate streaming
state. Its strongest local headline is C-PERSIST follow-up latency; C-VISION is
share-limited first-pass sparse vision; C-CEILING is the accounting rule that
prevents false multipliers.

### Similarities

- Both are video-compression-inspired and content-aware.
- Both try to stay close to deployable systems instead of requiring a large
  new training run.
- Both need a preservation mechanism after deleting work:
  RLT uses run length/duration metadata; VLMaxxing uses scatter-back,
  placeholder/cache alignment, paired drift checks, and explicit denominator
  accounting.
- Both are strongest on static, high-FPS, or repeated-evidence content and
  weakest under camera motion unless motion compensation or shifted-block reuse
  is added.

### Key Differences

| Dimension | RLT | VLMaxxing |
| --- | --- | --- |
| Primary unit | Same-position patch/tubelet runs | Runtime state: frames, vision tokens, KV/prefix cache, follow-up repair |
| Intervention point | Before embedding/model execution | Multiple points: vision tower, LLM prefill/cache, session reuse, streaming |
| Reported workload | Video Transformer action recognition/retrieval | Frozen video VLM QA and serving |
| Current denominator | Visual token sequence length | Explicit stage shares and per-regime denominators |
| Geometry contract | Variable-length packed attention | Frozen VLM placeholder, window, merger, and cache topology constraints |
| Strongest expected local role | Visual admission codec / mask source | Runtime scheduler and measurement discipline |

### Feedback Validation Against Pasted ChatGPT Answer

Verdicts use the feedback skill categories.

1. **"RLT and VLMaxxing are complementary, not competing."** VALID, with a
   caveat: they are complementary only when they attack distinct measured
   denominators or when the combined arm beats both single arms under paired
   measurement.
2. **"RLT removes repeated visual tokens before running the model."** VALID for
   RLT's native ViT setting. In this repo's frozen VLMs, reproducing that
   exactly requires additional geometry work; scatter-back C-VISION alone does
   not shorten LLM prefill tokens.
3. **"RLT can be training-free at inference."** VALID as imported RLT result,
   not reproduced here. The paper reports drop-in inference throughput gains.
4. **"RLT + C-PERSIST can multiply."** OPINION/HYPOTHESIS. Warm follow-up
   C-PERSIST already skips most visual ingest, so RLT mostly affects setup or
   re-prefill tails unless we build a true visual-state sidecar.
5. **"Selective re-prefill can be driven by RLT boundaries."** VALID as a
   design direction. The current Qwen implementation only supports whole-frame
   cache-safe cuts; token-level RLT boundaries require a new topology contract.
6. **"RLT code uses variable-length collation and length encoding."** VALID,
   but length encoding is partly disabled by default and the local code's
   length-ordering path needs verification before porting.
7. **"Composition with C-VISION should be tested as a measured stacked
   experiment."** VALID and required by this repo's timing methodology.

### Scientist Peer Feedback Validation

Validated on 2026-05-07 against the local repo, the local RLT clone, and the
local RLT PDF. Verdicts use the feedback skill categories.

| Peer claim | Verdict | Evidence / action |
| --- | --- | --- |
| Gemma `_keep_indices` silently derives `K` from row 0 and accepts variable-row masks. | VALID | `src/codec_through/pruned_vision_tower.py` only used row-0 count. Fixed in this branch: `_keep_indices` now hard-fails non-uniform row counts and all-empty rows before any RLT mask can reach the wrapper. Added `tests/test_pruned_vision_tower.py`. |
| H3 cannot test `T_prefill` reduction with current 1.51V/1.63G runners. | VALID | `scripts/run_phase1_51V.py` and `scripts/run_phase1_63G_gemma_track_b.py` record `generate_ms` as the whole `mlx_vlm.generate(...)` call. `qwen_selective_reprefill.py` splits `prefill_ms` and `generation_ms`, but these first-turn runners do not. RLT-3G must instrument canonical `multimodal prefill` separately before making a prefill-stage claim. |
| Current H3 2x2 is partly collinear because Gemma placeholder pruning can already compose with C-VISION. | VALID WITH PRECISION | `scripts/run_novelty_pruning_gemma.py` supports `--vision-tower-keep-rate` and also calls `prune_image_placeholders(...)`. The pure `run_phase1_63G_gemma_track_b.py` scatter-back path does not shorten placeholders. Therefore we need two H3 cells: scorer-stacking/union evidence in the combined runner, and a clean denominator-separation cell where scatter-back C-VISION is isolated from placeholder pruning. |
| RLT Table 2 accuracy changes are per-config, not a single 0.1 pp headline. | VALID | Local PDF Table 2 shows K400 `+0.1/-0.2/-0.5` for ViT-B/L/H and SSv2 `-1.0/-0.2` for ViT-B/L. The note now records these as imported per-configuration deltas. |
| RLT shipped configs use `encode_length: False`; skipping length encoding does not forfeit the headline. | VALID | `rlt/configs/experiment/*` set `encode_length: False`; Table 3 shows minimal effect for RLT-only. The local port will not include length encoding until alignment is tested. |
| `batched_get_token_lengths` likely has an ordering bug. | VALID RISK | The code permutes mask to `(B,H,W,T)` while token collation is `(T,H,W)`. This is hidden by disabled length encoding. The plan now forbids porting length encoding without an RLT-pipeline alignment unit test. |
| `tau=0.1` assumes ImageNet normalization and raw-domain mistakes can silently keep first tubelets. | VALID | The paper says comparisons follow ImageNet normalization; RLT code keeps first tubelet via a sentinel. The local helper must pin `mask_domain` and hard-fail if declared normalization is inconsistent with input statistics. |
| Low frame counts and uniform sampling can violate the tubelet assumption. | VALID | The RLT comparison spans the start of the earlier tubelet to the end of the later one. With sparse video sampling, adjacent sampled frames may be seconds apart. Added minimum-frame and repeated-frame tests to RLT-0. |
| Qwen helper must consume frame-major masks and return post-window-permutation indices. | VALID | Existing `QwenVisionPrunePlan.keep_indices` are post-window order. RLT masks are frame-major. The helper contract is now explicit. |
| `window_min_keep` already exists as a one-group floor. | VALID | `qwen_window_aligned_prune_plan` uses `max(1, round(...))`; the RLT plan now treats `window_min_keep=1` as the existing floor and any `>1` as a new explicit experiment. |
| Pixel domain differs between Qwen and Gemma preprocessors. | VALID | Gemma disables resize/image splitting and letterboxes to 512; Qwen uses processor defaults in the 1.51V runner. Thresholds must be calibrated and logged per `mask_domain`; `tau=0.1` is only paper-faithful in the ImageNet-normalized RLT domain. |
| Bootstrap must preserve duplicate item draws. | VALID | Existing analyzer precedent documents list-based paired resampling. New analyzers must use `B=2000`, `item_id` as the resampling unit, and lists rather than sets. |
| Phase protocol blocks, n-justification, claim mapping, decision-log pledge, and phase labels are missing. | VALID | Added below. The n=30 dev/n=30 holdout starting point inherits local VideoMME precedent and is treated as a screening design, not a powered final claim unless the cell-specific MDE is computed from prior timing variance. |
| H1 bucket thresholds are unanchored. | VALID | H1 bucket gap thresholds are now labeled exploratory until Phase RLT-1 estimates within-bucket noise. |
| RLT-as-free-prior deserves its own experiment. | VALID | Promoted to H1.5 / Phase RLT-1.5. |
| C-PERSIST should test Q0 shorter-cached-prefix economics, not only scheduler economics. | VALID AS HYPOTHESIS | Added H4A for Q0 cache shrinking after visual admission is safe; retained H4B whole-frame repair scheduling as conservative fallback. |
| Security audit should explicitly say no install/exec/import from `rlt/`. | VALID | Added to RLT-0 implementation rules. |

### RLT Algorithm Facts To Preserve

- Input shape in RLT code is `[B, C, T, H, W]`.
- For `tubelet_size=2`, the code compares frames `3 vs 0`, `5 vs 2`, etc.:
  the end of the later tubelet against the start of the previous tubelet.
- Differences are absolute, average-pooled over the spatial patch, averaged
  across channels, then thresholded.
- The first temporal tubelet is always kept.
- The paper's default threshold is `tau = 0.1` after ImageNet normalization;
  the code docstring default `2` is not the paper default.
- The inference deltas in Table 2 are not a universal "0.1 pp" claim:
  K400 changes are `+0.1`, `-0.2`, and `-0.5` for ViT-B/L/H respectively,
  while SSv2 changes are `-1.0` and `-0.2` for ViT-B/L. Treat them as
  imported per-configuration results.
- The shipped RLT experiment configs use `encode_length: False`; Table 3 shows
  length encoding has minimal effect for RLT-only. Skipping length encoding in
  the first local port should not forfeit the imported headline.
- The local RLT `batched_get_token_lengths` path appears to emit lengths in
  HWT-major order while token collation is THW-major. Do not port length
  encoding without an alignment unit test against RLT's own tokenizer pipeline.
- RLT's sinusoidal length embedding uses `base=1000`, while its positional
  sinusoid defaults to `base=10000`; preregister the exact variant before any
  duration-encoding experiment.
- Token order in the tokenizer is time-major `(T, H, W)`.
- The RLT clone is MIT-licensed, but its training stack pulls in CUDA/PyTorch,
  xformers, and decord. Port a small pure helper; do not vendor the stack.

### Denominator Model

Use repo timing-stage names from `docs/methodology/timing-harness.md`:

- `demux/decode`
- `frame extraction/image serialization`
- `planner/routing`
- `vision encode`
- `multimodal prefill`
- `text generation`

For first-query dense wall-clock, write:

```text
T_dense = T_decode
        + T_frame_extract_or_processor
        + T_planner_or_routing
        + T_vision_encode
        + T_multimodal_prefill
        + T_text_generation
```

Current C-VISION scatter-back reduces only part of `T_vision`:

```text
T_cvision ~= T_decode
            + T_frame_extract_or_processor
            + T_planner_or_routing
            + T_vision_encode * (1 - r_V)
            + T_multimodal_prefill
            + T_text_generation
            + overhead
```

A true RLT-style visual-admission path can reduce `T_vision` and/or visual
`T_prefill`, depending on where it is integrated:

- **RLT-as-C-VISION-scorer:** reduces later vision blocks only; no prompt
  shortening.
- **RLT-style visual admission after dense vision:** reduces LLM visual prefill only;
  no vision saving.
- **RLT before/inside vision with no scatter-back:** reduces both, but requires
  the most VLM-specific geometry work.

The primary composition model is stage-additive, not product-of-speedups:

```text
T_arm = demux_decode
      + frame_extract_or_processor
      + planner_or_routing
      + mask_compute
      + vision_encode_after_arm
      + multimodal_prefill_after_arm
      + text_generation
      + scatter_or_placeholder_overhead
```

Every modified arm must charge mask generation, threshold calibration,
scatter-back, placeholder pruning, and any repacking overhead. Token keep-rate
is a mechanism metric, not a timing result. `vision_reduction` means measured
vision-stage wall-clock reduction in the paired runner. Dense arms must record
`mask_compute_ms = 0`, `planner_or_routing_ms = 0` when those stages do not
exist, so arm schemas stay comparable. Scatter/placeholder overhead must be
instrumented where possible; if it remains residual, the analyzer must label it
as residual rather than silently folding it into text generation.

For C-PERSIST warm follow-up, RLT does not automatically help because the
cache path already reuses the expensive video prefix. RLT can help:

- setup-inclusive session economics by making Q0/ingest cheaper,
- selective re-prefill by making refreshed visual evidence cheaper,
- streaming-state updates by avoiding rediscovery of unchanged runs.

### Main Hypotheses

**H1-RLT-mask-sane (Track A/B precondition).** An RLT-style pixel/tubelet mask
has high overlap with static same-position reuse on static-camera and
screen-like content, lower overlap on egomotion, and produces monotone
token-retention curves as threshold increases.

- Primary metric: per-item keep rate and Jaccard overlap against
  `STATIC`, `STATIC|SHIFTED`, and current novelty top-k masks.
- Accept if synthetic exact-static cases keep exactly the first tubelet per
  location, a single frame repeated `N` times keeps exactly `1/N` temporal
  tubelets per location, synthetic all-motion cases keep every comparable
  tubelet, keep-rate is non-increasing as threshold rises, and the exploratory
  median keep-rate gap between static/screen/talking-head and FPV/egomotion
  buckets is at least the median within-bucket noise estimated in Phase RLT-1.
- Reject if any synthetic expected case fails, keep-rate is not monotone in
  threshold, the static-vs-egomotion median gap is not distinguishable from
  within-bucket noise, or mask ordering fails.
- Inconclusive if synthetic tests pass but the available corpus lacks enough
  static/egomotion contrast or bucket labels are too noisy for a bucket-level
  conclusion.

**H1.5-RLT-free-prior (Track A/B precondition).** Cheap RLT-style pixel masks
can replace or prefilter more expensive structural/novelty scoring for some
Gemma/Qwen cells.

- Primary metric: agreement/overlap between RLT-style masks and the local
  `gemma_structural`, pixel-novelty, max-min diversity, and magnitude masks at
  matched keep budgets; secondary metric is scorer compute time.
- Accept if RLT-style masks reach at least `0.80` Jaccard with a passing local
  scorer in a content bucket and reduce measured scorer/planner time by at
  least `50%` in the offline profiler.
- Reject if overlap stays below `0.50` in all buckets or if scorer/planner time
  is already too small to move the ceiling.
- Inconclusive if overlap is bucket-specific but the bucket lacks enough
  decision items for a model run.

**H2-CVISION-rlt-style (Track B).** RLT-style group masks can drive measured
Qwen/Gemma compact vision execution at equal or better fidelity-speed tradeoff
than current magnitude-norm and random baselines.

- Primary metrics: paired accuracy delta, choice agreement, vision reduction,
  E2E speedup, ceiling residual.
- Accept for a cell if `delta_acc >= -0.05`, parse failures match dense,
  choice agreement is at least `0.90`, paired correctness drift is no more
  than `2/60` on an n=60 cell, `vision_reduction >= 0.25`,
  `E2E speedup >= 1.03x`, observed speedup is within `0.05x` of the
  vision-share ceiling, and the same quality gates hold within each
  VideoMME duration bucket that has at least 10 paired items.
- Reject if `delta_acc < -0.05`, parse failures increase, choice agreement is
  below `0.80`, paired correctness drift exceeds `4/60`, or vision reduction
  is below `0.15`. Also reject paper-facing promotion if aggregate passes but
  any duration bucket with at least 10 paired items fails the quality gate.
- Inconclusive if quality passes but `vision_reduction` is in `[0.15, 0.25)`
  or E2E speedup is positive but below `1.03x`, or if bucket sample sizes are
  too small for per-bucket gating.

**H3A-scorer-stacking (Track B).** A combined RLT-style + existing
VLMaxxing visual-pruning arm earns composition only if it removes incremental
tokens or vision work beyond either scorer alone under the same model,
manifest, hardware, frame count, and sampling protocol.

- Primary metric: incremental retained-token/kept-group reduction and E2E
  speedup in the Gemma scorer-stacking 2x2: `dense`,
  existing placeholder-pruning scorer, `RLT-style visual-admission-only`, and
  `union/intersection/hybrid` combined arm.
- Acceptance band: combined speedup beats both single arms by at least `5%`
  relative or by more than the paired bootstrap 95% timing interval, whichever
  is stricter; fidelity remains within H2 gates including per-bucket gates;
  incremental tokens removed beyond the best single arm are at least `10%` of
  dense visual placeholders; and the observed speedup is within `0.05x` of the
  explicit stage-additive model above.
- Reject if the combined arm does not beat the best single arm beyond timing
  noise, if quality gates fail, if incremental token removal is below `5%` of
  dense placeholders, or if the stage-additive model cannot explain the
  observation.
- Inconclusive if incremental token removal is in `[5%, 10%)`, the bootstrap
  interval excludes zero but the lift is below the preregistered gate, or
  timing is too noisy to assign the reduced denominator.

**H3B-denominator-separation (Track B).** A true multiplier claim requires a
clean cell where one mechanism shortens measured vision encode and the other
shortens measured multimodal prefill/prompt work.

- Required instrumentation before the run: first-turn Gemma/Qwen runners must
  record `multimodal_prefill_ms` separately from `text_generation_ms`; otherwise
  H3B cannot be accepted.
- Primary 2x2: dense; pure scatter-back C-VISION with dense placeholders;
  RLT-style placeholder pruning with dense vision; and scatter-back C-VISION +
  RLT-style placeholder pruning.
- "Multiplier" language is allowed only if stage timing shows that C-VISION
  reduced measured `vision_encode_ms` while RLT-style admission reduced measured
  `multimodal_prefill_ms` or prompt tokens in the same paired cell. Product
  arithmetic is diagnostic only, never the primary gate.
- Accept if the combined arm beats both single arms beyond the paired bootstrap
  95% interval, passes H2 fidelity gates, and matches the stage-additive model
  within `0.05x`.
- Reject if prefill/generation are not split, if either single-stage mechanism
  fails to reduce its intended stage, or if combined quality fails.
- Inconclusive if both stage reductions are visible but the combined E2E lift
  is absorbed by decode/processor overhead.

**H4A-CPERSIST-q0-prefix-shrinker (Track B/session economics).** RLT-style
visual admission can improve setup-inclusive C-PERSIST if it makes Q0 ingest
and the persisted cached prefix cheaper while preserving follow-up behavior.

- Prerequisite: a safe first-query visual-admission path with paired fidelity
  already passed H3B or a narrower Qwen-specific prompt-shortening gate.
- Primary metrics: Q0 wall-clock, cached prefix token count, setup-inclusive
  per-session wall-clock for Q0..QN, paired follow-up drift, pathological
  output count, and per-turn median follow-up latency.
- Accept if setup-inclusive session wall-clock improves by `>= 5%` over dense
  Q0 + current C-PERSIST, Q0 prompt/prefix tokens are reduced, and no observed
  paired correctness drift appears in the tested slice.
- Reject if visual admission changes follow-up answers, pathological outputs
  increase, Q0 does not get cheaper, or setup-inclusive improvement is below
  `2%`.
- Inconclusive if setup-inclusive improvement is in `[2%, 5%)` with no drift
  or if Q0 gets cheaper but follow-up cache behavior becomes harder to
  interpret.

**H4B-CPERSIST-rlt-scheduler (Track B/session economics).** RLT boundaries can
improve C-PERSIST repair economics by deciding when whole-frame selective
re-prefill is necessary, but it will not improve warm follow-up latency unless
it changes the tail work.

- Primary metrics: setup-inclusive per-session wall-clock, paired follow-up
  drift, pathological output count, per-turn median follow-up latency.
- Accept if setup-inclusive wall-clock improves by `>= 5%` over the current
  adaptive policy with no observed paired correctness drift in the tested
  slice.
- Reject if any paired correctness drift appears in the focused slice,
  pathological output count increases, or setup-inclusive wall-clock improves
  by less than `2%`.
- Inconclusive if setup-inclusive improvement is in `[2%, 5%)` with no drift.

**H5-motion-compensated-rlt (Track A scout).** Same-position RLT will underuse
reuse under camera motion; adding VLMaxxing `SHIFTED`/motion-compensated
classes should recover keep-rate/fidelity on scroll/pan/egomotion clips.

- Primary metric: per-content keep-rate/fidelity boundary, not E2E speed.
- Accept as a follow-up direction if same-position RLT underperforms on
  egomotion while shifted-aware masks retain fidelity at lower fresh budget.
- Reject if shifted-aware masks do not improve egomotion keep-rate by at least
  `10 pp` at matched synthetic fidelity or select visibly wrong regions in the
  offline overlay audit.
- Inconclusive if the available egomotion/scroll corpus is too small or
  unlabeled to distinguish motion compensation from noise.

## Experiment Design

Implementation order is:

1. RLT-0 pure helper and safety checks,
2. RLT-1/H1 profiler,
3. RLT-1.5 free-prior profiler,
4. RLT-2G Gemma C-VISION,
5. RLT-3G Gemma composition cells,
6. RLT-4Q Qwen C-VISION,
7. RLT-5Q C-PERSIST,
8. RLT-6 motion-compensated scout.

This order intentionally front-loads Gemma because it is the cleanest local
measured sparse-vision cell and avoids the longer Qwen 7B thermal pairing
until cheaper evidence has survived.

### Shared Protocol Rules

- Pairing key: `item_id` for single-query runs; `(video_id, turn_index,
  policy, horizon)` for many-turn C-PERSIST rows.
- Bootstrap: paired resampling uses `B=2000`, item-level list resampling with
  replacement, and must never convert bootstrap samples to `set`.
- Order: use ABBA or randomized paired arm order when arms run back-to-back; if
  thermal or memory constraints force sequential arms, record that deviation
  and use existing background-activity and decode-delta gates.
- Power/n: initial `n=30 dev / n=30 holdout` inherits local VideoMME precedent
  from Phase 1.51V/1.63. Treat this as screening unless a cell-specific
  minimum detectable effect is computed from prior paired timing variance.
- Claim mapping: H2 maps to paper claim 15 and claim 5; H3A/H3B map to claim
  10 plus claims 11/15 depending on the arm; H4A/H4B map to claim 14. Any
  adopted, weakened, killed, or revived hypothesis must update
  `research/decision-log.md` after the run lands.
- Mask compute time is recorded on every arm, with dense arms writing
  `mask_compute_ms = 0`.

### Phase RLT-0: Pure Mask Port And Audit

Purpose: build a local, audited RLT mask helper before touching model code.

Implementation:

- Add `src/codec_through/rlt_masks.py`.
- Add `RLTMaskConfig` with:
  - `threshold`
  - `tubelet_size`
  - `patch_size`
  - `normalize_mode` (`none`, `imagenet`)
  - `first_tubelet_mode` (`keep`)
  - `grid_shape`
  - `window_min_keep`
  - `ordering` (`time_major`)
- Add `compute_rlt_keep_mask_from_frames(...)`.
- Add run-length summary helpers, but do not add learned length embeddings.
- Name local outputs `rlt_style_*` or `rlt_endpoint_*` unless and until length
  embeddings and variable-length packed attention are implemented. This is not
  a full local reproduction of RLT.
- Use explicit `ValueError` hard-fails, not `assert`.

Tests:

- first tubelet always kept,
- endpoint comparison matches RLT's `2*tubelet_size - 1` indexing,
- static runs collapse as expected,
- single-frame repeated `N` times keeps exactly one temporal tubelet per
  location,
- minimum-frame guards hard-fail clips whose sampled length cannot form the
  requested tubelet comparison,
- token order is time-major,
- threshold monotonicity,
- declared `normalize_mode` hard-fails if input statistics are inconsistent
  with the declared domain,
- RLT length-encoding alignment is tested against the RLT clone before any
  local length/duration embedding code is allowed,
- shape mismatch hard-fails,
- no dependency on `rlt/`, `torch`, or `decord`.

Security/audit rules:

- Do not run `rlt/dataset_env.sh`.
- Do not `pip install`, `uv add`, or import from the local `rlt/` clone.
- Do not load any RLT checkpoint.
- Re-derive the small mask helper by inspection from the MIT-licensed
  algorithm, preserving attribution if code is copied.

Protocol:

- Model: none.
- Manifest: synthetic unit fixtures plus optional offline frame fixtures.
- Frame count: explicit synthetic cases at 4, 8, 16, and 32 sampled frames.
- Runner command: `uv run pytest tests/test_rlt_masks.py`.
- Analyzer: pytest assertions only.
- Pairing key: not applicable.

### Phase RLT-1: Offline Mask Profiling

Purpose: test H1 before model wall-clock.

Inputs:

- Existing VideoMME dev/holdout manifests.
- Existing TOMATO/MVBench motion slices where local assets exist.
- Synthetic static, pan, object-motion, and screen/UI clips from the repo's
  synthetic corpus tooling if benchmark assets are not enough.

Outputs:

- `research/experiments/2026/artifacts/rlt_mask_profile/`
- Per-item JSONL with:
  - frame count, grid shape, threshold, normalize mode,
  - keep rate,
  - run-length histogram,
  - overlap with current `STATIC`, `STATIC|SHIFTED`, novelty top-k,
  - content bucket.
- Threshold selection must be split-safe: profiler/dev selects the threshold
  set; holdout confirms. Combined dev+holdout n=60 artifacts must be reported
  split-wise and must not feed threshold choice.

Gate:

- Do not run long model experiments until synthetic tests pass and at least one
  static/motion contrast appears in the profiler.

Runtime estimate:

- CPU-only; `n=60` VideoMME plus synthetic slices should be under 30 minutes.

Protocol:

- Model: none.
- Manifest: `research/benchmark_manifests/videomme_dev_v1.toml`,
  `research/benchmark_manifests/videomme_holdout_v1.toml`, plus available
  TOMATO/MVBench motion manifests.
- Frame count: 8 first, then 16/32 only if H1 bucket contrast exists.
- Runner command: new offline profiler, e.g.
  `uv run python scripts/profile_rlt_masks.py --manifest ... --frame-count 8`.
- Analyzer: new profiler summary plus overlap plots/tables.
- Pairing key: `item_id`.

### Phase RLT-1.5: RLT As A Free Prior

Purpose: test H1.5 before model wall-clock.

Design:

- Compute RLT-style masks, Gemma structural masks, pixel-novelty masks,
  max-min diversity masks where features are already available, and magnitude
  masks at matched keep budgets.
- Report overlap by content bucket and by duration bucket.
- Report scorer/planner compute time separately from decode/processor time.
- If RLT strongly agrees with an expensive scorer in a bucket, promote a
  bucket-specific model run that uses RLT as a prefilter or replacement.

Protocol:

- Model: none for pure pixel/structural/novelty arms; Gemma features only for
  feature-dependent offline comparisons if cached or explicitly generated.
- Manifest: same as RLT-1.
- Frame count: 8 first.
- Runner command: same profiler with `--compare-existing-scorers`.
- Analyzer: overlap/time summary; paired bootstrap only if promoted to model
  runs.
- Pairing key: `item_id`.

Runtime estimate:

- Pixel/structural/novelty comparison: under 30 minutes for n=60.
- Feature-dependent comparison may require Gemma vision features and should be
  staged behind an RSS-guarded smoke run.

### Phase RLT-2G: Gemma C-VISION With RLT Masks

Purpose: test H2 across the architecture that currently gives the cleanest
measured sparse-vision cell.

Implementation path:

- Use Gemma's `keep_mask_fn` hook in `src/codec_through/pruned_vision_tower.py`.
- Compute per-item RLT mask in `scripts/run_phase1_63G_gemma_track_b.py`.
- Validate grid shape against Gemma's current 16x16 per-frame token layout.
- Respect the current Gemma wrapper's constant-`K` contract. The first
  implementation must either use fixed-budget per-frame masks derived from
  RLT-style ranking, or extend the wrapper with hard-fails/support for variable
  per-row counts. Raw threshold masks are not drop-in safe.
- Log actual per-item kept counts from the applied mask; do not infer counts
  from `vision_tower_keep_rate`.
- Preserve scatter-back before the pooler.

Arms:

- Dense.
- Current Gemma magnitude mask `L=2`, `kr=0.50`.
- RLT-style fixed-budget threshold/ranking grid.
- RLT + magnitude fill hybrid.
- Matched random controls at the same effective keep-rate.

Decision run:

- Start with `32f short` or the same cell that produced the clean Gemma
  measured sparse-vision operating point.
- Then expand to 8f/16f/32f only if smoke and first decision cell pass.

Runtime estimate:

- Existing 8f/16f/32f Gemma sweep is about 7.5-10.5 h.
- A three-threshold RLT sweep can exceed 20 h unless staged by cell.
- RSS guard: 9 GB; model path `gemma-4-e4b-it-4bit`.

Protocol:

- Model: `gemma-4-e4b-it-4bit`.
- Manifest: start with `research/benchmark_manifests/videomme_holdout_v1_short_only.toml`
  or the exact checked manifest behind the clean 32f-short Gemma sparse cell;
  then use `research/benchmark_manifests/videomme_combined_v1_n60.toml` only
  after dev thresholds are frozen.
- Frame count: 32 for the clean short-cell replication first; 8/16/32 breadth
  only after the first cell passes.
- Runner command: `uv run --group vlm python scripts/run_phase1_63G_gemma_track_b.py ...`
  with new RLT mask flags.
- Analyzer: `scripts/analyze_phase1_63_track_b_sparse.py`, extended to report
  actual applied mask counts and per-bucket gates.
- Pairing key: `item_id`.

### Phase RLT-3G: Gemma Composition Cells

Purpose: test both scorer-stacking (H3A) and clean denominator separation
(H3B) without conflating the two.

Rationale:

The existing `scripts/run_novelty_pruning_gemma.py` can already combine
placeholder pruning with `--vision-tower-keep-rate`. That is useful, but it is
not automatically a denominator-separation experiment because placeholder
pruning and existing novelty/structural arms already attack LLM prompt length.
Therefore RLT-3G has two cells:

1. **RLT-3G-A scorer-stacking:** asks whether RLT-style masks remove
   additional tokens beyond existing structural/novelty arms while preserving
   paired fidelity.
2. **RLT-3G-B denominator separation:** isolates pure scatter-back C-VISION
   from pure placeholder pruning, then tests the combined arm after
   `multimodal_prefill_ms` is instrumented separately from text generation.

Implementation path:

- Add an RLT-style mask arm to `scripts/run_novelty_pruning_gemma.py` or a
  small sibling runner.
- Reuse `prune_image_placeholders(...)` validation.
- Instrument first-turn runners so `multimodal_prefill_ms` and
  `text_generation_ms` are separate; without this, H3B cannot accept.
- Persist `rlt_run_lengths_summary`, placeholder counts, prompt-token
  reduction, `mask_compute_ms`, `placeholder_prune_ms`, and any scatter-back
  overhead.
- Add a per-frame minimum keep requirement so visual admission cannot erase an
  entire frame's visual evidence.
- Use ABBA/randomized arm order where feasible and paired bootstrap intervals
  with duplicate-preserving item resampling.

RLT-3G-A arms:

- Dense.
- Existing placeholder-pruning scorer, e.g. `gemma_structural` or the current
  local Pareto arm.
- RLT-style visual-admission-only at a dev-selected threshold/budget.
- RLT-style plus existing scorer by union/intersection/hybrid policy.
- Matched random visual admission at the same effective keep-rate.

RLT-3G-B arms:

- Dense.
- Pure scatter-back C-VISION with dense placeholders.
- RLT-style placeholder pruning with dense vision.
- Scatter-back C-VISION + RLT-style placeholder pruning.

Gate:

- RLT-3G-A is accepted only under H3A.
- RLT-3G-B is accepted only under H3B.
- Both cells inherit H2 paired quality and per-bucket gates.

Protocol:

- Model: `gemma-4-e4b-it-4bit`.
- Manifest: start with the short-bucket cell used by the clean Gemma sparse
  result; expand to `research/benchmark_manifests/videomme_combined_v1_n60.toml`
  only after dev thresholds and arm definitions are frozen.
- Frame count: 32 for the first short-cell denominator test; 8/16/32 breadth
  only after the first cell passes.
- Runner command: new sibling autonomous runner or
  `uv run --group vlm python scripts/run_novelty_pruning_gemma.py ...` with
  explicit RLT flags and stage-split timing.
- Analyzer: new RLT composition analyzer or an extension of
  `scripts/analyze_phase1_63_track_b_sparse.py`; must report H3A/H3B
  separately.
- Pairing key: `item_id`.

Runtime estimate:

- Comparable to prior Gemma novelty-pruning cells: tens of minutes per n=30
  8f arm, several hours for a grid; full 1.51R stage history was about 10-12 h.

### Phase RLT-4Q: Qwen C-VISION With RLT Masks

Purpose: test H2 in the existing measured Qwen sparse-ViT harness after Gemma
has established whether the idea is worth the longer Qwen runs.

Implementation path:

- Add an explicit per-item external keep-index path to the Qwen pruning wrapper.
  A simple `score_mode="rlt_pixel"` is insufficient because the current wrapper
  computes scores from hidden states inside `_group_scores`, while RLT-style
  masks are pixel-side and item-specific.
- Compute RLT-style masks in `scripts/run_phase1_51V.py` after decode/processor
  preparation and before `_compute_qwen_features`.
- Change `_prepare_item` or add a sibling preparation function so decoded
  frames remain available for mask computation.
- The helper contract is explicit: input masks are frame-major; the helper
  applies Qwen's `window_index` permutation and returns keep indices in
  post-window group order, matching `QwenVisionPrunePlan.keep_indices`.
- The helper consumes `image_grid_thw`, `window_index`, `spatial_merge_size`,
  and `spatial_merge_unit`, then validates:
  - total groups match `qwen_groups_per_frame`,
  - emitted keep indices are in Qwen post-window group order,
  - windows do not cross frame boundaries,
  - every active window keeps at least one group,
  - `window_min_keep=1` is the existing floor; any value `>1` is a new
    experiment and must be logged,
  - promotions caused by `window_min_keep` are logged.
- Preserve scatter-back before merger so the LLM prompt geometry remains dense.

Arms:

- Dense.
- Current Qwen C-VISION magnitude norm, `L=2`, `kr=0.50`.
- Uniform random, matched keep-rate, four seeds where affordable.
- RLT-style thresholds selected only from profiler/dev: conservative,
  paper-default-like, aggressive.
- RLT-style capped-to-matched-keep-rate variants so RLT is compared both as
  content-adaptive and as a scorer at equal budget.
- RLT + magnitude hybrid: hard-keep first tubelet and RLT novel groups, fill
  remaining quota by magnitude.

First smoke:

- VideoMME `--n-items 1`, `8f`, one conservative threshold.

Decision run:

- VideoMME dev n=30 at `8f` first; holdout n=30 only after threshold/arm
  selection is frozen. Combined n=60 summaries are reporting artifacts, not
  tuning inputs.
- Add `16f` only if 8f passes fidelity and shows a meaningful distinct
  denominator effect.

Protocol:

- Model: `Qwen2.5-VL-7B-Instruct-4bit`.
- Manifest: `research/benchmark_manifests/videomme_dev_v1.toml`, then
  `research/benchmark_manifests/videomme_holdout_v1.toml` after freeze.
- Frame count: 8 first; 16 only after 8f passes.
- Runner command: `uv run --group vlm python scripts/run_phase1_51V.py ...`
  with new external keep-index flags.
- Analyzer: `scripts/analyze_phase1_63_track_b_sparse.py`, extended for RLT
  mask metadata and per-bucket gates.
- Pairing key: `item_id`.

Runtime estimate:

- Dense 8f arm: about 1.4-1.6 h if not reused.
- Each Qwen sparse 8f arm: about 1.3-1.5 h.
- Three RLT-style thresholds plus two controls: about 7-10 h if run
  sequentially.
- 16f expansion roughly doubles per-arm cost.
- RSS guard: 9 GB; model path `Qwen2.5-VL-7B-Instruct-4bit`.

### Phase RLT-5Q: C-PERSIST Q0 Prefix And Whole-Frame Scheduler

Purpose: test H4A/H4B without unsafe token-level Qwen cache cuts.

Implementation path:

- Do not change `qwen_selective_reprefill.py` to cut inside frame blocks.
- Use `scripts/run_phase1_55L_many_turn_cpersist.py` as the many-turn runner.
  Existing policy strings `fixed_k1`, `adaptive_post_q2`, and `refresh10`
  are the precedent to extend.
- H4A: after safe visual admission exists, compare dense Q0 + C-PERSIST
  against shorter-Q0-prefix + C-PERSIST under identical sessions.
- H4B: add a policy layer:
  - `fixed_k1` baseline,
  - current `adaptive_post_q2`,
  - `rlt_content_conditioned`: choose a whole-frame policy from fixed sampled
    video content under the existing many-turn protocol,
  - `rlt_run_age`: force K=1 when a reused run exceeds an age cap.
- Log the RLT decision features per turn.

The existing many-turn protocol reuses a fixed sampled frame set per video; it
does not expose a changing video tail. A sliding/updated-frame protocol would
be a separate C-STREAM-style phase.

Protocol:

- Model: Qwen C-PERSIST model used by current 1.55L artifacts.
- Manifest: the focused short-bucket many-turn manifest first, then the
  short/medium/long breadth only if the focused slice passes.
- Frame count: match the prior safe C-PERSIST cell.
- Runner command: `uv run --group vlm python scripts/run_phase1_55L_many_turn_cpersist.py ...`
  with new policy names.
- Analyzer: existing many-turn summary logic plus H4A/H4B setup-inclusive
  fields.
- Pairing key: `(policy, video_id, horizon, turn_index)`.

Gate:

- H4A uses the Q0 prefix-shrinker gates.
- H4B uses the scheduler gates.
- No token-level cache multiplier claim is allowed from H4B.

Runtime estimate:

- Existing adaptive many-turn breadth is about 5.1 h for short/medium/long/32f
  cells; a focused short-bucket policy comparison should be under 1.5 h.
- Full many-turn RLT policy grid can exceed 6 h.

### Phase RLT-6: Motion-Compensated / Shifted-Run Scout

Purpose: think outside same-position RLT without contaminating the main
measured claims.

Design:

- Use current `BlockClass.SHIFTED` and block statistics to identify likely
  translational shifts.
- Test a small set of offsets per block, not dense optical flow.
- Only promote to model runs if offline profiler shows same-position RLT
  fails on egomotion but shifted-run masks recover reuse without selecting
  obviously wrong regions.

Status:

- Scout only. It should not block RLT-2/RLT-3 implementation.

## Autonomous Runner Requirements

- Every long runner must:
  - write one JSONL row per item/turn,
  - write a summary JSON per arm,
  - be resumable by detecting complete arm artifacts,
  - hard-fail incomplete stale artifacts or rerun the arm,
  - keep `--n-items` smoke mode,
  - carry `rss_guard_mb`,
  - log model path, manifest, git SHA, decode backend, colorspace, resize
    policy, padding policy and pad-mask status, sampling mode, prompt-bank
    version, frame count, threshold, normalization, grid shape, and mask policy,
  - reuse existing analyzers where possible.
- The top-level autonomous queue should run:
  1. preflight,
  2. CPU mask profiler,
  3. n=1 Gemma smoke,
  4. n=1 Qwen smoke,
  5. selected decision cells,
  6. analyzers,
  7. gate summary.
- Claude/Codex supervision should interpret only completed artifacts and should
  record negative outcomes in this note, `research/decision-log.md`, and
  paper-facing docs only when a hypothesis changes status.

## Open Risks

- RLT threshold calibration differs by pixel domain. The faithful `tau=0.1`
  setting assumes ImageNet-normalized tensors, not raw RGB.
- The first local implementation must choose and log `mask_domain`. Candidate
  domains are raw decoded frames, explicit ImageNet-normalized tensors, Qwen
  processor tensors, and Gemma letterboxed processor tensors. Thresholds are
  not shared across those domains without profiler evidence.
- RLT's same-position assumption is brittle under camera motion.
- RLT length encoding is not safe to port first; the local RLT code's length
  ordering should be tested before any duration embedding claim.
- Current Qwen C-PERSIST helper intentionally rejects mid-frame image-token
  cuts. Bypassing that would risk silent cache/position corruption.
- A dense decoder still has to decode frames to compute RLT-style masks, so
  decode-heavy regimes may show little E2E gain.
- Composition with C-VISION may be subadditive because both methods can attack
  the same vision-stage share.
- Existing first-turn runners must be instrumented before they can prove
  prefill-stage reductions; otherwise prompt shortening remains inferred from
  prompt token counts and folded generate wall-clock.

## Verification Plan

Plan-design review completed before this commit:

- `ai-review team --stage plan` returned a soft-fail-only report at
  `.ai/reviews/20260506T220726+0000-plan-442ef6b7db4a1896-summary.json`.
  The managed reviewers produced no usable findings because Codex hit a local
  session permission error and Claude/Gemini timed out. The workflow gate
  allowed proceed-with-warning; no zombie reviewer process remained.
- Four sub-agents completed and were closed: one RLT paper/code researcher, one
  repo insertion-point explorer, one scientific plan reviewer, and one
  implementation-risk reviewer. Their required changes are incorporated above.
- `/Users/jfb/.local/bin/ai-workflow run-checks` reported no required checks
  configured.
- Scientist peer feedback was validated against the repo and local RLT source
  on 2026-05-07. Valid findings are recorded in the feedback-validation table
  above.
- `uv run --group vlm pytest tests/test_pruned_vision_tower.py` verifies the
  new Gemma sparse-wrapper hard fail for variable-row-`K` masks.

Before first implementation code commit:

- rerun the repo's review/check workflow for the implementation diff,
- confirm this preregistration still matches the code being added.

After pure-mask implementation:

- `uv run pytest tests/test_rlt_masks.py`
- `uv run pytest tests/test_temporal.py tests/test_novelty_pruning.py`

After Qwen/Gemma wiring:

- `uv run --group vlm pytest tests/test_pruned_vision_tower.py`
- `uv run pytest tests/test_qwen_vision_pruning.py tests/test_novelty_pruning.py`
- `uv run pytest tests/test_phase1_63_track_b_analyzer.py`
- n=1 smoke for Qwen and Gemma RLT arms

Before long runs:

- artifact preflight,
- model path checks,
- manifest checks,
- RSS guard check,
- explicit runtime estimate in the command output or queue status JSON.

## Expected Outcome Interpretation

If RLT improves visual admission but not C-PERSIST warm follow-up, the larger
system is still valuable: RLT handles ingest/refresh, VLMaxxing handles
session reuse and cache correctness.

If RLT + C-VISION does not beat the best single C-VISION arm, the result is a
useful negative composition boundary and should weaken any multiplier claim.

If RLT-style visual admission plus scatter-back C-VISION reduces both prefill
and vision shares with preserved fidelity, that is the strongest local path
toward the "bigger thing": a duration-aware, cache-aware video VLM runtime.
