#!/usr/bin/env python3
"""Run benchmark-native Track A reproduction slices on local assets."""

from __future__ import annotations

import argparse
import gc
import json
import subprocess
import sys
import time
import tomllib
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

import mlx.core as mx
import numpy as np
import numpy.typing as npt
from datasets import load_dataset  # type: ignore[import-untyped]
from mlx_vlm import generate, load  # type: ignore[import-untyped]
from mlx_vlm.utils import prepare_inputs  # type: ignore[import-untyped]
from PIL import Image

from codec_through.answers import extract_choice
from codec_through.feature_cache import (
    DEFAULT_FEATURE_CACHE_DIR,
    CacheKey,
    frame_sequence_sha256,
    get_feature_cache,
    model_content_sha256,
    preprocessing_hash,
    put_feature_cache,
)
from codec_through.temporal import (
    BlockClass,
    BlockStatistic,
    BlockThresholds,
    NeighborHaloVetoConfig,
    PlannerConfig,
    apply_neighbor_halo_veto,
    block_statistic_values,
    classify_blocks_with_planner,
)
from codec_through.track_a import (
    active_region_block_mask,
    flattened_reuse_mask,
    qwen_merged_token_counts,
)
from codec_through.video_decode import decode_uniform_frames

TOMATO_DATA_DIR = Path("data/benchmarks/tomato/hf/data")
TOMATO_VIDEO_DIR = Path("data/benchmarks/tomato/videos")
MVBENCH_JSON_DIR = Path("data/benchmarks/mvbench/hf/json")
MVBENCH_VIDEO_DIR = Path("data/benchmarks/mvbench/video")
VIDEOMME_PARQUET_DIR = Path("data/benchmarks/videomme/hf")
VIDEOMME_VIDEO_DIR = Path("data/benchmarks/videomme/videos")

DEFAULT_MODEL_PATH = Path.home() / "models" / "Qwen2.5-VL-7B-Instruct-4bit"
DEFAULT_THRESHOLDS = BlockThresholds(static_threshold=3.0, shifted_threshold=8.0)
DEFAULT_REUSE_CLASSES = (BlockClass.STATIC, BlockClass.SHIFTED)
DEFAULT_PLANNER = PlannerConfig(
    statistic=BlockStatistic.MEAN,
    static_threshold=DEFAULT_THRESHOLDS.static_threshold,
    shifted_threshold=DEFAULT_THRESHOLDS.shifted_threshold,
)
DEFAULT_OUTPUT_PATH = Path("results/benchmark_track_a.jsonl")
DEFAULT_SUMMARY_PATH = Path("results/benchmark_track_a_summary.json")
BENCHMARK_FRAME_SIZE = 560
QWEN_BLOCK_SIZE = 28
QWEN_SPATIAL_MERGE = 2

PREDECESSOR_MVBENCH_TASKS = [
    "action_antonym",
    "action_count",
    "action_localization",
    "action_prediction",
    "action_sequence",
    "character_order",
    "counterfactual_inference",
    "egocentric_navigation",
    "fine_grained_action",
    "moving_attribute",
    "moving_count",
    "moving_direction",
    "object_existence",
    "object_interaction",
    "object_shuffle",
    "scene_transition",
    "state_change",
    "unexpected_action",
]

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
class BenchmarkItem:
    item_id: str
    benchmark: Literal["tomato", "mvbench", "videomme"]
    group: str
    video_path: Path
    question: str
    candidates: list[str]
    answer_index: int
    start_seconds: float | None = None
    end_seconds: float | None = None


@dataclass(frozen=True, slots=True)
class PreparedSample:
    item: BenchmarkItem
    frames: list[Image.Image]
    active_boxes: list[tuple[int, int, int, int]]
    input_ids: mx.array
    pixel_values: mx.array
    mask: mx.array
    extra_kwargs: dict[str, mx.array]


@dataclass(frozen=True, slots=True)
class RunControl:
    stop_file: Path | None = None
    summary_path: Path | None = None


@dataclass(frozen=True, slots=True)
class BenchmarkManifest:
    benchmark: Literal["tomato", "mvbench", "videomme"]
    item_ids: list[str]
    description: str | None = None
    source: str | None = None


def _run(command: list[str]) -> str:
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    return completed.stdout.strip()


def _git_dirty() -> bool:
    return bool(_run(["git", "status", "--short"]))


def _ensure_clean_git_tree(*, allow_dirty: bool) -> None:
    if allow_dirty:
        return
    if _git_dirty():
        raise SystemExit(
            "benchmark runs require a clean git tree; commit or stash changes, "
            "or rerun with --allow-dirty"
        )


def _environment_record(model_path: Path) -> dict[str, Any]:
    import datasets
    import huggingface_hub
    import mlx_vlm

    return {
        "git_sha": _run(["git", "rev-parse", "HEAD"]),
        "git_dirty": _git_dirty(),
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "ffmpeg": _run(["ffmpeg", "-version"]).splitlines()[0],
        "datasets": datasets.__version__,
        "huggingface_hub": huggingface_hub.__version__,
        "mlx_vlm_module": str(Path(mlx_vlm.__file__).resolve()),
        "model_path": str(model_path),
    }


def _square_pad_frame(
    frame: Image.Image,
    *,
    size: int,
) -> tuple[Image.Image, tuple[int, int, int, int]]:
    width, height = frame.size
    if width <= 0 or height <= 0:
        raise ValueError("frame dimensions must be positive")
    scale = min(size / width, size / height)
    resized = frame.resize(
        (round(width * scale), round(height * scale)),
        Image.Resampling.BICUBIC,
    )
    canvas = Image.new("RGB", (size, size), color=(0, 0, 0))
    offset_x = (size - resized.width) // 2
    offset_y = (size - resized.height) // 2
    canvas.paste(resized, (offset_x, offset_y))
    return canvas, (offset_x, offset_y, offset_x + resized.width, offset_y + resized.height)


def _decode_uniform_frames(
    video_path: Path,
    *,
    frame_count: int,
    start_seconds: float | None,
    end_seconds: float | None,
) -> tuple[list[Image.Image], list[tuple[int, int, int, int]]]:
    """Memory-bounded uniform sample, letterboxed to BENCHMARK_FRAME_SIZE.

    Replaces the previous full-clip decode that was a contributing factor
    in the 2026-04-18 Gemma 1.51R pilot OOM (50 GB RSS on 16 GB Mac).
    Selection semantics match the legacy ``np.linspace`` index picking so
    all existing benchmark numbers stay apples-to-apples. See
    :mod:`codec_through.video_decode`.
    """
    selected = decode_uniform_frames(
        video_path,
        frame_count=frame_count,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
    )
    padded_frames: list[Image.Image] = []
    active_boxes: list[tuple[int, int, int, int]] = []
    for selected_frame in selected:
        padded_frame, active_box = _square_pad_frame(selected_frame, size=BENCHMARK_FRAME_SIZE)
        padded_frames.append(padded_frame)
        active_boxes.append(active_box)
    return padded_frames, active_boxes


def _multiple_choice_prompt(question: str, choices: list[str]) -> str:
    lines = [question]
    for index, choice in enumerate(choices):
        lines.append(f"{chr(ord('A') + index)}. {choice}")
    lines.append("Answer with one letter only.")
    return "\n".join(lines)


def _tomato_item_from_example(split: str, example: dict[str, Any]) -> BenchmarkItem:
    key = cast(str, example["key"])
    demonstration_type = cast(str, example["demonstration_type"])
    video_path = TOMATO_VIDEO_DIR / demonstration_type / f"{key}.mp4"
    if not video_path.exists():
        raise FileNotFoundError(f"missing TOMATO video: {video_path}")
    choices = list(cast(list[str], example["options"]))
    return BenchmarkItem(
        item_id=f"tomato:{split}:{key}",
        benchmark="tomato",
        group=split,
        video_path=video_path,
        question=_multiple_choice_prompt(cast(str, example["question"]), choices),
        candidates=choices,
        answer_index=int(example["answer"]),
    )


def _load_tomato_items(per_group: int, *, splits: list[str] | None = None) -> list[BenchmarkItem]:
    requested_splits = splits or [
        "count",
        "direction",
        "rotation",
        "shape_trend",
        "velocity_frequency",
        "visual_cues",
    ]
    data_files = {
        split: str(next(TOMATO_DATA_DIR.glob(f"{split}-*.parquet"))) for split in requested_splits
    }
    datasets_by_split = load_dataset("parquet", data_files=data_files)
    items: list[BenchmarkItem] = []
    for split in requested_splits:
        dataset_split = datasets_by_split[split]
        for example in dataset_split.select(range(min(per_group, len(dataset_split)))):
            items.append(_tomato_item_from_example(split, cast(dict[str, Any], example)))
    return items


def _parse_tomato_item_id(item_id: str) -> tuple[str, str]:
    prefix, split, key = item_id.split(":", maxsplit=2)
    if prefix != "tomato" or not split or not key:
        raise ValueError(f"invalid TOMATO item id: {item_id!r}")
    return split, key


def _load_tomato_items_by_id(item_ids: list[str]) -> list[BenchmarkItem]:
    requested_by_split: dict[str, list[str]] = defaultdict(list)
    for item_id in item_ids:
        split, key = _parse_tomato_item_id(item_id)
        requested_by_split[split].append(key)

    data_files = {
        split: str(next(TOMATO_DATA_DIR.glob(f"{split}-*.parquet"))) for split in requested_by_split
    }
    datasets_by_split = load_dataset("parquet", data_files=data_files)
    rows_by_split: dict[str, dict[str, dict[str, Any]]] = {}
    for split, requested_keys in requested_by_split.items():
        key_set = set(requested_keys)
        rows: dict[str, dict[str, Any]] = {}
        for example in datasets_by_split[split]:
            key = cast(str, example["key"])
            if key in key_set:
                rows[key] = cast(dict[str, Any], example)
        missing = sorted(key_set - set(rows))
        if missing:
            raise KeyError(f"missing TOMATO examples for split {split!r}: {missing}")
        rows_by_split[split] = rows

    return [
        _tomato_item_from_example(split, rows_by_split[split][key])
        for split, key in (_parse_tomato_item_id(item_id) for item_id in item_ids)
    ]


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


def _mvbench_item_from_example(
    task: str,
    index: int,
    example: dict[str, Any],
) -> BenchmarkItem:
    video_name = str(example["video"])
    choices = list(cast(list[str], example["candidates"]))
    answer = str(example["answer"])
    return BenchmarkItem(
        item_id=f"mvbench:{task}:{index}",
        benchmark="mvbench",
        group=task,
        video_path=_find_mvbench_video(video_name),
        question=_multiple_choice_prompt(cast(str, example["question"]), choices),
        candidates=choices,
        answer_index=choices.index(answer),
        start_seconds=(float(example["start"]) if example.get("start") not in {None, ""} else None),
        end_seconds=(float(example["end"]) if example.get("end") not in {None, ""} else None),
    )


def _load_mvbench_items(per_group: int, *, tasks: list[str] | None = None) -> list[BenchmarkItem]:
    requested_tasks = tasks or PREDECESSOR_MVBENCH_TASKS
    items: list[BenchmarkItem] = []
    for task in requested_tasks:
        payload = json.loads((MVBENCH_JSON_DIR / f"{task}.json").read_text())
        for index, example in enumerate(payload[:per_group]):
            items.append(_mvbench_item_from_example(task, index, cast(dict[str, Any], example)))
    return items


def _parse_mvbench_item_id(item_id: str) -> tuple[str, int]:
    prefix, task, raw_index = item_id.split(":", maxsplit=2)
    if prefix != "mvbench" or not task or not raw_index:
        raise ValueError(f"invalid MVBench item id: {item_id!r}")
    return task, int(raw_index)


def _load_mvbench_items_by_id(item_ids: list[str]) -> list[BenchmarkItem]:
    payload_by_task: dict[str, list[dict[str, Any]]] = {}
    ordered_keys = [_parse_mvbench_item_id(item_id) for item_id in item_ids]
    for task, _ in ordered_keys:
        if task not in payload_by_task:
            payload_by_task[task] = json.loads((MVBENCH_JSON_DIR / f"{task}.json").read_text())

    items: list[BenchmarkItem] = []
    for task, index in ordered_keys:
        payload = payload_by_task[task]
        if index >= len(payload):
            raise IndexError(
                f"MVBench item index {index} is out of range for task {task!r} "
                f"with {len(payload)} examples"
            )
        items.append(_mvbench_item_from_example(task, index, payload[index]))
    return items


VIDEOMME_DURATIONS: tuple[str, ...] = ("short", "medium", "long")


def _videomme_choice_text(raw_option: str) -> str:
    """Strip the 'A. '/'B. '/... prefix if the parquet already included one."""
    if len(raw_option) >= 3 and raw_option[0].isalpha() and raw_option[1:3] == ". ":
        return raw_option[3:]
    return raw_option


def _find_videomme_video(video_id: str) -> Path:
    extensions = (".mp4", ".mkv", ".webm", ".avi", ".mov")
    for extension in extensions:
        candidate = VIDEOMME_VIDEO_DIR / f"{video_id}{extension}"
        if candidate.exists():
            return candidate
    matches: list[Path] = []
    if VIDEOMME_VIDEO_DIR.exists():
        for extension in extensions:
            matches.extend(VIDEOMME_VIDEO_DIR.rglob(f"{video_id}{extension}"))
    unique_matches = sorted({match.resolve() for match in matches})
    if len(unique_matches) == 1:
        return unique_matches[0]
    if len(unique_matches) > 1:
        raise RuntimeError(f"ambiguous VideoMME video lookup for {video_id!r}: {unique_matches}")
    raise FileNotFoundError(
        f"could not locate VideoMME video {video_id!r} under {VIDEOMME_VIDEO_DIR}"
    )


def _videomme_item_from_row(row: dict[str, Any]) -> BenchmarkItem:
    video_id = str(row["videoID"])
    duration = str(row["duration"])
    question_id = str(row["question_id"])
    raw_options = [str(option) for option in cast(list[Any], row["options"])]
    choices = [_videomme_choice_text(option) for option in raw_options]
    answer_letter = str(row["answer"]).strip().upper()
    if not (answer_letter.isalpha() and len(answer_letter) == 1):
        raise ValueError(f"invalid VideoMME answer letter: {answer_letter!r}")
    answer_index = ord(answer_letter) - ord("A")
    if answer_index < 0 or answer_index >= len(choices):
        raise ValueError(
            f"VideoMME answer letter {answer_letter!r} out of range for "
            f"{len(choices)} options ({question_id})"
        )
    question_text = str(row["question"])
    return BenchmarkItem(
        item_id=f"videomme:{duration}:{question_id}",
        benchmark="videomme",
        group=duration,
        video_path=_find_videomme_video(video_id),
        question=_multiple_choice_prompt(question_text, choices),
        candidates=choices,
        answer_index=answer_index,
    )


def _videomme_parquet_path() -> Path:
    candidates = sorted(VIDEOMME_PARQUET_DIR.rglob("*.parquet"))
    if not candidates:
        raise FileNotFoundError(
            f"no VideoMME parquet found under {VIDEOMME_PARQUET_DIR}; "
            f"run scripts/fetch_benchmarks.py --dataset videomme --mode metadata"
        )
    return candidates[0]


def _load_videomme_rows() -> list[dict[str, Any]]:
    import pyarrow.parquet as pq

    parquet_path = _videomme_parquet_path()
    table = pq.read_table(parquet_path)
    records = table.to_pylist()
    return cast(list[dict[str, Any]], records)


def _load_videomme_items(
    per_group: int,
    *,
    durations: list[str] | None = None,
) -> list[BenchmarkItem]:
    requested = tuple(durations) if durations else VIDEOMME_DURATIONS
    for duration in requested:
        if duration not in VIDEOMME_DURATIONS:
            raise ValueError(f"unknown VideoMME duration {duration!r}")
    rows = _load_videomme_rows()
    bucket: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        duration = str(row.get("duration"))
        if duration in requested:
            bucket[duration].append(row)
    items: list[BenchmarkItem] = []
    for duration in requested:
        for row in bucket[duration][:per_group]:
            items.append(_videomme_item_from_row(row))
    return items


def _parse_videomme_item_id(item_id: str) -> tuple[str, str]:
    prefix, duration, question_id = item_id.split(":", maxsplit=2)
    if prefix != "videomme" or not duration or not question_id:
        raise ValueError(f"invalid VideoMME item id: {item_id!r}")
    return duration, question_id


def _load_videomme_items_by_id(item_ids: list[str]) -> list[BenchmarkItem]:
    parsed = [_parse_videomme_item_id(item_id) for item_id in item_ids]
    requested_ids = {question_id for _, question_id in parsed}
    rows = _load_videomme_rows()
    rows_by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        qid = str(row.get("question_id"))
        if qid in requested_ids:
            rows_by_id[qid] = row
    missing = sorted(requested_ids - set(rows_by_id))
    if missing:
        raise KeyError(f"missing VideoMME questions: {missing}")
    return [_videomme_item_from_row(rows_by_id[question_id]) for _, question_id in parsed]


def _load_items(
    benchmark: Literal["tomato", "mvbench", "videomme"],
    *,
    per_group: int,
    groups: list[str] | None,
) -> list[BenchmarkItem]:
    if benchmark == "tomato":
        return _load_tomato_items(per_group, splits=groups)
    if benchmark == "videomme":
        return _load_videomme_items(per_group, durations=groups)
    return _load_mvbench_items(per_group, tasks=groups)


def _load_items_by_id(
    benchmark: Literal["tomato", "mvbench", "videomme"],
    item_ids: list[str],
) -> list[BenchmarkItem]:
    if benchmark == "tomato":
        return _load_tomato_items_by_id(item_ids)
    if benchmark == "videomme":
        return _load_videomme_items_by_id(item_ids)
    return _load_mvbench_items_by_id(item_ids)


def _load_manifest(path: Path) -> BenchmarkManifest:
    payload = tomllib.loads(path.read_text())
    benchmark = payload.get("benchmark")
    item_ids = payload.get("item_ids")
    if benchmark not in {"tomato", "mvbench", "videomme"}:
        raise ValueError(f"invalid benchmark manifest benchmark: {benchmark!r}")
    if (
        not isinstance(item_ids, list)
        or not item_ids
        or not all(isinstance(item_id, str) for item_id in item_ids)
    ):
        raise ValueError(f"invalid benchmark manifest item_ids: {item_ids!r}")
    return BenchmarkManifest(
        benchmark=cast(Literal["tomato", "mvbench", "videomme"], benchmark),
        item_ids=list(cast(list[str], item_ids)),
        description=cast(str | None, payload.get("description")),
        source=cast(str | None, payload.get("source")),
    )


def _load_model(model_path: Path) -> tuple[Any, Any]:
    return cast(tuple[Any, Any], load(str(model_path)))


def _prepare_sample(
    model: Any,
    processor: Any,
    item: BenchmarkItem,
    *,
    frame_count: int,
) -> PreparedSample:
    del model
    if hasattr(processor, "image_processor"):
        if hasattr(processor.image_processor, "do_resize"):
            processor.image_processor.do_resize = False
        if hasattr(processor.image_processor, "do_image_splitting"):
            processor.image_processor.do_image_splitting = False
    frames, active_boxes = _decode_uniform_frames(
        item.video_path,
        frame_count=frame_count,
        start_seconds=item.start_seconds,
        end_seconds=item.end_seconds,
    )
    messages = [
        {
            "role": "user",
            "content": [
                *({"type": "image"} for _ in frames),
                {"type": "text", "text": item.question},
            ],
        }
    ]
    rendered_prompt = processor.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    raw_inputs = prepare_inputs(processor, images=frames, prompts=rendered_prompt)
    input_ids = mx.array(raw_inputs["input_ids"])
    pixel_values = mx.array(raw_inputs["pixel_values"])
    mask = mx.array(raw_inputs["attention_mask"])
    extra_kwargs = {
        key: mx.array(value)
        for key, value in raw_inputs.items()
        if key not in {"input_ids", "pixel_values", "attention_mask"}
    }
    return PreparedSample(
        item=item,
        frames=frames,
        active_boxes=active_boxes,
        input_ids=input_ids,
        pixel_values=pixel_values,
        mask=mask,
        extra_kwargs=extra_kwargs,
    )


def _compute_cached_features(model: Any, sample: PreparedSample) -> mx.array:
    image_grid_thw = sample.extra_kwargs["image_grid_thw"]
    dtype = model.vision_tower.patch_embed.proj.weight.dtype
    features = model.vision_tower(
        sample.pixel_values.astype(dtype),
        image_grid_thw,
        output_hidden_states=False,
    )
    mx.eval(features)
    return cast(mx.array, features)


def _feature_cache_key(
    sample: PreparedSample, *, model_path: Path, model_content_hash: str
) -> CacheKey:
    width, height = sample.frames[0].size
    return CacheKey(
        model_id=str(model_path.resolve()),
        model_content_sha256=model_content_hash,
        item_id=sample.item.item_id,
        frames_sha256=frame_sequence_sha256(sample.frames),
        frame_count=len(sample.frames),
        frame_size_h=height,
        frame_size_w=width,
        preprocessing_hash=preprocessing_hash(
            decode_backend="pyav",
            sampling_mode="uniform_global",
            max_size=BENCHMARK_FRAME_SIZE,
        ),
    )


def _compute_cached_features_with_replay(
    model: Any,
    sample: PreparedSample,
    *,
    model_path: Path,
    model_content_hash: str,
    use_feature_replay: bool,
    feature_cache_dir: Path,
) -> tuple[mx.array, bool]:
    if not use_feature_replay:
        return _compute_cached_features(model, sample), False

    key = _feature_cache_key(sample, model_path=model_path, model_content_hash=model_content_hash)
    cached = get_feature_cache(key, cache_dir=feature_cache_dir)
    current_grid = np.array(sample.extra_kwargs["image_grid_thw"].tolist(), dtype=np.int64)
    if cached is not None:
        cached_features_np, cached_grid, _meta = cached
        if not np.array_equal(cached_grid, current_grid):
            raise ValueError(
                f"feature replay cache hit had mismatched image_grid_thw for {sample.item.item_id}"
            )
        cached_features = mx.array(cached_features_np)
        mx.eval(cached_features)
        return cached_features, True

    features = _compute_cached_features(model, sample)
    put_feature_cache(
        key,
        features=np.array(features),
        image_grid_thw=current_grid,
        meta={
            "benchmark": sample.item.benchmark,
            "group": sample.item.group,
            "item_id": sample.item.item_id,
            "model_id": str(model_path.resolve()),
            "model_content_sha256": model_content_hash,
        },
        cache_dir=feature_cache_dir,
    )
    return features, False


def _masked_mean(values: np.ndarray, mask: np.ndarray) -> float:
    if values.shape != mask.shape:
        raise ValueError("values and mask must have the same shape")
    if not mask.any():
        raise ValueError("mask must select at least one block")
    return float(values[mask].mean())


def _mean_or_none(values: list[float]) -> float | None:
    return float(np.mean(values)) if values else None


def _planner_payload(
    planner_config: PlannerConfig,
    *,
    reuse_classes: tuple[BlockClass, ...],
    max_age: int | None,
    sticky_window: int | None = None,
    halo_veto: NeighborHaloVetoConfig | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "statistic": planner_config.statistic.value,
        "static_threshold": planner_config.static_threshold,
        "shifted_threshold": planner_config.shifted_threshold,
        "pixel_change_threshold": planner_config.pixel_change_threshold,
        "top_k": planner_config.top_k,
        "reuse_classes": [block_class.name.lower() for block_class in reuse_classes],
        "max_age": max_age,
        "sticky_window": sticky_window,
    }
    if halo_veto is not None:
        payload["neighbor_halo_veto"] = {
            "percentile": halo_veto.percentile,
            "neighborhood": halo_veto.neighborhood,
        }
    return payload


def _parse_reuse_classes(raw_value: str) -> tuple[BlockClass, ...]:
    mapping = {
        "static": BlockClass.STATIC,
        "shifted": BlockClass.SHIFTED,
        "novel": BlockClass.NOVEL,
    }
    selected: list[BlockClass] = []
    for part in raw_value.split(","):
        normalized = part.strip().lower()
        if not normalized:
            continue
        if normalized not in mapping:
            raise ValueError(f"unsupported reuse class: {part!r}")
        block_class = mapping[normalized]
        if block_class not in selected:
            selected.append(block_class)
    if not selected:
        raise ValueError("reuse_classes must include at least one class")
    return tuple(selected)


def _validate_max_age(max_age: int | None) -> int | None:
    if max_age is None:
        return None
    if max_age <= 0:
        raise ValueError("max_age must be positive when provided")
    return max_age


def _apply_age_gate(
    reuse_mask: npt.NDArray[np.bool_],
    ages: npt.NDArray[np.int32],
    *,
    max_age: int | None,
) -> tuple[npt.NDArray[np.bool_], npt.NDArray[np.int32]]:
    if reuse_mask.shape != ages.shape:
        raise ValueError("reuse_mask and ages must match")
    allowed = reuse_mask if max_age is None else reuse_mask & (ages < max_age)
    next_ages = np.where(allowed, ages + 1, 0).astype(np.int32)
    return allowed, next_ages


def _mix_qwen_features(
    sample: PreparedSample,
    features: mx.array,
    *,
    planner_config: PlannerConfig,
    reuse_classes: tuple[BlockClass, ...],
    max_age: int | None,
    sticky_window: int | None = None,
    halo_veto_config: NeighborHaloVetoConfig | None = None,
) -> tuple[mx.array, list[float], list[float]]:
    image_grid_thw = np.array(sample.extra_kwargs["image_grid_thw"].tolist(), dtype=np.int64)
    counts = qwen_merged_token_counts(image_grid_thw, spatial_merge_size=QWEN_SPATIAL_MERGE)
    if len(counts) != len(sample.frames):
        raise ValueError("frame count and Qwen grid count mismatch")

    dense_segments: list[mx.array] = []
    offset = 0
    for count in counts:
        dense_segments.append(features[offset : offset + count])
        offset += count

    mixed_segments = [dense_segments[0]]
    ages = np.zeros(dense_segments[0].shape[0], dtype=np.int32)
    # CodecSight-style sticky-dynamic: once a block is classified as
    # non-reusable within a reset window, it stays non-reusable for the
    # remainder of the window. Window resets at
    # `frame_index % sticky_window == 0` (the "I-frame equivalent").
    dynamic_latched = np.zeros(dense_segments[0].shape[0], dtype=bool)
    raw_reused_ratios: list[float] = []
    active_reused_ratios: list[float] = []
    for frame_index in range(1, len(sample.frames)):
        if sticky_window is not None and frame_index % sticky_window == 0:
            dynamic_latched = np.zeros_like(dynamic_latched)
        previous = np.array(sample.frames[frame_index - 1], dtype=np.uint8)
        current = np.array(sample.frames[frame_index], dtype=np.uint8)
        classification = classify_blocks_with_planner(
            previous,
            current,
            block_size=QWEN_BLOCK_SIZE,
            config=planner_config,
        )
        if halo_veto_config is not None:
            block_scores = block_statistic_values(
                previous,
                current,
                block_size=QWEN_BLOCK_SIZE,
                config=planner_config,
            )
            classification = apply_neighbor_halo_veto(
                classification,
                block_scores,
                config=halo_veto_config,
            )
        reuse_mask = flattened_reuse_mask(classification, reuse_classes=reuse_classes)
        if reuse_mask.size != dense_segments[frame_index].shape[0]:
            raise ValueError(
                "classification/token mismatch: "
                f"mask={reuse_mask.size}, tokens={dense_segments[frame_index].shape[0]}"
            )
        if sticky_window is not None:
            dynamic_latched = dynamic_latched | ~reuse_mask
            reuse_mask = reuse_mask & ~dynamic_latched
        allowed_mask, ages = _apply_age_gate(reuse_mask, ages, max_age=max_age)
        previous_active = active_region_block_mask(
            sample.frames[frame_index - 1].size,
            sample.active_boxes[frame_index - 1],
            block_size=QWEN_BLOCK_SIZE,
        )
        current_active = active_region_block_mask(
            sample.frames[frame_index].size,
            sample.active_boxes[frame_index],
            block_size=QWEN_BLOCK_SIZE,
        )
        active_mask = previous_active & current_active
        if active_mask.size != reuse_mask.size:
            raise ValueError(
                f"active-region/token mismatch: mask={active_mask.size}, tokens={reuse_mask.size}"
            )
        mixed_segments.append(
            mx.where(
                mx.array(allowed_mask[:, None]),
                mixed_segments[-1],
                dense_segments[frame_index],
            )
        )
        raw_reused_ratios.append(float(allowed_mask.mean()))
        active_reused_ratios.append(_masked_mean(allowed_mask.astype(np.float32), active_mask))
    mixed = mx.concatenate(mixed_segments, axis=0)
    mx.eval(mixed)
    return mixed, raw_reused_ratios, active_reused_ratios


def _select_cached_features(
    sample: PreparedSample,
    features: mx.array,
    *,
    cache_mode: Literal["default", "identity"],
    refresh_interval: int | None,
    planner_config: PlannerConfig,
    reuse_classes: tuple[BlockClass, ...],
    max_age: int | None,
    sticky_window: int | None = None,
    halo_veto_config: NeighborHaloVetoConfig | None = None,
) -> tuple[mx.array, list[float], list[float]]:
    if cache_mode == "identity":
        return features, [], []
    if refresh_interval is None or refresh_interval <= 0:
        return _mix_qwen_features(
            sample,
            features,
            planner_config=planner_config,
            reuse_classes=reuse_classes,
            max_age=max_age,
            sticky_window=sticky_window,
            halo_veto_config=halo_veto_config,
        )

    image_grid_thw = np.array(sample.extra_kwargs["image_grid_thw"].tolist(), dtype=np.int64)
    counts = qwen_merged_token_counts(image_grid_thw, spatial_merge_size=QWEN_SPATIAL_MERGE)
    if len(counts) != len(sample.frames):
        raise ValueError("frame count and Qwen grid count mismatch")

    dense_segments: list[mx.array] = []
    offset = 0
    for count in counts:
        dense_segments.append(features[offset : offset + count])
        offset += count

    mixed_segments = [dense_segments[0]]
    ages = np.zeros(dense_segments[0].shape[0], dtype=np.int32)
    raw_reused_ratios: list[float] = []
    active_reused_ratios: list[float] = []
    for frame_index in range(1, len(sample.frames)):
        if frame_index % refresh_interval == 0:
            mixed_segments.append(dense_segments[frame_index])
            ages = np.zeros(dense_segments[frame_index].shape[0], dtype=np.int32)
            raw_reused_ratios.append(0.0)
            active_reused_ratios.append(0.0)
            continue

        previous = np.array(sample.frames[frame_index - 1], dtype=np.uint8)
        current = np.array(sample.frames[frame_index], dtype=np.uint8)
        classification = classify_blocks_with_planner(
            previous,
            current,
            block_size=QWEN_BLOCK_SIZE,
            config=planner_config,
        )
        if halo_veto_config is not None:
            block_scores = block_statistic_values(
                previous,
                current,
                block_size=QWEN_BLOCK_SIZE,
                config=planner_config,
            )
            classification = apply_neighbor_halo_veto(
                classification,
                block_scores,
                config=halo_veto_config,
            )
        reuse_mask = flattened_reuse_mask(classification, reuse_classes=reuse_classes)
        if reuse_mask.size != dense_segments[frame_index].shape[0]:
            raise ValueError(
                "classification/token mismatch: "
                f"mask={reuse_mask.size}, tokens={dense_segments[frame_index].shape[0]}"
            )
        allowed_mask, ages = _apply_age_gate(reuse_mask, ages, max_age=max_age)
        previous_active = active_region_block_mask(
            sample.frames[frame_index - 1].size,
            sample.active_boxes[frame_index - 1],
            block_size=QWEN_BLOCK_SIZE,
        )
        current_active = active_region_block_mask(
            sample.frames[frame_index].size,
            sample.active_boxes[frame_index],
            block_size=QWEN_BLOCK_SIZE,
        )
        active_mask = previous_active & current_active
        if active_mask.size != reuse_mask.size:
            raise ValueError(
                f"active-region/token mismatch: mask={active_mask.size}, tokens={reuse_mask.size}"
            )
        mixed_segments.append(
            mx.where(
                mx.array(allowed_mask[:, None]),
                mixed_segments[-1],
                dense_segments[frame_index],
            )
        )
        raw_reused_ratios.append(float(allowed_mask.mean()))
        active_reused_ratios.append(_masked_mean(allowed_mask.astype(np.float32), active_mask))

    mixed = mx.concatenate(mixed_segments, axis=0)
    mx.eval(mixed)
    return mixed, raw_reused_ratios, active_reused_ratios


def _generate_response(
    model: Any,
    processor: Any,
    sample: PreparedSample,
    *,
    cached_features: mx.array | None,
    max_tokens: int,
) -> dict[str, Any]:
    mx.random.seed(42)
    kwargs = dict(sample.extra_kwargs)
    if cached_features is not None:
        kwargs["cached_image_features"] = cached_features
    start_ns = time.perf_counter_ns()
    response = generate(
        model,
        processor,
        "",
        input_ids=sample.input_ids,
        pixel_values=sample.pixel_values,
        mask=sample.mask,
        max_tokens=max_tokens,
        temperature=0.0,
        **kwargs,
    )
    elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000
    return {
        "text": response.text,
        "elapsed_ms": elapsed_ms,
        "prompt_tokens": response.prompt_tokens,
        "generation_tokens": response.generation_tokens,
        "peak_memory_gb": response.peak_memory,
    }


def _letter_token_ids(processor: Any, candidate_letters: list[str]) -> list[int]:
    """Return the single-token id for each candidate letter.

    Raises if a letter tokenizes to more than one token under the active
    tokenizer. Whitespace variants are tried when the bare letter doesn't
    encode cleanly.
    """
    tokenizer = processor.tokenizer if hasattr(processor, "tokenizer") else processor
    ids: list[int] = []
    for letter in candidate_letters:
        candidates = [letter, f" {letter}"]
        resolved: int | None = None
        for variant in candidates:
            tokens = tokenizer.encode(variant, add_special_tokens=False)
            if len(tokens) == 1:
                resolved = int(tokens[0])
                break
        if resolved is None:
            raise ValueError(
                f"letter {letter!r} does not tokenize to a single token on this tokenizer"
            )
        ids.append(resolved)
    return ids


def _option_logprobs(
    model: Any,
    processor: Any,
    sample: PreparedSample,
    *,
    candidate_letters: list[str],
    cached_features: mx.array | None,
) -> dict[str, Any]:
    """Compute per-letter log-probabilities at the answer position.

    Runs a single prefill of the model, extracts logits at the final prompt
    position, applies log-softmax, and reads back one log-probability per
    candidate letter. Returns the full per-letter map plus:
      - argmax_letter: letter with the highest logprob
      - top_margin: logprob(argmax) - logprob(second-highest)
      - correct_letter / correct_logprob: optional, filled by caller
    """
    kwargs = dict(sample.extra_kwargs)
    if cached_features is not None:
        kwargs["cached_image_features"] = cached_features
    outputs = model(sample.input_ids, sample.pixel_values, mask=sample.mask, **kwargs)
    logits = outputs.logits[0, -1, :]
    logprobs = logits - mx.logsumexp(logits, keepdims=True)
    mx.eval(logprobs)
    logprobs_np = np.array(logprobs)

    letter_ids = _letter_token_ids(processor, candidate_letters)
    per_letter = {
        letter: float(logprobs_np[token_id])
        for letter, token_id in zip(candidate_letters, letter_ids, strict=True)
    }
    sorted_letters = sorted(per_letter.items(), key=lambda kv: kv[1], reverse=True)
    argmax_letter, top_logprob = sorted_letters[0]
    top_margin = sorted_letters[0][1] - sorted_letters[1][1] if len(sorted_letters) >= 2 else 0.0
    return {
        "per_letter_logprob": per_letter,
        "argmax_letter": argmax_letter,
        "argmax_logprob": top_logprob,
        "top_margin": float(top_margin),
    }


def _clear_runtime_state() -> None:
    gc.collect()
    mx.clear_cache()


def _run_chunk(
    item_ids: list[str],
    *,
    benchmark: Literal["tomato", "mvbench", "videomme"],
    per_group: int,
    groups: list[str] | None,
    manifest_path: Path | None,
    model_path: Path,
    frame_count: int,
    max_tokens: int,
    cache_mode: Literal["default", "identity"],
    refresh_interval: int | None,
    planner_config: PlannerConfig,
    reuse_classes: tuple[BlockClass, ...],
    max_age: int | None,
    sticky_window: int | None,
    use_feature_replay: bool,
    feature_cache_dir: Path,
    allow_dirty: bool,
    log_option_logprobs: bool = False,
    halo_veto_config: NeighborHaloVetoConfig | None = None,
) -> list[dict[str, Any]]:
    _ensure_clean_git_tree(allow_dirty=allow_dirty)
    selected_manifest = _load_manifest(manifest_path) if manifest_path is not None else None
    if selected_manifest is not None and selected_manifest.benchmark != benchmark:
        raise ValueError(
            f"manifest benchmark {selected_manifest.benchmark!r} does not match "
            f"requested benchmark {benchmark!r}"
        )
    registry_source = (
        _load_items_by_id(benchmark, item_ids=selected_manifest.item_ids)
        if selected_manifest is not None
        else _load_items(benchmark, per_group=per_group, groups=groups)
    )
    registry = {item.item_id: item for item in registry_source}
    selected_items = [registry[item_id] for item_id in item_ids]
    model, processor = _load_model(model_path)
    model_content_hash = model_content_sha256(model_path)
    results: list[dict[str, Any]] = []
    for item in selected_items:
        sample = _prepare_sample(model, processor, item, frame_count=frame_count)
        features, feature_cache_hit = _compute_cached_features_with_replay(
            model,
            sample,
            model_path=model_path,
            model_content_hash=model_content_hash,
            use_feature_replay=use_feature_replay,
            feature_cache_dir=feature_cache_dir,
        )
        cached_features, raw_reused_ratios, active_reused_ratios = _select_cached_features(
            sample,
            features,
            cache_mode=cache_mode,
            refresh_interval=refresh_interval,
            planner_config=planner_config,
            reuse_classes=reuse_classes,
            max_age=max_age,
            sticky_window=sticky_window,
            halo_veto_config=halo_veto_config,
        )
        dense = _generate_response(
            model,
            processor,
            sample,
            cached_features=None,
            max_tokens=max_tokens,
        )
        cached = _generate_response(
            model,
            processor,
            sample,
            cached_features=cached_features,
            max_tokens=max_tokens,
        )
        dense_choice = extract_choice(str(dense["text"]), item.candidates)
        cached_choice = extract_choice(str(cached["text"]), item.candidates)
        if log_option_logprobs:
            candidate_letters = [chr(ord("A") + index) for index in range(len(item.candidates))]
            try:
                dense_margin = _option_logprobs(
                    model,
                    processor,
                    sample,
                    candidate_letters=candidate_letters,
                    cached_features=None,
                )
                cached_margin = _option_logprobs(
                    model,
                    processor,
                    sample,
                    candidate_letters=candidate_letters,
                    cached_features=cached_features,
                )
                correct_letter = candidate_letters[item.answer_index]
                dense_margin["correct_letter"] = correct_letter
                dense_margin["correct_logprob"] = dense_margin["per_letter_logprob"][correct_letter]
                cached_margin["correct_letter"] = correct_letter
                cached_margin["correct_logprob"] = cached_margin["per_letter_logprob"][
                    correct_letter
                ]
                dense["option_logprobs"] = dense_margin
                cached["option_logprobs"] = cached_margin
            except (ValueError, IndexError, KeyError) as exc:
                dense["option_logprobs_error"] = str(exc)
                cached["option_logprobs_error"] = str(exc)
        results.append(
            {
                "item_id": item.item_id,
                "benchmark": item.benchmark,
                "group": item.group,
                "video_path": str(item.video_path),
                "question": item.question,
                "answer_index": item.answer_index,
                "dense": {
                    **dense,
                    "choice_index": dense_choice,
                    "correct": (
                        dense_choice == item.answer_index if dense_choice is not None else False
                    ),
                    "parse_failure": dense_choice is None,
                },
                "cached": {
                    **cached,
                    "choice_index": cached_choice,
                    "correct": (
                        cached_choice == item.answer_index if cached_choice is not None else False
                    ),
                    "parse_failure": cached_choice is None,
                },
                "match": (
                    dense_choice == cached_choice
                    if dense_choice is not None and cached_choice is not None
                    else False
                ),
                "cache_mode": cache_mode,
                "refresh_interval": refresh_interval,
                "feature_cache_hit": feature_cache_hit,
                "reuse_ratio_mean": _mean_or_none(active_reused_ratios),
                "reuse_ratio_mean_active": _mean_or_none(active_reused_ratios),
                "reuse_ratio_mean_raw": _mean_or_none(raw_reused_ratios),
                "frame_count": frame_count,
                "thresholds": {
                    "static": planner_config.static_threshold,
                    "shifted": planner_config.shifted_threshold,
                },
                "planner": _planner_payload(
                    planner_config,
                    reuse_classes=reuse_classes,
                    max_age=max_age,
                    sticky_window=sticky_window,
                    halo_veto=halo_veto_config,
                ),
                "selection_mode": "manifest" if selected_manifest is not None else "per_group",
                "manifest_path": str(manifest_path) if manifest_path is not None else None,
            }
        )
        _clear_runtime_state()
    return results


def _chunked(items: list[str], size: int) -> list[list[str]]:
    if size <= 0:
        raise ValueError("chunk size must be positive")
    return [items[index : index + size] for index in range(0, len(items), size)]


def _read_completed_ids(output_path: Path) -> set[str]:
    if not output_path.exists():
        return set()
    completed: set[str] = set()
    with output_path.open() as handle:
        for line in handle:
            if not line.strip():
                continue
            completed.add(json.loads(line)["item_id"])
    return completed


def _append_results(output_path: Path, payload: list[dict[str, Any]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a") as handle:
        for item in payload:
            handle.write(json.dumps(item, sort_keys=True) + "\n")


def _write_summary(
    summary_path: Path,
    *,
    benchmark: Literal["tomato", "mvbench", "videomme"],
    requested_ids: list[str],
    output_path: Path,
    environment: dict[str, Any],
    stopped_early: bool,
    groups: list[str] | None,
    per_group: int,
    frame_count: int,
    cache_mode: Literal["default", "identity"],
    refresh_interval: int | None,
    manifest_path: Path | None,
    planner_config: PlannerConfig,
    reuse_classes: tuple[BlockClass, ...],
    max_age: int | None,
    sticky_window: int | None,
    use_feature_replay: bool,
    feature_cache_dir: Path,
    halo_veto_config: NeighborHaloVetoConfig | None = None,
) -> None:
    completed_items: list[dict[str, Any]] = []
    if output_path.exists():
        with output_path.open() as handle:
            for line in handle:
                if line.strip():
                    completed_items.append(json.loads(line))
    completed_ids = [item["item_id"] for item in completed_items]
    dense_correct = sum(bool(item["dense"]["correct"]) for item in completed_items)
    cached_correct = sum(bool(item["cached"]["correct"]) for item in completed_items)
    matched = sum(bool(item["match"]) for item in completed_items)
    parse_failures = sum(bool(item["cached"]["parse_failure"]) for item in completed_items)
    feature_cache_hits = sum(bool(item.get("feature_cache_hit")) for item in completed_items)
    reuse_ratio_values = [
        float(item["reuse_ratio_mean"])
        for item in completed_items
        if item["reuse_ratio_mean"] is not None
    ]
    reuse_ratio_active_values = [
        float(item["reuse_ratio_mean_active"])
        for item in completed_items
        if item["reuse_ratio_mean_active"] is not None
    ]
    reuse_ratio_raw_values = [
        float(item["reuse_ratio_mean_raw"])
        for item in completed_items
        if item["reuse_ratio_mean_raw"] is not None
    ]
    summary = {
        "benchmark": benchmark,
        "environment": environment,
        "selection": {
            "mode": "manifest" if manifest_path is not None else "per_group",
            "manifest_path": str(manifest_path) if manifest_path is not None else None,
            "groups": groups,
            "per_group": per_group,
        },
        "frame_count": frame_count,
        "cache_mode": cache_mode,
        "refresh_interval": refresh_interval,
        "feature_replay_enabled": use_feature_replay,
        "feature_cache_dir": str(feature_cache_dir),
        "feature_cache_hits": feature_cache_hits,
        "feature_cache_misses": len(completed_items) - feature_cache_hits,
        "planner": _planner_payload(
            planner_config,
            reuse_classes=reuse_classes,
            max_age=max_age,
            sticky_window=sticky_window,
            halo_veto=halo_veto_config,
        ),
        "requested_item_ids": requested_ids,
        "completed_item_ids": completed_ids,
        "remaining_item_ids": [
            item_id for item_id in requested_ids if item_id not in set(completed_ids)
        ],
        "stopped_early": stopped_early,
        "dense_accuracy": dense_correct / len(completed_items) if completed_items else 0.0,
        "cached_accuracy": cached_correct / len(completed_items) if completed_items else 0.0,
        "agreement": matched / len(completed_items) if completed_items else 0.0,
        "cached_parse_failures": parse_failures,
        "reuse_ratio_mean": _mean_or_none(reuse_ratio_values),
        "reuse_ratio_mean_active": _mean_or_none(reuse_ratio_active_values),
        "reuse_ratio_mean_raw": _mean_or_none(reuse_ratio_raw_values),
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")


def _stop_requested(control: RunControl | None) -> bool:
    return bool(control and control.stop_file is not None and control.stop_file.exists())


def run_benchmark(
    *,
    benchmark: Literal["tomato", "mvbench", "videomme"],
    per_group: int,
    groups: list[str] | None,
    manifest_path: Path | None,
    chunk_size: int,
    model_path: Path,
    frame_count: int,
    max_tokens: int,
    output_path: Path,
    control: RunControl | None,
    cache_mode: Literal["default", "identity"],
    refresh_interval: int | None,
    planner_config: PlannerConfig,
    reuse_classes: tuple[BlockClass, ...],
    max_age: int | None,
    sticky_window: int | None,
    use_feature_replay: bool,
    feature_cache_dir: Path,
    allow_dirty: bool,
    log_option_logprobs: bool = False,
    halo_veto_config: NeighborHaloVetoConfig | None = None,
) -> None:
    _ensure_clean_git_tree(allow_dirty=allow_dirty)
    environment = _environment_record(model_path)
    selected_manifest = _load_manifest(manifest_path) if manifest_path is not None else None
    if selected_manifest is not None and selected_manifest.benchmark != benchmark:
        raise ValueError(
            f"manifest benchmark {selected_manifest.benchmark!r} does not match "
            f"requested benchmark {benchmark!r}"
        )
    registry = (
        _load_items_by_id(benchmark, item_ids=selected_manifest.item_ids)
        if selected_manifest is not None
        else _load_items(benchmark, per_group=per_group, groups=groups)
    )
    requested_ids = [item.item_id for item in registry]
    completed_ids = _read_completed_ids(output_path)
    pending_ids = [item_id for item_id in requested_ids if item_id not in completed_ids]
    stopped_early = False

    for chunk in _chunked(pending_ids, chunk_size):
        if _stop_requested(control):
            stopped_early = True
            break
        command = [
            sys.executable,
            __file__,
            "run-chunk",
            "--benchmark",
            benchmark,
            "--model-path",
            str(model_path),
            "--frame-count",
            str(frame_count),
            "--max-tokens",
            str(max_tokens),
            "--cache-mode",
            cache_mode,
            "--refresh-interval",
            str(refresh_interval) if refresh_interval is not None else "0",
            "--statistic",
            planner_config.statistic.value,
            "--static-threshold",
            str(planner_config.static_threshold),
            "--shifted-threshold",
            str(planner_config.shifted_threshold),
            "--pixel-change-threshold",
            str(planner_config.pixel_change_threshold),
            "--top-k",
            str(planner_config.top_k),
            "--reuse-classes",
            ",".join(block_class.name.lower() for block_class in reuse_classes),
            "--item-id",
            *chunk,
        ]
        if max_age is not None:
            command.extend(["--max-age", str(max_age)])
        if sticky_window is not None:
            command.extend(["--sticky-window", str(sticky_window)])
        if halo_veto_config is not None:
            command.extend(
                [
                    "--halo-veto-percentile",
                    str(halo_veto_config.percentile),
                    "--halo-veto-neighborhood",
                    str(halo_veto_config.neighborhood),
                ]
            )
        # The parent run already validated the starting repo state before it
        # writes tracked artifacts, so child chunks should inherit that
        # provenance instead of rejecting the parent's own output files.
        command.append("--allow-dirty")
        if not use_feature_replay:
            command.append("--no-feature-replay")
        if log_option_logprobs:
            command.append("--log-option-logprobs")
        command.extend(["--feature-cache-dir", str(feature_cache_dir)])
        if manifest_path is not None:
            command.extend(["--manifest", str(manifest_path)])
        else:
            command.extend(["--per-group", str(per_group)])
        if groups:
            command.extend(["--groups", ",".join(groups)])
        completed = subprocess.run(command, check=True, capture_output=True, text=True)
        _append_results(output_path, json.loads(completed.stdout))
        if control and control.summary_path is not None:
            _write_summary(
                control.summary_path,
                benchmark=benchmark,
                requested_ids=requested_ids,
                output_path=output_path,
                environment=environment,
                stopped_early=False,
                groups=groups,
                per_group=per_group,
                frame_count=frame_count,
                cache_mode=cache_mode,
                refresh_interval=refresh_interval,
                manifest_path=manifest_path,
                planner_config=planner_config,
                reuse_classes=reuse_classes,
                max_age=max_age,
                sticky_window=sticky_window,
                use_feature_replay=use_feature_replay,
                feature_cache_dir=feature_cache_dir,
                halo_veto_config=halo_veto_config,
            )

    if _stop_requested(control):
        stopped_early = True
    if control and control.summary_path is not None:
        _write_summary(
            control.summary_path,
            benchmark=benchmark,
            requested_ids=requested_ids,
            output_path=output_path,
            environment=environment,
            stopped_early=stopped_early,
            groups=groups,
            per_group=per_group,
            frame_count=frame_count,
            cache_mode=cache_mode,
            refresh_interval=refresh_interval,
            manifest_path=manifest_path,
            planner_config=planner_config,
            reuse_classes=reuse_classes,
            max_age=max_age,
            sticky_window=sticky_window,
            use_feature_replay=use_feature_replay,
            feature_cache_dir=feature_cache_dir,
            halo_veto_config=halo_veto_config,
        )


def _maybe_halo_veto(
    percentile: float | None, neighborhood: int | None
) -> NeighborHaloVetoConfig | None:
    if percentile is None and neighborhood is None:
        return None
    if percentile is None or neighborhood is None:
        raise ValueError(
            "neighbor-halo-veto requires both --halo-veto-percentile and "
            "--halo-veto-neighborhood (or neither)"
        )
    return NeighborHaloVetoConfig(percentile=percentile, neighborhood=neighborhood)


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--benchmark", choices=["tomato", "mvbench", "videomme"], required=True)
    run_parser.add_argument("--per-group", type=int, default=2)
    run_parser.add_argument("--groups", default=None)
    run_parser.add_argument("--manifest", type=Path, default=None)
    run_parser.add_argument("--chunk-size", type=int, default=1)
    run_parser.add_argument("--frame-count", type=int, default=8)
    run_parser.add_argument("--max-tokens", type=int, default=32)
    run_parser.add_argument("--cache-mode", choices=["default", "identity"], default="default")
    run_parser.add_argument("--refresh-interval", type=int, default=0)
    run_parser.add_argument(
        "--statistic",
        choices=[statistic.value for statistic in BlockStatistic],
        default=DEFAULT_PLANNER.statistic.value,
    )
    run_parser.add_argument(
        "--static-threshold",
        type=float,
        default=DEFAULT_PLANNER.static_threshold,
    )
    run_parser.add_argument(
        "--shifted-threshold",
        type=float,
        default=DEFAULT_PLANNER.shifted_threshold,
    )
    run_parser.add_argument(
        "--pixel-change-threshold",
        type=float,
        default=DEFAULT_PLANNER.pixel_change_threshold,
    )
    run_parser.add_argument("--top-k", type=int, default=DEFAULT_PLANNER.top_k)
    run_parser.add_argument("--reuse-classes", default="static,shifted")
    run_parser.add_argument("--max-age", type=int, default=None)
    run_parser.add_argument(
        "--sticky-window",
        type=int,
        default=None,
        help=(
            "CodecSight-style sticky-dynamic: once a block is marked "
            "non-reusable, keep it non-reusable for the rest of the window "
            "of N frames. Reset at frame_index %% N == 0."
        ),
    )
    run_parser.add_argument(
        "--halo-veto-percentile",
        type=float,
        default=None,
        help=(
            "Phase 1.37B Planner 2.1A neighbor-halo veto: promote STATIC -> "
            "NOVEL if any *parent-block neighbor's* statistic score exceeds "
            "this quantile of the current frame-pair score distribution. "
            "Requires --halo-veto-neighborhood. (Not the within-block "
            "child-veto of phase 1.37, which is unimplemented.)"
        ),
    )
    run_parser.add_argument(
        "--halo-veto-neighborhood",
        type=int,
        default=None,
        help="Neighbor-halo radius in parent-block units (1 = 3x3 window, 2 = 5x5).",
    )
    run_parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL_PATH)
    run_parser.add_argument("--output-path", type=Path, default=DEFAULT_OUTPUT_PATH)
    run_parser.add_argument("--summary-path", type=Path, default=DEFAULT_SUMMARY_PATH)
    run_parser.add_argument("--stop-file", type=Path, default=None)
    run_parser.add_argument("--feature-cache-dir", type=Path, default=DEFAULT_FEATURE_CACHE_DIR)
    run_parser.add_argument("--no-feature-replay", action="store_true")
    run_parser.add_argument(
        "--log-option-logprobs",
        action="store_true",
        help="Record per-option log-probabilities and top-2 margins on every item.",
    )
    run_parser.add_argument("--allow-dirty", action="store_true")

    chunk_parser = subparsers.add_parser("run-chunk")
    chunk_parser.add_argument(
        "--benchmark", choices=["tomato", "mvbench", "videomme"], required=True
    )
    chunk_parser.add_argument("--per-group", type=int, default=0)
    chunk_parser.add_argument("--groups", default=None)
    chunk_parser.add_argument("--manifest", type=Path, default=None)
    chunk_parser.add_argument("--frame-count", type=int, required=True)
    chunk_parser.add_argument("--max-tokens", type=int, required=True)
    chunk_parser.add_argument("--cache-mode", choices=["default", "identity"], required=True)
    chunk_parser.add_argument("--refresh-interval", type=int, required=True)
    chunk_parser.add_argument(
        "--statistic",
        choices=[statistic.value for statistic in BlockStatistic],
        required=True,
    )
    chunk_parser.add_argument("--static-threshold", type=float, required=True)
    chunk_parser.add_argument("--shifted-threshold", type=float, required=True)
    chunk_parser.add_argument("--pixel-change-threshold", type=float, required=True)
    chunk_parser.add_argument("--top-k", type=int, required=True)
    chunk_parser.add_argument("--reuse-classes", required=True)
    chunk_parser.add_argument("--max-age", type=int, default=None)
    chunk_parser.add_argument("--sticky-window", type=int, default=None)
    chunk_parser.add_argument("--halo-veto-percentile", type=float, default=None)
    chunk_parser.add_argument("--halo-veto-neighborhood", type=int, default=None)
    chunk_parser.add_argument("--model-path", type=Path, required=True)
    chunk_parser.add_argument("--item-id", nargs="+", required=True)
    chunk_parser.add_argument("--feature-cache-dir", type=Path, default=DEFAULT_FEATURE_CACHE_DIR)
    chunk_parser.add_argument("--no-feature-replay", action="store_true")
    chunk_parser.add_argument("--log-option-logprobs", action="store_true")
    chunk_parser.add_argument("--allow-dirty", action="store_true")

    args = parser.parse_args()
    planner_config = PlannerConfig(
        statistic=BlockStatistic(args.statistic),
        static_threshold=args.static_threshold,
        shifted_threshold=args.shifted_threshold,
        pixel_change_threshold=args.pixel_change_threshold,
        top_k=args.top_k,
    )
    reuse_classes = _parse_reuse_classes(args.reuse_classes)
    max_age = _validate_max_age(args.max_age)
    sticky_window = args.sticky_window if args.sticky_window and args.sticky_window > 0 else None
    halo_veto_config = _maybe_halo_veto(args.halo_veto_percentile, args.halo_veto_neighborhood)
    if args.command == "run-chunk":
        groups = args.groups.split(",") if args.groups else None
        print(
            json.dumps(
                _run_chunk(
                    args.item_id,
                    benchmark=cast(Literal["tomato", "mvbench", "videomme"], args.benchmark),
                    per_group=args.per_group,
                    groups=groups,
                    manifest_path=args.manifest,
                    model_path=args.model_path,
                    frame_count=args.frame_count,
                    max_tokens=args.max_tokens,
                    cache_mode=cast(Literal["default", "identity"], args.cache_mode),
                    refresh_interval=args.refresh_interval if args.refresh_interval > 0 else None,
                    planner_config=planner_config,
                    reuse_classes=reuse_classes,
                    max_age=max_age,
                    sticky_window=sticky_window,
                    use_feature_replay=not bool(args.no_feature_replay),
                    feature_cache_dir=args.feature_cache_dir,
                    allow_dirty=bool(args.allow_dirty),
                    log_option_logprobs=bool(args.log_option_logprobs),
                    halo_veto_config=halo_veto_config,
                ),
                sort_keys=True,
            )
        )
        return

    groups = args.groups.split(",") if args.groups else None
    control = RunControl(stop_file=args.stop_file, summary_path=args.summary_path)
    run_benchmark(
        benchmark=cast(Literal["tomato", "mvbench", "videomme"], args.benchmark),
        per_group=args.per_group,
        groups=groups,
        manifest_path=args.manifest,
        chunk_size=args.chunk_size,
        model_path=args.model_path,
        frame_count=args.frame_count,
        max_tokens=args.max_tokens,
        output_path=args.output_path,
        control=control,
        cache_mode=cast(Literal["default", "identity"], args.cache_mode),
        refresh_interval=args.refresh_interval if args.refresh_interval > 0 else None,
        planner_config=planner_config,
        reuse_classes=reuse_classes,
        max_age=max_age,
        sticky_window=sticky_window,
        use_feature_replay=not bool(args.no_feature_replay),
        feature_cache_dir=args.feature_cache_dir,
        allow_dirty=bool(args.allow_dirty),
        log_option_logprobs=bool(args.log_option_logprobs),
        halo_veto_config=halo_veto_config,
    )


if __name__ == "__main__":
    main()
