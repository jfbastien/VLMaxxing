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
- [x] Add a precomputed H.264 codec-score sidecar path so Track B can separate
  model-side sparse-vision timing from one-time metadata extraction cost.
- [x] Add focused M5 launch scripts for confirmatory OneVision x VLMaxxing
  runs: Gemma N=57 transfer, Qwen kr=0.7/layer=2 parity/power, and OV-8
  setup-inclusive composition accounting.
- [x] Update preregistration, schedule, registry, and paper-facing framing with
  M3 sidecar and M5 confirmation gates before any broad run.
- [x] Run CPU and limited smoke checks only; defer long model runs to explicit
  green-light after scripts and gates are reviewed.

## Constraints

- Do not run broad GPU/model experiments without a preregistered gate. Limited
  one-item smoke tests are allowed when they validate new wiring.
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
- Keep query-aware/RLT implementation out of this branch; only record synergy
  notes for a future branch.

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
- Use M3 for sidecar building, analysis, and small smoke validation. Use M5 for
  confirmatory runs that need more memory, better thermals, or broader Gemma/Qwen
  coverage.

## Verification

This no-UV implementation pass used direct `.venv`/`python3` commands only:

- `python3 -m py_compile <modified Python modules/scripts>`
- `./.venv/bin/ruff check <modified Python/tests>`
- `./.venv/bin/python -m pytest tests/codec/test_score_sidecar.py
  tests/test_ov6_sidecar_artifacts.py tests/test_ov6_track_b_statistics.py
  tests/test_onevision_cpersist_session_accounting.py`
- `bash -n <new and modified OV-6 shell wrappers>`
- `.venv` `--help` smoke checks for new pure-CPU validators/analyzers

Repo-native full checks still normally run through the managed environment:

- `uv run ruff format --check .`
- `uv run ruff check .`
- `uv run mypy src tests`
- `uv run pytest`
- `ai-review team --stage plan` before the first code commit when available.
- `ai-review team --stage diff` before committing implementation changes when
  available.
