"""Dense feature cache for repeated Track A benchmark reruns."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
from PIL import Image

FeatureArray = npt.NDArray[Any]
GridArray = npt.NDArray[np.int64]

DEFAULT_FEATURE_CACHE_DIR = Path("research/cache/dense_features")

CACHE_KEY_SCHEMA_VERSION = "v2"
"""Bumped when `CacheKey` semantics change.

v1 used `model_id` as a path string. v2 adds `model_content_sha256` so an
in-place model swap invalidates the cache. Existing v1 entries are orphaned
and need a one-time prune.
"""

_MODEL_CONTENT_HASH_CHUNK = 1024 * 1024


@dataclass(frozen=True, slots=True)
class CacheKey:
    """Identity for a cached dense-vision feature tensor."""

    model_id: str
    model_content_sha256: str
    item_id: str
    frames_sha256: str
    frame_count: int
    frame_size_h: int
    frame_size_w: int
    preprocessing_hash: str

    def digest(self) -> str:
        payload = "|".join(
            [
                CACHE_KEY_SCHEMA_VERSION,
                self.model_id,
                self.model_content_sha256,
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


def model_content_sha256(model_path: Path, *, patterns: Iterable[str] | None = None) -> str:
    """Hash the binary content of a local MLX-VLM model directory.

    Hashes the bytes of every file matching ``patterns`` (default: weight and
    config files) after sorting by relative path, so directory ordering does
    not affect the result. Two models with identical weights produce the same
    hash regardless of where they are stored.
    """

    if not model_path.exists():
        raise FileNotFoundError(f"model_path does not exist: {model_path}")
    if not model_path.is_dir():
        raise ValueError(f"model_path must be a directory, got {model_path}")

    if patterns is None:
        patterns = (
            "*.safetensors",
            "*.npz",
            "*.bin",
            "*.gguf",
            "config.json",
            "tokenizer.json",
            "tokenizer_config.json",
            "preprocessor_config.json",
            "processor_config.json",
            "added_tokens.json",
            "special_tokens_map.json",
        )

    paths: list[Path] = []
    seen: set[Path] = set()
    for pattern in patterns:
        for candidate in model_path.rglob(pattern):
            if candidate.is_file() and candidate not in seen:
                paths.append(candidate)
                seen.add(candidate)
    if not paths:
        raise ValueError(f"no weight or config files matched under {model_path}")

    paths.sort(key=lambda candidate: candidate.relative_to(model_path).as_posix())
    digest = hashlib.sha256()
    for candidate in paths:
        rel = candidate.relative_to(model_path).as_posix().encode("utf-8")
        digest.update(len(rel).to_bytes(4, "little"))
        digest.update(rel)
        size = candidate.stat().st_size
        digest.update(size.to_bytes(8, "little"))
        with candidate.open("rb") as handle:
            while True:
                chunk = handle.read(_MODEL_CONTENT_HASH_CHUNK)
                if not chunk:
                    break
                digest.update(chunk)
    return digest.hexdigest()


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
