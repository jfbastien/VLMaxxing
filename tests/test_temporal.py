import numpy as np
import pytest

from codec_through.temporal import (
    BlockClass,
    BlockStatistic,
    BlockThresholds,
    PlannerConfig,
    block_size_from_vision_config,
    block_statistic_values,
    classify_blocks,
    classify_blocks_with_planner,
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


def test_classify_blocks_changed_fraction_is_stricter_on_sparse_changes() -> None:
    base = np.zeros((28, 28, 3), dtype=np.uint8)
    changed = base.copy()
    changed[14:18, 14:18] = 255

    mean_classes = classify_blocks_with_planner(
        base,
        changed,
        block_size=28,
        config=PlannerConfig(statistic=BlockStatistic.MEAN),
    )
    fraction_classes = classify_blocks_with_planner(
        base,
        changed,
        block_size=28,
        config=PlannerConfig(
            statistic=BlockStatistic.CHANGED_PIXEL_FRACTION,
            static_threshold=0.01,
            shifted_threshold=0.03,
            pixel_change_threshold=8.0,
        ),
    )

    assert int(mean_classes[0, 0]) == int(BlockClass.SHIFTED)
    assert int(fraction_classes[0, 0]) == int(BlockClass.SHIFTED)
    assert (
        block_statistic_values(
            base,
            changed,
            block_size=28,
            config=PlannerConfig(statistic=BlockStatistic.MEAN),
        )[0, 0]
        < 6.0
    )
    assert (
        block_statistic_values(
            base,
            changed,
            block_size=28,
            config=PlannerConfig(
                statistic=BlockStatistic.CHANGED_PIXEL_FRACTION,
                static_threshold=0.01,
                shifted_threshold=0.03,
                pixel_change_threshold=8.0,
            ),
        )[0, 0]
        > 0.02
    )


def test_classify_blocks_max_abs_flags_single_pixel_as_novel() -> None:
    base = np.zeros((28, 28, 3), dtype=np.uint8)
    changed = base.copy()
    changed[5, 5] = 200

    classes = classify_blocks_with_planner(
        base,
        changed,
        block_size=28,
        config=PlannerConfig(
            statistic=BlockStatistic.MAX_ABS,
            static_threshold=3.0,
            shifted_threshold=8.0,
        ),
    )

    assert int(classes[0, 0]) == int(BlockClass.NOVEL)


def test_classify_blocks_top_k_mean_beats_mean_for_sparse_changes() -> None:
    base = np.zeros((28, 28, 3), dtype=np.uint8)
    changed = base.copy()
    changed[10:14, 10:14] = 80

    mean_value = block_statistic_values(
        base,
        changed,
        block_size=28,
        config=PlannerConfig(statistic=BlockStatistic.MEAN),
    )[0, 0]
    top_k_value = block_statistic_values(
        base,
        changed,
        block_size=28,
        config=PlannerConfig(statistic=BlockStatistic.TOP_K_MEAN, top_k=16),
    )[0, 0]

    assert top_k_value > mean_value
