"""Precomputed codec-score sidecars for sparse-vision experiments."""

from __future__ import annotations

import json
import re
from hashlib import sha256
from pathlib import Path
from typing import Any, cast

import numpy as np

SIDECAR_SCHEMA = "codec_score_sidecar_v1"
DEFAULT_SCORE_CONFIG_ID = "default"
SCORE_SIDECAR_PROJECTION_VERSION = 1


def safe_item_id(item_id: str) -> str:
    """Return a filesystem-safe item identifier."""

    return re.sub(r"[^A-Za-z0-9_.-]+", "__", item_id).strip("_")


def score_config_id(
    *,
    source: str,
    frame_count: int,
    projection_version: int = SCORE_SIDECAR_PROJECTION_VERSION,
    fusion_mode: str = "weighted",
    motion_weight: float = 1.0,
    residual_weight: float = 1.0,
    normalize_fusion_inputs: bool = True,
) -> str:
    """Return a stable ID for the score-producing configuration.

    Simple codec sources ignore fusion knobs so they share the same path across
    irrelevant CLI defaults. The fused source includes the weights and
    normalization policy to prevent stale sidecars from being silently reused
    when the fusion recipe changes.
    """

    if frame_count <= 0:
        raise ValueError(f"frame_count must be positive, got {frame_count}")
    payload: dict[str, object] = {
        "source": source,
        "frame_count": int(frame_count),
        "projection_version": int(projection_version),
    }
    if source == "fused":
        payload.update(
            {
                "fusion_mode": fusion_mode,
                "motion_weight": float(motion_weight),
                "residual_weight": float(residual_weight),
                "normalize_fusion_inputs": bool(normalize_fusion_inputs),
            }
        )
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return digest[:16]


def sidecar_path(
    root: Path,
    *,
    item_id: str,
    source: str,
    geometry: str,
    score_config: str = DEFAULT_SCORE_CONFIG_ID,
) -> Path:
    return root / geometry / source / score_config / f"{safe_item_id(item_id)}.npz"


def score_grid_sha256(score_grid: np.ndarray) -> str:
    """Hash a normalized float32 score array including shape and dtype."""

    array = np.ascontiguousarray(np.asarray(score_grid, dtype=np.float32))
    shape = np.asarray(array.shape, dtype=np.int64)
    digest = sha256()
    digest.update(str(array.dtype).encode())
    digest.update(shape.tobytes())
    digest.update(array.tobytes())
    return digest.hexdigest()


def write_score_sidecar(
    path: Path,
    *,
    score_grid: np.ndarray,
    metadata: dict[str, Any],
    overwrite: bool = False,
) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"sidecar already exists: {path}")
    array = np.asarray(score_grid, dtype=np.float32)
    if not np.all(np.isfinite(array)):
        raise ValueError(f"sidecar score grid contains non-finite values: {path}")
    if np.any(array < 0.0):
        raise ValueError(f"sidecar score grid contains negative values: {path}")

    payload = {
        "schema": SIDECAR_SCHEMA,
        **metadata,
        "score_shape": list(array.shape),
        "score_grid_sha256": score_grid_sha256(array),
    }
    if "score_config_id" not in payload:
        raise ValueError("sidecar metadata must include score_config_id")
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        path,
        score_grid=array,
        metadata_json=np.array(json.dumps(payload, sort_keys=True)),
    )


def read_score_sidecar(path: Path) -> tuple[np.ndarray, dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(path)
    with np.load(path, allow_pickle=False) as loaded:
        array = np.asarray(loaded["score_grid"], dtype=np.float32)
        metadata_raw = str(loaded["metadata_json"].item())
    metadata = json.loads(metadata_raw)
    if not isinstance(metadata, dict):
        raise ValueError(f"sidecar metadata is not an object: {path}")
    metadata = cast(dict[str, Any], metadata)
    if metadata.get("schema") != SIDECAR_SCHEMA:
        raise ValueError(f"sidecar schema mismatch in {path}: {metadata.get('schema')!r}")
    if list(array.shape) != list(metadata.get("score_shape", [])):
        raise ValueError(
            f"sidecar shape mismatch in {path}: array={array.shape} "
            f"metadata={metadata.get('score_shape')!r}"
        )
    expected_hash = metadata.get("score_grid_sha256")
    actual_hash = score_grid_sha256(array)
    if expected_hash != actual_hash:
        raise ValueError(
            f"sidecar score hash mismatch in {path}: actual={actual_hash!r} "
            f"expected={expected_hash!r}"
        )
    if not np.all(np.isfinite(array)):
        raise ValueError(f"sidecar score grid contains non-finite values: {path}")
    if np.any(array < 0.0):
        raise ValueError(f"sidecar score grid contains negative values: {path}")
    return array, metadata


def require_sidecar_metadata(
    metadata: dict[str, Any],
    *,
    item_id: str,
    source: str,
    geometry: str,
    frame_count: int,
    score_config: str | None = None,
) -> None:
    expected = {
        "item_id": item_id,
        "codec_score_source": source,
        "geometry": geometry,
        "frame_count": frame_count,
    }
    if score_config is not None:
        expected["score_config_id"] = score_config
    for key, value in expected.items():
        if metadata.get(key) != value:
            raise ValueError(
                f"sidecar metadata {key} mismatch: actual={metadata.get(key)!r} expected={value!r}"
            )
