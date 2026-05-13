#!/usr/bin/env python3
"""Build precomputed H.264 score sidecars for OV-6 Track B runners.

This is CPU-only. It extracts and projects H.264 macroblock metadata once per
item/source/geometry so model-bearing Track B runs can measure the precomputed
or decoder-integrated denominator separately from the current PyAV extraction
path.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from codec_through.codec.continuous_score import (  # noqa: E402
    CodecScoreSource,
    project_macroblock_metadata_to_token_grid,
    sparse_sample_indices,
)
from codec_through.codec.h264_metadata import H264MetadataExtractor  # noqa: E402
from codec_through.codec.onevision_patchification import FuseMode  # noqa: E402
from codec_through.codec.score_sidecar import (  # noqa: E402
    SCORE_SIDECAR_PROJECTION_VERSION,
    score_config_id,
    score_grid_sha256,
    sidecar_path,
    write_score_sidecar,
)
from codec_through.provenance import artifact_metadata  # noqa: E402
from codec_through.qwen_vision_pruning import pool_token_grid_to_merged_groups  # noqa: E402
from codec_through.video_decode import _count_frames  # noqa: E402

RUNNER_PATH = REPO_ROOT / "scripts" / "run_benchmark_track_a.py"
QWEN_CANVAS_SIZE = 560
QWEN_TOKEN_BLOCK = 28
GEMMA_CANVAS_SIZE = 768
GEMMA_PATCH_SIZE = 16
GEMMA_PATCH_GRID_SHAPE = (48, 48)
GEMMA_MAX_PATCHES = 2520


def _load_runner_module() -> Any:
    name = "_ov6_sidecar_runner"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot build spec for {RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return module


def _load_manifest_items(runner: Any, manifest_path: Path) -> list[Any]:
    payload = tomllib.loads(manifest_path.read_text())
    return cast(list[Any], runner._load_items_by_id(payload["benchmark"], payload["item_ids"]))


def _load_sampled_metadata(
    item: Any,
    *,
    frame_count: int,
) -> tuple[list[int], dict[int, Any], Any, float]:
    if item.start_seconds is not None or item.end_seconds is not None:
        raise ValueError(
            f"codec score sidecars for windowed clips are not implemented for {item.item_id}"
        )
    total_frames = _count_frames(item.video_path, start_seconds=None, end_seconds=None)
    sampled = sparse_sample_indices(total_frames, frame_count)
    t0 = time.perf_counter_ns()
    extractor = H264MetadataExtractor(str(item.video_path), max_frames=sampled[-1] + 1)
    metadata_by_index: dict[int, Any] = {}
    sampled_set = set(sampled)
    for index, metadata in enumerate(extractor.iter_frames()):
        if index in sampled_set:
            metadata_by_index[index] = metadata
        if index >= sampled[-1]:
            break
    extract_s = (time.perf_counter_ns() - t0) / 1_000_000_000
    if len(metadata_by_index) != frame_count:
        raise ValueError(
            f"H264MetadataExtractor missed sampled frames for {item.item_id}; "
            f"wanted {frame_count}, got {len(metadata_by_index)}"
        )
    return sampled, metadata_by_index, extractor, extract_s


def _gemma_stack(grids: list[np.ndarray]) -> np.ndarray:
    flattened: list[np.ndarray] = []
    for index, grid in enumerate(grids):
        array = np.asarray(grid, dtype=np.float32)
        if array.shape != GEMMA_PATCH_GRID_SHAPE:
            raise ValueError(
                f"Gemma sidecar grid at frame {index} has shape {array.shape}, "
                f"expected {GEMMA_PATCH_GRID_SHAPE}"
            )
        flat = array.reshape(-1)
        if flat.shape[0] > GEMMA_MAX_PATCHES:
            raise ValueError(
                f"Gemma sidecar frame {index} has {flat.shape[0]} patches, "
                f"exceeds max_patches={GEMMA_MAX_PATCHES}"
            )
        if flat.shape[0] < GEMMA_MAX_PATCHES:
            flat = np.pad(flat, (0, GEMMA_MAX_PATCHES - flat.shape[0]), constant_values=0.0)
        flattened.append(flat)
    return np.stack(flattened, axis=0).astype(np.float32, copy=False)


def _scale_active_box(
    active_box: tuple[int, int, int, int],
    *,
    from_size: int,
    to_size: int,
) -> tuple[int, int, int, int]:
    if from_size <= 0 or to_size <= 0:
        raise ValueError("active-box scale sizes must be positive")
    scale = to_size / from_size
    left, top, right, bottom = active_box
    scaled = (
        max(0, min(to_size, round(left * scale))),
        max(0, min(to_size, round(top * scale))),
        max(0, min(to_size, round(right * scale))),
        max(0, min(to_size, round(bottom * scale))),
    )
    if scaled[0] >= scaled[2] or scaled[1] >= scaled[3]:
        raise ValueError(f"scaled active box is empty: {active_box} -> {scaled}")
    return scaled


def _active_boxes_for_geometry(
    active_boxes: list[tuple[int, int, int, int]],
    *,
    geometry: str,
) -> list[tuple[int, int, int, int]]:
    if geometry == "qwen_merged_groups_v1":
        return active_boxes
    if geometry == "gemma_prepool_patches_v1":
        return [
            _scale_active_box(box, from_size=QWEN_CANVAS_SIZE, to_size=GEMMA_CANVAS_SIZE)
            for box in active_boxes
        ]
    raise ValueError(f"unknown sidecar geometry: {geometry}")


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


def _project_item_source(
    *,
    item: Any,
    geometry: str,
    source: CodecScoreSource,
    sampled: list[int],
    metadata_by_index: dict[int, Any],
    extractor: Any,
    active_boxes: list[tuple[int, int, int, int]],
    fusion_mode: FuseMode,
    motion_weight: float,
    residual_weight: float,
    normalize_fusion_inputs: bool,
) -> np.ndarray:
    grids: list[np.ndarray] = []
    if geometry == "qwen_merged_groups_v1":
        canvas_size = QWEN_CANVAS_SIZE
        token_block = QWEN_TOKEN_BLOCK
    elif geometry == "gemma_prepool_patches_v1":
        canvas_size = GEMMA_CANVAS_SIZE
        token_block = GEMMA_PATCH_SIZE
    else:
        raise ValueError(f"unknown sidecar geometry: {geometry}")

    for sampled_index, active_box in zip(sampled, active_boxes, strict=True):
        metadata = metadata_by_index[sampled_index]
        grid = project_macroblock_metadata_to_token_grid(
            metadata.macroblocks,
            source=source,
            macroblock_size=extractor.mb_size,
            frame_width=extractor.width,
            frame_height=extractor.height,
            canvas_size=canvas_size,
            active_box=active_box,
            token_block=token_block,
            mode=fusion_mode,
            motion_weight=motion_weight,
            residual_weight=residual_weight,
            normalize_inputs=normalize_fusion_inputs,
        )
        grids.append(np.clip(grid, a_min=0.0, a_max=None).astype(np.float32))

    if geometry == "qwen_merged_groups_v1":
        return pool_token_grid_to_merged_groups(grids, spatial_merge_size=1).astype(
            np.float32,
            copy=False,
        )
    return _gemma_stack(grids)


def build_sidecars(args: argparse.Namespace) -> dict[str, Any]:
    build_t0 = time.perf_counter_ns()
    build_started_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    runner = _load_runner_module()
    provenance = artifact_metadata(
        REPO_ROOT,
        dirty_scope="worktree before sidecar build, excluding sidecar output paths",
        exclude_paths=[
            args.out_dir,
            args.manifest_json.parent if args.manifest_json else args.out_dir,
        ],
    )
    if bool(provenance.get("git_dirty", False)) and not args.allow_dirty:
        raise SystemExit(
            "sidecar builds require a clean git tree outside the sidecar output paths; "
            "commit or stash changes, or rerun with --allow-dirty"
        )
    items = _load_manifest_items(runner, args.manifest)
    if args.n_items > 0:
        items = items[: args.n_items]
    if not items:
        raise SystemExit("no items loaded from manifest")
    item_ids = [str(item.item_id) for item in items]

    sources = [CodecScoreSource(raw) for raw in args.sources]
    fusion_mode = cast(FuseMode, args.fusion_mode)
    normalize_inputs = not bool(args.no_normalize_fusion_inputs)

    entries: list[dict[str, Any]] = []
    item_extract_entries: list[dict[str, Any]] = []
    extract_total_s = 0.0
    projection_write_total_s = 0.0
    for index, item in enumerate(items, start=1):
        print(f"[sidecar] {index}/{len(items)} {item.item_id}", flush=True)
        _frames, decoded_active_boxes = runner._decode_uniform_frames(
            item.video_path,
            frame_count=args.frame_count,
            start_seconds=item.start_seconds,
            end_seconds=item.end_seconds,
        )
        active_boxes = _active_boxes_for_geometry(decoded_active_boxes, geometry=args.geometry)
        sampled, metadata_by_index, extractor, extract_s = _load_sampled_metadata(
            item,
            frame_count=args.frame_count,
        )
        extract_total_s += extract_s
        item_extract_entries.append({"item_id": item.item_id, "codec_extract_s": extract_s})
        for source in sources:
            source_t0 = time.perf_counter_ns()
            config_id = score_config_id(
                source=source.value,
                frame_count=args.frame_count,
                projection_version=SCORE_SIDECAR_PROJECTION_VERSION,
                fusion_mode=fusion_mode,
                motion_weight=float(args.motion_weight),
                residual_weight=float(args.residual_weight),
                normalize_fusion_inputs=normalize_inputs,
            )
            score_grid = _project_item_source(
                item=item,
                geometry=args.geometry,
                source=source,
                sampled=sampled,
                metadata_by_index=metadata_by_index,
                extractor=extractor,
                active_boxes=active_boxes,
                fusion_mode=fusion_mode,
                motion_weight=float(args.motion_weight),
                residual_weight=float(args.residual_weight),
                normalize_fusion_inputs=normalize_inputs,
            )
            path = sidecar_path(
                args.out_dir,
                item_id=item.item_id,
                source=source.value,
                geometry=args.geometry,
                score_config=config_id,
            )
            metadata = {
                **provenance,
                "item_id": item.item_id,
                "benchmark": item.benchmark,
                "group": item.group,
                "video_path": str(item.video_path),
                "geometry": args.geometry,
                "geometry_details": _geometry_details(args.geometry),
                "codec_score_source": source.value,
                "score_config_id": config_id,
                "score_projection_version": SCORE_SIDECAR_PROJECTION_VERSION,
                "frame_count": args.frame_count,
                "sampled_indices": sampled,
                "active_boxes": [list(box) for box in active_boxes],
                "decoded_active_boxes": [list(box) for box in decoded_active_boxes],
                "codec_extract_s": extract_s,
                "fusion_mode": fusion_mode,
                "motion_weight": float(args.motion_weight),
                "residual_weight": float(args.residual_weight),
                "normalize_fusion_inputs": normalize_inputs,
            }
            write_score_sidecar(
                path,
                score_grid=score_grid,
                metadata=metadata,
                overwrite=bool(args.overwrite),
            )
            projection_write_s = (time.perf_counter_ns() - source_t0) / 1_000_000_000
            projection_write_total_s += projection_write_s
            entries.append(
                {
                    "item_id": item.item_id,
                    "codec_score_source": source.value,
                    "geometry": args.geometry,
                    "path": str(path),
                    "score_shape": list(score_grid.shape),
                    "score_grid_sha256": score_grid_sha256(score_grid),
                    "score_config_id": config_id,
                    "score_projection_version": SCORE_SIDECAR_PROJECTION_VERSION,
                    "codec_extract_s": extract_s,
                    "projection_write_s": projection_write_s,
                }
            )

    build_elapsed_s = (time.perf_counter_ns() - build_t0) / 1_000_000_000
    return {
        "schema": "ov6_codec_score_sidecar_manifest_v1",
        **provenance,
        "build_started_at": build_started_at,
        "build_elapsed_s": build_elapsed_s,
        "manifest": str(args.manifest),
        "manifest_item_ids": item_ids,
        "out_dir": str(args.out_dir),
        "geometry": args.geometry,
        "geometry_details": _geometry_details(args.geometry),
        "frame_count": args.frame_count,
        "score_projection_version": SCORE_SIDECAR_PROJECTION_VERSION,
        "sources": [source.value for source in sources],
        "fusion_mode": fusion_mode,
        "motion_weight": float(args.motion_weight),
        "residual_weight": float(args.residual_weight),
        "normalize_fusion_inputs": normalize_inputs,
        "n_items": len(items),
        "n_sidecars": len(entries),
        "unique_item_extract_total_s": extract_total_s,
        "projection_write_total_s": projection_write_total_s,
        "item_extract_entries": item_extract_entries,
        "entries": entries,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--n-items", type=int, default=0, help="0 = all manifest items")
    parser.add_argument("--frame-count", type=int, default=8)
    parser.add_argument(
        "--geometry",
        choices=("qwen_merged_groups_v1", "gemma_prepool_patches_v1"),
        required=True,
    )
    parser.add_argument(
        "--sources",
        nargs="+",
        default=["novel_coded", "motion", "residual"],
        choices=tuple(source.value for source in CodecScoreSource),
    )
    parser.add_argument(
        "--fusion-mode",
        default="weighted",
        choices=("weighted", "sum", "max", "geomean"),
    )
    parser.add_argument("--motion-weight", type=float, default=1.0)
    parser.add_argument("--residual-weight", type=float, default=1.0)
    parser.add_argument("--no-normalize-fusion-inputs", action="store_true")
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--manifest-json", type=Path, default=None)
    args = parser.parse_args()

    payload = build_sidecars(args)
    manifest_json = args.manifest_json or args.out_dir / "sidecar_manifest.json"
    manifest_json.parent.mkdir(parents=True, exist_ok=True)
    manifest_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(manifest_json)


if __name__ == "__main__":
    main()
