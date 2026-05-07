"""Tests for the local RLT-style mask helper.

These tests are intentionally MLX-free. The mask kernel is a pure NumPy/Pillow
port-by-inspection of RLT's repeated-token detector; model wiring is tested
separately.
"""

from __future__ import annotations

import numpy as np
import pytest

from codec_through.rlt_masks import (
    RLTMaskConfig,
    aggregate_to_grid,
    artifact_config_hash,
    compute_rlt_keep_mask_from_array,
    compute_rlt_keep_mask_from_frames,
    compute_tubelet_run_lengths,
    fixed_budget_rlt_score_mask,
    fixed_budget_rlt_score_mask_for_positions,
    jaccard,
    mask_summary,
    project_bool_grid,
    project_float_grid,
)


def _constant_frames(frame_count: int, *, value: float = 64.0) -> np.ndarray:
    return np.full((frame_count, 16, 16, 3), value, dtype=np.float32)


def _motion_frames(frame_count: int) -> np.ndarray:
    frames = np.zeros((frame_count, 16, 16, 3), dtype=np.float32)
    for idx in range(frame_count):
        frames[idx] = idx * 16.0
    return frames


def test_exact_static_keeps_only_first_tubelet() -> None:
    cfg = RLTMaskConfig(
        threshold=0.1,
        tubelet_size=2,
        image_size=(16, 16),
        grid_shape=(4, 4),
        normalize_mode="imagenet",
    )

    result = compute_rlt_keep_mask_from_array(_constant_frames(8), config=cfg)

    assert result.keep_rate == pytest.approx(0.25)
    assert result.first_tubelet_token_count == 32
    assert result.threshold_active_token_count == 0
    assert result.floor_active_token_count == 0
    assert result.tubelet_keep_mask[0].all()
    assert not result.tubelet_keep_mask[1:].any()
    assert result.run_length_histogram() == {"4": 16}
    assert result.per_frame_keep_counts() == [16, 16, 0, 0, 0, 0, 0, 0]


def test_default_grid_shape_matches_published_rlt_patch_size() -> None:
    cfg = RLTMaskConfig(threshold=0.1, tubelet_size=2)

    result = compute_rlt_keep_mask_from_array(
        np.full((4, 224, 224, 3), 64.0, dtype=np.float32),
        config=cfg,
    )

    assert result.frame_keep_mask.shape == (4, 14, 14)
    assert cfg.as_dict()["grid_shape"] == [14, 14]
    assert cfg.as_dict()["grid_shape_source"] == "patch_size"
    assert cfg.as_dict()["ordering"] == "time_major"


def test_224_to_16_projection_operating_point() -> None:
    cfg = RLTMaskConfig(threshold=0.1, tubelet_size=2)
    result = compute_rlt_keep_mask_from_array(
        np.full((4, 224, 224, 3), 64.0, dtype=np.float32),
        config=cfg,
    )

    projected = project_bool_grid(result.frame_keep_mask, (16, 16))

    assert projected.shape == (4, 16, 16)
    assert projected[:2].all()
    assert not projected[2:].any()


def test_single_frame_repeat_with_unit_tubelet_keeps_one_over_n() -> None:
    cfg = RLTMaskConfig(
        threshold=0.1,
        tubelet_size=1,
        image_size=(16, 16),
        grid_shape=(4, 4),
        normalize_mode="imagenet",
    )

    result = compute_rlt_keep_mask_from_array(_constant_frames(8), config=cfg)

    assert result.keep_rate == pytest.approx(1.0 / 8.0)
    assert result.tubelet_keep_mask[0].all()
    assert not result.tubelet_keep_mask[1:].any()
    assert result.run_length_histogram() == {"8": 16}


def test_all_motion_keeps_every_comparable_tubelet() -> None:
    cfg = RLTMaskConfig(
        threshold=0.1,
        tubelet_size=2,
        image_size=(16, 16),
        grid_shape=(4, 4),
        normalize_mode="imagenet",
    )

    result = compute_rlt_keep_mask_from_array(_motion_frames(8), config=cfg)

    assert result.keep_rate == pytest.approx(1.0)
    assert result.tubelet_keep_mask.all()
    assert result.threshold_active_token_count == 96
    assert result.run_length_histogram() == {"1": 64}


def test_endpoint_comparison_matches_rlt_stride() -> None:
    cfg = RLTMaskConfig(
        threshold=0.1,
        tubelet_size=2,
        image_size=(16, 16),
        grid_shape=(4, 4),
        normalize_mode="imagenet",
    )
    frames = _constant_frames(4, value=32.0)
    frames[3] = 224.0

    result = compute_rlt_keep_mask_from_array(frames, config=cfg)

    # For tubelet_size=2, the second tubelet compares frame 3 to frame 0.
    assert result.tubelet_keep_mask[1].all()


def test_threshold_monotonicity() -> None:
    frames = _motion_frames(8)
    rates: list[float] = []
    for threshold in (0.0, 0.1, 10.0):
        cfg = RLTMaskConfig(
            threshold=threshold,
            tubelet_size=2,
            image_size=(16, 16),
            grid_shape=(4, 4),
            normalize_mode="imagenet",
        )
        rates.append(compute_rlt_keep_mask_from_array(frames, config=cfg).keep_rate)

    assert rates == sorted(rates, reverse=True)


def test_kernel_is_deterministic() -> None:
    cfg = RLTMaskConfig(
        threshold=0.1,
        tubelet_size=2,
        image_size=(16, 16),
        grid_shape=(4, 4),
        normalize_mode="imagenet",
    )
    frames = _motion_frames(8)

    first = compute_rlt_keep_mask_from_array(frames, config=cfg)
    second = compute_rlt_keep_mask_from_array(frames, config=cfg)

    assert np.array_equal(first.frame_keep_mask, second.frame_keep_mask)
    assert np.array_equal(first.frame_run_lengths, second.frame_run_lengths)


def test_time_major_ordering_is_explicit_and_observable() -> None:
    cfg = RLTMaskConfig(
        threshold=0.1,
        tubelet_size=2,
        image_size=(16, 16),
        grid_shape=(2, 2),
        normalize_mode="imagenet",
    )
    result = compute_rlt_keep_mask_from_array(_constant_frames(4), config=cfg)

    assert cfg.as_dict()["ordering"] == "time_major"
    assert result.frame_keep_mask.reshape(-1).tolist() == [True] * 8 + [False] * 8


def test_minimum_frame_guard_hard_fails() -> None:
    cfg = RLTMaskConfig(tubelet_size=2, image_size=(16, 16), grid_shape=(4, 4))
    with pytest.raises(ValueError, match="cannot form two tubelets"):
        compute_rlt_keep_mask_from_array(_constant_frames(3), config=cfg)


def test_non_divisible_frame_count_hard_fails() -> None:
    cfg = RLTMaskConfig(tubelet_size=2, image_size=(16, 16), grid_shape=(4, 4))
    with pytest.raises(ValueError, match="must be divisible"):
        compute_rlt_keep_mask_from_array(_constant_frames(5), config=cfg)


def test_pre_normalized_mode_rejects_raw_float01() -> None:
    cfg = RLTMaskConfig(
        tubelet_size=1,
        image_size=(16, 16),
        grid_shape=(4, 4),
        normalize_mode="pre_normalized_imagenet",
    )
    raw_float = np.full((4, 16, 16, 3), 0.5, dtype=np.float32)

    with pytest.raises(ValueError, match="expects ImageNet-normalized"):
        compute_rlt_keep_mask_from_array(raw_float, config=cfg)


def test_imagenet_mode_rejects_negative_raw_values() -> None:
    cfg = RLTMaskConfig(
        tubelet_size=1,
        image_size=(16, 16),
        grid_shape=(4, 4),
        normalize_mode="imagenet",
    )
    negative_raw = np.full((4, 16, 16, 3), -0.1, dtype=np.float32)

    with pytest.raises(ValueError, match="nonnegative raw RGB"):
        compute_rlt_keep_mask_from_array(negative_raw, config=cfg)


def test_float01_pixel_scale_matches_uint8_scale() -> None:
    uint8_cfg = RLTMaskConfig(
        threshold=0.1,
        tubelet_size=2,
        image_size=(16, 16),
        grid_shape=(4, 4),
        normalize_mode="imagenet",
        pixel_scale="uint8",
    )
    float01_cfg = RLTMaskConfig(
        threshold=0.1,
        tubelet_size=2,
        image_size=(16, 16),
        grid_shape=(4, 4),
        normalize_mode="imagenet",
        pixel_scale="float01",
    )
    uint8_result = compute_rlt_keep_mask_from_array(_motion_frames(4), config=uint8_cfg)
    float01_result = compute_rlt_keep_mask_from_array(
        _motion_frames(4) / 255.0,
        config=float01_cfg,
    )

    assert np.array_equal(uint8_result.frame_keep_mask, float01_result.frame_keep_mask)
    assert np.allclose(uint8_result.tubelet_scores, float01_result.tubelet_scores)


def test_float01_pixel_scale_rejects_uint8_values() -> None:
    cfg = RLTMaskConfig(
        threshold=0.1,
        tubelet_size=2,
        image_size=(16, 16),
        grid_shape=(4, 4),
        normalize_mode="imagenet",
        pixel_scale="float01",
    )

    with pytest.raises(ValueError, match="float01"):
        compute_rlt_keep_mask_from_array(_motion_frames(4), config=cfg)


def test_compute_from_frames_resizes_and_normalizes() -> None:
    cfg = RLTMaskConfig(
        threshold=0.1,
        tubelet_size=2,
        image_size=(16, 16),
        grid_shape=(4, 4),
        normalize_mode="imagenet",
    )
    frames = [np.full((8, 8, 3), 255, dtype=np.uint8) for _ in range(4)]

    result = compute_rlt_keep_mask_from_frames(frames, config=cfg)

    assert result.frame_keep_mask.shape == (4, 4, 4)
    assert result.keep_rate == pytest.approx(0.5)


def test_per_frame_floor_flags_added_tokens() -> None:
    cfg = RLTMaskConfig(
        threshold=0.1,
        tubelet_size=2,
        image_size=(16, 16),
        grid_shape=(4, 4),
        normalize_mode="imagenet",
        window_min_keep=2,
    )

    result = compute_rlt_keep_mask_from_array(_constant_frames(4), config=cfg)

    assert result.per_frame_keep_counts() == [16, 16, 2, 2]
    assert result.threshold_active_token_count == 0
    assert result.floor_active_token_count == 4
    assert result.floor_active


def test_run_lengths_align_with_tubelet_keep_order() -> None:
    keep = np.array(
        [
            [[True, True]],
            [[False, True]],
            [[True, False]],
            [[False, False]],
        ],
        dtype=bool,
    )

    lengths = compute_tubelet_run_lengths(keep)

    assert lengths[:, 0, 0].tolist() == [2, 0, 2, 0]
    assert lengths[:, 0, 1].tolist() == [1, 3, 0, 0]


def test_aggregate_and_projection_helpers() -> None:
    plane = np.arange(16, dtype=np.float32).reshape(4, 4)

    pooled = aggregate_to_grid(plane, (2, 2))
    bool_projected = project_bool_grid(pooled > 5.0, (4, 4))
    float_projected = project_float_grid(pooled, (4, 4))

    assert pooled.tolist() == [[2.5, 4.5], [10.5, 12.5]]
    assert bool_projected.shape == (4, 4)
    assert float_projected.shape == (4, 4)
    assert bool_projected[0, 0] == bool_projected[1, 1]
    assert float_projected[3, 3] == pytest.approx(12.5)


def test_fixed_budget_rlt_score_mask_keeps_uniform_k_after_projection() -> None:
    cfg = RLTMaskConfig(
        threshold=0.1,
        tubelet_size=2,
        image_size=(16, 16),
        grid_shape=(4, 4),
        normalize_mode="imagenet",
    )
    frames = _constant_frames(4)
    frames[3, 8:, 8:] = 255.0
    result = compute_rlt_keep_mask_from_array(frames, config=cfg)

    keep = fixed_budget_rlt_score_mask(result, out_grid_shape=(8, 8), keep_rate=0.25)

    assert keep.shape == (4, 8, 8)
    assert keep.reshape(4, -1).sum(axis=1).tolist() == [16, 16, 16, 16]
    assert keep[2:, 4:, 4:].any()


def test_fixed_budget_rlt_score_mask_for_positions_ignores_padding() -> None:
    cfg = RLTMaskConfig(
        threshold=0.1,
        tubelet_size=2,
        image_size=(16, 16),
        grid_shape=(4, 4),
        normalize_mode="imagenet",
    )
    frames = _constant_frames(4)
    frames[3, 8:, 8:] = 255.0
    result = compute_rlt_keep_mask_from_array(frames, config=cfg)
    real_positions = np.array([[x, y] for y in range(4) for x in range(4)], dtype=np.int64)
    padded_positions = np.concatenate(
        [real_positions, np.full((4, 2), -1, dtype=np.int64)],
        axis=0,
    )
    positions = np.stack([padded_positions] * 4, axis=0)

    keep = fixed_budget_rlt_score_mask_for_positions(result, positions=positions, keep_rate=0.5)

    assert keep.shape == (4, 20)
    assert keep.sum(axis=1).tolist() == [8, 8, 8, 8]
    assert not keep[:, 16:].any()


def test_jaccard_and_summary_and_hash_are_stable() -> None:
    left = np.array([[True, False], [True, False]])
    right = np.array([[True, True], [False, False]])
    cfg = RLTMaskConfig(
        threshold=0.1,
        tubelet_size=2,
        image_size=(16, 16),
        grid_shape=(4, 4),
        normalize_mode="imagenet",
    )
    result = compute_rlt_keep_mask_from_array(_constant_frames(4), config=cfg)

    assert jaccard(left, right) == pytest.approx(1.0 / 3.0)
    assert mask_summary(result)["kept_token_count"] == 32
    assert artifact_config_hash(cfg.as_dict()) == artifact_config_hash(cfg.as_dict())


def test_shape_mismatch_hard_fails() -> None:
    cfg = RLTMaskConfig(tubelet_size=2, image_size=(16, 16), grid_shape=(4, 4))

    with pytest.raises(ValueError, match="frames must be"):
        compute_rlt_keep_mask_from_array(np.zeros((4, 16, 16), dtype=np.float32), config=cfg)


def test_grid_shape_larger_than_pixels_hard_fails() -> None:
    cfg = RLTMaskConfig(tubelet_size=2, image_size=(16, 16), grid_shape=(32, 32))

    with pytest.raises(ValueError, match="cannot exceed"):
        compute_rlt_keep_mask_from_array(_constant_frames(4), config=cfg)
