from __future__ import annotations

from typing import cast

import pytest

from tests._mlx_probe import mlx_is_usable

if not mlx_is_usable():
    pytest.skip(
        "mlx.core not usable on this host (import or Metal-init fails); see tests/_mlx_probe.py",
        allow_module_level=True,
    )

import mlx.core as mx

from codec_through.pruned_vision_tower import _keep_indices, magnitude_valid_keep_mask


def test_keep_indices_hard_fails_variable_row_counts() -> None:
    keep_mask = mx.array(
        [
            [True, False, True, False],
            [False, True, False, False],
        ]
    )

    with pytest.raises(ValueError, match="uniform across rows"):
        _keep_indices(keep_mask)


def test_keep_indices_hard_fails_empty_rows() -> None:
    keep_mask = mx.array(
        [
            [False, False, False],
            [False, False, False],
        ]
    )

    with pytest.raises(ValueError, match="at least one token"):
        _keep_indices(keep_mask)


def test_keep_indices_hard_fails_bad_rank() -> None:
    keep_mask = mx.array([True, False, True])

    with pytest.raises(ValueError, match="2D"):
        _keep_indices(keep_mask)


def test_keep_indices_accepts_uniform_row_counts() -> None:
    keep_mask = mx.array(
        [
            [True, False, True, False],
            [False, True, False, True],
        ]
    )

    indices = _keep_indices(keep_mask)

    assert indices.shape == (2, 2)
    rows = cast(list[list[int]], indices.tolist())
    assert [sorted(row) for row in rows] == [[0, 2], [1, 3]]


def test_magnitude_valid_keep_mask_never_selects_padded_positions() -> None:
    hidden = mx.array(
        [
            [
                [1.0],
                [2.0],
                [3.0],
                [1000.0],
                [900.0],
                [800.0],
            ]
        ]
    )
    positions = mx.array(
        [
            [
                [0, 0],
                [0, 1],
                [0, 2],
                [-1, -1],
                [-1, -1],
                [-1, -1],
            ]
        ]
    )

    keep = magnitude_valid_keep_mask(hidden, positions, keep_rate=2 / 3)

    kept = cast(list[list[bool]], keep.tolist())
    assert kept == [[False, True, True, False, False, False]]


def test_magnitude_valid_keep_mask_hard_fails_nonuniform_k() -> None:
    hidden = mx.array(
        [
            [[1.0], [2.0], [3.0], [4.0]],
            [[1.0], [2.0], [3.0], [4.0]],
        ]
    )
    positions = mx.array(
        [
            [[0, 0], [0, 1], [0, 2], [-1, -1]],
            [[0, 0], [0, 1], [0, 2], [0, 3]],
        ]
    )

    with pytest.raises(ValueError, match="uniform K"):
        magnitude_valid_keep_mask(hidden, positions, keep_rate=0.5)
