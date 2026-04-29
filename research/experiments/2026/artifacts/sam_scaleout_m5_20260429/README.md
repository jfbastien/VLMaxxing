# Sam scale-out bundle — M5 / 26B / 2026-04-29

Bundle following the contract in
[`research/experiments/2026/2026-04-29-sam-scaleout-handoff.md`](../../2026-04-29-sam-scaleout-handoff.md)
and the operator prompt restored at
[`research/experiments/2026/2026-04-29-sam-scaleout-operator-prompt.md`](../../2026-04-29-sam-scaleout-operator-prompt.md)
(operator prompt was deleted from `main` in `73fb023` for release tightening;
restored here on the work branch from blob `4710f44` for reproducibility).

## Hardware / Runtime

- M5 Max MacBook Pro, 128 GB unified memory
- Darwin 25.4.0 (macOS 16-equivalent)
- Python 3.14.3
- mlx 0.31.1 / mlx-lm 0.31.2 / mlx-vlm 0.4.4 / transformers 5.5.4
- Model: `google/gemma-4-26B-A4B-it`
  (HF snapshot `7d4c97e54145f8ffd1a4dd1b4986a5015a517842`; native BF16; 30
  layers, 25 sliding-window + 5 full-attention; matches S0 provenance)

The 12 GB MLX memory cap from local jfb runs is **not** applied here.

## Phase ledger

| phase | file | status |
|---|---|---|
| B0b | `sam_b0b_cache_correctness.jsonl` | pending |
| B1  | `sam_b1_cpersist_replication.jsonl` | gated on B0b pass |
| B2  | `sam_b2_many_turn_horizon.jsonl` | gated on B0b pass |
| B3  | `sam_b3_streaming_baselines.jsonl` | pending |
| B4  | `sam_b4_sparse_vit_ceiling.jsonl` | not run (no sparse-ViT path on the 26B stack) |
| B5  | `sam_b5_s4_accuracy_1937.jsonl` + `sam_b5_s4_raw_paired_513.jsonl` | pending |
| bundle | `sam_scaleout_bundle_validation.json` | pending |

Artifacts and findings notes land here as each phase completes. Ledger above
is updated in the same commit as the artifact lands.

## Source

Imports from `sdamico/codec-through` @ `6594a7b` for the original S0 / S4 / E3
findings. This bundle re-runs / re-exports each piece against the
`sam_scaleout_artifact_v1` schema so it can be imported as same-graph evidence
rather than companion material.
