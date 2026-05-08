from __future__ import annotations

from typing import cast

import numpy as np
import pytest

from codec_through.codec.onevision_patchification import (
    FuseMode,
    PatchificationConfig,
    VisiblePatch,
    count_tokens_by_frame,
    fuse_motion_residual,
    percentile_normalize,
    pool_patch_scores,
    select_visible_patches,
    spatial_bias,
    temporal_coverage,
    visible_indices_array,
)


def test_select_visible_patches_keeps_full_anchor_then_global_topk() -> None:
    scores = np.zeros((3, 2, 2), dtype=np.float32)
    scores[0, :, :] = 100.0
    scores[1, 1, 0] = 9.0
    scores[2, 0, 1] = 8.0
    scores[1, 0, 0] = 7.0

    patches = select_visible_patches(
        scores,
        config=PatchificationConfig(token_budget=6, anchor_frames=(0,)),
    )

    assert len(patches) == 6
    assert [patch.source for patch in patches[:4]] == ["anchor", "anchor", "anchor", "anchor"]
    assert visible_indices_array(patches).tolist() == [
        [0, 0, 0],
        [0, 0, 1],
        [0, 1, 0],
        [0, 1, 1],
        [1, 1, 0],
        [2, 0, 1],
    ]


def test_select_visible_patches_rejects_anchor_budget_overflow() -> None:
    scores = np.zeros((2, 2, 2), dtype=np.float32)

    with pytest.raises(ValueError, match="mandatory anchor"):
        select_visible_patches(
            scores,
            config=PatchificationConfig(token_budget=3, anchor_frames=(0,)),
        )


def test_select_visible_patches_has_stable_tie_breaking() -> None:
    scores = np.ones((2, 2, 2), dtype=np.float32)

    patches = select_visible_patches(
        scores,
        config=PatchificationConfig(token_budget=3, anchor_frames=()),
    )

    assert visible_indices_array(patches).tolist() == [
        [0, 0, 0],
        [0, 0, 1],
        [0, 1, 0],
    ]


def test_pool_patch_scores_and_synthetic_motion_square() -> None:
    score_frames = np.zeros((2, 8, 8), dtype=np.float32)
    score_frames[1, 4:8, 0:4] = 10.0

    patch_scores = pool_patch_scores(score_frames, patch_size=4)
    patches = select_visible_patches(
        patch_scores,
        config=PatchificationConfig(token_budget=1, anchor_frames=()),
    )

    assert patch_scores.shape == (2, 2, 2)
    assert visible_indices_array(patches).tolist() == [[1, 1, 0]]


def test_percentile_normalize_and_fuse_motion_residual() -> None:
    motion = np.array([0.0, 1.0, 2.0], dtype=np.float32)
    residual = np.array([2.0, 0.0, 2.0], dtype=np.float32)

    normalized = percentile_normalize(motion, percentile=100.0)
    fused = fuse_motion_residual(
        motion,
        residual,
        mode="weighted",
        motion_weight=3.0,
        residual_weight=1.0,
        normalize_inputs=True,
    )

    assert np.allclose(normalized, np.array([0.0, 0.5, 1.0], dtype=np.float32))
    assert np.allclose(fused, np.array([0.25, 0.39473686, 1.0], dtype=np.float32))


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("sum", np.array([3.0, 4.0], dtype=np.float32)),
        ("max", np.array([2.0, 3.0], dtype=np.float32)),
        ("geomean", np.array([np.sqrt(2.0), np.sqrt(3.0)], dtype=np.float32)),
    ],
)
def test_fuse_motion_residual_exposed_modes(mode: str, expected: np.ndarray) -> None:
    motion = np.array([1.0, 3.0], dtype=np.float32)
    residual = np.array([2.0, 1.0], dtype=np.float32)

    fused = fuse_motion_residual(
        motion,
        residual,
        mode=cast(FuseMode, mode),
        motion_weight=1.0,
        residual_weight=1.0,
        normalize_inputs=False,
    )

    assert np.allclose(fused, expected)


def test_fuse_motion_residual_rejects_all_zero_weights() -> None:
    with pytest.raises(ValueError, match="at least one fusion weight"):
        fuse_motion_residual(
            np.ones((2,), dtype=np.float32),
            np.ones((2,), dtype=np.float32),
            motion_weight=0.0,
            residual_weight=0.0,
        )


def test_percentile_normalize_default_clips_and_zero_scale() -> None:
    values = np.array([0.0, 1.0, 2.0, 100.0], dtype=np.float32)
    normalized = percentile_normalize(values)

    assert float(normalized.max()) == 1.0
    assert np.array_equal(
        percentile_normalize(np.zeros((3,), dtype=np.float32)),
        np.zeros((3,), dtype=np.float32),
    )


def test_select_visible_patches_budget_edge_cases() -> None:
    with pytest.raises(ValueError, match="token_budget must be positive"):
        PatchificationConfig(token_budget=0)

    scores = np.array([[[3.0, 2.0], [1.0, 0.0]], [[9.0, 8.0], [7.0, 6.0]]], dtype=np.float32)
    patches = select_visible_patches(
        scores,
        config=PatchificationConfig(token_budget=4, anchor_frames=(0,)),
    )

    assert [patch.source for patch in patches] == ["anchor", "anchor", "anchor", "anchor"]
    assert visible_indices_array(patches).tolist() == [
        [0, 0, 0],
        [0, 0, 1],
        [0, 1, 0],
        [0, 1, 1],
    ]


def test_temporal_coverage_and_counts() -> None:
    patches = [
        VisiblePatch(frame=0, row=0, col=0, score=1.0, source="anchor"),
        VisiblePatch(frame=3, row=0, col=0, score=1.0, source="score"),
        VisiblePatch(frame=7, row=0, col=0, score=1.0, source="score"),
    ]

    counts = count_tokens_by_frame(patches, total_frames=8)
    coverage = temporal_coverage(patches, total_frames=8)

    assert counts.tolist() == [1, 0, 0, 1, 0, 0, 0, 1]
    assert coverage.observed_frames == 3
    assert coverage.observed_fraction == 3 / 8
    assert coverage.max_gap == 4
    assert coverage.mean_gap == 3.5


def test_spatial_bias_reports_center_and_boundary_distribution() -> None:
    patches = [
        VisiblePatch(frame=0, row=1, col=1, score=1.0, source="score"),
        VisiblePatch(frame=0, row=2, col=2, score=1.0, source="score"),
        VisiblePatch(frame=1, row=0, col=3, score=1.0, source="score"),
        VisiblePatch(frame=1, row=3, col=0, score=1.0, source="score"),
    ]

    bias = spatial_bias(patches, grid_shape=(4, 4))

    assert bias.center_fraction == 0.5
    assert bias.boundary_fraction == 0.5
    assert 0.0 < bias.mean_center_distance < 1.0
    assert bias.entropy_bits == 2.0
