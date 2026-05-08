#!/usr/bin/env python3
"""Render real-video explainers for VLMaxxing, OneVision, and their combination.

The output is for human explanation, not model inference. It uses the same
three paper-visualization clips as the existing VLMaxxing overlay renderer and
hard-fails when a real source clip is missing. There is deliberately no
synthetic fallback in this script.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from codec_through.codec.continuous_score import (
    CodecScoreSource,
    codec_score_units,
    project_macroblock_metadata_to_token_grid,
    sparse_sample_indices,
)
from codec_through.codec.h264_metadata import H264MetadataExtractor
from codec_through.codec.onevision_patchification import (
    PatchificationConfig,
    VisiblePatch,
    count_tokens_by_frame,
    select_visible_patches,
    spatial_bias,
    temporal_coverage,
)
from codec_through.video_decode import _count_frames, decode_uniform_frames

REPO_ROOT = Path(__file__).resolve().parent.parent
FIG1_SCRIPT_DIR = REPO_ROOT / "paper" / "arxiv" / "scripts"
if str(FIG1_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(FIG1_SCRIPT_DIR))

from find_fig1_candidates import (  # noqa: E402
    BENCHMARK_FRAME_SIZE,
    QWEN_BLOCK_SIZE,
    square_pad_frame,
    transition_details,
)

DEFAULT_OUT_DIR = Path("research/experiments/2026/artifacts/onevision_vlmaxxing_explainer_videos")
ONEVISION_VISUALS_OUT_DIR = Path("research/experiments/2026/artifacts/onevision_vlmaxxing_visuals")
OUTPUT_SIZE = (1600, 900)
VIDEO_BOX = (44, 112, 964, 808)
PANEL_BOX = (1008, 112, 1556, 808)
DEFAULT_FRAME_COUNT = 16
DEFAULT_FPS = 4.0

INK = (15, 23, 42)
MUTED = (71, 85, 105)
FAINT = (226, 232, 240)
PANEL_BG = (248, 250, 252)
WHITE = (255, 255, 255)
GREEN = (22, 163, 74)
GREEN_SOFT = (220, 252, 231)
YELLOW = (234, 179, 8)
YELLOW_SOFT = (254, 249, 195)
ORANGE = (249, 115, 22)
ORANGE_SOFT = (255, 237, 213)
ORANGE_DARK = (194, 65, 12)
BLUE = (37, 99, 235)
BLUE_SOFT = (219, 234, 254)
PURPLE = (124, 58, 237)
PURPLE_SOFT = (237, 233, 254)
RED = (220, 38, 38)

Mode = Literal["vlmaxxing", "onevision", "combined"]


@dataclass(frozen=True, slots=True)
class ClipSpec:
    key: str
    benchmark: str
    item_id: str
    video_id: str
    role: str
    video_path: Path
    start_seconds: float
    end_seconds: float


@dataclass(frozen=True, slots=True)
class ClipState:
    clip: ClipSpec
    frames: list[Image.Image]
    padded_frames: list[Image.Image]
    active_boxes: list[tuple[int, int, int, int]]
    transitions: list[dict[str, Any]]
    score_volumes: dict[CodecScoreSource, np.ndarray]
    patches: list[VisiblePatch]
    tokens_by_frame: np.ndarray
    token_budget: int
    sampled_relative_frames: list[int]
    sampled_absolute_frames: list[int]


CLIPS = (
    ClipSpec(
        key="tomato_0298_00",
        benchmark="TOMATO",
        item_id="tomato:rotation:0298-00",
        video_id="0298-00",
        role="existing paper visualization: high-reuse routing example",
        video_path=Path("data/benchmarks/tomato/videos/object/0298-00.mp4"),
        start_seconds=0.0,
        end_seconds=2.0,
    ),
    ClipSpec(
        key="videomme_380",
        benchmark="VideoMME",
        item_id="videomme:medium:380-3",
        video_id="2Bns2m5Bg4M",
        role="existing paper visualization: VideoMME visual anchor",
        video_path=Path("data/benchmarks/videomme/videos/2Bns2m5Bg4M.mp4"),
        start_seconds=206.39,
        end_seconds=207.89,
    ),
    ClipSpec(
        key="videomme_267",
        benchmark="VideoMME",
        item_id="videomme:short:267-2",
        video_id="Atf_Af1q_5w",
        role="existing paper visualization: lower-reuse boundary",
        video_path=Path("data/benchmarks/videomme/videos/Atf_Af1q_5w.mp4"),
        start_seconds=0.0,
        end_seconds=1.0,
    ),
)


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


FONTS = {
    "title": font(31, bold=True),
    "subtitle": font(17),
    "section": font(20, bold=True),
    "body": font(16),
    "small": font(13),
    "tiny": font(11),
    "number": font(28, bold=True),
}


def text_size(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.ImageFont) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def draw_wrapped_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    *,
    max_width: int,
    fill: tuple[int, int, int] = INK,
    fnt: ImageFont.ImageFont | None = None,
    line_height: int = 21,
) -> int:
    fnt = fnt or FONTS["body"]
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if draw.textlength(candidate, font=fnt) <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
        current = word
    if current:
        lines.append(current)
    x, y = xy
    for index, line in enumerate(lines):
        draw.text((x, y + index * line_height), line, fill=fill, font=fnt)
    return y + len(lines) * line_height


def rounded_rect(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    *,
    fill: tuple[int, int, int],
    outline: tuple[int, int, int] = FAINT,
    radius: int = 8,
    width: int = 1,
) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


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


def write_mp4(frames: list[Image.Image], out_path: Path, *, fps: float) -> None:
    if not frames:
        raise ValueError("no frames to encode")
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path is None:
        raise RuntimeError("ffmpeg is required to encode explainer videos")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    width, height = frames[0].size
    cmd = [
        ffmpeg_path,
        "-y",
        "-loglevel",
        "error",
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
        "veryfast",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(out_path),
    ]
    proc = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
    )
    assert proc.stdin is not None
    write_error: BrokenPipeError | None = None
    try:
        for frame in frames:
            if frame.size != (width, height):
                raise ValueError("all frames must have identical dimensions")
            proc.stdin.write(frame.convert("RGB").tobytes())
    except BrokenPipeError as exc:
        write_error = exc
    finally:
        proc.stdin.close()
    return_code = proc.wait()
    stderr = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
    if return_code != 0 or write_error is not None:
        detail = stderr.strip()
        if not detail and write_error is not None:
            detail = repr(write_error)
        raise RuntimeError(f"ffmpeg failed for {out_path} with code {return_code}: {detail}")


def _video_fps(video_path: Path) -> float:
    import av

    with av.open(str(video_path)) as container:
        stream = container.streams.video[0]
        rate = stream.average_rate or stream.base_rate
        if rate is None:
            raise ValueError(f"could not determine frame rate for {video_path}")
        return float(rate)


def _resolve_clip_path(path: Path) -> Path:
    full_path = REPO_ROOT / path
    if not full_path.exists():
        raise FileNotFoundError(f"required real source clip is missing: {path}")
    return full_path


def _effective_token_budget(score_volume: np.ndarray, requested: int | None) -> int:
    if score_volume.ndim != 3:
        raise ValueError("score_volume must be 3D")
    frames, rows, cols = score_volume.shape
    anchor_tokens = rows * cols
    dense_tokens = frames * anchor_tokens
    if requested is not None:
        if requested < anchor_tokens:
            raise ValueError(
                f"token budget {requested} is smaller than the anchor frame ({anchor_tokens})"
            )
        return min(requested, dense_tokens)
    return min(dense_tokens, max(anchor_tokens + 1, int(round(dense_tokens * 0.125))))


def load_clip_state(
    clip: ClipSpec,
    *,
    frame_count: int,
    token_budget: int | None,
) -> ClipState:
    video_path = _resolve_clip_path(clip.video_path)
    if frame_count <= 1:
        raise ValueError("frame_count must be greater than one")
    frames = decode_uniform_frames(
        video_path,
        frame_count,
        start_seconds=clip.start_seconds,
        end_seconds=clip.end_seconds,
    )
    padded_frames: list[Image.Image] = []
    active_boxes: list[tuple[int, int, int, int]] = []
    for frame in frames:
        padded, active_box = square_pad_frame(frame, size=BENCHMARK_FRAME_SIZE)
        padded_frames.append(padded)
        active_boxes.append(active_box)
    transitions = transition_details(padded_frames, active_boxes)

    window_frames = _count_frames(
        video_path,
        start_seconds=clip.start_seconds,
        end_seconds=clip.end_seconds,
    )
    sampled_relative = sparse_sample_indices(window_frames, frame_count)
    fps = _video_fps(video_path)
    start_index = int(round(clip.start_seconds * fps))
    sampled_absolute = [start_index + index for index in sampled_relative]

    score_by_source: dict[CodecScoreSource, dict[int, np.ndarray]] = {
        CodecScoreSource.NOVEL_CODED: {},
        CodecScoreSource.MOTION: {},
        CodecScoreSource.RESIDUAL: {},
        CodecScoreSource.FUSED: {},
    }
    sampled_set = set(sampled_absolute)
    extractor = H264MetadataExtractor(video_path, max_frames=max(sampled_absolute) + 1)
    active_box_for_projection: tuple[int, int, int, int] | None = None
    for frame_metadata in extractor.iter_frames():
        if frame_metadata.index not in sampled_set:
            continue
        if active_box_for_projection is None:
            active_box_for_projection = _active_box_for_canvas(
                frame_metadata.width,
                frame_metadata.height,
                canvas_size=BENCHMARK_FRAME_SIZE,
            )
        for source in score_by_source:
            score_by_source[source][frame_metadata.index] = (
                project_macroblock_metadata_to_token_grid(
                    frame_metadata.macroblocks,
                    source=source,
                    macroblock_size=frame_metadata.mb_size,
                    frame_width=frame_metadata.width,
                    frame_height=frame_metadata.height,
                    canvas_size=BENCHMARK_FRAME_SIZE,
                    active_box=active_box_for_projection,
                    token_block=QWEN_BLOCK_SIZE,
                    normalize_inputs=True,
                )
            )
    missing = [
        index
        for index in sampled_absolute
        if any(index not in per_source for per_source in score_by_source.values())
    ]
    if missing:
        raise ValueError(f"{clip.key} missing sampled codec metadata frames: {missing}")
    score_volumes = {
        source: np.stack([per_source[index] for index in sampled_absolute], axis=0).astype(
            np.float32
        )
        for source, per_source in score_by_source.items()
    }
    effective_budget = _effective_token_budget(score_volumes[CodecScoreSource.FUSED], token_budget)
    patches = select_visible_patches(
        score_volumes[CodecScoreSource.FUSED],
        config=PatchificationConfig(token_budget=effective_budget, anchor_frames=(0,)),
    )
    return ClipState(
        clip=clip,
        frames=frames,
        padded_frames=padded_frames,
        active_boxes=active_boxes,
        transitions=transitions,
        score_volumes=score_volumes,
        patches=patches,
        tokens_by_frame=count_tokens_by_frame(patches, total_frames=frame_count),
        token_budget=effective_budget,
        sampled_relative_frames=sampled_relative,
        sampled_absolute_frames=sampled_absolute,
    )


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


def normalized_boxes_to_pixels(
    boxes: list[list[float]] | list[tuple[float, float, float, float]],
    image: Image.Image,
) -> list[tuple[int, int, int, int]]:
    out: list[tuple[int, int, int, int]] = []
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


def transition_percentages(transition: dict[str, Any] | None) -> dict[str, float]:
    if transition is None:
        return {"has_transition": 0.0, "reused": 0.0, "fresh": 0.0, "stale": 0.0}
    return {
        "has_transition": 1.0,
        "reused": float(transition.get("reuse_ratio_active", 0.0)),
        "fresh": float(transition.get("fresh_fraction_active", 0.0)),
        "stale": float(transition.get("stale_fraction_active", 0.0)),
    }


def draw_vlmaxxing_overlay(image: Image.Image, transition: dict[str, Any] | None) -> Image.Image:
    if transition is None:
        return image.copy()
    rgba = image.convert("RGBA")
    overlay = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    for box in normalized_boxes_to_pixels(transition.get("static_reused_boxes", []), image):
        draw.rectangle(box, fill=(22, 163, 74, 35), outline=(22, 163, 74, 95), width=1)
    for box in normalized_boxes_to_pixels(transition.get("shifted_reused_boxes", []), image):
        draw.rectangle(box, fill=(234, 179, 8, 45), outline=(234, 179, 8, 130), width=1)
    for box in normalized_boxes_to_pixels(transition.get("stale_boxes", []), image):
        draw.rectangle(box, fill=(220, 38, 38, 80), outline=(220, 38, 38, 190), width=2)
    for box in normalized_boxes_to_pixels(transition.get("raw_novel_boxes", []), image):
        draw.rectangle(box, fill=(249, 115, 22, 95), outline=(194, 65, 12, 220), width=2)
    return Image.alpha_composite(rgba, overlay).convert("RGB")


def draw_onevision_overlay(
    image: Image.Image,
    patches: list[VisiblePatch],
    *,
    frame_index: int,
    combine_with_vlmaxxing: bool,
) -> Image.Image:
    rgba = image.convert("RGBA")
    overlay = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    for patch in patches:
        if patch.frame != frame_index:
            continue
        left = patch.col * QWEN_BLOCK_SIZE
        top = patch.row * QWEN_BLOCK_SIZE
        right = min(BENCHMARK_FRAME_SIZE, left + QWEN_BLOCK_SIZE)
        bottom = min(BENCHMARK_FRAME_SIZE, top + QWEN_BLOCK_SIZE)
        if patch.source == "anchor":
            fill = (37, 99, 235, 64)
            outline = (37, 99, 235, 215)
        elif combine_with_vlmaxxing:
            fill = (124, 58, 237, 125)
            outline = (88, 28, 135, 245)
        else:
            fill = (249, 115, 22, 125)
            outline = (194, 65, 12, 245)
        draw.rectangle((left, top, right, bottom), fill=fill, outline=outline, width=2)
    return Image.alpha_composite(rgba, overlay).convert("RGB")


def draw_frame(state: ClipState, *, mode: Mode, frame_index: int) -> Image.Image:
    frame = state.padded_frames[frame_index]
    transition = state.transitions[frame_index - 1] if frame_index > 0 else None
    if mode == "vlmaxxing":
        visual = draw_vlmaxxing_overlay(frame, transition)
    elif mode == "onevision":
        visual = draw_onevision_overlay(
            frame,
            state.patches,
            frame_index=frame_index,
            combine_with_vlmaxxing=False,
        )
    else:
        visual = draw_vlmaxxing_overlay(frame, transition)
        visual = draw_onevision_overlay(
            visual,
            state.patches,
            frame_index=frame_index,
            combine_with_vlmaxxing=True,
        )

    image = Image.new("RGB", OUTPUT_SIZE, (255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw_header(draw, state, mode=mode, frame_index=frame_index)
    fitted, pos = fit_image(visual, VIDEO_BOX)
    image.paste(fitted, pos)
    draw_panel(draw, state, mode=mode, frame_index=frame_index, transition=transition)
    draw_footer(draw, state)
    return image


def draw_header(
    draw: ImageDraw.ImageDraw,
    state: ClipState,
    *,
    mode: Mode,
    frame_index: int,
) -> None:
    titles = {
        "vlmaxxing": "VLMaxxing / FrameMogging",
        "onevision": "OneVision-style codec patchification",
        "combined": "VLMaxxing + OneVision-style refresh planning",
    }
    subtitles = {
        "vlmaxxing": (
            "Track A visualization: reuse validated state where frame-to-frame evidence is stable; "
            "buy fresh evidence where novelty or age says reuse is unsafe."
        ),
        "onevision": (
            "Clean-room reproduction of the codec-allocation surface: blue anchor context, "
            "orange global Top-K motion/residual patches."
        ),
        "combined": (
            "Hypothesis view: VLMaxxing controls when state is refreshed; OneVision-style codec "
            "scores rank where sparse fresh visual evidence would be spent."
        ),
    }
    draw.text((44, 28), titles[mode], fill=INK, font=FONTS["title"])
    draw_wrapped_text(
        draw,
        (46, 66),
        subtitles[mode],
        max_width=1110,
        fill=MUTED,
        fnt=FONTS["subtitle"],
        line_height=20,
    )
    draw.text(
        (1290, 34),
        f"sample {frame_index + 1}/{len(state.frames)}",
        fill=MUTED,
        font=FONTS["section"],
    )


def draw_panel(
    draw: ImageDraw.ImageDraw,
    state: ClipState,
    *,
    mode: Mode,
    frame_index: int,
    transition: dict[str, Any] | None,
) -> None:
    rounded_rect(draw, PANEL_BOX, fill=PANEL_BG, outline=FAINT, radius=8)
    x0, y0, x1, _ = PANEL_BOX
    x = x0 + 26
    y = y0 + 24
    draw.text((x, y), "What the overlay means", fill=INK, font=FONTS["section"])
    y += 38
    if mode in {"vlmaxxing", "combined"}:
        draw_legend(draw, (x, y), GREEN, "green", "same-position state reused")
        y += 30
        draw_legend(draw, (x, y), YELLOW, "yellow", "shifted-but-reusable state")
        y += 30
        draw_legend(draw, (x, y), ORANGE, "orange", "fresh or novel region")
        y += 30
        draw_legend(draw, (x, y), RED, "red", "age-expired refresh")
        y += 40
    if mode in {"onevision", "combined"}:
        draw_legend(draw, (x, y), BLUE, "blue", "mandatory anchor frame patches")
        y += 30
        patch_color = PURPLE if mode == "combined" else ORANGE
        draw_legend(draw, (x, y), patch_color, "patch", "selected motion/residual tokens")
        y += 40

    if mode in {"vlmaxxing", "combined"}:
        stats = transition_percentages(transition)
        draw_percent_bar(
            draw,
            (x, y),
            width=x1 - x - 34,
            label="VLMaxxing transition budget",
            values=[
                ("reuse", stats["reused"], GREEN),
                ("fresh", stats["fresh"], ORANGE),
            ],
            empty_label="first sampled frame: no prior transition",
        )
        y += 92

    if mode in {"onevision", "combined"}:
        selected_now = int(state.tokens_by_frame[frame_index])
        dense_per_frame = int(
            state.score_volumes[CodecScoreSource.FUSED].shape[1]
            * state.score_volumes[CodecScoreSource.FUSED].shape[2]
        )
        draw.text((x, y), "OneVision-style allocation", fill=MUTED, font=FONTS["small"])
        draw.text(
            (x, y + 21),
            f"{selected_now}/{dense_per_frame} tokens on this sampled frame",
            fill=INK,
            font=FONTS["number"],
        )
        y += 70
        draw_token_timeline(draw, (x, y), state=state, frame_index=frame_index, width=x1 - x - 34)
        y += 128

    note = {
        "vlmaxxing": (
            "Denominator: paired answer stability. This view alone is not a wall-clock speedup "
            "unless the runtime actually skips decode, vision, attention, or prefill work."
        ),
        "onevision": (
            "Denominator: visual patches retained. The imported OneVision paper reports patch "
            "reduction, not a directly comparable local end-to-end speedup."
        ),
        "combined": (
            "Denominators stay separated: OV-style sparse evidence can change first-ingest token "
            "allocation; VLMaxxing reuse and C-PERSIST session reuse are accounted separately."
        ),
    }[mode]
    draw_wrapped_text(
        draw,
        (x, max(y, PANEL_BOX[3] - 124)),
        note,
        max_width=x1 - x - 36,
        fill=MUTED,
        fnt=FONTS["small"],
        line_height=17,
    )


def draw_legend(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    color: tuple[int, int, int],
    label: str,
    text: str,
) -> None:
    x, y = xy
    draw.rounded_rectangle((x, y + 2, x + 42, y + 22), radius=4, fill=color)
    draw.text((x + 52, y), f"{label}: {text}", fill=INK, font=FONTS["body"])


def draw_percent_bar(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    *,
    width: int,
    label: str,
    values: list[tuple[str, float, tuple[int, int, int]]],
    empty_label: str,
) -> None:
    x, y = xy
    draw.text((x, y), label, fill=MUTED, font=FONTS["small"])
    y += 24
    if not any(value > 0.0 for _name, value, _color in values):
        rounded_rect(draw, (x, y, x + width, y + 28), fill=WHITE, outline=FAINT, radius=6)
        draw.text((x + 10, y + 7), empty_label, fill=MUTED, font=FONTS["small"])
        return
    cursor = x
    for name, value, color in values:
        segment = int(round(width * max(0.0, min(1.0, value))))
        if segment <= 0:
            continue
        draw.rectangle((cursor, y, cursor + segment, y + 28), fill=color)
        if segment > 58:
            draw.text((cursor + 8, y + 7), f"{name} {value:.0%}", fill=WHITE, font=FONTS["tiny"])
        cursor += segment
    draw.rounded_rectangle((x, y, x + width, y + 28), radius=6, outline=INK, width=1)


def draw_token_timeline(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    *,
    state: ClipState,
    frame_index: int,
    width: int,
) -> None:
    x, y = xy
    counts = state.tokens_by_frame
    max_count = max(1, int(counts.max()))
    bar_gap = 3
    bar_w = max(5, (width - (len(counts) - 1) * bar_gap) // len(counts))
    max_h = 74
    draw.text(
        (x, y),
        f"clip budget {state.token_budget} visible patches",
        fill=MUTED,
        font=FONTS["small"],
    )
    y += 24
    for index, count in enumerate(counts.tolist()):
        left = x + index * (bar_w + bar_gap)
        height = int(max_h * count / max_count)
        color = BLUE if index == 0 else ORANGE
        if index == frame_index:
            draw.rectangle((left - 2, y - 4, left + bar_w + 2, y + max_h + 4), outline=INK, width=2)
        draw.rectangle((left, y + max_h - height, left + bar_w, y + max_h), fill=color)
    draw.text((x, y + max_h + 10), "time -> sampled frames", fill=MUTED, font=FONTS["tiny"])


def draw_footer(draw: ImageDraw.ImageDraw, state: ClipState) -> None:
    clip = state.clip
    draw.text(
        (46, 842),
        (
            f"{clip.benchmark} {clip.item_id} - {clip.role} - "
            f"{clip.start_seconds:.2f}-{clip.end_seconds:.2f}s"
        ),
        fill=MUTED,
        font=FONTS["small"],
    )
    draw.text(
        (1010, 842),
        (
            "Real source video only; codec residual is repo-local PyAV proxy, "
            "not upstream cv_reader parity."
        ),
        fill=MUTED,
        font=FONTS["small"],
    )


def render_clip_videos(
    state: ClipState,
    *,
    out_dir: Path,
    fps: float,
    modes: tuple[Mode, ...],
) -> dict[str, str]:
    outputs: dict[str, str] = {}
    clip_dir = out_dir / state.clip.key
    clip_dir.mkdir(parents=True, exist_ok=True)
    for mode in modes:
        frames = [
            draw_frame(state, mode=mode, frame_index=index) for index in range(len(state.frames))
        ]
        out_path = clip_dir / f"{state.clip.key}_{mode}.mp4"
        write_mp4(frames, out_path, fps=fps)
        outputs[mode] = _repo_relative(out_path)
    return outputs


def _repo_relative(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _source_video_provenance(path: Path) -> dict[str, object]:
    full_path = _resolve_clip_path(path)
    return {
        "path": str(path),
        "sha256": _sha256_file(full_path),
        "size_bytes": full_path.stat().st_size,
    }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_metadata(*, exclude_paths: tuple[Path, ...] = ()) -> dict[str, object]:
    return {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "git_commit": _git_output("rev-parse", "HEAD"),
        "git_dirty": _git_dirty(exclude_paths=exclude_paths),
        "git_dirty_scope": (
            "repository excluding OneVision visualization output artifact directories"
        ),
    }


def _git_dirty(*, exclude_paths: tuple[Path, ...]) -> bool:
    args = ["status", "--porcelain", "--untracked-files=all", "--", "."]
    for path in exclude_paths:
        args.append(f":(exclude){_repo_relative(path)}")
    return bool(_git_output(*args))


def _git_output(*args: str) -> str | None:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _summary_for_state(state: ClipState, outputs: dict[str, str]) -> dict[str, Any]:
    coverage = temporal_coverage(state.patches, total_frames=len(state.frames))
    bias = spatial_bias(
        state.patches,
        grid_shape=(
            int(state.score_volumes[CodecScoreSource.FUSED].shape[1]),
            int(state.score_volumes[CodecScoreSource.FUSED].shape[2]),
        ),
    )
    transition_stats = [
        transition_percentages(state.transitions[index - 1])
        if index > 0
        else transition_percentages(None)
        for index in range(len(state.frames))
    ]
    clip_payload = asdict(state.clip)
    clip_payload["video_path"] = str(state.clip.video_path)
    clip_payload["source_video_provenance"] = _source_video_provenance(state.clip.video_path)
    return {
        "clip": clip_payload,
        "frame_count": len(state.frames),
        "sampled_relative_frames": state.sampled_relative_frames,
        "sampled_absolute_frames": state.sampled_absolute_frames,
        "token_budget": state.token_budget,
        "tokens_by_frame": state.tokens_by_frame.tolist(),
        "score_units": {source.value: codec_score_units(source) for source in state.score_volumes},
        "temporal_coverage": asdict(coverage),
        "spatial_bias": asdict(bias),
        "transition_stats": transition_stats,
        "outputs": outputs,
    }


def write_manifest(out_dir: Path, summaries: list[dict[str, Any]], *, fps: float) -> Path:
    payload = {
        "schema": "onevision_vlmaxxing_explainer_videos_v1",
        "status": "ok",
        **_artifact_metadata(exclude_paths=(out_dir, REPO_ROOT / ONEVISION_VISUALS_OUT_DIR)),
        "scientific_guardrails": [
            "No synthetic fallback exists in this renderer.",
            "All outputs are derived from the three established real benchmark clips.",
            "VLMaxxing, OneVision, and combined denominators are shown separately.",
            "Combined videos are hypothesis visualizations until OV-3/OV-6 model runs complete.",
        ],
        "fps": fps,
        "frame_size": list(OUTPUT_SIZE),
        "clip_summaries": summaries,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "explainer_video_manifest.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--frame-count", type=int, default=DEFAULT_FRAME_COUNT)
    parser.add_argument("--token-budget", type=int, default=None)
    parser.add_argument("--fps", type=float, default=DEFAULT_FPS)
    parser.add_argument(
        "--clip",
        action="append",
        choices=tuple(clip.key for clip in CLIPS),
        help="Render only the selected clip key. May be supplied multiple times.",
    )
    parser.add_argument(
        "--mode",
        action="append",
        choices=("vlmaxxing", "onevision", "combined"),
        help="Render only the selected mode. May be supplied multiple times.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.frame_count <= 1:
        raise ValueError("--frame-count must be greater than one")
    if args.fps <= 0.0 or not math.isfinite(args.fps):
        raise ValueError("--fps must be a positive finite value")
    selected_keys = set(args.clip or [clip.key for clip in CLIPS])
    selected_modes = tuple(args.mode or ["vlmaxxing", "onevision", "combined"])
    clips = [clip for clip in CLIPS if clip.key in selected_keys]
    if len(clips) != len(selected_keys):
        missing = sorted(selected_keys - {clip.key for clip in clips})
        raise ValueError(f"unknown clip keys: {missing}")

    out_dir = REPO_ROOT / args.out_dir
    summaries: list[dict[str, Any]] = []
    for clip in clips:
        state = load_clip_state(clip, frame_count=args.frame_count, token_budget=args.token_budget)
        outputs = render_clip_videos(
            state,
            out_dir=out_dir,
            fps=args.fps,
            modes=selected_modes,
        )
        summary = _summary_for_state(state, outputs)
        clip_dir = out_dir / clip.key
        (clip_dir / "explainer_summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        summaries.append(summary)
    manifest = write_manifest(out_dir, summaries, fps=args.fps)
    print(manifest)


if __name__ == "__main__":
    main()
