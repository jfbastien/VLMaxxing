"""Bounded-memory uniform frame decode for research benchmarks.

The naive pattern — decode every frame into a list, then subsample —
uses O(total_frames) memory at native resolution. On a 15-minute 30 fps
VideoMME clip (~27 k frames at 1280×720×3 bytes) this blows past 50 GB on
a 16 GB Mac and triggers the OOM killer (observed 2026-04-18 during the
phase 1.51R pilot).

This module provides :func:`decode_uniform_frames`, which holds at most
``frame_count`` PIL Images in memory regardless of video length, while
preserving the exact ``np.linspace(0, total-1, frame_count, dtype=int)``
selection semantics of the legacy unbounded implementation. The cost is
one extra decode pass to count frames when the container metadata is
unreliable (typical for raw streams; MP4 containers usually expose
accurate ``stream.frames`` and take the fast path).

Why not seek-based sampling? Keyframe seek is memory-bounded and faster,
but it can drift by up to the GOP length and subtly changes which frames
we benchmark on. We preserve index-based uniform sampling so legacy
comparisons stay exact.
"""

from __future__ import annotations

from pathlib import Path

import av
import numpy as np
from PIL import Image


def decode_uniform_frames(
    video_path: Path,
    frame_count: int,
    *,
    start_seconds: float | None = None,
    end_seconds: float | None = None,
) -> list[Image.Image]:
    """Return ``frame_count`` uniformly-spaced RGB PIL frames from ``video_path``.

    Memory is O(frame_count): at most ``frame_count`` PIL Images are held
    simultaneously. Frames outside the chosen indices are decoded but
    discarded without materializing them as PIL Images.

    Selection matches ``np.linspace(0, total-1, frame_count, dtype=int)``
    applied to the frames inside the ``[start_seconds, end_seconds]`` window
    (inclusive on both sides). This is the same selection the previous
    unbounded implementation used, so existing benchmark results stay
    comparable.

    Args:
        video_path: video file to decode.
        frame_count: number of frames to return. Must be positive.
        start_seconds: lower bound on frame timestamp (inclusive) or None.
        end_seconds: upper bound on frame timestamp (inclusive) or None.

    Returns:
        List of ``frame_count`` PIL Images in temporal order.

    Raises:
        ValueError: if ``frame_count <= 0`` or fewer than ``frame_count``
            frames fall in the requested window.
    """
    if frame_count <= 0:
        raise ValueError(f"frame_count must be positive, got {frame_count}")
    total = _count_frames(video_path, start_seconds=start_seconds, end_seconds=end_seconds)
    if total < frame_count:
        raise ValueError(
            f"video {video_path.name} has {total} frames in window"
            f" [{start_seconds}, {end_seconds}] but {frame_count} requested"
        )
    target_indices = set(np.linspace(0, total - 1, frame_count, dtype=int).tolist())
    selected: list[Image.Image] = []
    with av.open(str(video_path)) as container:
        stream = container.streams.video[0]
        idx = 0
        for frame in container.decode(stream):
            ts = float(frame.time) if frame.time is not None else None
            if start_seconds is not None and ts is not None and ts < start_seconds:
                continue
            if end_seconds is not None and ts is not None and ts > end_seconds:
                break
            if idx in target_indices:
                selected.append(frame.to_image().convert("RGB"))  # type: ignore[no-untyped-call]
                if len(selected) == frame_count:
                    break
            idx += 1
    if len(selected) != frame_count:
        # Second-pass count disagreed with first-pass count (rare: mutable
        # container or truncated read). Fail loudly rather than silently
        # returning fewer frames than requested.
        raise ValueError(
            f"decode mismatch on {video_path.name}: counted {total} frames but"
            f" only {len(selected)} matched target indices"
        )
    return selected


def _count_frames(
    video_path: Path,
    *,
    start_seconds: float | None,
    end_seconds: float | None,
) -> int:
    """Count frames in the requested window without retaining them.

    Always iterates the stream. The previously-used ``stream.frames`` fast
    path has been removed: on 2026-04-21 it was observed to report 366
    frames for ``tomato/videos/object/0298-00.mp4`` while the underlying
    stream only yields ~235 decodable frames, producing a
    ``decode_uniform_frames`` target-index mismatch that hard-fails the
    whole benchmark. Iteration is O(1) memory (each decoded frame is
    discarded immediately) and adds ~0.2-0.8s per 8-second clip on M3
    hardware — acceptable overhead for decode-correctness on corrupted
    or mis-indexed MP4 containers.
    """
    count = 0
    with av.open(str(video_path)) as container:
        stream = container.streams.video[0]
        for frame in container.decode(stream):
            ts = float(frame.time) if frame.time is not None else None
            if start_seconds is not None and ts is not None and ts < start_seconds:
                continue
            if end_seconds is not None and ts is not None and ts > end_seconds:
                break
            count += 1
    return count
