"""Pure helpers for Qwen vision-tower pruning.

The MLX-facing wrapper lives separately in ``qwen_pruned_vision_tower.py``.
This module keeps the frame/window bookkeeping pure-Python + NumPy so it is
testable on non-Metal hosts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

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
