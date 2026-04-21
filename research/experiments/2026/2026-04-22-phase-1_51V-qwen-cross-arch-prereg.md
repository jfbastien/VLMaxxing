---
phase: 1.51V
date: 2026-04-22
parent: research/experiments/2026/2026-04-18-phase-1_51V-vision-tower-pruning-prereg.md
prior:
  - research/experiments/2026/2026-04-21-phase-1_51V-exp10-n60-findings.md
  - paper/priority.md (should-do #3 "1.51V cross-architecture transfer probe")
status: preregistration 2026-04-22. Doc-only; implementation deferred (impl blocker documented below).
tracking: autonomous session 2026-04-21/22 dynamic-loop
---

# 1.51V Qwen cross-architecture transfer probe — preregistration

## Headline question

Does the scatter-back vision-tower pruning ceiling `E2E ≤ 1/(1 − V_share × V_red)`
— validated on Gemma 4-E4B-4bit at `L=2`, `kr_V=0.50` across 5 benchmark
cells — transfer to a *second* architecture (Qwen 2.5-VL-7B-4bit), at
matched `(L, kr_V)` and matched benchmark slice?

If yes: C-VISION stops being a single-architecture mechanism and becomes a
mechanism-class claim. Per Codex round-27, this is the highest-value next
result for the current paper.

If no: the falsification is interesting in its own right. It tells us the
ceiling law has architecture-dependent limits; we document what broke
(e.g. ceiling violated because Qwen's window-attention routing changed V_red
semantics, or because V_share on Qwen is too small for the prediction to
be distinguishable from noise).

## Design

**Architecture under test.** `mlx-community/Qwen2.5-VL-7B-Instruct-4bit`
(same model family as the 1.41 / 1.55A / 1.57 runs, so baseline VideoMME
8f accuracy is already known: dev n=30 aggregate ≈ 0.700).

**Pruning locus.** *Inside* Qwen's `VisionModel` at layer `L=2`,
magnitude-keep rate `kr_V=0.50`. Scatter-back to full length **before**
`self.merger` so the downstream LM prefill sees the same visual token
count as the dense path. This mirrors Gemma's `pruned_vision_tower.py`
contract: the ceiling law is a claim about ViT-transformer compute
reduction, not about LM prefill reduction.

**Benchmark.** VideoMME dev n=30, 8 frames, thermally-paired
patched/unpatched, identity frame cache, `videomme_dev_v1.toml`.

**Measurement.** Per-item: `V_wall` (vision-tower forward wall-clock),
`E2E_wall`, `prefill_tokens`, correctness. Aggregate V_share =
sum(V_wall) / sum(E2E_wall) across dense arm; V_red = 1 − sum(V_wall_pruned) / sum(V_wall_dense).

### Hypotheses

| ID       | Claim                                                    | Pre-registered gate                                     |
|----------|----------------------------------------------------------|---------------------------------------------------------|
| H_qwen_Vred | V_red in [0.35, 0.50]                                 | Mirrors Gemma's 39–43% at L=2 kr=0.50.                  |
| H_qwen_E2E  | E2E speedup within 15 % of `1/(1 − V_share × V_red)` | Ceiling-law transfer; matches Gemma paper-body 5.2 % envelope at looser gate for cross-arch first point. |
| H_qwen_acc  | `|Δacc| ≤ 0.10` aggregate                            | Matches the per-item 10 pp gate used across 1.51V Gemma cells. |

Any hypothesis missing its gate is reported as such — no silent falsification,
no soft-pass. If `V_share` on Qwen is < 0.05 (i.e. ViT compute is
~imperceptible on this architecture), H_qwen_E2E becomes trivially
unfalsifiable (the predicted ceiling collapses to ≈ 1.00×); we report the
V_share measurement and treat H_qwen_E2E as VACUOUS rather than as a pass.

### Non-hypotheses

- **This probe does NOT test cross-benchmark transfer on Qwen.** One
  benchmark × one frame count × one (L, kr) cell. Scaling to MVBench /
  TOMATO on Qwen is a follow-up if this one lands clean.
- **This probe does NOT test cross-`kr` transfer on Qwen.** If this
  lands clean at `kr=0.50`, an 8f kr sweep on Qwen would be a natural
  next probe; if it fails, the kr sweep does not rescue the headline.

## Implementation plan (impl-blocked, scoped here)

The existing `src/codec_through/pruned_vision_tower.py` is
Gemma-only. Qwen's `VisionModel.__call__` differs in three non-trivial
ways that require new plumbing:

1. **Flat `[seq_len, hidden]` token layout (no batch dim).** Post-`patch_embed`,
   Qwen's ViT operates on a single flat 2D tensor; `cu_seqlens` arrays
   carry the per-frame / per-window boundaries. Gemma's `[B, L, D]` slice
   helpers in `_slice_keep` / `_scatter_back` do not apply directly.

2. **Dual boundary arrays: `cu_seqlens` AND `cu_window_seqlens`,**
   selected per block by `fullatt_block_indexes`. If we prune tokens
   after layer `L` and run remaining blocks on a compact sequence, *both*
   arrays must be recomputed consistently on the compact layout.

3. **`spatial_merge_unit = 4` alignment constraint at the merger.**
   Post-all-blocks, `self.merger` reshapes groups of 4 adjacent tokens
   and projects to LM hidden dim; `reverse_indices` then undoes the
   `window_index` permutation. If we prune tokens that *split* a
   spatial_merge_unit group, the merger collapses a partially-zero
   group and the resulting token vector is no longer pool-geometry-equivalent
   to the dense path — a silent accuracy confound.

### Proposed implementation (not yet landed)

- **Keep-mask granularity: spatial_merge_unit-aligned groups of 4,
  scored by L2 magnitude of the mean-hidden-state of the group.** This
  sidesteps constraint (3) by construction — either a whole group
  survives or a whole group is pruned.
- **Per-frame uniform keep count.** For each frame, keep `(tokens_in_frame × kr_V) / 4`
  groups by magnitude (rounded to avoid non-divisible edge cases). This
  makes `cu_seqlens` recomputation a simple `× kr_V` rescaling per-frame.
- **Window-local pruning for `cu_window_seqlens`.** Enforce that each
  window chunk keeps exactly `(chunk_groups × kr_V)` groups so
  `cu_window_seqlens` also rescales cleanly per-window. Each window is
  pruned independently against its own magnitudes.
- **Scatter-back immediately before `self.merger`.** Compact sequence
  after layer `L` runs through blocks `L+1 … N−1`; then we scatter back
  to the original `seq_len` (zero-filled at pruned positions) and let
  `self.merger` + `reverse_indices` produce LM-ready tokens of the same
  count as the dense path.

### Impl effort estimate

~4–6 h. Breakdown: 1 h wrapper scaffolding (`QwenVisionPruneWrapper`
mirroring `_PrunedEncoderWrapper`), 1.5 h cu_seqlens/cu_window_seqlens
recomputation + alignment unit tests, 1.5 h parity-check vs dense
path at `kr=1.0` (should be bit-identical), 1 h CPU smoke test on a
single short VideoMME clip to catch merger-shape asserts, 1 h slack
for MLX-specific JIT recompilation issues (K must be invariant across
calls).

### Scheduling blocker

Not runnable in the current AFK session window without the 4–6 h
implementation time. Queued for Priority 1 of the next coding session;
this prereg locks the design so execution is a pure implementation
task.

## Reproduction (when impl lands)

```
uv run python scripts/run_phase1_51V.py \
    --model mlx-community/Qwen2.5-VL-7B-Instruct-4bit \
    --benchmark videomme \
    --split dev \
    --n 30 \
    --frame-count 8 \
    --prune-layer 2 \
    --keep-rate 0.50 \
    --anchor none \
    --thermal-pair \
    --out research/experiments/2026/artifacts/phase1_51V_qwen_videomme_dev30/
```

Depends on a new `--model` dispatch path in `scripts/run_phase1_51V.py`
that routes to `QwenVisionPruneWrapper` vs `patch_vision_tower` (Gemma)
based on `model.config.model_type`.

## Claim-matrix target

Row 15 (C-VISION). If H_qwen_Vred AND H_qwen_E2E AND H_qwen_acc all
pass, C-VISION moves from "single-architecture mechanism (Gemma 4-E4B-4bit)"
to "two-architecture mechanism (Gemma + Qwen 2.5-VL-7B-4bit)". If
H_qwen_E2E is VACUOUS (V_share < 0.05), C-VISION stays single-arch with
an explicit "Qwen 7B ViT share is too small for the ceiling-law prediction
to be distinguishable from measurement noise" caveat.

## Framing (JF voice draft for the eventual findings doc)

Gemma's vision share is about a third of end-to-end time on short-bucket
VideoMME 8f; that's the geometry where the ceiling law makes its sharpest
prediction. Qwen 2.5-VL-7B-4bit has a larger LM and a comparable ViT, so
V_share will be smaller — probably between 5 % and 15 %. The question is
whether the ceiling law still matches the measured E2E within its error
bar at that smaller V_share, or whether smaller V_share exposes a
second-order term we've been ignoring. Either answer is useful.

## Falsified-hypotheses ledger

No pre-commit entries. If the experiment runs and falsifies any gate,
the corresponding entry lands in `research/falsified-hypotheses.md`
against this prereg.
