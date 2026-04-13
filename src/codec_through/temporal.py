"""Temporal block classification utilities."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import IntEnum
from typing import Any

import numpy as np
import numpy.typing as npt

FrameArray = npt.NDArray[Any]


class BlockClass(IntEnum):
    """Historical planner labels for adjacent-frame block reuse.

    Under the current pixel-diff planner these are proxy classes: low delta,
    mid delta, and high delta. They are not literal codec-motion semantics
    until a decoder-side planner replaces the RGB proxy.
    """

    STATIC = 0
    SHIFTED = 1
    NOVEL = 2


@dataclass(frozen=True, slots=True)
class BlockThresholds:
    """Thresholds used by the original repo's pixel-diff planner."""

    static_threshold: float = 3.0
    shifted_threshold: float = 8.0


DEFAULT_THRESHOLDS = BlockThresholds()


@dataclass(frozen=True, slots=True)
class ClassificationSummary:
    """Count summary for a 2D block classification grid."""

    total_blocks: int
    static_blocks: int
    shifted_blocks: int
    novel_blocks: int

    @property
    def reused_blocks(self) -> int:
        return self.static_blocks + self.shifted_blocks

    @property
    def reused_ratio(self) -> float:
        if self.total_blocks == 0:
            return 0.0
        return self.reused_blocks / self.total_blocks

    @property
    def novel_ratio(self) -> float:
        if self.total_blocks == 0:
            return 0.0
        return self.novel_blocks / self.total_blocks


def _diff_plane(frame_a: FrameArray, frame_b: FrameArray) -> npt.NDArray[np.float32]:
    """Return mean absolute RGB error or grayscale absolute error.

    The current thresholds are calibrated against mean absolute channel
    difference in RGB space. Alternatives such as max-channel error, luminance,
    or perceptual color distance are not equivalent.
    """

    if frame_a.ndim not in (2, 3) or frame_b.ndim not in (2, 3):
        raise ValueError("expected 2D grayscale or 3D color frames")
    if frame_a.shape != frame_b.shape:
        raise ValueError(
            f"frame shapes must match exactly, got {frame_a.shape} and {frame_b.shape}"
        )

    diff = np.abs(frame_a.astype(np.float32) - frame_b.astype(np.float32))
    if diff.ndim == 3:
        return np.asarray(diff.mean(axis=2), dtype=np.float32)
    return np.asarray(diff, dtype=np.float32)


def block_size_from_vision_config(vision_config: Mapping[str, Any]) -> int:
    """Derive a token block size from a model vision config."""

    raw_patch_size = vision_config.get("patch_size")
    raw_merge_size = vision_config.get("spatial_merge_size", 1)
    if not isinstance(raw_patch_size, int) or raw_patch_size <= 0:
        raise ValueError(f"invalid patch_size in vision config: {raw_patch_size!r}")
    if not isinstance(raw_merge_size, int) or raw_merge_size <= 0:
        raise ValueError(f"invalid spatial_merge_size in vision config: {raw_merge_size!r}")
    return raw_patch_size * raw_merge_size


def classify_blocks(
    frame_a: FrameArray,
    frame_b: FrameArray,
    *,
    block_size: int,
    thresholds: BlockThresholds = DEFAULT_THRESHOLDS,
) -> npt.NDArray[np.int32]:
    """Classify adjacent-frame blocks as STATIC, SHIFTED, or NOVEL."""

    if block_size <= 0:
        raise ValueError("block_size must be positive")
    if thresholds.shifted_threshold < thresholds.static_threshold:
        raise ValueError("shifted_threshold must be >= static_threshold")

    diff = _diff_plane(frame_a, frame_b)
    if diff.shape[0] % block_size != 0 or diff.shape[1] % block_size != 0:
        raise ValueError(
            "frame dimensions must be exact multiples of block_size, "
            f"got {diff.shape[:2]} and block_size={block_size}"
        )

    block_rows = diff.shape[0] // block_size
    block_cols = diff.shape[1] // block_size
    if block_rows == 0 or block_cols == 0:
        raise ValueError("frame is smaller than a single block")

    blocks = diff.reshape(block_rows, block_size, block_cols, block_size).mean(axis=(1, 3))

    classes = np.full_like(blocks, BlockClass.NOVEL, dtype=np.int32)
    classes[blocks < thresholds.static_threshold] = BlockClass.STATIC
    classes[(blocks >= thresholds.static_threshold) & (blocks < thresholds.shifted_threshold)] = (
        BlockClass.SHIFTED
    )
    return classes


def summarize_classification(classification: npt.NDArray[np.int32]) -> ClassificationSummary:
    """Summarize a classification grid into reusable counts."""

    if classification.ndim != 2:
        raise ValueError("classification must be a 2D grid")

    unique_labels = set(int(value) for value in np.unique(classification))
    expected = {int(BlockClass.STATIC), int(BlockClass.SHIFTED), int(BlockClass.NOVEL)}
    if not unique_labels.issubset(expected):
        raise ValueError(f"unexpected classification labels: {sorted(unique_labels - expected)}")

    total_blocks = int(classification.size)
    static_blocks = int((classification == int(BlockClass.STATIC)).sum())
    shifted_blocks = int((classification == int(BlockClass.SHIFTED)).sum())
    novel_blocks = int((classification == int(BlockClass.NOVEL)).sum())

    return ClassificationSummary(
        total_blocks=total_blocks,
        static_blocks=static_blocks,
        shifted_blocks=shifted_blocks,
        novel_blocks=novel_blocks,
    )
