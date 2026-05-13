#!/usr/bin/env python3
"""Validate precomputed OV-6 codec-score sidecars before reuse."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any, cast

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from codec_through.codec.continuous_score import CodecScoreSource  # noqa: E402
from codec_through.codec.score_sidecar import (  # noqa: E402
    SCORE_SIDECAR_PROJECTION_VERSION,
    read_score_sidecar,
    require_sidecar_metadata,
    score_config_id,
)

QWEN_CANVAS_SIZE = 560
QWEN_TOKEN_BLOCK = 28
GEMMA_CANVAS_SIZE = 768
GEMMA_PATCH_SIZE = 16
GEMMA_PATCH_GRID_SHAPE = (48, 48)
GEMMA_MAX_PATCHES = 2520


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"expected object JSON: {path}")
    return cast(dict[str, Any], payload)


def _norm(value: str | Path) -> str:
    return str(Path(value).expanduser().resolve(strict=False))


def _assert_equal(actual: object, expected: object, field: str) -> None:
    if actual != expected:
        raise ValueError(f"{field} mismatch: actual={actual!r} expected={expected!r}")


def _current_git_commit() -> str | None:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def _manifest_item_ids(path: Path, *, n_items: int | None) -> list[str]:
    payload = tomllib.loads(path.read_text())
    item_ids = [str(item_id) for item_id in payload["item_ids"]]
    if n_items is not None and n_items > 0:
        item_ids = item_ids[:n_items]
    return item_ids


def _geometry_details(geometry: str) -> dict[str, Any]:
    if geometry == "qwen_merged_groups_v1":
        return {
            "canvas_size": QWEN_CANVAS_SIZE,
            "token_block": QWEN_TOKEN_BLOCK,
            "sidecar_shape": "flattened Qwen merged groups",
        }
    if geometry == "gemma_prepool_patches_v1":
        return {
            "canvas_size": GEMMA_CANVAS_SIZE,
            "token_block": GEMMA_PATCH_SIZE,
            "patch_grid_shape": list(GEMMA_PATCH_GRID_SHAPE),
            "real_patches_per_frame": GEMMA_PATCH_GRID_SHAPE[0] * GEMMA_PATCH_GRID_SHAPE[1],
            "max_patches": GEMMA_MAX_PATCHES,
            "padding_policy": "zero-score padded patches; runtime excludes [-1,-1] positions",
        }
    raise ValueError(f"unknown sidecar geometry: {geometry}")


def validate(args: argparse.Namespace) -> None:
    manifest = _load_json(args.manifest_json)
    current_commit = _current_git_commit()
    _assert_equal(manifest.get("schema"), "ov6_codec_score_sidecar_manifest_v1", "schema")
    _assert_equal(_norm(str(manifest.get("out_dir"))), _norm(args.sidecar_dir), "out_dir")
    _assert_equal(manifest.get("geometry"), args.geometry, "geometry")
    _assert_equal(
        manifest.get("geometry_details"), _geometry_details(args.geometry), "geometry_details"
    )
    _assert_equal(int(manifest.get("frame_count", -1)), args.frame_count, "frame_count")
    _assert_equal(
        int(manifest.get("score_projection_version", -1)),
        SCORE_SIDECAR_PROJECTION_VERSION,
        "score_projection_version",
    )
    _assert_equal(_norm(str(manifest.get("manifest"))), _norm(args.input_manifest), "manifest")
    expected_item_ids = _manifest_item_ids(args.input_manifest, n_items=args.n_items)
    _assert_equal(
        list(manifest.get("manifest_item_ids", [])), expected_item_ids, "manifest_item_ids"
    )

    expected_sources = [CodecScoreSource(raw).value for raw in args.sources]
    _assert_equal(list(manifest.get("sources", [])), expected_sources, "sources")
    _assert_equal(int(manifest.get("n_items", -1)), len(expected_item_ids), "n_items")
    if bool(manifest.get("git_dirty", False)) and not args.allow_dirty:
        raise ValueError("sidecar manifest was generated from a dirty git tree")
    if current_commit is not None and not args.allow_dirty:
        _assert_equal(manifest.get("git_commit"), current_commit, "git_commit")

    entries_raw = manifest.get("entries", [])
    if not isinstance(entries_raw, list):
        raise ValueError("entries must be a list")
    expected_count = len(expected_item_ids) * len(expected_sources)
    _assert_equal(len(entries_raw), expected_count, "entry count")
    expected_keys = {
        (item_id, source) for item_id in expected_item_ids for source in expected_sources
    }
    seen: set[tuple[str, str]] = set()
    for raw_entry in entries_raw:
        if not isinstance(raw_entry, dict):
            raise ValueError(f"sidecar manifest entry is not an object: {raw_entry!r}")
        entry = cast(dict[str, Any], raw_entry)
        item_id = str(entry["item_id"])
        source = CodecScoreSource(str(entry["codec_score_source"])).value
        key = (item_id, source)
        if key in seen:
            raise ValueError(f"duplicate sidecar entry for item/source: {key}")
        seen.add(key)

        config_id = score_config_id(
            source=source,
            frame_count=args.frame_count,
            projection_version=SCORE_SIDECAR_PROJECTION_VERSION,
            fusion_mode=str(manifest.get("fusion_mode", "weighted")),
            motion_weight=float(manifest.get("motion_weight", 1.0)),
            residual_weight=float(manifest.get("residual_weight", 1.0)),
            normalize_fusion_inputs=bool(manifest.get("normalize_fusion_inputs", True)),
        )
        _assert_equal(entry.get("score_config_id"), config_id, f"{key} score_config_id")
        _assert_equal(
            int(entry.get("score_projection_version", -1)),
            SCORE_SIDECAR_PROJECTION_VERSION,
            f"{key} score_projection_version",
        )

        path = Path(str(entry["path"]))
        if not path.is_absolute():
            path = REPO_ROOT / path
        expected_prefix = Path(args.sidecar_dir).expanduser().resolve(strict=False)
        if expected_prefix not in path.resolve(strict=False).parents:
            raise ValueError(f"sidecar path escapes sidecar dir: {path}")
        score_grid, metadata = read_score_sidecar(path)
        require_sidecar_metadata(
            metadata,
            item_id=item_id,
            source=source,
            geometry=args.geometry,
            frame_count=args.frame_count,
            score_config=config_id,
        )
        _assert_equal(
            metadata.get("geometry_details"),
            _geometry_details(args.geometry),
            f"{key} geometry_details",
        )
        _assert_equal(
            int(metadata.get("score_projection_version", -1)),
            SCORE_SIDECAR_PROJECTION_VERSION,
            f"{key} score_projection_version",
        )
        _assert_equal(
            metadata.get("score_grid_sha256"),
            entry.get("score_grid_sha256"),
            f"{key} hash",
        )
        _assert_equal(list(score_grid.shape), list(entry.get("score_shape", [])), f"{key} shape")
        if bool(metadata.get("git_dirty", False)) and not args.allow_dirty:
            raise ValueError(f"sidecar {path} was generated from a dirty git tree")
        if current_commit is not None and not args.allow_dirty:
            _assert_equal(metadata.get("git_commit"), current_commit, f"{key} git_commit")
        extract_s = float(metadata.get("codec_extract_s", float("nan")))
        if not math.isfinite(extract_s) or extract_s < 0.0:
            raise ValueError(f"sidecar {path} is missing finite codec_extract_s")
        projection_write_s = float(entry.get("projection_write_s", float("nan")))
        if not math.isfinite(projection_write_s) or projection_write_s < 0.0:
            raise ValueError(f"sidecar manifest entry {key} is missing finite projection_write_s")

    _assert_equal(seen, expected_keys, "manifest item/source keys")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-json", type=Path, required=True)
    parser.add_argument("--sidecar-dir", type=Path, required=True)
    parser.add_argument("--input-manifest", type=Path, required=True)
    parser.add_argument("--geometry", required=True)
    parser.add_argument("--frame-count", type=int, required=True)
    parser.add_argument("--n-items", type=int, default=None)
    parser.add_argument(
        "--sources",
        nargs="+",
        default=["novel_coded", "motion", "residual"],
        choices=tuple(source.value for source in CodecScoreSource),
    )
    parser.add_argument("--allow-dirty", action="store_true")
    validate(parser.parse_args())


if __name__ == "__main__":
    main()
