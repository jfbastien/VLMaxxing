# ruff: noqa: E402

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from PIL import Image


def _is_darwin() -> bool:
    return sys.platform == "darwin"


if not _is_darwin():
    pytest.skip("MLX tests require macOS/Darwin", allow_module_level=True)

import mlx.core as mx

from codec_through.codec.continuous_score import CodecScoreSource
from codec_through.codec.score_sidecar import (
    SCORE_SIDECAR_PROJECTION_VERSION,
    score_config_id,
    sidecar_path,
    write_score_sidecar,
)
from codec_through.pruned_vision_tower import (
    PruneConfig,
    _PrunedEncoderWrapper,
    score_keep_mask,
)
from scripts.run_phase1_63G_gemma_track_b import (
    GEMMA_IMAGE_SIZE,
    GEMMA_PATCH_GRID_SHAPE,
    GEMMA_SIDECAR_GEOMETRY,
    GEMMA_SOFT_GRID_SHAPE,
    GemmaCodecGeometry,
    _load_gemma_sidecar_scores,
    _resize_square_with_active_box,
    _stack_gemma_codec_score_grid,
    _validate_gemma_placeholders,
)

GEOMETRY = GemmaCodecGeometry(
    image_size=GEMMA_IMAGE_SIZE,
    soft_grid_shape=GEMMA_SOFT_GRID_SHAPE,
    patch_grid_shape=GEMMA_PATCH_GRID_SHAPE,
    patch_size=16,
    pooling_kernel_size=3,
    max_patches=2520,
)


def test_gemma_codec_grid_keep_mask_is_per_frame_topk() -> None:
    hidden = mx.zeros((2, 4, 3))
    positions = mx.zeros((2, 4, 2))
    config = PruneConfig(layer_idx=0, keep_rate=0.5, score_mode="codec_grid")
    grid = np.array([[0.0, 1.0, 9.0, 2.0], [7.0, 0.0, 1.0, 8.0]], dtype=np.float32)

    mask = score_keep_mask(hidden, positions, config, grid)

    assert np.asarray(mask).tolist() == [[False, False, True, True], [True, False, False, True]]


def test_gemma_codec_grid_keep_mask_excludes_padding_positions() -> None:
    hidden = mx.zeros((1, 6, 3))
    positions = mx.array([[[0, 0], [1, 0], [2, 0], [-1, -1], [-1, -1], [-1, -1]]])
    config = PruneConfig(layer_idx=0, keep_rate=0.5, score_mode="codec_grid")
    # Padding scores are deliberately high. They must still be ineligible.
    grid = np.array([[1.0, 3.0, 2.0, 999.0, 999.0, 999.0]], dtype=np.float32)

    mask = np.asarray(score_keep_mask(hidden, positions, config, grid))

    assert mask.tolist() == [[False, True, False, False, False, False]]


def test_gemma_runner_stacks_per_frame_codec_grids_for_encoder() -> None:
    first = np.arange(np.prod(GEMMA_PATCH_GRID_SHAPE), dtype=np.float32).reshape(
        GEMMA_PATCH_GRID_SHAPE
    )
    second = (first + 1000).astype(np.float32)

    stacked = _stack_gemma_codec_score_grid([first, second], geometry=GEOMETRY)

    assert stacked.shape == (2, GEOMETRY.max_patches)
    assert stacked.dtype == np.float32
    assert stacked[0, 0] == 0.0
    assert stacked[0, GEOMETRY.real_patches_per_frame - 1] == 2303.0
    assert stacked[0, GEOMETRY.real_patches_per_frame] == 0.0
    assert stacked[1, 0] == 1000.0


def test_gemma_codec_grid_rejects_shape_mismatch() -> None:
    hidden = mx.zeros((2, 4, 3))
    positions = mx.zeros((2, 4, 2))
    config = PruneConfig(layer_idx=0, keep_rate=0.5, score_mode="codec_grid")

    with pytest.raises(ValueError, match="Gemma expects 8"):
        score_keep_mask(hidden, positions, config, np.ones(7, dtype=np.float32))

    with pytest.raises(ValueError, match="frame 0 has shape"):
        _stack_gemma_codec_score_grid([np.ones((8, 32), dtype=np.float32)], geometry=GEOMETRY)


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


def test_gemma_wrapper_uses_encoder_length_grid_and_clears_state() -> None:
    class IdentityLayer:
        def __call__(
            self, hidden_states: mx.array, positions: mx.array, mask: mx.array
        ) -> mx.array:
            return hidden_states

    wrapper = _PrunedEncoderWrapper(
        SimpleNamespace(layers=[IdentityLayer(), IdentityLayer()]),
        PruneConfig(layer_idx=0, keep_rate=0.5, score_mode="codec_grid"),
    )
    hidden = mx.array([[[10.0], [20.0], [30.0], [40.0], [50.0], [60.0]]])
    positions = mx.array([[[0, 0], [1, 0], [2, 0], [-1, -1], [-1, -1], [-1, -1]]])
    mask = mx.zeros((1, 1, 6, 6))
    wrapper.set_codec_score_grid(np.array([[1.0, 3.0, 2.0, 999.0, 999.0, 999.0]], dtype=np.float32))

    output = np.asarray(wrapper(hidden, positions, mask)).reshape(6)

    assert output.tolist() == [0.0, 20.0, 0.0, 0.0, 0.0, 0.0]
    assert wrapper._codec_score_grid is None


def test_gemma_resize_square_preserves_scaled_active_box() -> None:
    image = Image.new("RGB", (560, 560))
    resized, active_box = _resize_square_with_active_box(image, (56, 112, 504, 448))

    assert resized.size == (768, 768)
    assert active_box == (77, 154, 691, 614)


def test_gemma_placeholder_guard_uses_runtime_grid_shape() -> None:
    image_token_id = 99
    model = SimpleNamespace(config=SimpleNamespace(image_token_id=image_token_id))
    frame_count = 2
    expected = frame_count * GEMMA_SOFT_GRID_SHAPE[0] * GEMMA_SOFT_GRID_SHAPE[1]
    raw = {"input_ids": np.full((1, expected), image_token_id, dtype=np.int64)}

    _validate_gemma_placeholders(model, raw, frame_count=frame_count, geometry=GEOMETRY)

    raw_bad = {"input_ids": np.full((1, expected - 1), image_token_id, dtype=np.int64)}
    with pytest.raises(RuntimeError, match="placeholder-count mismatch"):
        _validate_gemma_placeholders(model, raw_bad, frame_count=frame_count, geometry=GEOMETRY)


def test_gemma_sidecar_loader_accepts_padded_patch_grid(tmp_path: Path) -> None:
    item_id = "gemma/item"
    item = SimpleNamespace(item_id=item_id)
    geometry = GemmaCodecGeometry(
        image_size=32,
        soft_grid_shape=(1, 1),
        patch_grid_shape=(1, 2),
        patch_size=16,
        pooling_kernel_size=1,
        max_patches=4,
    )
    config_id = score_config_id(source="novel_coded", frame_count=2)
    path = sidecar_path(
        tmp_path,
        item_id=item_id,
        source="novel_coded",
        geometry=GEMMA_SIDECAR_GEOMETRY,
        score_config=config_id,
    )
    write_score_sidecar(
        path,
        score_grid=np.array([[1.0, 2.0, 0.0, 0.0], [3.0, 4.0, 0.0, 0.0]], dtype=np.float32),
        metadata={
            "item_id": item_id,
            "codec_score_source": "novel_coded",
            "geometry": GEMMA_SIDECAR_GEOMETRY,
            "frame_count": 2,
            "score_config_id": config_id,
            "score_projection_version": SCORE_SIDECAR_PROJECTION_VERSION,
        },
    )

    score_grid, load_s, metadata = _load_gemma_sidecar_scores(
        tmp_path,
        item,
        frame_count=2,
        codec_score_source=CodecScoreSource.NOVEL_CODED,
        geometry=geometry,
        score_config=config_id,
    )

    assert score_grid.shape == (2, 4)
    assert load_s >= 0.0
    assert metadata["score_config_id"] == config_id


def test_gemma_sidecar_loader_rejects_encoder_length_mismatch(tmp_path: Path) -> None:
    item_id = "gemma/item"
    item = SimpleNamespace(item_id=item_id)
    geometry = GemmaCodecGeometry(
        image_size=32,
        soft_grid_shape=(1, 1),
        patch_grid_shape=(1, 2),
        patch_size=16,
        pooling_kernel_size=1,
        max_patches=4,
    )
    config_id = score_config_id(source="novel_coded", frame_count=2)
    path = sidecar_path(
        tmp_path,
        item_id=item_id,
        source="novel_coded",
        geometry=GEMMA_SIDECAR_GEOMETRY,
        score_config=config_id,
    )
    write_score_sidecar(
        path,
        score_grid=np.ones((2, 3), dtype=np.float32),
        metadata={
            "item_id": item_id,
            "codec_score_source": "novel_coded",
            "geometry": GEMMA_SIDECAR_GEOMETRY,
            "frame_count": 2,
            "score_config_id": config_id,
            "score_projection_version": SCORE_SIDECAR_PROJECTION_VERSION,
        },
    )

    with pytest.raises(ValueError, match="expected"):
        _load_gemma_sidecar_scores(
            tmp_path,
            item,
            frame_count=2,
            codec_score_source=CodecScoreSource.NOVEL_CODED,
            geometry=geometry,
            score_config=config_id,
        )
