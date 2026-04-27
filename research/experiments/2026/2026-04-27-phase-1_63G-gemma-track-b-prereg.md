---
date: 2026-04-27
phase: 1.63G
status: preregistered; not yet run
related:
  - research/experiments/2026/2026-04-27-phase-1_63-track-b-sparse-vit-prereg.md
  - research/experiments/2026/2026-04-18-phase-1_51V-implementation-design.md
---

# Phase 1.63G — Gemma Track B Sparse-ViT Frame Scaling

## Question

Does Track B compact vision execution and the arithmetic-ceiling model transfer
from Qwen to Gemma across frame budgets, or is the measured sparse-ViT result
architecture-specific?

This is not a C-PERSIST experiment. It is the Gemma analogue of the Qwen 1.63
Track B MVP: execute later Gemma vision blocks on a compact token sequence,
then scatter back before the pooler/merger so the language model prompt remains
dense. The claim scope is real skipped Gemma ViT work only.

## Protocol

- Model: `gemma-4-e4b-it-4bit`.
- Manifest: `research/benchmark_manifests/videomme_combined_v1_n60.toml`.
- Frame counts: `8, 16, 32` by default.
- Dense arm: `scripts/run_phase1_63G_gemma_track_b.py
  --vision-tower-keep-rate 1.0`.
- Sparse arm: `scripts/run_phase1_63G_gemma_track_b.py
  --vision-tower-layer 2 --vision-tower-keep-rate 0.50`.
- Per-cell analyzer: `scripts/analyze_phase1_63_track_b_sparse.py` with a
  Gemma scope label.
- Scaling summary: `scripts/summarize_phase1_63_track_b_scaling.py --phase
  1.63G`.
- Pairing: exact `item_id` pairing across 60 VideoMME items.

## Gates

- **H_pairing**: every cell has 60 paired items and zero parse failures in both
  arms.
- **H_fidelity**: every cell has sparse-minus-dense accuracy delta >= -0.05.
- **H_sparse_vision**: every cell has aggregate vision-stage time reduction >=
  25%.
- **H_e2e_positive**: every cell has aggregate dense/sparse end-to-end speedup
  >= 1.03x.
- **H_ceiling_explained**: every cell's observed end-to-end speedup is within
  +/-0.05x of the vision-only arithmetic-ceiling prediction.

## Interpretation

- All gates pass across the frame-count sweep: Track B sparse-ViT evidence is
  two-architecture and frame-budget aware rather than Qwen-only.
- H_sparse_vision passes but H_e2e_positive fails: Gemma skips real vision work,
  but local overhead/stage share prevents end-to-end gain.
- H_fidelity fails: Gemma compact execution is a semantic boundary even if
  Qwen held; keep architecture-conditioned language.
- H_ceiling_explained fails: the arithmetic model is not architecture-stable.

## Runtime And Resources

Expected local wall time: ~7.5-10.5 h for the default 8f/16f/32f sweep. The
run is sequential and uses the Gemma 4-bit checkpoint, so each arm should fit
under the 9 GB RSS guard on the 16 GB laptop. If a higher-frame cell times out
or hits the guard, the outcome is a systems boundary for that operating point,
not a scientific pass.
