"""Temporal block classification utilities."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Any

import numpy as np
import numpy.typing as npt

FrameArray = npt.NDArray[Any]


class BlockClass(IntEnum):
    """Semantic labels for adjacent-frame block reuse."""

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
    if frame_a.ndim not in (2, 3) or frame_b.ndim not in (2, 3):
        raise ValueError("expected 2D grayscale or 3D color frames")

    height = min(frame_a.shape[0], frame_b.shape[0])
    width = min(frame_a.shape[1], frame_b.shape[1])
    diff = np.abs(
        frame_a[:height, :width].astype(np.float32) - frame_b[:height, :width].astype(np.float32)
    )
    if diff.ndim == 3:
        return np.asarray(diff.mean(axis=2), dtype=np.float32)
    return np.asarray(diff, dtype=np.float32)


def classify_blocks(
    frame_a: FrameArray,
    frame_b: FrameArray,
    *,
    block_size: int = 28,
    thresholds: BlockThresholds = DEFAULT_THRESHOLDS,
) -> npt.NDArray[np.int32]:
    """Classify adjacent-frame blocks as STATIC, SHIFTED, or NOVEL."""

    if block_size <= 0:
        raise ValueError("block_size must be positive")
    if thresholds.shifted_threshold < thresholds.static_threshold:
        raise ValueError("shifted_threshold must be >= static_threshold")

    diff = _diff_plane(frame_a, frame_b)
    block_rows = diff.shape[0] // block_size
    block_cols = diff.shape[1] // block_size
    if block_rows == 0 or block_cols == 0:
        return np.zeros((1, 1), dtype=np.int32)

    cropped = diff[: block_rows * block_size, : block_cols * block_size]
    blocks = cropped.reshape(block_rows, block_size, block_cols, block_size).mean(axis=(1, 3))

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
