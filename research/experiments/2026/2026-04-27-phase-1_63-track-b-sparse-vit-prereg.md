---
date: 2026-04-27
phase: 1.63
status: preregistered; not yet run
related:
  - research/experiments/2026/2026-04-17-phase-1_50-track-b-dense-baseline.md
  - research/experiments/2026/2026-04-23-phase-1_51V-qwen-cross-arch-findings.md
---

# Phase 1.63 — Track B Compact Qwen ViT Execution

## Question

Does the C-VISION Qwen policy that preserves answer quality also skip real
vision-tower work, and does the observed end-to-end speedup match the
arithmetic ceiling implied by the dense vision-stage share?

This is the minimal Track B MVP. It is not a new sparse-prefill system. It
uses the already-validated Qwen compact post-layer vision path:

1. dense patch embedding and early vision blocks through layer `L=2`,
2. select merged-token groups at `kr=0.50`,
3. execute the remaining vision blocks on the compact group sequence,
4. scatter back before the merger so the language model still sees dense
   prompt geometry.

Therefore this phase measures **real skipped ViT work** while explicitly not
claiming prefill-token reduction.

## Protocol

- Model: `Qwen2.5-VL-7B-Instruct-4bit`.
- Manifest: `research/benchmark_manifests/videomme_combined_v1_n60.toml`.
- Frame count: 8.
- Dense arm: `scripts/run_phase1_51V.py --vision-tower-keep-rate 1.0`.
- Sparse arm: `scripts/run_phase1_51V.py --vision-tower-layer 2
  --vision-tower-keep-rate 0.50`.
- Analyzer: `scripts/analyze_phase1_63_track_b_sparse.py`.
- Pairing: exact `item_id` pairing across the 60 VideoMME items.

## Gates

- **H_pairing**: 60 paired items, zero parse failures in both arms.
- **H_fidelity**: sparse-minus-dense accuracy delta ≥ -0.05.
- **H_sparse_vision**: aggregate vision-stage time reduction ≥ 25%.
- **H_e2e_positive**: aggregate dense/sparse end-to-end speedup ≥ 1.03×.
- **H_ceiling_explained**: observed end-to-end speedup is within ±0.05× of the
  vision-only arithmetic-ceiling prediction
  `1 / (1 - dense_vision_share * observed_vision_reduction)`.

## Interpretation

- H_fidelity + H_sparse_vision + H_e2e_positive + H_ceiling_explained:
  C-VISION becomes measured Track B evidence, not only Track A semantic
  evidence. The paper can say the sparse path reaches the local vision-only
  ceiling within tolerance.
- H_fidelity + H_sparse_vision but not H_e2e_positive: the policy skips real
  vision work, but overhead or decode/prefill dominance absorbs the win. This
  is still a useful systems boundary.
- H_fidelity fails: semantic transfer from prior 1.51V cells did not reproduce
  in the fresh paired Track B run; use the run as a boundary result.
- H_ceiling_explained fails with positive E2E: the arithmetic model is
  incomplete and the paper should not over-use it for Track B claims.

## Runtime And Resources

Expected wall time on the local 16 GB laptop:

- dense n=60 arm: ~1.4-1.6 h
- sparse n=60 arm: ~1.3-1.5 h
- analysis: <1 min
- total: ~2.8-3.2 h

Peak RSS should stay under the 9 GB guard because the run uses the same Qwen
7B-4bit 8f geometry as prior 1.51V cells.
