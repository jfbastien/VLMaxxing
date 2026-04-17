"""Tests for phase 1.37B Planner 2.1A neighbor-halo veto.

Note: the original "child-veto" name was a mechanism misnomer — the
implementation scans the (2N+1)×(2N+1) neighborhood of parent blocks, not
within-block 2×2 sub-children. The true within-block child-veto is phase
1.37 and remains unimplemented (see
`research/experiments/2026/2026-04-16-phase-1_37-child-veto-subtoken-guard.md`).
"""

from __future__ import annotations

import numpy as np
import pytest

from codec_through.temporal import (
    BlockClass,
    NeighborHaloVetoConfig,
    _neighborhood_max,
    apply_neighbor_halo_veto,
)


def test_neighborhood_max_excludes_self_by_default() -> None:
    values = np.array(
        [
            [0.0, 0.0, 0.0],
            [0.0, 5.0, 0.0],
            [0.0, 0.0, 0.0],
        ],
        dtype=np.float32,
    )
    # With include_self=False, center cell's OWN value does not leak into its own max.
    out = _neighborhood_max(values, neighborhood=1, include_self=False)
    # Center cell has no hot neighbors, so its neighborhood max is 0.
    assert out[1, 1] == 0.0
    # All 8 surrounding cells see the center value 5.0 as a neighbor.
    for r in range(3):
        for c in range(3):
            if (r, c) != (1, 1):
                assert out[r, c] == 5.0


def test_neighborhood_max_includes_self_when_asked() -> None:
    values = np.array(
        [
            [1.0, 2.0],
            [3.0, 4.0],
        ],
        dtype=np.float32,
    )
    out = _neighborhood_max(values, neighborhood=1, include_self=True)
    # Each cell with neighborhood=1 and include_self=True sees the global max of
    # its own 2x2 block, which is 4.0 for this tiny grid.
    assert np.all(out == 4.0)


def test_neighborhood_max_edges_use_padding() -> None:
    values = np.array(
        [
            [0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0],
            [0.0, 0.0, 10.0],
        ],
        dtype=np.float32,
    )
    out = _neighborhood_max(values, neighborhood=1, include_self=False)
    # (2,2) has no in-bounds neighbors with real values that are > 0, so its
    # max-over-neighbors is 0 (padding is -inf).
    assert out[2, 2] == 0.0
    # (1,1) is fully surrounded and sees 10 at (2,2).
    assert out[1, 1] == 10.0
    # (0,0) is far from 10 and all its neighbors are zero or padding.
    assert out[0, 0] == 0.0


def test_halo_veto_promotes_static_next_to_hot_block() -> None:
    # 3x3 grid: center block is hot, all others are low.
    scores = np.array(
        [
            [0.1, 0.1, 0.1],
            [0.1, 9.0, 0.1],
            [0.1, 0.1, 0.1],
        ],
        dtype=np.float32,
    )
    classification = np.full(scores.shape, int(BlockClass.STATIC), dtype=np.int32)
    classification[1, 1] = int(BlockClass.NOVEL)  # the hot cell was already NOVEL
    cfg = NeighborHaloVetoConfig(percentile=0.5, neighborhood=1)

    out = apply_neighbor_halo_veto(classification, scores, config=cfg)
    # Threshold = median = 0.1. Neighbors of the hot cell see 9.0 > 0.1, so
    # all 8 surrounding STATIC blocks get promoted to NOVEL.
    expected = np.full(scores.shape, int(BlockClass.NOVEL), dtype=np.int32)
    np.testing.assert_array_equal(out, expected)


def test_halo_veto_leaves_shifted_alone() -> None:
    scores = np.array(
        [
            [9.0, 0.1],
            [0.1, 0.1],
        ],
        dtype=np.float32,
    )
    classification = np.array(
        [
            [int(BlockClass.NOVEL), int(BlockClass.SHIFTED)],
            [int(BlockClass.SHIFTED), int(BlockClass.STATIC)],
        ],
        dtype=np.int32,
    )
    cfg = NeighborHaloVetoConfig(percentile=0.5, neighborhood=1)

    out = apply_neighbor_halo_veto(classification, scores, config=cfg)
    # SHIFTED cells stay SHIFTED; only the STATIC at (1,1) might flip.
    assert out[0, 1] == int(BlockClass.SHIFTED)
    assert out[1, 0] == int(BlockClass.SHIFTED)
    # (1,1) STATIC has neighbor (0,0)=9.0 > median 0.1, so it flips to NOVEL.
    assert out[1, 1] == int(BlockClass.NOVEL)
    assert out[0, 0] == int(BlockClass.NOVEL)


def test_halo_veto_does_not_promote_when_no_hot_neighbor() -> None:
    # Uniformly low scores: threshold is also low, but neighbor max is not
    # strictly greater than it, so no promotion.
    scores = np.full((3, 3), 0.5, dtype=np.float32)
    classification = np.full(scores.shape, int(BlockClass.STATIC), dtype=np.int32)
    cfg = NeighborHaloVetoConfig(percentile=0.95, neighborhood=1)

    out = apply_neighbor_halo_veto(classification, scores, config=cfg)
    # Threshold = 0.5 (uniform). Neighbor max is also 0.5. Not strictly greater.
    np.testing.assert_array_equal(out, classification)


def test_halo_veto_shape_mismatch_raises() -> None:
    classification = np.zeros((3, 3), dtype=np.int32)
    scores = np.zeros((3, 4), dtype=np.float32)
    with pytest.raises(ValueError, match="shape"):
        apply_neighbor_halo_veto(
            classification,
            scores,
            config=NeighborHaloVetoConfig(percentile=0.9, neighborhood=1),
        )


def test_halo_veto_bad_percentile_raises() -> None:
    classification = np.zeros((3, 3), dtype=np.int32)
    scores = np.zeros((3, 3), dtype=np.float32)
    with pytest.raises(ValueError, match="percentile"):
        apply_neighbor_halo_veto(
            classification,
            scores,
            config=NeighborHaloVetoConfig(percentile=1.5, neighborhood=1),
        )


def test_halo_veto_respects_neighborhood_radius() -> None:
    # 5x5 grid, hot at (0,0). With neighborhood=1, only (0,1), (1,0), (1,1)
    # see it. With neighborhood=2, cells up to 2 away see it.
    scores = np.full((5, 5), 0.1, dtype=np.float32)
    scores[0, 0] = 9.0
    classification = np.full(scores.shape, int(BlockClass.STATIC), dtype=np.int32)
    classification[0, 0] = int(BlockClass.NOVEL)

    out1 = apply_neighbor_halo_veto(
        classification, scores, config=NeighborHaloVetoConfig(percentile=0.5, neighborhood=1)
    )
    # Only direct neighbors of (0,0) flip.
    flipped_1 = [(r, c) for r in range(5) for c in range(5) if out1[r, c] == int(BlockClass.NOVEL)]
    assert set(flipped_1) == {(0, 0), (0, 1), (1, 0), (1, 1)}

    out2 = apply_neighbor_halo_veto(
        classification, scores, config=NeighborHaloVetoConfig(percentile=0.5, neighborhood=2)
    )
    flipped_2 = [(r, c) for r in range(5) for c in range(5) if out2[r, c] == int(BlockClass.NOVEL)]
    assert set(flipped_2) == {
        (0, 0),
        (0, 1),
        (0, 2),
        (1, 0),
        (1, 1),
        (1, 2),
        (2, 0),
        (2, 1),
        (2, 2),
    }


def test_halo_veto_pure_function_does_not_mutate_inputs() -> None:
    scores = np.array(
        [
            [0.1, 9.0],
            [0.1, 0.1],
        ],
        dtype=np.float32,
    )
    classification = np.array(
        [
            [int(BlockClass.STATIC), int(BlockClass.NOVEL)],
            [int(BlockClass.STATIC), int(BlockClass.STATIC)],
        ],
        dtype=np.int32,
    )
    classification_before = classification.copy()
    scores_before = scores.copy()

    apply_neighbor_halo_veto(
        classification, scores, config=NeighborHaloVetoConfig(percentile=0.5, neighborhood=1)
    )
    np.testing.assert_array_equal(classification, classification_before)
    np.testing.assert_array_equal(scores, scores_before)
