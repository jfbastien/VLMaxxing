"""Unit tests for novelty-ranked dense selection helpers."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import numpy as np
import pytest

pytest.importorskip("mlx.core", reason="mlx is Apple-only; skipping on non-MLX hosts")

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_novelty_ranked_dense.py"
MODULE_NAME = "_novelty_under_test"


def _load_module() -> ModuleType:
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


NOVELTY = _load_module()


def test_select_top_novel_time_ordered() -> None:
    scores = np.array([0.0, 5.0, 1.0, 10.0, 2.0, 8.0], dtype=np.float32)
    selected = NOVELTY._select_top_novel(scores, frame_count=3, force_first=True)
    # Force-first keeps 0; top scores (excluding 0) are at 3 (10.0), 5 (8.0)
    assert selected == [0, 3, 5]


def test_select_top_novel_without_force_first() -> None:
    scores = np.array([0.0, 5.0, 1.0, 10.0, 2.0, 8.0], dtype=np.float32)
    selected = NOVELTY._select_top_novel(scores, frame_count=3, force_first=False)
    # Top three: 3 (10), 5 (8), 1 (5) -> sorted: [1, 3, 5]
    assert selected == [1, 3, 5]


def test_select_top_novel_rejects_out_of_range() -> None:
    scores = np.zeros(4, dtype=np.float32)
    with pytest.raises(ValueError):
        NOVELTY._select_top_novel(scores, frame_count=5, force_first=True)
    with pytest.raises(ValueError):
        NOVELTY._select_top_novel(scores, frame_count=0, force_first=True)


def test_select_top_novel_always_full_budget() -> None:
    scores = np.array([10.0, 1.0, 1.0, 1.0], dtype=np.float32)
    selected = NOVELTY._select_top_novel(scores, frame_count=3, force_first=True)
    assert len(selected) == 3
    assert 0 in selected


def test_select_top_novel_handles_ties() -> None:
    scores = np.array([1.0, 1.0, 1.0, 1.0, 1.0], dtype=np.float32)
    # mergesort is stable; with force_first=True, frame 0 is prepended,
    # then remaining ties get their original order (1, 2).
    selected = NOVELTY._select_top_novel(scores, frame_count=3, force_first=True)
    assert selected == [0, 1, 2]


def test_per_frame_novelty_shape_matches_frames() -> None:
    rng = np.random.default_rng(0)

    class FakePil:
        def __init__(self, arr: np.ndarray) -> None:
            self._arr = arr
            self.size = (arr.shape[1], arr.shape[0])

        def __array__(self, dtype: np.dtype | None = None) -> np.ndarray:
            if dtype is None:
                return self._arr
            return self._arr.astype(dtype)

    fakes = [FakePil(rng.integers(0, 255, (28, 28, 3), dtype=np.uint8)) for _ in range(4)]
    scores = NOVELTY._per_frame_novelty(fakes, statistic=NOVELTY.BlockStatistic.MAX_ABS)
    assert scores.shape == (4,)
    # All frames should have non-zero novelty with random frames.
    assert np.all(scores > 0)
