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

### RLT Algorithm Facts To Preserve

- Input shape in RLT code is `[B, C, T, H, W]`.
- For `tubelet_size=2`, the code compares frames `3 vs 0`, `5 vs 2`, etc.:
  the end of the later tubelet against the start of the previous tubelet.
- Differences are absolute, average-pooled over the spatial patch, averaged
  across channels, then thresholded.
- The first temporal tubelet is always kept.
- The paper's default threshold is `tau = 0.1` after ImageNet normalization;
  the code docstring default `2` is not the paper default.
- Token order in the tokenizer is time-major `(T, H, W)`.
- The RLT clone is MIT-licensed, but its training stack pulls in CUDA/PyTorch,
  xformers, and decord. Port a small pure helper; do not vendor the stack.

### Denominator Model

For first-query dense wall-clock, write:

```text
T_dense = T_decode + T_processor + T_vision + T_prefill + T_generate
```

Current C-VISION scatter-back reduces only part of `T_vision`:

```text
T_cvision ~= T_decode + T_processor + T_vision * (1 - r_V) + T_prefill + T_generate + overhead
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
T_arm = decode + processor + mask_or_planner
      + vision_after_arm + visual_prefill_after_arm
      + generate + scatter_or_placeholder_overhead
```

Every modified arm must charge mask generation, threshold calibration,
scatter-back, placeholder pruning, and any repacking overhead. Token keep-rate
is a mechanism metric, not a timing result. `vision_reduction` means measured
vision-stage wall-clock reduction in the paired runner.

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
  location, synthetic all-motion cases keep every tubelet, keep-rate is
  non-increasing as threshold rises, and the median keep-rate gap between
  static/screen/talking-head and FPV/egomotion buckets is at least `15 pp`.
- Reject if any synthetic expected case fails, keep-rate is not monotone in
  threshold, the static-vs-egomotion median gap is below `5 pp`, or mask
  ordering fails.
- Inconclusive if synthetic tests pass but bucket gaps land in `[5 pp, 15 pp)`
  or the available corpus lacks enough static/egomotion contrast.

**H2-CVISION-rlt-style (Track B).** RLT-style group masks can drive measured
Qwen/Gemma compact vision execution at equal or better fidelity-speed tradeoff
than current magnitude-norm and random baselines.

- Primary metrics: paired accuracy delta, choice agreement, vision reduction,
  E2E speedup, ceiling residual.
- Accept for a cell if `delta_acc >= -0.05`, parse failures match dense,
  choice agreement is at least `0.90`, paired correctness drift is no more
  than `2/60` on an n=60 cell, `vision_reduction >= 0.25`,
  `E2E speedup >= 1.03x`, and observed speedup is within `0.05x` of the
  vision-share ceiling.
- Reject if `delta_acc < -0.05`, parse failures increase, choice agreement is
  below `0.80`, paired correctness drift exceeds `4/60`, or vision reduction
  is below `0.15`.
- Inconclusive if quality passes but `vision_reduction` is in `[0.15, 0.25)`
  or E2E speedup is positive but below `1.03x`.

**H3-true-composition (Track B).** A combined RLT + VLMaxxing arm earns
composition only if it beats both corresponding single arms under the same
model, manifest, hardware, frame count, and sampling protocol.

- Primary metric: combined-arm E2E speedup over dense in the Gemma 2x2
  `dense`, `C-VISION-only`, `RLT-style visual-admission-only`, and
  `C-VISION + RLT-style visual admission` cell.
- Acceptance band: combined speedup beats both single arms by at least `5%`
  relative or by more than the paired bootstrap 95% timing interval, whichever
  is stricter; fidelity remains within H2 gates; and the observed combined
  speedup is within `0.05x` of the explicit stage-additive model above.
- "Multiplier" language is allowed only if stage timing shows that C-VISION
  reduced measured vision work while RLT-style admission reduced measured
  visual-prefill/prompt work in the same paired cell. Product arithmetic is
  diagnostic only, never the primary gate.
- Reject if the combined arm does not beat the best single arm beyond timing
  noise, if quality gates fail, or if the stage-additive model cannot explain
  the observed result.
- Inconclusive if combined speedup beats the best single arm by less than `5%`
  relative but the bootstrap interval excludes zero, or if stage timing is
  too noisy to assign the reduced denominator.

**H4-CPERSIST-rlt-scheduler (Track B/session economics).** RLT boundaries can
improve setup-inclusive C-PERSIST economics by deciding when whole-frame
selective re-prefill is necessary, but it will not improve warm follow-up
latency unless it changes the tail work.

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
- token order is time-major,
- threshold monotonicity,
- shape mismatch hard-fails,
- no dependency on `rlt/`, `torch`, or `decord`.

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

### Phase RLT-2Q: Qwen C-VISION With RLT Masks

Purpose: test H2 in the existing measured Qwen sparse-ViT harness.

Implementation path:

- Add an explicit per-item external keep-index path to the Qwen pruning wrapper.
  A simple `score_mode="rlt_pixel"` is insufficient because the current wrapper
  computes scores from hidden states inside `_group_scores`, while RLT-style masks
  are pixel-side and item-specific.
- Compute RLT-style masks in `scripts/run_phase1_51V.py` after decode/processor
  preparation and before `_compute_qwen_features`.
- Change `_prepare_item` or add a sibling preparation function so decoded
  frames remain available for mask computation.
- Convert frame-major RLT-style masks into Qwen post-window group indices with
  a pure helper that consumes `image_grid_thw`, `window_index`,
  `spatial_merge_size`, and `spatial_merge_unit`, then validates:
  - total groups match `qwen_groups_per_frame`,
  - emitted keep indices are in Qwen post-window group order,
  - windows do not cross frame boundaries,
  - every active window keeps at least one group,
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

Runtime estimate:

- Dense 8f arm: about 1.4-1.6 h if not reused.
- Each Qwen sparse 8f arm: about 1.3-1.5 h.
- Three RLT-style thresholds plus two controls: about 7-10 h if run
  sequentially.
- 16f expansion roughly doubles per-arm cost.
- RSS guard: 9 GB; model path `Qwen2.5-VL-7B-Instruct-4bit`.

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

### Phase RLT-3G: Primary Gemma 2x2 Visual-Admission Composition

Purpose: directly test the multiplication hunch on a denominator that
C-VISION scatter-back does not reduce.

Rationale:

Existing C-VISION scatter-back shortens later vision-block execution but leaves
LLM visual prompt geometry dense. RLT's native promise is visual-token admission
before transformer execution. The closest safe frozen-VLM proxy is Gemma
placeholder pruning: compute visual features, drop RLT-static visual tokens,
shorten image placeholders with existing validation, and measure
visual-prefill/generate effects. By itself this does not save dense vision
work, but it attacks a different stage share from scatter-back C-VISION. The
primary multiplication test is therefore a paired 2x2:

1. dense,
2. C-VISION-only,
3. RLT-style visual-admission-only,
4. C-VISION + RLT-style visual admission.

All four arms must use the same model, manifest split, frame count, item order,
sampler, prompt format, and preprocessing.

Implementation path:

- Add an RLT mask arm to `scripts/run_novelty_pruning_gemma.py` or a small new
  sibling runner.
- Reuse `prune_image_placeholders(...)` validation.
- Persist `rlt_run_lengths_summary`, placeholder counts, and prompt-token
  reduction.
- Add a per-frame minimum keep requirement so the first visual-admission arm
  cannot erase an entire frame's visual evidence.
- ABBA-order or otherwise randomize paired arms where feasible, and compute
  paired bootstrap intervals for latency deltas.

Arms:

- Dense.
- C-VISION-only at the current validated Gemma operating point.
- RLT-style visual-admission-only at a dev-selected threshold/budget.
- C-VISION + RLT-style visual admission.
- Matched random visual admission at the same effective keep-rate.

Gate:

- Same paired quality gates as H2.
- Composition accepted only under H3 and the stage-additive model.
- Inconclusive if the RLT-style admission arm reduces prompt tokens but not
  measured prefill/generate wall-clock beyond timing noise.

Runtime estimate:

- Comparable to prior Gemma novelty-pruning cells: tens of minutes per n=30
  8f arm, several hours for a grid; full 1.51R stage history was about 10-12 h.

### Phase RLT-4Q: C-PERSIST Whole-Frame RLT Scheduler

Purpose: test H4 without unsafe token-level Qwen cache cuts. This phase is
scheduler/session-economics evidence, not primary multiplication evidence.

Implementation path:

- Do not change `qwen_selective_reprefill.py` to cut inside frame blocks.
- Add a policy layer in the many-turn/selective-reprefill runner:
  - `fixed_k1` baseline,
  - current `adaptive_post_q2`,
  - `rlt_content_conditioned`: choose a whole-frame policy from fixed sampled
    video content under the existing many-turn protocol,
  - `rlt_run_age`: force K=1 when a reused run exceeds an age cap.
- Log the RLT decision features per turn.

The existing many-turn protocol reuses a fixed sampled frame set per video; it
does not expose a changing video tail. A sliding/updated-frame protocol would
be a separate C-STREAM-style phase.

Gate:

- Compare setup-inclusive wall-clock and follow-up drift under identical video
  IDs, prompts, frame count, sampler, and seed.
- No token-level multiplier claim is allowed from this phase.

Runtime estimate:

- Existing adaptive many-turn breadth is about 5.1 h for short/medium/long/32f
  cells; a focused short-bucket policy comparison should be under 1.5 h.
- Full many-turn RLT policy grid can exceed 6 h.

### Phase RLT-5: Motion-Compensated / Shifted-Run Scout

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
  3. n=1 Qwen smoke,
  4. n=1 Gemma smoke,
  5. selected decision cells,
  6. analyzers,
  7. gate summary.
- Claude/Codex supervision should interpret only completed artifacts and should
  record negative outcomes in this note, `research/decision-log.md`, and
  paper-facing docs only when a hypothesis changes status.

## Open Risks

- RLT threshold calibration differs by pixel domain. The faithful `tau=0.1`
  setting assumes ImageNet-normalized tensors, not raw RGB.
- RLT's same-position assumption is brittle under camera motion.
- RLT length encoding is not safe to port first; the local RLT code's length
  ordering should be tested before any duration embedding claim.
- Current Qwen C-PERSIST helper intentionally rejects mid-frame image-token
  cuts. Bypassing that would risk silent cache/position corruption.
- A dense decoder still has to decode frames to compute RLT-style masks, so
  decode-heavy regimes may show little E2E gain.
- Composition with C-VISION may be subadditive because both methods can attack
  the same vision-stage share.

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

Before first implementation code commit:

- rerun the repo's review/check workflow for the implementation diff,
- confirm this preregistration still matches the code being added.

After pure-mask implementation:

- `uv run pytest tests/test_rlt_masks.py`
- `uv run pytest tests/test_temporal.py tests/test_novelty_pruning.py`

After Qwen/Gemma wiring:

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
