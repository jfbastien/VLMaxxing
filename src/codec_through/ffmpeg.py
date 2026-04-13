"""FFmpeg/ffprobe helpers rewritten from the original prototype repo."""

from __future__ import annotations

import json
import subprocess
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
import numpy.typing as npt
from PIL import Image

FrameArray = npt.NDArray[np.uint8]


@dataclass(frozen=True, slots=True)
class FramePacketInfo:
    """Minimal packet metadata used for cheap routing decisions."""

    index: int
    pict_type: str
    key_frame: bool
    pkt_size: int


@dataclass(frozen=True, slots=True)
class ExtractedFrame:
    """A decoded frame paired with its source frame index."""

    index: int
    image: FrameArray


def _run_command(command: Sequence[str], *, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        list(command),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "unknown error"
        raise RuntimeError(f"command failed ({' '.join(command)}): {message}")
    return result


def probe_frame_count(video_path: Path) -> int | None:
    """Return the decoded frame count when ffprobe exposes it."""

    result = _run_command(
        [
            "ffprobe",
            "-v",
            "quiet",
            "-count_frames",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=nb_read_frames",
            "-of",
            "csv=p=0",
            str(video_path),
        ]
    )
    raw_value = result.stdout.strip()
    if raw_value in {"", "N/A"}:
        return None
    return int(raw_value)


def uniform_frame_indices(total_frames: int, sample_count: int) -> list[int]:
    """Match the prototype repo's evenly spaced frame sampling policy."""

    if total_frames <= 0 or sample_count <= 0:
        return []
    if sample_count == 1:
        return [0]
    return [int((index * (total_frames - 1)) / (sample_count - 1)) for index in range(sample_count)]


def extract_frames(
    video_path: Path,
    frame_indices: Sequence[int],
    *,
    max_size: int = 560,
) -> list[ExtractedFrame]:
    """Extract specific decoded frames with bounded temp-file lifetime."""

    extracted: list[ExtractedFrame] = []
    with tempfile.TemporaryDirectory(prefix="codec-through-frames-") as tmp_dir:
        temp_dir = Path(tmp_dir)
        for frame_index in frame_indices:
            output_path = temp_dir / f"frame-{frame_index}.png"
            _run_command(
                [
                    "ffmpeg",
                    "-v",
                    "quiet",
                    "-y",
                    "-i",
                    str(video_path),
                    "-vf",
                    (
                        f"select=eq(n\\,{frame_index}),"
                        f"scale={max_size}:{max_size}:force_original_aspect_ratio=decrease,"
                        f"pad={max_size}:{max_size}:(ow-iw)/2:(oh-ih)/2"
                    ),
                    "-vframes",
                    "1",
                    str(output_path),
                ]
            )
            if not output_path.exists() or output_path.stat().st_size == 0:
                raise RuntimeError(f"ffmpeg did not produce frame {frame_index} for {video_path}")
            with Image.open(output_path) as image:
                rgb = np.array(image.convert("RGB"), dtype=np.uint8)
            extracted.append(ExtractedFrame(index=frame_index, image=rgb))
    return extracted


def probe_frame_packets(video_path: Path, *, max_frames: int = 500) -> list[FramePacketInfo]:
    """Extract frame packet metadata used in the original codec pipeline."""

    result = _run_command(
        [
            "ffprobe",
            "-v",
            "quiet",
            "-select_streams",
            "v:0",
            "-show_frames",
            "-show_entries",
            "frame=pict_type,pkt_size,key_frame",
            "-of",
            "json",
            str(video_path),
        ]
    )
    payload = json.loads(result.stdout)
    packets: list[FramePacketInfo] = []
    for index, frame in enumerate(payload.get("frames", [])[:max_frames]):
        pict_type = str(frame.get("pict_type", ""))
        raw_pkt_size = frame.get("pkt_size", 0)
        pkt_size = int(raw_pkt_size) if str(raw_pkt_size).isdigit() else 0
        key_frame = str(frame.get("key_frame", "0")) == "1"
        packets.append(
            FramePacketInfo(
                index=index,
                pict_type=pict_type,
                key_frame=key_frame,
                pkt_size=pkt_size,
            )
        )
    return packets


def mean_i_frame_size(packets: Sequence[FramePacketInfo]) -> float:
    """Compute the mean packet size for I-frames or keyframes."""

    i_frame_sizes = [
        packet.pkt_size
        for packet in packets
        if packet.pkt_size > 0 and (packet.key_frame or packet.pict_type == "I")
    ]
    if not i_frame_sizes:
        return 0.0
    return float(sum(i_frame_sizes) / len(i_frame_sizes))


def frame_level_early_exit(
    packet: FramePacketInfo,
    avg_i_frame_size: float,
    *,
    threshold: float = 0.02,
) -> Literal["ALL_STATIC"] | None:
    """Return ``ALL_STATIC`` when a tiny non-I frame can skip pixel diff."""

    if packet.key_frame or packet.pict_type == "I":
        return None
    if avg_i_frame_size <= 0:
        return None
    if packet.pkt_size / avg_i_frame_size < threshold:
        return "ALL_STATIC"
    return None
