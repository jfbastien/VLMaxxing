from __future__ import annotations

import argparse
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH = 320
HEIGHT = 240
FPS = 12
FRAME_COUNT = 48


@dataclass(frozen=True, slots=True)
class SyntheticClipSpec:
    clip_id: str
    description: str


SPECS = (
    SyntheticClipSpec("synthetic_affine_pan", "grid scene with horizontal pan"),
    SyntheticClipSpec("synthetic_scene_cut", "abrupt scene cut between two rooms"),
    SyntheticClipSpec("synthetic_fullframe_flicker", "stable layout with brightness flicker"),
    SyntheticClipSpec("synthetic_color_swap", "center square changes color"),
    SyntheticClipSpec("synthetic_small_object", "small moving object on static background"),
    SyntheticClipSpec("synthetic_screen_ocr", "screen-like clip with OCR text change"),
)


def _font() -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    return ImageFont.load_default()


def _base_canvas(color: tuple[int, int, int]) -> Image.Image:
    return Image.new("RGB", (WIDTH, HEIGHT), color)


def _draw_grid(draw: ImageDraw.ImageDraw, *, offset_x: int = 0) -> None:
    step = 24
    for x in range(-step, WIDTH + step, step):
        draw.line(((x + offset_x) % step, 0, (x + offset_x) % step, HEIGHT), fill=(70, 90, 120))
    for y in range(0, HEIGHT + step, step):
        draw.line((0, y, WIDTH, y), fill=(70, 90, 120))


def _affine_pan_frame(frame_index: int) -> Image.Image:
    image = _base_canvas((20, 24, 34))
    draw = ImageDraw.Draw(image)
    _draw_grid(draw, offset_x=-4 * frame_index)
    draw.rectangle((115, 90, 205, 170), fill=(40, 80, 160), outline=(220, 230, 255), width=2)
    draw.rectangle((148, 120, 172, 144), fill=(255, 80, 170), outline=(255, 230, 245), width=1)
    draw.text((14, 12), "PAN TEST", fill=(230, 235, 255), font=_font())
    return image


def _scene_cut_frame(frame_index: int) -> Image.Image:
    if frame_index < FRAME_COUNT // 2:
        image = _base_canvas((35, 80, 150))
        draw = ImageDraw.Draw(image)
        draw.rectangle((50, 60, 140, 180), fill=(210, 215, 225))
        draw.rectangle((185, 90, 275, 165), fill=(230, 185, 90))
    else:
        image = _base_canvas((210, 120, 55))
        draw = ImageDraw.Draw(image)
        draw.rectangle((38, 85, 125, 165), fill=(85, 170, 95))
        draw.rectangle((190, 55, 290, 175), fill=(70, 90, 145))
    draw.text((12, 12), "SCENE CUT", fill=(255, 248, 238), font=_font())
    return image


def _fullframe_flicker_frame(frame_index: int) -> Image.Image:
    level = 70 if frame_index % 2 == 0 else 210
    image = _base_canvas((level, level, level))
    draw = ImageDraw.Draw(image)
    draw.rectangle((72, 58, 248, 182), outline=(30, 60, 160), width=4)
    draw.ellipse((132, 92, 188, 148), fill=(230, 70, 80), outline=(20, 20, 20), width=2)
    draw.text(
        (12, 12), "FLICKER", fill=(20, 20, 20) if level > 150 else (245, 245, 245), font=_font()
    )
    return image


def _color_swap_frame(frame_index: int) -> Image.Image:
    image = _base_canvas((235, 236, 240))
    draw = ImageDraw.Draw(image)
    draw.rectangle((94, 54, 226, 186), fill=(120, 120, 125), outline=(20, 20, 20), width=3)
    fill = (220, 40, 50) if frame_index < FRAME_COUNT // 2 else (50, 180, 75)
    draw.rectangle((122, 82, 198, 158), fill=fill, outline=(255, 255, 255), width=2)
    draw.text((12, 12), "COLOR", fill=(20, 20, 20), font=_font())
    return image


def _small_object_frame(frame_index: int) -> Image.Image:
    image = _base_canvas((18, 24, 32))
    draw = ImageDraw.Draw(image)
    _draw_grid(draw)
    y = HEIGHT // 2
    x = 22 + int((WIDTH - 44) * frame_index / (FRAME_COUNT - 1))
    draw.rectangle(
        (x - 5, y - 5, x + 5, y + 5), fill=(250, 245, 140), outline=(255, 255, 255), width=1
    )
    draw.text((12, 12), "SMALL OBJ", fill=(235, 240, 250), font=_font())
    return image


def _screen_ocr_frame(frame_index: int) -> Image.Image:
    image = _base_canvas((24, 26, 31))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((18, 18, WIDTH - 18, HEIGHT - 18), radius=8, fill=(38, 42, 52))
    draw.rectangle((18, 18, WIDTH - 18, 42), fill=(52, 58, 74))
    draw.text((28, 24), "demo.py", fill=(232, 236, 245), font=_font())
    lines = [
        "def run():",
        "    mode = 'live'",
        "    state = 'ALPHA'" if frame_index < FRAME_COUNT // 2 else "    state = 'BRAVO'",
        "    return state",
    ]
    for line_index, text in enumerate(lines):
        draw.text((34, 66 + line_index * 26), text, fill=(205, 220, 235), font=_font())
    if frame_index % 6 < 3:
        cursor_x = 174 if frame_index < FRAME_COUNT // 2 else 181
        draw.rectangle((cursor_x, 118, cursor_x + 2, 130), fill=(245, 245, 245))
    draw.text((20, HEIGHT - 28), "SCREEN OCR", fill=(180, 190, 215), font=_font())
    return image


def _render_frame(clip_id: str, frame_index: int) -> Image.Image:
    if clip_id == "synthetic_affine_pan":
        return _affine_pan_frame(frame_index)
    if clip_id == "synthetic_scene_cut":
        return _scene_cut_frame(frame_index)
    if clip_id == "synthetic_fullframe_flicker":
        return _fullframe_flicker_frame(frame_index)
    if clip_id == "synthetic_color_swap":
        return _color_swap_frame(frame_index)
    if clip_id == "synthetic_small_object":
        return _small_object_frame(frame_index)
    if clip_id == "synthetic_screen_ocr":
        return _screen_ocr_frame(frame_index)
    raise ValueError(f"unknown synthetic clip id: {clip_id}")


def _encode_clip(
    frames_dir: Path, destination: Path, *, fps: int, force: bool, dry_run: bool
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not force:
        print(f"skip existing {destination}")
        return
    command = [
        "ffmpeg",
        "-y",
        "-framerate",
        str(fps),
        "-i",
        str(frames_dir / "frame-%04d.png"),
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        str(destination),
    ]
    print("$", " ".join(command))
    if dry_run:
        return
    subprocess.run(command, check=True)


def _render_clip(
    output_dir: Path,
    spec: SyntheticClipSpec,
    *,
    fps: int,
    frame_count: int,
    force: bool,
    dry_run: bool,
) -> None:
    with tempfile.TemporaryDirectory(prefix=f"{spec.clip_id}-") as temp_dir:
        frames_dir = Path(temp_dir)
        for frame_index in range(frame_count):
            image = _render_frame(spec.clip_id, frame_index)
            image.save(frames_dir / f"frame-{frame_index:04d}.png")
        destination = output_dir / f"{spec.clip_id}.mp4"
        _encode_clip(frames_dir, destination, fps=fps, force=force, dry_run=dry_run)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic local stress clips.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/corpus/synthetic"),
        help="Directory for generated MP4 files.",
    )
    parser.add_argument(
        "--clip-id",
        action="append",
        default=[],
        help="Generate only the selected synthetic clip ids.",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=FPS,
        help="Frames per second for generated clips.",
    )
    parser.add_argument(
        "--frames",
        type=int,
        default=FRAME_COUNT,
        help="Number of frames per generated clip.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing MP4 files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the ffmpeg work without producing MP4 files.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.fps <= 0:
        raise ValueError("fps must be positive")
    if args.frames <= 1:
        raise ValueError("frames must be greater than 1")

    selected_ids = set(args.clip_id)
    specs = [spec for spec in SPECS if not selected_ids or spec.clip_id in selected_ids]
    if not specs:
        raise SystemExit("no matching synthetic clip ids selected")

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    for spec in specs:
        print(f"generate {spec.clip_id}: {spec.description}")
        _render_clip(
            output_dir,
            spec,
            fps=args.fps,
            frame_count=args.frames,
            force=args.force,
            dry_run=args.dry_run,
        )


if __name__ == "__main__":
    main()
