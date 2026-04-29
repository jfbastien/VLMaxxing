# Sam scale-out bundle — M5 / 26B / 2026-04-29

Bundle following the contract in
[`research/experiments/2026/2026-04-29-sam-scaleout-handoff.md`](../../2026-04-29-sam-scaleout-handoff.md)
and the operator prompt at
[`research/experiments/2026/2026-04-29-sam-scaleout-operator-prompt.md`](../../2026-04-29-sam-scaleout-operator-prompt.md)
(operator prompt was deleted from `main` in `73fb023` for release tightening;
restored on this work branch from blob `4710f44` for reproducibility).

## Hardware / Runtime

- M5 Max MacBook Pro, 128 GB unified memory
- Darwin 25.4.0 (macOS 16-equivalent)
- Python 3.14.3
- mlx 0.31.1 / mlx-lm 0.31.2 / mlx-vlm 0.4.4 / transformers 5.5.4
- Model: `google/gemma-4-26B-A4B-it`
  (HF snapshot `7d4c97e54145f8ffd1a4dd1b4986a5015a517842`; native BF16; 30
  layers, 25 sliding-window + 5 full-attention)

The 12 GB MLX memory cap from local jfb runs is **not** applied here.

## Final phase ledger

| phase | file(s) | status | gate | findings doc |
|---|---|---|---|---|
| **B0b** | `sam_b0b_cache_correctness.jsonl` (42 rows) | **closed-arch-blocked** | **FAIL** (16/21 cross_turn_warm text-different; within-turn 21/21 pass) | [`2026-04-29-phase-B0b-…`](../../2026-04-29-phase-B0b-sam-cache-correctness-findings.md) |
| **B1** | `sam_b1_cpersist_replication.jsonl` | **blocked** by B0b | n/a | n/a |
| **B2** | `sam_b2_many_turn_horizon.jsonl` | **blocked** by B0b | n/a | n/a |
| **B3** | `sam_b3_streaming_baselines.jsonl` (88 rows) | **closed-earned (protocol) / closed-partial (sam_policy)** | **PASS** | [`2026-04-29-phase-B3-…`](../../2026-04-29-phase-B3-sam-streaming-baselines-findings.md) |
| **B4** | `sam_b4_sparse_vit_ceiling.jsonl` | **not run** (no sparse-ViT execution path on this 26B stack; "dense-with-zeros" is not Track B per the operator prompt) | n/a | n/a |
| **B5** | `sam_b5_s4_accuracy_1937.jsonl` (1937 rows) + `sam_b5_s4_raw_paired_513.jsonl` (513 rows) | **closed-earned** | **PASS** (both) | [`2026-04-29-phase-B5-…`](../../2026-04-29-phase-B5-sam-s4-reexport-findings.md) |
| **bundle** | `sam_scaleout_bundle_validation.json` | overall fails on B0b (intentional; that is the gate), other phases clean | n/a | (this README) |

## Headline results

- **B0b** confirms the mlx-vlm 0.4.4 `PromptCacheState` cross-turn cache
  bug at scale on Gemma 4 26B-A4B (76% text-different on cross-turn;
  100% byte-identical on within-turn). C-PERSIST numbers in the
  sdamico whitepaper §2.13.3 stand as **wall-clock** results but cannot
  stand as **correctness-preserving** results without a SWA-aware
  cache-trim fix in mlx-vlm or a custom wrapper that only persists KV
  for the 5 full-attention layers.
- **B3** delivers reviewer-defense streaming-baseline numbers at
  matched 4-frame evidence budget on twitter + terminal scrolls.
  Per-arm match-vs-fresh-oracle: `low_fps_dense` 77.3 % (strongest),
  `screenshot_polling` 59.1 %, `sam_policy` (proxy) 59.1 %,
  `recency_last_k` 54.5 %. The codec-through value lives on the
  *throughput axis* (E3, sdamico/codec-through `6594a7b` —
  22–64× ViT reduction at matched temporal coverage), **not** at
  matched-fixed-evidence budget. Section assignment in
  `paper/arxiv/sections/08_real_applications.tex` should pair the two
  axes explicitly.
- **B5** re-exports the S4 evidence as two bounded artifacts with
  schema-compliant provenance: `S4_zero_acc_delta_1937` (1937/1937
  pass) and `S4_byte_identical_513` (513/513 pass). The "byte-identical
  on 1,937" form previously cited in the sdamico whitepaper at lines
  9 / 11 / 766 is *not* supported by these artifacts and must be
  reduced to 513 or qualified as loose-match.

## Source

Imports from `sdamico/codec-through @ 6594a7b` for the original S0 / S4
/ E3 findings. This bundle re-runs / re-exports each piece against the
`sam_scaleout_artifact_v1` schema so it can be imported as same-graph
evidence rather than companion material.
