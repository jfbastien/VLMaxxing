# External Feedback Validation

Scope:

- validated the imported ChatGPT review/backlog files under `seed/chatgpt/reviews/`
- validated the newer future-research memo and backlog
- validated the Claude review against the current repo, imported artifacts, local model configs, and primary sources where needed

## Overall Verdict

The external reviews were useful, but not equally trustworthy.

What survived validation:

- the repo's main evidentiary split is Track A versus Track B
- several benchmark-hygiene and fail-closed issues were real
- the project should keep its current narrow claim and expand only with measured local evidence
- changed-window execution, screen-content specialization, and decoder-side routing deserve plan space

What needed reframing:

- `compute-denial` is a worthwhile robustness evaluation bucket, not a current headline claim
- machine-oriented sidecars and AI-native codecs are future horizons, not near-term repo objectives
- several stronger whitepaper numbers and phrasing needed correction before they become paper claims

## Validated And Fixed In This Commit

### 1. Fail-closed utility behavior

Verdict:

- VALID

Evidence:

- `extract_choice` could treat ambiguous `A or B` output as a real answer
- `uniform_frame_indices(1, 4)` previously returned duplicates
- temporal diffing silently cropped mismatched frame shapes

Fixes made:

- ambiguous letter outputs now return `None`
- invalid frame sampling now raises
- mismatched frame shapes and misaligned block geometry now raise

### 2. Timing harness hazard in frame extraction

Verdict:

- VALID

Evidence:

- `src/codec_through/ffmpeg.py` inherited a one-ffmpeg-process-per-frame helper

Fixes made:

- existing helper is now explicitly reference/debug only
- added `extract_frames_single_pass(...)` for timing-sensitive paths

### 3. Qwen geometry and checkpoint nuance

Verdict:

- VALID

Evidence:

- local config inspection confirms Qwen2.5-VL full-attention blocks at `[7, 15, 23, 31]`
- the stronger claim that layer `23` is the best merge point still comes only from imported artifacts

Fixes made:

- docs now distinguish locally verified config structure from imported merge-point ranking

## Validated And Promoted Into The Plan

### 4. Add a Phase 0.5 feasibility spike

Verdict:

- VALID

Why:

- before Phase 1, the repo should prove that the local MLX-VLM path exposes the required cached-feature interface cleanly enough for Track A work

Plan impact:

- added a preregistered Phase 0.5 experiment note under `research/experiments/2026/`

### 5. Determinism and agreement-floor requirements

Verdict:

- VALID

Why:

- Track A agreement is uninterpretable if the dense baseline itself is unstable
- raw agreement without baseline accuracy or chance correction is too weak

Plan impact:

- methodology now requires repeated dense-baseline checks and chance-corrected agreement when task format permits it

### 6. Acceptance bands and composition gate

Verdict:

- VALID

Why:

- the repo needs preregistered success or rejection criteria
- stacked multipliers should stay gated until measured on the same stack

Plan impact:

- performance and timing docs now require acceptance bands and explicit composition rules

### 7. Screen-content path and machine-oriented standards

Verdict:

- VALID, WITH SCOPE CONTROL

Why:

- the repo and external sources both support keeping screen content as a separate later-phase branch
- MPEG VCM, MPEG FCM, JPEG AI, and AV1 screen-content tools support the long-term framing

Plan impact:

- literature map and paper framing now include these directions, but only as future horizons

## Validated But Reframed Or Softened

### 8. Continuous H.264 spatial scoring

Verdict:

- VALID (MINOR)

Why:

- the underlying skepticism is justified
- calling it fully `killed` is stronger than the current local evidence

Plan impact:

- status changed to `deprioritized`

### 9. Provenance-aware KV policy

Verdict:

- OPINION

Why:

- it was never a core tested claim in this repo

Plan impact:

- treated as `not currently in scope`, not as a killed idea

### 10. Robustness / compute-denial framing

Verdict:

- OPINION

Why:

- it is a useful red-team evaluation idea
- it is not yet a primary claim backed by this repo

Plan impact:

- kept in `paper/framing.md` as future evaluation language, not as a top-level result

## Still Hypotheses

### 11. Changed-query attention

Verdict:

- CAN'T VERIFY

Why:

- plausible and worth planning
- not yet backed by local runtime evidence

Plan impact:

- remains after changed-window execution, not before it

### 12. Sensor-fusion codecs and AI-native codecs

Verdict:

- OPINION

Why:

- useful long-term framing
- outside the currently justified repo scope

Plan impact:

- recorded as future horizons only

## Whitepaper Corrections Triggered By Review

Validated issues:

- MVBench wording needed to distinguish the 20-task benchmark from the local 18-task saved run
- cache-size arithmetic needed model- and resolution-specific clarification

## 2026-04-27 Reviewer-Defense Queue Feedback

Validated issues:

- Track B remained the largest systems-evidence gap, but the minimal publishable
  MVP is not a 1-2 week project. The existing Qwen compact post-layer vision
  path already performs real skipped vision-tower work after the configured
  pruning layer; what remains multi-day work is custom-kernel sparse execution
  that also shrinks prompt geometry or prefill.
- Low-FPS dense baselines must be interpreted as a benchmark-conditioned
  deployment baseline, not as evidence that reuse is unnecessary unless a
  matched low-FPS-plus-reuse arm is run.
- Sampler robustness should not be reported as sampler-invariance from a single
  perturbed point. The T=0.7 scout is a reviewer-defense check with an explicit
  exact-match miss if any paired drift appears.
- Cross-architecture drift needs a numeric matched-geometry rule before the run,
  otherwise the same result can be narrated either as transfer or as an
  architecture-conditioned boundary after inspection.

Plan impact:

- staged a Phase 1.63 Track B compact-Qwen-ViT run as the first reviewer-defense
  queue phase
- hardened the 1.62D low-FPS analyzer so format failures cannot be called
  competitive
- raised and documented the 1.55F-16f speedup floor and fixed the sampler/max
  token contract
- added a numeric Gemma-vs-Qwen drift threshold to the 1.57G summary path
- TurboQuant was being presented too aggressively for a quality-neutral composed claim

Those corrections now live in `seed/whitepaper/whitepaper.md`.

## Additional Round-2 Claude Review Takeaways

Validated and integrated:

- move the imported whitepaper under `seed/`
- tighten Phase 0.5 with concrete models, clip ids, prompts, API DAG steps, and `N=50` repeated runs
- add a local redundancy-measurement phase before caching comparisons
- move Gemma from `later` to `early cross-family check`
- shrink KB notes so the decision log is the canonical status ledger
- add a local-only clip policy with primary corpus versus predecessor cross-check tiers

Validated but not executed in this commit:

- adding a repository license

Reason:

- the user has not chosen between MIT and Apache-2.0 yet

## Additional Round-3 ChatGPT Review Takeaways

Validated and integrated:

- add a Phase 0.75 cache-path identity control between determinism and
  planner-driven reuse
- add an explicit preprocessing contract covering decode backend, resize,
  padding, masking, and sampling mode
- make prompt banks and answer keys first-class versioned artifacts
- add a synthetic local stress corpus for controlled OCR, color, small-object,
  scene-cut, and flicker cases
- keep `contiguous_window` and `uniform_global` sampling as explicitly separate
  modes
- tighten Track B timing rules so temp-image helpers stay reference-only and
  in-memory decode becomes a required follow-on for paper-grade claims
- add compressed-video and temporal-redundancy lineage references such as
  CoViAR, DMC-Net, Eventful Transformers, and FitPrune

## Post-Bring-Up Review Validation

These checks were run against the current local notes, artifacts, prompt bank,
generator, and tracked seed material after the first local Track A bring-up.

### 13. "The whitepaper headline claims are not reproduced locally yet"

Verdict:

- VALID

Evidence:

- the repo reproduces determinism, cache-path identity, local redundancy spread,
  and a narrow synthetic answer-stability slice
- the repo does not yet contain local direct feature-space reproductions for the
  whitepaper mechanism section, benchmark-native TOMATO or MVBench runs,
  refresh-interval drift, or Track B skipped-compute evidence

Action:

- added [reproduction-status.md](reproduction-status.md) as the canonical local
  ledger for imported versus reproduced claims
- softened current-plan and paper-framing language so the synthetic pilot is not
  mistaken for full whitepaper reproduction

### 14. "The first synthetic pilot can be over-interpreted"

Verdict:

- VALID

Evidence:

- the pilot agreement result is real, but the current suite is synthetic-only
- the current suite does not yet include divergence-capable items where
  over-aggressive reuse would be expected to fail

Action:

- plan and paper framing now treat the pilot as substrate evidence, not a
  headline reproduction

### 15. "`synthetic_affine_pan` is a weak semantic pan probe"

Verdict:

- VALID

Evidence:

- the current generator offsets the background grid while leaving the dominant
  foreground content stationary
- the prompt wording therefore overstates what the clip visibly shows

Action:

- queued for synthetic-suite repair before threshold sweeps treat it as a strong
  semantic probe

### 16. "`synthetic_scene_cut` wording is too strong for the current geometry-only clip"

Verdict:

- VALID (MINOR)

Evidence:

- the current clip does show an abrupt layout and color change
- the current prompt wording says `different room`, which is stronger than the
  current geometric stand-in supports

Action:

- queued for prompt or clip repair before it carries more semantic weight

### 17. "Phase 0.5 accepted the Qwen cache-liveness step too strongly"

Verdict:

- VALID

Evidence:

- the preregistered step-`5` wording required the altered cached-feature path to
  change the output
- on Qwen, output text stayed the same while logits shifted strongly
- Phase `0.75` is the stronger cache-path identity control

Action:

- Phase `0.5` note now records the Qwen step-`5` result as a caveat rather than
  a clean direct pass

### 18. "The predecessor result artifacts referenced in `seed/original_repo/results/` are missing"

Verdict:

- FALSE POSITIVE

Evidence:

- the tracked directory contains:
  - `tomato_7b_ALL_1000.json`
  - `mvbench_7b_10.json`
  - `mv_relocation_results.json`
  - `codec_native_results.json`
  - `vit_attention_results.json`
  - `h264_spatial_signals_results.json`

### 19. "Chunked subprocess execution is acceptable for Track A semantics, not for Track B timing"

Verdict:

- VALID

Evidence:

- the current Qwen pilot hit a reproducible Metal GPU timeout in a longer-lived
  process on this machine
- the current successful workaround restarts Python subprocesses in `2`-item
  chunks, which is valid for semantic paired comparisons but not for timing

Action:

- plan and note language keep the current chunking rule as an operational Track A
  constraint only

### 20. "The next reproduction tranche should prioritize direct mechanism runs, stronger local items, and content-class coverage before benchmark-native claims"

Verdict:

- VALID

Evidence:

- that order closes the current evidence gaps without pretending that TOMATO or
  MVBench are already locally reproduced
- it also keeps Track A foundation work ahead of Track B timing or benchmark
  extrapolation

Action:

- the near-term plan order now reflects this sequence
- freeze Gemma's configurable visual token budget in the initial pilot instead
  of leaving it as a hidden degree of freedom

Validated but reframed:

- the recommended `Qwen -> Gemma -> Qwen-7B` model order is a sensible local
  repo choice, not an official recommendation from the model authors
- `STATIC / SHIFTED / NOVEL` remain acceptable code labels, but docs should say
  clearly that they are proxy classes under the current RGB-diff planner
- MLX-VLM runtime support for cached image features and TurboQuant is useful
  tooling evidence, not local proof of quality-neutral composition

False positives or already addressed:

- the claimed gap around missing imported result artifacts is false in the
  current repo snapshot; the referenced JSON files are present under
  `seed/original_repo/results/`

Still future work, not executed in this commit:

- an in-memory decode path for Track B timing runs
- pad-masked reuse accounting implemented end to end in runtime code
- automated benchmark-native dataset helpers for TOMATO and MVBench

## Round 4 Validation

### 21. "The v2 pilot headline is inflated by prompt-prior or endpoint contamination"

Verdict:

- VALID

Evidence:

- the follow-up temporal-necessity ablation shows that `syn2_mid_color_flash`
  and `syn2_mid_text_flash_word` stay correct without the middle frames
- the paired item `syn2_mid_text_ever_bravo` still fails without the middle
  frames and under caching, so the contradiction is real and informative

Action:

- added [2026-04-13-phase-1_05-temporal-necessity-ablation.md](../research/experiments/2026/2026-04-13-phase-1_05-temporal-necessity-ablation.md)
- softened the v2 pilot interpretation and shifted the next-step plan toward the
  discrimination-safe subset

### 22. "Several v2 metadata flags understate endpoint solvability"

Verdict:

- VALID

Evidence:

- `syn2_flicker_change_type`, `syn2_flicker_layout`, and
  `syn2_small_object_motion` were all marked as not solvable from first and
  last frames, but the ablation showed that they are
- `syn2_color_swap_event` was marked as requiring middle frames even though the
  selected window endpoints already expose the event

Action:

- corrected the prompt-bank metadata in
  [research/prompt_bank/local_suite_v2.toml](../research/prompt_bank/local_suite_v2.toml)

### 23. "The current mechanism mismatch is more likely probe-design than conceptual disagreement"

Verdict:

- VALID

Evidence:

- the current shift probe likely crosses a token boundary at larger shifts
- the current partial-change probe is harsher than the imported whitepaper's
  intended aligned-token perturbation
- the local result remains only partial until the repaired probe passes

Action:

- the reproduction ledger and plan now point to a dedicated Phase `1.15`
  probe-repair step before broader sweeps

### 24. "Synthetic clip provenance should be locked with manifest hashes"

Verdict:

- VALID

Evidence:

- the synthetic MP4s were generated locally but the manifest did not yet record
  expected hashes

Action:

- added `expected_sha256` values for the synthetic clips and generator-side hash
  verification

### 25. "The harness issue should be treated as a real root-cause problem, not just a workaround"

Verdict:

- VALID

Evidence:

- the temporal-ablation bring-up accidentally overlapped stale workers and the
  current local harness still needs explicit stabilization before larger runs

Action:

- current semantic reruns are now being kept single-worker and sequential
- root-cause work remains queued before the benchmark-native reproduction tranche

### 26. "Sam switched from pixel diff to H.264 metadata"

Verdict:

- VALID (with scope limit)

Evidence:

- `/Users/jfb/s/codec-through-sam/whitepaper.md:347-349` states the regime split
  explicitly: pixel diff is the right default for sparse-sampled benchmark QA,
  while MV / codec metadata is the right default for native-rate streaming
- this repo already reflected part of that in `paper/framing.md` and
  `paper/claim-matrix.md`, but stale copies remained in `paper/intro.md`,
  `paper/publishability-status.md`, `research/experiments/registry.md`, and
  the manuscript sections on limitations and source traceability

Action:

- synced the paper routers and manuscript so the regime split is now explicit
- updated 1.29 language to say the semantic bridge is landed locally, while the
  remaining bridge is decoder-integrated streaming/native-rate systems evidence

### 27. "Sam evidence classes and exactness counts need sharper traceability"

Verdict:

- VALID

Evidence:

- `/Users/jfb/s/codec-through-sam/whitepaper.md` is internally inconsistent on
  the sparse exactness count: the abstract and summary use `1,937`, while the
  comparison-table and "unique contribution" prose use `1,837`
- this repo's appendix had been too coarse, collapsing Sam's streaming,
  follow-up, and live-camera rows into one traceability row
- one intro bullet and one framing-table row also over-compressed sparse
  exactness into the streaming lane

Action:

- split the manuscript traceability rows by evidence class
- separated sparse exactness from streaming/live deployment wording in the
  paper-facing docs
