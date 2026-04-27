---
date: 2026-04-27
phase: 1.63E
status: preregistered; not yet run
related:
  - research/experiments/2026/2026-04-27-phase-1_63-track-b-sparse-vit-prereg.md
---

# Phase 1.63E — Track B Frame-Budget Scaling

## Question

Does the Track B arithmetic-ceiling model remain predictive as frame count
increases, or was the 8f result a single operating-point coincidence?

This phase keeps the sparse-execution scope identical to 1.63: compact
post-layer Qwen vision execution only. Dense patch embedding and early vision
blocks run through `L=2`; the remaining vision blocks run on the compact
sequence at `kr=0.50`; outputs are scattered back before the merger so the
language model still sees dense prompt geometry. This measures real skipped
ViT work, not LM-prefill sparsity.

## Protocol

- Model: `Qwen2.5-VL-7B-Instruct-4bit`.
- Manifest: `research/benchmark_manifests/videomme_combined_v1_n60.toml`.
- New frame counts: 16f, 20f, 32f.
- Reference frame count: include the landed 8f 1.63 summary if present.
- Dense arms: `scripts/run_phase1_51V.py --vision-tower-keep-rate 1.0`.
- Sparse arms: `scripts/run_phase1_51V.py --vision-tower-layer 2
  --vision-tower-keep-rate 0.50`.
- Analyzer: `scripts/analyze_phase1_63_track_b_sparse.py` per frame count.
- Scaling summary: `scripts/summarize_phase1_63_track_b_scaling.py`.
- Pairing: exact `item_id` pairing within each frame count.

## Gates

Each new frame-count cell is evaluated with the 1.63 gates:

- **H_pairing**: 60 paired items, zero parse failures in both arms.
- **H_fidelity**: sparse-minus-dense accuracy delta >= -0.05.
- **H_sparse_vision**: aggregate vision-stage time reduction >= 25%.
- **H_e2e_positive**: aggregate dense/sparse end-to-end speedup >= 1.03x.
- **H_ceiling_explained**: observed end-to-end speedup is within +/-0.05x of
  the vision-only arithmetic-ceiling prediction
  `1 / (1 - dense_vision_share * observed_vision_reduction)`.

Headline scaling PASS requires all new cells to pass H_fidelity,
H_sparse_vision, H_e2e_positive, and H_ceiling_explained. If the 8f reference
is present it is summarized but does not veto the new-cell gate, because it was
preregistered and adjudicated in 1.63.

## Interpretation

- All cells pass: C-CEILING becomes predictive across frame budgets for the
  Qwen vision-tower-only Track B path. The paper can show predicted-vs-observed
  wall-clock speedups, not only one 8f validation point.
- Sparse vision passes but E2E positivity fails at a frame count: the compact
  ViT path skips real work, but non-ViT stages dominate enough that the local
  deployment gain is not measurable there.
- Fidelity fails at higher frame counts: the C-VISION sparse path has a
  frame-depth boundary; report as a semantic boundary, not a systems failure.
- Ceiling explanation fails: the arithmetic model is incomplete for that
  operating point and the paper must state the boundary.

## Runtime And Resources

Expected local wall time on the 16 GB laptop: 6-8 h for 16f/20f/32f plus
analysis. Peak RSS should stay under the 9 GB guard because the language-model
prompt geometry remains dense and each arm runs sequentially.
