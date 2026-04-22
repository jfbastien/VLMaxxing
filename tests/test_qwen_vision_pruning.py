from __future__ import annotations

import numpy as np

from codec_through.qwen_vision_pruning import (
    qwen_compact_cu_seqlens,
    qwen_groups_per_frame,
    qwen_window_aligned_prune_plan,
    qwen_window_group_counts,
    qwen_window_slices_for_frames,
)


def test_qwen_groups_per_frame_matches_merged_counts() -> None:
    image_grid_thw = np.array([[1, 18, 24], [1, 18, 24]], dtype=np.int64)
    assert qwen_groups_per_frame(image_grid_thw, spatial_merge_size=2) == (108, 108)


def test_qwen_window_group_counts_filters_zero_windows() -> None:
    cu_window = np.array([0, 16, 16, 32, 48], dtype=np.int32)
    assert qwen_window_group_counts(cu_window, spatial_merge_unit=4) == (4, 4, 4)


def test_qwen_window_slices_track_frame_boundaries() -> None:
    assert qwen_window_slices_for_frames((6, 4), (2, 2, 2, 1, 3)) == (
        ((0, 2), (2, 4), (4, 6)),
        ((6, 7), (7, 10)),
    )


def test_qwen_window_aligned_prune_plan_keeps_top_groups_per_window() -> None:
    scores = np.array([1.0, 3.0, 2.0, 4.0, 7.0, 5.0, 6.0, 8.0], dtype=np.float32)
    plan = qwen_window_aligned_prune_plan(
        scores,
        groups_per_frame=(4, 4),
        groups_per_window=(2, 2, 2, 2),
        keep_rate=0.5,
    )
    assert plan.keep_indices == (1, 3, 4, 7)
    assert plan.kept_groups_per_frame == (2, 2)
    assert plan.kept_groups_per_window == (1, 1, 1, 1)


def test_qwen_compact_cu_seqlens_uses_merge_unit() -> None:
    assert qwen_compact_cu_seqlens((3, 2, 1), spatial_merge_unit=4).tolist() == [0, 12, 20, 24]
