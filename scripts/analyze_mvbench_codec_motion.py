#!/usr/bin/env python3
"""Summarize cheap H.264 motion/residual signals by MVBench group.

This is a CPU-only smoke/probe for codec-conditioned admission scheduling. It
does not run a VLM. The output is hypothesis-generating evidence about whether
compressed-domain metadata separates content classes before any model-facing
codec-routing implementation is attempted.
"""

from __future__ import annotations

import argparse
import json
import math
import time
import tomllib
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import av
import numpy as np

from codec_through.codec.h264_metadata import H264MetadataExtractor

MVBENCH_JSON_DIR = Path("data/benchmarks/mvbench/hf/json")
MVBENCH_VIDEO_DIR = Path("data/benchmarks/mvbench/video")
MVBENCH_SEARCH_DIRS = [
    MVBENCH_VIDEO_DIR / "clevrer" / "video_validation",
    MVBENCH_VIDEO_DIR / "ssv2_video",
    MVBENCH_VIDEO_DIR / "Moments_in_Time_Raw" / "videos",
    MVBENCH_VIDEO_DIR / "scene_qa" / "video",
    MVBENCH_VIDEO_DIR / "star" / "Charades_v1_480",
    MVBENCH_VIDEO_DIR / "sta" / "sta_video",
    MVBENCH_VIDEO_DIR / "FunQA_test" / "test",
    MVBENCH_VIDEO_DIR / "data0613" / "star" / "Charades_v1_480",
    MVBENCH_VIDEO_DIR / "data0613" / "clevrer" / "video_validation",
    MVBENCH_VIDEO_DIR / "data0613",
    MVBENCH_VIDEO_DIR / "vlnqa",
    MVBENCH_VIDEO_DIR,
]


@dataclass(frozen=True, slots=True)
class MVBenchProbeItem:
    item_id: str
    group: str
    video_path: Path
    question: str
    start_seconds: float | None
    end_seconds: float | None


def _find_mvbench_video(video_name: str) -> Path:
    requested = Path(video_name)
    for directory in MVBENCH_SEARCH_DIRS:
        candidate = directory / requested
        if candidate.exists():
            return candidate
        if requested.suffix == "":
            for extension in (".mp4", ".avi", ".webm", ".mkv"):
                candidate = directory / f"{video_name}{extension}"
                if candidate.exists():
                    return candidate
    matches: list[Path] = []
    for directory in MVBENCH_SEARCH_DIRS:
        if not directory.exists():
            continue
        for candidate in directory.rglob(requested.name):
            if requested.parent == Path(".") or candidate.as_posix().endswith(requested.as_posix()):
                matches.append(candidate)
    unique_matches = sorted({path.resolve() for path in matches})
    if len(unique_matches) == 1:
        return unique_matches[0]
    if len(unique_matches) > 1:
        raise RuntimeError(f"ambiguous MVBench video lookup for {video_name!r}: {unique_matches}")
    raise FileNotFoundError(
        f"could not locate MVBench video {video_name!r} under {MVBENCH_VIDEO_DIR}"
    )


def _parse_mvbench_item_id(item_id: str) -> tuple[str, int]:
    prefix, task, raw_index = item_id.split(":", maxsplit=2)
    if prefix != "mvbench" or not task or not raw_index:
        raise ValueError(f"invalid MVBench item id: {item_id!r}")
    return task, int(raw_index)


def _manifest_item_ids(manifest: Path) -> list[str]:
    payload = tomllib.loads(manifest.read_text(encoding="utf-8"))
    if payload.get("benchmark") != "mvbench":
        raise ValueError(f"expected an MVBench manifest, got {payload.get('benchmark')!r}")
    item_ids = payload.get("item_ids")
    if not isinstance(item_ids, list) or not item_ids:
        raise ValueError(f"{manifest} must contain a non-empty item_ids list")
    if not all(isinstance(item_id, str) for item_id in item_ids):
        raise ValueError(f"{manifest} has non-string item_ids")
    if len(set(item_ids)) != len(item_ids):
        raise ValueError(f"{manifest} has duplicate item_ids")
    return item_ids


def _load_items(manifest: Path) -> list[MVBenchProbeItem]:
    item_ids = _manifest_item_ids(manifest)
    payload_by_task: dict[str, list[dict[str, Any]]] = {}
    ordered_keys = [_parse_mvbench_item_id(item_id) for item_id in item_ids]
    for task, _ in ordered_keys:
        if task not in payload_by_task:
            payload_by_task[task] = json.loads((MVBENCH_JSON_DIR / f"{task}.json").read_text())

    items: list[MVBenchProbeItem] = []
    for item_id, (task, index) in zip(item_ids, ordered_keys, strict=True):
        payload = payload_by_task[task]
        if index >= len(payload):
            raise IndexError(
                f"MVBench item index {index} is out of range for task {task!r} "
                f"with {len(payload)} examples"
            )
        example = payload[index]
        video_name = str(example["video"])
        items.append(
            MVBenchProbeItem(
                item_id=item_id,
                group=task,
                video_path=_find_mvbench_video(video_name),
                question=str(example["question"]),
                start_seconds=(
                    float(example["start"]) if example.get("start") not in {None, ""} else None
                ),
                end_seconds=(
                    float(example["end"]) if example.get("end") not in {None, ""} else None
                ),
            )
        )
    return items


def _video_frame_rate(video_path: Path) -> float:
    with av.open(str(video_path)) as container:
        stream = container.streams.video[0]
        rate = stream.average_rate or stream.base_rate
    if rate is None:
        raise ValueError(f"could not determine frame rate for {video_path}")
    return float(rate)


def _frame_window(
    video_path: Path,
    *,
    start_seconds: float | None,
    end_seconds: float | None,
    max_frames: int,
) -> tuple[float, int, int]:
    if start_seconds is not None and start_seconds < 0.0:
        raise ValueError("start_seconds must be non-negative")
    if end_seconds is not None and end_seconds < 0.0:
        raise ValueError("end_seconds must be non-negative")
    if start_seconds is not None and end_seconds is not None and end_seconds <= start_seconds:
        raise ValueError(
            f"end_seconds must be greater than start_seconds, got {start_seconds} -> {end_seconds}"
        )

    fps = _video_frame_rate(video_path)
    start_frame = 0 if start_seconds is None else max(0, int(math.floor(start_seconds * fps)))
    max_end_frame = start_frame + max_frames
    if end_seconds is None:
        end_frame = max_end_frame
    else:
        segment_end_frame = max(start_frame + 1, int(math.ceil(end_seconds * fps)))
        end_frame = min(max_end_frame, segment_end_frame)
    return fps, start_frame, end_frame


def _summarize_video(
    video_path: Path,
    *,
    max_frames: int,
    mv_only: bool,
    start_seconds: float | None,
    end_seconds: float | None,
) -> dict[str, Any]:
    fps, start_frame, end_frame = _frame_window(
        video_path,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        max_frames=max_frames,
    )
    started = time.perf_counter()
    extractor = H264MetadataExtractor(video_path, max_frames=end_frame, mv_only=mv_only)
    motion_means: list[float] = []
    residual_means: list[float] = []
    frame_types: dict[str, int] = {}
    frames = 0
    for frame in extractor.iter_frames():
        if frame.index < start_frame:
            continue
        if frame.index >= end_frame:
            break
        frames += 1
        frame_types[frame.frame_type] = frame_types.get(frame.frame_type, 0) + 1
        macroblocks = frame.macroblocks
        forward = np.nan_to_num(
            np.asarray(macroblocks["mv_magnitude"], dtype=np.float32),
            nan=0.0,
            posinf=0.0,
            neginf=0.0,
        )
        backward = np.nan_to_num(
            np.asarray(macroblocks["mv_magnitude_back"], dtype=np.float32),
            nan=0.0,
            posinf=0.0,
            neginf=0.0,
        )
        motion = np.maximum(forward, backward)
        residual = np.nan_to_num(
            np.asarray(macroblocks["residual_energy"], dtype=np.float32),
            nan=0.0,
            posinf=0.0,
            neginf=0.0,
        )
        motion_means.append(float(np.mean(motion)))
        residual_means.append(float(np.mean(residual)))
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    if frames == 0:
        raise ValueError(f"no frames decoded from {video_path}")
    return {
        "video_path": str(video_path),
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "fps": fps,
        "start_frame": start_frame,
        "end_frame_exclusive": end_frame,
        "frames": frames,
        "frame_types": frame_types,
        "mean_motion_magnitude": float(np.mean(motion_means)),
        "mean_residual_energy": float(np.mean(residual_means)),
        "elapsed_ms": elapsed_ms,
        "elapsed_ms_per_frame": elapsed_ms / float(frames),
    }


def _group_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    motion = np.asarray([row["mean_motion_magnitude"] for row in rows], dtype=np.float64)
    residual = np.asarray([row["mean_residual_energy"] for row in rows], dtype=np.float64)
    elapsed = np.asarray([row["elapsed_ms_per_frame"] for row in rows], dtype=np.float64)
    return {
        "n": len(rows),
        "mean_motion_magnitude": float(np.mean(motion)),
        "median_motion_magnitude": float(np.median(motion)),
        "mean_residual_energy": float(np.mean(residual)),
        "median_residual_energy": float(np.median(residual)),
        "mean_elapsed_ms_per_frame": float(np.mean(elapsed)),
        "item_ids": [str(row["item_id"]) for row in rows],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("research/benchmark_manifests/mvbench_motion_dev_v2.toml"),
    )
    parser.add_argument("--max-items-per-group", type=int, default=5)
    parser.add_argument("--max-frames", type=int, default=20)
    parser.add_argument("--mv-only", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.max_items_per_group <= 0:
        raise SystemExit("--max-items-per-group must be positive")
    if args.max_frames <= 0:
        raise SystemExit("--max-frames must be positive")

    items = _load_items(args.manifest)
    selected_by_group: dict[str, list[MVBenchProbeItem]] = defaultdict(list)
    for item in items:
        bucket = selected_by_group[item.group]
        if len(bucket) < args.max_items_per_group:
            bucket.append(item)

    rows: list[dict[str, Any]] = []
    for group in sorted(selected_by_group):
        for item in selected_by_group[group]:
            summary = _summarize_video(
                item.video_path,
                max_frames=args.max_frames,
                mv_only=args.mv_only,
                start_seconds=item.start_seconds,
                end_seconds=item.end_seconds,
            )
            rows.append(
                {
                    "item_id": item.item_id,
                    "group": item.group,
                    "question": item.question,
                    **summary,
                }
            )

    rows_by_group: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        rows_by_group[cast(str, row["group"])].append(row)
    payload = {
        "manifest": str(args.manifest),
        "max_items_per_group": args.max_items_per_group,
        "max_frames": args.max_frames,
        "mv_only": args.mv_only,
        "n_items": len(rows),
        "by_group": {
            group: _group_summary(group_rows) for group, group_rows in sorted(rows_by_group.items())
        },
        "rows": rows,
    }
    encoded = json.dumps(payload, indent=2, sort_keys=True)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded + "\n", encoding="utf-8")
    else:
        print(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
