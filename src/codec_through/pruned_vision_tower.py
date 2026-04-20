"""Phase 1.51V — vision-tower-internal token pruning for Gemma 4.

Monkey-patches `VisionTransformerModel.__call__` to apply a keep-mask after
a configurable transformer layer L, run the remaining layers on the compact
sequence, then scatter-back to the original length so `VisionPooler` operates
on the same geometry as the dense path.

See `research/experiments/2026/2026-04-18-phase-1_51V-implementation-design.md`
for the slice-then-scatter-back rationale and pool-geometry constraint.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, cast

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


def magnitude_keep_mask(hidden_states: mx.array, positions: mx.array, keep_rate: float) -> mx.array:
    """Top-k keep-mask by L2 magnitude of each token's hidden state.

    Per-frame independent pruning: for each batch row (frame), keep the top-k
    tokens by L2 norm of hidden state. K is identical across frames (derived
    from keep_rate * L), so the compact sequence post-prune is [B, K, D].
    """
    del positions  # unused in magnitude policy
    B, L, _ = hidden_states.shape
    scores = mx.linalg.norm(hidden_states.astype(mx.float32), axis=-1)  # [B, L]
    k = max(1, int(L * keep_rate))
    # Per-row argsort ascending; take last k (highest magnitudes per frame)
    order = mx.argsort(scores, axis=-1)  # [B, L]
    top_k = order[:, -k:]  # [B, k] — indices of kept tokens per frame
    # Build bool mask [B, L] via broadcast equality: [B, k, 1] == [1, 1, L] -> [B, k, L]
    one_hot = cast(
        mx.array, mx.expand_dims(top_k, -1) == mx.expand_dims(mx.arange(L), 0)
    )  # [B, k, L]
    keep_mask = mx.any(one_hot, axis=1)  # [B, L] bool
    return keep_mask


def _slice_keep(x: mx.array, indices: mx.array, axis: int) -> mx.array:
    """Per-row gather along `axis` using integer indices [B, K].

    Supports B>=1. `indices[b, :]` selects K entries along `axis` from `x[b, ...]`.
    """
    if axis < 0:
        axis = x.ndim + axis
    B, K = indices.shape
    # Reshape indices to [B, 1, ..., K, ..., 1] with K at `axis`
    idx_shape = [1] * x.ndim
    idx_shape[0] = B
    idx_shape[axis] = K
    idx_reshaped = indices.reshape(idx_shape)
    broadcast_shape = list(x.shape)
    broadcast_shape[axis] = K
    idx_broadcast = mx.broadcast_to(idx_reshaped, broadcast_shape)
    return mx.take_along_axis(x, idx_broadcast, axis=axis)


def _scatter_back(pruned: mx.array, indices: mx.array, length: int) -> mx.array:
    """Scatter [B, K, D] back into [B, length, D] zero-filled at pruned slots.

    Per-frame one-hot matmul. Uses batched matmul to avoid mx.scatter
    (not yet in MLX). Cost: O(B*L*K*D) — negligible vs transformer layers.
    """
    # indices: [B, K] int32. Build [B, L, K] one-hot then batched matmul.
    # arange(L)[None, :, None]: [1, L, 1]; indices[:, None, :]: [B, 1, K]
    eq = cast(mx.array, mx.arange(length)[None, :, None] == indices[:, None, :])  # [B, L, K]
    W = eq.astype(pruned.dtype)  # [B, L, K]
    out = W @ pruned  # [B, L, D]
    return out


def _keep_indices(keep_mask: mx.array) -> mx.array:
    """Convert bool mask [B, L] to int indices [B, K]. K must be uniform across rows."""
    B, L = keep_mask.shape
    # Per-row argsort on bool (True=1 sorts last).
    order = mx.argsort(keep_mask.astype(mx.int32), axis=-1)  # [B, L]
    # K derived from row-0 sum; per-row K is identical by construction (top-k).
    k = int(keep_mask[0].astype(mx.int32).sum().item())
    idx = order[:, -k:]  # [B, K]
    return idx


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
        raise ValueError(f"layer_idx {layer_idx} out of range [0, {len(layers) - 1}]")

    def _call(hidden_states: mx.array, positions: mx.array, mask: mx.array) -> mx.array:
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


class _PrunedEncoderWrapper:
    """Call-operator wrapper around a VisionTransformerModel.

    Python looks up `__call__` on the TYPE, not the instance, so assigning
    `encoder.__call__ = new_call` is silently a no-op. This wrapper class
    defines `__call__` at class-scope, so replacing the encoder attribute
    with an instance of this wrapper actually routes calls through our
    replacement. Other attribute access forwards to the wrapped encoder.
    """

    def __init__(self, wrapped: Any, new_call: Callable[..., mx.array]) -> None:
        object.__setattr__(self, "_wrapped", wrapped)
        object.__setattr__(self, "_new_call", new_call)

    def __call__(self, *args: Any, **kwargs: Any) -> mx.array:
        result: mx.array = self._new_call(*args, **kwargs)
        return result

    def __getattr__(self, name: str) -> Any:
        return getattr(self._wrapped, name)


def patch_vision_tower(
    model: Any, config: PruneConfig, keep_mask_fn: KeepMaskFn | None = None
) -> None:
    """Replace `model.vision_tower.encoder` with a call-wrapper.

    Call once after load. Instance-level `__call__` assignment does NOT
    work in Python (magic methods are looked up on the type), so we swap
    the encoder attribute for a wrapper whose class defines `__call__`.
    """
    if keep_mask_fn is None:
        kr = config.keep_rate
        keep_mask_fn = lambda h, p: magnitude_keep_mask(h, p, kr)  # noqa: E731
    encoder = model.vision_tower.encoder
    new_call = make_pruned_encoder_call(encoder, config, keep_mask_fn)
    model.vision_tower.encoder = _PrunedEncoderWrapper(encoder, new_call)
