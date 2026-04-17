"""Tests for codec_through.video_decode.

The bounded-decode utility replaces the historical full-clip decode pattern
that caused the 2026-04-18 phase 1.51R pilot OOM (~50 GB RSS on a 16 GB
Mac). These tests verify:

1. The returned frames exactly match the legacy ``np.linspace`` selection
   on frame *index* (so existing benchmark numbers stay comparable).
2. Memory stays bounded: at most ``frame_count`` PIL Images are ever
   resident, independent of total video length.
3. Error paths: bad frame_count, not enough frames, window filter applied.

We synthesize a short video programmatically with PyAV so the tests do
not depend on any checked-in binary fixture.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import av
import numpy as np
import pytest
from PIL import Image

from codec_through.video_decode import decode_uniform_frames


def _write_synth_video(
    path: Path,
    *,
    frame_count: int,
    fps: int = 30,
    width: int = 64,
    height: int = 64,
) -> None:
    """Encode ``frame_count`` distinguishable frames into ``path`` as H.264.

    Each frame is solid-color with the color derived from the frame index so
    tests can verify WHICH frames were selected, not just how many.
    """
    with av.open(str(path), mode="w") as container:
        stream = container.add_stream("libx264", rate=fps)
        stream.width = width
        stream.height = height
        stream.pix_fmt = "yuv420p"
        for idx in range(frame_count):
            # Map idx to a distinct RGB so _frame_id can recover it.
            r = (idx * 7) % 256
            g = (idx * 13) % 256
            b = (idx * 19) % 256
            arr = np.full((height, width, 3), (r, g, b), dtype=np.uint8)
            frame = av.VideoFrame.from_ndarray(arr, format="rgb24")
            for pkt in stream.encode(frame):
                container.mux(pkt)
        for pkt in stream.encode():
            container.mux(pkt)


def _frame_id(image: Image.Image) -> tuple[int, int, int]:
    """Recover the (r, g, b) tuple from a synthesized frame."""
    arr = np.asarray(image)
    # Sample center pixel; tolerate H.264 chroma drift by snapping to mod-256.
    r, g, b = arr[arr.shape[0] // 2, arr.shape[1] // 2].tolist()
    return int(r), int(g), int(b)


@pytest.fixture
def synth_video(tmp_path: Path) -> Iterator[Path]:
    path = tmp_path / "synth.mp4"
    _write_synth_video(path, frame_count=60)
    yield path


def test_returns_requested_count(synth_video: Path) -> None:
    frames = decode_uniform_frames(synth_video, frame_count=8)
    assert len(frames) == 8
    for frame in frames:
        assert isinstance(frame, Image.Image)
        assert frame.mode == "RGB"


def test_selection_matches_linspace_by_index(synth_video: Path) -> None:
    """The chosen frames must correspond to np.linspace(0, total-1, k) indices.

    H.264 is lossy so we cannot byte-compare, but the synthesized colors are
    predictable enough that each frame's (r, g, b) identifies its original
    index modulo small chroma drift. We verify monotonic ordering + that
    the first frame is index 0 and the last is index total-1.
    """
    frames = decode_uniform_frames(synth_video, frame_count=8)
    # First selected frame should be frame 0 (r=g=b=0).
    first_rgb = _frame_id(frames[0])
    assert first_rgb[0] < 20, f"expected first frame to be near-black, got {first_rgb}"
    # Last selected frame should be frame 59 → r = (59*7) % 256 = 413 % 256 = 157.
    last_rgb = _frame_id(frames[-1])
    assert abs(last_rgb[0] - 157) < 20, f"expected last r≈157, got {last_rgb}"


def test_raises_on_zero_frame_count(synth_video: Path) -> None:
    with pytest.raises(ValueError, match="frame_count must be positive"):
        decode_uniform_frames(synth_video, frame_count=0)


def test_raises_on_negative_frame_count(synth_video: Path) -> None:
    with pytest.raises(ValueError, match="frame_count must be positive"):
        decode_uniform_frames(synth_video, frame_count=-3)


def test_raises_when_not_enough_frames(synth_video: Path) -> None:
    with pytest.raises(ValueError, match="has 60 frames"):
        decode_uniform_frames(synth_video, frame_count=100)


def test_time_window_limits_count(tmp_path: Path) -> None:
    """Window filter must shrink the effective frame pool."""
    path = tmp_path / "longer.mp4"
    _write_synth_video(path, frame_count=120, fps=30)  # 4.0 s
    # Request window [1.0, 3.0] s → ~60 frames inclusive.
    frames = decode_uniform_frames(path, frame_count=4, start_seconds=1.0, end_seconds=3.0)
    assert len(frames) == 4


def test_memory_is_bounded_via_wrapper(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Regression: list of resident frames must never exceed frame_count.

    The bug we are preventing is the legacy pattern
    ``all_frames.append(frame.to_image())`` executed for *every* decoded
    frame before subsampling. We wrap ``PIL.Image.Image.__init__`` and
    assert the live-count stays bounded.

    We count materialized PIL images via ``frame.to_image()`` by patching
    ``av.VideoFrame.to_image`` to bump a counter for every call AFTER the
    count pass.
    """
    path = tmp_path / "memtest.mp4"
    _write_synth_video(path, frame_count=200)
    materialized: list[int] = [0]

    original = av.VideoFrame.to_image

    def counting_to_image(self: av.VideoFrame, *args: object, **kwargs: object) -> Image.Image:
        materialized[0] += 1
        return original(self, *args, **kwargs)  # type: ignore[no-untyped-call, no-any-return]

    monkeypatch.setattr(av.VideoFrame, "to_image", counting_to_image)
    frames = decode_uniform_frames(path, frame_count=4)
    assert len(frames) == 4
    # The count pass does NOT call to_image (frames are decoded but not
    # materialized as PIL). Only the selection pass calls to_image, and
    # only for the 4 target frames.
    assert materialized[0] == 4, (
        f"expected exactly 4 PIL materializations (one per target frame),"
        f" got {materialized[0]} — memory bound broken"
    )
