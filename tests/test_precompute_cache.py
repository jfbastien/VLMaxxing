from __future__ import annotations

import json

import numpy as np
import pytest

from codec_through.precompute_cache import (
    decode_array,
    encode_array,
    read_json_cache,
    write_json_cache_atomic,
)


def test_array_payload_round_trips_dtype_and_shape() -> None:
    source = np.arange(12, dtype=np.float32).reshape(3, 4)

    decoded = decode_array(encode_array(source))

    np.testing.assert_array_equal(decoded, source)
    assert decoded.dtype == np.float32
    assert decoded.shape == (3, 4)


def test_array_payload_rejects_shape_mismatch() -> None:
    payload = {"dtype": "int32", "shape": [2, 2], "data": [1, 2, 3]}

    with pytest.raises(ValueError, match="requires 4"):
        decode_array(payload)


def test_json_cache_write_is_readable(tmp_path) -> None:
    cache_path = tmp_path / "precompute.json"
    payload = {"version": 1, "items": [{"item_id": "x"}]}

    write_json_cache_atomic(cache_path, payload)

    assert read_json_cache(cache_path) == payload
    assert json.loads(cache_path.read_text()) == payload
    assert not cache_path.with_name("precompute.json.tmp").exists()
