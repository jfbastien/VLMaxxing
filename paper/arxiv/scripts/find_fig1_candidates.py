#!/usr/bin/env python3
"""Mine real-video windows for Figure 1 review.

This is an exploratory script. It consumes local raw videos when available and
emits checked derivative review assets, but it is not part of the production
paper sync path.
"""

from __future__ import annotations

import argparse
import contextlib
import csv
import hashlib
import json
import os
import sys
from collections import Counter
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, JpegImagePlugin

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

os.environ.setdefault("MPLCONFIGDIR", str(REPO_ROOT / ".tmp" / "matplotlib"))

import av  # noqa: E402

assert JpegImagePlugin is not None

from codec_through.codec._pyav_util import robust_reformat  # noqa: E402
from codec_through.temporal import (  # noqa: E402
    BlockClass,
    BlockStatistic,
    PlannerConfig,
    block_statistic_values,
    classify_blocks_with_planner,
)
from codec_through.track_a import active_region_block_mask  # noqa: E402

GENERATED = REPO_ROOT / "paper" / "arxiv" / "generated"
OUT_DIR = GENERATED / "figures" / "fig1_candidates"
ASSET_DIR = OUT_DIR / "candidate_assets"

BENCHMARK_FRAME_SIZE = 560
QWEN_BLOCK_SIZE = 28
DISPLAY_FRAMES = 4
THUMB_WIDTH = 280
EXACT_PIXEL_PLANNER = PlannerConfig(
    statistic=BlockStatistic.MAX_ABS,
    static_threshold=8.0,
    shifted_threshold=32.0,
)
TRACK_A_MAX_AGE = 4
REUSE_CLASSES = (BlockClass.STATIC, BlockClass.SHIFTED)
RECOMMENDED_SOURCE_JSONLS = (
    REPO_ROOT
    / "research"
    / "experiments"
    / "2026"
    / "artifacts"
    / "phase1_29B_dev30_artifact_20260424"
    / "artifact_results.jsonl",
    REPO_ROOT
    / "research"
    / "experiments"
    / "2026"
    / "artifacts"
    / "phase1_29B_dev30_duration_20260423"
    / "results.jsonl",
    REPO_ROOT
    / "research"
    / "experiments"
    / "2026"
    / "artifacts"
    / "phase1_29B_short_n20_calibration_20260423"
    / "artifact_results.jsonl",
    REPO_ROOT
    / "research"
    / "experiments"
    / "2026"
    / "artifacts"
    / "phase1_29B_short_holdout_20260423"
    / "results.jsonl",
)


@dataclass(frozen=True)
class VideoSource:
    video_id: str
    item_id: str
    video_path: Path
    benchmark: str
    split: str | None
    question: str | None
    source_jsonl: Path


@dataclass(frozen=True)
class WindowMetrics:
    reuse_mean_active: float
    reuse_min_active: float
    novel_fraction_mean: float
    novel_fraction_max: float
    novel_fraction_std: float
    compactness_mean: float
    largest_component_fraction_mean: float
    component_count_mean: float
    highlighted_region_fraction: float
    cut_penalty: float
    brightness_mean: float
    contrast_mean: float
    dark_fraction_mean: float
    blur_penalty: float
    border_penalty: float
    text_overlay_penalty: float
    clutter_penalty: float
    color_entropy_mean: float
    graphic_card_penalty: float
    story_score: float


@dataclass(frozen=True)
class WindowRecord:
    candidate_id: str
    video_id: str
    item_id: str
    video_path_hint: str
    benchmark: str
    split: str | None
    question: str | None
    source_jsonl: str
    start_s: float
    end_s: float
    duration_s: float
    frame_times_s: list[float]
    window_length_s: float
    metrics: WindowMetrics
    passes_basic_filters: bool
    assets: dict[str, Any] | None = None


VISUALIZATION_POLICY = {
    "purpose": (
        "All candidate windows are rendered with the audited Qwen routing-budget "
        "visualization policy, regardless of which artifact supplied the video path."
    ),
    "statistic": EXACT_PIXEL_PLANNER.statistic.value,
    "static_threshold": EXACT_PIXEL_PLANNER.static_threshold,
    "shifted_threshold": EXACT_PIXEL_PLANNER.shifted_threshold,
    "reuse_classes": [value.name.lower() for value in REUSE_CLASSES],
    "fresh_classes": ["novel", "stale_by_age"],
    "max_age": TRACK_A_MAX_AGE,
    "active_region_only": True,
    "source_row_policy_hint": (
        "source_jsonl may come from older planner sweeps; do not treat it as the rendering policy."
    ),
}


def read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open() as handle:
        for line in handle:
            line = line.strip()
            if line:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue


def safe_rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def infer_video_id(item_id: str, video_path: Path, row: dict[str, Any]) -> str:
    raw_video_id = row.get("video_id")
    if isinstance(raw_video_id, str) and raw_video_id and raw_video_id not in {"egoschema"}:
        return raw_video_id
    if item_id.startswith("videomme:"):
        tail = item_id.removeprefix("videomme:")
        parts = tail.split(":")
        if len(parts) >= 2:
            return parts[1].split("-", 1)[0]
    return video_path.stem


def infer_benchmark(item_id: str, source_jsonl: Path) -> str:
    if item_id.startswith("videomme:"):
        return "videomme"
    path_text = str(source_jsonl).lower()
    for name in ("mvbench", "tomato", "egoschema", "videomme"):
        if name in path_text:
            return name
    return "unknown"


def parse_video_source_row(row: dict[str, Any], source_jsonl: Path) -> VideoSource | None:
    item_id = row.get("item_id") or row.get("sample_id") or row.get("id")
    raw_video_path = (
        row.get("video_path") or row.get("path") or row.get("video") or row.get("source_video")
    )
    if not isinstance(item_id, str) or not isinstance(raw_video_path, str):
        return None
    video_path = Path(raw_video_path)
    if not video_path.is_absolute():
        video_path = REPO_ROOT / video_path
    if not video_path.exists() or not video_path.is_file():
        return None
    benchmark = infer_benchmark(item_id, source_jsonl)
    video_id = infer_video_id(item_id, video_path, row)
    split = (
        row.get("split") or row.get("group") or row.get("duration") or row.get("duration_bucket")
    )
    question = row.get("question") or row.get("prompt")
    return VideoSource(
        video_id=str(video_id),
        item_id=item_id,
        video_path=video_path,
        benchmark=benchmark,
        split=str(split) if split is not None else None,
        question=str(question) if question is not None else None,
        source_jsonl=source_jsonl,
    )


def discover_video_sources(
    *,
    source_jsonls: tuple[Path, ...],
    max_jsonl_mb: float,
    exclude_video_ids: set[str],
) -> list[VideoSource]:
    if source_jsonls:
        candidate_jsonls = list(source_jsonls)
    else:
        roots = [
            REPO_ROOT / "research" / "experiments" / "2026" / "artifacts",
            REPO_ROOT / "research" / "benchmark_manifests",
            REPO_ROOT / "data",
        ]
        candidate_jsonls = []
        for root in roots:
            if root.exists():
                candidate_jsonls.extend(root.rglob("*.jsonl"))
    sources: dict[str, VideoSource] = {}
    for path in candidate_jsonls:
        if not path.exists():
            continue
        try:
            if path.stat().st_size > max_jsonl_mb * 1024 * 1024:
                continue
        except OSError:
            continue
        for row in read_jsonl(path):
            source = parse_video_source_row(row, path)
            if source is None or source.video_id in exclude_video_ids:
                continue
            key = str(source.video_path.resolve())
            sources.setdefault(key, source)

    def sort_key(source: VideoSource) -> tuple[int, int, str, str]:
        path_text = safe_rel(source.source_jsonl)
        source_priority = 0
        if "phase1_41" in path_text:
            source_priority = -2
        elif "phase1_29" in path_text:
            source_priority = -1
        duration_priority = {"short": 0, "medium": 1, "long": 2}.get(source.split or "", 3)
        return (source_priority, duration_priority, source.video_id, source.item_id)

    return sorted(sources.values(), key=sort_key)


def duration_seconds(video_path: Path) -> float:
    with av.open(str(video_path)) as container:
        stream = container.streams.video[0]
        if stream.duration is not None and stream.time_base is not None:
            return float(stream.duration * stream.time_base)
        if container.duration is not None:
            return float(container.duration / 1_000_000)
    raise ValueError(f"could not determine duration for {video_path}")


def decode_frames_at_times(video_path: Path, times: list[float]) -> list[Image.Image]:
    if not times:
        return []
    indexed_times = sorted((float(t), idx) for idx, t in enumerate(times))
    selected: list[Image.Image | None] = [None] * len(times)
    target_idx = 0
    last_image: Image.Image | None = None
    first_time = indexed_times[0][0]
    with av.open(str(video_path)) as container:
        stream = container.streams.video[0]
        with contextlib.suppress(Exception):
            container.seek(
                int(max(0.0, first_time - 0.35) * 1_000_000), any_frame=False, backward=True
            )
        for frame in container.decode(stream):
            ts = float(frame.time) if frame.time is not None else None
            if ts is None:
                continue
            last_image = Image.fromarray(robust_reformat(frame, format="rgb24"))
            while target_idx < len(indexed_times) and ts >= indexed_times[target_idx][0]:
                _, original_idx = indexed_times[target_idx]
                selected[original_idx] = last_image.copy()
                target_idx += 1
            if target_idx >= len(indexed_times):
                break
    if any(image is None for image in selected):
        if last_image is None:
            raise ValueError(f"no decodable frames for {video_path}")
        selected = [image if image is not None else last_image.copy() for image in selected]
    return [image for image in selected if image is not None]


def square_pad_frame(
    frame: Image.Image, *, size: int = BENCHMARK_FRAME_SIZE
) -> tuple[Image.Image, tuple[int, int, int, int]]:
    width, height = frame.size
    if width <= 0 or height <= 0:
        raise ValueError("frame dimensions must be positive")
    scale = min(size / width, size / height)
    resized = frame.resize((round(width * scale), round(height * scale)), Image.Resampling.BICUBIC)
    canvas = Image.new("RGB", (size, size), color=(0, 0, 0))
    offset_x = (size - resized.width) // 2
    offset_y = (size - resized.height) // 2
    canvas.paste(resized, (offset_x, offset_y))
    return canvas, (offset_x, offset_y, offset_x + resized.width, offset_y + resized.height)


def active_crop(padded: Image.Image, active_box: tuple[int, int, int, int]) -> Image.Image:
    return padded.crop(active_box)


def resize_width(image: Image.Image, width: int) -> Image.Image:
    scale = width / image.width
    return image.resize((width, max(1, round(image.height * scale))), Image.Resampling.LANCZOS)


def block_scores_and_classes(
    previous: Image.Image,
    current: Image.Image,
    previous_active_box: tuple[int, int, int, int],
    current_active_box: tuple[int, int, int, int],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    previous_arr = np.asarray(previous, dtype=np.uint8)
    current_arr = np.asarray(current, dtype=np.uint8)
    scores = block_statistic_values(
        previous_arr,
        current_arr,
        block_size=QWEN_BLOCK_SIZE,
        config=EXACT_PIXEL_PLANNER,
    )
    classes = classify_blocks_with_planner(
        previous_arr,
        current_arr,
        block_size=QWEN_BLOCK_SIZE,
        config=EXACT_PIXEL_PLANNER,
    )
    previous_active = active_region_block_mask(
        (BENCHMARK_FRAME_SIZE, BENCHMARK_FRAME_SIZE),
        previous_active_box,
        block_size=QWEN_BLOCK_SIZE,
    ).reshape(classes.shape)
    current_active = active_region_block_mask(
        (BENCHMARK_FRAME_SIZE, BENCHMARK_FRAME_SIZE),
        current_active_box,
        block_size=QWEN_BLOCK_SIZE,
    ).reshape(classes.shape)
    return scores, classes, previous_active & current_active


def connected_components(mask: np.ndarray) -> list[np.ndarray]:
    height, width = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    comps: list[np.ndarray] = []
    for y in range(height):
        for x in range(width):
            if not bool(mask[y, x]) or bool(seen[y, x]):
                continue
            stack = [(y, x)]
            seen[y, x] = True
            points: list[tuple[int, int]] = []
            while stack:
                cy, cx = stack.pop()
                points.append((cy, cx))
                for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                    if (
                        0 <= ny < height
                        and 0 <= nx < width
                        and bool(mask[ny, nx])
                        and not bool(seen[ny, nx])
                    ):
                        seen[ny, nx] = True
                        stack.append((ny, nx))
            comp = np.zeros_like(mask, dtype=bool)
            for py, px in points:
                comp[py, px] = True
            comps.append(comp)
    return comps


def dilate_mask(mask: np.ndarray, *, iterations: int) -> np.ndarray:
    out = mask.copy()
    for _ in range(iterations):
        padded = np.pad(out, 1, mode="constant")
        grown = np.zeros_like(out)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                grown |= padded[1 + dy : 1 + dy + out.shape[0], 1 + dx : 1 + dx + out.shape[1]]
        out = grown
    return out


def novelty_component_metrics(novel_mask: np.ndarray) -> tuple[float, float]:
    total = float(novel_mask.sum())
    if total <= 0:
        return 1.0, 0.0
    comps = connected_components(novel_mask)
    sizes = sorted((float(comp.sum()) for comp in comps), reverse=True)
    return sizes[0] / total, float(len(comps))


def merge_novel_blocks_to_regions(
    novel_mask: np.ndarray,
    *,
    max_regions: int = 2,
    min_blocks: int = 2,
    dilate_iters: int = 1,
) -> list[tuple[int, int, int, int]]:
    mask = dilate_mask(novel_mask, iterations=dilate_iters)
    comps = [comp for comp in connected_components(mask) if int(comp.sum()) >= min_blocks]
    comps = sorted(comps, key=lambda comp: int(comp.sum()), reverse=True)[:max_regions]
    boxes: list[tuple[int, int, int, int]] = []
    for comp in comps:
        ys, xs = np.where(comp)
        if len(xs) == 0:
            continue
        boxes.append((int(ys.min()), int(xs.min()), int(ys.max()) + 1, int(xs.max()) + 1))
    return boxes


def block_boxes_to_normalized_active_boxes(
    boxes: list[tuple[int, int, int, int]],
    active_box: tuple[int, int, int, int],
) -> list[tuple[float, float, float, float]]:
    left, top, right, bottom = active_box
    crop_w = right - left
    crop_h = bottom - top
    out: list[tuple[float, float, float, float]] = []
    for row0, col0, row1, col1 in boxes:
        px0 = col0 * QWEN_BLOCK_SIZE
        py0 = row0 * QWEN_BLOCK_SIZE
        px1 = col1 * QWEN_BLOCK_SIZE
        py1 = row1 * QWEN_BLOCK_SIZE
        ix0 = max(px0, left)
        iy0 = max(py0, top)
        ix1 = min(px1, right)
        iy1 = min(py1, bottom)
        if ix1 <= ix0 or iy1 <= iy0:
            continue
        out.append(
            (
                (ix0 - left) / crop_w,
                (iy0 - top) / crop_h,
                (ix1 - left) / crop_w,
                (iy1 - top) / crop_h,
            )
        )
    return out


def mask_to_normalized_boxes(
    mask: np.ndarray,
    active_box: tuple[int, int, int, int],
) -> list[tuple[float, float, float, float]]:
    boxes: list[tuple[int, int, int, int]] = []
    rows, cols = mask.shape
    for row in range(rows):
        for col in range(cols):
            if bool(mask[row, col]):
                boxes.append((row, col, row + 1, col + 1))
    return block_boxes_to_normalized_active_boxes(boxes, active_box)


def box_area(box: tuple[float, float, float, float]) -> float:
    x0, y0, x1, y1 = box
    return max(0.0, x1 - x0) * max(0.0, y1 - y0)


def content_stats(img: Image.Image) -> tuple[float, float, float]:
    arr = np.asarray(img.convert("L"), dtype=np.float32)
    return float(arr.mean()), float(arr.std()), float((arr < 18.0).mean())


def cut_penalty(prev: Image.Image, curr: Image.Image) -> float:
    a = np.asarray(prev.convert("RGB").resize((128, 72)), dtype=np.float32)
    b = np.asarray(curr.convert("RGB").resize((128, 72)), dtype=np.float32)
    diff = float(np.abs(a - b).mean())
    hist_pen = 0.0
    for channel in range(3):
        ha = np.histogram(a[..., channel], bins=16, range=(0, 255), density=True)[0]
        hb = np.histogram(b[..., channel], bins=16, range=(0, 255), density=True)[0]
        hist_pen += float(np.abs(ha - hb).sum())
    return diff + 30.0 * hist_pen


def text_overlay_penalty(img: Image.Image) -> float:
    arr = np.asarray(img.convert("L").resize((256, 144)), dtype=np.float32)
    bands = np.concatenate([arr[:24, :], arr[-24:, :]], axis=0)
    gx = np.abs(np.diff(bands, axis=1)).mean()
    gy = np.abs(np.diff(bands, axis=0)).mean()
    return float(gx + gy)


def border_penalty(img: Image.Image) -> float:
    arr = np.asarray(img.convert("L"), dtype=np.float32)
    h, w = arr.shape
    bands = [
        arr[: max(1, h // 12), :],
        arr[-max(1, h // 12) :, :],
        arr[:, : max(1, w // 12)],
        arr[:, -max(1, w // 12) :],
    ]
    penalty = 0.0
    for band in bands:
        if band.mean() < 12.0 or band.mean() > 242.0:
            penalty += 1.0
        if band.std() < 6.0:
            penalty += 0.5
    return penalty


def blur_penalty(img: Image.Image) -> float:
    arr = np.asarray(img.convert("L").resize((160, 90)), dtype=np.float32)
    gx = np.diff(arr, axis=1)
    gy = np.diff(arr, axis=0)
    sharpness = float(np.mean(gx * gx) + np.mean(gy * gy))
    return max(0.0, 40.0 - sharpness) / 40.0


def clutter_penalty(img: Image.Image) -> float:
    arr = np.asarray(img.convert("L").resize((160, 90)), dtype=np.float32)
    gx = np.abs(np.diff(arr, axis=1))
    gy = np.abs(np.diff(arr, axis=0))
    edge_density = float((gx > 24.0).mean() + (gy > 24.0).mean())
    return edge_density * 4.0


def color_entropy(img: Image.Image) -> float:
    arr = np.asarray(img.convert("RGB").resize((128, 72)), dtype=np.uint8)
    quantized = (arr // 32).reshape(-1, 3)
    _, counts = np.unique(quantized, axis=0, return_counts=True)
    p = counts / counts.sum()
    return float(-(p * np.log2(p)).sum())


def graphic_card_penalty(img: Image.Image) -> float:
    """Penalize title cards, centered logos, credits, and flat slide graphics."""

    entropy = color_entropy(img)
    arr = np.asarray(img.convert("L").resize((160, 90)), dtype=np.float32)
    center = arr[12:78, 18:142]
    gx = np.abs(np.diff(center, axis=1))
    gy = np.abs(np.diff(center, axis=0))
    center_edge_density = float((gx > 24.0).mean() + (gy > 24.0).mean())
    penalty = 0.0
    if entropy < 2.6:
        penalty += (2.6 - entropy) * 1.4
    if entropy < 3.0 and center_edge_density > 0.035:
        penalty += (center_edge_density - 0.035) * 10.0
    if entropy < 1.2:
        penalty += 1.2
    return float(penalty)


def score_window(metrics: WindowMetrics) -> float:
    score = 0.0
    score += 3.0 * metrics.reuse_mean_active
    score += 1.0 * metrics.reuse_min_active
    novelty = metrics.novel_fraction_mean
    if 0.03 <= novelty <= 0.20:
        score += 1.2
    elif novelty < 0.01:
        score -= 3.8
    elif novelty < 0.03:
        score -= 1.4
    else:
        score -= 4.0 * max(0.0, novelty - 0.20)
    score += 2.2 * metrics.largest_component_fraction_mean
    score -= 0.45 * metrics.component_count_mean
    # Merged component boxes are useful for contact sheets but can visually
    # overstate the amount of fresh evidence. Penalize large display boxes so
    # selected examples do not read as semantic localization or whole-frame
    # recomputation.
    score -= 5.5 * max(0.0, metrics.highlighted_region_fraction - 0.18)
    score -= 2.0 * max(0.0, metrics.highlighted_region_fraction - 0.30)
    score += 0.012 * metrics.contrast_mean
    score -= 1.8 * metrics.dark_fraction_mean
    score -= 1.2 * metrics.blur_penalty
    score -= 0.05 * metrics.cut_penalty
    score -= 0.20 * metrics.text_overlay_penalty
    score -= 0.80 * metrics.border_penalty
    score -= 0.60 * metrics.clutter_penalty
    score -= 1.40 * metrics.graphic_card_penalty
    return float(score)


def passes_basic_filters(metrics: WindowMetrics) -> bool:
    return (
        metrics.reuse_mean_active >= 0.35
        and metrics.novel_fraction_mean <= 0.55
        and metrics.cut_penalty <= 160.0
        and metrics.dark_fraction_mean <= 0.50
        and metrics.component_count_mean <= 16.0
        and metrics.graphic_card_penalty <= 2.20
        and metrics.novel_fraction_mean >= 0.012
    )


def compute_window_metrics(
    padded_frames: list[Image.Image],
    active_boxes: list[tuple[int, int, int, int]],
) -> WindowMetrics:
    reuse_ratios: list[float] = []
    novel_fracs: list[float] = []
    largest_fracs: list[float] = []
    component_counts: list[float] = []
    highlighted_areas: list[float] = []
    cut_scores: list[float] = []
    brightness: list[float] = []
    contrast: list[float] = []
    dark: list[float] = []
    blur: list[float] = []
    text_penalties: list[float] = []
    border_penalties: list[float] = []
    clutter_penalties: list[float] = []
    color_entropy_values: list[float] = []
    graphic_card_penalties: list[float] = []
    ages: np.ndarray | None = None

    for padded, active_box in zip(padded_frames, active_boxes, strict=True):
        crop = active_crop(padded, active_box)
        mean, std, dark_fraction = content_stats(crop)
        brightness.append(mean)
        contrast.append(std)
        dark.append(dark_fraction)
        blur.append(blur_penalty(crop))
        text_penalties.append(text_overlay_penalty(crop))
        border_penalties.append(border_penalty(crop))
        clutter_penalties.append(clutter_penalty(crop))
        color_entropy_values.append(color_entropy(crop))
        graphic_card_penalties.append(graphic_card_penalty(crop))

    for idx, (previous, current) in enumerate(
        zip(padded_frames[:-1], padded_frames[1:], strict=True)
    ):
        scores, classes, active = block_scores_and_classes(
            previous,
            current,
            active_boxes[idx],
            active_boxes[idx + 1],
        )
        del scores
        if not active.any():
            continue
        raw_reuse = np.isin(classes, [int(value) for value in REUSE_CLASSES])
        if ages is None:
            ages = np.zeros(raw_reuse.shape, dtype=np.int32)
        raw_novel = (classes == int(BlockClass.NOVEL)) & active
        stale = raw_reuse & active & (ages >= TRACK_A_MAX_AGE)
        reused = raw_reuse & active & ~stale
        fresh = raw_novel | stale
        ages = np.where(reused, ages + 1, 0).astype(np.int32)
        reuse_ratios.append(float(reused.sum() / active.sum()))
        novel_fracs.append(float(fresh.sum() / active.sum()))
        largest, count = novelty_component_metrics(fresh)
        largest_fracs.append(largest)
        component_counts.append(count)
        regions = merge_novel_blocks_to_regions(fresh, max_regions=2, min_blocks=2, dilate_iters=1)
        norm_regions = block_boxes_to_normalized_active_boxes(regions, active_boxes[idx + 1])
        highlighted_areas.append(float(sum(box_area(box) for box in norm_regions)))
        cut_scores.append(
            cut_penalty(
                active_crop(previous, active_boxes[idx]),
                active_crop(current, active_boxes[idx + 1]),
            )
        )

    if not reuse_ratios:
        reuse_ratios = [0.0]
        novel_fracs = [1.0]
        largest_fracs = [0.0]
        component_counts = [999.0]
        highlighted_areas = [1.0]
        cut_scores = [999.0]

    metrics = WindowMetrics(
        reuse_mean_active=float(np.mean(reuse_ratios)),
        reuse_min_active=float(np.min(reuse_ratios)),
        novel_fraction_mean=float(np.mean(novel_fracs)),
        novel_fraction_max=float(np.max(novel_fracs)),
        novel_fraction_std=float(np.std(novel_fracs)),
        compactness_mean=float(np.mean(largest_fracs)),
        largest_component_fraction_mean=float(np.mean(largest_fracs)),
        component_count_mean=float(np.mean(component_counts)),
        highlighted_region_fraction=float(np.mean(highlighted_areas)),
        cut_penalty=float(np.mean(cut_scores)),
        brightness_mean=float(np.mean(brightness)),
        contrast_mean=float(np.mean(contrast)),
        dark_fraction_mean=float(np.mean(dark)),
        blur_penalty=float(np.mean(blur)),
        border_penalty=float(np.mean(border_penalties)),
        text_overlay_penalty=float(np.mean(text_penalties)),
        clutter_penalty=float(np.mean(clutter_penalties)),
        color_entropy_mean=float(np.mean(color_entropy_values)),
        graphic_card_penalty=float(np.mean(graphic_card_penalties)),
        story_score=0.0,
    )
    return WindowMetrics(**{**asdict(metrics), "story_score": score_window(metrics)})


def enumerate_windows(
    duration_s: float,
    *,
    lengths_s: tuple[float, ...],
    max_windows_per_video: int,
) -> list[tuple[float, float]]:
    windows: list[tuple[float, float]] = []
    per_length = max(1, max_windows_per_video // max(1, len(lengths_s)))
    for length_s in lengths_s:
        if duration_s < length_s + 0.1:
            continue
        max_start = duration_s - length_s
        starts = (
            np.linspace(0.0, max_start, num=per_length)
            if per_length > 1
            else np.array([max_start / 2.0])
        )
        for start in starts:
            windows.append((float(start), float(start + length_s)))
    return windows


def candidate_id_for(source: VideoSource, start_s: float, end_s: float) -> str:
    key = f"{source.item_id}|{safe_rel(source.video_path)}|{start_s:.3f}|{end_s:.3f}"
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:8]
    video = "".join(ch if ch.isalnum() else "_" for ch in source.video_id)[:24]
    return f"{video}_{start_s:06.2f}_{end_s:06.2f}_{digest}".replace(".", "p")


def evaluate_window(
    source: VideoSource, start_s: float, end_s: float, duration_s: float
) -> WindowRecord | None:
    frame_times = [float(t) for t in np.linspace(start_s, end_s, num=DISPLAY_FRAMES)]
    try:
        frames = decode_frames_at_times(source.video_path, frame_times)
    except Exception:
        return None
    if len(frames) != DISPLAY_FRAMES:
        return None
    padded_frames: list[Image.Image] = []
    active_boxes: list[tuple[int, int, int, int]] = []
    for frame in frames:
        padded, active_box = square_pad_frame(frame)
        padded_frames.append(padded)
        active_boxes.append(active_box)
    metrics = compute_window_metrics(padded_frames, active_boxes)
    return WindowRecord(
        candidate_id=candidate_id_for(source, start_s, end_s),
        video_id=source.video_id,
        item_id=source.item_id,
        video_path_hint=safe_rel(source.video_path),
        benchmark=source.benchmark,
        split=source.split,
        question=source.question,
        source_jsonl=safe_rel(source.source_jsonl),
        start_s=start_s,
        end_s=end_s,
        duration_s=duration_s,
        frame_times_s=frame_times,
        window_length_s=end_s - start_s,
        metrics=metrics,
        passes_basic_filters=passes_basic_filters(metrics),
    )


def draw_overlay_pil(
    image: Image.Image,
    boxes: list[tuple[float, float, float, float]],
    *,
    fill_alpha: int,
    outline_alpha: int,
    width: int = 3,
) -> Image.Image:
    rgba = image.convert("RGBA")
    overlay = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    outline = (194, 65, 12, outline_alpha) if outline_alpha > 0 and width > 0 else None
    for x0, y0, x1, y1 in boxes:
        rect = (
            round(x0 * rgba.width),
            round(y0 * rgba.height),
            round(x1 * rgba.width),
            round(y1 * rgba.height),
        )
        draw.rectangle(rect, fill=(249, 115, 22, fill_alpha), outline=outline, width=max(1, width))
    return Image.alpha_composite(rgba, overlay).convert("RGB")


def transition_details(
    padded_frames: list[Image.Image],
    active_boxes: list[tuple[int, int, int, int]],
) -> list[dict[str, Any]]:
    details: list[dict[str, Any]] = []
    ages: np.ndarray | None = None
    for idx, (previous, current) in enumerate(
        zip(padded_frames[:-1], padded_frames[1:], strict=True)
    ):
        scores, classes, active = block_scores_and_classes(
            previous,
            current,
            active_boxes[idx],
            active_boxes[idx + 1],
        )
        del scores
        raw_reuse = np.isin(classes, [int(value) for value in REUSE_CLASSES])
        if ages is None:
            ages = np.zeros(raw_reuse.shape, dtype=np.int32)
        raw_novel = (classes == int(BlockClass.NOVEL)) & active
        stale = raw_reuse & active & (ages >= TRACK_A_MAX_AGE)
        reused = raw_reuse & active & ~stale
        fresh = raw_novel | stale
        ages = np.where(reused, ages + 1, 0).astype(np.int32)
        shifted = (classes == int(BlockClass.SHIFTED)) & active
        static = (classes == int(BlockClass.STATIC)) & active
        active_count = int(active.sum())
        reuse_ratio = float(reused.sum() / active_count) if active_count else 0.0
        regions = merge_novel_blocks_to_regions(fresh, max_regions=2, min_blocks=2, dilate_iters=1)
        merged_boxes = block_boxes_to_normalized_active_boxes(regions, active_boxes[idx + 1])
        fresh_fraction = float(fresh.sum() / active_count) if active_count else 0.0
        raw_novel_fraction = float(raw_novel.sum() / active_count) if active_count else 0.0
        stale_fraction = float(stale.sum() / active_count) if active_count else 0.0
        details.append(
            {
                "transition_index": idx + 1,
                "reuse_ratio_active": reuse_ratio,
                "fresh_fraction_active": fresh_fraction,
                "raw_novel_fraction_active": raw_novel_fraction,
                "stale_fraction_active": stale_fraction,
                # Back-compat alias for older review code. Prefer
                # fresh_fraction_active in publication-facing text.
                "novel_fraction_active": fresh_fraction,
                "highlight_boxes": merged_boxes,
                "highlight_area_fraction": float(sum(box_area(box) for box in merged_boxes)),
                "fresh_boxes": mask_to_normalized_boxes(fresh, active_boxes[idx + 1]),
                "raw_novel_boxes": mask_to_normalized_boxes(raw_novel, active_boxes[idx + 1]),
                "stale_boxes": mask_to_normalized_boxes(stale, active_boxes[idx + 1]),
                "novel_boxes": mask_to_normalized_boxes(raw_novel, active_boxes[idx + 1]),
                "shifted_boxes": mask_to_normalized_boxes(shifted, active_boxes[idx + 1]),
                "static_boxes": mask_to_normalized_boxes(static, active_boxes[idx + 1]),
            }
        )
    return details


def add_candidate_assets(record: WindowRecord, rank: int) -> WindowRecord:
    frames = decode_frames_at_times(REPO_ROOT / record.video_path_hint, record.frame_times_s)
    padded_frames: list[Image.Image] = []
    active_boxes: list[tuple[int, int, int, int]] = []
    for frame in frames:
        padded, active_box = square_pad_frame(frame)
        padded_frames.append(padded)
        active_boxes.append(active_box)
    details = transition_details(padded_frames, active_boxes)
    out_dir = ASSET_DIR / f"r{rank:02d}_{record.candidate_id}"
    out_dir.mkdir(parents=True, exist_ok=True)

    frame_paths: list[str] = []
    subtle_paths: list[str] = []
    readable_mask_paths: list[str] = []
    exact_paths: list[str] = []
    for idx, (padded, active_box) in enumerate(zip(padded_frames, active_boxes, strict=True)):
        crop = resize_width(active_crop(padded, active_box), THUMB_WIDTH)
        frame_path = out_dir / f"frame_{idx:02d}.png"
        crop.save(frame_path)
        frame_paths.append(safe_rel(frame_path))
        boxes = details[idx - 1]["highlight_boxes"] if idx > 0 else []
        subtle = draw_overlay_pil(crop, boxes, fill_alpha=24, outline_alpha=210, width=3)
        subtle_path = out_dir / f"subtle_overlay_{idx:02d}.png"
        subtle.save(subtle_path)
        subtle_paths.append(safe_rel(subtle_path))
        exact_boxes = details[idx - 1]["fresh_boxes"] if idx > 0 else []
        readable = draw_overlay_pil(crop, exact_boxes, fill_alpha=46, outline_alpha=0, width=0)
        readable_path = out_dir / f"readable_mask_{idx:02d}.png"
        readable.save(readable_path)
        readable_mask_paths.append(safe_rel(readable_path))
        exact = draw_overlay_pil(crop, exact_boxes, fill_alpha=78, outline_alpha=230, width=1)
        exact_path = out_dir / f"exact_overlay_{idx:02d}.png"
        exact.save(exact_path)
        exact_paths.append(safe_rel(exact_path))

    assets = {
        "rank": rank,
        "asset_dir": safe_rel(out_dir),
        "frames": frame_paths,
        "subtle_overlays": subtle_paths,
        "readable_masks": readable_mask_paths,
        "exact_overlays": exact_paths,
        "transitions": details,
    }
    return WindowRecord(**{**asdict(record), "metrics": record.metrics, "assets": assets})


def flatten_record_for_csv(rank: int, record: WindowRecord) -> dict[str, Any]:
    metrics = asdict(record.metrics)
    return {
        "rank": rank,
        "candidate_id": record.candidate_id,
        "video_id": record.video_id,
        "item_id": record.item_id,
        "benchmark": record.benchmark,
        "split": record.split,
        "start_s": f"{record.start_s:.3f}",
        "end_s": f"{record.end_s:.3f}",
        "window_length_s": f"{record.window_length_s:.3f}",
        "passes_basic_filters": record.passes_basic_filters,
        **{
            key: f"{value:.6f}" if isinstance(value, float) else value
            for key, value in metrics.items()
        },
        "video_path_hint": record.video_path_hint,
        "source_jsonl": record.source_jsonl,
    }


def select_diverse_records(
    records: list[WindowRecord],
    *,
    top_n: int,
    max_per_video: int,
    max_per_benchmark: int | None,
    require_benchmarks: tuple[str, ...],
    fallback_records: list[WindowRecord] | None = None,
) -> list[WindowRecord]:
    """Select a review set that does not repeat the same easy clip."""

    ranked = sorted(records, key=lambda record: record.metrics.story_score, reverse=True)
    selected: list[WindowRecord] = []
    selected_ids: set[str] = set()
    by_video: Counter[str] = Counter()
    by_benchmark: Counter[str] = Counter()

    def can_add(record: WindowRecord, *, enforce_benchmark_cap: bool) -> bool:
        if record.candidate_id in selected_ids:
            return False
        if by_video[record.video_id] >= max_per_video:
            return False
        return not (
            enforce_benchmark_cap
            and max_per_benchmark is not None
            and by_benchmark[record.benchmark] >= max_per_benchmark
        )

    def add(record: WindowRecord) -> None:
        selected.append(record)
        selected_ids.add(record.candidate_id)
        by_video[record.video_id] += 1
        by_benchmark[record.benchmark] += 1

    for benchmark in require_benchmarks:
        for record in ranked:
            if record.benchmark == benchmark and can_add(record, enforce_benchmark_cap=False):
                add(record)
                break
        else:
            fallback_ranked = sorted(
                fallback_records or [],
                key=lambda record: record.metrics.story_score,
                reverse=True,
            )
            for record in fallback_ranked:
                if record.benchmark == benchmark and can_add(record, enforce_benchmark_cap=False):
                    add(record)
                    break

    for record in ranked:
        if len(selected) >= top_n:
            break
        if can_add(record, enforce_benchmark_cap=True):
            add(record)

    return selected


def save_ranked_outputs(records: list[WindowRecord]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUT_DIR / "ranked_candidates.csv"
    json_path = OUT_DIR / "ranked_candidates.json"
    rows = [flatten_record_for_csv(idx + 1, record) for idx, record in enumerate(records)]
    if rows:
        with csv_path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
    json_path.write_text(
        json.dumps(
            {
                "purpose": (
                    "Figure 1 candidate windows ranked by persistence, compact novelty, "
                    "and visual clarity."
                ),
                "planner": {
                    "frame_size": BENCHMARK_FRAME_SIZE,
                    "block_size": QWEN_BLOCK_SIZE,
                    "statistic": EXACT_PIXEL_PLANNER.statistic.value,
                    "static_threshold": EXACT_PIXEL_PLANNER.static_threshold,
                    "shifted_threshold": EXACT_PIXEL_PLANNER.shifted_threshold,
                    "reuse_classes": [value.name.lower() for value in REUSE_CLASSES],
                    "max_age": TRACK_A_MAX_AGE,
                },
                "visualization_policy": VISUALIZATION_POLICY,
                "candidates": [asdict(record) for record in records],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def candidate_row_image(
    record: WindowRecord, rank: int, *, width: int = 1650, height: int = 310
) -> Image.Image:
    row = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(row)
    metrics = record.metrics
    draw.text(
        (22, 18),
        f"#{rank:02d} {record.item_id}  {record.start_s:.2f}-{record.end_s:.2f}s",
        fill=(15, 23, 42),
    )
    draw.text(
        (22, 42),
        (
            f"score {metrics.story_score:.2f} | reuse {metrics.reuse_mean_active:.0%} "
            f"min {metrics.reuse_min_active:.0%} | novel {metrics.novel_fraction_mean:.0%} "
            f"| comps {metrics.component_count_mean:.1f} | cut {metrics.cut_penalty:.1f} "
            f"| text {metrics.text_overlay_penalty:.1f}"
        ),
        fill=(71, 85, 105),
    )
    if record.question:
        question = record.question.replace("\n", " ")
        draw.text((22, 66), question[:145], fill=(71, 85, 105))
    assert record.assets is not None
    thumb_w = 145
    gap = 10
    y0 = 132
    x0 = 22
    draw.text((x0, y0 - 22), "clean frames", fill=(15, 23, 42))
    for idx, rel in enumerate(record.assets["frames"]):
        img = Image.open(REPO_ROOT / rel).convert("RGB")
        img = resize_width(img, thumb_w)
        row.paste(img, (x0 + idx * (thumb_w + gap), y0))
    x1 = x0 + 4 * (thumb_w + gap) + 28
    draw.text((x1, y0 - 22), "merged fresh-region highlights", fill=(15, 23, 42))
    for idx, rel in enumerate(record.assets["subtle_overlays"]):
        img = Image.open(REPO_ROOT / rel).convert("RGB")
        img = resize_width(img, thumb_w)
        row.paste(img, (x1 + idx * (thumb_w + gap), y0))
    x2 = x1 + 4 * (thumb_w + gap) + 28
    draw.text((x2, y0 - 22), "exact mask sample", fill=(15, 23, 42))
    exact_rel = record.assets["exact_overlays"][1]
    exact = Image.open(REPO_ROOT / exact_rel).convert("RGB")
    exact = resize_width(exact, thumb_w)
    row.paste(exact, (x2, y0))
    return row


def save_contact_sheets(records: list[WindowRecord], *, rows_per_page: int = 4) -> None:
    pages: list[Image.Image] = []
    page_w = 1650
    row_h = 345
    title_h = 70
    for page_idx in range(0, len(records), rows_per_page):
        page_records = records[page_idx : page_idx + rows_per_page]
        page = Image.new("RGB", (page_w, title_h + row_h * rows_per_page), "white")
        draw = ImageDraw.Draw(page)
        draw.text((22, 20), "Real-clip planner candidate windows", fill=(15, 23, 42))
        draw.text(
            (22, 43),
            (
                "Rows show clean frames, merged planner-derived highlights, and one "
                "exact planner mask inset."
            ),
            fill=(71, 85, 105),
        )
        for offset, record in enumerate(page_records):
            row = candidate_row_image(record, page_idx + offset + 1, width=page_w, height=row_h)
            page.paste(row, (0, title_h + offset * row_h))
        pages.append(page)
    if not pages:
        return
    pdf_path = OUT_DIR / "top_40_contact_sheet.pdf"
    pages[0].save(pdf_path, save_all=True, append_images=pages[1:])
    png_path = OUT_DIR / "top_12_contact_sheet.png"
    preview_count = min(12, len(records))
    preview_pages: list[Image.Image] = []
    for page_idx in range(0, preview_count, rows_per_page):
        page = Image.new("RGB", (page_w, title_h + row_h * rows_per_page), "white")
        draw = ImageDraw.Draw(page)
        draw.text((22, 20), "Real-clip planner candidate windows preview", fill=(15, 23, 42))
        for offset, record in enumerate(records[page_idx : page_idx + rows_per_page]):
            row = candidate_row_image(record, page_idx + offset + 1, width=page_w, height=row_h)
            page.paste(row, (0, title_h + offset * row_h))
        preview_pages.append(page)
    if preview_pages:
        total_h = sum(page.height for page in preview_pages)
        sheet = Image.new("RGB", (page_w, total_h), "white")
        y = 0
        for page in preview_pages:
            sheet.paste(page, (0, y))
            y += page.height
        sheet.save(png_path)


def mine(args: argparse.Namespace) -> list[WindowRecord]:
    exclude_video_ids = {part.strip() for part in args.exclude_video_ids.split(",") if part.strip()}
    if args.source_jsonl:
        source_jsonls = tuple(Path(path).resolve() for path in args.source_jsonl)
    elif args.scan_all_artifacts:
        source_jsonls = ()
    else:
        source_jsonls = tuple(path for path in RECOMMENDED_SOURCE_JSONLS if path.exists())
    sources = discover_video_sources(
        source_jsonls=source_jsonls,
        max_jsonl_mb=args.max_jsonl_mb,
        exclude_video_ids=exclude_video_ids,
    )
    if args.max_videos:
        sources = sources[: args.max_videos]
    print(f"discovered {len(sources)} local video sources")
    records: list[WindowRecord] = []
    lengths = tuple(float(item) for item in args.window_lengths_s.split(",") if item)
    for source_idx, source in enumerate(sources, start=1):
        try:
            duration_s = duration_seconds(source.video_path)
        except Exception as exc:
            print(f"skip duration failure {safe_rel(source.video_path)}: {exc}")
            continue
        windows = enumerate_windows(
            duration_s,
            lengths_s=lengths,
            max_windows_per_video=args.max_windows_per_video,
        )
        print(
            f"[{source_idx}/{len(sources)}] {source.item_id} "
            f"windows={len(windows)} duration={duration_s:.1f}s"
        )
        for start_s, end_s in windows:
            record = evaluate_window(source, start_s, end_s, duration_s)
            if record is not None:
                records.append(record)
    records.sort(key=lambda record: record.metrics.story_score, reverse=True)
    filtered = [record for record in records if record.passes_basic_filters]
    rank_source = filtered or records
    if args.diverse:
        max_per_benchmark = args.max_per_benchmark if args.max_per_benchmark > 0 else None
        ranked = select_diverse_records(
            rank_source,
            top_n=args.top_n,
            max_per_video=args.max_per_video,
            max_per_benchmark=max_per_benchmark,
            require_benchmarks=tuple(args.require_benchmark),
            fallback_records=records,
        )
    else:
        ranked = rank_source[: args.top_n]
    with_assets: list[WindowRecord] = []
    for rank, record in enumerate(ranked, start=1):
        try:
            with_assets.append(add_candidate_assets(record, rank))
        except Exception as exc:
            print(f"asset generation failed for {record.candidate_id}: {exc}")
    return with_assets


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--top-n", type=int, default=40)
    parser.add_argument("--max-videos", type=int, default=80)
    parser.add_argument("--max-windows-per-video", type=int, default=16)
    parser.add_argument("--max-jsonl-mb", type=float, default=80.0)
    parser.add_argument("--window-lengths-s", default="1.0,1.5,2.0,3.0")
    parser.add_argument("--exclude-video-ids", default="037")
    parser.add_argument("--source-jsonl", action="append", default=[])
    parser.add_argument("--scan-all-artifacts", action="store_true")
    parser.add_argument("--diverse", action="store_true")
    parser.add_argument("--max-per-video", type=int, default=1)
    parser.add_argument("--max-per-benchmark", type=int, default=16)
    parser.add_argument("--require-benchmark", action="append", default=[])
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    records = mine(args)
    save_ranked_outputs(records)
    save_contact_sheets(records)
    print(f"wrote {safe_rel(OUT_DIR / 'ranked_candidates.csv')}")
    print(f"wrote {safe_rel(OUT_DIR / 'ranked_candidates.json')}")
    print(f"wrote {safe_rel(OUT_DIR / 'top_40_contact_sheet.pdf')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
