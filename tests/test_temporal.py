import numpy as np
import pytest

from codec_through.temporal import (
    BlockClass,
    BlockThresholds,
    block_size_from_vision_config,
    classify_blocks,
    summarize_classification,
)


def test_classify_blocks_static_shifted_and_novel() -> None:
    base = np.zeros((56, 56, 3), dtype=np.uint8)
    changed = base.copy()
    changed[:28, 28:] = 5
    changed[28:, :28] = 20

    classification = classify_blocks(base, changed, block_size=28, thresholds=BlockThresholds())
    assert classification.tolist() == [
        [int(BlockClass.STATIC), int(BlockClass.SHIFTED)],
        [int(BlockClass.NOVEL), int(BlockClass.STATIC)],
    ]


def test_classify_blocks_requires_matching_shapes() -> None:
    base = np.zeros((56, 56, 3), dtype=np.uint8)
    changed = np.zeros((28, 56, 3), dtype=np.uint8)

    with pytest.raises(ValueError, match="frame shapes must match"):
        classify_blocks(base, changed, block_size=28, thresholds=BlockThresholds())


def test_classify_blocks_requires_exact_block_alignment() -> None:
    base = np.zeros((56, 60, 3), dtype=np.uint8)
    changed = base.copy()

    with pytest.raises(ValueError, match="exact multiples"):
        classify_blocks(base, changed, block_size=28, thresholds=BlockThresholds())


def test_block_size_from_vision_config_uses_patch_and_merge_size() -> None:
    assert block_size_from_vision_config({"patch_size": 14, "spatial_merge_size": 2}) == 28
    assert block_size_from_vision_config({"patch_size": 16}) == 16


def test_summarize_classification_reports_reuse_ratio() -> None:
    classification = np.array(
        [
            [int(BlockClass.STATIC), int(BlockClass.SHIFTED)],
            [int(BlockClass.NOVEL), int(BlockClass.NOVEL)],
        ],
        dtype=np.int32,
    )

    summary = summarize_classification(classification)
    assert summary.total_blocks == 4
    assert summary.reused_blocks == 2
    assert summary.reused_ratio == 0.5
    assert summary.novel_ratio == 0.5
