"""Clean-room OneVision-style sparse patch allocation primitives.

The functions here model the codec patchification surface needed for
VLMaxxing experiments: fuse motion/residual score planes, allocate a fixed
visible-patch budget across a clip, and compute allocation diagnostics. They
do not implement OneVision-Encoder's trained vision tower.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

import numpy as np
import numpy.typing as npt

FuseMode = Literal["weighted", "sum", "max", "geomean"]
PatchSource = Literal["anchor", "score"]


@dataclass(frozen=True, slots=True)
class PatchificationConfig:
    """Configuration for global codec-style patch budget allocation."""

    token_budget: int
    anchor_frames: tuple[int, ...] = (0,)

    def __post_init__(self) -> None:
        if self.token_budget <= 0:
            raise ValueError("token_budget must be positive")
        if len(set(self.anchor_frames)) != len(self.anchor_frames):
            raise ValueError("anchor_frames must not contain duplicates")


@dataclass(frozen=True, slots=True)
class VisiblePatch:
    """One selected patch in virtual temporal-height-width coordinates."""

    frame: int
    row: int
    col: int
    score: float
    source: PatchSource


@dataclass(frozen=True, slots=True)
class TemporalCoverage:
    """Temporal distribution of selected visible patches."""

    observed_frames: int
    observed_fraction: float
    max_gap: int
    mean_gap: float
    entropy_bits: float


@dataclass(frozen=True, slots=True)
class SpatialBias:
    """Spatial distribution diagnostics for selected visible patches."""

    center_fraction: float
    boundary_fraction: float
    mean_center_distance: float
    entropy_bits: float


def percentile_normalize(
    values: npt.ArrayLike,
    *,
    percentile: float = 95.0,
    clip: bool = True,
) -> npt.NDArray[np.float32]:
    """Normalize a finite non-negative score array by a robust percentile."""

    array = np.asarray(values, dtype=np.float32)
    _validate_score_array(array, name="values")
    if not (0.0 < percentile <= 100.0):
        raise ValueError("percentile must lie in (0, 100]")

    scale = float(np.percentile(array, percentile))
    if scale <= 0.0:
        return np.zeros_like(array, dtype=np.float32)
    normalized = np.asarray(array / np.float32(scale), dtype=np.float32)
    if clip:
        normalized = np.asarray(np.clip(normalized, 0.0, 1.0), dtype=np.float32)
    return normalized


def fuse_motion_residual(
    motion_scores: npt.ArrayLike,
    residual_scores: npt.ArrayLike,
    *,
    mode: FuseMode = "weighted",
    motion_weight: float = 1.0,
    residual_weight: float = 1.0,
    normalize_inputs: bool = True,
) -> npt.NDArray[np.float32]:
    """Fuse motion-vector and residual-energy score volumes.

    Inputs may be pixel planes, patch grids, or full ``T x H x W`` score
    volumes, but both inputs must have the same shape.
    """

    motion = np.asarray(motion_scores, dtype=np.float32)
    residual = np.asarray(residual_scores, dtype=np.float32)
    _validate_score_array(motion, name="motion_scores")
    _validate_score_array(residual, name="residual_scores")
    if motion.shape != residual.shape:
        raise ValueError(
            "motion_scores and residual_scores must have the same shape, "
            f"got {motion.shape} and {residual.shape}"
        )
    if motion_weight < 0.0 or residual_weight < 0.0:
        raise ValueError("motion_weight and residual_weight must be non-negative")
    if motion_weight == 0.0 and residual_weight == 0.0:
        raise ValueError("at least one fusion weight must be positive")

    if normalize_inputs:
        motion = percentile_normalize(motion)
        residual = percentile_normalize(residual)

    weighted_motion = np.asarray(motion * np.float32(motion_weight), dtype=np.float32)
    weighted_residual = np.asarray(residual * np.float32(residual_weight), dtype=np.float32)
    if mode in {"weighted", "sum"}:
        fused = weighted_motion + weighted_residual
        if mode == "weighted":
            fused = fused / np.float32(motion_weight + residual_weight)
    elif mode == "max":
        fused = np.maximum(weighted_motion, weighted_residual)
    elif mode == "geomean":
        fused = np.sqrt(weighted_motion * weighted_residual, dtype=np.float32)
    else:
        raise ValueError(f"unsupported fusion mode: {mode}")
    return np.asarray(fused, dtype=np.float32)


def pool_patch_scores(
    score_frames: npt.ArrayLike,
    *,
    patch_size: int,
) -> npt.NDArray[np.float32]:
    """Mean-pool ``T x H x W`` score frames into ``T x Gh x Gw`` patch scores."""

    scores = np.asarray(score_frames, dtype=np.float32)
    _validate_score_array(scores, name="score_frames")
    if scores.ndim != 3:
        raise ValueError("score_frames must be a 3D T x H x W array")
    if patch_size <= 0:
        raise ValueError("patch_size must be positive")
    frames, height, width = scores.shape
    if height % patch_size != 0 or width % patch_size != 0:
        raise ValueError(
            "score frame shape must be divisible by patch_size, "
            f"got {(height, width)} with patch_size={patch_size}"
        )
    rows = height // patch_size
    cols = width // patch_size
    reshaped = scores.reshape(frames, rows, patch_size, cols, patch_size)
    pooled = reshaped.transpose(0, 1, 3, 2, 4).mean(axis=(3, 4))
    return np.asarray(pooled, dtype=np.float32)


def select_visible_patches(
    patch_scores: npt.ArrayLike,
    *,
    config: PatchificationConfig,
) -> list[VisiblePatch]:
    """Select mandatory anchor-frame patches plus globally ranked score patches."""

    scores = np.asarray(patch_scores, dtype=np.float32)
    _validate_score_array(scores, name="patch_scores")
    if scores.ndim != 3:
        raise ValueError("patch_scores must be a 3D T x Gh x Gw array")
    frames, rows, cols = (int(value) for value in scores.shape)
    total_patches = frames * rows * cols
    if config.token_budget > total_patches:
        raise ValueError(
            f"token_budget={config.token_budget} exceeds total patch count={total_patches}"
        )

    anchor_positions: set[tuple[int, int, int]] = set()
    for frame_index in config.anchor_frames:
        if not (0 <= frame_index < frames):
            raise ValueError(f"anchor frame {frame_index} is outside [0, {frames})")
        for row in range(rows):
            for col in range(cols):
                anchor_positions.add((frame_index, row, col))
    if len(anchor_positions) > config.token_budget:
        raise ValueError(
            "mandatory anchor frames exceed token_budget, "
            f"need {len(anchor_positions)} tokens for anchors"
        )

    selected: list[VisiblePatch] = [
        VisiblePatch(
            frame=frame,
            row=row,
            col=col,
            score=float(scores[frame, row, col]),
            source="anchor",
        )
        for frame, row, col in sorted(anchor_positions)
    ]

    candidates: list[tuple[float, int, int, int]] = []
    for frame in range(frames):
        for row in range(rows):
            for col in range(cols):
                if (frame, row, col) in anchor_positions:
                    continue
                candidates.append((float(scores[frame, row, col]), frame, row, col))
    candidates.sort(key=lambda item: (-item[0], item[1], item[2], item[3]))

    remaining = config.token_budget - len(selected)
    selected.extend(
        VisiblePatch(frame=frame, row=row, col=col, score=score, source="score")
        for score, frame, row, col in candidates[:remaining]
    )
    return selected


def visible_indices_array(patches: Sequence[VisiblePatch]) -> npt.NDArray[np.int32]:
    """Return selected patch coordinates as ``N x 3`` int32 ``[t, h, w]`` rows."""

    if not patches:
        return np.empty((0, 3), dtype=np.int32)
    return np.asarray(
        [[patch.frame, patch.row, patch.col] for patch in patches],
        dtype=np.int32,
    )


def count_tokens_by_frame(
    patches: Sequence[VisiblePatch],
    *,
    total_frames: int,
) -> npt.NDArray[np.int32]:
    """Count selected patches per frame."""

    if total_frames <= 0:
        raise ValueError("total_frames must be positive")
    counts = np.zeros(total_frames, dtype=np.int32)
    for patch in patches:
        if not (0 <= patch.frame < total_frames):
            raise ValueError(f"patch frame {patch.frame} is outside [0, {total_frames})")
        counts[patch.frame] += 1
    return counts


def temporal_coverage(
    patches: Sequence[VisiblePatch],
    *,
    total_frames: int,
) -> TemporalCoverage:
    """Compute temporal coverage metrics for a visible-patch set."""

    counts = count_tokens_by_frame(patches, total_frames=total_frames)
    observed = np.flatnonzero(counts)
    observed_frames = int(observed.size)
    observed_fraction = float(observed_frames / total_frames)
    if observed_frames <= 1:
        max_gap = 0
        mean_gap = 0.0
    else:
        gaps = np.diff(observed)
        max_gap = int(gaps.max())
        mean_gap = float(gaps.mean())
    return TemporalCoverage(
        observed_frames=observed_frames,
        observed_fraction=observed_fraction,
        max_gap=max_gap,
        mean_gap=mean_gap,
        entropy_bits=_entropy_bits(counts.astype(np.float64)),
    )


def spatial_bias(
    patches: Sequence[VisiblePatch],
    *,
    grid_shape: tuple[int, int],
) -> SpatialBias:
    """Compute center, boundary, and entropy diagnostics over patch positions."""

    rows, cols = grid_shape
    if rows <= 0 or cols <= 0:
        raise ValueError("grid_shape dimensions must be positive")
    if not patches:
        raise ValueError("patches must not be empty")

    counts = np.zeros((rows, cols), dtype=np.float64)
    for patch in patches:
        if not (0 <= patch.row < rows and 0 <= patch.col < cols):
            raise ValueError(f"patch coordinate {(patch.row, patch.col)} is outside {grid_shape}")
        counts[patch.row, patch.col] += 1.0
    total = float(counts.sum())

    center_row_start = rows // 4
    center_row_end = rows - center_row_start
    center_col_start = cols // 4
    center_col_end = cols - center_col_start
    center_count = float(
        counts[center_row_start:center_row_end, center_col_start:center_col_end].sum()
    )
    boundary_count = float(
        counts[0, :].sum() + counts[-1, :].sum() + counts[1:-1, 0].sum() + counts[1:-1, -1].sum()
    )

    row_center = (rows - 1) / 2.0
    col_center = (cols - 1) / 2.0
    max_distance = float(np.hypot(row_center, col_center))
    distance_sum = 0.0
    for patch in patches:
        distance_sum += float(np.hypot(patch.row - row_center, patch.col - col_center))
    mean_center_distance = 0.0 if max_distance == 0.0 else distance_sum / total / max_distance

    return SpatialBias(
        center_fraction=center_count / total,
        boundary_fraction=boundary_count / total,
        mean_center_distance=mean_center_distance,
        entropy_bits=_entropy_bits(counts.reshape(-1)),
    )


def _validate_score_array(array: npt.NDArray[np.float32], *, name: str) -> None:
    if array.size == 0:
        raise ValueError(f"{name} must not be empty")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    if np.any(array < 0.0):
        raise ValueError(f"{name} must contain non-negative scores")


def _entropy_bits(counts: npt.NDArray[np.float64]) -> float:
    total = float(counts.sum())
    if total <= 0.0:
        return 0.0
    probabilities = counts[counts > 0.0] / total
    return float(-(probabilities * np.log2(probabilities)).sum())
