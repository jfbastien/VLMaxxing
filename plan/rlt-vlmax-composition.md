# Design RLT and VLMaxxing composition experiments

## Goal

- [x] Research RLT from the local PDF, local clone, and primary online
  sources; compare it against current VLMaxxing paper claims and repo
  evidence.
- [x] Land a reviewed preregistration/design note for RLT x VLMaxxing
  composition experiments.
- [ ] Implement a small, audited RLT mask module in `src/codec_through/`
  without vendoring RLT's training stack or third-party dependencies.
- [ ] Add unit tests for RLT endpoint comparisons, first-tubelet retention,
  run-length accounting, grid/order contracts, and hard-fail shape checks.
- [ ] Wire RLT-style masks into the existing measured C-VISION Track B
  harness for Qwen and Gemma behind explicit CLI flags; label this as scorer
  substitution, not multiplier evidence.
- [ ] Add autonomous sweep runners and analyzers that reuse the existing dense
  baselines, stage-share accounting, paired fidelity gates, and artifact
  schemas.
- [ ] Add the primary Gemma 2x2 composition experiment: dense, C-VISION-only,
  RLT-style visual-admission-only, and C-VISION + RLT-style visual admission
  on the same manifest/model/frame count/order.
- [ ] Add a conservative C-PERSIST scheduler experiment where RLT controls
  whole-frame repair decisions only; do not cut inside Qwen image-frame cache
  blocks until a separate topology contract exists.
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
  C-PERSIST surgery is out of scope for the first implementation.
- Current C-VISION scatter-back paths preserve downstream dense prompt geometry.
  They can test real skipped vision work, but not visual-token prefill
  reduction unless paired with a separate visual-admission path.
- Local implementation will initially be an RLT-style tubelet endpoint mask
  and run summary, not a full reproduction of RLT's learned length encoding or
  variable-length ViT training stack.
- RLT's faithful patch comparison uses normalized pixel/tubelet endpoint
  differences, not the repo's raw adjacent-frame RGB planner by default.
- The local target is an Apple 16 GB unified-memory machine. Long sweeps must
  be resumable, sequential, RSS-guarded, and checkpoint artifacts per cell.
- Do not vendor RLT's CUDA/PyTorch/xformers/decord training stack. Port only a
  small pure algorithmic subset if the plan is accepted.

## Decisions

- The first code implementation should measure composition, not assume
  multiplicative speedups. A combined arm must beat both single arms under the
  same manifest/model/hardware and match an explicit combined stage-share
  timing model before any "multiplier" language is earned.
- C-VISION integration comes first because Qwen/Gemma already have measured
  sparse vision execution and paired analyzers, but it is a scorer/substitution
  test rather than the primary multiplier test.
- Gemma visual admission is the first candidate for attacking a different
  denominator from C-VISION because existing placeholder-pruning machinery
  already validates image-token alignment.
- Qwen C-PERSIST will initially use RLT as a whole-frame repair scheduler. A
  partial image-token cache path is a separate systems project.

## Verification

- `ai-review team --stage plan`
- sub-agent plan review focused on science, denominator accounting, and
  implementation risk
- `ai-workflow run-checks`
- `uv run pytest tests/test_qwen_vision_pruning.py tests/test_novelty_pruning.py tests/test_qwen_selective_reprefill.py`
- new RLT mask unit tests after implementation
- smoke run with `--n-items 1` before any long autonomous experiment
- paired analyzer output for every Track B cell before interpreting results
