#!/usr/bin/env python3
"""Render RLT/VLMaxxing overlays on the three VLMaxxing clips.

The renderer is an explanatory artifact, but the masks are computed by the same
local primitives used by the experiments:

* measured_c_vision mode shows the post-result Gemma RLT-as-C-VISION mechanism:
  dense encoder positions, fixed-K RLT-kept positions, and skipped compute.
* preregistration_overlay mode preserves the older Fig. 1 routing ∪ RLT
  admission view for provenance.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

from codec_through.rlt_masks import (
    RLTMaskConfig,
    artifact_config_hash,
    compute_rlt_keep_mask_from_frames,
    fixed_budget_rlt_score_mask,
    mask_summary,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

from render_codec_through_video_overlays import (  # type: ignore[import-not-found]  # noqa: E402
    BENCHMARK_FRAME_SIZE,
    CLIPS,
    FAINT,
    INK,
    MUTED,
    ORANGE,
    ORANGE_DARK,
    QWEN_BLOCK_SIZE,
    TRACK_A_MAX_AGE,
    WHITE,
    active_crop,
    decode_frames_at_times,
    font,
    overlay_boxes,
    square_pad_frame,
    text_size,
    thumbnail,
    transition_details,
    write_mp4,
)

OUT_ROOT = (
    REPO_ROOT / "research" / "experiments" / "2026" / "artifacts" / "rlt_vlmax_composition_overlays"
)
RLT_FOLLOWUP_ARTIFACT_DIR = (
    REPO_ROOT / "research" / "experiments" / "2026" / "artifacts" / "rlt_followup_queue"
)

BLUE = (37, 99, 235)
BLUE_DARK = (29, 78, 216)
GREEN = (22, 163, 74)
PURPLE = (126, 34, 206)
PANEL = (248, 250, 252)
OUTPUT_SIZE = (1600, 900)
PANE_BOXES = {
    "source": (40, 120, 780, 430),
    "vlmax": (820, 120, 1560, 430),
    "rlt": (40, 520, 780, 830),
    "combined": (820, 520, 1560, 830),
}
RLT_CONFIG = RLTMaskConfig(
    threshold=0.1,
    tubelet_size=2,
    image_size=(224, 224),
    patch_size=16,
    normalize_mode="imagenet",
    pixel_scale="uint8",
    first_tubelet_mode="full_grid",
    window_min_keep=0,
    ordering="time_major",
)
GEMMA_CVISION_GRID_SHAPE = (32, 32)
GEMMA_CVISION_KEEP_RATE = 0.5
PanelMode = str


def _git_sha() -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return completed.stdout.strip() or None


def _draw_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    *,
    fill: tuple[int, int, int] = INK,
    size: int = 18,
    bold: bool = False,
) -> None:
    draw.text(xy, text, fill=fill, font=font(size, bold=bold))


def _fit(image: Image.Image, box: tuple[int, int, int, int]) -> tuple[Image.Image, tuple[int, int]]:
    x0, y0, x1, y1 = box
    scale = min((x1 - x0) / image.width, (y1 - y0) / image.height)
    resized = image.resize(
        (max(1, round(image.width * scale)), max(1, round(image.height * scale))),
        Image.Resampling.LANCZOS,
    )
    return resized, (x0 + (x1 - x0 - resized.width) // 2, y0 + (y1 - y0 - resized.height) // 2)


def _label_pane(
    canvas: Image.Image,
    box: tuple[int, int, int, int],
    title: str,
    subtitle: str,
) -> None:
    draw = ImageDraw.Draw(canvas)
    x0, y0, _, _ = box
    _draw_text(draw, (x0, y0 - 42), title, size=20, bold=True)
    _draw_text(draw, (x0, y0 - 18), subtitle, fill=MUTED, size=13)


def _paste_pane(
    canvas: Image.Image,
    image: Image.Image,
    box: tuple[int, int, int, int],
    *,
    title: str,
    subtitle: str,
) -> None:
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle(box, radius=8, fill=WHITE, outline=FAINT, width=2)
    fitted, xy = _fit(image, (box[0] + 8, box[1] + 8, box[2] - 8, box[3] - 8))
    canvas.paste(fitted, xy)
    _label_pane(canvas, box, title, subtitle)


def _mask_to_active_pixels(
    mask: np.ndarray,
    *,
    active_box: tuple[int, int, int, int],
    padded_size: tuple[int, int],
    active_size: tuple[int, int],
) -> np.ndarray:
    rows, cols = mask.shape
    padded_w, padded_h = padded_size
    left, top, right, bottom = active_box
    active_w, active_h = active_size
    out = np.zeros((active_h, active_w), dtype=bool)
    for row in range(rows):
        for col in range(cols):
            if not bool(mask[row, col]):
                continue
            x0 = int(math.floor(col * padded_w / cols))
            x1 = int(math.ceil((col + 1) * padded_w / cols))
            y0 = int(math.floor(row * padded_h / rows))
            y1 = int(math.ceil((row + 1) * padded_h / rows))
            ix0 = max(x0, left)
            ix1 = min(x1, right)
            iy0 = max(y0, top)
            iy1 = min(y1, bottom)
            if ix1 <= ix0 or iy1 <= iy0:
                continue
            out[iy0 - top : iy1 - top, ix0 - left : ix1 - left] = True
    return out


def _boxes_to_active_pixels(
    boxes: list[list[float]] | list[tuple[float, float, float, float]],
    *,
    active_size: tuple[int, int],
) -> np.ndarray:
    active_w, active_h = active_size
    out = np.zeros((active_h, active_w), dtype=bool)
    for x0, y0, x1, y1 in boxes:
        px0 = max(0, min(active_w, int(math.floor(x0 * active_w))))
        px1 = max(0, min(active_w, int(math.ceil(x1 * active_w))))
        py0 = max(0, min(active_h, int(math.floor(y0 * active_h))))
        py1 = max(0, min(active_h, int(math.ceil(y1 * active_h))))
        if px1 > px0 and py1 > py0:
            out[py0:py1, px0:px1] = True
    return out


def _overlay_rlt(
    crop: Image.Image,
    rlt_mask: np.ndarray,
    *,
    active_box: tuple[int, int, int, int],
    padded_size: tuple[int, int],
) -> tuple[Image.Image, np.ndarray]:
    active_mask = _mask_to_active_pixels(
        rlt_mask,
        active_box=active_box,
        padded_size=padded_size,
        active_size=crop.size,
    )
    rgba = crop.convert("RGBA")
    layer = Image.new("RGBA", crop.size, (0, 0, 0, 0))
    data = np.zeros((crop.height, crop.width, 4), dtype=np.uint8)
    data[~active_mask] = (*GREEN, 34)
    data[active_mask] = (*BLUE, 105)
    layer = Image.fromarray(data, "RGBA")
    out = Image.alpha_composite(rgba, layer)
    draw = ImageDraw.Draw(out, "RGBA")
    rows, cols = rlt_mask.shape
    for row in range(rows):
        for col in range(cols):
            x0 = int(round(col * crop.width / cols))
            x1 = int(round((col + 1) * crop.width / cols))
            y0 = int(round(row * crop.height / rows))
            y1 = int(round((row + 1) * crop.height / rows))
            outline = (*BLUE_DARK, 150) if bool(rlt_mask[row, col]) else (*GREEN, 70)
            draw.rectangle((x0, y0, x1, y1), outline=outline, width=1)
    return out.convert("RGB"), active_mask


def _overlay_combined(
    crop: Image.Image,
    rlt_active: np.ndarray,
    vl_fresh: np.ndarray,
) -> tuple[Image.Image, dict[str, float]]:
    rlt_only = rlt_active & ~vl_fresh
    vl_only = vl_fresh & ~rlt_active
    overlap = rlt_active & vl_fresh
    data = np.zeros((crop.height, crop.width, 4), dtype=np.uint8)
    data[rlt_only] = (*BLUE, 95)
    data[vl_only] = (*ORANGE, 115)
    data[overlap] = (*PURPLE, 135)
    layer = Image.fromarray(data, "RGBA")
    out = Image.alpha_composite(crop.convert("RGBA"), layer)
    union = rlt_active | vl_fresh
    total = max(1, union.size)
    return (
        out.convert("RGB"),
        {
            "rlt_admit_active_pixel_fraction": float(rlt_active.sum() / total),
            "vlmax_fresh_active_pixel_fraction": float(vl_fresh.sum() / total),
            "combined_refresh_active_pixel_fraction": float(union.sum() / total),
            "overlap_active_pixel_fraction": float(overlap.sum() / total),
        },
    )


def _overlay_grid_mask(
    crop: Image.Image,
    keep_mask: np.ndarray,
    *,
    active_box: tuple[int, int, int, int],
    padded_size: tuple[int, int],
    mode: str,
) -> tuple[Image.Image, dict[str, float]]:
    active_keep = _mask_to_active_pixels(
        keep_mask,
        active_box=active_box,
        padded_size=padded_size,
        active_size=crop.size,
    )
    active_skip = ~active_keep
    data = np.zeros((crop.height, crop.width, 4), dtype=np.uint8)
    if mode == "dense":
        data[:, :] = (*BLUE, 45)
    elif mode == "kept":
        data[active_keep] = (*BLUE, 115)
        data[active_skip] = (*GREEN, 38)
    elif mode == "skipped":
        data[active_skip] = (*GREEN, 125)
        data[active_keep] = (*BLUE, 32)
    else:
        raise ValueError(f"unknown grid overlay mode {mode!r}")
    out = Image.alpha_composite(crop.convert("RGBA"), Image.fromarray(data, "RGBA"))
    draw = ImageDraw.Draw(out, "RGBA")
    rows, cols = keep_mask.shape
    for row in range(rows):
        for col in range(cols):
            x0 = int(round(col * crop.width / cols))
            x1 = int(round((col + 1) * crop.width / cols))
            y0 = int(round(row * crop.height / rows))
            y1 = int(round((row + 1) * crop.height / rows))
            outline = (*BLUE_DARK, 95) if bool(keep_mask[row, col]) else (*GREEN, 62)
            draw.rectangle((x0, y0, x1, y1), outline=outline, width=1)
    total = max(1, active_keep.size)
    return (
        out.convert("RGB"),
        {
            "kept_active_pixel_fraction": float(active_keep.sum() / total),
            "skipped_active_pixel_fraction": float(active_skip.sum() / total),
        },
    )


def _read_analysis_metrics(artifact_dir: Path) -> dict[str, dict[str, Any]]:
    metrics: dict[str, dict[str, Any]] = {}
    for benchmark in ("videomme", "tomato", "mvbench"):
        analysis_path = artifact_dir / f"cvision_rlt_{benchmark}_analysis.json"
        if not analysis_path.exists():
            continue
        analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
        all_summary = analysis.get("all", {})
        measured_item_ids: list[str] = []
        sparse_jsonl = analysis.get("sparse_jsonl")
        sparse_path = Path(sparse_jsonl) if isinstance(sparse_jsonl, str) else None
        if sparse_path is not None and not sparse_path.is_absolute():
            sparse_path = REPO_ROOT / sparse_path
        if sparse_path is not None and sparse_path.exists():
            with sparse_path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    if row.get("kind") in (None, "item"):
                        measured_item_ids.append(str(row.get("item_id")))
        maxmin_path = artifact_dir / f"cvision_maxmin_{benchmark}_analysis.json"
        maxmin_summary: dict[str, Any] = {}
        if maxmin_path.exists():
            maxmin = json.loads(maxmin_path.read_text(encoding="utf-8"))
            maxmin_summary = maxmin.get("all", {})
        rlt_scorer = all_summary.get("mean_sparse_scorer_total_ms")
        maxmin_scorer = maxmin_summary.get("mean_sparse_scorer_total_ms")
        metrics[benchmark] = {
            "analysis_path": str(analysis_path),
            "measured_item_ids": measured_item_ids,
            "e2e_speedup": all_summary.get("actual_e2e_speedup_dense_over_sparse"),
            "e2e_speedup_ci95": all_summary.get("actual_e2e_speedup_dense_over_sparse_ci95"),
            "accuracy_delta": all_summary.get("accuracy_delta_sparse_minus_dense"),
            "accuracy_delta_ci95": all_summary.get("accuracy_delta_sparse_minus_dense_ci95"),
            "vision_reduction": all_summary.get("vision_reduction"),
            "vision_share_dense": all_summary.get("vision_share_dense"),
            "rlt_scorer_ms": rlt_scorer,
            "maxmin_scorer_ms": maxmin_scorer,
            "scorer_cost_ratio_maxmin_over_rlt": (
                float(maxmin_scorer) / float(rlt_scorer)
                if isinstance(maxmin_scorer, (int, float))
                and isinstance(rlt_scorer, (int, float))
                and float(rlt_scorer) > 0.0
                else None
            ),
        }
    return metrics


def _metric_for_spec(spec: Any, measured_results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return measured_results.get(str(spec.benchmark).lower(), {})


def _draw_badge(
    canvas: Image.Image, text: str, xy: tuple[int, int], color: tuple[int, int, int]
) -> None:
    draw = ImageDraw.Draw(canvas)
    fnt = font(14, bold=True)
    w, h = text_size(draw, text, fnt)
    box = (xy[0], xy[1], xy[0] + w + 20, xy[1] + h + 12)
    soft = tuple(int(round(255 - (255 - channel) * 0.14)) for channel in color)
    draw.rounded_rectangle(box, radius=6, fill=soft, outline=color, width=2)
    draw.text((xy[0] + 10, xy[1] + 6), text, fill=color, font=fnt)


def _decode(
    spec: Any, fps: float
) -> tuple[list[float], list[Image.Image], list[tuple[int, int, int, int]]]:
    frame_count = max(4, int(math.ceil((spec.end_s - spec.start_s) * fps)) + 1)
    times = [
        spec.start_s + (spec.end_s - spec.start_s) * idx / max(1, frame_count - 1)
        for idx in range(frame_count)
    ]
    raw = decode_frames_at_times(spec.video_path, times)
    padded_frames: list[Image.Image] = []
    active_boxes: list[tuple[int, int, int, int]] = []
    for frame in raw:
        padded, active_box = square_pad_frame(frame)
        padded_frames.append(padded)
        active_boxes.append(active_box)
    return times, padded_frames, active_boxes


def _rlt_frames_for_compute(padded_frames: list[Image.Image]) -> tuple[list[Image.Image], int]:
    if len(padded_frames) % RLT_CONFIG.tubelet_size == 0:
        return padded_frames, 0
    return [*padded_frames, padded_frames[-1].copy()], 1


def _render_frame(
    *,
    spec: Any,
    frame_idx: int,
    frame_count: int,
    crop: Image.Image,
    vl_overlay: Image.Image,
    rlt_overlay: Image.Image,
    combined_overlay: Image.Image,
    stats: dict[str, float],
    rlt_keep_rate: float,
) -> Image.Image:
    canvas = Image.new("RGB", OUTPUT_SIZE, PANEL)
    draw = ImageDraw.Draw(canvas)
    _draw_text(
        draw,
        (40, 28),
        f"RLT + VLMaxxing composition: {spec.benchmark} {spec.video_id}",
        size=30,
        bold=True,
    )
    _draw_text(
        draw,
        (42, 66),
        (
            f"{spec.role} · frame {frame_idx + 1}/{frame_count} · "
            "orange=VL fresh, blue=RLT representative token, purple=overlap"
        ),
        fill=MUTED,
        size=16,
    )
    _paste_pane(
        canvas,
        crop,
        PANE_BOXES["source"],
        title="source frame",
        subtitle="same window used by the VLMaxxing overlay",
    )
    _paste_pane(
        canvas,
        vl_overlay,
        PANE_BOXES["vlmax"],
        title="VLMaxxing routing",
        subtitle="fresh blocks from checked transition policy",
    )
    _paste_pane(
        canvas,
        rlt_overlay,
        PANE_BOXES["rlt"],
        title="RLT-style admission",
        subtitle=f"mask only, no length encoding; token keep={rlt_keep_rate:.1%}",
    )
    _paste_pane(
        canvas,
        combined_overlay,
        PANE_BOXES["combined"],
        title="conservative composition",
        subtitle=f"union active pixels={stats['combined_refresh_active_pixel_fraction']:.1%}",
    )
    _draw_badge(
        canvas,
        f"RLT px {stats['rlt_admit_active_pixel_fraction']:.0%}",
        (40, 842),
        BLUE_DARK,
    )
    _draw_badge(
        canvas,
        f"VL px {stats['vlmax_fresh_active_pixel_fraction']:.0%}",
        (205, 842),
        ORANGE_DARK,
    )
    _draw_badge(
        canvas,
        f"overlap px {stats['overlap_active_pixel_fraction']:.0%}",
        (350, 842),
        PURPLE,
    )
    return canvas


def _fmt_metric(value: Any, suffix: str = "") -> str:
    if isinstance(value, (int, float)):
        return f"{value:.3g}{suffix}"
    return "n/a"


def _render_measured_frame(
    *,
    spec: Any,
    frame_idx: int,
    frame_count: int,
    crop: Image.Image,
    dense_overlay: Image.Image,
    kept_overlay: Image.Image,
    skipped_overlay: Image.Image,
    stats: dict[str, float],
    token_keep_rate: float,
    metrics: dict[str, Any],
) -> Image.Image:
    canvas = Image.new("RGB", OUTPUT_SIZE, PANEL)
    draw = ImageDraw.Draw(canvas)
    speedup = metrics.get("e2e_speedup")
    vision_reduction = metrics.get("vision_reduction")
    scorer_ms = metrics.get("rlt_scorer_ms")
    ratio = metrics.get("scorer_cost_ratio_maxmin_over_rlt")
    vision_saved_pct = (
        float(vision_reduction) * 100 if isinstance(vision_reduction, (int, float)) else None
    )
    _draw_text(
        draw,
        (40, 28),
        f"Measured RLT-as-C-VISION: {spec.benchmark} {spec.video_id}",
        size=30,
        bold=True,
    )
    _draw_text(
        draw,
        (42, 66),
        (
            f"{spec.role} · frame {frame_idx + 1}/{frame_count} · "
            f"e2e={_fmt_metric(speedup, '×')} · "
            f"vision saved={_fmt_metric(vision_saved_pct, '%')} · "
            f"RLT scorer={_fmt_metric(scorer_ms, ' ms/item')}"
        ),
        fill=MUTED,
        size=16,
    )
    _paste_pane(
        canvas,
        crop,
        PANE_BOXES["source"],
        title="source frame",
        subtitle="same decoded window as the benchmark item",
    )
    _paste_pane(
        canvas,
        dense_overlay,
        PANE_BOXES["vlmax"],
        title="dense vision tower",
        subtitle="all valid Gemma encoder positions computed",
    )
    _paste_pane(
        canvas,
        kept_overlay,
        PANE_BOXES["rlt"],
        title="RLT-as-C-VISION kept",
        subtitle=f"fixed-K RLT scorer; token keep={token_keep_rate:.1%}",
    )
    _paste_pane(
        canvas,
        skipped_overlay,
        PANE_BOXES["combined"],
        title="compute skipped",
        subtitle=f"active pixels skipped={stats['skipped_active_pixel_fraction']:.1%}",
    )
    _draw_badge(
        canvas,
        f"kept px {stats['kept_active_pixel_fraction']:.0%}",
        (40, 842),
        BLUE_DARK,
    )
    _draw_badge(
        canvas,
        f"skipped px {stats['skipped_active_pixel_fraction']:.0%}",
        (205, 842),
        GREEN,
    )
    if isinstance(ratio, (int, float)):
        _draw_badge(canvas, f"max-min scorer {ratio:.0f}x cost", (380, 842), PURPLE)
    return canvas


def render_clip(
    spec: Any,
    *,
    fps: float,
    out_dir: Path,
    panel_mode: PanelMode,
    measured_results: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    _times, padded_frames, active_boxes = _decode(spec, fps)
    transitions = transition_details(padded_frames, active_boxes)
    rlt_frames, rlt_padding_frame_count = _rlt_frames_for_compute(padded_frames)
    rlt_result = compute_rlt_keep_mask_from_frames(rlt_frames, config=RLT_CONFIG)
    cvision_mask = fixed_budget_rlt_score_mask(
        rlt_result,
        out_grid_shape=GEMMA_CVISION_GRID_SHAPE,
        keep_rate=GEMMA_CVISION_KEEP_RATE,
    )
    frames: list[Image.Image] = []
    combined_stats: list[dict[str, float]] = []
    measured_stats: list[dict[str, float]] = []
    clip_metrics = _metric_for_spec(spec, measured_results)

    for idx, (padded, active_box) in enumerate(zip(padded_frames, active_boxes, strict=True)):
        crop = active_crop(padded, active_box).convert("RGB")
        if panel_mode == "preregistration_overlay":
            transition = transitions[idx - 1] if idx > 0 else None
            vl_overlay = overlay_boxes(crop, transition, mode="audit")
            rlt_overlay, rlt_active = _overlay_rlt(
                crop,
                rlt_result.frame_keep_mask[idx],
                active_box=active_box,
                padded_size=padded.size,
            )
            vl_fresh = _boxes_to_active_pixels(
                [] if transition is None else transition.get("fresh_boxes", []),
                active_size=crop.size,
            )
            combined, stats = _overlay_combined(crop, rlt_active, vl_fresh)
            combined_stats.append(stats)
            frames.append(
                _render_frame(
                    spec=spec,
                    frame_idx=idx,
                    frame_count=len(padded_frames),
                    crop=crop,
                    vl_overlay=vl_overlay,
                    rlt_overlay=rlt_overlay,
                    combined_overlay=combined,
                    stats=stats,
                    rlt_keep_rate=float(rlt_result.frame_keep_mask[idx].mean()),
                )
            )
        elif panel_mode == "measured_c_vision":
            frame_mask = cvision_mask[idx]
            dense_overlay, _dense_stats = _overlay_grid_mask(
                crop,
                np.ones_like(frame_mask, dtype=bool),
                active_box=active_box,
                padded_size=padded.size,
                mode="dense",
            )
            kept_overlay, stats = _overlay_grid_mask(
                crop,
                frame_mask,
                active_box=active_box,
                padded_size=padded.size,
                mode="kept",
            )
            skipped_overlay, _skip_stats = _overlay_grid_mask(
                crop,
                frame_mask,
                active_box=active_box,
                padded_size=padded.size,
                mode="skipped",
            )
            measured_stats.append(stats)
            frames.append(
                _render_measured_frame(
                    spec=spec,
                    frame_idx=idx,
                    frame_count=len(padded_frames),
                    crop=crop,
                    dense_overlay=dense_overlay,
                    kept_overlay=kept_overlay,
                    skipped_overlay=skipped_overlay,
                    stats=stats,
                    token_keep_rate=float(frame_mask.mean()),
                    metrics=clip_metrics,
                )
            )
        else:
            raise ValueError(f"unknown panel_mode {panel_mode!r}")

    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = (
        "rlt_cvision_mechanism" if panel_mode == "measured_c_vision" else "rlt_vlmax_composition"
    )
    video_path = out_dir / f"{spec.key}_{suffix}.mp4"
    write_mp4(frames, video_path, fps=fps)
    thumb_path = out_dir / "thumbnails" / f"{video_path.stem}.png"
    thumbnail(frames[min(len(frames) - 1, max(0, len(frames) // 2))], thumb_path)
    stats_source = measured_stats if panel_mode == "measured_c_vision" else combined_stats
    mean_stats = {
        key: float(np.mean([stats[key] for stats in stats_source])) for key in stats_source[0]
    }
    return {
        "key": spec.key,
        "benchmark": spec.benchmark,
        "video_id": spec.video_id,
        "video_path": str(video_path),
        "thumbnail_path": str(thumb_path),
        "source_video": str(spec.video_path),
        "start_s": spec.start_s,
        "end_s": spec.end_s,
        "frame_count": len(frames),
        "displayed_frame_count": len(frames),
        "rlt_input_frame_count": rlt_result.frame_count,
        "rlt_duplicate_last_frame_count": rlt_padding_frame_count,
        "fps": fps,
        "rlt_mask_summary": mask_summary(rlt_result),
        "rlt_keep_rate_token_domain": rlt_result.keep_rate,
        "panel_mode": panel_mode,
        "gemma_cvision_grid_shape": list(GEMMA_CVISION_GRID_SHAPE),
        "gemma_cvision_keep_rate": GEMMA_CVISION_KEEP_RATE,
        "mean_composition_stats": mean_stats if panel_mode == "preregistration_overlay" else None,
        "mean_measured_cvision_stats": mean_stats if panel_mode == "measured_c_vision" else None,
        "measured_benchmark_result": clip_metrics,
        "measured_item_exact": spec.item_id
        in set(str(item_id) for item_id in clip_metrics.get("measured_item_ids", [])),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fps", type=float, default=12.0)
    parser.add_argument("--out-dir", type=Path, default=OUT_ROOT)
    parser.add_argument(
        "--panel-mode",
        choices=("measured_c_vision", "preregistration_overlay"),
        default="measured_c_vision",
    )
    parser.add_argument("--results-dir", type=Path, default=RLT_FOLLOWUP_ARTIFACT_DIR)
    args = parser.parse_args()
    if args.fps <= 0.0:
        raise SystemExit("--fps must be positive")

    measured_results = _read_analysis_metrics(args.results_dir)
    records = [
        render_clip(
            spec,
            fps=args.fps,
            out_dir=args.out_dir,
            panel_mode=args.panel_mode,
            measured_results=measured_results,
        )
        for spec in CLIPS
    ]
    schema_version = (
        "rlt_cvision_mechanism_overlay_v1"
        if args.panel_mode == "measured_c_vision"
        else "rlt_vlmax_composition_overlay_v1"
    )
    manifest = {
        "schema_version": schema_version,
        "git_sha": _git_sha(),
        "rlt_config_hash": artifact_config_hash(RLT_CONFIG.as_dict()),
        "panel_mode": args.panel_mode,
        "purpose": (
            "Post-result RLT/VLMaxxing visualization. In measured_c_vision mode "
            "the panes show the measured Gemma C-VISION mechanism: dense encoder "
            "positions, fixed-K RLT-kept positions, and skipped compute."
            if args.panel_mode == "measured_c_vision"
            else (
                "Scientifically grounded visualization of the preregistered "
                "RLT/VLMaxxing composition hypothesis on the same three videos "
                "used by the VLMaxxing overlay reel."
            )
        ),
        "accuracy_contract": {
            "vlmaxxing": (
                "In measured_c_vision mode, VLMaxxing means Gemma sparse-vision "
                "scatter-back: the prompt geometry is unchanged while the vision "
                "tower computes only fixed-K encoder positions. In preregistration "
                "mode, fresh/reuse boxes are recomputed with the older Fig. 1 "
                "Qwen routing-budget policy."
            ),
            "rlt": (
                "RLT panes are computed with codec_through.rlt_masks on the same "
                "square-padded frames, using tau=0.1, tubelet_size=2, 224x224 "
                "ImageNet-normalized input, and patch_size=16. Measured C-VISION "
                "mode converts those scores to a fixed-K top-50% Gemma 32x32 "
                "encoder mask, matching the rlt_topk scorer used by the runner."
            ),
            "combined": (
                "Measured C-VISION mode shows skipped vision-tower compute, not "
                "a pixel-domain union. The old union view is retained only under "
                "panel_mode=preregistration_overlay and should not be used as the "
                "post-result speedup explanation."
            ),
            "denominators": (
                "Overlay fractions are active-crop pixel fractions for visualization. "
                "The manifest records the Gemma token-domain keep rate separately."
            ),
            "rlt_frame_parity": (
                "Displayed frame counts match the existing VLMaxxing windows. If a window has an "
                "odd frame count, the renderer duplicates the final frame only for RLT mask "
                "computation, then displays the original frame sequence."
            ),
            "mask_reconstruction": (
                "The renderer reconstructs fixed-K RLT C-VISION masks from the "
                "logged config and local source videos. The committed JSONLs record "
                "counts and timings, not per-position boolean masks; this visualization "
                "is therefore algorithmically faithful but not a replay of persisted "
                "mask arrays."
            ),
        },
        "measured_results": measured_results,
        "algorithm_policy": {
            "routing": {
                "preprocessing": f"square-pad resize {BENCHMARK_FRAME_SIZE}x{BENCHMARK_FRAME_SIZE}",
                "block_size": QWEN_BLOCK_SIZE,
                "statistic": "max_abs",
                "static_threshold": 8.0,
                "shifted_threshold": 32.0,
                "reuse_rule": f"static + shifted while age < {TRACK_A_MAX_AGE}",
                "fresh_rule": "novel + age-expired",
                "active_region_only": True,
            },
            "rlt": RLT_CONFIG.as_dict(),
            "gemma_cvision": {
                "grid_shape": list(GEMMA_CVISION_GRID_SHAPE),
                "keep_rate": GEMMA_CVISION_KEEP_RATE,
                "score_mode": "rlt_topk_fixed_k",
                "scatter_back": True,
            },
        },
        "clips": records,
    }
    manifest_path = args.out_dir / "rlt_vlmax_composition_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"manifest": str(manifest_path), "clips": records}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
