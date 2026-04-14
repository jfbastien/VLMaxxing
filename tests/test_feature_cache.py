from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from codec_through.feature_cache import (
    CACHE_KEY_SCHEMA_VERSION,
    CacheKey,
    frame_sequence_sha256,
    get_feature_cache,
    model_content_sha256,
    preprocessing_hash,
    put_feature_cache,
)


def _solid_frame(color: tuple[int, int, int]) -> Image.Image:
    return Image.new("RGB", (8, 8), color=color)


def _make_key(
    *,
    model_id: str = "model-a",
    model_content_sha256: str = "0" * 64,
    item_id: str = "item-1",
    frames_sha256: str = "abc123",
) -> CacheKey:
    return CacheKey(
        model_id=model_id,
        model_content_sha256=model_content_sha256,
        item_id=item_id,
        frames_sha256=frames_sha256,
        frame_count=8,
        frame_size_h=560,
        frame_size_w=560,
        preprocessing_hash=preprocessing_hash(
            decode_backend="pyav",
            sampling_mode="uniform_global",
            max_size=560,
        ),
    )


def test_frame_sequence_sha256_changes_with_pixels_and_order() -> None:
    red = _solid_frame((255, 0, 0))
    blue = _solid_frame((0, 0, 255))

    first = frame_sequence_sha256([red, blue])
    second = frame_sequence_sha256([blue, red])
    third = frame_sequence_sha256([red, red])

    assert first != second
    assert first != third


def test_feature_cache_round_trip(tmp_path: Path) -> None:
    key = _make_key()
    features = np.arange(24, dtype=np.float16).reshape(3, 8)
    image_grid_thw = np.array([[1, 20, 20], [1, 20, 20]], dtype=np.int64)
    meta = {"item_id": "item-1", "model_id": "model-a", "model_content_sha256": "0" * 64}

    path = put_feature_cache(
        key,
        features=features,
        image_grid_thw=image_grid_thw,
        meta=meta,
        cache_dir=tmp_path,
    )
    loaded = get_feature_cache(key, cache_dir=tmp_path)

    assert path == tmp_path / f"{key.digest()}.npz"
    assert loaded is not None
    loaded_features, loaded_grid, loaded_meta = loaded
    np.testing.assert_array_equal(loaded_features, features)
    np.testing.assert_array_equal(loaded_grid, image_grid_thw)
    assert loaded_meta == meta


def test_cache_key_changes_with_model_content_hash(tmp_path: Path) -> None:
    key_a = _make_key(model_content_sha256="a" * 64)
    key_b = _make_key(model_content_sha256="b" * 64)
    assert key_a.digest() != key_b.digest()

    features = np.ones((4, 8), dtype=np.float16)
    grid = np.array([[1, 20, 20]], dtype=np.int64)
    put_feature_cache(key_a, features=features, image_grid_thw=grid, meta={}, cache_dir=tmp_path)

    # hit on A, miss on B
    assert get_feature_cache(key_a, cache_dir=tmp_path) is not None
    assert get_feature_cache(key_b, cache_dir=tmp_path) is None


def test_cache_key_schema_version_in_digest() -> None:
    assert CACHE_KEY_SCHEMA_VERSION == "v2"


def test_model_content_sha256_is_deterministic_and_distinguishes_contents(tmp_path: Path) -> None:
    model_a = tmp_path / "model_a"
    model_a.mkdir()
    (model_a / "config.json").write_text('{"model_type": "test"}\n')
    (model_a / "weights.safetensors").write_bytes(b"alpha-weights")

    model_b = tmp_path / "model_b"
    model_b.mkdir()
    (model_b / "config.json").write_text('{"model_type": "test"}\n')
    (model_b / "weights.safetensors").write_bytes(b"beta-weights")

    # repeatable
    assert model_content_sha256(model_a) == model_content_sha256(model_a)
    # distinguishes content
    assert model_content_sha256(model_a) != model_content_sha256(model_b)


def test_model_content_sha256_ignores_unrelated_files(tmp_path: Path) -> None:
    model = tmp_path / "m"
    model.mkdir()
    (model / "config.json").write_text("{}\n")
    (model / "weights.safetensors").write_bytes(b"W")

    before = model_content_sha256(model)
    (model / "README.md").write_text("hello")
    (model / "training_log.txt").write_text("noise")
    after = model_content_sha256(model)
    assert before == after


def test_model_content_sha256_rejects_missing_and_empty(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        model_content_sha256(tmp_path / "nope")
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(ValueError):
        model_content_sha256(empty)
