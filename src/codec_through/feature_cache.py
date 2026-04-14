"""Dense feature cache for repeated Track A benchmark reruns."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
from PIL import Image

FeatureArray = npt.NDArray[Any]
GridArray = npt.NDArray[np.int64]

DEFAULT_FEATURE_CACHE_DIR = Path("research/cache/dense_features")


@dataclass(frozen=True, slots=True)
class CacheKey:
    """Identity for a cached dense-vision feature tensor."""

    model_id: str
    item_id: str
    frames_sha256: str
    frame_count: int
    frame_size_h: int
    frame_size_w: int
    preprocessing_hash: str

    def digest(self) -> str:
        payload = "|".join(
            [
                self.model_id,
                self.item_id,
                self.frames_sha256,
                str(self.frame_count),
                f"{self.frame_size_h}x{self.frame_size_w}",
                self.preprocessing_hash,
            ]
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]

    def path(self, *, cache_dir: Path = DEFAULT_FEATURE_CACHE_DIR) -> Path:
        return cache_dir / f"{self.digest()}.npz"


def preprocessing_hash(
    *,
    decode_backend: str,
    sampling_mode: str,
    max_size: int,
) -> str:
    """Hash the decode and preprocessing contract into a compact token."""

    payload = f"{decode_backend}|{sampling_mode}|{max_size}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def frame_sequence_sha256(frames: Sequence[Image.Image]) -> str:
    """Hash a sequence of preprocessed frames into a stable cache key."""

    digest = hashlib.sha256()
    for index, frame in enumerate(frames):
        width, height = frame.size
        digest.update(index.to_bytes(4, "little"))
        digest.update(width.to_bytes(4, "little"))
        digest.update(height.to_bytes(4, "little"))
        digest.update(frame.mode.encode("utf-8"))
        digest.update(frame.tobytes())
    return digest.hexdigest()


def put_feature_cache(
    key: CacheKey,
    *,
    features: FeatureArray,
    image_grid_thw: GridArray,
    meta: Mapping[str, Any],
    cache_dir: Path = DEFAULT_FEATURE_CACHE_DIR,
) -> Path:
    """Persist dense features, image grid metadata, and cache provenance."""

    path = key.path(cache_dir=cache_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        path,
        features=np.asarray(features),
        image_grid_thw=np.asarray(image_grid_thw, dtype=np.int64),
        meta_json=np.asarray(json.dumps(dict(meta), sort_keys=True)),
    )
    return path


def get_feature_cache(
    key: CacheKey,
    *,
    cache_dir: Path = DEFAULT_FEATURE_CACHE_DIR,
) -> tuple[FeatureArray, GridArray, dict[str, Any]] | None:
    """Load cached dense features, or return ``None`` on miss."""

    path = key.path(cache_dir=cache_dir)
    if not path.exists():
        return None
    with np.load(path, allow_pickle=False) as data:
        features = np.asarray(data["features"])
        image_grid_thw = np.asarray(data["image_grid_thw"], dtype=np.int64)
        meta_json = str(np.asarray(data["meta_json"]).item())
    meta = json.loads(meta_json)
    if not isinstance(meta, dict):
        raise ValueError(f"cached metadata must decode to a dict, got {type(meta)!r}")
    return features, image_grid_thw, meta
