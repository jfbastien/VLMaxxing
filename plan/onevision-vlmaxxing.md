# OneVision + VLMaxxing research plan

## Goal

- [x] Record primary-source OneVision research and a falsifiable
  VLMaxxing integration plan without editing manuscript prose.
- [x] Add a clean-room CPU-only OneVision-style codec patchification module
  with unit tests for budget allocation, anchors, temporal coverage, and
  spatial-bias diagnostics.
- [x] Add an autonomous experiment-runner plan that schedules OneVision
  reproduction, VLMaxxing+OneVision ablations, and visualization generation
  sequentially with no concurrent GPU/model use.
- [x] Add or extend visualization tooling for OneVision-style token allocation
  and combined reused/fresh/codec-selected tile views, runnable as dry-run or
  metadata-only without local benchmark videos.
- [x] Run repo checks that do not start model inference or GPU-heavy work.

## Constraints

- Do not run GPU/model experiments in this session; the user is already using
  the machine for experiments.
- Target local feasibility first on an M3 MacBook Air with 16 GB RAM, while
  separating any M5 128 GB or NVIDIA/cluster follow-up plan.
- Treat OneVision primary claims as external until reproduced here; label new
  claims as `hypothesis`, `imported result`, or `reproduced here`.
- Keep Track A semantic substitution, Track B real skipped work, and
  after-ingest C-PERSIST denominators separate.
- Read OneVision paper/code for specification only. Reimplement cleanly in
  this repo; do not vendor or copy their implementation.
- Do not modify paper manuscript files in this branch. Add a later editor
  feedback phase to the experiment plan instead.

## Decisions

- Reproduce the codec patchification algorithm first, not OneVision's trained
  benchmark scores. Full score reproduction appears to require large-scale
  training/fine-tuning and multi-GPU evaluation; the local first step is
  algorithmic equivalence and planner-level ablations.
- Treat codec motion/residual scores as freshness or uncertainty signals for
  VLMaxxing unless a task-level paired test shows semantic selection value.
- Use existing repo videos/manifests and Qwen/Gemma local model lanes in the
  experimental plan; add M5/cluster lanes only when they answer questions the
  M3 cannot.

## Verification

- `uv run ruff format --check .`
- `uv run ruff check .`
- `uv run mypy src tests`
- `uv run pytest`
- `ai-review team --stage plan` before the first code commit when available.
- `ai-review team --stage diff` before committing implementation changes when
  available.
