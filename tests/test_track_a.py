from __future__ import annotations

import numpy as np

from codec_through.temporal import BlockClass
from codec_through.track_a import (
    active_region_block_mask,
    flattened_reuse_mask,
    gemma_cached_token_index_grid,
    gemma_grouped_all,
    gemma_grouped_mean,
    qwen_merged_grid_shapes,
    qwen_merged_token_counts,
    resized_dimensions_for_block_multiple,
    square_grid_shape_from_token_count,
)


def test_resized_dimensions_for_qwen_synthetic_clip() -> None:
    assert resized_dimensions_for_block_multiple(320, 240, block_size=28, target_height=252) == (
        336,
        252,
    )


def test_resized_dimensions_for_qwen_xiph_clip() -> None:
    assert resized_dimensions_for_block_multiple(352, 288, block_size=28, target_height=252) == (
        308,
        252,
    )


def test_qwen_merged_token_counts_match_merge_geometry() -> None:
    image_grid_thw = np.array([[1, 18, 24], [1, 18, 24]], dtype=np.int64)
    assert qwen_merged_token_counts(image_grid_thw, spatial_merge_size=2) == [108, 108]


def test_qwen_merged_grid_shapes_match_merge_geometry() -> None:
    image_grid_thw = np.array([[1, 18, 24], [1, 18, 24]], dtype=np.int64)
    assert qwen_merged_grid_shapes(image_grid_thw, spatial_merge_size=2) == [(9, 12), (9, 12)]


def test_square_grid_shape_from_token_count() -> None:
    assert square_grid_shape_from_token_count(256) == (16, 16)


def test_flattened_reuse_mask_marks_requested_classes() -> None:
    classification = np.array(
        [
            [int(BlockClass.STATIC), int(BlockClass.SHIFTED)],
            [int(BlockClass.NOVEL), int(BlockClass.STATIC)],
        ],
        dtype=np.int32,
    )
    mask = flattened_reuse_mask(
        classification, reuse_classes=(BlockClass.STATIC, BlockClass.SHIFTED)
    )
    assert mask.tolist() == [True, True, False, True]


def test_active_region_block_mask_excludes_padded_border_blocks() -> None:
    mask = active_region_block_mask(
        (112, 84),
        (28, 0, 84, 84),
        block_size=28,
    )
    assert mask.tolist() == [
        False,
        True,
        True,
        False,
        False,
        True,
        True,
        False,
        False,
        True,
        True,
        False,
    ]


def test_active_region_block_mask_handles_gemma_soft_grid() -> None:
    token_index_grid = gemma_cached_token_index_grid(
        (560, 560),
        patch_size=16,
        pooling_kernel_size=3,
        output_length=280,
    )
    assert token_index_grid.shape == (35, 35)
    assert int(token_index_grid.max()) + 1 == 133
    assert int(token_index_grid[0, 34]) == 11
    assert int(token_index_grid[3, 0]) == 11
    assert int(token_index_grid[34, 34]) == 132


def test_gemma_grouped_mean_and_all_follow_cached_layout() -> None:
    token_index_grid = np.array(
        [
            [0, 0, 1],
            [2, 1, 1],
        ],
        dtype=np.int32,
    )
    values = np.array(
        [
            [1.0, 3.0, 4.0],
            [9.0, 7.0, 10.0],
        ],
        dtype=np.float32,
    )
    active = np.array(
        [
            [True, True, True],
            [False, True, True],
        ],
        dtype=bool,
    )
    means = gemma_grouped_mean(values, token_index_grid)
    grouped_active = gemma_grouped_all(active, token_index_grid)
    assert means.tolist() == [2.0, 7.0, 9.0]
    assert grouped_active.tolist() == [True, True, False]
