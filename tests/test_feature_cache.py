from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from codec_through.feature_cache import (
    CacheKey,
    frame_sequence_sha256,
    get_feature_cache,
    preprocessing_hash,
    put_feature_cache,
)


def _solid_frame(color: tuple[int, int, int]) -> Image.Image:
    return Image.new("RGB", (8, 8), color=color)


def test_frame_sequence_sha256_changes_with_pixels_and_order() -> None:
    red = _solid_frame((255, 0, 0))
    blue = _solid_frame((0, 0, 255))

    first = frame_sequence_sha256([red, blue])
    second = frame_sequence_sha256([blue, red])
    third = frame_sequence_sha256([red, red])

    assert first != second
    assert first != third


def test_feature_cache_round_trip(tmp_path: Path) -> None:
    key = CacheKey(
        model_id="model-a",
        item_id="item-1",
        frames_sha256="abc123",
        frame_count=8,
        frame_size_h=560,
        frame_size_w=560,
        preprocessing_hash=preprocessing_hash(
            decode_backend="pyav",
            sampling_mode="uniform_global",
            max_size=560,
        ),
    )
    features = np.arange(24, dtype=np.float16).reshape(3, 8)
    image_grid_thw = np.array([[1, 20, 20], [1, 20, 20]], dtype=np.int64)
    meta = {"item_id": "item-1", "model_id": "model-a"}

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
