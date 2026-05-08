from __future__ import annotations

import numpy as np

from codec_through.codec.continuous_score import (
    calibrate_score_thresholds,
    class_share_vector,
    classify_score_grid,
    project_fused_motion_residual_to_token_grid,
    project_macroblock_scores_to_token_grid,
    sparse_pair_spans,
    sparse_sample_indices,
)
from codec_through.temporal import BlockClass


def test_sparse_sample_indices_match_linspace_contract() -> None:
    assert sparse_sample_indices(10, 4) == [0, 3, 6, 9]


def test_sparse_pair_spans_are_inclusive_between_samples() -> None:
    assert sparse_pair_spans([0, 3, 6, 9]) == [(1, 3), (4, 6), (7, 9)]


def test_project_macroblock_scores_to_token_grid_respects_padding() -> None:
    projected = project_macroblock_scores_to_token_grid(
        np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32),
        macroblock_size=16,
        frame_width=32,
        frame_height=32,
        canvas_size=64,
        active_box=(16, 16, 48, 48),
        token_block=16,
    )
    expected = np.array(
        [
            [0.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 2.0, 0.0],
            [0.0, 3.0, 4.0, 0.0],
            [0.0, 0.0, 0.0, 0.0],
        ],
        dtype=np.float32,
    )
    assert np.allclose(projected, expected)


def test_project_fused_motion_residual_to_token_grid_matches_weighted_fusion() -> None:
    motion = np.array([[1.0, 0.0], [0.0, 0.0]], dtype=np.float32)
    residual = np.array([[0.0, 3.0], [0.0, 0.0]], dtype=np.float32)

    projected = project_fused_motion_residual_to_token_grid(
        motion,
        residual,
        macroblock_size=16,
        frame_width=32,
        frame_height=32,
        canvas_size=32,
        active_box=(0, 0, 32, 32),
        token_block=16,
        mode="weighted",
        normalize_inputs=False,
    )

    assert np.allclose(projected, np.array([[0.5, 1.5], [0.0, 0.0]], dtype=np.float32))


def test_project_fused_motion_residual_zero_weight_lanes_match_inputs() -> None:
    motion = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)
    residual = np.array([[4.0, 3.0], [2.0, 1.0]], dtype=np.float32)

    motion_only = project_fused_motion_residual_to_token_grid(
        motion,
        residual,
        macroblock_size=16,
        frame_width=32,
        frame_height=32,
        canvas_size=32,
        active_box=(0, 0, 32, 32),
        token_block=16,
        motion_weight=1.0,
        residual_weight=0.0,
        normalize_inputs=False,
    )
    residual_only = project_fused_motion_residual_to_token_grid(
        motion,
        residual,
        macroblock_size=16,
        frame_width=32,
        frame_height=32,
        canvas_size=32,
        active_box=(0, 0, 32, 32),
        token_block=16,
        motion_weight=0.0,
        residual_weight=1.0,
        normalize_inputs=False,
    )

    assert np.array_equal(motion_only, motion)
    assert np.array_equal(residual_only, residual)


def test_calibrate_score_thresholds_and_classify_score_grid() -> None:
    thresholds = calibrate_score_thresholds(
        np.array([0.0, 0.1, 0.2, 0.7, 0.8, 0.9], dtype=np.float32),
        static_share=1.0 / 3.0,
        shifted_share=1.0 / 3.0,
    )
    classes = classify_score_grid(
        np.array([[0.05, 0.50, 0.85]], dtype=np.float32),
        thresholds=thresholds,
    )
    assert np.array_equal(
        classes,
        np.array([[BlockClass.STATIC, BlockClass.SHIFTED, BlockClass.NOVEL]], dtype=np.int32),
    )


def test_class_share_vector_aggregates_multiple_pair_grids() -> None:
    shares = class_share_vector(
        [
            np.array([[BlockClass.STATIC, BlockClass.SHIFTED]], dtype=np.int32),
            np.array([[BlockClass.NOVEL, BlockClass.NOVEL]], dtype=np.int32),
        ]
    )
    assert np.allclose(shares, np.array([0.25, 0.25, 0.5], dtype=np.float64))
