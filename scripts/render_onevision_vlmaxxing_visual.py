#!/usr/bin/env python3
"""Render a CPU-only OneVision + VLMaxxing explainer figure.

The default path uses synthetic score volumes so the visualization can be
checked without benchmark videos, PyAV, MLX, or model inference.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from codec_through.codec.continuous_score import (
    CodecScoreSource,
    codec_score_units,
    mean_pool_blocks,
    project_macroblock_metadata_to_token_grid,
    sparse_sample_indices,
)
from codec_through.codec.onevision_patchification import (
    PatchificationConfig,
    SpatialBias,
    TemporalCoverage,
    VisiblePatch,
    count_tokens_by_frame,
    fuse_motion_residual,
    select_visible_patches,
    spatial_bias,
    temporal_coverage,
    visible_indices_array,
)

DEFAULT_OUT_DIR = Path("research/experiments/2026/artifacts/onevision_vlmaxxing_visuals")
GRID_SHAPE = (8, 8)
FRAMES = 16
CELL = 20
GAP = 2
CANVAS_SIZE = 560
TOKEN_BLOCK = 28
PROJECTION_GEOMETRY = {
    "local_grid": "VLMaxxing/Qwen-style visualization token grid",
    "canvas_size": CANVAS_SIZE,
    "token_block": TOKEN_BLOCK,
    "upstream_stage1_reference": {"canvas_size": 576, "source_patch_size": 16},
    "onevision_encoder_reference": {"vit_patch_size": 14},
}
REAL_SCORE_SOURCES = (
    CodecScoreSource.MOTION,
    CodecScoreSource.RESIDUAL,
    CodecScoreSource.FUSED,
)

BLUE = (54, 107, 196)
ORANGE = (226, 135, 46)
GREEN = (54, 150, 92)
RED = (198, 70, 70)
GRAY = (155, 160, 166)
DARK = (35, 39, 47)
LIGHT_BG = (247, 248, 250)
PANEL_BG = (255, 255, 255)
TEXT = (28, 32, 38)


@dataclass(frozen=True, slots=True)
class ClipSpec:
    name: str
    video_path: Path
    start_seconds: float
    end_seconds: float


REAL_CLIPS = (
    ClipSpec(
        name="tomato_0298_00",
        video_path=Path("data/benchmarks/tomato/videos/object/0298-00.mp4"),
        start_seconds=0.0,
        end_seconds=2.0,
    ),
    ClipSpec(
        name="videomme_380",
        video_path=Path("data/benchmarks/videomme/videos/2Bns2m5Bg4M.mp4"),
        start_seconds=206.39,
        end_seconds=207.89,
    ),
    ClipSpec(
        name="videomme_267",
        video_path=Path("data/benchmarks/videomme/videos/Atf_Af1q_5w.mp4"),
        start_seconds=0.0,
        end_seconds=1.0,
    ),
)


def build_synthetic_scores() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return motion, residual, and fused score volumes for the explainer."""

    rows, cols = GRID_SHAPE
    motion = np.zeros((FRAMES, rows, cols), dtype=np.float32)
    residual = np.zeros_like(motion)
    for frame in range(FRAMES):
        row = 1 + min(5, frame // 3)
        col = 1 + ((frame * 2) % 6)
        motion[frame, row : row + 2, max(0, col - 1) : min(cols, col + 1)] = 3.0
        residual[frame, row, col] = 5.0
        if 5 <= frame <= 7:
            residual[frame, 6, 1:7] = 2.5
        if frame in {11, 12}:
            motion[frame, 0:2, 6:8] = 2.0
            residual[frame, 0, 7] = 4.0
    fused = fuse_motion_residual(motion, residual, mode="weighted")
    return motion, residual, fused


def draw_grid(
    draw: ImageDraw.ImageDraw,
    origin: tuple[int, int],
    *,
    fills: dict[tuple[int, int], tuple[int, int, int]],
    outline: tuple[int, int, int] = (218, 222, 228),
) -> None:
    x0, y0 = origin
    rows, cols = GRID_SHAPE
    for row in range(rows):
        for col in range(cols):
            left = x0 + col * (CELL + GAP)
            top = y0 + row * (CELL + GAP)
            right = left + CELL
            bottom = top + CELL
            fill = fills.get((row, col), (236, 239, 243))
            draw.rectangle((left, top, right, bottom), fill=fill, outline=outline)


def draw_timeline(
    draw: ImageDraw.ImageDraw,
    origin: tuple[int, int],
    *,
    counts: np.ndarray,
    color: tuple[int, int, int],
    max_count: int,
) -> None:
    x0, y0 = origin
    bar_w = 14
    max_h = 90
    for index, count in enumerate(counts.tolist()):
        height = int(max_h * (float(count) / float(max_count))) if max_count > 0 else 0
        left = x0 + index * (bar_w + 4)
        draw.rectangle((left, y0 + max_h - height, left + bar_w, y0 + max_h), fill=color)
        draw.text((left + 2, y0 + max_h + 8), str(index), fill=(90, 96, 105), font=small_font())


def draw_panel_title(
    draw: ImageDraw.ImageDraw,
    origin: tuple[int, int],
    title: str,
    subtitle: str,
) -> None:
    x, y = origin
    draw.text((x, y), title, fill=TEXT, font=title_font())
    draw_wrapped_text(
        draw,
        (x, y + 34),
        subtitle,
        fill=(84, 91, 102),
        font=body_font(),
        max_width=305,
        line_height=20,
    )


def draw_wrapped_text(
    draw: ImageDraw.ImageDraw,
    origin: tuple[int, int],
    text: str,
    *,
    fill: tuple[int, int, int],
    font: ImageFont.ImageFont,
    max_width: int,
    line_height: int,
) -> None:
    x, y = origin
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if draw.textlength(candidate, font=font) <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
        current = word
    if current:
        lines.append(current)
    for index, line in enumerate(lines):
        draw.text((x, y + index * line_height), line, fill=fill, font=font)


def title_font() -> ImageFont.ImageFont:
    return ImageFont.load_default(size=23)


def body_font() -> ImageFont.ImageFont:
    return ImageFont.load_default(size=16)


def small_font() -> ImageFont.ImageFont:
    return ImageFont.load_default(size=12)


def grid_fills_from_patches(
    patches: list[VisiblePatch],
    *,
    frame: int,
) -> dict[tuple[int, int], tuple[int, int, int]]:
    fills: dict[tuple[int, int], tuple[int, int, int]] = {}
    for patch in patches:
        if patch.frame != frame:
            continue
        fills[(patch.row, patch.col)] = BLUE if patch.source == "anchor" else ORANGE
    return fills


def fake_vlmaxxing_fresh_mask(frame_scores: np.ndarray) -> dict[tuple[int, int], str]:
    """Build a deterministic fresh/reused/age-expired mask for explanation only."""

    rows, cols = GRID_SHAPE
    flat_threshold = float(np.quantile(frame_scores.reshape(-1), 0.82))
    labels: dict[tuple[int, int], str] = {}
    for row in range(rows):
        for col in range(cols):
            if frame_scores[row, col] >= flat_threshold and frame_scores[row, col] > 0.0:
                labels[(row, col)] = "fresh"
            elif (row + col) % 7 == 0:
                labels[(row, col)] = "expired"
            else:
                labels[(row, col)] = "reused"
    return labels


def render_synthetic(out_dir: Path) -> dict[str, object]:
    _, _, fused = build_synthetic_scores()
    config = PatchificationConfig(token_budget=96, anchor_frames=(0,))
    patches = select_visible_patches(fused, config=config)
    counts = count_tokens_by_frame(patches, total_frames=FRAMES)
    coverage = temporal_coverage(patches, total_frames=FRAMES)
    bias = spatial_bias(patches, grid_shape=GRID_SHAPE)

    out_dir.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (1600, 900), LIGHT_BG)
    draw = ImageDraw.Draw(image)
    draw.text(
        (48, 34),
        "VLMaxxing + OneVision: separate freshness from sparse encoding",
        fill=DARK,
        font=title_font(),
    )
    draw.text(
        (48, 70),
        "Synthetic CPU-only explainer: budgets are visual evidence, not model accuracy or speedup.",
        fill=(74, 81, 93),
        font=body_font(),
    )

    panel_w = 360
    panel_h = 720
    panel_y = 130
    panel_xs = [48, 428, 808, 1188]
    for x in panel_xs:
        draw.rounded_rectangle(
            (x, panel_y, x + panel_w, panel_y + panel_h), radius=8, fill=PANEL_BG
        )

    # Panel 1: dense uniform frame sampling.
    draw_panel_title(
        draw,
        (panel_xs[0] + 24, panel_y + 24),
        "1. Uniform dense frames",
        "Few timestamps, every patch in each chosen frame.",
    )
    dense_counts = np.zeros(FRAMES, dtype=np.int32)
    dense_counts[[0, 5, 10, 15]] = GRID_SHAPE[0] * GRID_SHAPE[1]
    draw_timeline(
        draw,
        (panel_xs[0] + 36, panel_y + 110),
        counts=dense_counts,
        color=GRAY,
        max_count=64,
    )
    draw_grid(
        draw,
        (panel_xs[0] + 92, panel_y + 285),
        fills={(r, c): GRAY for r in range(8) for c in range(8)},
    )
    draw.text(
        (panel_xs[0] + 34, panel_y + 505),
        "Budget: 4 x 64 = 256 patches",
        fill=TEXT,
        font=body_font(),
    )
    draw_wrapped_text(
        draw,
        (panel_xs[0] + 34, panel_y + 540),
        "Failure mode: motion between sampled frames is invisible.",
        fill=(84, 91, 102),
        font=body_font(),
        max_width=300,
        line_height=22,
    )

    # Panel 2: OneVision-style allocation.
    draw_panel_title(
        draw,
        (panel_xs[1] + 24, panel_y + 24),
        "2. Codec patch allocation",
        "Anchor context plus global motion/residual Top-K.",
    )
    draw_timeline(
        draw,
        (panel_xs[1] + 36, panel_y + 110),
        counts=counts,
        color=ORANGE,
        max_count=64,
    )
    draw_grid(
        draw, (panel_xs[1] + 92, panel_y + 285), fills=grid_fills_from_patches(patches, frame=7)
    )
    draw.text(
        (panel_xs[1] + 34, panel_y + 505),
        "Budget: 96 selected patches over 16 frames",
        fill=TEXT,
        font=body_font(),
    )
    draw.text(
        (panel_xs[1] + 34, panel_y + 540),
        f"Observed frames: {coverage.observed_frames}/16",
        fill=(84, 91, 102),
        font=body_font(),
    )
    draw.text(
        (panel_xs[1] + 34, panel_y + 570),
        f"Spatial center share: {bias.center_fraction:.2f}",
        fill=(84, 91, 102),
        font=body_font(),
    )

    # Panel 3: VLMaxxing-style reuse.
    draw_panel_title(
        draw,
        (panel_xs[2] + 24, panel_y + 24),
        "3. VLMaxxing freshness",
        "Decide reused, fresh, or age-expired state.",
    )
    labels = fake_vlmaxxing_fresh_mask(fused[7])
    reuse_fills = {
        pos: (GREEN if label == "fresh" else RED if label == "expired" else GRAY)
        for pos, label in labels.items()
    }
    draw_grid(draw, (panel_xs[2] + 92, panel_y + 160), fills=reuse_fills)
    draw.text(
        (panel_xs[2] + 34, panel_y + 390), "Green: fresh evidence", fill=GREEN, font=body_font()
    )
    draw.text(
        (panel_xs[2] + 34, panel_y + 425),
        "Gray: reused validated state",
        fill=GRAY,
        font=body_font(),
    )
    draw.text(
        (panel_xs[2] + 34, panel_y + 460), "Red: forced refresh by age", fill=RED, font=body_font()
    )
    draw_wrapped_text(
        draw,
        (panel_xs[2] + 34, panel_y + 520),
        "This is a runtime/cache policy, not semantic saliency.",
        fill=(84, 91, 102),
        font=body_font(),
        max_width=300,
        line_height=22,
    )

    # Panel 4: combined, thinning only the fresh lane.
    draw_panel_title(
        draw,
        (panel_xs[3] + 24, panel_y + 24),
        "4. Combined policy",
        "Reuse stable state; sparse-codec only where fresh.",
    )
    selected_frame7 = {pos for pos, label in labels.items() if label != "reused"}
    codec_frame7 = {
        (patch.row, patch.col)
        for patch in patches
        if patch.frame == 7 and (patch.row, patch.col) in selected_frame7
    }
    combined_fills: dict[tuple[int, int], tuple[int, int, int]] = {}
    for pos, label in labels.items():
        if label == "reused":
            combined_fills[pos] = GRAY
        elif pos in codec_frame7:
            combined_fills[pos] = ORANGE
        else:
            combined_fills[pos] = (230, 218, 197)
    draw_grid(draw, (panel_xs[3] + 92, panel_y + 160), fills=combined_fills)
    draw.text(
        (panel_xs[3] + 34, panel_y + 390),
        f"Fresh candidates: {len(selected_frame7)} blocks",
        fill=TEXT,
        font=body_font(),
    )
    draw.text(
        (panel_xs[3] + 34, panel_y + 425),
        f"Codec-selected fresh: {len(codec_frame7)} blocks",
        fill=ORANGE,
        font=body_font(),
    )
    draw_wrapped_text(
        draw,
        (panel_xs[3] + 34, panel_y + 485),
        "Report Track A, Track B, and C-PERSIST separately.",
        fill=(84, 91, 102),
        font=body_font(),
        max_width=300,
        line_height=22,
    )

    out_png = out_dir / "onevision_vlmaxxing_synthetic_explainer.png"
    image.save(out_png)
    summary = {
        "image": str(out_png),
        "token_budget": config.token_budget,
        "frames": FRAMES,
        "grid_shape": list(GRID_SHAPE),
        "tokens_by_frame": counts.tolist(),
        "temporal_coverage": {
            "observed_frames": coverage.observed_frames,
            "observed_fraction": coverage.observed_fraction,
            "max_gap": coverage.max_gap,
            "mean_gap": coverage.mean_gap,
            "entropy_bits": coverage.entropy_bits,
        },
        "spatial_bias": {
            "center_fraction": bias.center_fraction,
            "boundary_fraction": bias.boundary_fraction,
            "mean_center_distance": bias.mean_center_distance,
            "entropy_bits": bias.entropy_bits,
        },
    }
    (out_dir / "onevision_vlmaxxing_synthetic_explainer.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_run_manifest(
        out_dir,
        mode="synthetic",
        synthetic_summary=summary,
        real_summary=None,
    )
    return summary


def render_real_clips(
    out_dir: Path,
    *,
    frame_count: int,
    token_budget: int | None,
    allow_missing: bool,
) -> dict[str, object]:
    summaries: list[dict[str, object]] = []
    missing: list[str] = []
    for clip in REAL_CLIPS:
        if not clip.video_path.exists():
            missing.append(str(clip.video_path))
            continue
        summaries.append(
            _render_real_clip(
                clip,
                out_dir=out_dir,
                frame_count=frame_count,
                token_budget=token_budget,
            )
        )
    payload: dict[str, object] = {
        "mode": "real",
        "frame_count": frame_count,
        "requested_token_budget": token_budget,
        "clips": summaries,
        "missing_sources": missing,
        "score_sources": [source.value for source in REAL_SCORE_SOURCES],
        "residual_extractor": "pyav_motion_compensated_reconstructed_y_proxy",
        "artifact_schema": "onevision_vlmaxxing_real_video_v1",
        "projection_geometry": PROJECTION_GEOMETRY,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    status_path = out_dir / "onevision_real_video_status.json"
    status_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_run_manifest(
        out_dir,
        mode="real",
        synthetic_summary=None,
        real_summary=payload,
    )
    if missing and not allow_missing:
        raise FileNotFoundError(
            "missing raw source videos for real OneVision visualization: " + ", ".join(missing)
        )
    return payload


def _render_real_clip(
    clip: ClipSpec,
    *,
    out_dir: Path,
    frame_count: int,
    token_budget: int | None,
) -> dict[str, object]:
    from codec_through.codec.h264_metadata import H264MetadataExtractor
    from codec_through.video_decode import _count_frames, decode_uniform_frames

    if frame_count <= 0:
        raise ValueError("frame_count must be positive")
    window_frames = _count_frames(
        clip.video_path,
        start_seconds=clip.start_seconds,
        end_seconds=clip.end_seconds,
    )
    if window_frames < frame_count:
        raise ValueError(
            f"{clip.name} has only {window_frames} frames in the requested window, "
            f"less than frame_count={frame_count}"
        )
    fps = _video_fps(clip.video_path)
    start_index = int(round(clip.start_seconds * fps))
    sampled_rel = sparse_sample_indices(window_frames, frame_count)
    sampled_abs = [start_index + index for index in sampled_rel]

    extractor = H264MetadataExtractor(clip.video_path, max_frames=max(sampled_abs) + 1)
    score_by_source: dict[CodecScoreSource, dict[int, np.ndarray]] = {
        source: {} for source in REAL_SCORE_SOURCES
    }
    gradient_by_abs_index: dict[int, np.ndarray] = {}
    active_box: tuple[int, int, int, int] | None = None
    sampled_set = set(sampled_abs)
    for frame_metadata in extractor.iter_frames():
        if frame_metadata.index not in sampled_set:
            continue
        if active_box is None:
            active_box = _active_box_for_canvas(
                frame_metadata.width,
                frame_metadata.height,
                canvas_size=CANVAS_SIZE,
            )
        for source in REAL_SCORE_SOURCES:
            score_by_source[source][frame_metadata.index] = (
                project_macroblock_metadata_to_token_grid(
                    frame_metadata.macroblocks,
                    source=source,
                    macroblock_size=frame_metadata.mb_size,
                    frame_width=frame_metadata.width,
                    frame_height=frame_metadata.height,
                    canvas_size=CANVAS_SIZE,
                    active_box=active_box,
                    token_block=TOKEN_BLOCK,
                    normalize_inputs=True,
                )
            )
        if frame_metadata.y_plane is not None:
            gradient_by_abs_index[frame_metadata.index] = _project_y_gradient_proxy_to_token_grid(
                frame_metadata.y_plane,
                canvas_size=CANVAS_SIZE,
                active_box=active_box,
                token_block=TOKEN_BLOCK,
            )
    missing_samples = [
        index
        for index in sampled_abs
        if any(index not in source_scores for source_scores in score_by_source.values())
    ]
    if missing_samples:
        raise ValueError(f"{clip.name} missing sampled metadata frames: {missing_samples}")
    if active_box is None:
        raise ValueError(f"{clip.name} produced no active video geometry")
    score_volumes = {
        source: np.stack(
            [score_by_source[source][index] for index in sampled_abs],
            axis=0,
        ).astype(np.float32)
        for source in REAL_SCORE_SOURCES
    }
    gradient_volume = np.stack(
        [
            gradient_by_abs_index.get(
                index,
                np.zeros_like(score_volumes[CodecScoreSource.FUSED][0]),
            )
            for index in sampled_abs
        ],
        axis=0,
    ).astype(np.float32)
    score_volume = score_volumes[CodecScoreSource.FUSED]
    effective_budget = _effective_token_budget(score_volume, requested=token_budget)

    config = PatchificationConfig(token_budget=effective_budget, anchor_frames=(0,))
    patches = select_visible_patches(score_volume, config=config)
    counts = count_tokens_by_frame(patches, total_frames=frame_count)
    coverage = temporal_coverage(patches, total_frames=frame_count)
    bias = spatial_bias(patches, grid_shape=score_volume.shape[1:])
    selected_mask = _selected_patch_mask(
        patches,
        volume_shape=score_volume.shape,
    )
    starvation_rows = _starvation_metric_rows(
        score_volume=score_volume,
        gradient_volume=gradient_volume,
        selected_mask=selected_mask,
    )

    clip_dir = out_dir / clip.name
    clip_dir.mkdir(parents=True, exist_ok=True)
    image_path = clip_dir / "token_timeline.png"
    _draw_real_clip_summary(
        image_path,
        clip=clip,
        counts=counts,
        patches=patches,
        grid_shape=score_volume.shape[1:],
        token_budget=effective_budget,
        coverage=coverage,
        bias=bias,
    )
    selected_contact_sheet_path = clip_dir / "selected_overlay_contact_sheet.png"
    frames = decode_uniform_frames(
        clip.video_path,
        frame_count,
        start_seconds=clip.start_seconds,
        end_seconds=clip.end_seconds,
    )
    _draw_selected_overlay_contact_sheet(
        selected_contact_sheet_path,
        clip=clip,
        frames=frames,
        active_box=active_box,
        counts=counts,
        patches=patches,
        grid_shape=score_volume.shape[1:],
    )
    starvation_contact_sheet_path = clip_dir / "starvation_summary.png"
    _draw_starvation_summary(
        starvation_contact_sheet_path,
        clip=clip,
        starvation_rows=starvation_rows,
    )
    visible_indices_path = clip_dir / "visible_indices.npy"
    np.save(visible_indices_path, visible_indices_array(patches))
    score_volume_path = clip_dir / "score_volumes.npz"
    np.savez_compressed(
        score_volume_path,
        motion=score_volumes[CodecScoreSource.MOTION],
        residual=score_volumes[CodecScoreSource.RESIDUAL],
        fused=score_volumes[CodecScoreSource.FUSED],
        y_gradient_proxy=gradient_volume,
        selected_mask=selected_mask,
    )
    selected_jsonl_path = clip_dir / "selected_patches.jsonl"
    _write_selected_patches_jsonl(selected_jsonl_path, patches)
    token_allocation_path = clip_dir / "token_allocation.csv"
    _write_token_allocation_csv(token_allocation_path, counts)
    starvation_path = clip_dir / "starvation_metrics.csv"
    _write_csv_rows(starvation_path, starvation_rows)
    starvation_summary = _starvation_summary(starvation_rows)
    summary = {
        "clip": clip.name,
        "video_path": str(clip.video_path),
        "window_seconds": [clip.start_seconds, clip.end_seconds],
        "frame_count": frame_count,
        "sampled_relative_frames": sampled_rel,
        "sampled_absolute_frames": sampled_abs,
        "requested_token_budget": token_budget,
        "token_budget": effective_budget,
        "tokens_by_sampled_frame": counts.tolist(),
        "grid_shape": [int(score_volume.shape[1]), int(score_volume.shape[2])],
        "projection_geometry": PROJECTION_GEOMETRY,
        "artifacts": {
            "allocation_summary": str(clip_dir / "allocation_summary.json"),
            "token_timeline": str(image_path),
            "selected_overlay_contact_sheet": str(selected_contact_sheet_path),
            "starvation_summary": str(starvation_contact_sheet_path),
            "visible_indices": str(visible_indices_path),
            "selected_patches_jsonl": str(selected_jsonl_path),
            "score_volumes": str(score_volume_path),
            "token_allocation": str(token_allocation_path),
            "starvation_metrics": str(starvation_path),
        },
        "score_source": "fused",
        "score_units": codec_score_units(CodecScoreSource.FUSED),
        "residual_extractor": "pyav_motion_compensated_reconstructed_y_proxy",
        "temporal_coverage": {
            "observed_frames": coverage.observed_frames,
            "observed_fraction": coverage.observed_fraction,
            "max_gap": coverage.max_gap,
            "mean_gap": coverage.mean_gap,
            "entropy_bits": coverage.entropy_bits,
        },
        "spatial_bias": {
            "center_fraction": bias.center_fraction,
            "boundary_fraction": bias.boundary_fraction,
            "mean_center_distance": bias.mean_center_distance,
            "entropy_bits": bias.entropy_bits,
        },
        "starvation_summary": starvation_summary,
    }
    (clip_dir / "allocation_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def _draw_real_clip_summary(
    image_path: Path,
    *,
    clip: ClipSpec,
    counts: np.ndarray,
    patches: list[VisiblePatch],
    grid_shape: tuple[int, int],
    token_budget: int,
    coverage: TemporalCoverage,
    bias: SpatialBias,
) -> None:
    image = Image.new("RGB", (1400, 820), LIGHT_BG)
    draw = ImageDraw.Draw(image)
    draw.text((42, 34), f"OneVision-style allocation: {clip.name}", fill=DARK, font=title_font())
    draw.text(
        (42, 70),
        "CPU H.264 metadata proxy: fused motion/residual scores. "
        "This is planner evidence, not a speed claim.",
        fill=(74, 81, 93),
        font=body_font(),
    )
    draw_timeline(draw, (58, 145), counts=counts, color=ORANGE, max_count=max(1, int(counts.max())))
    draw.text((58, 260), "Token allocation over sampled frames", fill=TEXT, font=body_font())

    selected_frames = _representative_patch_frames(patches, total_frames=len(counts))
    x_offsets = [70, 470, 870]
    for x_offset, frame_index in zip(x_offsets, selected_frames, strict=False):
        frame_patches = [patch for patch in patches if patch.frame == frame_index]
        fills = {
            (patch.row, patch.col): BLUE if patch.source == "anchor" else ORANGE
            for patch in frame_patches
        }
        draw.text(
            (x_offset, 330),
            f"sample {frame_index}: {len(frame_patches)} tokens",
            fill=TEXT,
            font=body_font(),
        )
        draw_scaled_grid(draw, (x_offset, 365), grid_shape=grid_shape, fills=fills)

    draw.text((58, 700), f"Budget: {token_budget} tokens", fill=TEXT, font=body_font())
    draw.text(
        (300, 700),
        f"Observed sampled frames: {coverage.observed_frames}/{len(counts)}",
        fill=TEXT,
        font=body_font(),
    )
    draw.text(
        (650, 700),
        f"Center share: {bias.center_fraction:.2f}",
        fill=TEXT,
        font=body_font(),
    )
    draw.text(
        (910, 700),
        f"Boundary share: {bias.boundary_fraction:.2f}",
        fill=TEXT,
        font=body_font(),
    )
    image.save(image_path)


def _draw_selected_overlay_contact_sheet(
    image_path: Path,
    *,
    clip: ClipSpec,
    frames: list[Image.Image],
    active_box: tuple[int, int, int, int],
    counts: np.ndarray,
    patches: list[VisiblePatch],
    grid_shape: tuple[int, int],
) -> None:
    selected_frames = _representative_patch_frames(patches, total_frames=len(counts))
    image = Image.new("RGB", (1400, 720), LIGHT_BG)
    draw = ImageDraw.Draw(image)
    draw.text((42, 34), f"Selected-patch overlays: {clip.name}", fill=DARK, font=title_font())
    draw.text(
        (42, 70),
        "Orange cells are codec-selected patches; blue cells are anchor-context patches.",
        fill=(74, 81, 93),
        font=body_font(),
    )
    x_offsets = [58, 486, 914]
    for x_offset, frame_index in zip(x_offsets, selected_frames, strict=False):
        canvas = _letterbox_frame(
            frames[frame_index],
            canvas_size=CANVAS_SIZE,
            active_box=active_box,
        )
        overlay = canvas.convert("RGBA")
        layer = Image.new("RGBA", overlay.size, (0, 0, 0, 0))
        layer_draw = ImageDraw.Draw(layer)
        for patch in patches:
            if patch.frame != frame_index:
                continue
            left = patch.col * TOKEN_BLOCK
            top = patch.row * TOKEN_BLOCK
            right = min(CANVAS_SIZE, left + TOKEN_BLOCK)
            bottom = min(CANVAS_SIZE, top + TOKEN_BLOCK)
            color = (54, 107, 196, 90) if patch.source == "anchor" else (226, 135, 46, 150)
            outline = (54, 107, 196, 230) if patch.source == "anchor" else (226, 135, 46, 255)
            layer_draw.rectangle((left, top, right, bottom), fill=color, outline=outline, width=2)
        layer_draw.rectangle(active_box, outline=(30, 34, 42, 220), width=2)
        overlay = Image.alpha_composite(overlay, layer)
        thumb = overlay.convert("RGB").resize((360, 360), Image.Resampling.LANCZOS)
        image.paste(thumb, (x_offset, 150))
        draw.text(
            (x_offset, 530),
            f"sample {frame_index}: {int(counts[frame_index])} / {grid_shape[0] * grid_shape[1]}",
            fill=TEXT,
            font=body_font(),
        )
    image.save(image_path)


def _letterbox_frame(
    frame: Image.Image,
    *,
    canvas_size: int,
    active_box: tuple[int, int, int, int],
) -> Image.Image:
    if canvas_size <= 0:
        raise ValueError("canvas_size must be positive")
    canvas = Image.new("RGB", (canvas_size, canvas_size), (0, 0, 0))
    left, top, right, bottom = active_box
    working = frame.convert("RGB").resize((right - left, bottom - top), Image.Resampling.LANCZOS)
    canvas.paste(working, (left, top))
    return canvas


def draw_scaled_grid(
    draw: ImageDraw.ImageDraw,
    origin: tuple[int, int],
    *,
    grid_shape: tuple[int, int],
    fills: dict[tuple[int, int], tuple[int, int, int]],
) -> None:
    rows, cols = grid_shape
    if rows <= 0 or cols <= 0:
        raise ValueError("grid_shape must be positive")
    cell = max(4, min(12, 260 // max(rows, cols)))
    gap = 1
    x0, y0 = origin
    for row in range(rows):
        for col in range(cols):
            left = x0 + col * (cell + gap)
            top = y0 + row * (cell + gap)
            fill = fills.get((row, col), (236, 239, 243))
            draw.rectangle((left, top, left + cell, top + cell), fill=fill, outline=(218, 222, 228))


def _effective_token_budget(
    score_volume: np.ndarray,
    *,
    requested: int | None,
) -> int:
    if score_volume.ndim != 3:
        raise ValueError("score_volume must be 3D")
    frames, rows, cols = score_volume.shape
    anchor_tokens = rows * cols
    dense_tokens = frames * anchor_tokens
    if requested is not None:
        if requested < anchor_tokens:
            raise ValueError(
                f"token budget {requested} is smaller than the first anchor frame "
                f"({anchor_tokens} tokens)"
            )
        return min(requested, dense_tokens)
    return min(dense_tokens, max(anchor_tokens + 1, int(round(dense_tokens * 0.125))))


def _selected_patch_mask(
    patches: list[VisiblePatch],
    *,
    volume_shape: tuple[int, int, int],
) -> np.ndarray:
    mask = np.zeros(volume_shape, dtype=bool)
    for patch in patches:
        mask[patch.frame, patch.row, patch.col] = True
    return mask


def _project_y_gradient_proxy_to_token_grid(
    y_plane: np.ndarray,
    *,
    canvas_size: int,
    active_box: tuple[int, int, int, int],
    token_block: int,
) -> np.ndarray:
    if y_plane.ndim != 2:
        raise ValueError("y_plane must be 2D")
    y = np.asarray(y_plane, dtype=np.float32)
    grad = np.zeros_like(y, dtype=np.float32)
    grad[:, 1:] += np.abs(y[:, 1:] - y[:, :-1])
    grad[1:, :] += np.abs(y[1:, :] - y[:-1, :])
    left, top, right, bottom = active_box
    resized = Image.fromarray(grad, mode="F").resize(
        (right - left, bottom - top),
        Image.Resampling.BICUBIC,
    )
    canvas = np.zeros((canvas_size, canvas_size), dtype=np.float32)
    canvas[top:bottom, left:right] = np.asarray(resized, dtype=np.float32)
    return mean_pool_blocks(canvas, block_size=token_block)


def _starvation_metric_rows(
    *,
    score_volume: np.ndarray,
    gradient_volume: np.ndarray,
    selected_mask: np.ndarray,
) -> list[dict[str, object]]:
    if score_volume.shape != selected_mask.shape or gradient_volume.shape != score_volume.shape:
        raise ValueError("score, gradient, and selected volumes must have the same shape")
    rows_out: list[dict[str, object]] = []
    _, rows, cols = score_volume.shape
    center_mask = _center_region_mask(rows, cols)
    boundary_mask = _boundary_region_mask(rows, cols)
    for frame_index in range(score_volume.shape[0]):
        score_grid = score_volume[frame_index]
        selected_grid = selected_mask[frame_index]
        regions = {
            "center": center_mask,
            "boundary": boundary_mask,
            "ocr_edge_proxy_top15": _top_fraction_mask(gradient_volume[frame_index], share=0.15),
        }
        for region_name, region_mask in regions.items():
            rows_out.append(
                _starvation_row(
                    frame_index=frame_index,
                    region=region_name,
                    score_grid=score_grid,
                    selected_grid=selected_grid,
                    region_mask=region_mask,
                )
            )
    return rows_out


def _starvation_row(
    *,
    frame_index: int,
    region: str,
    score_grid: np.ndarray,
    selected_grid: np.ndarray,
    region_mask: np.ndarray,
) -> dict[str, object]:
    score_total = float(score_grid.sum())
    selected_total = int(selected_grid.sum())
    score_mass_share = (
        float(score_grid[region_mask].sum()) / score_total if score_total > 0.0 else 0.0
    )
    selected_token_share = (
        float(selected_grid[region_mask].sum()) / float(selected_total)
        if selected_total > 0
        else 0.0
    )
    return {
        "frame": int(frame_index),
        "region": region,
        "score_mass_share": score_mass_share,
        "selected_token_share": selected_token_share,
        "starvation_deficit": score_mass_share - selected_token_share,
        "selected_tokens": int(selected_grid[region_mask].sum()),
        "region_tokens": int(region_mask.sum()),
    }


def _center_region_mask(rows: int, cols: int) -> np.ndarray:
    mask = np.zeros((rows, cols), dtype=bool)
    row_lo = rows // 3
    row_hi = rows - row_lo
    col_lo = cols // 3
    col_hi = cols - col_lo
    mask[row_lo:row_hi, col_lo:col_hi] = True
    return mask


def _boundary_region_mask(rows: int, cols: int) -> np.ndarray:
    mask = np.zeros((rows, cols), dtype=bool)
    band = max(1, min(rows, cols) // 5)
    mask[:band, :] = True
    mask[-band:, :] = True
    mask[:, :band] = True
    mask[:, -band:] = True
    return mask


def _top_fraction_mask(values: np.ndarray, *, share: float) -> np.ndarray:
    if values.ndim != 2:
        raise ValueError("values must be 2D")
    if not (0.0 < share <= 1.0):
        raise ValueError("share must lie in (0, 1]")
    if not np.any(values > 0.0):
        return np.zeros(values.shape, dtype=bool)
    threshold = float(np.quantile(values.reshape(-1), 1.0 - share))
    return (values >= threshold) & (values > 0.0)


def _starvation_summary(rows: list[dict[str, object]]) -> dict[str, float]:
    summary: dict[str, float] = {}
    regions = sorted({str(row["region"]) for row in rows})
    for region in regions:
        deficits = [
            float(row["starvation_deficit"]) for row in rows if str(row["region"]) == region
        ]
        summary[f"{region}_mean_deficit"] = float(np.mean(deficits)) if deficits else 0.0
        summary[f"{region}_max_deficit"] = float(np.max(deficits)) if deficits else 0.0
    return summary


def _write_selected_patches_jsonl(path: Path, patches: list[VisiblePatch]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for patch in patches:
            handle.write(
                json.dumps(
                    {
                        "frame": patch.frame,
                        "row": patch.row,
                        "col": patch.col,
                        "score": patch.score,
                        "source": patch.source,
                    },
                    sort_keys=True,
                )
                + "\n"
            )


def _write_token_allocation_csv(path: Path, counts: np.ndarray) -> None:
    rows = [
        {"sampled_frame": int(frame_index), "selected_tokens": int(count)}
        for frame_index, count in enumerate(counts.tolist())
    ]
    _write_csv_rows(path, rows)


def _write_csv_rows(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _draw_starvation_summary(
    image_path: Path,
    *,
    clip: ClipSpec,
    starvation_rows: list[dict[str, object]],
) -> None:
    summary = _starvation_summary(starvation_rows)
    image = Image.new("RGB", (900, 460), LIGHT_BG)
    draw = ImageDraw.Draw(image)
    draw.text((36, 32), f"Spatial starvation audit: {clip.name}", fill=DARK, font=title_font())
    draw.text(
        (36, 72),
        "Positive deficit means score mass exceeded selected-token share.",
        fill=(74, 81, 93),
        font=body_font(),
    )
    y = 130
    for key, value in sorted(summary.items()):
        draw.text((54, y), key, fill=TEXT, font=body_font())
        bar_width = max(0, min(420, int(420 * value)))
        draw.rectangle((360, y + 3, 360 + bar_width, y + 18), fill=RED if value > 0 else GREEN)
        draw.text((800, y), f"{value:.3f}", fill=TEXT, font=body_font())
        y += 38
    image.save(image_path)


def _write_run_manifest(
    out_dir: Path,
    *,
    mode: str,
    synthetic_summary: dict[str, object] | None,
    real_summary: dict[str, object] | None,
) -> None:
    payload = {
        "schema": "onevision_vlmaxxing_visual_manifest_v1",
        "mode": mode,
        "synthetic": synthetic_summary,
        "real": real_summary,
        "notes": [
            "Real-video artifacts use repo-local H.264 motion/residual proxies.",
            "The visual budget is not an end-to-end latency or accuracy claim.",
            "The fused score source is OneVision-style, not upstream cv_reader residual parity.",
        ],
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "onevision_vlmaxxing_manifest.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _representative_patch_frames(
    patches: list[VisiblePatch],
    *,
    total_frames: int,
) -> list[int]:
    counts = count_tokens_by_frame(patches, total_frames=total_frames)
    observed = [int(index) for index in np.flatnonzero(counts)]
    if not observed:
        return [0, total_frames // 2, total_frames - 1]
    middle = observed[len(observed) // 2]
    return [observed[0], middle, observed[-1]]


def _active_box_for_canvas(
    frame_width: int,
    frame_height: int,
    *,
    canvas_size: int,
) -> tuple[int, int, int, int]:
    if frame_width <= 0 or frame_height <= 0 or canvas_size <= 0:
        raise ValueError("frame dimensions and canvas_size must be positive")
    scale = min(canvas_size / frame_width, canvas_size / frame_height)
    active_width = max(1, int(round(frame_width * scale)))
    active_height = max(1, int(round(frame_height * scale)))
    left = (canvas_size - active_width) // 2
    top = (canvas_size - active_height) // 2
    return (left, top, left + active_width, top + active_height)


def _video_fps(video_path: Path) -> float:
    import av

    with av.open(video_path) as container:
        stream = container.streams.video[0]
        rate = stream.average_rate or stream.base_rate
        if rate is None:
            raise ValueError(f"could not determine frame rate for {video_path}")
        return float(rate)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument(
        "--mode",
        choices=("synthetic", "real", "auto"),
        default="auto",
        help="Render synthetic fallback, real-video allocation, or both when assets exist.",
    )
    parser.add_argument("--frame-count", type=int, default=16)
    parser.add_argument(
        "--token-budget",
        type=int,
        default=None,
        help="Real-video token budget. Defaults to 12.5% of dense sampled tokens.",
    )
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Do not fail real/auto mode when raw benchmark videos are absent.",
    )
    args = parser.parse_args()
    if args.mode == "synthetic":
        summary = render_synthetic(args.out_dir)
        print(summary["image"])
    elif args.mode == "real":
        summary = render_real_clips(
            args.out_dir,
            frame_count=args.frame_count,
            token_budget=args.token_budget,
            allow_missing=bool(args.allow_missing),
        )
        print(args.out_dir / "onevision_real_video_status.json")
    else:
        synthetic = render_synthetic(args.out_dir)
        real = render_real_clips(
            args.out_dir,
            frame_count=args.frame_count,
            token_budget=args.token_budget,
            allow_missing=True,
        )
        _write_run_manifest(
            args.out_dir,
            mode="auto",
            synthetic_summary=synthetic,
            real_summary=real,
        )
        print(synthetic["image"])
        print(args.out_dir / "onevision_real_video_status.json")


if __name__ == "__main__":
    main()
