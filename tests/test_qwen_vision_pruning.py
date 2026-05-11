from __future__ import annotations

import numpy as np

import pytest

from codec_through.qwen_vision_pruning import (
    pool_token_grid_to_merged_groups,
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


def test_pool_token_grid_to_merged_groups_frame_major_order() -> None:
    frame_a = np.array(
        [[1.0, 2.0, 5.0, 6.0], [3.0, 4.0, 7.0, 8.0]], dtype=np.float32
    )
    frame_b = np.array(
        [[10.0, 10.0, 20.0, 20.0], [10.0, 10.0, 20.0, 20.0]], dtype=np.float32
    )
    pooled = pool_token_grid_to_merged_groups([frame_a, frame_b], spatial_merge_size=2)

    assert pooled.tolist() == [2.5, 6.5, 10.0, 20.0]


def test_pool_token_grid_to_merged_groups_uniform_pool() -> None:
    grid = np.full((4, 4), 3.0, dtype=np.float32)
    pooled = pool_token_grid_to_merged_groups([grid], spatial_merge_size=2)

    assert pooled.tolist() == [3.0, 3.0, 3.0, 3.0]


def test_pool_token_grid_to_merged_groups_rejects_non_divisible_shape() -> None:
    grid = np.zeros((3, 4), dtype=np.float32)
    with pytest.raises(ValueError, match="not divisible"):
        pool_token_grid_to_merged_groups([grid], spatial_merge_size=2)


def test_pool_token_grid_to_merged_groups_rejects_nan_inf() -> None:
    bad = np.array([[np.nan, 0.0], [0.0, 0.0]], dtype=np.float32)
    with pytest.raises(ValueError, match="non-finite"):
        pool_token_grid_to_merged_groups([bad], spatial_merge_size=2)


def test_pool_token_grid_to_merged_groups_rejects_negative() -> None:
    bad = np.array([[-1.0, 0.0], [0.0, 0.0]], dtype=np.float32)
    with pytest.raises(ValueError, match="negative"):
        pool_token_grid_to_merged_groups([bad], spatial_merge_size=2)


def test_pool_token_grid_to_merged_groups_rejects_3d_input() -> None:
    bad = np.zeros((2, 4, 4), dtype=np.float32)
    with pytest.raises(ValueError, match="2D"):
        pool_token_grid_to_merged_groups([bad], spatial_merge_size=2)


def test_pool_token_grid_to_merged_groups_rejects_empty_iterator() -> None:
    with pytest.raises(ValueError, match="at least one frame"):
        pool_token_grid_to_merged_groups([], spatial_merge_size=2)


def test_pool_token_grid_to_merged_groups_flatten_passthrough_when_stride_one() -> None:
    # When the per-frame token grid is already at merged-group resolution,
    # spatial_merge_size=1 should just flatten in frame-major / row-major order.
    frame_a = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)
    frame_b = np.array([[10.0, 20.0], [30.0, 40.0]], dtype=np.float32)
    pooled = pool_token_grid_to_merged_groups([frame_a, frame_b], spatial_merge_size=1)

    assert pooled.tolist() == [1.0, 2.0, 3.0, 4.0, 10.0, 20.0, 30.0, 40.0]
