from __future__ import annotations

import pytest

from tests._mlx_probe import mlx_is_usable

if not mlx_is_usable():
    pytest.skip(
        "mlx.core not usable on this host (import or Metal-init fails); see tests/_mlx_probe.py",
        allow_module_level=True,
    )

import mlx.core as mx

from codec_through.pruned_vision_tower import _keep_indices


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


def test_keep_indices_accepts_uniform_row_counts() -> None:
    keep_mask = mx.array(
        [
            [True, False, True, False],
            [False, True, False, True],
        ]
    )

    indices = _keep_indices(keep_mask)

    assert indices.shape == (2, 2)
    assert indices.tolist() == [[0, 2], [1, 3]]
