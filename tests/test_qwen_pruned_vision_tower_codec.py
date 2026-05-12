"""CPU tests for the codec_grid score path in qwen_pruned_vision_tower.

These tests cover the parts of the pruner that do not require MLX: the
``_group_scores`` dispatch, codec score validation, window-index permutation,
and wrapper state management. The MLX-backed __call__ path is exercised by
the smoke run; here we only need to make sure the alignment math is correct.
"""

from __future__ import annotations

import mlx.core as mx
import numpy as np
import pytest

from codec_through.qwen_pruned_vision_tower import (
    QwenVisionPruneConfig,
    _group_scores,
    _QwenPrunedVisionWrapper,
)


class _StubModelBlock:
    pass


class _StubModel:
    """Minimal stand-in for an MLX Qwen vision tower for wrapper state tests."""

    def __init__(self) -> None:
        self.blocks = [_StubModelBlock(), _StubModelBlock(), _StubModelBlock()]
        self.spatial_merge_unit = 4
        self.spatial_merge_size = 2


def test_group_scores_codec_grid_returns_input_when_no_window_permutation() -> None:
    grid = np.array([3.0, 1.0, 4.0, 1.0, 5.0, 9.0, 2.0, 6.0], dtype=np.float32)
    fake_groups = mx.zeros((8, 4, 8))
    scores = _group_scores(
        fake_groups,
        mode="codec_grid",
        codec_score_grid=grid,
        window_index=None,
    )
    assert scores.tolist() == grid.tolist()


def test_group_scores_codec_grid_applies_window_permutation() -> None:
    grid = np.array([10.0, 20.0, 30.0, 40.0], dtype=np.float32)
    window_index = np.array([2, 0, 3, 1], dtype=np.int64)
    fake_groups = mx.zeros((4, 4, 8))
    scores = _group_scores(
        fake_groups,
        mode="codec_grid",
        codec_score_grid=grid,
        window_index=window_index,
    )
    assert scores.tolist() == [30.0, 10.0, 40.0, 20.0]


def test_group_scores_codec_grid_rejects_size_mismatch() -> None:
    fake_groups = mx.zeros((4, 4, 8))
    with pytest.raises(ValueError, match="expects 4"):
        _group_scores(
            fake_groups,
            mode="codec_grid",
            codec_score_grid=np.array([1.0, 2.0, 3.0], dtype=np.float32),
        )


def test_group_scores_codec_grid_rejects_nan() -> None:
    fake_groups = mx.zeros((2, 4, 8))
    with pytest.raises(ValueError, match="non-finite"):
        _group_scores(
            fake_groups,
            mode="codec_grid",
            codec_score_grid=np.array([1.0, np.nan], dtype=np.float32),
        )


def test_group_scores_codec_grid_rejects_negative() -> None:
    fake_groups = mx.zeros((2, 4, 8))
    with pytest.raises(ValueError, match="negative"):
        _group_scores(
            fake_groups,
            mode="codec_grid",
            codec_score_grid=np.array([1.0, -0.5], dtype=np.float32),
        )


def test_group_scores_codec_grid_requires_grid_when_mode_selected() -> None:
    fake_groups = mx.zeros((2, 4, 8))
    with pytest.raises(ValueError, match="requires a codec score grid"):
        _group_scores(fake_groups, mode="codec_grid", codec_score_grid=None)


def test_group_scores_unknown_mode_rejected_in_message() -> None:
    fake_groups = mx.zeros((2, 4, 8))
    with pytest.raises(ValueError, match="codec_grid"):
        _group_scores(fake_groups, mode="not_a_real_mode")


def test_wrapper_set_codec_score_grid_clears_with_none() -> None:
    wrapper = _QwenPrunedVisionWrapper(
        _StubModel(),
        QwenVisionPruneConfig(layer_idx=0, keep_rate=0.5, score_mode="codec_grid"),
    )
    wrapper.set_codec_score_grid(np.array([1.0, 2.0], dtype=np.float32))
    wrapper.set_codec_score_grid(None)
    assert wrapper._codec_score_grid is None


def test_wrapper_set_codec_score_grid_rejects_nan() -> None:
    wrapper = _QwenPrunedVisionWrapper(
        _StubModel(),
        QwenVisionPruneConfig(layer_idx=0, keep_rate=0.5, score_mode="codec_grid"),
    )
    with pytest.raises(ValueError, match="non-finite"):
        wrapper.set_codec_score_grid(np.array([np.inf, 0.0], dtype=np.float32))


def test_wrapper_set_codec_score_grid_rejects_negative() -> None:
    wrapper = _QwenPrunedVisionWrapper(
        _StubModel(),
        QwenVisionPruneConfig(layer_idx=0, keep_rate=0.5, score_mode="codec_grid"),
    )
    with pytest.raises(ValueError, match="negative"):
        wrapper.set_codec_score_grid(np.array([-1.0, 0.0], dtype=np.float32))


def test_config_records_codec_score_source_for_provenance() -> None:
    config = QwenVisionPruneConfig(
        layer_idx=2,
        keep_rate=0.7,
        score_mode="codec_grid",
        codec_score_source="novel_coded",
    )
    assert config.score_mode == "codec_grid"
    assert config.codec_score_source == "novel_coded"
