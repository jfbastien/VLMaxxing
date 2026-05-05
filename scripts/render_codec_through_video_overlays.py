#!/usr/bin/env python3
"""Render exploratory video overlays for VLMaxxing mechanisms.

This is a review/demo renderer, not part of the paper build.  The spatial
overlay uses the exact Qwen routing-budget visualization policy from the
appendix candidate miner.  The right-hand state ledger is deliberately
separated: C-PERSIST, C-VISION, and C-STREAM are different regimes, so they
are shown as mechanism/claim lanes rather than as per-pixel saliency masks.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parent.parent
FIG1_SCRIPT_DIR = REPO_ROOT / "paper" / "arxiv" / "scripts"
if str(FIG1_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(FIG1_SCRIPT_DIR))

from find_fig1_candidates import (  # noqa: E402
    BENCHMARK_FRAME_SIZE,
    QWEN_BLOCK_SIZE,
    TRACK_A_MAX_AGE,
    active_crop,
    decode_frames_at_times,
    safe_rel,
    square_pad_frame,
    transition_details,
)

OUT_ROOT = (
    REPO_ROOT
    / "research"
    / "experiments"
    / "2026"
    / "artifacts"
    / "codec_through_video_overlays_exploratory"
)
GENERATED_DATA = REPO_ROOT / "paper" / "arxiv" / "generated" / "data"
VIDEO_BOX = (40, 110, 1040, 790)
PANEL_BOX = (1080, 110, 1560, 790)
OUTPUT_SIZE = (1600, 900)
REEL_FPS = 24.0
TITLE_CARD_SECONDS = 1.0

INK = (15, 23, 42)
MUTED = (71, 85, 105)
FAINT = (226, 232, 240)
PANEL = (248, 250, 252)
GREEN = (22, 163, 74)
GREEN_SOFT = (220, 252, 231)
YELLOW = (234, 179, 8)
ORANGE = (249, 115, 22)
ORANGE_DARK = (194, 65, 12)
RED = (220, 38, 38)
BLUE = (37, 99, 235)
PURPLE = (124, 58, 237)
WHITE = (255, 255, 255)
TRANSPARENT = (0, 0, 0, 0)

PAPER_TITLE = "VLMaxxing through FrameMogging"
PAPER_SUBTITLE = "Training-Free Anti-Recomputation for Video Vision-Language Models"
PAPER_AUTHORS = "JF Bastien · Sam D'Amico"


@dataclass(frozen=True)
class ClipSpec:
    key: str
    benchmark: str
    item_id: str
    video_id: str
    role: str
    video_path: Path
    source_jsonl: Path
    start_s: float
    end_s: float


CLIPS = (
    ClipSpec(
        key="tomato_0298_00",
        benchmark="TOMATO",
        item_id="tomato:rotation:0298-00",
        video_id="0298-00",
        role="high-reuse routing example",
        video_path=REPO_ROOT
        / "data"
        / "benchmarks"
        / "tomato"
        / "videos"
        / "object"
        / "0298-00.mp4",
        source_jsonl=REPO_ROOT
        / "research"
        / "experiments"
        / "2026"
        / "artifacts"
        / "phase1_6_tomato_motion_holdout_mean_age4.jsonl",
        start_s=0.0,
        end_s=2.0,
    ),
    ClipSpec(
        key="videomme_380",
        benchmark="VideoMME",
        item_id="videomme:medium:380-3",
        video_id="380",
        role="VideoMME visual anchor",
        video_path=REPO_ROOT / "data" / "benchmarks" / "videomme" / "videos" / "2Bns2m5Bg4M.mp4",
        source_jsonl=REPO_ROOT
        / "research"
        / "experiments"
        / "2026"
        / "artifacts"
        / "phase1_29B_dev30_artifact_20260424"
        / "artifact_results.jsonl",
        start_s=206.39,
        end_s=207.89,
    ),
    ClipSpec(
        key="videomme_267",
        benchmark="VideoMME",
        item_id="videomme:short:267-2",
        video_id="267",
        role="lower-reuse boundary",
        video_path=REPO_ROOT / "data" / "benchmarks" / "videomme" / "videos" / "Atf_Af1q_5w.mp4",
        source_jsonl=REPO_ROOT
        / "research"
        / "experiments"
        / "2026"
        / "artifacts"
        / "phase1_29B_short_n20_calibration_20260423"
        / "artifact_results.jsonl",
        start_s=0.0,
        end_s=1.0,
    ),
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
        if bold
        else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    )
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def paper_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Use a paper-like serif face for the title card.

    The manuscript body is LaTeX serif. The exact Computer/Latin Modern font is
    not necessarily installed in every local video environment, so STIX/Times
    are the closest system-safe scientific-paper fallbacks.
    """

    tectonic_fonts = sorted(
        (Path.home() / "Library" / "Caches" / "Tectonic" / "bundles" / "data").glob(
            "*/lmroman10-regular.otf"
        )
    )
    candidates = (
        *[str(path) for path in tectonic_fonts],
        "/System/Library/Fonts/Supplemental/STIXTwoText.ttf",
        "/System/Library/Fonts/Supplemental/STIXGeneral.otf",
        "/System/Library/Fonts/Times.ttc",
        "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
    )
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


FONTS = {
    "title": font(34, bold=True),
    "subtitle": font(18),
    "h": font(22, bold=True),
    "body": font(17),
    "small": font(14),
    "tiny": font(12),
    "number": font(30, bold=True),
    "number_small": font(22, bold=True),
    "paper_title": paper_font(66),
    "paper_subtitle": paper_font(33),
    "paper_author": paper_font(26),
}


def text_size(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.ImageFont) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def draw_text_supersampled(
    image: Image.Image,
    xy: tuple[int, int],
    text: str,
    *,
    fill: tuple[int, int, int] = INK,
    fnt: ImageFont.ImageFont,
    scale: int = 3,
) -> None:
    """Render thin serif title-card text with less video-visible aliasing."""

    try:
        path = fnt.path
        size = fnt.size
        high_font = ImageFont.truetype(path, size * scale)
    except (AttributeError, OSError):
        ImageDraw.Draw(image).text(xy, text, fill=fill, font=fnt)
        return

    probe = Image.new("RGBA", (1, 1), TRANSPARENT)
    probe_draw = ImageDraw.Draw(probe)
    bbox = probe_draw.textbbox((0, 0), text, font=high_font)
    pad = 8 * scale
    layer_w = bbox[2] - bbox[0] + pad * 2
    layer_h = bbox[3] - bbox[1] + pad * 2
    layer = Image.new("RGBA", (layer_w, layer_h), TRANSPARENT)
    layer_draw = ImageDraw.Draw(layer)
    layer_draw.text((pad - bbox[0], pad - bbox[1]), text, fill=(*fill, 255), font=high_font)
    down = layer.resize(
        (max(1, round(layer_w / scale)), max(1, round(layer_h / scale))), Image.Resampling.LANCZOS
    )
    image.paste(down, (xy[0] - round(pad / scale), xy[1] - round(pad / scale)), down)


def draw_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    *,
    fill: tuple[int, int, int] = INK,
    fnt: ImageFont.ImageFont | None = None,
) -> None:
    draw.text(xy, text, fill=fill, font=fnt or FONTS["body"])


def draw_centered(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    *,
    fill: tuple[int, int, int] = INK,
    fnt: ImageFont.ImageFont | None = None,
) -> None:
    fnt = fnt or FONTS["body"]
    w, h = text_size(draw, text, fnt)
    x0, y0, x1, y1 = box
    draw.text((x0 + (x1 - x0 - w) // 2, y0 + (y1 - y0 - h) // 2), text, fill=fill, font=fnt)


def rounded_rect(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    *,
    fill: tuple[int, int, int] = WHITE,
    outline: tuple[int, int, int] = FAINT,
    radius: int = 16,
    width: int = 2,
) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def bar(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    fraction: float,
    *,
    left_color: tuple[int, int, int] = GREEN,
    right_color: tuple[int, int, int] = ORANGE,
    outline: tuple[int, int, int] = FAINT,
) -> None:
    x0, y0, x1, y1 = box
    fraction = max(0.0, min(1.0, float(fraction)))
    split = int(round(x0 + (x1 - x0) * fraction))
    draw.rectangle((x0, y0, split, y1), fill=left_color)
    draw.rectangle((split, y0, x1, y1), fill=right_color)
    draw.rectangle(box, outline=outline, width=1)


def empty_bar(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    *,
    fill: tuple[int, int, int] = (241, 245, 249),
    outline: tuple[int, int, int] = FAINT,
) -> None:
    draw.rectangle(box, fill=fill)
    draw.rectangle(box, outline=outline, width=1)


def draw_pill(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    *,
    fill: tuple[int, int, int],
    outline: tuple[int, int, int],
    text_fill: tuple[int, int, int] = INK,
    fnt: ImageFont.ImageFont | None = None,
) -> tuple[int, int, int, int]:
    fnt = fnt or FONTS["small"]
    w, h = text_size(draw, text, fnt)
    x, y = xy
    box = (x, y, x + w + 24, y + h + 14)
    rounded_rect(draw, box, fill=fill, outline=outline, radius=18, width=2)
    draw.text((x + 12, y + 7), text, fill=text_fill, font=fnt)
    return box


def fit_image(
    image: Image.Image, box: tuple[int, int, int, int]
) -> tuple[Image.Image, tuple[int, int]]:
    x0, y0, x1, y1 = box
    max_w = x1 - x0
    max_h = y1 - y0
    scale = min(max_w / image.width, max_h / image.height)
    resized = image.resize(
        (max(1, round(image.width * scale)), max(1, round(image.height * scale))),
        Image.Resampling.LANCZOS,
    )
    return resized, (x0 + (max_w - resized.width) // 2, y0 + (max_h - resized.height) // 2)


def normalized_boxes_to_pixels(
    boxes: list[list[float]] | list[tuple[float, float, float, float]],
    image: Image.Image,
) -> list[tuple[int, int, int, int]]:
    out = []
    for x0, y0, x1, y1 in boxes:
        out.append(
            (
                int(round(x0 * image.width)),
                int(round(y0 * image.height)),
                int(round(x1 * image.width)),
                int(round(y1 * image.height)),
            )
        )
    return out


def overlay_boxes(
    image: Image.Image,
    transition: dict[str, Any] | None,
    *,
    mode: str,
) -> Image.Image:
    if transition is None:
        return image.copy()
    rgba = image.convert("RGBA")
    overlay = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")

    if mode == "audit":
        static_boxes = transition.get("static_reused_boxes", transition.get("static_boxes", []))
        shifted_boxes = transition.get("shifted_reused_boxes", transition.get("shifted_boxes", []))
        for box in normalized_boxes_to_pixels(static_boxes, image):
            draw.rectangle(box, fill=(22, 163, 74, 30), outline=(22, 163, 74, 60), width=1)
        for box in normalized_boxes_to_pixels(shifted_boxes, image):
            draw.rectangle(box, fill=(234, 179, 8, 50), outline=(234, 179, 8, 120), width=1)
        for box in normalized_boxes_to_pixels(transition.get("fresh_boxes", []), image):
            draw.rectangle(box, fill=(249, 115, 22, 115), outline=(194, 65, 12, 230), width=2)
    else:
        for box in normalized_boxes_to_pixels(transition.get("fresh_boxes", []), image):
            draw.rectangle(box, fill=(249, 115, 22, 88), outline=(194, 65, 12, 230), width=2)

    return Image.alpha_composite(rgba, overlay).convert("RGB")


def transition_percentages(transition: dict[str, Any] | None) -> dict[str, float]:
    if transition is None:
        return {
            "has_transition": 0.0,
            "reused": 0.0,
            "fresh": 0.0,
            "stale": 0.0,
            "static": 0.0,
            "shifted": 0.0,
        }
    static = len(transition.get("static_reused_boxes", transition.get("static_boxes", [])))
    shifted = len(transition.get("shifted_reused_boxes", transition.get("shifted_boxes", [])))
    fresh = len(transition.get("fresh_boxes", []))
    total = max(1, static + shifted + fresh)
    return {
        "has_transition": 1.0,
        "reused": float(transition.get("reuse_ratio_active", (static + shifted) / total)),
        "fresh": float(transition.get("fresh_fraction_active", fresh / total)),
        "stale": float(transition.get("stale_fraction_active", 0.0)),
        "static": static / total,
        "shifted": shifted / total,
    }


def pct_pair(reuse: float) -> tuple[int, int]:
    reuse_pct = int(math.floor(max(0.0, min(1.0, reuse)) * 100.0 + 0.5))
    return reuse_pct, 100 - reuse_pct


def pct_pair_from_stats(stats: dict[str, float]) -> tuple[int, int]:
    reuse_pct = int(math.floor(max(0.0, min(1.0, stats["reused"])) * 100.0 + 0.5))
    fresh_pct = int(math.floor(max(0.0, min(1.0, stats["fresh"])) * 100.0 + 0.5))
    if abs((stats["reused"] + stats["fresh"]) - 1.0) < 0.02:
        fresh_pct = 100 - reuse_pct
    return reuse_pct, fresh_pct


def load_story_values() -> dict[str, Any]:
    timeline = load_json(GENERATED_DATA / "c_persist_timeline_snapshot.json")
    sparse = load_json(GENERATED_DATA / "measured_sparse_execution_snapshot.json")
    stream = load_json(
        REPO_ROOT
        / "research"
        / "experiments"
        / "2026"
        / "artifacts"
        / "phase1_30_scaleout_streaming"
        / "pair_summary.json"
    )
    return {
        "persist_q3_speedup": float(timeline["paired_q3_fixed_over_adaptive_speedup"]),
        "persist_tail_reduction": float(timeline["paired_q3_tail_token_reduction"]),
        "persist_adaptive_tokens": int(round(float(timeline["adaptive_q3_tail_prompt_tokens"]))),
        "persist_fixed_tokens": int(round(float(timeline["fixed_q3_tail_prompt_tokens"]))),
        "vision_speedup": float(sparse["gemma_32f_short"]["observed_e2e"]),
        "vision_reduction": float(sparse["gemma_32f_short"]["vision_reduction"]),
        "vision_n": int(sparse["gemma_32f_short"]["n"]),
        "stream_speedup": float(stream["amortized_speedup_cold_over_streaming"]),
        "stream_acc_delta": float(stream["accuracy_delta_streaming_minus_cold"]),
    }


def cadence_label(fps: float) -> str:
    if abs(fps - 12.0) < 1e-6:
        return "12 fps"
    return f"{fps:g} fps resampled cadence"


def decode_clip(
    spec: ClipSpec, fps: float
) -> tuple[list[float], list[Image.Image], list[dict[str, Any]]]:
    n = max(2, int(math.ceil((spec.end_s - spec.start_s) * fps)) + 1)
    times = [spec.start_s + idx / fps for idx in range(n)]
    times = [min(spec.end_s, t) for t in times]
    if times[-1] < spec.end_s:
        times.append(spec.end_s)
    frames = decode_frames_at_times(spec.video_path, times)
    padded: list[Image.Image] = []
    active_boxes: list[tuple[int, int, int, int]] = []
    crops: list[Image.Image] = []
    for frame in frames:
        padded_frame, active_box = square_pad_frame(frame)
        padded.append(padded_frame)
        active_boxes.append(active_box)
        crops.append(active_crop(padded_frame, active_box))
    details = transition_details(padded, active_boxes)
    return times, crops, details


def draw_frame_header(
    draw: ImageDraw.ImageDraw,
    spec: ClipSpec,
    frame: Image.Image,
    *,
    title: str,
    subtitle: str,
) -> None:
    draw_text(draw, (36, 24), title, fnt=FONTS["title"])
    draw_text(draw, (38, 64), subtitle, fill=MUTED, fnt=FONTS["subtitle"])
    draw_text(
        draw,
        (38, frame.height - 34),
        f"{spec.benchmark} {spec.video_id} · {spec.role} · {spec.start_s:.2f}-{spec.end_s:.2f}s",
        fill=MUTED,
        fnt=FONTS["small"],
    )


def draw_budget_card(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    stats: dict[str, float],
    *,
    title: str = "routing budget",
) -> None:
    rounded_rect(draw, box, fill=WHITE, outline=FAINT, radius=18, width=2)
    x0, y0, x1, _ = box
    draw_text(draw, (x0 + 22, y0 + 18), title, fill=MUTED, fnt=FONTS["small"])
    if not stats.get("has_transition"):
        draw_text(draw, (x0 + 22, y0 + 50), "no prior frame", fill=MUTED, fnt=FONTS["number_small"])
        draw_text(
            draw,
            (x0 + 22, y0 + 88),
            "transition not scored yet",
            fill=INK,
            fnt=FONTS["small"],
        )
        draw_text(
            draw,
            (x0 + 22, y0 + 122),
            "first frame establishes the reference state",
            fill=MUTED,
            fnt=FONTS["small"],
        )
        empty_bar(draw, (x0 + 22, y0 + 178, x1 - 22, y0 + 194))
        return

    reuse_pct, fresh_pct = pct_pair_from_stats(stats)
    draw_text(draw, (x0 + 22, y0 + 48), f"{reuse_pct}% reused", fill=GREEN, fnt=FONTS["number"])
    draw_text(
        draw, (x0 + 22, y0 + 88), f"{fresh_pct}% fresh", fill=ORANGE, fnt=FONTS["number_small"]
    )
    draw_text(
        draw,
        (x0 + 22, y0 + 122),
        f"static {stats['static']:.0%} + shifted {stats['shifted']:.0%} → reused",
        fill=INK,
        fnt=FONTS["small"],
    )
    draw_text(
        draw,
        (x0 + 22, y0 + 147),
        f"age-expired: {stats['stale']:.0%}",
        fill=MUTED,
        fnt=FONTS["small"],
    )
    bar(draw, (x0 + 22, y0 + 178, x1 - 22, y0 + 194), stats["reused"])


def render_audit_frame(
    spec: ClipSpec,
    image: Image.Image,
    transition: dict[str, Any] | None,
    *,
    fps: float,
    frame_idx: int,
    frame_count: int,
) -> Image.Image:
    canvas = Image.new("RGB", (1280, 720), WHITE)
    draw = ImageDraw.Draw(canvas)
    draw_frame_header(
        draw,
        spec,
        canvas,
        title="Exact routing-budget overlay",
        subtitle=(
            f"{cadence_label(fps)} replay of the Qwen policy: static/shifted reused; "
            "novel or age-expired blocks are fresh."
        ),
    )
    overlay = overlay_boxes(image, transition, mode="audit")
    fitted, pos = fit_image(overlay, (36, 105, 905, 640))
    canvas.paste(fitted, pos)
    draw.rectangle(
        (pos[0], pos[1], pos[0] + fitted.width, pos[1] + fitted.height), outline=INK, width=2
    )

    stats = transition_percentages(transition)
    draw_budget_card(draw, (930, 130, 1238, 352), stats, title="current transition")
    draw_pill(
        draw, (930, 380), "green: static reused", fill=GREEN_SOFT, outline=GREEN, text_fill=GREEN
    )
    draw_pill(draw, (930, 430), "yellow: shifted reused", fill=(254, 249, 195), outline=YELLOW)
    draw_pill(
        draw,
        (930, 480),
        "orange: fresh bought",
        fill=(255, 237, 213),
        outline=ORANGE,
        text_fill=ORANGE_DARK,
    )
    draw_text(
        draw,
        (930, 555),
        "Freshness evidence, not object localization.",
        fill=MUTED,
        fnt=FONTS["small"],
    )
    draw_text(draw, (1128, 646), f"{frame_idx + 1}/{frame_count}", fill=MUTED, fnt=FONTS["small"])
    return canvas


def draw_cache_bricks(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    *,
    n: int,
    green: int,
    orange: int,
    blue: int = 0,
) -> None:
    gap = 4
    w = 22
    h = 18
    for idx in range(n):
        color = (241, 245, 249)
        outline = (203, 213, 225)
        if idx < green:
            color = GREEN_SOFT
            outline = GREEN
        if green <= idx < green + orange:
            color = (255, 237, 213)
            outline = ORANGE
        if green + orange <= idx < green + orange + blue:
            color = (219, 234, 254)
            outline = BLUE
        draw.rounded_rectangle(
            (x + idx * (w + gap), y, x + idx * (w + gap) + w, y + h),
            radius=4,
            fill=color,
            outline=outline,
            width=1,
        )


def draw_routing_timeline(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    history: list[dict[str, float]],
    current_idx: int,
) -> None:
    x0, y0, x1, y1 = box
    rounded_rect(draw, box, fill=WHITE, outline=FAINT, radius=10, width=1)
    if len(history) <= 1:
        draw_text(draw, (x0 + 10, y0 + 10), "budget over window", fill=MUTED, fnt=FONTS["tiny"])
        return

    usable = history[1:]
    n = len(usable)
    inner_x0 = x0 + 10
    inner_x1 = x1 - 10
    inner_y0 = y0 + 28
    inner_y1 = y1 - 12
    draw_text(draw, (x0 + 10, y0 + 8), "budget over window", fill=MUTED, fnt=FONTS["tiny"])
    col_w = max(2.0, (inner_x1 - inner_x0) / n)
    for idx, stat in enumerate(usable):
        left = int(round(inner_x0 + idx * col_w))
        right = int(round(inner_x0 + (idx + 1) * col_w - 1))
        if right <= left:
            right = left + 1
        reuse = max(0.0, min(1.0, stat["reused"]))
        split = int(round(inner_y1 - (inner_y1 - inner_y0) * reuse))
        draw.rectangle((left, inner_y0, right, split), fill=ORANGE)
        draw.rectangle((left, split, right, inner_y1), fill=GREEN)

    marker_idx = max(1, min(current_idx, len(history) - 1)) - 1
    marker_x = int(round(inner_x0 + (marker_idx + 0.5) * col_w))
    draw.line((marker_x, inner_y0 - 4, marker_x, inner_y1 + 5), fill=INK, width=3)
    draw.polygon(
        ((marker_x - 5, inner_y0 - 8), (marker_x + 5, inner_y0 - 8), (marker_x, inner_y0 - 2)),
        fill=INK,
    )


def draw_pipeline_panel(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    stats: dict[str, float],
    values: dict[str, Any],
    *,
    history: list[dict[str, float]],
    current_idx: int,
    phase: float,
) -> None:
    rounded_rect(draw, box, fill=PANEL, outline=FAINT, radius=20, width=2)
    x0, y0, x1, _ = box
    draw_text(draw, (x0 + 24, y0 + 18), "state ledger", fnt=FONTS["h"])
    draw_text(
        draw,
        (x0 + 24, y0 + 48),
        "Per-clip routing budget + separate regime claims",
        fill=MUTED,
        fnt=FONTS["small"],
    )

    routing_y = y0 + 88
    draw_text(draw, (x0 + 24, routing_y), "Routing planner", fnt=FONTS["body"], fill=INK)
    if stats.get("has_transition"):
        reuse_pct, fresh_pct = pct_pair_from_stats(stats)
        bar(draw, (x0 + 24, routing_y + 30, x1 - 24, routing_y + 48), stats["reused"])
        draw_text(
            draw,
            (x0 + 24, routing_y + 58),
            f"reproduced here: {reuse_pct}% reused / {fresh_pct}% fresh",
            fill=MUTED,
            fnt=FONTS["small"],
        )
        draw_text(
            draw,
            (x0 + 24, routing_y + 80),
            f"age-expired refresh: {stats['stale']:.0%}",
            fill=MUTED,
            fnt=FONTS["tiny"],
        )
    else:
        empty_bar(draw, (x0 + 24, routing_y + 30, x1 - 24, routing_y + 48))
        draw_text(
            draw,
            (x0 + 24, routing_y + 58),
            "no prior frame / transition not scored",
            fill=MUTED,
            fnt=FONTS["small"],
        )
        draw_text(
            draw,
            (x0 + 24, routing_y + 80),
            "first frame establishes the reference state",
            fill=MUTED,
            fnt=FONTS["tiny"],
        )
    draw_routing_timeline(
        draw,
        (x0 + 24, routing_y + 106, x1 - 24, routing_y + 178),
        history,
        current_idx,
    )

    persist_y = y0 + 292
    draw_text(draw, (x0 + 24, persist_y), "C-PERSIST", fnt=FONTS["body"], fill=GREEN)
    if phase < 0.34:
        step = "Q1 pays full ingest"
        green, orange, blue = 0, 10, 0
    elif phase < 0.67:
        step = "Q2 repairs newest tail"
        green, orange, blue = 8, 2, 0
    else:
        step = "Q3 reuses repaired cache"
        green, orange, blue = 9, 0, 1
    draw_cache_bricks(draw, x0 + 24, persist_y + 30, n=10, green=green, orange=orange, blue=blue)
    draw_text(draw, (x0 + 24, persist_y + 58), step, fill=INK, fnt=FONTS["small"])
    draw_text(
        draw,
        (x0 + 24, persist_y + 80),
        (
            f"reproduced here: Q3 {values['persist_fixed_tokens']}→"
            f"{values['persist_adaptive_tokens']} tail tok; {values['persist_q3_speedup']:.2f}×"
        ),
        fill=MUTED,
        fnt=FONTS["tiny"],
    )

    vision_y = y0 + 412
    draw_text(draw, (x0 + 24, vision_y), "C-VISION", fnt=FONTS["body"], fill=BLUE)
    keep = 1.0 - float(values["vision_reduction"])
    bar(
        draw,
        (x0 + 24, vision_y + 30, x1 - 24, vision_y + 48),
        keep,
        left_color=BLUE,
        right_color=FAINT,
    )
    draw_text(
        draw,
        (x0 + 24, vision_y + 58),
        f"reproduced here: {values['vision_reduction']:.0%} vision work skipped",
        fill=INK,
        fnt=FONTS["small"],
    )
    draw_text(
        draw,
        (x0 + 24, vision_y + 80),
        (
            f"Gemma 32f short: {values['vision_speedup']:.3f}× E2E, "
            f"n={values['vision_n']}; no per-clip mask"
        ),
        fill=MUTED,
        fnt=FONTS["tiny"],
    )

    stream_y = y0 + 532
    draw_text(draw, (x0 + 24, stream_y), "C-STREAM", fnt=FONTS["body"], fill=PURPLE)
    draw_cache_bricks(draw, x0 + 24, stream_y + 30, n=10, green=7, orange=3)
    draw_text(
        draw,
        (x0 + 24, stream_y + 58),
        "native-rate target: update state instead of replaying pixels",
        fill=INK,
        fnt=FONTS["small"],
    )
    draw_text(
        draw,
        (x0 + 24, stream_y + 80),
        (
            f"hypothesis / candidate bridge: {values['stream_speedup']:.2f}× but "
            f"Δacc {values['stream_acc_delta']:.3f}"
        ),
        fill=MUTED,
        fnt=FONTS["tiny"],
    )

    draw_text(
        draw,
        (x0 + 24, y0 + 640),
        "Orange overlay is per-clip; other lanes keep denominators separate.",
        fill=RED,
        fnt=FONTS["tiny"],
    )


def render_pipeline_frame(
    spec: ClipSpec,
    image: Image.Image,
    transition: dict[str, Any] | None,
    values: dict[str, Any],
    *,
    fps: float,
    history: list[dict[str, float]],
    frame_idx: int,
    frame_count: int,
) -> Image.Image:
    canvas = Image.new("RGB", OUTPUT_SIZE, WHITE)
    draw = ImageDraw.Draw(canvas)
    draw_frame_header(
        draw,
        spec,
        canvas,
        title="Codec-through VLM state visualization",
        subtitle=(
            f"{cadence_label(fps)} routing overlay; C-PERSIST / C-VISION / C-STREAM stay separate."
        ),
    )
    overlay = overlay_boxes(image, transition, mode="fresh")
    fitted, pos = fit_image(overlay, VIDEO_BOX)
    canvas.paste(fitted, pos)
    draw.rectangle(
        (pos[0], pos[1], pos[0] + fitted.width, pos[1] + fitted.height), outline=INK, width=2
    )
    draw_text(
        draw,
        (pos[0], pos[1] - 28),
        "video stream: orange blocks are fresh or age-expired visual evidence",
        fill=INK,
        fnt=FONTS["body"],
    )
    stats = transition_percentages(transition)
    phase = frame_idx / max(1, frame_count - 1)
    draw_pipeline_panel(
        draw,
        PANEL_BOX,
        stats,
        values,
        history=history,
        current_idx=frame_idx,
        phase=phase,
    )
    draw_text(draw, (1450, 830), f"{frame_idx + 1}/{frame_count}", fill=MUTED, fnt=FONTS["small"])
    return canvas


def render_clean_cinematic_frame(
    spec: ClipSpec,
    image: Image.Image,
    *,
    fps: float,
    frame_idx: int,
    frame_count: int,
) -> Image.Image:
    canvas = Image.new("RGB", OUTPUT_SIZE, WHITE)
    draw = ImageDraw.Draw(canvas)
    draw_frame_header(
        draw,
        spec,
        canvas,
        title="Watch the clip first",
        subtitle=f"Clean frames at {cadence_label(fps)}; no planner overlay yet.",
    )
    fitted, pos = fit_image(image, VIDEO_BOX)
    canvas.paste(fitted, pos)
    draw.rectangle(
        (pos[0], pos[1], pos[0] + fitted.width, pos[1] + fitted.height), outline=INK, width=2
    )
    rounded_rect(draw, PANEL_BOX, fill=PANEL, outline=FAINT, radius=20, width=2)
    x0, y0, _, _ = PANEL_BOX
    draw_text(draw, (x0 + 24, y0 + 24), "phase 1", fill=MUTED, fnt=FONTS["small"])
    draw_text(draw, (x0 + 24, y0 + 62), "watch the video", fnt=FONTS["h"])
    draw_text(
        draw,
        (x0 + 24, y0 + 110),
        "No colored blocks yet.",
        fill=MUTED,
        fnt=FONTS["small"],
    )
    draw_text(
        draw,
        (x0 + 24, y0 + 140),
        "This first pass establishes the scene before the algorithm view.",
        fill=MUTED,
        fnt=FONTS["small"],
    )
    draw_text(
        draw,
        (x0 + 24, y0 + 210),
        "Next:",
        fill=INK,
        fnt=FONTS["body"],
    )
    draw_text(
        draw,
        (x0 + 24, y0 + 244),
        "same frame size",
        fill=GREEN,
        fnt=FONTS["h"],
    )
    draw_text(
        draw,
        (x0 + 24, y0 + 284),
        "slow replay with exact fresh/reused blocks",
        fill=INK,
        fnt=FONTS["small"],
    )
    draw_text(draw, (1450, 830), f"{frame_idx + 1}/{frame_count}", fill=MUTED, fnt=FONTS["small"])
    return canvas


def render_cinematic_clip(
    spec: ClipSpec,
    crops: list[Image.Image],
    details: list[dict[str, Any]],
    history: list[dict[str, float]],
    values: dict[str, Any],
    *,
    source_fps: float,
    out_dir: Path,
    output_fps: float = 24.0,
    slow_display_fps: float = 4.0,
) -> Path:
    """Render a clean-then-slow explainer without changing planner decisions."""

    normal_repeat = max(1, int(round(output_fps / source_fps)))
    slow_repeat = max(normal_repeat, int(round(output_fps / slow_display_fps)))
    frames: list[Image.Image] = []

    for idx, crop in enumerate(crops):
        clean = render_clean_cinematic_frame(
            spec,
            crop,
            fps=source_fps,
            frame_idx=idx,
            frame_count=len(crops),
        )
        frames.extend([clean] * normal_repeat)

    for idx, crop in enumerate(crops):
        transition = details[idx - 1] if idx > 0 else None
        slow = render_pipeline_frame(
            spec,
            crop,
            transition,
            values,
            fps=source_fps,
            history=history,
            frame_idx=idx,
            frame_count=len(crops),
        )
        badge = ImageDraw.Draw(slow)
        rounded_rect(badge, (40, 790, 735, 845), fill=WHITE, outline=FAINT, radius=16, width=2)
        draw_text(
            badge,
            (62, 806),
            (
                f"phase 2: same {cadence_label(source_fps)} planner decisions, "
                f"played back at ~{slow_display_fps:g} fps for inspection"
            ),
            fill=INK,
            fnt=FONTS["small"],
        )
        frames.extend([slow] * slow_repeat)

    out_path = out_dir / f"{spec.key}_cinematic_explainer.mp4"
    write_mp4(frames, out_path, fps=output_fps)
    if frames:
        thumbnail(
            frames[min(len(frames) - 1, len(crops) * normal_repeat + slow_repeat)],
            out_dir / "thumbnails" / f"{out_path.stem}.png",
        )
    return out_path


def write_mp4(frames: list[Image.Image], out_path: Path, *, fps: float) -> None:
    if not frames:
        raise ValueError("no frames to encode")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    width, height = frames[0].size
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{width}x{height}",
        "-r",
        f"{fps}",
        "-i",
        "-",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "slow",
        "-crf",
        "17",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(out_path),
    ]
    proc = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    assert proc.stdin is not None
    try:
        for frame in frames:
            if frame.size != (width, height):
                raise ValueError("all frames must have identical dimensions")
            proc.stdin.write(frame.convert("RGB").tobytes())
    finally:
        proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError(f"ffmpeg failed for {out_path}")


def thumbnail(frame: Image.Image, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    frame.save(out_path)


def render_clip(
    spec: ClipSpec,
    *,
    fps: float,
    values: dict[str, Any],
    out_dir: Path,
    render_cinematic: bool,
) -> dict[str, Any]:
    if not spec.video_path.exists():
        raise FileNotFoundError(spec.video_path)
    times, crops, details = decode_clip(spec, fps=fps)
    history = [
        transition_percentages(None),
        *(transition_percentages(detail) for detail in details),
    ]
    audit_frames: list[Image.Image] = []
    pipeline_frames: list[Image.Image] = []
    transition_rows: list[dict[str, Any]] = []

    for idx, crop in enumerate(crops):
        transition = details[idx - 1] if idx > 0 else None
        audit_frames.append(
            render_audit_frame(
                spec, crop, transition, fps=fps, frame_idx=idx, frame_count=len(crops)
            )
        )
        pipeline_frames.append(
            render_pipeline_frame(
                spec,
                crop,
                transition,
                values,
                fps=fps,
                history=history,
                frame_idx=idx,
                frame_count=len(crops),
            )
        )
        stats = transition_percentages(transition)
        transition_rows.append(
            {
                "frame_index": idx,
                "time_s": times[idx],
                "reuse_ratio_active": stats["reused"],
                "fresh_fraction_active": stats["fresh"],
                "stale_fraction_active": stats["stale"],
                "static_fraction_active": stats["static"],
                "shifted_fraction_active": stats["shifted"],
            }
        )

    audit_path = out_dir / f"{spec.key}_routing_audit.mp4"
    pipeline_path = out_dir / f"{spec.key}_state_pipeline.mp4"
    write_mp4(audit_frames, audit_path, fps=fps)
    write_mp4(pipeline_frames, pipeline_path, fps=fps)
    thumbnail(
        audit_frames[min(1, len(audit_frames) - 1)],
        out_dir / "thumbnails" / f"{audit_path.stem}.png",
    )
    thumbnail(
        pipeline_frames[min(1, len(pipeline_frames) - 1)],
        out_dir / "thumbnails" / f"{pipeline_path.stem}.png",
    )
    cinematic_path = (
        render_cinematic_clip(
            spec, crops, details, history, values, source_fps=fps, out_dir=out_dir
        )
        if render_cinematic
        else None
    )
    record = {
        "key": spec.key,
        "benchmark": spec.benchmark,
        "item_id": spec.item_id,
        "video_id": spec.video_id,
        "role": spec.role,
        "source_video": safe_rel(spec.video_path),
        "source_jsonl": safe_rel(spec.source_jsonl),
        "start_s": spec.start_s,
        "end_s": spec.end_s,
        "fps": fps,
        "frame_count": len(crops),
        "audit_video": safe_rel(audit_path),
        "pipeline_video": safe_rel(pipeline_path),
        "transitions": transition_rows,
    }
    if cinematic_path is not None:
        record["cinematic_video"] = safe_rel(cinematic_path)
        record["cinematic_note"] = (
            "Planner decisions are computed at the listed fps; the second half repeats frames "
            "for slow playback only."
        )
    return record


def render_montage(records: list[dict[str, Any]], out_dir: Path, *, fps: float) -> None:
    """Make a compact chooser that plays the three pipeline videos side by side."""

    # Render directly from source crops instead of shrinking the full pipeline
    # frames; the montage has its own labels and uses the same transition-aware
    # budget display as the per-clip videos.
    spec_by_key = {spec.key: spec for spec in CLIPS}
    decoded_records: list[tuple[dict[str, Any], list[Image.Image], list[dict[str, Any]]]] = []
    max_len = 0
    for record in records:
        spec = spec_by_key[record["key"]]
        _, crops, details = decode_clip(spec, fps=fps)
        decoded_records.append((record, crops, details))
        max_len = max(max_len, len(crops))
    montage_frames: list[Image.Image] = []
    for idx in range(max_len):
        canvas = Image.new("RGB", (1600, 900), WHITE)
        draw = ImageDraw.Draw(canvas)
        draw_text(
            draw, (40, 28), "Three real windows, same exact routing policy", fnt=FONTS["title"]
        )
        draw_text(
            draw,
            (42, 70),
            (
                "Compare high reuse, VideoMME anchor, and lower-reuse boundary; "
                "see per-clip videos for full-size overlays."
            ),
            fill=MUTED,
            fnt=FONTS["subtitle"],
        )
        y = 120
        for record, crops, details in decoded_records:
            frame_idx = min(idx, len(crops) - 1)
            transition = details[frame_idx - 1] if frame_idx > 0 else None
            overlay = overlay_boxes(crops[frame_idx], transition, mode="fresh")
            fitted, pos = fit_image(overlay, (70, y + 10, 660, y + 230))
            canvas.paste(fitted, pos)
            draw.rectangle(
                (pos[0], pos[1], pos[0] + fitted.width, pos[1] + fitted.height),
                outline=INK,
                width=2,
            )
            draw_text(
                draw,
                (710, y + 8),
                f"{record['benchmark']} {record['video_id']}",
                fnt=FONTS["h"],
            )
            draw_text(draw, (710, y + 42), record["role"], fill=MUTED, fnt=FONTS["body"])
            stats = transition_percentages(transition)
            if stats["has_transition"]:
                reuse_pct, fresh_pct = pct_pair_from_stats(stats)
                draw_text(
                    draw, (710, y + 88), f"{reuse_pct}% reused", fill=GREEN, fnt=FONTS["number"]
                )
                draw_text(
                    draw,
                    (710, y + 126),
                    f"{fresh_pct}% fresh",
                    fill=ORANGE,
                    fnt=FONTS["number_small"],
                )
                draw_text(
                    draw,
                    (710, y + 154),
                    f"age-expired refresh: {stats['stale']:.0%}",
                    fill=MUTED,
                    fnt=FONTS["small"],
                )
                bar(draw, (710, y + 185, 1220, y + 204), stats["reused"])
            else:
                draw_text(
                    draw,
                    (710, y + 92),
                    "no prior frame",
                    fill=MUTED,
                    fnt=FONTS["number_small"],
                )
                draw_text(
                    draw,
                    (710, y + 130),
                    "transition not scored yet",
                    fill=MUTED,
                    fnt=FONTS["small"],
                )
                empty_bar(draw, (710, y + 185, 1220, y + 204))
            y += 250
        montage_frames.append(canvas)
    write_mp4(montage_frames, out_dir / "three_window_pipeline_montage.mp4", fps=fps)
    if montage_frames:
        thumbnail(
            montage_frames[min(1, len(montage_frames) - 1)],
            out_dir / "thumbnails" / "three_window_pipeline_montage.png",
        )


def render_title_card() -> Image.Image:
    canvas = Image.new("RGB", OUTPUT_SIZE, WHITE)
    draw = ImageDraw.Draw(canvas)
    title_w, title_h = text_size(draw, PAPER_TITLE, FONTS["paper_title"])
    subtitle_w, _ = text_size(draw, PAPER_SUBTITLE, FONTS["paper_subtitle"])
    authors_w, _ = text_size(draw, PAPER_AUTHORS, FONTS["paper_author"])
    tagline = "Video is mostly the same. Stop paying twice."
    tagline_w, _ = text_size(draw, tagline, FONTS["h"])
    center_x = OUTPUT_SIZE[0] // 2
    top = 270
    draw_text_supersampled(
        canvas,
        (center_x - title_w // 2, top),
        PAPER_TITLE,
        fill=INK,
        fnt=FONTS["paper_title"],
    )
    draw_text_supersampled(
        canvas,
        (center_x - subtitle_w // 2, top + title_h + 28),
        PAPER_SUBTITLE,
        fill=INK,
        fnt=FONTS["paper_subtitle"],
    )
    draw_text_supersampled(
        canvas,
        (center_x - authors_w // 2, top + title_h + 86),
        PAPER_AUTHORS,
        fill=MUTED,
        fnt=FONTS["paper_author"],
    )
    draw_text_supersampled(
        canvas,
        (center_x - tagline_w // 2, top + title_h + 154),
        tagline,
        fill=GREEN,
        fnt=FONTS["h"],
    )
    return canvas


def frames_from_video(path: Path, tmp_dir: Path) -> list[Image.Image]:
    tmp_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(path),
        str(tmp_dir / "frame_%05d.png"),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return [Image.open(frame).convert("RGB") for frame in sorted(tmp_dir.glob("frame_*.png"))]


def render_back_to_back_reel(records: list[dict[str, Any]], out_dir: Path) -> Path | None:
    cinematic_records = [record for record in records if "cinematic_video" in record]
    if not cinematic_records:
        return None

    tmp_root = out_dir / "_reel_frames"
    if tmp_root.exists():
        shutil.rmtree(tmp_root)
    title_frames = int(round(REEL_FPS * TITLE_CARD_SECONDS))
    frames: list[Image.Image] = [render_title_card()] * title_frames
    for record in cinematic_records:
        source = REPO_ROOT / record["cinematic_video"]
        clip_frames = frames_from_video(source, tmp_root / record["key"])
        frames.extend(clip_frames)

    out_path = out_dir / "all_clips_cinematic_reel.mp4"
    write_mp4(frames, out_path, fps=REEL_FPS)
    thumbnail(render_title_card(), out_dir / "thumbnails" / "all_clips_cinematic_reel_title.png")
    if frames:
        thumbnail(
            frames[min(len(frames) - 1, title_frames + 4)],
            out_dir / "thumbnails" / "all_clips_cinematic_reel.png",
        )
    shutil.rmtree(tmp_root)
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fps", type=float, default=12.0)
    parser.add_argument("--out-dir", type=Path, default=OUT_ROOT)
    parser.add_argument("--no-montage", action="store_true")
    parser.add_argument("--no-cinematic", action="store_true")
    parser.add_argument("--no-reel", action="store_true")
    args = parser.parse_args()

    values = load_story_values()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    records = [
        render_clip(
            spec,
            fps=args.fps,
            values=values,
            out_dir=args.out_dir,
            render_cinematic=not args.no_cinematic,
        )
        for spec in CLIPS
    ]
    if not args.no_montage:
        render_montage(records, args.out_dir, fps=args.fps)
    reel_path = None if args.no_reel else render_back_to_back_reel(records, args.out_dir)
    manifest = {
        "purpose": (
            "Exploratory video overlays for VLMaxxing mechanisms. Spatial overlays are exact "
            "Qwen routing-budget policy outputs; C-PERSIST/C-VISION/C-STREAM lanes are regime "
            "mechanism ledgers from checked paper snapshots."
        ),
        "cinematic_policy": (
            "Cinematic videos compute planner decisions at the listed fps, then slow the rendered "
            "frames for readability. Slow playback does not change the computed block classes."
        ),
        "reel_video": safe_rel(reel_path) if reel_path is not None else None,
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
            "c_persist": (
                "Mechanism lane from c_persist_timeline_snapshot.json; not recomputed per clip."
            ),
            "c_vision": (
                "Aggregate measured sparse-vision lane; no checked per-example "
                "token keep mask is implied."
            ),
            "c_stream": (
                "Candidate state-update target lane; reported bridge remains fidelity-limited."
            ),
        },
        "values": values,
        "clips": records,
    }
    manifest_path = args.out_dir / "video_overlay_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"wrote {manifest_path}")
    for record in records:
        print(record["audit_video"])
        print(record["pipeline_video"])
        if "cinematic_video" in record:
            print(record["cinematic_video"])
    if not args.no_montage:
        print(safe_rel(args.out_dir / "three_window_pipeline_montage.mp4"))
    if reel_path is not None:
        print(safe_rel(reel_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
