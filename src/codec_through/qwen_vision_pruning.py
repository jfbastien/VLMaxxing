"""Pure helpers for Qwen vision-tower pruning.

The MLX-facing wrapper lives separately in ``qwen_pruned_vision_tower.py``.
This module keeps the frame/window bookkeeping pure-Python + NumPy so it is
testable on non-Metal hosts.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from .track_a import qwen_merged_token_counts


@dataclass(frozen=True, slots=True)
class QwenVisionPrunePlan:
    """Pruning plan in group space.

    ``keep_indices`` are in the post-window-permutation group order used inside
    Qwen's vision blocks, i.e. after ``window_index`` has been applied and
    before ``self.merger`` collapses each group of 4 tokens.
    """

    keep_indices: tuple[int, ...]
    kept_groups_per_frame: tuple[int, ...]
    kept_groups_per_window: tuple[int, ...]


def qwen_groups_per_frame(
    image_grid_thw: npt.NDArray[np.integer],
    *,
    spatial_merge_size: int,
) -> tuple[int, ...]:
    """Return merged-token group counts per frame."""

    return tuple(
        int(value)
        for value in qwen_merged_token_counts(
            image_grid_thw,
            spatial_merge_size=spatial_merge_size,
        )
    )


def qwen_window_group_counts(
    cu_window_seqlens: Iterable[int],
    *,
    spatial_merge_unit: int,
) -> tuple[int, ...]:
    """Convert Qwen's cumulative window token offsets into group counts.

    Zero-length windows collapse to repeated offsets in ``cu_window_seqlens``.
    These are filtered out so downstream slicing logic only sees windows that
    actually contributed tokens.
    """

    if spatial_merge_unit <= 0:
        raise ValueError("spatial_merge_unit must be positive")
    values = np.asarray(list(cu_window_seqlens), dtype=np.int64)
    if values.ndim != 1 or values.size == 0:
        raise ValueError("cu_window_seqlens must be a non-empty 1D sequence")
    if values[0] != 0:
        raise ValueError("cu_window_seqlens must start at 0")
    deltas = np.diff(values)
    if np.any(deltas < 0):
        raise ValueError("cu_window_seqlens must be non-decreasing")
    if np.any(deltas % spatial_merge_unit != 0):
        raise ValueError("window token counts must be divisible by spatial_merge_unit")
    return tuple(int(delta // spatial_merge_unit) for delta in deltas if delta > 0)


def qwen_window_slices_for_frames(
    groups_per_frame: Iterable[int],
    groups_per_window: Iterable[int],
) -> tuple[tuple[tuple[int, int], ...], ...]:
    """Map contiguous window spans onto each frame's contiguous group span."""

    frame_counts = [int(value) for value in groups_per_frame]
    window_counts = [int(value) for value in groups_per_window]
    frame_slices: list[tuple[tuple[int, int], ...]] = []
    window_cursor = 0
    group_cursor = 0
    for frame_count in frame_counts:
        if frame_count <= 0:
            raise ValueError("groups_per_frame must be positive")
        frame_end = group_cursor + frame_count
        current: list[tuple[int, int]] = []
        while group_cursor < frame_end:
            if window_cursor >= len(window_counts):
                raise ValueError("window counts ended before frame counts")
            window_count = window_counts[window_cursor]
            if window_count <= 0:
                raise ValueError("groups_per_window must be positive")
            window_end = group_cursor + window_count
            if window_end > frame_end:
                raise ValueError("window spans cannot cross frame boundaries")
            current.append((group_cursor, window_end))
            group_cursor = window_end
            window_cursor += 1
        frame_slices.append(tuple(current))
    if window_cursor != len(window_counts):
        raise ValueError("unused window counts remained after frame mapping")
    return tuple(frame_slices)


def qwen_window_aligned_prune_plan(
    group_scores: npt.NDArray[np.floating],
    *,
    groups_per_frame: Iterable[int],
    groups_per_window: Iterable[int],
    keep_rate: float,
) -> QwenVisionPrunePlan:
    """Select top-scoring merged-token groups with one quota per window."""

    if not (0.0 < keep_rate <= 1.0):
        raise ValueError(f"keep_rate must be in (0, 1], got {keep_rate}")
    scores = np.asarray(group_scores, dtype=np.float64).reshape(-1)
    if scores.size == 0:
        raise ValueError("group_scores must be non-empty")

    frame_windows = qwen_window_slices_for_frames(groups_per_frame, groups_per_window)
    if sum(int(value) for value in groups_per_frame) != scores.size:
        raise ValueError("group_scores length must match groups_per_frame total")

    keep_mask = np.zeros(scores.shape[0], dtype=bool)
    kept_groups_per_frame: list[int] = []
    kept_groups_per_window: list[int] = []
    for windows in frame_windows:
        frame_kept = 0
        for start, end in windows:
            window_scores = scores[start:end]
            keep_count = min(
                window_scores.size,
                max(1, int(round(window_scores.size * keep_rate))),
            )
            order = np.argsort(window_scores, kind="stable")
            chosen = order[-keep_count:]
            keep_mask[start + chosen] = True
            kept_groups_per_window.append(int(keep_count))
            frame_kept += int(keep_count)
        kept_groups_per_frame.append(frame_kept)

    keep_indices = tuple(int(value) for value in np.flatnonzero(keep_mask))
    return QwenVisionPrunePlan(
        keep_indices=keep_indices,
        kept_groups_per_frame=tuple(kept_groups_per_frame),
        kept_groups_per_window=tuple(kept_groups_per_window),
    )


def pool_token_grid_to_merged_groups(
    token_grids: Iterable[npt.NDArray[np.floating]],
    *,
    spatial_merge_size: int,
) -> npt.NDArray[np.float32]:
    """Pool per-frame token-level codec score grids into merged-group scores.

    Inputs are per-frame 2D arrays of shape ``(grid_h, grid_w)`` at the token
    granularity Qwen consumes (e.g., 20x20 at canvas=560, token_block=28).
    Each ``(spatial_merge_size, spatial_merge_size)`` block is mean-pooled into
    a single merged-group score, and frames are concatenated in input order.
    The result is a 1D array in pre-window-permutation group order matching
    ``qwen_groups_per_frame``: frame-major, then row-major within each frame.

    Hard-fails on shape mismatches, NaN/Inf, or negative entries — codec score
    sources are non-negative by construction.
    """

    if spatial_merge_size <= 0:
        raise ValueError("spatial_merge_size must be positive")
    pooled: list[npt.NDArray[np.float32]] = []
    for index, grid in enumerate(token_grids):
        array = np.asarray(grid, dtype=np.float32)
        if array.ndim != 2:
            raise ValueError(f"per-frame token grid {index} must be 2D, got shape {array.shape}")
        rows, cols = array.shape
        if rows % spatial_merge_size != 0 or cols % spatial_merge_size != 0:
            raise ValueError(
                f"per-frame token grid {index} shape {array.shape} is not divisible "
                f"by spatial_merge_size={spatial_merge_size}"
            )
        if not np.all(np.isfinite(array)):
            raise ValueError(f"per-frame token grid {index} contains non-finite values")
        if np.any(array < 0.0):
            raise ValueError(f"per-frame token grid {index} contains negative values")
        merged_rows = rows // spatial_merge_size
        merged_cols = cols // spatial_merge_size
        reshaped = array.reshape(merged_rows, spatial_merge_size, merged_cols, spatial_merge_size)
        merged = reshaped.transpose(0, 2, 1, 3).mean(axis=(2, 3))
        pooled.append(merged.reshape(-1).astype(np.float32))
    if not pooled:
        raise ValueError("token_grids must contain at least one frame")
    return np.concatenate(pooled, axis=0)


def qwen_compact_cu_seqlens(
    kept_groups: Iterable[int],
    *,
    spatial_merge_unit: int,
) -> npt.NDArray[np.int32]:
    """Build Qwen-compatible cumulative sequence offsets for compact tokens."""

    if spatial_merge_unit <= 0:
        raise ValueError("spatial_merge_unit must be positive")
    offsets = [0]
    total = 0
    for count in kept_groups:
        count_int = int(count)
        if count_int <= 0:
            continue
        total += count_int * spatial_merge_unit
        offsets.append(total)
    if len(offsets) == 1:
        raise ValueError("kept_groups must contain at least one positive count")
    return np.asarray(offsets, dtype=np.int32)
