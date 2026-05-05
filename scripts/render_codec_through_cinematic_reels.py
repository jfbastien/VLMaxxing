#!/usr/bin/env python3
"""Render cinematic exploratory codec-through reels.

These are communication drafts, not paper-build assets.  They reuse the exact
Qwen routing-budget masks from ``render_codec_through_video_overlays.py`` and
change only pacing, camera, typography, and scene composition.
"""

from __future__ import annotations

import argparse
import json
import math
import struct
import subprocess
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from render_codec_through_video_overlays import (
    CLIPS,
    FAINT,
    GREEN,
    INK,
    MUTED,
    ORANGE,
    PAPER_AUTHORS,
    PAPER_SUBTITLE,
    PAPER_TITLE,
    PURPLE,
    RED,
    REPO_ROOT,
    WHITE,
    ClipSpec,
    active_crop,
    decode_clip,
    decode_frames_at_times,
    draw_text_supersampled,
    fit_image,
    font,
    load_story_values,
    overlay_boxes,
    paper_font,
    pct_pair_from_stats,
    render_title_card,
    safe_rel,
    square_pad_frame,
    text_size,
    thumbnail,
    transition_details,
    transition_percentages,
    write_mp4,
)

OUT_ROOT = (
    REPO_ROOT
    / "research"
    / "experiments"
    / "2026"
    / "artifacts"
    / "codec_through_cinematic_reels_exploratory"
)

FPS = 24.0
SIZE = (1920, 1080)
ANCHOR_VIDEO_BOX = (70, 138, 1230, 790)
ANCHOR_PANEL_BOX = (1280, 138, 1845, 790)
TEASER_VIDEO_BOX = (70, 126, 1230, 820)
TEASER_PANEL_BOX = (1280, 126, 1845, 820)
NAVY = (6, 10, 24)
NAVY_2 = (10, 18, 38)
CARD = (248, 250, 252)
WARM = (250, 247, 239)
WARM_DARK = (40, 34, 26)
GOLD = (245, 158, 11)
BLUE = (96, 165, 250)
SOFT_ORANGE = (255, 237, 213)
SOFT_GREEN = (220, 252, 231)
DIM_WHITE = (226, 232, 240)


FONTS = {
    "paper_title": paper_font(92),
    "paper_subtitle": paper_font(38),
    "paper_author": paper_font(24),
    "display": font(86, bold=True),
    "hero": font(68, bold=True),
    "title": font(46, bold=True),
    "h": font(34, bold=True),
    "body": font(26),
    "small": font(21),
    "tiny": font(17),
    "number": font(78, bold=True),
    "number_small": font(48, bold=True),
}


@dataclass(frozen=True)
class ClipData:
    spec: ClipSpec
    times: list[float]
    crops: list[Image.Image]
    details: list[dict[str, Any]]


def draw_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    *,
    fill: tuple[int, int, int],
    fnt: ImageFont.ImageFont,
) -> None:
    draw.text(xy, text, fill=fill, font=fnt)


def centered_text(
    draw: ImageDraw.ImageDraw,
    y: int,
    text: str,
    *,
    fill: tuple[int, int, int],
    fnt: ImageFont.ImageFont,
    width: int = SIZE[0],
) -> None:
    tw, _ = text_size(draw, text, fnt)
    draw.text(((width - tw) // 2, y), text, fill=fill, font=fnt)


def centered_text_in_box(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    *,
    fill: tuple[int, int, int],
    fnt: ImageFont.ImageFont,
    y_frac: float = 0.5,
) -> None:
    x0, y0, x1, y1 = box
    tw, th = text_size(draw, text, fnt)
    x = x0 + (x1 - x0 - tw) // 2
    y = y0 + round((y1 - y0) * y_frac) - th // 2
    draw.text((x, y), text, fill=fill, font=fnt)


def centered_text_supersampled(
    canvas: Image.Image,
    y: int,
    text: str,
    *,
    fill: tuple[int, int, int],
    fnt: ImageFont.ImageFont,
    width: int = SIZE[0],
) -> None:
    draw = ImageDraw.Draw(canvas)
    tw, _ = text_size(draw, text, fnt)
    draw_text_supersampled(canvas, ((width - tw) // 2, y), text, fill=fill, fnt=fnt)


def rounded_rect(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    *,
    fill: tuple[int, int, int],
    outline: tuple[int, int, int] | None = None,
    radius: int = 24,
    width: int = 2,
) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def alpha_composite(base: Image.Image, overlay: Image.Image, alpha: float) -> Image.Image:
    if alpha <= 0:
        return base
    if alpha >= 1:
        return overlay
    return Image.blend(base.convert("RGB"), overlay.convert("RGB"), alpha)


def fade_in(frames: list[Image.Image], *, color: tuple[int, int, int] = NAVY) -> list[Image.Image]:
    if not frames:
        return frames
    out: list[Image.Image] = []
    blank = Image.new("RGB", frames[0].size, color)
    n = min(12, len(frames))
    for idx, frame in enumerate(frames):
        if idx < n:
            out.append(alpha_composite(blank, frame, idx / max(1, n - 1)))
        else:
            out.append(frame)
    return out


def fade_out(frames: list[Image.Image], *, color: tuple[int, int, int] = NAVY) -> list[Image.Image]:
    if not frames:
        return frames
    out = list(frames)
    blank = Image.new("RGB", frames[0].size, color)
    n = min(12, len(out))
    for idx in range(n):
        pos = len(out) - n + idx
        out[pos] = alpha_composite(out[pos], blank, idx / max(1, n - 1))
    return out


def hold(frame: Image.Image, seconds: float) -> list[Image.Image]:
    return [frame.copy() for _ in range(max(1, round(seconds * FPS)))]


def zoom_image(
    image: Image.Image,
    zoom: float,
    *,
    center: tuple[float, float] = (0.5, 0.5),
) -> Image.Image:
    zoom = max(1.0, zoom)
    if zoom <= 1.001:
        return image.copy()
    crop_w = max(1, round(image.width / zoom))
    crop_h = max(1, round(image.height / zoom))
    cx = int(round(center[0] * image.width))
    cy = int(round(center[1] * image.height))
    x0 = max(0, min(image.width - crop_w, cx - crop_w // 2))
    y0 = max(0, min(image.height - crop_h, cy - crop_h // 2))
    return image.crop((x0, y0, x0 + crop_w, y0 + crop_h)).resize(
        image.size, Image.Resampling.LANCZOS
    )


def fresh_center(transition: dict[str, Any] | None) -> tuple[float, float]:
    if not transition:
        return (0.5, 0.5)
    boxes = transition.get("fresh_boxes", [])
    if not boxes:
        return (0.5, 0.5)
    area_sum = 0.0
    x_sum = 0.0
    y_sum = 0.0
    for x0, y0, x1, y1 in boxes:
        area = max(0.0001, (x1 - x0) * (y1 - y0))
        area_sum += area
        x_sum += area * (x0 + x1) * 0.5
        y_sum += area * (y0 + y1) * 0.5
    return (x_sum / area_sum, y_sum / area_sum)


def fit_on_canvas(
    canvas: Image.Image,
    image: Image.Image,
    box: tuple[int, int, int, int],
    *,
    border: tuple[int, int, int] | None = None,
    shadow: bool = False,
) -> tuple[int, int, int, int]:
    fitted, pos = fit_image(image, box)
    draw = ImageDraw.Draw(canvas)
    if shadow:
        sx0, sy0 = pos[0] + 16, pos[1] + 18
        rounded_rect(
            draw,
            (sx0, sy0, sx0 + fitted.width, sy0 + fitted.height),
            fill=(0, 0, 0),
            radius=10,
        )
        shadow_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow_layer)
        shadow_draw.rounded_rectangle(
            (sx0, sy0, sx0 + fitted.width, sy0 + fitted.height),
            radius=10,
            fill=(0, 0, 0, 70),
        )
        shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(14))
        canvas.paste(shadow_layer.convert("RGB"), (0, 0), shadow_layer)
    canvas.paste(fitted, pos)
    if border is not None:
        draw.rectangle(
            (pos[0], pos[1], pos[0] + fitted.width, pos[1] + fitted.height),
            outline=border,
            width=3,
        )
    return (pos[0], pos[1], pos[0] + fitted.width, pos[1] + fitted.height)


def title_card(theme: str, *, seconds: float = 1.3) -> list[Image.Image]:
    if theme == "dark":
        canvas = Image.new("RGB", SIZE, NAVY)
        centered_text_supersampled(canvas, 352, PAPER_TITLE, fill=WHITE, fnt=FONTS["paper_title"])
        centered_text_supersampled(
            canvas, 445, PAPER_SUBTITLE, fill=DIM_WHITE, fnt=FONTS["paper_subtitle"]
        )
        centered_text_supersampled(
            canvas, 518, PAPER_AUTHORS, fill=(148, 163, 184), fnt=FONTS["paper_author"]
        )
        return fade_in(hold(canvas, seconds), color=NAVY)
    card = render_title_card().resize(SIZE, Image.Resampling.LANCZOS)
    return fade_in(hold(card, seconds), color=WHITE)


def draw_identity_title(
    canvas: Image.Image,
    *,
    theme: str,
    y_offset: int = 0,
    x_offset: int = 0,
) -> tuple[int, int, int, int]:
    draw = ImageDraw.Draw(canvas)
    dark = theme == "dark"
    title_fill = WHITE if dark else INK
    subtitle_fill = DIM_WHITE if dark else MUTED
    title_w, title_h = text_size(draw, PAPER_TITLE, FONTS["paper_title"])
    subtitle_w, _ = text_size(draw, PAPER_SUBTITLE, FONTS["paper_subtitle"])
    authors_w, _ = text_size(draw, PAPER_AUTHORS, FONTS["paper_author"])
    x = (SIZE[0] - title_w) // 2 + x_offset
    y = 318 + y_offset
    draw_text_supersampled(canvas, (x, y), PAPER_TITLE, fill=title_fill, fnt=FONTS["paper_title"])
    draw_text_supersampled(
        canvas,
        ((SIZE[0] - subtitle_w) // 2 + x_offset // 2, y + title_h + 24),
        PAPER_SUBTITLE,
        fill=subtitle_fill,
        fnt=FONTS["paper_subtitle"],
    )
    draw_text_supersampled(
        canvas,
        ((SIZE[0] - authors_w) // 2 + x_offset // 3, y + title_h + 88),
        PAPER_AUTHORS,
        fill=(148, 163, 184) if dark else MUTED,
        fnt=FONTS["paper_author"],
    )
    return (x, y, x + title_w, y + title_h)


def end_card_raw_frame(theme: str, *, progress: float) -> Image.Image:
    bg = NAVY if theme == "dark" else WARM
    canvas = Image.new("RGBA", SIZE, (*bg, 255))
    y_offset = round(-52 * progress)
    x_offset = round(18 * math.sin(progress * math.pi))
    draw_identity_title(
        canvas,
        theme=theme,
        y_offset=y_offset,
        x_offset=x_offset,
    )
    return canvas.convert("RGB")


def end_card(theme: str, *, seconds: float = 1.8) -> list[Image.Image]:
    n = max(1, round(seconds * FPS))
    hold_before = min(round(0.55 * FPS), max(1, n // 4))
    motion_n = min(4, max(1, n - hold_before))
    static = end_card_raw_frame(theme, progress=0.0)
    motion_raw = [
        end_card_raw_frame(theme, progress=idx / max(1, motion_n - 1)) for idx in range(motion_n)
    ]
    frames = [static.copy() for _ in range(hold_before)]
    frames.extend(motion_raw)
    final = motion_raw[-1] if motion_raw else static
    while len(frames) < n:
        frames.append(final.copy())
    return frames[:n]


def anchored_title_raw_frame(*, progress: float) -> Image.Image:
    """Closing title card used inside the fixed video stage."""

    canvas = Image.new("RGBA", SIZE, (*NAVY, 255))
    draw_identity_title(
        canvas,
        theme="dark",
        y_offset=round(-24 * progress),
        x_offset=round(20 * math.sin(progress * math.pi)),
    )
    return canvas.convert("RGB")


def anchored_title_frames(*, seconds: float) -> list[Image.Image]:
    """Generate a moving title card without reusing clip-mask color grammar."""

    n = max(1, round(seconds * FPS))
    hold_before = min(round(0.65 * FPS), max(1, n // 4))
    motion_n = min(12, max(1, n - hold_before))
    static = anchored_title_raw_frame(progress=0.0)
    raw = [anchored_title_raw_frame(progress=idx / max(1, motion_n - 1)) for idx in range(motion_n)]
    frames = [static.copy() for _ in range(hold_before)]
    frames.extend(raw)
    final = raw[-1] if raw else static
    while len(frames) < n:
        frames.append(final.copy())
    return frames[:n]


def generated_title_motion_frames(*, seconds: float) -> list[Image.Image]:
    """Generated title-card motion for the optional synthetic title probe."""

    n = max(1, round(seconds * FPS))
    frames: list[Image.Image] = []
    card_w, card_h = 1280, 210
    bounds = (90, 150, SIZE[0] - 90 - card_w, 900 - card_h)
    for idx in range(n):
        t = idx / FPS
        tri_x = abs(((t * 0.46) % 2.0) - 1.0)
        tri_y = abs(((t * 0.36 + 0.35) % 2.0) - 1.0)
        x = bounds[0] + round((bounds[2] - bounds[0]) * tri_x)
        y = bounds[1] + round((bounds[3] - bounds[1]) * tri_y)
        canvas = Image.new("RGBA", SIZE, (*NAVY, 255))
        card = Image.new("RGBA", (card_w, card_h), (7, 11, 26, 255))
        card_draw = ImageDraw.Draw(card)
        card_draw.rectangle((0, 0, card_w - 1, card_h - 1), outline=WHITE, width=3)
        title_font = paper_font(68)
        subtitle_font = paper_font(29)
        title_w, title_h = text_size(card_draw, PAPER_TITLE, title_font)
        subtitle_w, _ = text_size(card_draw, PAPER_SUBTITLE, subtitle_font)
        card_draw.text(
            ((card_w - title_w) // 2, 42),
            PAPER_TITLE,
            fill=WHITE,
            font=title_font,
        )
        card_draw.text(
            ((card_w - subtitle_w) // 2, 125),
            PAPER_SUBTITLE,
            fill=DIM_WHITE,
            font=subtitle_font,
        )
        canvas.paste(card, (x, y), card)
        frames.append(canvas.convert("RGB"))
    return frames


def planner_details_for_generated_frames(raw_frames: list[Image.Image]) -> list[dict[str, Any]]:
    """Run the same block planner over generated frames."""

    padded_frames: list[Image.Image] = []
    active_boxes: list[tuple[int, int, int, int]] = []
    for frame in raw_frames:
        padded, active_box = square_pad_frame(frame)
        padded_frames.append(padded)
        active_boxes.append(active_box)
    return transition_details(padded_frames, active_boxes)


def apply_planner_fresh_overlay_to_generated_frames(
    raw_frames: list[Image.Image],
    details: list[dict[str, Any]] | None = None,
) -> list[Image.Image]:
    """Apply the same block freshness visualization to generated frames.

    This is used only for the synthetic title-card joke/probe. It is not
    benchmark evidence, but the displayed orange blocks are still produced by
    the same planner path over the generated frames.
    """

    details = details if details is not None else planner_details_for_generated_frames(raw_frames)
    out: list[Image.Image] = []
    for idx, frame in enumerate(raw_frames):
        transition = details[idx - 1] if idx > 0 else None
        overlaid = overlay_boxes(frame, transition, mode="fresh")
        out.append(Image.blend(frame.convert("RGB"), overlaid.convert("RGB"), 0.68))
    return out


def stats_for(details: list[dict[str, Any]], idx: int) -> dict[str, float]:
    if idx <= 0 or idx - 1 >= len(details):
        return transition_percentages(None)
    return transition_percentages(details[idx - 1])


def decode_display_crops(spec: ClipSpec, *, fps: float = 24.0) -> list[Image.Image]:
    n = max(2, int(math.ceil((spec.end_s - spec.start_s) * fps)) + 1)
    times = [spec.start_s + idx / fps for idx in range(n)]
    times = [min(spec.end_s, t) for t in times]
    frames = decode_frames_at_times(spec.video_path, times)
    crops: list[Image.Image] = []
    for frame in frames:
        padded, active_box = square_pad_frame(frame)
        crops.append(active_crop(padded, active_box))
    return crops


def resolve_input_path(path: str | Path) -> Path:
    raw = Path(path)
    return raw if raw.is_absolute() else REPO_ROOT / raw


def resolve_optional_input_path(path: str | Path | None) -> Path | None:
    if path is None or str(path) == "":
        return None
    return resolve_input_path(path)


def clip_spec_from_record(record: dict[str, Any], *, index: int) -> ClipSpec:
    video_path_raw = record.get("video_path") or record.get("source_video")
    if not video_path_raw:
        raise ValueError(f"clip record {index} is missing video_path")
    start_s = float(record.get("start_s", 0.0))
    if "end_s" not in record:
        raise ValueError(f"clip record {index} is missing end_s")
    end_s = float(record["end_s"])
    if end_s <= start_s:
        raise ValueError(f"clip record {index} has end_s <= start_s")
    key = str(record.get("key") or f"custom_{index:02d}")
    video_path = resolve_input_path(video_path_raw)
    return ClipSpec(
        key=key,
        benchmark=str(record.get("benchmark", "custom")),
        item_id=str(record.get("item_id", key)),
        video_id=str(record.get("video_id", video_path.stem)),
        role=str(record.get("role", "custom routing window")),
        video_path=video_path,
        source_jsonl=resolve_optional_input_path(record.get("source_jsonl")),
        start_s=start_s,
        end_s=end_s,
    )


def load_clip_specs_from_manifest(path: Path) -> list[ClipSpec]:
    payload = json.loads(path.read_text())
    records = payload.get("clips", payload if isinstance(payload, list) else None)
    if not isinstance(records, list):
        raise ValueError("clip manifest must be a list or an object with a clips list")
    specs = [clip_spec_from_record(record, index=idx) for idx, record in enumerate(records)]
    if not specs:
        raise ValueError("clip manifest did not contain any clips")
    return specs


def single_clip_spec_from_args(args: argparse.Namespace) -> ClipSpec:
    if args.video_path is None:
        raise ValueError("--video-path is required for direct custom input")
    if args.end_s is None:
        raise ValueError("--end-s is required for direct custom input")
    record = {
        "key": args.key,
        "benchmark": args.benchmark,
        "item_id": args.item_id,
        "video_id": args.video_id,
        "role": args.role,
        "video_path": args.video_path,
        "start_s": args.start_s,
        "end_s": args.end_s,
    }
    return clip_spec_from_record(record, index=0)


def draw_budget_hero(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    stats: dict[str, float],
    *,
    large: bool = False,
    dark: bool = True,
) -> None:
    if not stats["has_transition"]:
        draw_text(draw, (x, y), "no prior frame", fill=DIM_WHITE if dark else MUTED, fnt=FONTS["h"])
        return
    reuse_pct, fresh_pct = pct_pair_from_stats(stats)
    draw_text(
        draw,
        (x, y),
        f"{reuse_pct}% reused",
        fill=(74, 222, 128) if dark else GREEN,
        fnt=FONTS["number" if large else "number_small"],
    )
    draw_text(
        draw,
        (x, y + (80 if large else 52)),
        f"{fresh_pct}% fresh",
        fill=ORANGE,
        fnt=FONTS["number_small" if large else "h"],
    )
    if stats["stale"] > 0.08:
        draw_text(
            draw,
            (x, y + (136 if large else 90)),
            f"age-expired refresh: {stats['stale']:.0%}",
            fill=DIM_WHITE if dark else MUTED,
            fnt=FONTS["small"],
        )


def chapter_tag(draw: ImageDraw.ImageDraw, spec: ClipSpec, *, dark: bool) -> None:
    fill = DIM_WHITE if dark else MUTED
    draw_text(
        draw,
        (70, 990),
        f"{spec.benchmark} {spec.video_id} · {spec.role} · {spec.start_s:.2f}-{spec.end_s:.2f}s",
        fill=fill,
        fnt=FONTS["tiny"],
    )


def raw_frame(
    clip: ClipData,
    idx: int,
    *,
    theme: str,
    label: str,
    zoom: float,
) -> Image.Image:
    dark = theme == "dark"
    bg = NAVY if dark else WARM
    canvas = Image.new("RGB", SIZE, bg)
    draw = ImageDraw.Draw(canvas)
    image = zoom_image(clip.crops[idx], zoom)
    fit_on_canvas(canvas, image, (120, 150, 1800, 880), border=WHITE if dark else INK, shadow=True)
    draw_text(draw, (120, 92), label, fill=WHITE if dark else INK, fnt=FONTS["title"])
    chapter_tag(draw, clip.spec, dark=dark)
    return canvas


def overlay_frame(
    clip: ClipData,
    idx: int,
    *,
    theme: str,
    label: str,
    hero: str | None = None,
    ledger: bool = True,
) -> Image.Image:
    dark = theme == "dark"
    bg = NAVY if dark else WARM
    canvas = Image.new("RGB", SIZE, bg)
    draw = ImageDraw.Draw(canvas)
    transition = clip.details[idx - 1] if idx > 0 else None
    image = overlay_boxes(clip.crops[idx], transition, mode="fresh")
    image = zoom_image(image, 1.04 if transition else 1.0, center=fresh_center(transition))
    fit_on_canvas(canvas, image, (80, 150, 1260, 880), border=WHITE if dark else INK, shadow=True)
    draw_text(draw, (80, 88), label, fill=WHITE if dark else INK, fnt=FONTS["title"])
    stats = stats_for(clip.details, idx)
    if hero is not None:
        draw_text(draw, (1320, 170), hero, fill=WHITE if dark else INK, fnt=FONTS["h"])
    draw_budget_hero(draw, 1320, 250, stats, large=True, dark=dark)
    if ledger and stats["has_transition"]:
        bar_x, bar_y = 1320, 500
        rounded_rect(
            draw,
            (bar_x, bar_y, bar_x + 440, bar_y + 34),
            fill=(15, 23, 42) if dark else WHITE,
            outline=(51, 65, 85) if dark else FAINT,
            radius=10,
        )
        split = int(round(bar_x + 440 * stats["reused"]))
        draw.rectangle((bar_x, bar_y, split, bar_y + 34), fill=(34, 197, 94))
        draw.rectangle((split, bar_y, bar_x + 440, bar_y + 34), fill=ORANGE)
        draw_text(
            draw,
            (1320, 568),
            "orange = fresh visual evidence",
            fill=ORANGE,
            fnt=FONTS["small"],
        )
        draw_text(
            draw,
            (1320, 602),
            "not saliency; not C-PERSIST timing",
            fill=DIM_WHITE if dark else MUTED,
            fnt=FONTS["tiny"],
        )
    chapter_tag(draw, clip.spec, dark=dark)
    return canvas


def rewind_frames(clip: ClipData, idxs: list[int], *, theme: str) -> list[Image.Image]:
    dark = theme == "dark"
    out: list[Image.Image] = []
    for step, idx in enumerate(reversed(idxs)):
        base = raw_frame(clip, idx, theme=theme, label="REWIND", zoom=1.02)
        overlay = Image.new("RGBA", SIZE, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        for y in range(0, SIZE[1], 18):
            od.line((0, y + step % 5, SIZE[0], y + step % 5), fill=(255, 255, 255, 28), width=2)
        for x in range(0, SIZE[0], 80):
            od.line(
                (x + step * 11, 0, x - 220 + step * 11, SIZE[1]),
                fill=(255, 255, 255, 28),
                width=2,
            )
        od.rectangle((0, 0, SIZE[0], SIZE[1]), fill=(0, 0, 0, 60 if dark else 35))
        base = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(base)
        draw_text(draw, (1180, 100), "same frames", fill=WHITE if dark else INK, fnt=FONTS["h"])
        draw_text(draw, (1180, 142), "different bill", fill=ORANGE, fnt=FONTS["h"])
        out.append(base)
    return out


def clip_sequence(
    clip: ClipData,
    *,
    theme: str,
    raw_seconds: float,
    overlay_seconds: float,
    label: str,
    hero: str,
) -> list[Image.Image]:
    raw_n = min(len(clip.crops), max(4, round(raw_seconds * 12)))
    raw_idxs = [
        min(len(clip.crops) - 1, round(idx * (raw_n - 1) / max(1, raw_n - 1)))
        for idx in range(raw_n)
    ]
    frames: list[Image.Image] = []
    for pos, idx in enumerate(raw_idxs):
        zoom = 1.0 + 0.035 * (pos / max(1, len(raw_idxs) - 1))
        frame = raw_frame(clip, idx, theme=theme, label=label, zoom=zoom)
        frames.extend([frame] * 2)
    freeze = raw_frame(
        clip,
        raw_idxs[-1],
        theme=theme,
        label="freeze: what changed?",
        zoom=1.04,
    )
    frames.extend(hold(freeze, 0.22))
    frames.extend(rewind_frames(clip, raw_idxs[-6:], theme=theme))

    overlay_n = min(len(clip.crops), max(5, round(overlay_seconds * 6)))
    overlay_idxs = [
        min(len(clip.crops) - 1, 1 + round(idx * (len(clip.crops) - 2) / max(1, overlay_n - 1)))
        for idx in range(overlay_n)
    ]
    for idx in overlay_idxs:
        frame = overlay_frame(clip, idx, theme=theme, label="replay: freshness budget", hero=hero)
        frames.extend([frame] * 4)
    return frames


def result_beat(values: dict[str, Any], *, theme: str, seconds: float = 1.3) -> list[Image.Image]:
    dark = theme == "dark"
    bg = NAVY_2 if dark else WARM
    fg = WHITE if dark else INK
    canvas = Image.new("RGB", SIZE, bg)
    draw = ImageDraw.Draw(canvas)
    centered_text(draw, 220, "After ingest, stop paying twice.", fill=fg, fnt=FONTS["title"])
    centered_text(draw, 330, "14.90–35.92×", fill=ORANGE, fnt=FONTS["display"])
    centered_text(draw, 440, "repaired follow-up speedup", fill=fg, fnt=FONTS["h"])
    centered_text(
        draw,
        520,
        "0/93 observed paired drift",
        fill=(74, 222, 128) if dark else GREEN,
        fnt=FONTS["h"],
    )
    centered_text(
        draw,
        710,
        "C-PERSIST is after-ingest reuse; first query still pays.",
        fill=DIM_WHITE if dark else MUTED,
        fnt=FONTS["small"],
    )
    return fade_in(hold(canvas, seconds), color=bg)


def ceiling_beat(*, theme: str, seconds: float = 1.0) -> list[Image.Image]:
    dark = theme == "dark"
    bg = (8, 12, 28) if dark else WARM
    fg = WHITE if dark else INK
    canvas = Image.new("RGB", SIZE, bg)
    draw = ImageDraw.Draw(canvas)
    centered_text(draw, 275, "component speedup", fill=fg, fnt=FONTS["title"])
    centered_text(draw, 395, "!=", fill=RED, fnt=FONTS["display"])
    centered_text(draw, 525, "end-to-end speedup", fill=fg, fnt=FONTS["title"])
    centered_text(draw, 710, "C-CEILING: stage share bounds every win", fill=ORANGE, fnt=FONTS["h"])
    return hold(canvas, seconds)


def stream_beat(*, theme: str, seconds: float = 1.0) -> list[Image.Image]:
    dark = theme == "dark"
    bg = NAVY if dark else WARM
    fg = WHITE if dark else INK
    canvas = Image.new("RGB", SIZE, bg)
    draw = ImageDraw.Draw(canvas)
    centered_text(draw, 260, "Candidate C-STREAM target.", fill=PURPLE, fnt=FONTS["display"])
    centered_text(draw, 420, "native-rate state updates", fill=fg, fnt=FONTS["title"])
    centered_text(
        draw,
        510,
        "hypothesis bridge; not headline here",
        fill=DIM_WHITE if dark else MUTED,
        fnt=FONTS["h"],
    )
    centered_text(draw, 690, "state > pixels", fill=ORANGE, fnt=FONTS["display"])
    return hold(canvas, seconds)


PASS_LABELS = {
    "look": "LOOK",
    "freeze": "FREEZE",
    "rewind": "REWIND",
    "replay": "REPLAY",
    "paper result": "RESULT",
    "local motion": "LOCAL MOTION",
    "camera motion": "CAMERA MOTION",
    "title": "TITLE",
}

PASS_ACTIONS = {
    "look": "raw play",
    "freeze": "hold frame",
    "rewind": "scrub backward",
    "replay": "replay forward",
    "paper result": "paper-level result",
    "local motion": "raw then replay",
    "camera motion": "raw then replay",
    "title": "closing card",
}


def draw_transport_status(
    draw: ImageDraw.ImageDraw,
    *,
    current: str,
    progress: float,
    rewind: bool = False,
) -> None:
    video_x0, _, video_x1, video_y1 = ANCHOR_VIDEO_BOX
    label = PASS_LABELS.get(current, current.upper())
    direction_label = PASS_ACTIONS.get(
        current,
        "scrub backward" if rewind else "scrub forward",
    )
    status_y = video_y1 + 26
    status_w = 415
    status_box = (video_x0, status_y - 6, video_x0 + status_w, status_y + 45)
    rounded_rect(
        draw,
        status_box,
        fill=(10, 18, 38),
        outline=(51, 65, 85),
        radius=16,
    )
    accent = ORANGE if rewind or current in {"replay", "title"} else (148, 163, 184)
    draw.rectangle((video_x0, status_y - 6, video_x0 + 6, status_y + 45), fill=accent)
    draw.text(
        (video_x0 + 20, status_y + 5),
        f"{label} · {direction_label}",
        fill=ORANGE if rewind else WHITE,
        font=FONTS["small"],
    )
    draw.text(
        (video_x1 - 430, video_y1 + 42),
        "same stage; evidence changes inside the frame",
        fill=(148, 163, 184),
        font=FONTS["tiny"],
    )


def anchor_canvas(*, current: str, progress: float, rewind: bool = False) -> Image.Image:
    canvas = Image.new("RGB", SIZE, NAVY)
    draw = ImageDraw.Draw(canvas)
    rounded_rect(draw, ANCHOR_PANEL_BOX, fill=(10, 18, 38), outline=(51, 65, 85), radius=24)
    return canvas


def draw_anchor_video(
    canvas: Image.Image,
    image: Image.Image,
    *,
    dim: bool = False,
    rewind: bool = False,
) -> None:
    display = image.copy()
    if dim:
        veil = Image.new("RGB", display.size, (0, 0, 0))
        display = Image.blend(display, veil, 0.38)
    fit_on_canvas(canvas, display, ANCHOR_VIDEO_BOX, border=WHITE, shadow=True)
    if rewind:
        draw_rewind_icon(canvas)


def draw_rewind_icon(canvas: Image.Image) -> None:
    """Tiny transport glyph for the rewind pass; no explanatory text."""

    draw = ImageDraw.Draw(canvas)
    x0, y0, x1, _ = ANCHOR_VIDEO_BOX
    box = (x1 - 142, y0 + 24, x1 - 34, y0 + 78)
    rounded_rect(draw, box, fill=(15, 23, 42), outline=(148, 163, 184), radius=18)
    cx = box[0] + 39
    cy = box[1] + 27
    for off in (0, 30):
        draw.polygon(
            ((cx + off, cy), (cx + off + 24, cy - 18), (cx + off + 24, cy + 18)),
            fill=WHITE,
        )


def draw_panel_header(draw: ImageDraw.ImageDraw, text: str) -> None:
    x0, y0, _, _ = ANCHOR_PANEL_BOX
    draw_text(draw, (x0 + 34, y0 + 40), text, fill=DIM_WHITE, fnt=FONTS["small"])


def budget_slot_geometry(
    count: int,
    inner: tuple[int, int, int, int],
) -> tuple[int, int]:
    count = max(1, count)
    max_gap = 8
    gap = max(2, min(max_gap, (inner[2] - inner[0]) // max(1, count * 5)))
    bar_w = max(5, (inner[2] - inner[0] - gap * (count - 1)) // count)
    return bar_w, gap


def draw_budget_cursor(
    draw: ImageDraw.ImageDraw,
    *,
    inner: tuple[int, int, int, int],
    slot: int,
    count: int,
    bar_w: int,
    gap: int,
) -> None:
    slot = max(0, min(max(0, count - 1), slot))
    bx = inner[0] + slot * (bar_w + gap)
    cx = bx + bar_w // 2
    draw.line((cx, inner[1] - 14, cx, inner[3] + 14), fill=WHITE, width=3)
    draw.polygon(
        ((cx - 8, inner[1] - 18), (cx + 8, inner[1] - 18), (cx, inner[1] - 6)),
        fill=WHITE,
    )


def draw_dense_frame_budget_panel(
    draw: ImageDraw.ImageDraw,
    clip: ClipData,
    *,
    current_idx: int,
    dim: bool = False,
) -> None:
    draw_dense_frame_budget_values(draw, len(clip.crops), current_idx=current_idx, dim=dim)


def draw_dense_frame_budget_values(
    draw: ImageDraw.ImageDraw,
    frame_count: int,
    *,
    current_idx: int,
    dim: bool = False,
) -> None:
    """Dense baseline budget over the actual sampled-frame sequence."""

    x0, y0, x1, _ = ANCHOR_PANEL_BOX
    chart = (x0 + 34, y0 + 190, x1 - 34, y0 + 520)
    draw_panel_header(draw, "dense input")
    label = "frame bought"
    label_w, _ = text_size(draw, label, FONTS["small"])
    draw.text((chart[2] - label_w, chart[1] - 42), label, fill=ORANGE, font=FONTS["small"])
    rounded_rect(draw, chart, fill=(15, 23, 42), outline=(51, 65, 85), radius=16)
    inner = (chart[0] + 20, chart[1] + 20, chart[2] - 20, chart[3] - 20)
    slots = max(1, frame_count)
    bar_w, gap = budget_slot_geometry(slots, inner)
    current_idx = max(0, min(slots - 1, current_idx))
    for slot in range(slots):
        bx = inner[0] + slot * (bar_w + gap)
        fill = ORANGE if slot <= current_idx and not dim else (20, 30, 52)
        if slot <= current_idx and dim:
            fill = (51, 65, 85)
        draw.rounded_rectangle((bx, inner[1], bx + bar_w, inner[3]), radius=6, fill=fill)
    draw_budget_cursor(draw, inner=inner, slot=current_idx, count=slots, bar_w=bar_w, gap=gap)


def budget_values_for_details(
    frame_count: int,
    details: list[dict[str, Any]],
) -> list[tuple[float, float]]:
    values: list[tuple[float, float]] = []
    for pos in range(frame_count):
        if pos == 0:
            values.append((0.0, 1.0))
        else:
            stats = stats_for(details, pos)
            values.append((stats["reused"], stats["fresh"]))
    return values


def draw_budget_history_values(
    draw: ImageDraw.ImageDraw,
    values: list[tuple[float, float]],
    idx: int,
    *,
    header: str,
) -> None:
    """Frame-by-frame stacked reused/fresh budget, without numeric labels."""

    x0, y0, x1, _ = ANCHOR_PANEL_BOX
    chart = (x0 + 34, y0 + 190, x1 - 34, y0 + 520)
    draw_panel_header(draw, header)
    draw.text((chart[0], chart[1] - 42), "fresh", fill=ORANGE, font=FONTS["small"])
    draw.text((chart[0], chart[3] + 14), "reused", fill=(74, 222, 128), font=FONTS["small"])
    rounded_rect(draw, chart, fill=(15, 23, 42), outline=(51, 65, 85), radius=16)
    inner = (chart[0] + 20, chart[1] + 20, chart[2] - 20, chart[3] - 20)
    draw.line((inner[0], inner[3], inner[2], inner[3]), fill=(71, 85, 105), width=2)
    slots = len(values)
    bar_w, gap = budget_slot_geometry(slots, inner)
    max_h = inner[3] - inner[1]
    for slot in range(slots):
        bx = inner[0] + slot * (bar_w + gap)
        draw.rounded_rectangle((bx, inner[1], bx + bar_w, inner[3]), radius=6, fill=(20, 30, 52))
    for slot, (reuse, fresh) in enumerate(values):
        bx = inner[0] + slot * (bar_w + gap)
        fresh = max(0.0, min(1.0, fresh))
        reuse = max(0.0, min(1.0, reuse))
        fresh_h = round(max_h * fresh)
        reuse_h = max(2, max_h - fresh_h)
        draw.rounded_rectangle(
            (bx, inner[3] - reuse_h, bx + bar_w, inner[3]),
            radius=6,
            fill=(74, 222, 128),
        )
        if fresh_h > 0:
            draw.rounded_rectangle(
                (bx, inner[1], bx + bar_w, inner[1] + fresh_h),
                radius=6,
                fill=ORANGE,
            )
    draw_budget_cursor(draw, inner=inner, slot=idx, count=slots, bar_w=bar_w, gap=gap)


def draw_reuse_fresh_history(
    draw: ImageDraw.ImageDraw,
    clip: ClipData,
    idx: int,
) -> None:
    draw_budget_history_values(
        draw,
        budget_values_for_details(len(clip.crops), clip.details),
        idx,
        header="routing budget",
    )


def draw_speedup_panel(draw: ImageDraw.ImageDraw) -> None:
    x0, y0, _, _ = ANCHOR_PANEL_BOX
    draw_panel_header(draw, "speedup")
    draw_text(draw, (x0 + 34, y0 + 180), "14.90–35.92×", fill=ORANGE, fnt=FONTS["number"])
    draw_text(draw, (x0 + 38, y0 + 286), "follow-up speedup", fill=WHITE, fnt=FONTS["h"])


def draw_title_probe_panel(
    draw: ImageDraw.ImageDraw,
    values: list[tuple[float, float]] | None = None,
    idx: int = 0,
) -> None:
    if values:
        draw_budget_history_values(draw, values, idx, header="title motion")
    else:
        draw_panel_header(draw, "title motion")


def representative_replay_indices(clip: ClipData, *, max_fresh: float = 0.70) -> list[int]:
    """Return scored-frame indices for a readable replay sample.

    The right-side chart still contains every scored frame.  This list only
    chooses which exact scored frames to display in the video stage, avoiding
    an opening frame that visually floods orange due to reference/age-refresh
    behavior.
    """

    indices: list[int] = []
    for idx in range(1, len(clip.crops)):
        stats = stats_for(clip.details, idx)
        if stats["has_transition"] and stats["fresh"] <= max_fresh:
            indices.append(idx)
    if indices:
        return indices
    return list(range(1, len(clip.crops)))


def draw_anchor_panel_raw(
    draw: ImageDraw.ImageDraw,
    *,
    headline: str,
    subline: str,
    badge: str = "planner hidden",
    body_line: str = "First, just look at the video.",
    detail_line: str = "The overlay has to earn your trust.",
) -> None:
    x0, y0, x1, _ = ANCHOR_PANEL_BOX
    draw_text(draw, (x0 + 34, y0 + 42), headline, fill=WHITE, fnt=FONTS["h"])
    draw_text(draw, (x0 + 34, y0 + 94), subline, fill=DIM_WHITE, fnt=FONTS["body"])
    rounded_rect(
        draw,
        (x0 + 34, y0 + 185, x1 - 34, y0 + 250),
        fill=(15, 23, 42),
        outline=(51, 65, 85),
        radius=14,
    )
    draw_text(draw, (x0 + 56, y0 + 204), badge, fill=DIM_WHITE, fnt=FONTS["h"])
    draw_text(draw, (x0 + 34, y0 + 318), body_line, fill=WHITE, fnt=FONTS["body"])
    draw_text(draw, (x0 + 34, y0 + 360), detail_line, fill=DIM_WHITE, fnt=FONTS["small"])


def draw_anchor_budget_panel(
    draw: ImageDraw.ImageDraw,
    stats: dict[str, float],
    *,
    headline: str,
    note: str,
) -> None:
    x0, y0, x1, _ = ANCHOR_PANEL_BOX
    draw_text(draw, (x0 + 34, y0 + 42), headline, fill=WHITE, fnt=FONTS["h"])
    if not stats.get("has_transition"):
        draw_text(draw, (x0 + 34, y0 + 128), "no prior frame", fill=DIM_WHITE, fnt=FONTS["h"])
        draw_text(
            draw, (x0 + 34, y0 + 172), "transition not scored", fill=DIM_WHITE, fnt=FONTS["small"]
        )
        return
    reuse_pct, fresh_pct = pct_pair_from_stats(stats)
    draw_text(
        draw, (x0 + 34, y0 + 122), f"{reuse_pct}% reused", fill=(74, 222, 128), fnt=FONTS["number"]
    )
    draw_text(
        draw, (x0 + 34, y0 + 212), f"{fresh_pct}% fresh", fill=ORANGE, fnt=FONTS["number_small"]
    )
    bar_x0, bar_y0, bar_x1, bar_y1 = x0 + 34, y0 + 315, x1 - 34, y0 + 358
    rounded_rect(draw, (bar_x0, bar_y0, bar_x1, bar_y1), fill=(15, 23, 42), radius=12)
    split = round(bar_x0 + (bar_x1 - bar_x0) * stats["reused"])
    draw.rectangle((bar_x0, bar_y0, split, bar_y1), fill=(34, 197, 94))
    draw.rectangle((split, bar_y0, bar_x1, bar_y1), fill=ORANGE)
    draw_text(
        draw, (x0 + 34, y0 + 410), "orange = fresh visual evidence", fill=ORANGE, fnt=FONTS["body"]
    )
    draw_text(
        draw,
        (x0 + 34, y0 + 448),
        "fresh = novel + age-expired",
        fill=DIM_WHITE,
        fnt=FONTS["small"],
    )
    if stats["stale"] > 0.08:
        draw_text(
            draw,
            (x0 + 34, y0 + 494),
            f"age-expired refresh: {stats['stale']:.0%}",
            fill=DIM_WHITE,
            fnt=FONTS["small"],
        )
    draw_text(
        draw,
        (x0 + 34, y0 + 532),
        "not saliency; not C-PERSIST timing",
        fill=DIM_WHITE,
        fnt=FONTS["small"],
    )
    draw_text(draw, (x0 + 34, y0 + 590), note, fill=WHITE, fnt=FONTS["body"])


def draw_anchor_result_panel(draw: ImageDraw.ImageDraw) -> None:
    x0, y0, _, _ = ANCHOR_PANEL_BOX
    draw_text(
        draw,
        (x0 + 34, y0 + 42),
        "C-PERSIST paper-level result",
        fill=DIM_WHITE,
        fnt=FONTS["body"],
    )
    draw_text(draw, (x0 + 34, y0 + 118), "After ingest:", fill=WHITE, fnt=FONTS["h"])
    draw_text(draw, (x0 + 34, y0 + 188), "14.90–35.92×", fill=ORANGE, fnt=FONTS["number"])
    draw_text(draw, (x0 + 34, y0 + 286), "follow-up speedup", fill=WHITE, fnt=FONTS["h"])
    draw_text(
        draw,
        (x0 + 34, y0 + 378),
        "0/93 observed paired drift",
        fill=(74, 222, 128),
        fnt=FONTS["body"],
    )
    draw_text(
        draw,
        (x0 + 34, y0 + 480),
        "not this clip's timing",
        fill=DIM_WHITE,
        fnt=FONTS["body"],
    )
    draw_text(
        draw,
        (x0 + 34, y0 + 522),
        "first query still pays",
        fill=DIM_WHITE,
        fnt=FONTS["small"],
    )


def anchor_frame_raw(
    clip: ClipData,
    image: Image.Image,
    *,
    current: str,
    progress: float,
    headline: str,
    subline: str,
) -> Image.Image:
    canvas = anchor_canvas(current=current, progress=progress)
    draw_anchor_video(canvas, image)
    draw = ImageDraw.Draw(canvas)
    if headline:
        centered_text_in_box(
            draw,
            ANCHOR_VIDEO_BOX,
            headline,
            fill=WHITE,
            fnt=FONTS["title"],
            y_frac=0.10,
        )
    current_idx = round(progress * (len(clip.crops) - 1))
    draw_dense_frame_budget_panel(draw, clip, current_idx=current_idx)
    return canvas


def anchor_frame_overlay(
    clip: ClipData,
    idx: int,
    *,
    current: str,
    progress: float,
    headline: str,
    note: str,
) -> Image.Image:
    canvas = anchor_canvas(current=current, progress=progress)
    transition = clip.details[idx - 1] if idx > 0 else None
    image = overlay_boxes(clip.crops[idx], transition, mode="fresh")
    draw_anchor_video(canvas, image)
    draw = ImageDraw.Draw(canvas)
    draw_reuse_fresh_history(draw, clip, idx)
    return canvas


def anchor_frame_freeze(
    clip: ClipData,
    image: Image.Image,
    *,
    current: str,
    show_question: bool = True,
) -> Image.Image:
    canvas = anchor_canvas(current=current, progress=0.5)
    draw_anchor_video(canvas, image, dim=True)
    draw = ImageDraw.Draw(canvas)
    draw_dense_frame_budget_panel(draw, clip, current_idx=len(clip.crops) - 1, dim=True)
    if show_question:
        centered_text_in_box(
            draw,
            ANCHOR_VIDEO_BOX,
            "what actually changed?",
            fill=WHITE,
            fnt=FONTS["title"],
            y_frac=0.5,
        )
    return canvas


def anchor_frame_rewind(
    clip: ClipData,
    image: Image.Image,
    *,
    progress: float,
) -> Image.Image:
    canvas = anchor_canvas(current="rewind", progress=progress, rewind=True)
    draw_anchor_video(canvas, vhs_rewind_image(image, progress=progress), rewind=True)
    draw = ImageDraw.Draw(canvas)
    current_idx = round((1.0 - progress) * (len(clip.crops) - 1))
    draw_dense_frame_budget_panel(draw, clip, current_idx=current_idx, dim=True)
    return canvas


def opening_title_hold(*, seconds: float) -> list[Image.Image]:
    canvas = Image.new("RGBA", SIZE, (*NAVY, 255))
    draw_identity_title(canvas, theme="dark", y_offset=-10)
    return hold(canvas.convert("RGB"), seconds)


def teaser_canvas(*, accent: tuple[int, int, int] = ORANGE) -> Image.Image:
    canvas = Image.new("RGB", SIZE, NAVY)
    draw = ImageDraw.Draw(canvas)
    rounded_rect(draw, TEASER_PANEL_BOX, fill=(10, 18, 38), outline=(51, 65, 85), radius=24)
    x0, _, x1, _ = TEASER_VIDEO_BOX
    draw.text((x0, 60), "VLMaxxing through FrameMogging", fill=DIM_WHITE, font=FONTS["small"])
    draw.line((x0, 100, x1, 100), fill=accent, width=3)
    return canvas


def draw_teaser_status(
    draw: ImageDraw.ImageDraw,
    text: str,
    *,
    accent: tuple[int, int, int] = ORANGE,
) -> None:
    x0, _, _, y1 = TEASER_VIDEO_BOX
    box = (x0, y1 + 20, x0 + 360, y1 + 72)
    rounded_rect(draw, box, fill=(10, 18, 38), outline=(51, 65, 85), radius=16)
    draw.rectangle((x0, y1 + 20, x0 + 6, y1 + 72), fill=accent)
    draw.text((x0 + 20, y1 + 34), text, fill=WHITE, font=FONTS["small"])


def draw_teaser_video(
    canvas: Image.Image,
    image: Image.Image,
    *,
    dim: bool = False,
) -> None:
    display = image.copy()
    if dim:
        veil = Image.new("RGB", display.size, (0, 0, 0))
        display = Image.blend(display, veil, 0.40)
    fit_on_canvas(canvas, display, TEASER_VIDEO_BOX, border=WHITE, shadow=True)


def vhs_rewind_image(image: Image.Image, *, progress: float) -> Image.Image:
    """Presentation-only reverse-scrub distortion for the rewind beat."""

    out = image.convert("RGB").copy()
    w, h = out.size
    # Horizontal tracking tears: copy thin bands with deterministic offsets.
    for band_idx in range(7):
        phase = progress * 9.0 + band_idx * 1.7
        band_h = max(8, h // 34)
        y = round((0.12 + 0.78 * ((math.sin(phase) + 1.0) / 2.0)) * (h - band_h))
        shift = round(math.sin(phase * 1.9) * 36)
        strip = out.crop((0, y, w, y + band_h))
        shifted = Image.new("RGB", (w, band_h), (0, 0, 0))
        shifted.paste(strip, (shift, 0))
        if shift > 0:
            shifted.paste(strip.crop((0, 0, min(shift, w), band_h)), (0, 0))
        elif shift < 0:
            shifted.paste(strip.crop((max(0, w + shift), 0, w, band_h)), (w + shift, 0))
        out.paste(Image.blend(strip, shifted, 0.74), (0, y))
    overlay = Image.new("RGBA", out.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for y in range(0, h, 13):
        alpha = 26 + round(18 * (0.5 + 0.5 * math.sin(progress * 18 + y * 0.08)))
        draw.line((0, y, w, y), fill=(255, 255, 255, alpha), width=1)
    for idx in range(5):
        y = round((idx + 1) * h / 6 + 18 * math.sin(progress * 14 + idx))
        draw.rectangle((0, y, w, y + 5), fill=(255, 255, 255, 44))
    return Image.alpha_composite(out.convert("RGBA"), overlay).convert("RGB")


def recent_fresh_values(details: list[dict[str, Any]], idx: int, *, count: int = 14) -> list[float]:
    values: list[float] = []
    start = max(1, idx - count + 1)
    for pos in range(start, idx + 1):
        stats = stats_for(details, pos)
        if stats["has_transition"]:
            values.append(stats["fresh"])
    return values


def draw_fresh_sparkline(
    draw: ImageDraw.ImageDraw,
    values: list[float],
    box: tuple[int, int, int, int],
) -> None:
    x0, y0, x1, y1 = box
    draw.text((x0, y0 - 30), "fresh over time", fill=DIM_WHITE, font=FONTS["tiny"])
    draw.rounded_rectangle(box, radius=10, fill=(15, 23, 42), outline=(51, 65, 85), width=1)
    if not values:
        draw.text((x0 + 18, y0 + 19), "waiting for transition", fill=DIM_WHITE, font=FONTS["tiny"])
        return
    slot_count = 14
    values = values[-slot_count:]
    gap = 5
    bar_w = max(4, (x1 - x0 - 28 - gap * (slot_count - 1)) // slot_count)
    base = y1 - 12
    missing = slot_count - len(values)
    for i in range(slot_count):
        xx = x0 + 14 + i * (bar_w + gap)
        draw.rounded_rectangle((xx, base - 4, xx + bar_w, base), radius=3, fill=(51, 65, 85))
    for i, value in enumerate(values):
        slot = missing + i
        xx = x0 + 14 + slot * (bar_w + gap)
        h = max(5, round((y1 - y0 - 24) * max(0.0, min(1.0, value))))
        color = ORANGE if i == len(values) - 1 else (251, 146, 60)
        draw.rounded_rectangle((xx, base - h, xx + bar_w, base), radius=3, fill=color)


def draw_teaser_raw_panel(
    draw: ImageDraw.ImageDraw,
    *,
    headline: str,
    note: str = "",
) -> None:
    x0, y0, x1, _ = TEASER_PANEL_BOX
    draw.text((x0 + 34, y0 + 72), headline, fill=WHITE, font=FONTS["hero"])
    if note:
        draw.text((x0 + 34, y0 + 178), note, fill=DIM_WHITE, font=FONTS["h"])
    rounded_rect(
        draw,
        (x0 + 34, y0 + 378, x1 - 34, y0 + 445),
        fill=(15, 23, 42),
        outline=(51, 65, 85),
        radius=16,
    )
    draw.text((x0 + 58, y0 + 397), "planner hidden", fill=DIM_WHITE, font=FONTS["h"])


def draw_teaser_budget_panel(
    draw: ImageDraw.ImageDraw,
    stats: dict[str, float],
    history: list[float],
    *,
    headline: str,
) -> None:
    x0, y0, x1, _ = TEASER_PANEL_BOX
    draw.text((x0 + 34, y0 + 52), headline, fill=WHITE, font=FONTS["h"])
    if not stats["has_transition"]:
        draw.text((x0 + 34, y0 + 160), "reference frame", fill=DIM_WHITE, font=FONTS["h"])
        draw.text((x0 + 34, y0 + 210), "no prior frame yet", fill=DIM_WHITE, font=FONTS["small"])
        return
    reuse_pct, fresh_pct = pct_pair_from_stats(stats)
    draw.text(
        (x0 + 34, y0 + 140),
        f"{reuse_pct}% reused",
        fill=(74, 222, 128),
        font=FONTS["number"],
    )
    draw.text((x0 + 34, y0 + 228), f"{fresh_pct}% fresh", fill=ORANGE, font=FONTS["number_small"])
    bar = (x0 + 34, y0 + 342, x1 - 34, y0 + 386)
    rounded_rect(draw, bar, fill=(15, 23, 42), radius=12)
    split = round(bar[0] + (bar[2] - bar[0]) * stats["reused"])
    draw.rectangle((bar[0], bar[1], split, bar[3]), fill=(34, 197, 94))
    draw.rectangle((split, bar[1], bar[2], bar[3]), fill=ORANGE)
    draw.text((x0 + 34, y0 + 430), "orange = fresh evidence", fill=ORANGE, font=FONTS["body"])
    draw_fresh_sparkline(draw, history, (x0 + 34, y0 + 535, x1 - 34, y0 + 642))


def draw_teaser_result_panel(draw: ImageDraw.ImageDraw) -> None:
    x0, y0, _, _ = TEASER_PANEL_BOX
    draw.text((x0 + 34, y0 + 72), "After ingest:", fill=WHITE, font=FONTS["h"])
    draw.text((x0 + 34, y0 + 152), "14.90–35.92×", fill=ORANGE, font=FONTS["number"])
    draw.text((x0 + 34, y0 + 246), "follow-up", fill=WHITE, font=FONTS["h"])
    draw.text((x0 + 34, y0 + 336), "0/93 paired drift", fill=(74, 222, 128), font=FONTS["h"])
    draw.text((x0 + 34, y0 + 442), "First query still pays.", fill=DIM_WHITE, font=FONTS["h"])


def teaser_raw_frame(
    clip: ClipData,
    image: Image.Image,
    *,
    headline: str,
    note: str,
    status: str,
) -> Image.Image:
    canvas = teaser_canvas(accent=(148, 163, 184))
    draw_teaser_video(canvas, image)
    draw = ImageDraw.Draw(canvas)
    draw_teaser_raw_panel(draw, headline=headline, note=note)
    draw_teaser_status(draw, status, accent=(148, 163, 184))
    chapter_tag(draw, clip.spec, dark=True)
    return canvas


def teaser_freeze_frame(clip: ClipData, image: Image.Image) -> Image.Image:
    canvas = teaser_canvas(accent=WHITE)
    draw_teaser_video(canvas, image, dim=True)
    draw = ImageDraw.Draw(canvas)
    centered_text_in_box(
        draw,
        TEASER_VIDEO_BOX,
        "What actually changed?",
        fill=WHITE,
        fnt=FONTS["title"],
    )
    draw_teaser_raw_panel(draw, headline="What changed?", note="ask again, cheaper")
    draw_teaser_status(draw, "FREEZE", accent=WHITE)
    chapter_tag(draw, clip.spec, dark=True)
    return canvas


def teaser_rewind_frame(clip: ClipData, image: Image.Image, *, progress: float) -> Image.Image:
    canvas = teaser_canvas(accent=ORANGE)
    draw_teaser_video(canvas, vhs_rewind_image(image, progress=progress))
    draw = ImageDraw.Draw(canvas)
    draw_teaser_raw_panel(draw, headline="same frames", note="different bill")
    draw_teaser_status(draw, "<< REWIND", accent=ORANGE)
    chapter_tag(draw, clip.spec, dark=True)
    return canvas


def teaser_overlay_frame(
    clip: ClipData,
    idx: int,
    *,
    headline: str,
    status: str,
) -> Image.Image:
    canvas = teaser_canvas(accent=ORANGE)
    transition = clip.details[idx - 1] if idx > 0 else None
    draw_teaser_video(canvas, overlay_boxes(clip.crops[idx], transition, mode="fresh"))
    draw = ImageDraw.Draw(canvas)
    draw_teaser_budget_panel(
        draw,
        stats_for(clip.details, idx),
        recent_fresh_values(clip.details, idx),
        headline=headline,
    )
    draw_teaser_status(draw, status, accent=ORANGE)
    chapter_tag(draw, clip.spec, dark=True)
    return canvas


def teaser_result_frame(clip: ClipData) -> Image.Image:
    canvas = teaser_canvas(accent=ORANGE)
    result_video = overlay_boxes(clip.crops[4], clip.details[3], mode="fresh")
    draw_teaser_video(canvas, result_video, dim=True)
    draw = ImageDraw.Draw(canvas)
    draw_teaser_result_panel(draw)
    draw_teaser_status(draw, "PAPER RESULT", accent=ORANGE)
    return canvas


def render_minimal_teaser_cut(
    clips: list[ClipData],
    out_dir: Path,
    *,
    scored: bool = False,
) -> Path:
    """Render the short social/teaser cut.

    This cut deliberately explains one mechanism only: raw clip, freeze,
    rewind, replay with exact routing fresh blocks, paper-level result, and one
    harder-scene honesty beat. The longer anchored cut remains the broader
    landing-page draft.
    """

    wall_display = decode_display_crops(clips[0].spec, fps=24.0)
    landscape_display = decode_display_crops(clips[2].spec, fps=24.0)
    frames: list[Image.Image] = []

    frames.extend(opening_title_hold(seconds=1.6))

    raw_n = round(3.8 * FPS)
    for pos in range(raw_n):
        p = pos / max(1, raw_n - 1)
        idx = min(len(wall_display) - 1, pos)
        frames.append(
            teaser_raw_frame(
                clips[0],
                zoom_image(wall_display[idx], 1.0 + 0.012 * p),
                headline="The wall did not move.",
                note="so why pay for it again?",
                status="WATCH",
            )
        )

    freeze_img = zoom_image(wall_display[min(len(wall_display) - 1, round(4.8 * FPS))], 1.018)
    frames.extend(hold(teaser_freeze_frame(clips[0], freeze_img), 1.0))

    rewind_n = round(1.5 * FPS)
    rewind_start = len(wall_display) - 1
    rewind_stop = max(0, rewind_start - round(1.2 * FPS))
    rewind_idxs = list(range(rewind_start, rewind_stop, -2)) or [rewind_start]
    for pos in range(rewind_n):
        p = pos / max(1, rewind_n - 1)
        idx = rewind_idxs[min(len(rewind_idxs) - 1, round(p * (len(rewind_idxs) - 1)))]
        frames.append(teaser_rewind_frame(clips[0], wall_display[idx], progress=p))

    replay_n = round(5.0 * FPS)
    for pos in range(replay_n):
        p = pos / max(1, replay_n - 1)
        idx = round(1 + p * 3)
        frames.append(
            teaser_overlay_frame(
                clips[0],
                idx,
                headline="fresh-block budget",
                status="REPLAY",
            )
        )

    frames.extend(hold(teaser_result_frame(clips[0]), 3.0))

    honesty_raw_n = round(1.5 * FPS)
    for pos in range(honesty_raw_n):
        p = pos / max(1, honesty_raw_n - 1)
        idx = min(len(landscape_display) - 1, pos)
        frames.append(
            teaser_raw_frame(
                clips[2],
                zoom_image(landscape_display[idx], 1.0 + 0.01 * p),
                headline="Not every scene",
                note="is the wall.",
                status="HARDER SCENE",
            )
        )

    honesty_overlay_n = round(2.9 * FPS)
    for pos in range(honesty_overlay_n):
        p = pos / max(1, honesty_overlay_n - 1)
        idx = round(1 + p * (len(clips[2].crops) - 2))
        frames.append(
            teaser_overlay_frame(
                clips[2],
                idx,
                headline="camera motion spends more",
                status="HONESTY",
            )
        )

    frames.extend(end_card("dark", seconds=2.4))

    stem = "minimal_teaser_cut_scored" if scored else "minimal_teaser_cut"
    out_path = out_dir / f"{stem}.mp4"
    if scored:
        silent_path = out_dir / "minimal_teaser_cut.mp4"
        write_mp4(frames, silent_path, fps=FPS)
        mux_audio(
            silent_path,
            out_path,
            duration_s=probe_duration_s(silent_path),
            accent_times=[1.45, 5.35, 6.35, 7.85, 12.65, 15.65, 20.6],
            rewind_times=[6.35],
        )
    else:
        write_mp4(frames, out_path, fps=FPS)
    thumbnail(frames[round(FPS * 8.9)], out_dir / "thumbnails" / f"{stem}.png")
    return out_path


def render_title_motion_probe(out_dir: Path, *, scored: bool = False) -> Path:
    """Render the synthetic moving-title joke as a separate artifact."""

    raw_title = generated_title_motion_frames(seconds=5.6)
    planner_step = max(1, round(FPS / 12.0))
    planner_title = raw_title[::planner_step]
    overlay_title = apply_planner_fresh_overlay_to_generated_frames(planner_title)
    frames: list[Image.Image] = []
    frames.extend(raw_title[: round(1.8 * FPS)])
    # VHS rewind over the generated card before the planner view.
    reverse = list(reversed(raw_title[: round(1.8 * FPS)]))
    for pos, frame in enumerate(reverse[: round(1.0 * FPS)]):
        p = pos / max(1, round(1.0 * FPS) - 1)
        frames.append(vhs_rewind_image(frame, progress=p))
    for frame in overlay_title:
        frames.extend([frame.copy() for _ in range(planner_step)])
    frames.extend(end_card("dark", seconds=1.4))
    stem = "title_motion_probe_scored" if scored else "title_motion_probe"
    out_path = out_dir / f"{stem}.mp4"
    if scored:
        silent_path = out_dir / "title_motion_probe.mp4"
        write_mp4(frames, silent_path, fps=FPS)
        mux_audio(
            silent_path,
            out_path,
            duration_s=probe_duration_s(silent_path),
            accent_times=[0.4, 1.8, 2.8, 4.2, 6.1],
            rewind_times=[1.9],
        )
    else:
        write_mp4(frames, out_path, fps=FPS)
    thumbnail(
        frames[min(len(frames) - 1, round(FPS * 4.0))],
        out_dir / "thumbnails" / f"{stem}.png",
    )
    return out_path


def render_anchored_lure_cut(
    clips: list[ClipData],
    out_dir: Path,
    *,
    scored: bool = False,
    result_mode: str = "paper",
) -> Path:
    displays = [decode_display_crops(clip.spec, fps=24.0) for clip in clips]
    frames: list[Image.Image] = []
    accent_times: list[float] = []
    rewind_times: list[float] = []
    tick_times: list[float] = []
    soft_tick_times: list[float] = []

    def now_s() -> float:
        return len(frames) / FPS

    def cue(kind: str) -> None:
        if kind == "rewind":
            rewind_times.append(now_s())
        elif kind == "tick":
            tick_times.append(now_s())
        elif kind == "soft_tick":
            soft_tick_times.append(now_s())
        else:
            accent_times.append(now_s())

    # First frame is a clean title card for social/link previews.
    cue("accent")
    frames.extend(opening_title_hold(seconds=1.25))

    first_clip_result_video: Image.Image | None = None
    for clip_idx, (clip, display_frames) in enumerate(zip(clips, displays, strict=True)):
        raw_seconds = 3.0 if clip_idx == 0 else 1.55
        freeze_seconds = 0.68 if clip_idx == 0 else 0.32
        rewind_seconds = 0.92 if clip_idx == 0 else 0.58
        replay_seconds = 3.65 if clip_idx == 0 else 2.45
        raw_n = round(raw_seconds * FPS)
        last_dense_slot = -1
        for pos in range(raw_n):
            p = pos / max(1, raw_n - 1)
            source_idx = round(p * (len(display_frames) - 1))
            dense_slot = round(p * (len(clip.crops) - 1))
            if dense_slot != last_dense_slot:
                cue("tick")
                last_dense_slot = dense_slot
            frames.append(
                anchor_frame_raw(
                    clip,
                    zoom_image(display_frames[source_idx], 1.0 + 0.014 * p),
                    current="look",
                    progress=p,
                    headline="The wall did not move." if clip_idx == 0 else "",
                    subline="",
                )
            )

        cue("accent")
        freeze_img = zoom_image(display_frames[-1], 1.018)
        frames.extend(
            hold(
                anchor_frame_freeze(
                    clip,
                    freeze_img,
                    current="freeze",
                    show_question=clip_idx == 0,
                ),
                freeze_seconds,
            )
        )
        rewind_start = len(display_frames) - 1
        rewind_idxs = list(range(rewind_start, 0, -4)) or [rewind_start]
        rewind_n = round(rewind_seconds * FPS)
        cue("rewind")
        for pos in range(rewind_n):
            p = pos / max(1, rewind_n - 1)
            idx = rewind_idxs[min(len(rewind_idxs) - 1, round(p * (len(rewind_idxs) - 1)))]
            frames.append(anchor_frame_rewind(clip, display_frames[idx], progress=p))

        replay_idxs = representative_replay_indices(clip)
        if not replay_idxs:
            replay_idxs = [min(len(clip.crops) - 1, 1)]
        replay_n = round(replay_seconds * FPS)
        cue("accent")
        last_replay_idx = -1
        for pos in range(replay_n):
            p = pos / max(1, replay_n - 1)
            idx = replay_idxs[min(len(replay_idxs) - 1, round(p * (len(replay_idxs) - 1)))]
            if idx != last_replay_idx:
                cue("soft_tick")
                last_replay_idx = idx
            frames.append(
                anchor_frame_overlay(
                    clip,
                    idx,
                    current="replay",
                    progress=p,
                    headline="",
                    note="",
                )
            )
        if clip_idx == 0:
            result_idx = replay_idxs[-1]
            result_transition = clip.details[result_idx - 1] if result_idx > 0 else None
            first_clip_result_video = overlay_boxes(
                clip.crops[result_idx], result_transition, mode="fresh"
            )
            if result_mode == "paper":
                cue("accent")
                result_n = round(2.55 * FPS)
                for pos in range(result_n):
                    p = pos / max(1, result_n - 1)
                    canvas = anchor_canvas(current="paper result", progress=p)
                    draw_anchor_video(canvas, first_clip_result_video, dim=True)
                    draw = ImageDraw.Draw(canvas)
                    draw_speedup_panel(draw)
                    frames.append(canvas)

    if result_mode == "paper" and first_clip_result_video is None:
        raise ValueError("no clips available for anchored lure cut")

    raw_title = generated_title_motion_frames(seconds=5.25)
    title_planner_frames = raw_title[::2]
    if (len(raw_title) - 1) % 2 != 0:
        title_planner_frames.append(raw_title[-1])
    title_details = planner_details_for_generated_frames(title_planner_frames)
    title_values = budget_values_for_details(len(title_planner_frames), title_details)
    title_overlay = apply_planner_fresh_overlay_to_generated_frames(
        title_planner_frames,
        title_details,
    )
    raw_title_n = round(1.55 * FPS)
    for pos, frame in enumerate(raw_title[:raw_title_n]):
        p = pos / max(1, raw_title_n - 1)
        canvas = anchor_canvas(current="title", progress=0.0)
        draw_anchor_video(canvas, frame)
        draw = ImageDraw.Draw(canvas)
        current_title_idx = round(p * (len(title_planner_frames) - 1))
        draw_dense_frame_budget_values(
            draw,
            len(title_planner_frames),
            current_idx=current_title_idx,
        )
        frames.append(canvas)
    cue("rewind")
    reverse = list(reversed(raw_title[: round(1.45 * FPS)]))
    rewind_title_n = round(0.70 * FPS)
    for pos, frame in enumerate(reverse[:rewind_title_n]):
        p = pos / max(1, rewind_title_n - 1)
        canvas = anchor_canvas(current="title", progress=p, rewind=True)
        draw_anchor_video(canvas, vhs_rewind_image(frame, progress=p), rewind=True)
        draw = ImageDraw.Draw(canvas)
        current_title_idx = round((1.0 - p) * (len(title_planner_frames) - 1))
        draw_dense_frame_budget_values(
            draw,
            len(title_planner_frames),
            current_idx=current_title_idx,
            dim=True,
        )
        frames.append(canvas)
    cue("accent")
    for idx, frame in enumerate(title_overlay):
        canvas = anchor_canvas(current="title", progress=1.0)
        draw_anchor_video(canvas, frame)
        draw = ImageDraw.Draw(canvas)
        draw_title_probe_panel(draw, title_values, idx)
        frames.extend([canvas] * 2)
    clean_title = anchor_canvas(current="title", progress=1.0)
    draw_anchor_video(clean_title, raw_title[-1])
    clean_draw = ImageDraw.Draw(clean_title)
    draw_title_probe_panel(clean_draw, title_values, len(title_values) - 1)
    frames.extend(hold(clean_title, 1.0))

    stem = "anchored_lure_cut_scored" if scored else "anchored_lure_cut"
    out_path = out_dir / f"{stem}.mp4"
    if scored:
        silent_path = out_dir / "anchored_lure_cut.mp4"
        write_mp4(frames, silent_path, fps=FPS)
        duration = probe_duration_s(silent_path)
        mux_audio(
            silent_path,
            out_path,
            duration_s=duration,
            accent_times=accent_times,
            rewind_times=rewind_times,
            tick_times=tick_times,
            soft_tick_times=soft_tick_times,
        )
    else:
        write_mp4(frames, out_path, fps=FPS)
    thumb_frame = frames[min(len(frames) - 1, round(FPS * 8.8))]
    thumbnail(thumb_frame, out_dir / "thumbnails" / f"{stem}.png")
    return out_path


def opening_question(seconds: float = 1.6) -> list[Image.Image]:
    canvas = Image.new("RGB", SIZE, NAVY)
    draw = ImageDraw.Draw(canvas)
    centered_text(draw, 390, "The wall did not move.", fill=WHITE, fnt=FONTS["display"])
    centered_text(draw, 520, "so why pay for it again?", fill=ORANGE, fnt=FONTS["title"])
    return fade_in(hold(canvas, seconds), color=NAVY)


def lure_raw_pass(
    clip: ClipData,
    display_crops: list[Image.Image],
    *,
    seconds: float,
    label: str,
) -> list[Image.Image]:
    frames: list[Image.Image] = []
    n = max(1, round(seconds * FPS))
    for idx in range(n):
        progress = idx / max(1, n - 1)
        source_idx = min(len(display_crops) - 1, idx)
        canvas = Image.new("RGB", SIZE, NAVY)
        draw = ImageDraw.Draw(canvas)
        image = zoom_image(display_crops[source_idx], 1.0 + 0.035 * progress)
        fit_on_canvas(canvas, image, (110, 145, 1810, 905), border=WHITE, shadow=True)
        draw_text(draw, (110, 82), label, fill=WHITE, fnt=FONTS["title"])
        chapter_tag(draw, clip.spec, dark=True)
        frames.append(canvas)
    return frames


def freeze_question(
    clip: ClipData,
    display_crops: list[Image.Image],
    *,
    seconds: float = 0.9,
    label: str = "what actually changed?",
) -> list[Image.Image]:
    frame = Image.new("RGB", SIZE, NAVY)
    image = zoom_image(display_crops[-1], 1.045)
    fit_on_canvas(frame, image, (110, 145, 1810, 905), border=WHITE, shadow=True)
    overlay = Image.new("RGBA", SIZE, (0, 0, 0, 88))
    frame = Image.alpha_composite(frame.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(frame)
    centered_text(draw, 455, label, fill=WHITE, fnt=FONTS["display"])
    centered_text(draw, 560, "same pixels, different bill", fill=ORANGE, fnt=FONTS["h"])
    chapter_tag(draw, clip.spec, dark=True)
    return hold(frame, seconds)


def lure_overlay_pass(
    clip: ClipData,
    *,
    seconds: float,
    hero: str,
    start_idx: int = 1,
    end_idx: int | None = None,
    label: str = "replay with exact fresh blocks",
) -> list[Image.Image]:
    frames: list[Image.Image] = []
    end_idx = min(len(clip.crops) - 1, end_idx if end_idx is not None else len(clip.crops) - 1)
    start_idx = max(1, min(start_idx, end_idx))
    n = max(1, round(seconds * FPS))
    for pos in range(n):
        progress = pos / max(1, n - 1)
        idx = round(start_idx + progress * (end_idx - start_idx))
        frame = overlay_frame(clip, idx, theme="dark", label=label, hero=hero)
        frames.append(frame)
    return frames


def lure_result_card(seconds: float = 3.0) -> list[Image.Image]:
    canvas = Image.new("RGB", SIZE, NAVY_2)
    draw = ImageDraw.Draw(canvas)
    centered_text(draw, 250, "After ingest:", fill=WHITE, fnt=FONTS["title"])
    centered_text(draw, 355, "14.90–35.92×", fill=ORANGE, fnt=FONTS["display"])
    centered_text(draw, 465, "follow-up speedup", fill=WHITE, fnt=FONTS["h"])
    centered_text(draw, 570, "0/93 observed paired drift", fill=(74, 222, 128), fnt=FONTS["h"])
    centered_text(draw, 710, "first query still pays", fill=DIM_WHITE, fnt=FONTS["small"])
    return hold(canvas, seconds)


def render_paper_lure_cut(clips: list[ClipData], out_dir: Path, *, scored: bool = False) -> Path:
    display_wall = decode_display_crops(clips[0].spec, fps=24.0)
    display_landscape = decode_display_crops(clips[2].spec, fps=24.0)
    frames: list[Image.Image] = []
    frames.extend(opening_question(seconds=1.8))
    frames.extend(lure_raw_pass(clips[0], display_wall, seconds=3.0, label="watch first"))
    frames.extend(freeze_question(clips[0], display_wall, seconds=1.0))
    frames.extend(
        lure_overlay_pass(
            clips[0],
            seconds=4.5,
            hero="the wall is mostly paid",
            start_idx=1,
            end_idx=4,
        )
    )
    frames.extend(lure_result_card(seconds=3.2))
    frames.extend(
        lure_raw_pass(
            clips[2],
            display_landscape,
            seconds=2.2,
            label="not every scene is the wall",
        )
    )
    frames.extend(
        lure_overlay_pass(
            clips[2],
            seconds=4.2,
            hero="camera motion spends more",
            start_idx=1,
            end_idx=len(clips[2].crops) - 1,
        )
    )
    frames.extend(end_card("dark", seconds=5.0))
    stem = "paper_lure_cut_scored" if scored else "paper_lure_cut"
    out_path = out_dir / f"{stem}.mp4"
    if scored:
        silent_path = out_dir / "paper_lure_cut.mp4"
        write_mp4(frames, silent_path, fps=FPS)
        mux_audio(silent_path, out_path, duration_s=probe_duration_s(silent_path))
    else:
        write_mp4(frames, out_path, fps=FPS)
    thumbnail(frames[round(FPS * 6.2)], out_dir / "thumbnails" / f"{stem}.png")
    return out_path


def synth_score_wav(
    out_path: Path,
    *,
    duration_s: float,
    accent_times_s: list[float],
    rewind_times_s: list[float] | None = None,
    tick_times_s: list[float] | None = None,
    soft_tick_times_s: list[float] | None = None,
    sample_rate: int = 48_000,
) -> None:
    """Write a minimal synthetic pulse/sweep bed for review-only reels."""

    out_path.parent.mkdir(parents=True, exist_ok=True)
    rewind_times_s = rewind_times_s or []
    tick_times_s = tick_times_s or []
    soft_tick_times_s = soft_tick_times_s or []
    total = max(1, round(duration_s * sample_rate))
    with wave.open(str(out_path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        for idx in range(total):
            t = idx / sample_rate
            fade_in_amp = min(1.0, t / 0.8)
            fade_out_amp = min(1.0, max(0.0, (duration_s - t) / 1.0))
            env = fade_in_amp * fade_out_amp
            sweep = 62.0 + 34.0 * (0.5 + 0.5 * math.sin(t * 0.21 * math.tau))
            sample = 0.13 * math.sin(t * sweep * math.tau)
            sample += 0.04 * math.sin(t * 124.0 * math.tau + 0.6 * math.sin(t * 0.8))
            sample += 0.018 * math.sin(t * 248.0 * math.tau)
            for accent in accent_times_s:
                dt = t - accent
                if 0 <= dt < 0.22:
                    hit_env = math.exp(-dt * 18.0)
                    sample += hit_env * (0.28 * math.sin(dt * 44.0 * math.tau))
                    sample += hit_env * (0.08 * math.sin(dt * 180.0 * math.tau))
            for tick in tick_times_s:
                dt = t - tick
                if 0 <= dt < 0.045:
                    tick_env = math.exp(-dt * 95.0)
                    sample += tick_env * 0.075 * math.sin(dt * 940.0 * math.tau)
            for tick in soft_tick_times_s:
                dt = t - tick
                if 0 <= dt < 0.060:
                    tick_env = math.exp(-dt * 72.0)
                    sample += tick_env * 0.035 * math.sin(dt * 620.0 * math.tau)
            for rewind in rewind_times_s:
                dt = t - rewind
                if 0 <= dt < 0.95:
                    rev_env = math.sin((dt / 0.95) * math.pi)
                    freq = 760.0 - 520.0 * (dt / 0.95)
                    flutter = 1.0 + 0.16 * math.sin(dt * 38.0 * math.tau)
                    sample += 0.19 * rev_env * math.sin(dt * freq * flutter * math.tau)
                    sample += 0.045 * rev_env * math.sin(dt * 95.0 * math.tau)
            sample *= env
            sample_i = max(-32767, min(32767, round(sample * 32767)))
            wav.writeframes(struct.pack("<h", sample_i))


def mux_audio(
    video_path: Path,
    out_path: Path,
    *,
    duration_s: float,
    accent_times: list[float] | None = None,
    rewind_times: list[float] | None = None,
    tick_times: list[float] | None = None,
    soft_tick_times: list[float] | None = None,
) -> None:
    accent_times = accent_times or [
        1.15,
        2.55,
        4.15,
        5.95,
        7.25,
        9.15,
        10.75,
        max(0.0, duration_s - 1.25),
    ]
    with tempfile.TemporaryDirectory(prefix="codec-through-score-") as tmp:
        wav_path = Path(tmp) / "score.wav"
        synth_score_wav(
            wav_path,
            duration_s=duration_s,
            accent_times_s=accent_times,
            rewind_times_s=rewind_times,
            tick_times_s=tick_times,
            soft_tick_times_s=soft_tick_times,
        )
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-i",
            str(wav_path),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(out_path),
        ]
        proc = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg audio mux failed for {out_path}")


def probe_duration_s(video_path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe failed for {video_path}: {proc.stderr.strip()}")
    return float(proc.stdout.strip())


def decode_all(
    specs: list[ClipSpec] | tuple[ClipSpec, ...] = CLIPS,
    fps: float = 12.0,
) -> list[ClipData]:
    out = []
    for spec in specs:
        if not spec.video_path.exists():
            raise FileNotFoundError(f"video not found for {spec.key}: {spec.video_path}")
        times, crops, details = decode_clip(spec, fps=fps)
        out.append(ClipData(spec=spec, times=times, crops=crops, details=details))
    return out


def render_rewind_trailer(clips: list[ClipData], values: dict[str, Any], out_dir: Path) -> Path:
    frames: list[Image.Image] = []
    frames.extend(title_card("dark", seconds=1.2))
    frames.extend(
        clip_sequence(
            clips[0],
            theme="dark",
            raw_seconds=1.1,
            overlay_seconds=1.3,
            label="WATCH FIRST · what actually changed?",
            hero="the wall did not move",
        )
    )
    frames.extend(result_beat(values, theme="dark", seconds=1.15))
    frames.extend(
        clip_sequence(
            clips[1],
            theme="dark",
            raw_seconds=0.8,
            overlay_seconds=0.9,
            label="local motion",
            hero="fresh evidence follows motion",
        )
    )
    frames.extend(ceiling_beat(theme="dark", seconds=0.9))
    frames.extend(
        clip_sequence(
            clips[2],
            theme="dark",
            raw_seconds=0.8,
            overlay_seconds=1.0,
            label="honesty check",
            hero="camera motion changes the bill",
        )
    )
    frames.extend(stream_beat(theme="dark", seconds=0.9))
    frames.extend(end_card("dark", seconds=1.5))
    out_path = out_dir / "cinematic_rewind_trailer.mp4"
    write_mp4(frames, out_path, fps=FPS)
    thumbnail(frames[round(FPS * 4.2)], out_dir / "thumbnails" / "cinematic_rewind_trailer.png")
    return out_path


def render_rewind_trailer_scored(
    clips: list[ClipData],
    values: dict[str, Any],
    out_dir: Path,
) -> Path:
    silent = render_rewind_trailer(clips, values, out_dir)
    scored = out_dir / "cinematic_rewind_trailer_scored.mp4"
    # Keep the audio version as a delivery experiment; the silent source remains
    # the canonical visual artifact.
    mux_audio(silent, scored, duration_s=probe_duration_s(silent))
    return scored


def paper_explainer_frame(
    clip: ClipData,
    idx: int,
    *,
    label: str,
    show_overlay: bool,
    show_budget: bool,
) -> Image.Image:
    canvas = Image.new("RGB", SIZE, WARM)
    draw = ImageDraw.Draw(canvas)
    transition = clip.details[idx - 1] if idx > 0 else None
    image = (
        overlay_boxes(clip.crops[idx], transition, mode="fresh")
        if show_overlay
        else clip.crops[idx]
    )
    fit_on_canvas(canvas, image, (95, 170, 1265, 850), border=INK, shadow=True)
    draw_text(draw, (95, 90), label, fill=INK, fnt=FONTS["title"])
    stats = stats_for(clip.details, idx)
    rounded_rect(draw, (1330, 190, 1810, 650), fill=WHITE, outline=FAINT, radius=26)
    if show_budget:
        draw_text(draw, (1370, 235), "routing budget", fill=INK, fnt=FONTS["h"])
        draw_budget_hero(draw, 1370, 305, stats, large=True, dark=False)
    else:
        draw_text(draw, (1370, 235), "watch first", fill=INK, fnt=FONTS["h"])
        draw_text(draw, (1370, 310), "planner hidden", fill=MUTED, fnt=FONTS["h"])
        draw_text(
            draw,
            (1370, 390),
            "no budget reveal yet",
            fill=MUTED,
            fnt=FONTS["small"],
        )
    draw_text(
        draw,
        (1370, 560),
        "fixed-backend policy; visualization summary",
        fill=MUTED,
        fnt=FONTS["tiny"],
    )
    draw_text(
        draw,
        (95, 920),
        f"{clip.spec.benchmark} {clip.spec.video_id} · {clip.spec.role}",
        fill=MUTED,
        fnt=FONTS["small"],
    )
    return canvas


def render_paper_explainer(clips: list[ClipData], values: dict[str, Any], out_dir: Path) -> Path:
    frames: list[Image.Image] = []
    frames.extend(title_card("paper", seconds=1.1))
    for clip in clips:
        idxs = [0, max(1, len(clip.crops) // 3), max(1, 2 * len(clip.crops) // 3)]
        for idx in idxs:
            frame = paper_explainer_frame(
                clip,
                idx,
                label="raw evidence first",
                show_overlay=False,
                show_budget=False,
            )
            frames.extend(hold(frame, 0.23))
        rewind = paper_explainer_frame(
            clip,
            idxs[-1],
            label="rewind: ask what stayed paid",
            show_overlay=False,
            show_budget=False,
        )
        frames.extend(hold(rewind, 0.35))
        for idx in idxs[1:]:
            frame = paper_explainer_frame(
                clip,
                idx,
                label="replay with fresh blocks",
                show_overlay=True,
                show_budget=True,
            )
            frames.extend(hold(frame, 0.42))
    frames.extend(result_beat(values, theme="paper", seconds=1.25))
    frames.extend(ceiling_beat(theme="paper", seconds=1.0))
    frames.extend(end_card("paper", seconds=1.4))
    out_path = out_dir / "paper_explainer_cut.mp4"
    write_mp4(frames, out_path, fps=FPS)
    thumbnail(frames[round(FPS * 3.0)], out_dir / "thumbnails" / "paper_explainer_cut.png")
    return out_path


def render_social_cut(clips: list[ClipData], values: dict[str, Any], out_dir: Path) -> Path:
    frames: list[Image.Image] = []
    frames.extend(title_card("dark", seconds=0.85))
    for clip, hero in (
        (clips[0], "mostly reused"),
        (clips[1], "motion is local"),
        (clips[2], "not every scene is easy"),
    ):
        frames.extend(
            clip_sequence(
                clip,
                theme="dark",
                raw_seconds=0.55,
                overlay_seconds=0.62,
                label="watch first",
                hero=hero,
            )
        )
    frames.extend(result_beat(values, theme="dark", seconds=0.85))
    frames.extend(ceiling_beat(theme="dark", seconds=0.65))
    frames.extend(end_card("dark", seconds=1.0))
    out_path = out_dir / "social_punch_cut.mp4"
    write_mp4(frames, out_path, fps=FPS)
    thumbnail(frames[round(FPS * 2.0)], out_dir / "thumbnails" / "social_punch_cut.png")
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=OUT_ROOT)
    parser.add_argument(
        "--clip-manifest",
        type=Path,
        help=(
            "Optional JSON list, or object with a clips list, containing video_path, "
            "start_s, end_s, and optional key/benchmark/item_id/video_id/role fields."
        ),
    )
    parser.add_argument("--video-path", type=Path, help="Optional single custom input video.")
    parser.add_argument("--start-s", type=float, default=0.0)
    parser.add_argument("--end-s", type=float)
    parser.add_argument("--key", default="custom_00")
    parser.add_argument("--benchmark", default="custom")
    parser.add_argument("--item-id", default="custom:00")
    parser.add_argument("--video-id", default="custom")
    parser.add_argument("--role", default="custom routing window")
    parser.add_argument(
        "--result-mode",
        choices=("paper", "none"),
        default="paper",
        help=(
            "Use 'paper' for the teaser money-shot, or 'none' for pure routing "
            "visualization on arbitrary/custom clips."
        ),
    )
    parser.add_argument(
        "--variant",
        choices=(
            "all",
            "minimal-teaser",
            "minimal-teaser-scored",
            "title-probe",
            "title-probe-scored",
            "rewind",
            "rewind-scored",
            "paper",
            "paper-lure",
            "paper-lure-scored",
            "anchored-lure",
            "anchored-lure-scored",
            "social",
        ),
        default="all",
    )
    args = parser.parse_args()
    if args.clip_manifest is not None and args.video_path is not None:
        raise ValueError("use either --clip-manifest or --video-path, not both")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "thumbnails").mkdir(parents=True, exist_ok=True)
    if args.clip_manifest is not None:
        specs = load_clip_specs_from_manifest(args.clip_manifest)
    elif args.video_path is not None:
        specs = [single_clip_spec_from_args(args)]
    else:
        specs = list(CLIPS)
    clips = decode_all(specs, fps=12.0)
    three_clip_variants = {
        "all",
        "minimal-teaser",
        "minimal-teaser-scored",
        "paper-lure",
        "paper-lure-scored",
        "rewind",
        "rewind-scored",
        "paper",
        "social",
    }
    if len(clips) < 3 and args.variant in three_clip_variants:
        raise ValueError(
            f"--variant {args.variant} requires at least three clips; "
            "use --variant anchored-lure or provide a three-clip manifest"
        )
    values = load_story_values()
    outputs: list[Path] = []
    if args.variant in ("all", "minimal-teaser"):
        outputs.append(render_minimal_teaser_cut(clips, args.out_dir))
    if args.variant in ("all", "minimal-teaser-scored"):
        outputs.append(render_minimal_teaser_cut(clips, args.out_dir, scored=True))
    if args.variant == "title-probe":
        outputs.append(render_title_motion_probe(args.out_dir))
    if args.variant == "title-probe-scored":
        outputs.append(render_title_motion_probe(args.out_dir, scored=True))
    if args.variant in ("all", "paper-lure"):
        outputs.append(render_paper_lure_cut(clips, args.out_dir))
    if args.variant in ("all", "paper-lure-scored"):
        outputs.append(render_paper_lure_cut(clips, args.out_dir, scored=True))
    if args.variant in ("all", "anchored-lure"):
        outputs.append(render_anchored_lure_cut(clips, args.out_dir, result_mode=args.result_mode))
    if args.variant in ("all", "anchored-lure-scored"):
        outputs.append(
            render_anchored_lure_cut(
                clips,
                args.out_dir,
                scored=True,
                result_mode=args.result_mode,
            )
        )
    if args.variant in ("all", "rewind"):
        outputs.append(render_rewind_trailer(clips, values, args.out_dir))
    if args.variant in ("all", "rewind-scored"):
        outputs.append(render_rewind_trailer_scored(clips, values, args.out_dir))
    if args.variant in ("all", "paper"):
        outputs.append(render_paper_explainer(clips, values, args.out_dir))
    if args.variant in ("all", "social"):
        outputs.append(render_social_cut(clips, values, args.out_dir))

    manifest = {
        "purpose": (
            "Cinematic exploratory reels using exact routing masks and checked paper values."
        ),
        "science_guardrails": [
            (
                "orange overlay on source clips is Qwen routing freshness evidence, "
                "not semantic saliency"
            ),
            (
                "benchmark title cards avoid orange grid blocks; the closing title probe "
                "is synthetic generated-frame planner output, not benchmark evidence"
            ),
            "C-PERSIST/C-VISION/C-STREAM beats are paper-level regime lanes, not per-clip masks",
            "rewind/slowdown repeats rendered frames; it does not recompute planner decisions",
            "first frame remains an unscored reference frame",
            (
                "synthetic audio, when present, is a review-only communication layer "
                "with no scientific meaning"
            ),
            (
                "title_motion_probe applies the same planner path to generated title "
                "frames; it is a synthetic communication joke, not benchmark evidence"
            ),
        ],
        "values": values,
        "result_mode": args.result_mode,
        "clips": [
            {
                "key": clip.spec.key,
                "benchmark": clip.spec.benchmark,
                "video_id": clip.spec.video_id,
                "item_id": clip.spec.item_id,
                "role": clip.spec.role,
                "start_s": clip.spec.start_s,
                "end_s": clip.spec.end_s,
                "source_video": safe_rel(clip.spec.video_path),
                "source_jsonl": (
                    safe_rel(clip.spec.source_jsonl) if clip.spec.source_jsonl is not None else None
                ),
                "frames": len(clip.crops),
            }
            for clip in clips
        ],
        "outputs": [safe_rel(path) for path in outputs],
    }
    manifest_path = args.out_dir / "cinematic_reel_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"wrote {manifest_path}")
    for output in outputs:
        print(safe_rel(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
