from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pytest

from codec_through.codec.score_sidecar import (
    SCORE_SIDECAR_PROJECTION_VERSION,
    score_config_id,
    score_grid_sha256,
    sidecar_path,
    write_score_sidecar,
)
from scripts.analyze_ov6_sidecar_equivalence import analyze as analyze_sidecar_equivalence
from scripts.validate_ov6_codec_score_sidecars import validate as validate_sidecars
from scripts.validate_ov6_sidecar_equivalence_gate import validate as validate_equivalence_gate


def _write_result_row(path: Path, *, item_id: str = "a") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "item_id": item_id,
                "correct": True,
                "choice_index": 0,
                "kept_groups": 3,
                "kept_groups_per_frame": [1, 2],
                "parse_failure": False,
            }
        )
        + "\n"
    )


def _write_summary(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n")


def _qwen_geometry_details() -> dict[str, object]:
    return {
        "canvas_size": 560,
        "token_block": 28,
        "sidecar_shape": "flattened Qwen merged groups",
    }


def _write_valid_qwen_sidecar_bundle(
    tmp_path: Path,
    *,
    input_item_ids: list[str] | None = None,
    manifest_item_ids: list[str] | None = None,
    codec_extract_s: float = 2.0,
    projection_write_s: float = 0.01,
) -> argparse.Namespace:
    input_item_ids = input_item_ids or ["a"]
    manifest_item_ids = manifest_item_ids or input_item_ids
    sidecar_dir = tmp_path / "sidecars"
    input_manifest = tmp_path / "manifest.toml"
    input_manifest.write_text(
        'benchmark = "videomme"\nitem_ids = ['
        + ", ".join(json.dumps(item_id) for item_id in input_item_ids)
        + "]\n"
    )
    config_id = score_config_id(source="novel_coded", frame_count=8)
    grid = np.array([0.0, 2.0], dtype=np.float32)
    path = sidecar_path(
        sidecar_dir,
        item_id="a",
        source="novel_coded",
        geometry="qwen_merged_groups_v1",
        score_config=config_id,
    )
    write_score_sidecar(
        path,
        score_grid=grid,
        metadata={
            "item_id": "a",
            "codec_score_source": "novel_coded",
            "geometry": "qwen_merged_groups_v1",
            "geometry_details": _qwen_geometry_details(),
            "frame_count": 8,
            "score_config_id": config_id,
            "score_projection_version": SCORE_SIDECAR_PROJECTION_VERSION,
            "codec_extract_s": codec_extract_s,
            "git_dirty": False,
        },
    )
    manifest_json = tmp_path / "sidecar_manifest.json"
    manifest_json.write_text(
        json.dumps(
            {
                "schema": "ov6_codec_score_sidecar_manifest_v1",
                "git_dirty": False,
                "out_dir": str(sidecar_dir),
                "geometry": "qwen_merged_groups_v1",
                "geometry_details": _qwen_geometry_details(),
                "frame_count": 8,
                "score_projection_version": SCORE_SIDECAR_PROJECTION_VERSION,
                "manifest": str(input_manifest),
                "manifest_item_ids": manifest_item_ids,
                "sources": ["novel_coded"],
                "fusion_mode": "weighted",
                "motion_weight": 1.0,
                "residual_weight": 1.0,
                "normalize_fusion_inputs": True,
                "n_items": len(manifest_item_ids),
                "entries": [
                    {
                        "item_id": "a",
                        "codec_score_source": "novel_coded",
                        "path": str(path),
                        "score_shape": [2],
                        "score_grid_sha256": score_grid_sha256(grid),
                        "score_config_id": config_id,
                        "score_projection_version": SCORE_SIDECAR_PROJECTION_VERSION,
                        "projection_write_s": projection_write_s,
                    }
                ],
            }
        )
        + "\n"
    )
    return argparse.Namespace(
        manifest_json=manifest_json,
        sidecar_dir=sidecar_dir,
        input_manifest=input_manifest,
        geometry="qwen_merged_groups_v1",
        frame_count=8,
        n_items=1,
        sources=["novel_coded"],
        allow_dirty=True,
    )


def test_sidecar_manifest_validator_accepts_hash_and_config_bound_sidecar(
    tmp_path: Path,
) -> None:
    sidecar_dir = tmp_path / "sidecars"
    input_manifest = tmp_path / "manifest.toml"
    input_manifest.write_text('benchmark = "videomme"\nitem_ids = ["a"]\n')
    config_id = score_config_id(source="novel_coded", frame_count=8)
    grid = np.array([0.0, 2.0], dtype=np.float32)
    path = sidecar_path(
        sidecar_dir,
        item_id="a",
        source="novel_coded",
        geometry="qwen_merged_groups_v1",
        score_config=config_id,
    )
    write_score_sidecar(
        path,
        score_grid=grid,
        metadata={
            "item_id": "a",
            "codec_score_source": "novel_coded",
            "geometry": "qwen_merged_groups_v1",
            "geometry_details": _qwen_geometry_details(),
            "frame_count": 8,
            "score_config_id": config_id,
            "score_projection_version": SCORE_SIDECAR_PROJECTION_VERSION,
            "codec_extract_s": 2.0,
            "git_dirty": False,
        },
    )
    manifest_json = tmp_path / "sidecar_manifest.json"
    manifest_json.write_text(
        json.dumps(
            {
                "schema": "ov6_codec_score_sidecar_manifest_v1",
                "git_dirty": False,
                "out_dir": str(sidecar_dir),
                "geometry": "qwen_merged_groups_v1",
                "geometry_details": _qwen_geometry_details(),
                "frame_count": 8,
                "score_projection_version": SCORE_SIDECAR_PROJECTION_VERSION,
                "manifest": str(input_manifest),
                "manifest_item_ids": ["a"],
                "sources": ["novel_coded"],
                "fusion_mode": "weighted",
                "motion_weight": 1.0,
                "residual_weight": 1.0,
                "normalize_fusion_inputs": True,
                "n_items": 1,
                "entries": [
                    {
                        "item_id": "a",
                        "codec_score_source": "novel_coded",
                        "path": str(path),
                        "score_shape": [2],
                        "score_grid_sha256": score_grid_sha256(grid),
                        "score_config_id": config_id,
                        "score_projection_version": SCORE_SIDECAR_PROJECTION_VERSION,
                        "projection_write_s": 0.01,
                    }
                ],
            }
        )
        + "\n"
    )

    validate_sidecars(
        argparse.Namespace(
            manifest_json=manifest_json,
            sidecar_dir=sidecar_dir,
            input_manifest=input_manifest,
            geometry="qwen_merged_groups_v1",
            frame_count=8,
            n_items=1,
            sources=["novel_coded"],
            allow_dirty=True,
        )
    )


def test_sidecar_manifest_validator_rejects_wrong_config_id(tmp_path: Path) -> None:
    sidecar_dir = tmp_path / "sidecars"
    input_manifest = tmp_path / "manifest.toml"
    input_manifest.write_text('benchmark = "videomme"\nitem_ids = ["a"]\n')
    config_id = score_config_id(source="novel_coded", frame_count=8)
    grid = np.array([0.0, 2.0], dtype=np.float32)
    path = sidecar_path(
        sidecar_dir,
        item_id="a",
        source="novel_coded",
        geometry="qwen_merged_groups_v1",
        score_config=config_id,
    )
    write_score_sidecar(
        path,
        score_grid=grid,
        metadata={
            "item_id": "a",
            "codec_score_source": "novel_coded",
            "geometry": "qwen_merged_groups_v1",
            "geometry_details": _qwen_geometry_details(),
            "frame_count": 8,
            "score_config_id": config_id,
            "score_projection_version": SCORE_SIDECAR_PROJECTION_VERSION,
            "codec_extract_s": 2.0,
            "git_dirty": False,
        },
    )
    manifest_json = tmp_path / "sidecar_manifest.json"
    manifest_json.write_text(
        json.dumps(
            {
                "schema": "ov6_codec_score_sidecar_manifest_v1",
                "git_dirty": False,
                "out_dir": str(sidecar_dir),
                "geometry": "qwen_merged_groups_v1",
                "geometry_details": _qwen_geometry_details(),
                "frame_count": 8,
                "score_projection_version": SCORE_SIDECAR_PROJECTION_VERSION,
                "manifest": str(input_manifest),
                "manifest_item_ids": ["a"],
                "sources": ["novel_coded"],
                "fusion_mode": "weighted",
                "motion_weight": 1.0,
                "residual_weight": 1.0,
                "normalize_fusion_inputs": True,
                "n_items": 1,
                "entries": [
                    {
                        "item_id": "a",
                        "codec_score_source": "novel_coded",
                        "path": str(path),
                        "score_shape": [2],
                        "score_grid_sha256": score_grid_sha256(grid),
                        "score_config_id": "wrong",
                        "score_projection_version": SCORE_SIDECAR_PROJECTION_VERSION,
                        "projection_write_s": 0.01,
                    }
                ],
            }
        )
        + "\n"
    )

    with pytest.raises(ValueError, match="score_config_id"):
        validate_sidecars(
            argparse.Namespace(
                manifest_json=manifest_json,
                sidecar_dir=sidecar_dir,
                input_manifest=input_manifest,
                geometry="qwen_merged_groups_v1",
                frame_count=8,
                n_items=1,
                sources=["novel_coded"],
                allow_dirty=True,
            )
        )


def test_sidecar_manifest_validator_rejects_stale_manifest_item_ids(
    tmp_path: Path,
) -> None:
    args = _write_valid_qwen_sidecar_bundle(
        tmp_path,
        input_item_ids=["a"],
        manifest_item_ids=["b"],
    )

    with pytest.raises(ValueError, match="manifest_item_ids mismatch"):
        validate_sidecars(args)


def test_sidecar_manifest_validator_rejects_nonfinite_extract_timing(
    tmp_path: Path,
) -> None:
    args = _write_valid_qwen_sidecar_bundle(tmp_path, codec_extract_s=float("nan"))

    with pytest.raises(ValueError, match="finite codec_extract_s"):
        validate_sidecars(args)


def test_sidecar_equivalence_analyzer_gates_zero_drift(tmp_path: Path) -> None:
    root = tmp_path
    for label, runtime_source in (
        ("live_novel_coded", "live_pyav"),
        ("sidecar_novel_coded", "sidecar"),
    ):
        _write_result_row(root / label / "results.jsonl")
        summary = {
            "codec_score_runtime_source": runtime_source,
            "codec_extract_mean_s_per_item": 2.0 if runtime_source == "live_pyav" else None,
            "codec_sidecar_load_mean_s_per_item": 0.002 if runtime_source == "sidecar" else None,
        }
        _write_summary(root / label / "summary.json", summary)

    payload = analyze_sidecar_equivalence(root, sources=("novel_coded",))

    assert payload["gate_pass"] is True
    assert payload["pairs"]["novel_coded"]["choice_drift"] == 0


def test_sidecar_equivalence_gate_validator_requires_passed_gate(tmp_path: Path) -> None:
    _write_valid_qwen_sidecar_bundle(tmp_path)
    for label, runtime_source in (
        ("live_novel_coded", "live_pyav"),
        ("sidecar_novel_coded", "sidecar"),
    ):
        _write_result_row(tmp_path / label / "results.jsonl")
        summary = {
            "codec_score_runtime_source": runtime_source,
            "codec_extract_mean_s_per_item": 2.0 if runtime_source == "live_pyav" else None,
            "codec_sidecar_load_mean_s_per_item": 0.002 if runtime_source == "sidecar" else None,
        }
        _write_summary(tmp_path / label / "summary.json", summary)
    payload = analyze_sidecar_equivalence(tmp_path, sources=("novel_coded",))
    (tmp_path / "sidecar_equivalence.json").write_text(json.dumps(payload) + "\n")

    validate_equivalence_gate(
        argparse.Namespace(
            root=tmp_path,
            geometry="qwen_merged_groups_v1",
            frame_count=8,
            sources=["novel_coded"],
            allow_dirty=True,
        )
    )

    payload["gate_pass"] = False
    (tmp_path / "sidecar_equivalence.json").write_text(json.dumps(payload) + "\n")

    with pytest.raises(ValueError, match="gate did not pass"):
        validate_equivalence_gate(
            argparse.Namespace(
                root=tmp_path,
                geometry="qwen_merged_groups_v1",
                frame_count=8,
                sources=["novel_coded"],
                allow_dirty=True,
            )
        )
