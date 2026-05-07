#!/usr/bin/env python3
"""Profile local RLT-style masks before spending MLX wall-clock.

This script is intentionally useful in two modes:

- synthetic-only, CPU-only, dependency-light sanity checks;
- manifest-backed profiling that lazily imports the existing benchmark loader.

JSONL row 0 is schema metadata. Item rows carry a run hash so autonomous queues
can reject stale artifacts instead of accidentally resuming incompatible work.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Literal

import numpy as np
from PIL import Image

from codec_through.novelty_pruning import compute_pixel_novelty
from codec_through.rlt_masks import (
    RLTMaskConfig,
    artifact_config_hash,
    coerce_frames_to_array,
    compute_rlt_keep_mask_from_array,
    mask_summary,
    project_bool_grid,
    project_float_grid,
)
from codec_through.video_decode import decode_uniform_frames

SCHEMA_VERSION = "rlt_mask_profile_v2"
DEFAULT_OUTPUT = Path("research/experiments/2026/artifacts/rlt_mask_profile.jsonl")
DEFAULT_SUMMARY = Path("research/experiments/2026/artifacts/rlt_mask_profile_summary.json")
SyntheticKind = Literal[
    "exact_static",
    "single_frame_repeat",
    "all_motion",
    "fixed_camera_positive",
    "camera_pan",
]


def _parse_grid(value: str) -> tuple[int, int]:
    normalized = value.lower().replace(",", "x")
    parts = normalized.split("x")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError(f"grid must be ROWSxCOLS, got {value!r}")
    try:
        rows, cols = int(parts[0]), int(parts[1])
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"grid must contain integers: {value!r}") from exc
    if rows <= 0 or cols <= 0:
        raise argparse.ArgumentTypeError(f"grid dims must be positive: {value!r}")
    return rows, cols


def _git_sha() -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return completed.stdout.strip()


def _sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_payload(args: argparse.Namespace, config: RLTMaskConfig) -> dict[str, Any]:
    manifest_hash = _sha256_file(args.manifest) if args.manifest else None
    clip_hashes = {str(path): _sha256_file(path) for path in args.clip}
    return {
        "schema_version": SCHEMA_VERSION,
        "manifest_path": str(args.manifest) if args.manifest else None,
        "manifest_content_hash": manifest_hash,
        "clip_hashes": clip_hashes,
        "clip_group": args.clip_group,
        "frame_count": args.frame_count,
        "config": config.as_dict(),
        "project_grid_shape": list(args.project_grid_shape) if args.project_grid_shape else None,
        "synthetic": list(args.synthetic),
        "n_items": args.n_items,
        "rng_seed": args.rng_seed,
        "compare_pixel_novelty": args.compare_pixel_novelty,
    }


def _load_existing_run_hash(path: Path) -> str | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                payload = json.loads(line)
                if payload.get("kind") != "schema":
                    raise ValueError(f"{path} exists but row 0 is not schema metadata")
                if payload.get("schema_version") != SCHEMA_VERSION:
                    raise ValueError(
                        f"{path} schema mismatch: {payload.get('schema_version')} vs "
                        f"{SCHEMA_VERSION}"
                    )
                return str(payload.get("run_hash"))
    raise ValueError(f"{path} exists but is empty")


def _prepare_output(path: Path, *, run_hash: str, overwrite: bool, resume: bool) -> bool:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        return True
    existing_hash = _load_existing_run_hash(path)
    if existing_hash == run_hash and resume:
        return False
    if overwrite:
        return True
    raise SystemExit(
        f"{path} already exists with run_hash={existing_hash}; expected {run_hash}. "
        "Use --resume for matching artifacts or --overwrite to replace."
    )


def _synthetic_frames(kind: SyntheticKind, *, frame_count: int, size: int) -> list[Image.Image]:
    if frame_count <= 0:
        raise ValueError("frame_count must be positive")
    yy, xx = np.mgrid[0:size, 0:size]
    frames: list[Image.Image] = []
    for idx in range(frame_count):
        if kind in ("exact_static", "single_frame_repeat"):
            arr = np.full((size, size, 3), 96, dtype=np.uint8)
        elif kind == "all_motion":
            value = np.uint8(min(255, idx * max(1, 220 // max(1, frame_count - 1))))
            arr = np.full((size, size, 3), int(value), dtype=np.uint8)
        elif kind == "fixed_camera_positive":
            arr = np.full((size, size, 3), 80, dtype=np.uint8)
            box = max(4, size // 8)
            offset = (idx * max(1, size // max(1, frame_count))) % (size - box)
            arr[offset : offset + box, offset : offset + box, :] = (220, 40, 40)
        elif kind == "camera_pan":
            base = ((xx + idx * max(1, size // max(1, frame_count))) % size) / max(1, size - 1)
            arr = np.stack(
                [
                    np.rint(base * 255),
                    np.rint(((yy % size) / max(1, size - 1)) * 255),
                    np.full((size, size), 120),
                ],
                axis=2,
            ).astype(np.uint8)
        else:  # pragma: no cover - argparse choices keep this unreachable.
            raise ValueError(f"unknown synthetic kind {kind!r}")
        frames.append(Image.fromarray(arr, mode="RGB"))
    return frames


def _load_track_a_helpers() -> Any:
    script_path = Path("scripts/run_benchmark_track_a.py").resolve()
    spec = importlib.util.spec_from_file_location("run_benchmark_track_a_for_rlt", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _iter_manifest_items(
    manifest: Path,
    *,
    frame_count: int,
    n_items: int | None,
) -> Iterable[tuple[str, list[Image.Image], dict[str, Any]]]:
    helpers = _load_track_a_helpers()
    loaded_manifest = helpers._load_manifest(manifest)
    items = helpers._load_items_by_id(loaded_manifest.item_ids)
    if n_items is not None:
        items = items[:n_items]
    for item in items:
        frames, active_boxes = helpers._decode_uniform_frames(
            item.video_path,
            frame_count=frame_count,
            start_seconds=item.start_seconds,
            end_seconds=item.end_seconds,
        )
        yield (
            str(item.item_id),
            frames,
            {
                "source": "manifest",
                "benchmark": str(item.benchmark),
                "group": str(item.group),
                "video_path": str(item.video_path),
                "active_boxes": [list(box) for box in active_boxes],
            },
        )


def _iter_clip_items(
    clips: list[Path],
    *,
    frame_count: int,
    group: str,
) -> Iterable[tuple[str, list[Image.Image], dict[str, Any]]]:
    for path in clips:
        if not path.exists():
            raise FileNotFoundError(path)
        frames = decode_uniform_frames(path, frame_count=frame_count)
        yield (
            f"clip:{path.stem}",
            frames,
            {
                "source": "clip",
                "group": group,
                "video_path": str(path),
                "content_hash": _sha256_file(path),
            },
        )


def _matched_pixel_novelty_mask(frames: np.ndarray, rlt_keep_mask: np.ndarray) -> np.ndarray:
    novelty = compute_pixel_novelty(frames, grid_shape=rlt_keep_mask.shape[1:], first_frame="max")
    frame_count, rows, cols = rlt_keep_mask.shape
    out = np.zeros_like(rlt_keep_mask, dtype=bool)
    for frame_idx in range(frame_count):
        budget = int(rlt_keep_mask[frame_idx].sum())
        if budget <= 0:
            continue
        scores = novelty[frame_idx]
        order = np.lexsort((np.arange(scores.size), -scores))
        out[frame_idx].reshape(rows * cols)[order[:budget]] = True
    return out


def _jaccard(a: np.ndarray, b: np.ndarray) -> float:
    union = int(np.logical_or(a, b).sum())
    if union == 0:
        return 1.0
    return float(np.logical_and(a, b).sum() / union)


def _duration_anchor_summary(result_mask: np.ndarray, run_lengths: np.ndarray) -> dict[str, Any]:
    lengths = run_lengths[result_mask]
    if lengths.size == 0:
        return {
            "kept_anchor_count": 0,
            "mean_duration_frames": 0.0,
            "max_duration_frames": 0,
            "long_duration_fraction": 0.0,
        }
    return {
        "kept_anchor_count": int(lengths.size),
        "mean_duration_frames": float(lengths.mean()),
        "max_duration_frames": int(lengths.max()),
        "long_duration_fraction": float((lengths >= 4).mean()),
    }


def _profile_one(
    *,
    item_id: str,
    frames: list[Image.Image],
    item_meta: dict[str, Any],
    config: RLTMaskConfig,
    project_grid_shape: tuple[int, int] | None,
    compare_pixel_novelty: bool,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    arr = coerce_frames_to_array(
        frames,
        image_size=config.image_size,
        normalize_mode=config.normalize_mode,
        pixel_scale=config.pixel_scale,
    )
    t1 = time.perf_counter()
    result = compute_rlt_keep_mask_from_array(arr, config=config, frames_are_normalized=True)
    t2 = time.perf_counter()
    mask_project_ms = 0.0
    projected_shape: tuple[int, int] | None = None
    if project_grid_shape is not None:
        p0 = time.perf_counter()
        _ = project_bool_grid(result.frame_keep_mask, project_grid_shape)
        _ = project_float_grid(
            np.repeat(result.tubelet_scores, config.tubelet_size, axis=0), project_grid_shape
        )
        mask_project_ms = (time.perf_counter() - p0) * 1000.0
        projected_shape = project_grid_shape
    pixel_jaccard = None
    if compare_pixel_novelty:
        pixel_mask = _matched_pixel_novelty_mask(arr, result.frame_keep_mask)
        pixel_jaccard = _jaccard(result.frame_keep_mask, pixel_mask)

    summary = mask_summary(result)
    row = {
        "kind": "item",
        "schema_version": SCHEMA_VERSION,
        "item_id": item_id,
        "item_meta": item_meta,
        "mask_domain": "post-decode_raw_224_imagenet_normalized",
        "mask_config": config.as_dict(),
        "mask_compute_ms": (t2 - t1) * 1000.0,
        "frame_prepare_ms": (t1 - t0) * 1000.0,
        "mask_project_ms": mask_project_ms,
        "projected_grid_shape": list(projected_shape) if projected_shape else None,
        "pixel_novelty_jaccard": pixel_jaccard,
        "duration_anchor_summary": _duration_anchor_summary(
            result.frame_keep_mask,
            result.frame_run_lengths,
        ),
        **summary,
    }
    return row


def _write_jsonl(path: Path, rows: list[dict[str, Any]], schema_row: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(schema_row, sort_keys=True) + "\n")
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def _write_summary(path: Path, rows: list[dict[str, Any]], schema_row: dict[str, Any]) -> None:
    item_rows = [row for row in rows if row.get("kind") == "item"]
    keep_rates = [float(row["keep_rate"]) for row in item_rows]
    compute_ms = [float(row["mask_compute_ms"]) for row in item_rows]
    project_ms = [float(row["mask_project_ms"]) for row in item_rows]
    pixel_jaccards = [
        float(row["pixel_novelty_jaccard"])
        for row in item_rows
        if row.get("pixel_novelty_jaccard") is not None
    ]
    summary = {
        **schema_row,
        "kind": "summary",
        "item_count": len(item_rows),
        "mean_keep_rate": float(np.mean(keep_rates)) if keep_rates else None,
        "median_keep_rate": float(np.median(keep_rates)) if keep_rates else None,
        "mean_mask_compute_ms": float(np.mean(compute_ms)) if compute_ms else None,
        "mean_mask_project_ms": float(np.mean(project_ms)) if project_ms else None,
        "mean_pixel_novelty_jaccard": (float(np.mean(pixel_jaccards)) if pixel_jaccards else None),
        "floor_active_item_count": int(sum(bool(row["floor_active"]) for row in item_rows)),
        "threshold_active_token_count": int(
            sum(int(row["threshold_active_token_count"]) for row in item_rows)
        ),
        "floor_active_token_count": int(
            sum(int(row["floor_active_token_count"]) for row in item_rows)
        ),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--clip", type=Path, action="append", default=[])
    parser.add_argument("--clip-group", default="fixed_camera_positive")
    parser.add_argument("--frame-count", type=int, default=8)
    parser.add_argument("--threshold", type=float, default=0.1)
    parser.add_argument("--tubelet-size", type=int, default=2)
    parser.add_argument("--image-size", type=int, default=224)
    parser.add_argument("--patch-size", type=int, default=16)
    parser.add_argument("--grid-shape", type=_parse_grid)
    parser.add_argument("--project-grid-shape", type=_parse_grid)
    parser.add_argument(
        "--normalize-mode",
        choices=["imagenet", "none", "pre_normalized_imagenet"],
        default="imagenet",
    )
    parser.add_argument("--pixel-scale", choices=["uint8", "float01"], default="uint8")
    parser.add_argument("--window-min-keep", "--per-frame-min-keep", type=int, default=0)
    parser.add_argument(
        "--synthetic",
        action="append",
        choices=[
            "exact_static",
            "single_frame_repeat",
            "all_motion",
            "fixed_camera_positive",
            "camera_pan",
        ],
        default=[],
    )
    parser.add_argument("--n-items", type=int)
    parser.add_argument("--rng-seed", type=int, default=0)
    parser.add_argument("--compare-pixel-novelty", action="store_true")
    parser.add_argument("--output-jsonl", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary-json", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    if args.image_size <= 0:
        raise SystemExit("--image-size must be positive")
    if args.frame_count <= 0:
        raise SystemExit("--frame-count must be positive")
    if args.n_items is not None and args.n_items <= 0:
        raise SystemExit("--n-items must be positive when supplied")
    if not args.manifest and not args.synthetic and not args.clip:
        args.synthetic = [
            "exact_static",
            "single_frame_repeat",
            "all_motion",
            "fixed_camera_positive",
            "camera_pan",
        ]

    config = RLTMaskConfig(
        threshold=args.threshold,
        tubelet_size=args.tubelet_size,
        image_size=(args.image_size, args.image_size),
        patch_size=args.patch_size,
        grid_shape=args.grid_shape,
        normalize_mode=args.normalize_mode,
        pixel_scale=args.pixel_scale,
        first_tubelet_mode="full_grid",
        window_min_keep=args.window_min_keep,
        ordering="time_major",
    )
    artifact_payload = _artifact_payload(args, config)
    run_hash = artifact_config_hash(artifact_payload)
    should_run = _prepare_output(
        args.output_jsonl,
        run_hash=run_hash,
        overwrite=args.overwrite,
        resume=args.resume,
    )
    if not should_run:
        print(f"[resume] existing matching artifact: {args.output_jsonl}")
        return 0

    schema_row = {
        "kind": "schema",
        "schema_version": SCHEMA_VERSION,
        "run_hash": run_hash,
        "git_sha": _git_sha(),
        "artifact_payload": artifact_payload,
    }
    rows: list[dict[str, Any]] = []

    for synthetic_kind in args.synthetic:
        frames = _synthetic_frames(
            synthetic_kind,
            frame_count=args.frame_count,
            size=args.image_size,
        )
        rows.append(
            _profile_one(
                item_id=f"synthetic:{synthetic_kind}:{args.frame_count}",
                frames=frames,
                item_meta={"source": "synthetic", "synthetic_kind": synthetic_kind},
                config=config,
                project_grid_shape=args.project_grid_shape,
                compare_pixel_novelty=args.compare_pixel_novelty,
            )
        )

    if args.manifest:
        for item_id, frames, item_meta in _iter_manifest_items(
            args.manifest,
            frame_count=args.frame_count,
            n_items=args.n_items,
        ):
            rows.append(
                _profile_one(
                    item_id=item_id,
                    frames=frames,
                    item_meta=item_meta,
                    config=config,
                    project_grid_shape=args.project_grid_shape,
                    compare_pixel_novelty=args.compare_pixel_novelty,
                )
            )

    for item_id, frames, item_meta in _iter_clip_items(
        args.clip,
        frame_count=args.frame_count,
        group=args.clip_group,
    ):
        rows.append(
            _profile_one(
                item_id=item_id,
                frames=frames,
                item_meta=item_meta,
                config=config,
                project_grid_shape=args.project_grid_shape,
                compare_pixel_novelty=args.compare_pixel_novelty,
            )
        )

    _write_jsonl(args.output_jsonl, rows, schema_row)
    _write_summary(args.summary_json, rows, schema_row)
    print(
        json.dumps(
            {
                "output_jsonl": str(args.output_jsonl),
                "summary_json": str(args.summary_json),
                "item_count": len(rows),
                "run_hash": run_hash,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
