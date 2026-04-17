"""Temporal block classification utilities."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import IntEnum, StrEnum
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


class BlockStatistic(StrEnum):
    """Per-block scalar derived from the diff plane."""

    MEAN = "mean"
    MAX_ABS = "max_abs"
    CHANGED_PIXEL_FRACTION = "changed_pixel_fraction"
    TOP_K_MEAN = "top_k_mean"


@dataclass(frozen=True, slots=True)
class BlockThresholds:
    """Thresholds used by the original repo's pixel-diff planner."""

    static_threshold: float = 3.0
    shifted_threshold: float = 8.0


DEFAULT_THRESHOLDS = BlockThresholds()


@dataclass(frozen=True, slots=True)
class PlannerConfig:
    """Planner statistic and thresholds for RGB diff classification.

    Thresholds are interpreted in the statistic's native units:

    - `MEAN`, `MAX_ABS`, `TOP_K_MEAN`: diff-plane intensity on the current
      `0-255` scale
    - `CHANGED_PIXEL_FRACTION`: fraction of block pixels whose diff-plane value
      exceeds `pixel_change_threshold`
    """

    statistic: BlockStatistic = BlockStatistic.MEAN
    static_threshold: float = 3.0
    shifted_threshold: float = 8.0
    pixel_change_threshold: float = 8.0
    top_k: int = 16


DEFAULT_PLANNER = PlannerConfig()


@dataclass(frozen=True, slots=True)
class ChildVetoConfig:
    """Phase 1.37 Planner 2.1 child-veto concentration guard.

    Promotes STATIC → NOVEL when any neighbor within `neighborhood` blocks has
    a parent-statistic score above `percentile` of the current frame-pair's
    score distribution. Rationale: a low-score block surrounded by high-score
    neighbors likely participates in a localized concentrated motion event
    that the parent statistic missed by averaging.
    """

    percentile: float = 0.95
    neighborhood: int = 1


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


def _reshape_blocks(
    diff: npt.NDArray[np.float32],
    *,
    block_size: int,
) -> npt.NDArray[np.float32]:
    if diff.shape[0] % block_size != 0 or diff.shape[1] % block_size != 0:
        raise ValueError(
            "frame dimensions must be exact multiples of block_size, "
            f"got {diff.shape[:2]} and block_size={block_size}"
        )
    block_rows = diff.shape[0] // block_size
    block_cols = diff.shape[1] // block_size
    if block_rows == 0 or block_cols == 0:
        raise ValueError("frame is smaller than a single block")
    reshaped = diff.reshape(block_rows, block_size, block_cols, block_size)
    return reshaped.transpose(0, 2, 1, 3).reshape(block_rows, block_cols, block_size * block_size)


def block_statistic_values(
    frame_a: FrameArray,
    frame_b: FrameArray,
    *,
    block_size: int,
    config: PlannerConfig = DEFAULT_PLANNER,
) -> npt.NDArray[np.float32]:
    """Return a scalar planner value per block."""

    if block_size <= 0:
        raise ValueError("block_size must be positive")
    if config.top_k <= 0:
        raise ValueError("top_k must be positive")

    diff = _diff_plane(frame_a, frame_b)
    per_block = _reshape_blocks(diff, block_size=block_size)

    if config.statistic == BlockStatistic.MEAN:
        return np.asarray(per_block.mean(axis=2), dtype=np.float32)
    if config.statistic == BlockStatistic.MAX_ABS:
        return np.asarray(per_block.max(axis=2), dtype=np.float32)
    if config.statistic == BlockStatistic.CHANGED_PIXEL_FRACTION:
        above = np.asarray(per_block > config.pixel_change_threshold, dtype=np.float32)
        return np.asarray(above.mean(axis=2), dtype=np.float32)
    if config.statistic == BlockStatistic.TOP_K_MEAN:
        k = min(config.top_k, per_block.shape[-1])
        top_k = np.partition(per_block, -k, axis=2)[:, :, -k:]
        return np.asarray(top_k.mean(axis=2), dtype=np.float32)
    raise ValueError(f"unsupported planner statistic: {config.statistic}")


def classify_blocks_with_planner(
    frame_a: FrameArray,
    frame_b: FrameArray,
    *,
    block_size: int,
    config: PlannerConfig = DEFAULT_PLANNER,
) -> npt.NDArray[np.int32]:
    """Classify adjacent-frame blocks with a configurable planner."""

    if block_size <= 0:
        raise ValueError("block_size must be positive")
    if config.shifted_threshold < config.static_threshold:
        raise ValueError("shifted_threshold must be >= static_threshold")

    blocks = block_statistic_values(frame_a, frame_b, block_size=block_size, config=config)
    classes = np.full_like(blocks, BlockClass.NOVEL, dtype=np.int32)
    classes[blocks < config.static_threshold] = BlockClass.STATIC
    classes[(blocks >= config.static_threshold) & (blocks < config.shifted_threshold)] = (
        BlockClass.SHIFTED
    )
    return classes


def classify_blocks(
    frame_a: FrameArray,
    frame_b: FrameArray,
    *,
    block_size: int,
    thresholds: BlockThresholds = DEFAULT_THRESHOLDS,
) -> npt.NDArray[np.int32]:
    """Classify adjacent-frame blocks as STATIC, SHIFTED, or NOVEL."""

    return classify_blocks_with_planner(
        frame_a,
        frame_b,
        block_size=block_size,
        config=PlannerConfig(
            statistic=BlockStatistic.MEAN,
            static_threshold=thresholds.static_threshold,
            shifted_threshold=thresholds.shifted_threshold,
        ),
    )


def _neighborhood_max(
    values: npt.NDArray[np.float32],
    *,
    neighborhood: int,
    include_self: bool = False,
) -> npt.NDArray[np.float32]:
    """Return per-cell maximum over a (2N+1)×(2N+1) neighborhood window.

    Pure numpy; no scipy dependency. Padded with -inf so edges see only real
    neighbors. When `include_self=False`, the cell itself is excluded from
    the max (useful for child-veto where we want to know if any NEIGHBOR is
    hot, independent of the current cell).
    """

    if values.ndim != 2:
        raise ValueError("values must be a 2D grid")
    if neighborhood < 1:
        raise ValueError("neighborhood must be >= 1")

    padded = np.pad(
        values,
        pad_width=neighborhood,
        mode="constant",
        constant_values=-np.inf,
    )
    rows, cols = values.shape
    acc = np.full_like(values, -np.inf, dtype=np.float32)
    for dr in range(-neighborhood, neighborhood + 1):
        for dc in range(-neighborhood, neighborhood + 1):
            if not include_self and dr == 0 and dc == 0:
                continue
            r0 = neighborhood + dr
            c0 = neighborhood + dc
            acc = np.maximum(acc, padded[r0 : r0 + rows, c0 : c0 + cols])
    return acc


def apply_child_veto(
    classification: npt.NDArray[np.int32],
    block_scores: npt.NDArray[np.float32],
    *,
    config: ChildVetoConfig,
) -> npt.NDArray[np.int32]:
    """Promote STATIC blocks whose neighbors exceed the percentile threshold.

    Pure function; does not mutate `classification`. SHIFTED and NOVEL blocks
    are left unchanged — they already have a motion signal. Only STATIC
    blocks are candidates for promotion, so child-veto can only ADD novelty,
    never remove it.
    """

    if classification.shape != block_scores.shape:
        raise ValueError(
            f"classification shape {classification.shape} must match "
            f"block_scores shape {block_scores.shape}"
        )
    if not 0.0 <= config.percentile <= 1.0:
        raise ValueError(f"percentile must be in [0, 1], got {config.percentile}")

    threshold = float(np.quantile(block_scores, config.percentile))
    neighbor_max = _neighborhood_max(
        block_scores.astype(np.float32, copy=False),
        neighborhood=config.neighborhood,
        include_self=False,
    )

    out = classification.copy()
    static_mask = classification == int(BlockClass.STATIC)
    hot_neighbor = neighbor_max > threshold
    out[static_mask & hot_neighbor] = int(BlockClass.NOVEL)
    return out


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
