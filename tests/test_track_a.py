from __future__ import annotations

import numpy as np

from codec_through.temporal import BlockClass
from codec_through.track_a import (
    flattened_reuse_mask,
    qwen_merged_token_counts,
    resized_dimensions_for_block_multiple,
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
