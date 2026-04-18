---
title: Phase 1.51V implementation design note
date: 2026-04-18
status: design
---

# Phase 1.51V implementation design

**Purpose.** Lock in the mechanical choices for vision-tower-internal
pruning before writing code. Companion to
`2026-04-18-phase-1_51V-vision-tower-pruning-prereg.md`.

## Code structure

### Target file

`src/codec_through/pruned_vision_tower.py` — CPU-independent module
exposing:

```python
def patch_vision_tower(model, layer_idx: int, keep_mask_fn):
    """Monkey-patch model.vision_tower.encoder with a pruned variant.

    layer_idx: apply keep mask AFTER this layer (0..num_hidden_layers-1)
    keep_mask_fn: callable(hidden_states, positions) -> bool mask [B, L]
    """
```

### Integration point

`scripts/run_novelty_pruning_gemma.py` currently calls the vision
tower at lines 345-350 / 414-417. Add a `--vision-tower-layer` and
`--vision-tower-keep-rate` CLI pair; patch once after model load and
before the per-item loop.

### StageTimings dataclass extension

Add two fields at lines 170-189:

- `vision_tower_ms_dense: float`
- `vision_tower_ms_pruned: float`

Instrumented in the same way we time `_generate` today. Measure V by
wrapping `model.vision_tower(pixel_values)` in `mx.eval` + `perf_counter`.

## Architectural constraint: pool geometry

The pooler uses `k = int((input_seq_len // output_length) ** 0.5)`
and `k_squared = k**2` to normalize the weighted average. At 8 frames
with 1024×1024 input and patch size 14:

- `max_patches = default_output_length * pooling_kernel_size**2 =
  256 * 4**2 = 4096`.
- `k = 4`, so each output cell averages a 4×4 kernel of patches.

**If we slice hidden_states mid-tower, input_seq_len drops and k
changes.** k=3 or k=2 would remap patches into different output cells,
breaking the pool operation.

### Solution: slice-then-scatter-back

1. At layer L, compute `keep_mask` of shape `[B, L_full]` (bool).
2. Run remaining layers (L+1..N) on only the kept tokens. Gather
   positions + attention mask alongside.
3. Before returning from the encoder, **scatter kept tokens back to
   their original positions in a zero-filled `[B, L_full, d]` tensor**.
4. The pooler operates on L_full as usual, with zeros at the
   pruned positions. The weighted average still divides by `k**2`, so
   pruned cells contribute 0; in practice the pool output at a cell
   with p of k² kept patches is `(kept_sum / k²)` vs dense
   `(all_sum / k²)` — a scale factor of `p/k²`.

### Scale-correction

After pool, multiply each output cell by `k² / p_cell` where
`p_cell` is the number of kept patches mapped to that cell. This
preserves magnitude regardless of prune pattern. Two details:

- Cells with `p_cell == 0` (all patches pruned) are left at zero —
  no information, so any correction is undefined. Downstream LLM sees
  a zero token; this is intentional (pruning signal = "skip").
- Compute `p_cell` from the same one-hot `weights` tensor: sum over
  the input axis after masking by `keep_mask`.

### Alternative considered: FlexAttention-style no-scatter

Keep the sequence compact (no scatter-back) and provide a pool that
works on variable length. Rejected because:

- Pooler is a library class from `mlx_vlm`. Rewriting it risks
  subtle bugs in weight normalization.
- Scatter-back is O(L_full × d) memcpy, negligible vs the transformer
  FLOPs savings.

## Keep-mask source

For the first implementation, use a **magnitude-based keep-mask
computed at layer L**:

```python
# scores: L2 norm of hidden_states along d
scores = mx.linalg.norm(hidden_states, axis=-1)  # [B, L_full]
keep = top_k_per_batch(scores, k=int(L_full * keep_rate))
```

**Rationale.** Layer-L activation magnitude correlates with "how much
this token attended" and is free (no separate signal). Matches the
SigLIP-style pruning literature.

The 1.51R pixel-novelty signal is computed **pre-vision-tower** and
is per-frame, not per-patch. It cannot directly supply a per-patch
keep mask without a spatial-aware extension. Deferred to a follow-up:
use pixel-novelty as a **frame-level gate** (skip entire frames) and
magnitude as a **patch-level gate** (within kept frames).

## Pilot: smoke test acceptance

1. Pick a single VideoMME long item.
2. Run dense: record `vision_tower_ms_dense`, final `hidden_states`
   shape, first-token L2.
3. Run pruned @ L=1, kr=0.5: record `vision_tower_ms_pruned`, final
   `hidden_states` shape, first-token L2.
4. Acceptance:
   - shapes match (scatter-back + pool preserves output length)
   - first-token L2 within 20% of dense (scale-correction works)
   - `vision_tower_ms_pruned / vision_tower_ms_dense ∈ [0.55, 0.85]`
     (matches H1 arithmetic: 15/16 layers × 0.5 tokens ≈ 0.53×
     FLOPs; add overhead)

If shapes mismatch or timing shows < 10% reduction, fail loud and
dig in before scaling to n=5 or n=30.

## Risk register

| risk | mitigation |
|------|------------|
| pool scale correction drifts token magnitudes out of the range the LLM expects | measure first-token L2 dense vs pruned; if >20% off, add a global rescale constant |
| keep-mask collapses entire frames to zero | enforce a per-frame minimum keep (e.g., 10% of tokens/frame) |
| MLX JIT recompiles when L_full shrinks | pre-set keep_rate to a fixed fraction of max_patches; no dynamic shapes after layer L |
| timing jitter on M3 Air swamps the V-reduction signal at n=1 | pilot at n=5 per cell, not n=1 |

## Execution order (post kr=0.25)

1. Implement `src/codec_through/pruned_vision_tower.py` (~1h).
2. Add CLI wire-up to driver (~30 min).
3. Pilot on n=1 long item — validate shapes + timing sanity (~10 min).
4. Dev tranche: 9 cells × 5 items per prereg (~2h wall clock).
5. n=30 at winning cell (~40 min).

## Links

- `2026-04-18-phase-1_51V-vision-tower-pruning-prereg.md` — hypotheses.
- `2026-04-18-arithmetic-ceiling-findings.md` — V-term breakdown.
- `.venv/lib/python3.12/site-packages/mlx_vlm/models/gemma4/vision.py:375-389`
  — hook site (VisionTransformerModel.__call__).
- `.venv/lib/python3.12/site-packages/mlx_vlm/models/gemma4/vision.py:335-372`
  — VisionPooler (the scale-correction target).
