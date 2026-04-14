#!/usr/bin/env python3
"""Replay-accelerated planner grid search over statistic × thresholds × reuse_classes × max_age.

Splits into two phases:

calibrate
  CPU-only pass over a frozen benchmark manifest. For each candidate policy
  point, decode frames once and compute the per-adjacent-pair reuse ratio that
  the policy would produce. Groups candidates into target active-reuse bins
  (configurable) and emits a compact `calibration.json` describing which
  policy points fall into each bin.

sweep
  Given a calibration file, pick a small number of policies per bin (by
  default one policy per bin per statistic) and invoke the benchmark runner
  for each. Uses the feature replay cache, so repeated runs on the same
  manifest skip the dense vision encode entirely.

Both phases are preregistered: they write their config into the output JSON
so a future reader can reproduce the search by rerunning the same commands.
"""

from __future__ import annotations

import argparse
import itertools
import json
import subprocess
import sys
import tomllib
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

import av
import numpy as np
from PIL import Image

from codec_through.temporal import (
    BlockClass,
    BlockStatistic,
    PlannerConfig,
    classify_blocks_with_planner,
)

# Re-use the main benchmark runner's manifest + video lookup so path
# resolution stays consistent across Track A scripts.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_benchmark_track_a import _load_items_by_id as _load_benchmark_items  # noqa: E402

TOMATO_VIDEO_DIR = Path("data/benchmarks/tomato/videos")
MVBENCH_VIDEO_DIR = Path("data/benchmarks/mvbench/video")
DEFAULT_MODEL_PATH = Path.home() / "models" / "Qwen2.5-VL-7B-Instruct-4bit"
BENCHMARK_FRAME_SIZE = 560
BLOCK_SIZE = 28


@dataclass(frozen=True, slots=True)
class PolicyCandidate:
    """A candidate planner policy point.

    `label` is a short string suitable for artifact filenames.
    """

    label: str
    statistic: BlockStatistic
    static_threshold: float
    shifted_threshold: float
    pixel_change_threshold: float
    top_k: int
    reuse_classes: tuple[BlockClass, ...]
    max_age: int | None = None

    def planner_config(self) -> PlannerConfig:
        return PlannerConfig(
            statistic=self.statistic,
            static_threshold=self.static_threshold,
            shifted_threshold=self.shifted_threshold,
            pixel_change_threshold=self.pixel_change_threshold,
            top_k=self.top_k,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "statistic": self.statistic.value,
            "static_threshold": self.static_threshold,
            "shifted_threshold": self.shifted_threshold,
            "pixel_change_threshold": self.pixel_change_threshold,
            "top_k": self.top_k,
            "reuse_classes": [cls.name.lower() for cls in self.reuse_classes],
            "max_age": self.max_age,
        }


@dataclass(frozen=True, slots=True)
class CalibrationPoint:
    candidate: PolicyCandidate
    mean_active_reuse: float
    per_item_active_reuse: list[float]


@dataclass(frozen=True, slots=True)
class Manifest:
    benchmark: Literal["tomato", "mvbench"]
    item_ids: tuple[str, ...]
    path: Path


def _load_manifest(path: Path) -> Manifest:
    payload = tomllib.loads(path.read_text())
    benchmark = payload.get("benchmark")
    if benchmark not in {"tomato", "mvbench"}:
        raise ValueError(f"invalid benchmark in manifest {path}: {benchmark!r}")
    ids = tuple(str(entry) for entry in payload.get("item_ids", []))
    if not ids:
        raise ValueError(f"manifest {path} has no item_ids")
    return Manifest(benchmark=benchmark, item_ids=ids, path=path)


def _resolve_video_paths(
    benchmark: Literal["tomato", "mvbench"], item_ids: list[str]
) -> dict[str, Path]:
    """Resolve benchmark item ids to video paths via the main runner registry."""
    items = _load_benchmark_items(benchmark, item_ids=item_ids)
    return {item.item_id: item.video_path for item in items}


def _decode_uniform_frames(video_path: Path, *, frame_count: int) -> list[Image.Image]:
    """Decode all frames, then resample to frame_count with np.linspace indices.

    Mirrors `scripts/run_benchmark_track_a.py` so calibration reuse ratios
    match the ratios observed during the actual benchmark run: duplicates
    allowed when the source clip has fewer than frame_count frames.
    """
    if frame_count <= 0:
        raise ValueError("frame_count must be positive")
    raw_frames: list[Image.Image] = []
    with av.open(str(video_path)) as container:
        stream = container.streams.video[0]
        stream.thread_type = "AUTO"
        for frame in container.decode(video=0):
            img = cast(Image.Image, frame.to_image()).convert("RGB")  # type: ignore[no-untyped-call]
            raw_frames.append(img)
    if not raw_frames:
        raise ValueError(f"no frames decoded from {video_path}")
    if frame_count == 1:
        return [raw_frames[0]]
    indices = np.linspace(0, len(raw_frames) - 1, frame_count, dtype=int).tolist()
    return [raw_frames[index] for index in indices]


def _letterbox_to(image: Image.Image, *, size: int) -> Image.Image:
    w, h = image.size
    scale = size / max(w, h)
    new_w = max(1, round(w * scale))
    new_h = max(1, round(h * scale))
    resized = image.resize((new_w, new_h), Image.Resampling.BICUBIC)
    canvas = Image.new("RGB", (size, size), (0, 0, 0))
    paste_x = (size - new_w) // 2
    paste_y = (size - new_h) // 2
    canvas.paste(resized, (paste_x, paste_y))
    return canvas


def _classify_pair_active_reuse(
    prev_frame: np.ndarray,
    curr_frame: np.ndarray,
    *,
    config: PlannerConfig,
    reuse_classes: tuple[BlockClass, ...],
) -> float:
    classes = classify_blocks_with_planner(
        prev_frame, curr_frame, block_size=BLOCK_SIZE, config=config
    )
    reuse_set = {int(c) for c in reuse_classes}
    mask = np.isin(classes, list(reuse_set))
    return float(mask.mean())


def _build_candidate_list(
    *,
    statistics: list[BlockStatistic],
    mean_threshold_pairs: list[tuple[float, float]],
    max_abs_threshold_pairs: list[tuple[float, float]],
    cpf_configs: list[tuple[float, float, float]],
    topk_configs: list[tuple[int, float, float]],
    reuse_classes_options: list[tuple[BlockClass, ...]],
    max_ages: list[int | None],
) -> list[PolicyCandidate]:
    candidates: list[PolicyCandidate] = []

    def emit(
        stat: BlockStatistic,
        label: str,
        static_thr: float,
        shifted_thr: float,
        *,
        pixel_thr: float = 8.0,
        top_k: int = 16,
    ) -> None:
        for reuse_cls in reuse_classes_options:
            for age in max_ages:
                reuse_label = "+".join(c.name.lower() for c in reuse_cls)
                age_label = f"age{age}" if age is not None else "noage"
                full_label = f"{stat.value}-{label}-{reuse_label}-{age_label}"
                candidates.append(
                    PolicyCandidate(
                        label=full_label,
                        statistic=stat,
                        static_threshold=static_thr,
                        shifted_threshold=shifted_thr,
                        pixel_change_threshold=pixel_thr,
                        top_k=top_k,
                        reuse_classes=reuse_cls,
                        max_age=age,
                    )
                )

    if BlockStatistic.MEAN in statistics:
        for s, h in mean_threshold_pairs:
            emit(BlockStatistic.MEAN, f"{s}-{h}", s, h)
    if BlockStatistic.MAX_ABS in statistics:
        for s, h in max_abs_threshold_pairs:
            emit(BlockStatistic.MAX_ABS, f"{s}-{h}", s, h)
    if BlockStatistic.CHANGED_PIXEL_FRACTION in statistics:
        for pixel_thr, s, h in cpf_configs:
            emit(
                BlockStatistic.CHANGED_PIXEL_FRACTION,
                f"px{pixel_thr}-{s}-{h}",
                s,
                h,
                pixel_thr=pixel_thr,
            )
    if BlockStatistic.TOP_K_MEAN in statistics:
        for k, s, h in topk_configs:
            emit(
                BlockStatistic.TOP_K_MEAN,
                f"k{k}-{s}-{h}",
                s,
                h,
                top_k=k,
            )
    return candidates


def _default_candidates() -> list[PolicyCandidate]:
    return _build_candidate_list(
        statistics=[
            BlockStatistic.MEAN,
            BlockStatistic.MAX_ABS,
            BlockStatistic.CHANGED_PIXEL_FRACTION,
            BlockStatistic.TOP_K_MEAN,
        ],
        mean_threshold_pairs=[
            (1.0, 4.0),
            (2.0, 6.0),
            (3.0, 8.0),
            (4.0, 10.0),
            (5.0, 12.0),
        ],
        max_abs_threshold_pairs=[
            (8.0, 32.0),
            (12.0, 48.0),
            (16.0, 64.0),
            (24.0, 96.0),
            (32.0, 128.0),
        ],
        cpf_configs=[
            (8.0, 0.02, 0.08),
            (8.0, 0.05, 0.15),
            (8.0, 0.1, 0.3),
            (16.0, 0.02, 0.08),
            (16.0, 0.05, 0.15),
        ],
        topk_configs=[
            (4, 8.0, 24.0),
            (16, 8.0, 24.0),
            (64, 4.0, 12.0),
        ],
        reuse_classes_options=[
            (BlockClass.STATIC,),
            (BlockClass.STATIC, BlockClass.SHIFTED),
        ],
        max_ages=[None, 2, 4, 8],
    )


def _decode_and_normalize(
    video_path: Path, *, frame_count: int
) -> list[np.ndarray]:
    frames = _decode_uniform_frames(video_path, frame_count=frame_count)
    letterboxed = [_letterbox_to(f, size=BENCHMARK_FRAME_SIZE) for f in frames]
    return [np.array(f, dtype=np.uint8) for f in letterboxed]


def _calibrate(
    candidates: list[PolicyCandidate],
    manifest: Manifest,
    *,
    frame_count: int,
) -> list[CalibrationPoint]:
    # decode once per item, then loop policies (cheap on CPU)
    print(f"decoding {len(manifest.item_ids)} clips for calibration", file=sys.stderr)
    video_paths = _resolve_video_paths(manifest.benchmark, list(manifest.item_ids))
    frames_by_item: dict[str, list[np.ndarray]] = {}
    for item_id in manifest.item_ids:
        frames_by_item[item_id] = _decode_and_normalize(
            video_paths[item_id], frame_count=frame_count
        )
    results: list[CalibrationPoint] = []
    for idx, cand in enumerate(candidates):
        per_item = []
        cfg = cand.planner_config()
        for item_id in manifest.item_ids:
            frames = frames_by_item[item_id]
            pair_reuses = []
            for a, b in itertools.pairwise(frames):
                pair_reuses.append(
                    _classify_pair_active_reuse(
                        a, b, config=cfg, reuse_classes=cand.reuse_classes
                    )
                )
            per_item.append(float(np.mean(pair_reuses)) if pair_reuses else 0.0)
        mean_reuse = float(np.mean(per_item))
        results.append(
            CalibrationPoint(
                candidate=cand,
                mean_active_reuse=mean_reuse,
                per_item_active_reuse=per_item,
            )
        )
        if (idx + 1) % 25 == 0 or idx == len(candidates) - 1:
            print(
                f"  calibrated {idx + 1}/{len(candidates)} policies",
                file=sys.stderr,
            )
    return results


def _bin_candidates(
    points: list[CalibrationPoint],
    *,
    target_bins: list[tuple[float, float]],
) -> dict[str, list[CalibrationPoint]]:
    bins: dict[str, list[CalibrationPoint]] = {
        f"{low:.2f}-{high:.2f}": [] for low, high in target_bins
    }
    for point in points:
        for low, high in target_bins:
            if low <= point.mean_active_reuse < high:
                bins[f"{low:.2f}-{high:.2f}"].append(point)
                break
    return bins


def _select_representative_policies(
    bins: dict[str, list[CalibrationPoint]],
    *,
    per_bin: int,
) -> list[CalibrationPoint]:
    selected: list[CalibrationPoint] = []
    seen_labels: set[str] = set()
    for bin_points in bins.values():
        # dedup per (statistic, reuse_classes, max_age), pick the closest to bin center
        grouped: dict[tuple[str, str, str], list[CalibrationPoint]] = defaultdict(list)
        for point in bin_points:
            key = (
                point.candidate.statistic.value,
                "+".join(c.name.lower() for c in point.candidate.reuse_classes),
                str(point.candidate.max_age),
            )
            grouped[key].append(point)
        for items in grouped.values():
            # pick per_bin items per (statistic, reuse_classes, max_age) per bin
            items_sorted = sorted(items, key=lambda p: p.mean_active_reuse)
            take = items_sorted[:per_bin]
            for chosen in take:
                if chosen.candidate.label in seen_labels:
                    continue
                selected.append(chosen)
                seen_labels.add(chosen.candidate.label)
    return selected


def _run_sweep_policy(
    *,
    candidate: PolicyCandidate,
    manifest_path: Path,
    benchmark: str,
    frame_count: int,
    model_path: Path,
    output_dir: Path,
    feature_cache_dir: Path,
    allow_dirty: bool,
    log_option_logprobs: bool,
) -> dict[str, Any]:
    jsonl_path = output_dir / f"{candidate.label}.jsonl"
    summary_path = output_dir / f"{candidate.label}_summary.json"
    command = [
        sys.executable,
        str(Path("scripts/run_benchmark_track_a.py")),
        "run",
        "--benchmark",
        benchmark,
        "--manifest",
        str(manifest_path),
        "--chunk-size",
        "1",
        "--frame-count",
        str(frame_count),
        "--cache-mode",
        "default",
        "--model-path",
        str(model_path),
        "--output-path",
        str(jsonl_path),
        "--summary-path",
        str(summary_path),
        "--feature-cache-dir",
        str(feature_cache_dir),
        "--statistic",
        candidate.statistic.value,
        "--static-threshold",
        str(candidate.static_threshold),
        "--shifted-threshold",
        str(candidate.shifted_threshold),
        "--pixel-change-threshold",
        str(candidate.pixel_change_threshold),
        "--top-k",
        str(candidate.top_k),
        "--reuse-classes",
        ",".join(cls.name.lower() for cls in candidate.reuse_classes),
    ]
    if candidate.max_age is not None:
        command.extend(["--max-age", str(candidate.max_age)])
    if allow_dirty:
        command.append("--allow-dirty")
    if log_option_logprobs:
        command.append("--log-option-logprobs")
    subprocess.run(command, check=True)
    summary = json.loads(summary_path.read_text())
    return {
        "candidate": candidate.as_dict(),
        "jsonl_path": str(jsonl_path),
        "summary_path": str(summary_path),
        "summary": summary,
    }


def _cmd_calibrate(args: argparse.Namespace) -> None:
    manifest = _load_manifest(args.manifest)
    candidates = _default_candidates()
    points = _calibrate(candidates, manifest, frame_count=args.frame_count)
    target_bins = [
        (0.0, 0.25),
        (0.25, 0.50),
        (0.50, 0.70),
        (0.70, 0.85),
        (0.85, 0.95),
        (0.95, 1.0001),
    ]
    bins = _bin_candidates(points, target_bins=target_bins)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "manifest_path": str(args.manifest),
        "benchmark": manifest.benchmark,
        "frame_count": args.frame_count,
        "candidate_count": len(candidates),
        "target_bins": [list(b) for b in target_bins],
        "points": [
            {
                "candidate": point.candidate.as_dict(),
                "mean_active_reuse": point.mean_active_reuse,
                "per_item_active_reuse": point.per_item_active_reuse,
            }
            for point in points
        ],
        "bin_counts": {k: len(v) for k, v in bins.items()},
    }
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"wrote {args.out}", file=sys.stderr)
    for bin_label, bin_points in bins.items():
        print(f"  bin {bin_label}: {len(bin_points)} policies", file=sys.stderr)


def _cmd_sweep(args: argparse.Namespace) -> None:
    calibration = json.loads(Path(args.calibration).read_text())
    manifest_path = Path(calibration["manifest_path"])
    manifest = _load_manifest(manifest_path)
    if manifest.benchmark != calibration["benchmark"]:
        raise ValueError("benchmark mismatch between calibration and manifest")
    target_bins = [tuple(b) for b in calibration["target_bins"]]
    points = [
        CalibrationPoint(
            candidate=_candidate_from_dict(p["candidate"]),
            mean_active_reuse=p["mean_active_reuse"],
            per_item_active_reuse=p["per_item_active_reuse"],
        )
        for p in calibration["points"]
    ]
    bins = _bin_candidates(points, target_bins=target_bins)
    selected = _select_representative_policies(bins, per_bin=args.per_bin)
    print(f"selected {len(selected)} representative policies", file=sys.stderr)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for idx, point in enumerate(selected):
        label = point.candidate.label
        print(
            f"[{idx + 1}/{len(selected)}] {label} (calibrated reuse {point.mean_active_reuse:.3f})",
            file=sys.stderr,
        )
        try:
            run_result = _run_sweep_policy(
                candidate=point.candidate,
                manifest_path=manifest_path,
                benchmark=manifest.benchmark,
                frame_count=args.frame_count,
                model_path=args.model_path,
                output_dir=args.output_dir,
                feature_cache_dir=args.feature_cache_dir,
                allow_dirty=args.allow_dirty,
                log_option_logprobs=args.log_option_logprobs,
            )
            run_result["calibrated_mean_active_reuse"] = point.mean_active_reuse
            results.append(run_result)
        except subprocess.CalledProcessError as exc:
            print(f"  FAILED: {exc}", file=sys.stderr)
            results.append(
                {
                    "candidate": point.candidate.as_dict(),
                    "error": str(exc),
                    "calibrated_mean_active_reuse": point.mean_active_reuse,
                }
            )
    payload = {
        "manifest_path": str(manifest_path),
        "benchmark": manifest.benchmark,
        "frame_count": args.frame_count,
        "calibration_path": str(args.calibration),
        "results": results,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"wrote {args.out}", file=sys.stderr)


def _candidate_from_dict(payload: dict[str, Any]) -> PolicyCandidate:
    reuse = tuple(_parse_reuse_class(name) for name in payload["reuse_classes"])
    return PolicyCandidate(
        label=payload["label"],
        statistic=BlockStatistic(payload["statistic"]),
        static_threshold=float(payload["static_threshold"]),
        shifted_threshold=float(payload["shifted_threshold"]),
        pixel_change_threshold=float(payload["pixel_change_threshold"]),
        top_k=int(payload["top_k"]),
        reuse_classes=reuse,
        max_age=payload.get("max_age"),
    )


def _parse_reuse_class(name: str) -> BlockClass:
    mapping = {
        "static": BlockClass.STATIC,
        "shifted": BlockClass.SHIFTED,
        "novel": BlockClass.NOVEL,
    }
    if name not in mapping:
        raise ValueError(f"unknown reuse class: {name}")
    return mapping[name]


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    cal = subparsers.add_parser("calibrate", help="CPU-only active-reuse calibration pass")
    cal.add_argument("--manifest", type=Path, required=True)
    cal.add_argument("--frame-count", type=int, default=8)
    cal.add_argument("--out", type=Path, required=True)
    cal.set_defaults(handler=_cmd_calibrate)

    sweep = subparsers.add_parser("sweep", help="run benchmark sweep on calibrated policies")
    sweep.add_argument("--calibration", type=Path, required=True)
    sweep.add_argument("--frame-count", type=int, default=8)
    sweep.add_argument("--per-bin", type=int, default=1)
    sweep.add_argument("--output-dir", type=Path, required=True)
    sweep.add_argument("--out", type=Path, required=True)
    sweep.add_argument("--model-path", type=Path, default=DEFAULT_MODEL_PATH)
    sweep.add_argument(
        "--feature-cache-dir",
        type=Path,
        default=Path("research/cache/dense_features"),
    )
    sweep.add_argument("--allow-dirty", action="store_true")
    sweep.add_argument("--log-option-logprobs", action="store_true")
    sweep.set_defaults(handler=_cmd_sweep)

    args = parser.parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
