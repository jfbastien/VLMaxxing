from __future__ import annotations

from pathlib import Path

import numpy as np

from codec_through.codec.continuous_score import macroblock_score_plane
from codec_through.codec.h264_metadata import H264MetadataExtractor
from scripts.analyze_mvbench_codec_motion import _summarize_video
from tests.codec.test_h264_metadata import (
    _black_clip,
    _encode_rgb_frames,
    _translating_patch_clip,
)


def _mean_score(path: Path, *, source: str) -> float:
    extractor = H264MetadataExtractor(path, max_frames=8)
    scores: list[float] = []
    for frame in extractor.iter_frames():
        if frame.frame_type == "I":
            continue
        plane = macroblock_score_plane(frame.macroblocks, source=source)
        scores.append(float(np.mean(plane)))
    if not scores:
        raise AssertionError(f"no non-I frames decoded from {path}")
    return float(np.mean(scores))


def test_synthetic_motion_bucket_has_larger_codec_motion_signal(tmp_path: Path) -> None:
    static_path = tmp_path / "static.mp4"
    motion_path = tmp_path / "motion.mp4"
    _black_clip(static_path, n=12, w=128, h=128)
    _translating_patch_clip(motion_path, n=12, w=128, h=128, dx=8, dy=0, bframes=0)

    static_motion = _mean_score(static_path, source="motion")
    dynamic_motion = _mean_score(motion_path, source="motion")
    static_coded = _mean_score(static_path, source="novel_coded")
    dynamic_coded = _mean_score(motion_path, source="novel_coded")

    assert static_motion < 1e-3
    assert dynamic_motion > static_motion + 0.05
    assert dynamic_coded > static_coded


def test_codec_motion_probe_honors_item_time_window(tmp_path: Path) -> None:
    path = tmp_path / "windowed.mp4"
    frames: list[np.ndarray] = []
    for _ in range(12):
        frames.append(np.zeros((128, 128, 3), dtype=np.uint8))
    for i in range(12):
        arr = np.full((128, 128, 3), 96, dtype=np.uint8)
        x0 = 16 + i * 6
        arr[16:48, x0 : x0 + 32] = 230
        frames.append(arr)
    _encode_rgb_frames(path, frames, fps=12, gop=24, bframes=0)

    first_second = _summarize_video(
        path,
        max_frames=8,
        mv_only=False,
        start_seconds=None,
        end_seconds=None,
    )
    second_second = _summarize_video(
        path,
        max_frames=8,
        mv_only=False,
        start_seconds=1.0,
        end_seconds=2.0,
    )

    assert first_second["start_frame"] == 0
    assert second_second["start_frame"] == 12
    assert second_second["end_frame_exclusive"] == 20
    assert second_second["mean_motion_magnitude"] > first_second["mean_motion_magnitude"] + 0.05
