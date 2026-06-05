# ruff: noqa: E402

from __future__ import annotations

import sys
from typing import cast

import pytest


def _is_darwin() -> bool:
    return sys.platform == "darwin"


if not _is_darwin():
    pytest.skip("MLX tests require macOS/Darwin", allow_module_level=True)

import mlx.core as mx

from codec_through.pruned_vision_tower import (
    PruneConfig,
    _keep_indices,
    magnitude_valid_keep_mask,
    make_pruned_encoder_call,
)


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


def test_pruned_encoder_call_handles_variable_row_keep_counts() -> None:
    class FakeLayer:
        def __init__(self, offset: float) -> None:
            self.offset = offset
            self.calls: list[tuple[int, ...]] = []

        def __call__(self, hidden: mx.array, positions: mx.array, mask: mx.array) -> mx.array:
            del positions, mask
            self.calls.append(tuple(int(value) for value in hidden.shape))
            return hidden + self.offset

    class FakeEncoder:
        def __init__(self) -> None:
            self.layers = [FakeLayer(0.0), FakeLayer(10.0)]

    encoder = FakeEncoder()
    call = make_pruned_encoder_call(
        encoder,
        PruneConfig(layer_idx=0, keep_rate=0.5),
        lambda _hidden, _positions: mx.array(
            [
                [True, True, False, False],
                [True, False, False, False],
            ]
        ),
    )
    hidden = mx.array([[[1.0], [2.0], [3.0], [4.0]], [[5.0], [6.0], [7.0], [8.0]]])
    positions = mx.array(
        [
            [[0, 0], [1, 0], [2, 0], [3, 0]],
            [[0, 1], [1, 1], [2, 1], [3, 1]],
        ]
    )
    mask = mx.zeros((2, 1, 4, 4))

    output = call(hidden, positions, mask)

    assert tuple(int(value) for value in output.shape) == (2, 4, 1)
    assert encoder.layers[0].calls == [(2, 4, 1)]
    assert encoder.layers[1].calls == [(1, 2, 1), (1, 1, 1)]
    values = cast(list[list[list[float]]], output.tolist())
    assert values == [[[11.0], [12.0], [0.0], [0.0]], [[15.0], [0.0], [0.0], [0.0]]]


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
