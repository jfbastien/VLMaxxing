# Design RLT and VLMaxxing composition experiments

## Goal

- [x] Research RLT from the local PDF, local clone, and primary online
  sources; compare it against current VLMaxxing paper claims and repo
  evidence.
- [x] Land a reviewed preregistration/design note for RLT x VLMaxxing
  composition experiments.
- [x] Validate scientist peer feedback against the repo and hard-fail Gemma
  sparse-wrapper variable-`K` masks before any adaptive RLT mask can reach it.
- [x] Close the 2026-05-19/20 cross-benchmark cost-accounting run: validate
  Claude's claims against artifacts, update the decision log / registry /
  closeout notes, and make the M5/query-aware boundaries explicit.
- [x] Add a bounded M3 cost-accounting follow-up launcher and preregistration:
  default to VideoMME-short admission keep-rate bracketing, keep broader
  MVBench/composition cells behind an explicit extended tier, and keep
  query-aware routing out of this branch.
- [x] Validate the executed M3 extended follow-up at `n=19`: accept the
  stage-cost model, mark VideoMME-short `kr=0.3/0.7` as parsed-choice clean,
  and classify MVBench/TOMATO extensions as timing or boundary evidence.
- [x] Narrow the M5 scale-confirmation wrapper to a core default, with scorer
  and full expansion available only through explicit opt-in tiers.
- [ ] Implement a small, audited RLT mask module in `src/codec_through/`
  without installing, importing, executing, or vendoring RLT's training stack
  or third-party dependencies.
- [ ] Add unit tests for RLT endpoint comparisons, first-tubelet retention,
  repeated-frame keep-rate, minimum-frame guards, run-length accounting,
  grid/order contracts, normalization-domain hard-fails, and shape checks.
- [ ] Add an offline positive-control profile on fixed-camera/repetitive clips
  resembling RLT's published evaluation domain before treating local
  `RLT-style` masks as grounded.
- [ ] Add runner timing instrumentation for canonical stages, including
  separate multimodal prefill and text generation where RLT-3G makes
  prefill-stage claims; land this as a prerequisite commit before any RLT-3G-B
  denominator-separation run.
- [ ] Wire RLT-style masks into the existing measured C-VISION Track B
  harness for Qwen and Gemma behind explicit CLI flags; label this as scorer
  substitution, not multiplier evidence.
- [ ] Add the RLT-as-free-prior experiment: test whether cheap RLT-style pixel
  masks can prefilter more expensive feature-dependent scoring, then require a
  paired model-run drift gate before any "replacement" language. Treat
  `max_min_diversity` as the current live expensive-scorer target and
  `nuwa_pillar` as rejected unless a later preregistration resurrects it.
- [ ] Add autonomous sweep runners and analyzers that reuse the existing dense
  baselines, stage-share accounting, paired fidelity gates, and artifact
  schemas. Preflight must abort before smokes if selected cells lack prefill
  split instrumentation or Gemma SWA-safe cache verification.
- [ ] Add the Gemma composition experiments in cleanly separated cells:
  scorer-stacking/union evidence and a denominator-separation cell with
  scatter-back C-VISION versus encoder-state-invariant RLT-style placeholder
  pruning.
- [ ] Add C-PERSIST experiments in two tiers: Gemma-first Q0
  shorter-cached-prefix economics after visual admission and SWA-safe cache
  semantics are verified, then conservative Qwen whole-frame RLT repair/frame
  selection scheduling; do not cut inside Qwen image-frame cache blocks until
  a separate topology contract exists.
- [ ] Add a Track A scout for duration-annotated anchors: log RLT-style run
  lengths alongside unchanged VLMaxxing structural anchors without changing
  token counts.
- [ ] Run smoke tests, unit tests, repo checks, plan/diff review, and commit
  each logical chunk.

## Constraints

- The repo protocol requires claims to be labeled as reproduced here, imported
  result, or hypothesis, and Track A semantic substitution must not be reported
  as Track B skipped work.
- RLT's reported numbers are imported/external until reproduced locally. They
  come from action-recognition VideoMAE-style models, not video VLM QA.
- Current Qwen selective re-prefill is whole-frame/cache-prefix oriented and
  intentionally rejects cuts inside image-frame token blocks. RLT token-level
  C-PERSIST surgery is out of scope for the first implementation, and Qwen
  H4A is only a coarse frame-selection scout.
- Gemma C-PERSIST is the architecture where RLT-style patch-level prefix
  shrinking is meaningful, but Gemma mixed-SWA cache semantics must be verified
  against the active `mlx-vlm` install or a checked prefix-snapshot wrapper
  before any H4A run.
- Current C-VISION scatter-back paths preserve downstream dense prompt geometry.
  They can test real skipped vision work, but not visual-token prefill
  reduction unless paired with a separate visual-admission path.
- Local implementation will initially be an RLT-style tubelet endpoint mask
  and run summary, not a full reproduction of RLT's learned length encoding or
  variable-length ViT training stack.
- RLT's faithful patch comparison uses normalized pixel/tubelet endpoint
  differences, not the repo's raw adjacent-frame RGB planner by default.
- `tau = 0.1` is meaningful only for the paper's normalized pixel domain. The
  local implementation must pin and log `mask_domain`; thresholds are not
  transferable across raw frames, Qwen processor tensors, and Gemma processor
  tensors without profiler evidence.
- The local target is an Apple 16 GB unified-memory machine. Long sweeps must
  be resumable, sequential, RSS-guarded, and checkpoint artifacts per cell.
- Do not install, execute, import from, or vendor RLT's
  CUDA/PyTorch/xformers/decord training stack. Port only a small pure
  algorithmic subset by inspection, with attribution and license preservation
  if code is copied.

## Decisions

- The first code implementation should measure composition, not assume
  multiplicative speedups. A combined arm must beat both single arms under the
  same manifest/model/hardware, pass per-bucket fidelity gates, and match an
  explicit combined stage-share timing model before any "multiplier" language
  is earned.
- C-VISION integration comes first because Qwen/Gemma already have measured
  sparse vision execution and paired analyzers, but it is a scorer/substitution
  test rather than the primary multiplier test.
- Gemma evidence should run first, before Qwen, because it is the cleanest
  local measured C-VISION cell and has the safer placeholder-pruning path.
- Gemma visual admission is the first candidate for denominator separation
  from scatter-back C-VISION, but existing novelty-pruning runners can already
  combine placeholder pruning and C-VISION; label that as scorer-stacking
  unless the arm protocol cleanly separates stages.
- Qwen C-PERSIST has two possible RLT roles. Q0 cache shrinking is the more
  interesting multiplier hypothesis but depends on safe visual admission;
  whole-frame repair scheduling is the conservative fallback. A partial
  image-token cache path is a separate systems project.

## Verification

- `ai-review team --stage plan`
- sub-agent plan review focused on science, denominator accounting, and
  implementation risk
- `ai-workflow run-checks`
- `uv run --group vlm pytest tests/test_pruned_vision_tower.py`
- `uv run pytest tests/test_qwen_vision_pruning.py tests/test_novelty_pruning.py tests/test_qwen_selective_reprefill.py`
- new RLT mask unit tests after implementation
- smoke run with `--n-items 1` before any long autonomous experiment
- paired analyzer output for every Track B cell before interpreting results
