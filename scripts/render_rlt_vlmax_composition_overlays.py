#!/usr/bin/env python3
"""Render RLT/VLMaxxing composition overlays on the three VLMaxxing clips.

The renderer is an explanatory artifact, but the masks are computed by the same
local primitives used by the experiments:

* VLMaxxing fresh/reuse blocks come from the checked Fig. 1 routing policy.
* RLT admission tokens come from :mod:`codec_through.rlt_masks`.
* The composition pane is the pixel-domain union of those two "must process"
  signals on the displayed active crop.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

from codec_through.rlt_masks import RLTMaskConfig, compute_rlt_keep_mask_from_frames, mask_summary

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

from render_codec_through_video_overlays import (  # noqa: E402
    CLIPS,
    FAINT,
    INK,
    MUTED,
    ORANGE,
    ORANGE_DARK,
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
            "rlt_admit_fraction": float(rlt_active.sum() / total),
            "vlmax_fresh_fraction": float(vl_fresh.sum() / total),
            "combined_refresh_fraction": float(union.sum() / total),
            "overlap_fraction": float(overlap.sum() / total),
        },
    )


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
    if frame_count % RLT_CONFIG.tubelet_size:
        frame_count -= 1
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
        subtitle=f"run-length keep mask, keep={rlt_keep_rate:.1%}",
    )
    _paste_pane(
        canvas,
        combined_overlay,
        PANE_BOXES["combined"],
        title="conservative composition",
        subtitle=f"union refresh/admit={stats['combined_refresh_fraction']:.1%}",
    )
    _draw_badge(canvas, f"RLT {stats['rlt_admit_fraction']:.0%}", (40, 842), BLUE_DARK)
    _draw_badge(canvas, f"VL fresh {stats['vlmax_fresh_fraction']:.0%}", (190, 842), ORANGE_DARK)
    _draw_badge(canvas, f"overlap {stats['overlap_fraction']:.0%}", (385, 842), PURPLE)
    return canvas


def render_clip(spec: Any, *, fps: float, out_dir: Path) -> dict[str, Any]:
    times, padded_frames, active_boxes = _decode(spec, fps)
    transitions = transition_details(padded_frames, active_boxes)
    rlt_result = compute_rlt_keep_mask_from_frames(padded_frames, config=RLT_CONFIG)
    frames: list[Image.Image] = []
    combined_stats: list[dict[str, float]] = []

    for idx, (padded, active_box) in enumerate(zip(padded_frames, active_boxes, strict=True)):
        crop = active_crop(padded, active_box).convert("RGB")
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

    out_dir.mkdir(parents=True, exist_ok=True)
    video_path = out_dir / f"{spec.key}_rlt_vlmax_composition.mp4"
    write_mp4(frames, video_path, fps=fps)
    thumb_path = out_dir / "thumbnails" / f"{video_path.stem}.png"
    thumbnail(frames[min(len(frames) - 1, max(0, len(frames) // 2))], thumb_path)
    mean_stats = {
        key: float(np.mean([stats[key] for stats in combined_stats])) for key in combined_stats[0]
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
        "fps": fps,
        "rlt_mask_summary": mask_summary(rlt_result),
        "mean_composition_stats": mean_stats,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fps", type=float, default=12.0)
    parser.add_argument("--out-dir", type=Path, default=OUT_ROOT)
    args = parser.parse_args()
    if args.fps <= 0.0:
        raise SystemExit("--fps must be positive")

    records = [render_clip(spec, fps=args.fps, out_dir=args.out_dir) for spec in CLIPS]
    manifest = {
        "schema_version": "rlt_vlmax_composition_overlay_v1",
        "purpose": (
            "Scientifically grounded visualization of the RLT/VLMaxxing composition "
            "hypothesis on the same three videos used by the VLMaxxing overlay reel."
        ),
        "accuracy_contract": {
            "vlmaxxing": (
                "Fresh/reuse boxes are recomputed with the existing Fig. 1 Qwen routing-budget "
                "policy, not hand annotated."
            ),
            "rlt": (
                "RLT panes are computed with codec_through.rlt_masks on the same square-padded "
                "frames used by Track A benchmark decoding, using tau=0.1, tubelet_size=2, "
                "224x224 ImageNet-normalized input, and patch_size=16."
            ),
            "combined": (
                "The combined pane shows the conservative pixel-domain union of VLMaxxing fresh "
                "regions and RLT representative-token regions. It visualizes the preregistered "
                "composition candidate, not an already-earned speedup claim."
            ),
        },
        "clips": records,
    }
    manifest_path = args.out_dir / "rlt_vlmax_composition_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"manifest": str(manifest_path), "clips": records}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
