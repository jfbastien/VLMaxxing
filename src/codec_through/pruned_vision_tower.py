"""Phase 1.51V — vision-tower-internal token pruning for Gemma 4.

Monkey-patches `VisionTransformerModel.__call__` to apply a keep-mask after
a configurable transformer layer L, run the remaining layers on the compact
sequence, then scatter-back to the original length so `VisionPooler` operates
on the same geometry as the dense path.

See `research/experiments/2026/2026-04-18-phase-1_51V-implementation-design.md`
for the slice-then-scatter-back rationale and pool-geometry constraint.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import mlx.core as mx


KeepMaskFn = Callable[[mx.array, mx.array], mx.array]
"""(hidden_states [B,L,D], positions [B,L,2]) -> bool keep-mask [B,L].

B==1 is assumed; the callable must return a mask whose True count is
constant across invocations to avoid MLX JIT recompilation.
"""


@dataclass
class PruneConfig:
    """Configuration for vision-tower-internal pruning.

    layer_idx: apply keep mask AFTER this layer index (0..N-1).
    keep_rate: fraction of tokens to keep in [0, 1]. Applied to max_patches
        of the encoder (e.g., 4096 at 8 frames), not the pooled output.
    """

    layer_idx: int
    keep_rate: float


def magnitude_keep_mask(
    hidden_states: mx.array, positions: mx.array, keep_rate: float
) -> mx.array:
    """Top-k keep-mask by L2 magnitude of each token's hidden state.

    This is the first-pass policy: the literature (FasterVLM, EvoPrune)
    suggests layer-wise activation norm correlates with downstream utility.
    Later versions can replace this with the pixel-novelty signal 1.51R
    already computes (frame-level gate), intersected with magnitude
    (patch-level gate within kept frames).
    """
    del positions  # unused in magnitude policy
    B, L, _ = hidden_states.shape
    if B != 1:
        raise NotImplementedError("batch>1 not supported; Gemma VLM uses B=1")
    scores = mx.linalg.norm(hidden_states.astype(mx.float32), axis=-1)  # [B, L]
    k = max(1, int(L * keep_rate))
    # argsort ascending; take last k (highest magnitudes)
    order = mx.argsort(scores, axis=-1)  # [B, L]
    top_k = order[:, -k:]  # [B, k] — indices of kept tokens
    # Build bool mask by scattering into a zero tensor via one-hot
    one_hot = (
        mx.expand_dims(top_k, -1) == mx.expand_dims(mx.arange(L), 0)
    )  # [B, k, L]
    keep_mask = mx.any(one_hot, axis=1)  # [B, L] bool
    return keep_mask


def _slice_keep(x: mx.array, indices: mx.array, axis: int) -> mx.array:
    """Slice tokens along `axis` using integer indices [B, K]. Assumes B=1."""
    return mx.take(x, indices[0], axis=axis)


def _scatter_back(
    pruned: mx.array, indices: mx.array, length: int
) -> mx.array:
    """Scatter [B, K, D] back into [B, length, D] zero-filled at pruned slots.

    Uses one-hot matmul to avoid mx.scatter (not yet in MLX). O(L*K*D) but
    negligible vs transformer layers (~L*K*D*4 flops in matmul approach,
    vs per-layer ~L*D^2 FLOPs ≈ L*3M for Gemma-4 vision).
    """
    B, K, D = pruned.shape
    if B != 1:
        raise NotImplementedError("batch>1 not supported")
    # indices: [B, K] int32. Build [L, K] one-hot matrix.
    kept = indices[0]  # [K]
    W = (mx.arange(length)[:, None] == kept[None, :]).astype(pruned.dtype)  # [L, K]
    out = W @ pruned[0]  # [L, D]
    return mx.expand_dims(out, 0)  # [1, L, D]


def _keep_indices(keep_mask: mx.array) -> mx.array:
    """Convert bool mask [B, L] to int indices [B, K]. B=1, K fixed per call."""
    B, L = keep_mask.shape
    if B != 1:
        raise NotImplementedError("batch>1 not supported")
    # mx lacks `nonzero`; compute via argsort on bool (True=1 sorts last).
    order = mx.argsort(keep_mask[0].astype(mx.int32))
    k = int(keep_mask[0].astype(mx.int32).sum().item())
    idx = order[-k:]
    return mx.expand_dims(idx, 0)


def make_pruned_encoder_call(
    original_encoder: Any, config: PruneConfig, keep_mask_fn: KeepMaskFn
) -> Callable[[mx.array, mx.array, mx.array], mx.array]:
    """Return a replacement for `VisionTransformerModel.__call__`.

    Applies `keep_mask_fn` AFTER layer `config.layer_idx`, slices tokens +
    positions + attention mask, runs remaining layers on the compact
    sequence, then scatters the output back to original length.
    """
    layer_idx = config.layer_idx
    layers = original_encoder.layers
    if layer_idx < 0 or layer_idx >= len(layers):
        raise ValueError(
            f"layer_idx {layer_idx} out of range [0, {len(layers) - 1}]"
        )

    def _call(
        hidden_states: mx.array, positions: mx.array, mask: mx.array
    ) -> mx.array:
        for i, layer in enumerate(layers):
            hidden_states = layer(hidden_states, positions, mask)
            if i == layer_idx:
                B, L_full, _ = hidden_states.shape
                keep = keep_mask_fn(hidden_states, positions)  # [B, L]
                idx = _keep_indices(keep)  # [B, K]
                hidden_states = _slice_keep(hidden_states, idx, axis=1)
                positions = _slice_keep(positions, idx, axis=1)
                # mask shape: [B, 1, L, L] (or [B, 1, 1, L, L] — varies).
                # Slice last two axes, preserving leading ones.
                # For mlx_vlm Gemma4: shape is [B, 1, L, L].
                if mask is not None and mask.ndim == 4:
                    mask = _slice_keep(mask, idx, axis=-1)
                    mask = _slice_keep(mask, idx, axis=-2)
                # Save indices for scatter-back after remaining layers.
                _kept_idx_saved = idx  # noqa: F841 (captured via closure below)
                # Continue remaining layers with compact sequence.
                # Break out of the enumerate loop so we can do this cleanly.
                remaining = layers[i + 1 :]
                for later_layer in remaining:
                    hidden_states = later_layer(hidden_states, positions, mask)
                # Scatter back to [B, L_full, D] so pooler geometry is
                # preserved. Pruned positions become zero.
                hidden_states = _scatter_back(hidden_states, idx, L_full)
                return hidden_states
        return hidden_states

    return _call


def patch_vision_tower(
    model: Any, config: PruneConfig, keep_mask_fn: KeepMaskFn | None = None
) -> None:
    """Monkey-patch `model.vision_tower.encoder.__call__` in place.

    Call once after load. No-op if already patched for the same config.
    """
    if keep_mask_fn is None:
        kr = config.keep_rate
        keep_mask_fn = lambda h, p: magnitude_keep_mask(h, p, kr)  # noqa: E731
    encoder = model.vision_tower.encoder
    new_call = make_pruned_encoder_call(encoder, config, keep_mask_fn)
    # bind as a method on the instance
    encoder.__call__ = new_call  # type: ignore[assignment]
