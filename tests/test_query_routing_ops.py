from __future__ import annotations

import numpy as np

from codec_through.query_routing import (
    endpoint_anchor_budget,
    fixed_uniform_mask_for_positions,
    grid_shape_from_valid_positions,
    random_valid_mask_for_positions,
    rlt_endpoint_anchor_mask_for_positions,
    rlt_static_floor_mask_for_positions,
    static_floor_indices_for_grid,
)
from codec_through.rlt_masks import RLTMaskConfig, RLTMaskResult


def _positions(side: int, *, frames: int = 1) -> np.ndarray:
    xy = np.asarray([[x, y] for y in range(side) for x in range(side)], dtype=np.int64)
    return np.repeat(xy[None, :, :], frames, axis=0)


def test_static_floor_stride_arithmetic_on_known_gemma_grids() -> None:
    assert static_floor_indices_for_grid((32, 32), 2).size == 256
    assert static_floor_indices_for_grid((32, 32), 4).size == 64
    assert static_floor_indices_for_grid((32, 32), 8).size == 16
    assert static_floor_indices_for_grid((48, 48), 2).size == 576
    assert static_floor_indices_for_grid((48, 48), 4).size == 144
    assert static_floor_indices_for_grid((48, 48), 8).size == 36


def test_fixed_uniform_keeps_matched_per_frame_budget() -> None:
    mask, ledger = fixed_uniform_mask_for_positions(_positions(32, frames=3), keep_rate=0.5)

    assert mask.shape == (3, 1024)
    assert [int(row.sum()) for row in mask] == [512, 512, 512]
    assert ledger.operator_plan == "fixed_uniform"
    assert ledger.complement_size_per_frame == [1024, 1024, 1024]


def test_static_floor_rlt_fill_does_not_double_count_reserved_positions() -> None:
    positions = _positions(32, frames=2)
    scores = np.arange(2 * 14 * 14, dtype=np.float32).reshape(2, 14, 14)
    result = RLTMaskResult(
        config=RLTMaskConfig(tubelet_size=1, grid_shape=(14, 14)),
        tubelet_keep_mask=np.ones((2, 14, 14), dtype=bool),
        frame_keep_mask=np.ones((2, 14, 14), dtype=bool),
        floor_active_frame_mask=np.zeros((2, 14, 14), dtype=bool),
        tubelet_scores=scores,
        tubelet_run_lengths=np.ones((2, 14, 14), dtype=np.int32),
        frame_run_lengths=np.ones((2, 14, 14), dtype=np.int32),
        first_tubelet_token_count=196,
        threshold_active_token_count=196,
        floor_active_token_count=0,
    )

    mask, ledger = rlt_static_floor_mask_for_positions(
        result,
        positions=positions,
        keep_rate=0.5,
        floor_stride=4,
    )

    assert [int(row.sum()) for row in mask] == [512, 512]
    assert ledger.reserved_positions_per_frame == [64, 64]
    assert ledger.complement_size_per_frame == [960, 960]
    assert ledger.operator_overlap_count_per_frame == [0, 0]


def test_static_floor_overflow_clips_and_logs() -> None:
    positions = _positions(4, frames=1)
    result = RLTMaskResult(
        config=RLTMaskConfig(tubelet_size=1, grid_shape=(4, 4)),
        tubelet_keep_mask=np.ones((1, 4, 4), dtype=bool),
        frame_keep_mask=np.ones((1, 4, 4), dtype=bool),
        floor_active_frame_mask=np.zeros((1, 4, 4), dtype=bool),
        tubelet_scores=np.ones((1, 4, 4), dtype=np.float32),
        tubelet_run_lengths=np.ones((1, 4, 4), dtype=np.int32),
        frame_run_lengths=np.ones((1, 4, 4), dtype=np.int32),
        first_tubelet_token_count=16,
        threshold_active_token_count=16,
        floor_active_token_count=0,
    )

    mask, ledger = rlt_static_floor_mask_for_positions(
        result,
        positions=positions,
        keep_rate=0.25,
        floor_stride=1,
    )

    assert int(mask.sum()) == 4
    assert ledger.reserved_positions_per_frame == [4]
    assert ledger.static_floor_overflow


def test_random_valid_position_is_seeded_and_reproducible() -> None:
    positions = _positions(32, frames=2)
    mask_a, _ = random_valid_mask_for_positions(positions, keep_rate=0.5, seed=11)
    mask_b, _ = random_valid_mask_for_positions(positions, keep_rate=0.5, seed=11)
    mask_c, _ = random_valid_mask_for_positions(positions, keep_rate=0.5, seed=23)

    assert np.array_equal(mask_a, mask_b)
    assert not np.array_equal(mask_a, mask_c)
    assert [int(row.sum()) for row in mask_a] == [512, 512]


def test_endpoint_anchor_accounting_debits_video_level_budget() -> None:
    budget = endpoint_anchor_budget(
        frame_count=8,
        valid_positions_per_frame=1024,
        keep_rate=0.5,
        anchor_frames=(0, 7),
    )

    assert budget["total_budget"] == 4096
    assert budget["anchor_debit"] == 2048
    assert budget["remaining_frames"] == 6
    assert budget["remaining_budget"] == 2048
    assert budget["remaining_budget_remainder"] == 2
    assert budget["per_remaining_frame_min"] == 341
    assert budget["per_remaining_frame_max"] == 342
    assert budget["remaining_budget_per_frame"] == [342, 342, 341, 341, 341, 341]
    assert sum(budget["remaining_budget_per_frame"]) == budget["remaining_budget"]


def test_endpoint_anchor_mask_keeps_anchor_frames_dense_and_preserves_total_budget() -> None:
    positions = _positions(8, frames=8)
    scores = np.arange(8 * 4 * 4, dtype=np.float32).reshape(8, 4, 4)
    result = RLTMaskResult(
        config=RLTMaskConfig(tubelet_size=1, grid_shape=(4, 4)),
        tubelet_keep_mask=np.ones((8, 4, 4), dtype=bool),
        frame_keep_mask=np.ones((8, 4, 4), dtype=bool),
        floor_active_frame_mask=np.zeros((8, 4, 4), dtype=bool),
        tubelet_scores=scores,
        tubelet_run_lengths=np.ones((8, 4, 4), dtype=np.int32),
        frame_run_lengths=np.ones((8, 4, 4), dtype=np.int32),
        first_tubelet_token_count=16,
        threshold_active_token_count=16,
        floor_active_token_count=0,
    )

    mask, ledger = rlt_endpoint_anchor_mask_for_positions(
        result,
        positions=positions,
        keep_rate=0.5,
        anchor_frames=(0, -1),
    )

    assert mask.shape == (8, 64)
    assert [int(row.sum()) for row in mask] == [64, 1, 1, 1, 1, 60, 64, 64]
    assert int(mask.sum()) == 256
    assert ledger.operator_plan == "rlt_topk_endpoint_anchor"
    assert ledger.operator_budget_mode == "video_level"
    assert ledger.reserved_positions_per_frame == [64, 1, 1, 1, 1, 1, 1, 64]


def test_endpoint_anchor_mask_rejects_zero_token_non_anchor_frames() -> None:
    positions = _positions(8, frames=4)
    result = RLTMaskResult(
        config=RLTMaskConfig(tubelet_size=1, grid_shape=(4, 4)),
        tubelet_keep_mask=np.ones((4, 4, 4), dtype=bool),
        frame_keep_mask=np.ones((4, 4, 4), dtype=bool),
        floor_active_frame_mask=np.zeros((4, 4, 4), dtype=bool),
        tubelet_scores=np.ones((4, 4, 4), dtype=np.float32),
        tubelet_run_lengths=np.ones((4, 4, 4), dtype=np.int32),
        frame_run_lengths=np.ones((4, 4, 4), dtype=np.int32),
        first_tubelet_token_count=16,
        threshold_active_token_count=16,
        floor_active_token_count=0,
    )

    try:
        rlt_endpoint_anchor_mask_for_positions(
            result,
            positions=positions,
            keep_rate=0.5,
            anchor_frames=(0, -1),
        )
    except ValueError as exc:
        assert "fewer than one token" in str(exc)
    else:
        raise AssertionError("expected zero-token non-anchor rejection")


def test_grid_shape_from_positions_rejects_non_dense_valid_grid() -> None:
    positions = _positions(4)[0]
    sparse = np.delete(positions, 5, axis=0)

    assert grid_shape_from_valid_positions(positions) == (4, 4)
    try:
        grid_shape_from_valid_positions(sparse)
    except ValueError as exc:
        assert "not a dense grid" in str(exc)
    else:
        raise AssertionError("expected sparse grid rejection")
