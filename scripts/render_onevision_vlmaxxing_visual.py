#!/usr/bin/env python3
"""Render a CPU-only OneVision + VLMaxxing explainer figure.

The default path uses synthetic score volumes so the visualization can be
checked without benchmark videos, PyAV, MLX, or model inference.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from codec_through.codec.onevision_patchification import (
    PatchificationConfig,
    VisiblePatch,
    count_tokens_by_frame,
    fuse_motion_residual,
    select_visible_patches,
    spatial_bias,
    temporal_coverage,
)

DEFAULT_OUT_DIR = Path("research/experiments/2026/artifacts/onevision_vlmaxxing_visuals")
GRID_SHAPE = (8, 8)
FRAMES = 16
CELL = 20
GAP = 2

BLUE = (54, 107, 196)
ORANGE = (226, 135, 46)
GREEN = (54, 150, 92)
RED = (198, 70, 70)
GRAY = (155, 160, 166)
DARK = (35, 39, 47)
LIGHT_BG = (247, 248, 250)
PANEL_BG = (255, 255, 255)
TEXT = (28, 32, 38)


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


def render(out_dir: Path) -> dict[str, object]:
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
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()
    summary = render(args.out_dir)
    print(summary["image"])


if __name__ == "__main__":
    main()
