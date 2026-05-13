from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from codec_through.codec.score_sidecar import (
    read_score_sidecar,
    require_sidecar_metadata,
    safe_item_id,
    score_config_id,
    score_grid_sha256,
    sidecar_path,
    write_score_sidecar,
)


def _metadata(*, item_id: str = "video/001", config_id: str = "cfg") -> dict[str, object]:
    return {
        "item_id": item_id,
        "codec_score_source": "novel_coded",
        "geometry": "qwen_merged_groups_v1",
        "frame_count": 8,
        "score_config_id": config_id,
    }


def test_score_sidecar_roundtrip_validates_metadata_and_hash(tmp_path: Path) -> None:
    score_grid = np.array([0.0, 1.5, 2.0], dtype=np.float32)
    config_id = score_config_id(source="novel_coded", frame_count=8)
    path = sidecar_path(
        tmp_path,
        item_id="video/001",
        source="novel_coded",
        geometry="qwen_merged_groups_v1",
        score_config=config_id,
    )

    write_score_sidecar(path, score_grid=score_grid, metadata=_metadata(config_id=config_id))
    loaded, metadata = read_score_sidecar(path)

    assert loaded.tolist() == score_grid.tolist()
    assert metadata["score_grid_sha256"] == score_grid_sha256(score_grid)
    require_sidecar_metadata(
        metadata,
        item_id="video/001",
        source="novel_coded",
        geometry="qwen_merged_groups_v1",
        frame_count=8,
        score_config=config_id,
    )


def test_score_sidecar_rejects_corrupted_hash(tmp_path: Path) -> None:
    path = tmp_path / "bad.npz"
    metadata = {
        "schema": "codec_score_sidecar_v1",
        **_metadata(),
        "score_shape": [2],
        "score_grid_sha256": "0" * 64,
    }
    np.savez_compressed(
        path,
        score_grid=np.array([1.0, 2.0], dtype=np.float32),
        metadata_json=np.array(json.dumps(metadata, sort_keys=True)),
    )

    with pytest.raises(ValueError, match="score hash mismatch"):
        read_score_sidecar(path)


def test_score_sidecar_requires_score_config_id(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="score_config_id"):
        write_score_sidecar(
            tmp_path / "missing.npz",
            score_grid=np.array([1.0], dtype=np.float32),
            metadata={
                "item_id": "a",
                "codec_score_source": "novel_coded",
                "geometry": "qwen_merged_groups_v1",
                "frame_count": 8,
            },
        )


def test_score_sidecar_paths_include_config_and_sanitize_item_id(tmp_path: Path) -> None:
    path = sidecar_path(
        tmp_path,
        item_id="folder/item:01",
        source="motion",
        geometry="qwen_merged_groups_v1",
        score_config="abc123",
    )

    assert safe_item_id("folder/item:01") == "folder__item__01"
    assert path.relative_to(tmp_path).parts == (
        "qwen_merged_groups_v1",
        "motion",
        "abc123",
        "folder__item__01.npz",
    )


def test_fused_score_config_id_binds_weights_but_simple_sources_do_not() -> None:
    simple = score_config_id(source="motion", frame_count=8, motion_weight=1.0)
    simple_changed_weight = score_config_id(source="motion", frame_count=8, motion_weight=2.0)
    simple_changed_projection = score_config_id(
        source="motion",
        frame_count=8,
        projection_version=2,
    )
    fused = score_config_id(source="fused", frame_count=8, motion_weight=1.0)
    fused_changed_weight = score_config_id(source="fused", frame_count=8, motion_weight=2.0)

    assert simple == simple_changed_weight
    assert simple != simple_changed_projection
    assert fused != fused_changed_weight
