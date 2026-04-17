"""Unit tests for the phase 1.36 feature-change oracle helpers."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "feature_change_oracle.py"
MODULE_NAME = "_feature_change_oracle_under_test"


def _load_module():
    if MODULE_NAME in sys.modules:
        return sys.modules[MODULE_NAME]
    spec = importlib.util.spec_from_file_location(MODULE_NAME, SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot build spec for {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[MODULE_NAME] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(MODULE_NAME, None)
        raise
    return module


ORACLE = _load_module()


def test_rankdata_handles_ties() -> None:
    # [10, 20, 20, 30] -> ranks [1, 2.5, 2.5, 4]
    result = ORACLE._rankdata(np.array([10.0, 20.0, 20.0, 30.0]))
    np.testing.assert_allclose(result, np.array([1.0, 2.5, 2.5, 4.0]))


def test_rankdata_matches_sorted_input() -> None:
    # monotone input should yield sequential ranks
    result = ORACLE._rankdata(np.array([5.0, 10.0, 15.0, 20.0]))
    np.testing.assert_allclose(result, np.array([1.0, 2.0, 3.0, 4.0]))


def test_pearson_identity() -> None:
    x = np.arange(10, dtype=np.float64)
    y = 2.0 * x + 3.0
    assert ORACLE._pearson(x, y) == pytest.approx(1.0)


def test_pearson_zero_variance() -> None:
    x = np.ones(5, dtype=np.float64)
    y = np.arange(5, dtype=np.float64)
    assert np.isnan(ORACLE._pearson(x, y))


def test_spearman_monotone_nonlinear() -> None:
    # spearman should be 1.0 even when pearson < 1.0 for a monotone transform
    x = np.arange(1, 6, dtype=np.float64)
    y = x**3
    assert ORACLE._spearman(x, y) == pytest.approx(1.0)


def test_features_per_frame_shapes() -> None:
    # 2 frames, grid_thw = [1, 4, 4] each -> 2*2 merged tokens per frame = 4
    grid = np.array([[1, 4, 4], [1, 4, 4]], dtype=np.int64)
    # token feature dim 3 for readability
    features = np.arange(2 * 4 * 3, dtype=np.float32).reshape(8, 3)
    per_frame = ORACLE._features_per_frame(features, grid)
    assert len(per_frame) == 2
    assert per_frame[0].shape == (2, 2, 3)
    assert per_frame[1].shape == (2, 2, 3)
    np.testing.assert_array_equal(
        per_frame[0].reshape(4, 3),
        features[0:4],
    )
    np.testing.assert_array_equal(
        per_frame[1].reshape(4, 3),
        features[4:8],
    )


def test_features_per_frame_rejects_token_mismatch() -> None:
    # 8 tokens of features, but grid says we'd need 4 + 4 = 8, then pad an
    # extra row to trigger a token-count mismatch
    grid = np.array([[1, 4, 4], [1, 4, 4]], dtype=np.int64)
    features = np.zeros((9, 3), dtype=np.float32)  # off by one
    with pytest.raises(RuntimeError):
        ORACLE._features_per_frame(features, grid)


def test_pairwise_cosine_identical_frames_zero() -> None:
    a = np.random.default_rng(42).standard_normal((3, 3, 8)).astype(np.float32)
    distances = ORACLE._pairwise_cosine(a, a.copy())
    np.testing.assert_allclose(distances, 0.0, atol=1e-5)


def test_pairwise_cosine_opposite_frames_two() -> None:
    a = np.ones((2, 2, 4), dtype=np.float32)
    b = -a
    distances = ORACLE._pairwise_cosine(a, b)
    np.testing.assert_allclose(distances, 2.0, atol=1e-5)


def test_pairwise_cosine_shape_mismatch_rejected() -> None:
    a = np.zeros((2, 2, 4), dtype=np.float32)
    b = np.zeros((3, 2, 4), dtype=np.float32)
    with pytest.raises(RuntimeError):
        ORACLE._pairwise_cosine(a, b)
