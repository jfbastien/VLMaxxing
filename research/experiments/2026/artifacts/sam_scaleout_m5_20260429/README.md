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
| **B1** | `sam_b1_cpersist_replication.jsonl` (42 rows) | **closed-arch-blocked (diagnostic)** | gate-pass on numbers, ~80% text-divergence | [`2026-04-29-phase-B1-…`](../../2026-04-29-phase-B1-sam-cpersist-replication-findings.md) |
| **B2** | `sam_b2_many_turn_horizon.jsonl` (450 rows) | **closed-arch-blocked (diagnostic)** | adaptive arm passes ≤3% drift gate at horizon=50, but at 0.84× speedup | [`2026-04-29-phase-B2-…`](../../2026-04-29-phase-B2-sam-many-turn-horizon-findings.md) |
| **B3** | `sam_b3_streaming_baselines.jsonl` (88 rows) | **closed-earned (protocol) / closed-partial (sam_policy)** | **PASS** | [`2026-04-29-phase-B3-…`](../../2026-04-29-phase-B3-sam-streaming-baselines-findings.md) |
| **B4** | `sam_b4_sparse_vit_ceiling.jsonl` (10 rows) | **closed-arch-blocked** (strict B4) / **closed-negative** (post-ViT hard-prune at fixed frames) | non-conformant; **8f median 0.757× (slower); 32f median 1.042× (essentially flat); 0/10 byte-identical** | [`2026-04-29-phase-B4-…`](../../2026-04-29-phase-B4-sam-track-b-hard-prune-findings.md) |
| **B5** | `sam_b5_s4_accuracy_1937.jsonl` (1937 rows) + `sam_b5_s4_raw_paired_513.jsonl` (513 rows) | **closed-earned** | **PASS** (both) | [`2026-04-29-phase-B5-…`](../../2026-04-29-phase-B5-sam-s4-reexport-findings.md) |
| **bundle** | `sam_scaleout_bundle_validation.json` | overall fails on B0b (intentional; that is the gate), B3+B5 pass cleanly | n/a | (this README) |

## Headline results — all framed on the right axis (effective frame rate at fixed compute, not query latency)

- **The cache mechanism does not deliver a frames-at-fixed-compute gain
  at deployment-grade quality on Gemma 4 26B / mlx-vlm 0.4.4.** Three
  policies tested across B0b/B1/B2; no operating point gets both
  correctness and speedup simultaneously:
  - rebuild-from-setup-per-turn: 28× speedup, 33–67 % wrong on hard
    questions (content-conditional reliability)
  - cumulative-cache adaptive: 99 % correct, 0.84× speedup (slower
    than dense due to `PromptCacheState` cache-growth pathology)
  - scheduled refresh: 90–93 % correct, 0.83× speedup
  Root cause is the same SWA / RotatingKVCache class JF flagged in
  1.55C/1.55D, now reproducing at 26B scale. Fresh-cache cross-turn
  reuse is unsafe; cumulative-context same-question polling
  self-corrects after turn 0 but loses speedup.
- **Streaming cache at the ViT-fire-rate level DOES deliver frames at
  fixed compute** — see E3 (sdamico/codec-through `6594a7b`):
  22–64× ViT-fire reduction at matched temporal coverage, ~30 fps
  effective perception vs 0.015–0.045 fps for polling baselines at the
  same ViT cost. **This is the headline frame-rate-at-fixed-compute
  claim; the C-PERSIST follow-up cache is a different mechanism that
  does not deliver this on this stack.**
- **Hard-prune (B4-adjacent) is a flat-or-negative result at fixed
  frames** on this stack. Measured median speedups are 8f: **0.757×
  (slower; 30% overhead from the post-ViT prune cascade)**, 32f:
  **1.042× (essentially flat)**, with 0/10 byte-identical paired
  rows. The artifact does NOT support a "1.5× ingestion-density"
  reframe — that axis assumes you'd use the saved prefill budget to
  push more frames at fixed wall-clock, but the only data we collected
  is fixed-frame query speedup, where the headline number is 1.042×.
  Future work could test the ingestion-density framing by actually
  running 48f-pruned vs 32f-dense at matched compute; until then,
  this is non-conformant Track B (post-ViT hard-prune ≠ sparse-ViT)
  with a flat-to-negative observed speedup.
- **B3 streaming baselines.** At matched 4-frame evidence budget,
  `low_fps_dense` 77.3 % > `sam_policy_proxy` 59.1 % ≈
  `screenshot_polling` 59.1 % > `recency_last_k` 54.5 %. **Reviewer-
  defense framing:** the matched-evidence-budget axis is not the
  axis on which codec-through wins; the throughput axis (above) is.
  Pair the two axes explicitly in `paper/arxiv/sections/08_real_applications.tex`.
- **B5 S4 re-export.** The "byte-identical on 1,937" claim must be
  reduced to **513 paired-response items** or qualified as
  loose-match on the 1,484-TOMATO subset. The `0 acc-delta on 1,937`
  claim survives in full (paired-bootstrap CI [0, 0]).

## Composition story (orthogonal mechanisms)

The two cache levels and the prune mechanism compose orthogonally:

| mechanism | axis | what it caps | measured factor on this stack |
|---|---|---|---|
| streaming cache (E3) | ViT-fire-rate | how often the ViT fires per second of video | **22–64×** ViT reduction at matched temporal coverage |
| hard-prune (B4-adj) | per-prompt prefill tokens | how many visual tokens enter the LLM per query | **flat-to-negative** at fixed frames on this stack: 8f 0.757×, 32f 1.042×; ingestion-density reframe is not supported by the collected artifact (would require fixed-wall-clock variable-frames experiment) |
| C-PERSIST (B0b/B1/B2) | per-query LLM prefill amortization | repeat-the-prompt-prefix cost across queries | **0×** at deployment-grade quality on this stack (broken cross-turn cache) |

**Combined paper claim should be:** "more frames at fixed compute,
primarily via ViT-fire-rate reduction (E3, 22-64× at matched
temporal coverage). Per-prompt prefill-token reduction (hard-prune)
is flat-to-negative on this stack at fixed frames; the
ingestion-density reframe is a hypothesis that would need its own
fixed-wall-clock variable-frames experiment to confirm. The
C-PERSIST follow-up axis does not contribute to deployment-grade
speedup on Gemma 4 26B until the SWA-aware cache fix lands."

## Source

Imports from `sdamico/codec-through @ 6594a7b` for the original S0 / S4
/ E3 findings. This bundle re-runs / re-exports each piece against the
`sam_scaleout_artifact_v1` schema so it can be imported as same-graph
evidence rather than companion material.
