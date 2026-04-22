"""Phase 1.51V Qwen vision-tower pruning.

This mirrors the Gemma-side ``pruned_vision_tower.py`` idea, but Qwen's
vision stack is structurally different:

- hidden states are flat ``[seq, hidden]`` rather than ``[B, L, D]``
- the vision path maintains both full-attention and window-attention
  cumulative sequence arrays
- the merger consumes groups of ``spatial_merge_unit`` contiguous tokens

The pruning contract here is therefore:

1. run Qwen's patch embed + window permutation exactly as the dense path does
2. after layer ``L``, score *merged-token groups* in the post-window order
3. prune whole groups with one quota per window
4. recompute compact ``cu_seqlens`` / ``cu_window_seqlens`` for the remaining
   layers
5. scatter back to the original sequence length before ``self.merger`` so the
   language model still sees the dense-path token geometry
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import mlx.core as mx
import numpy as np

from .qwen_vision_pruning import (
    qwen_compact_cu_seqlens,
    qwen_groups_per_frame,
    qwen_window_aligned_prune_plan,
    qwen_window_group_counts,
)


@dataclass(frozen=True, slots=True)
class QwenVisionPruneConfig:
    layer_idx: int
    keep_rate: float


def _dense_cu_seqlens(grid_thw: mx.array) -> mx.array:
    batch_size = int(grid_thw.shape[0])
    parts = []
    for i in range(batch_size):
        seq_len = int(grid_thw[i, 1].item()) * int(grid_thw[i, 2].item())
        repeats = int(grid_thw[i, 0].item())
        parts.append(mx.repeat(mx.array(seq_len, dtype=mx.int32), repeats))
    cu = mx.concatenate(parts)
    cu = mx.cumsum(cu.astype(mx.int32), axis=0)
    return mx.pad(cu, (1, 0), mode="constant", constant_values=0)


def _group_scores(group_hidden_states: mx.array) -> np.ndarray:
    mean_hidden = mx.mean(group_hidden_states.astype(mx.float32), axis=1)
    scores = mx.linalg.norm(mean_hidden, axis=-1)
    mx.eval(scores)
    return np.asarray(scores, dtype=np.float32)


def _scatter_groups(compact_groups: mx.array, keep_indices: mx.array, total_groups: int) -> mx.array:
    """Scatter compact group tensor [K, U, D] back to [G, U, D]."""

    if total_groups <= 0:
        raise ValueError("total_groups must be positive")
    if compact_groups.ndim != 3:
        raise ValueError("compact_groups must be rank 3")
    unit = int(compact_groups.shape[1])
    hidden = int(compact_groups.shape[2])
    one_hot = (mx.arange(total_groups)[:, None] == keep_indices[None, :]).astype(
        compact_groups.dtype
    )
    compact_flat = compact_groups.reshape(compact_groups.shape[0], unit * hidden)
    scattered = one_hot @ compact_flat
    return scattered.reshape(total_groups, unit, hidden)


def _dedup_cu_window_seqlens(cu_window_seqlens: mx.array) -> mx.array:
    seen: set[int] = set()
    keep: list[int] = []
    for index, value in enumerate(np.asarray(cu_window_seqlens, dtype=np.int32).tolist()):
        if value not in seen:
            seen.add(value)
            keep.append(index)
    return cu_window_seqlens[mx.array(keep, dtype=mx.int32)]


class _QwenPrunedVisionWrapper:
    def __init__(self, wrapped: Any, config: QwenVisionPruneConfig) -> None:
        object.__setattr__(self, "_wrapped", wrapped)
        object.__setattr__(self, "_config", config)
        object.__setattr__(self, "_last_prune_info", None)

    @property
    def last_prune_info(self) -> dict[str, Any] | None:
        return self._last_prune_info

    def __getattr__(self, name: str) -> Any:
        return getattr(self._wrapped, name)

    def __call__(
        self,
        hidden_states: mx.array,
        grid_thw: mx.array,
        output_hidden_states: bool | None = None,
    ) -> mx.array:
        model = self._wrapped
        config = self._config
        if config.layer_idx < 0 or config.layer_idx >= len(model.blocks):
            raise ValueError(
                f"layer_idx {config.layer_idx} out of range [0, {len(model.blocks) - 1}]"
            )
        if not (0.0 < config.keep_rate <= 1.0):
            raise ValueError(f"keep_rate must be in (0, 1], got {config.keep_rate}")

        hidden_states = model.patch_embed(hidden_states)
        rotary_pos_emb = model.rot_pos_emb(grid_thw)
        window_index, cu_window_seqlens = model.get_window_index(grid_thw)
        cu_window_seqlens = _dedup_cu_window_seqlens(cu_window_seqlens)

        seq_len, hidden = hidden_states.shape
        if seq_len % model.spatial_merge_unit != 0:
            raise ValueError(
                f"seq_len {seq_len} must be divisible by spatial_merge_unit {model.spatial_merge_unit}"
            )
        total_groups = seq_len // model.spatial_merge_unit

        hidden_groups = hidden_states.reshape(total_groups, model.spatial_merge_unit, hidden)
        hidden_groups = hidden_groups[window_index, :, :]
        hidden_states = hidden_groups.reshape(seq_len, hidden)

        rotary_groups = rotary_pos_emb.reshape(total_groups, model.spatial_merge_unit, -1)
        rotary_groups = rotary_groups[window_index, :, :]
        rotary_pos_emb = rotary_groups.reshape(seq_len, -1)

        cu_seqlens = _dense_cu_seqlens(grid_thw)
        kept_indices: mx.array | None = None
        kept_frame_counts: tuple[int, ...] | None = None
        kept_window_counts: tuple[int, ...] | None = None

        if output_hidden_states:
            encoder_states = (hidden_states,)
        else:
            encoder_states = None

        for layer_num, blk in enumerate(model.blocks):
            cu_seqlens_now = cu_seqlens if layer_num in model.fullatt_block_indexes else cu_window_seqlens
            hidden_states = blk(
                hidden_states,
                cu_seqlens=cu_seqlens_now,
                rotary_pos_emb=rotary_pos_emb,
            )
            if output_hidden_states:
                encoder_states = encoder_states + (hidden_states,)  # type: ignore[operator]

            if layer_num == config.layer_idx and config.keep_rate < 1.0:
                group_hidden_states = hidden_states.reshape(
                    total_groups, model.spatial_merge_unit, hidden
                )
                group_rotary = rotary_pos_emb.reshape(total_groups, model.spatial_merge_unit, -1)
                scores = _group_scores(group_hidden_states)
                groups_per_frame = qwen_groups_per_frame(
                    np.asarray(grid_thw.tolist(), dtype=np.int64),
                    spatial_merge_size=model.spatial_merge_size,
                )
                groups_per_window = qwen_window_group_counts(
                    np.asarray(cu_window_seqlens.tolist(), dtype=np.int32),
                    spatial_merge_unit=model.spatial_merge_unit,
                )
                plan = qwen_window_aligned_prune_plan(
                    scores,
                    groups_per_frame=groups_per_frame,
                    groups_per_window=groups_per_window,
                    keep_rate=config.keep_rate,
                )
                kept_frame_counts = plan.kept_groups_per_frame
                kept_window_counts = plan.kept_groups_per_window
                kept_indices = mx.array(plan.keep_indices, dtype=mx.int32)

                compact_groups = group_hidden_states[kept_indices, :, :]
                compact_rotary = group_rotary[kept_indices, :, :]
                hidden_states = compact_groups.reshape(-1, hidden)
                rotary_pos_emb = compact_rotary.reshape(-1, compact_rotary.shape[-1])
                cu_seqlens = mx.array(
                    qwen_compact_cu_seqlens(
                        kept_frame_counts,
                        spatial_merge_unit=model.spatial_merge_unit,
                    )
                )
                cu_window_seqlens = mx.array(
                    qwen_compact_cu_seqlens(
                        kept_window_counts,
                        spatial_merge_unit=model.spatial_merge_unit,
                    )
                )

        if kept_indices is not None:
            compact_groups = hidden_states.reshape(-1, model.spatial_merge_unit, hidden)
            hidden_states = _scatter_groups(compact_groups, kept_indices, total_groups).reshape(
                seq_len, hidden
            )
            object.__setattr__(
                self,
                "_last_prune_info",
                {
                    "total_groups": int(total_groups),
                    "kept_groups": int(compact_groups.shape[0]),
                    "kept_groups_per_frame": list(kept_frame_counts or []),
                    "kept_groups_per_window": list(kept_window_counts or []),
                },
            )
        else:
            object.__setattr__(
                self,
                "_last_prune_info",
                {
                    "total_groups": int(total_groups),
                    "kept_groups": int(total_groups),
                    "kept_groups_per_frame": list(
                        qwen_groups_per_frame(
                            np.asarray(grid_thw.tolist(), dtype=np.int64),
                            spatial_merge_size=model.spatial_merge_size,
                        )
                    ),
                    "kept_groups_per_window": list(
                        qwen_window_group_counts(
                            np.asarray(cu_window_seqlens.tolist(), dtype=np.int32),
                            spatial_merge_unit=model.spatial_merge_unit,
                        )
                    ),
                },
            )

        hidden_states = model.merger(hidden_states)
        reverse_indices = mx.argsort(window_index, axis=0)
        hidden_states = hidden_states[reverse_indices, :]
        return hidden_states


def patch_qwen_vision_tower(model: Any, config: QwenVisionPruneConfig) -> None:
    if getattr(model.config, "model_type", None) != "qwen2_5_vl":
        raise ValueError(
            "patch_qwen_vision_tower only supports qwen2_5_vl models; "
            f"got {getattr(model.config, 'model_type', None)!r}"
        )
    model.vision_tower = _QwenPrunedVisionWrapper(model.vision_tower, config)
