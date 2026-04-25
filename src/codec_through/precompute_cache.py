"""Small JSON cache helpers for expensive deterministic precompute stages."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import numpy as np


def encode_array(array: np.ndarray) -> dict[str, Any]:
    """Encode a NumPy array into a JSON-stable payload with dtype and shape."""

    values = np.asarray(array)
    return {
        "dtype": str(values.dtype),
        "shape": list(values.shape),
        "data": values.reshape(-1).tolist(),
    }


def decode_array(payload: dict[str, Any]) -> np.ndarray:
    """Decode an array payload emitted by :func:`encode_array`."""

    dtype = np.dtype(str(payload["dtype"]))
    shape = tuple(int(dim) for dim in payload["shape"])
    values = np.asarray(payload["data"], dtype=dtype)
    expected_size = int(np.prod(shape, dtype=np.int64))
    if values.size != expected_size:
        raise ValueError(
            f"array payload has {values.size} values but shape {shape} requires {expected_size}"
        )
    return values.reshape(shape)


def read_json_cache(path: Path) -> dict[str, Any]:
    """Read a JSON cache payload."""

    return cast(dict[str, Any], json.loads(path.read_text()))


def write_json_cache_atomic(path: Path, payload: dict[str, Any]) -> None:
    """Write a JSON cache through an atomic same-directory replacement."""

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    tmp_path.replace(path)
