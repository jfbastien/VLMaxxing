from __future__ import annotations

from types import SimpleNamespace

import mlx.core as mx
import numpy as np
import pytest
from PIL import Image

from codec_through.pruned_vision_tower import (
    PruneConfig,
    _PrunedEncoderWrapper,
    score_keep_mask,
)
from scripts.run_phase1_63G_gemma_track_b import (
    GEMMA_GRID_SHAPE,
    _resize_square_with_active_box,
    _validate_gemma_placeholders,
)


def test_gemma_codec_grid_keep_mask_is_per_frame_topk() -> None:
    hidden = mx.zeros((2, 4, 3))
    positions = mx.zeros((2, 4, 2))
    config = PruneConfig(layer_idx=0, keep_rate=0.5, score_mode="codec_grid")
    grid = np.array([[0.0, 1.0, 9.0, 2.0], [7.0, 0.0, 1.0, 8.0]], dtype=np.float32)

    mask = score_keep_mask(hidden, positions, config, grid)

    assert np.asarray(mask).tolist() == [[False, False, True, True], [True, False, False, True]]


def test_gemma_codec_grid_rejects_shape_mismatch() -> None:
    hidden = mx.zeros((2, 4, 3))
    positions = mx.zeros((2, 4, 2))
    config = PruneConfig(layer_idx=0, keep_rate=0.5, score_mode="codec_grid")

    with pytest.raises(ValueError, match="Gemma expects 8"):
        score_keep_mask(hidden, positions, config, np.ones(7, dtype=np.float32))


def test_gemma_codec_grid_rejects_nan_and_negative() -> None:
    wrapper = _PrunedEncoderWrapper(
        SimpleNamespace(layers=[object()]),
        PruneConfig(layer_idx=0, keep_rate=0.5, score_mode="codec_grid"),
    )

    with pytest.raises(ValueError, match="non-finite"):
        wrapper.set_codec_score_grid(np.array([np.nan], dtype=np.float32))
    with pytest.raises(ValueError, match="negative"):
        wrapper.set_codec_score_grid(np.array([-1.0], dtype=np.float32))


def test_gemma_uniform_random_keep_mask_is_seed_stable() -> None:
    hidden = mx.zeros((1, 8, 3))
    positions = mx.zeros((1, 8, 2))
    config = PruneConfig(layer_idx=0, keep_rate=0.5, score_mode="uniform_random", score_seed=7)

    first = np.asarray(score_keep_mask(hidden, positions, config, None))
    second = np.asarray(score_keep_mask(hidden, positions, config, None))

    assert first.tolist() == second.tolist()
    assert int(first.sum()) == 4


def test_gemma_resize_square_preserves_scaled_active_box() -> None:
    image = Image.new("RGB", (560, 560))
    resized, active_box = _resize_square_with_active_box(image, (56, 112, 504, 448))

    assert resized.size == (512, 512)
    assert active_box == (51, 102, 461, 410)


def test_gemma_placeholder_guard_uses_runtime_grid_shape() -> None:
    image_token_id = 99
    model = SimpleNamespace(config=SimpleNamespace(image_token_id=image_token_id))
    frame_count = 2
    expected = frame_count * GEMMA_GRID_SHAPE[0] * GEMMA_GRID_SHAPE[1]
    raw = {"input_ids": np.full((1, expected), image_token_id, dtype=np.int64)}

    _validate_gemma_placeholders(model, raw, frame_count=frame_count)

    raw_bad = {"input_ids": np.full((1, expected - 1), image_token_id, dtype=np.int64)}
    with pytest.raises(RuntimeError, match="placeholder-count mismatch"):
        _validate_gemma_placeholders(model, raw_bad, frame_count=frame_count)
