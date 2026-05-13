"""Deterministic visual evidence operators for query-routing experiments.

These helpers are deliberately small and numpy-only. The first branch uses
them for Q1 smoke tests and for Gemma C-VISION keep-mask construction where
the operator can be expressed over explicit encoder positions.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

import numpy as np
import numpy.typing as npt

from codec_through.rlt_masks import RLTMaskResult, project_float_grid

BoolArray = npt.NDArray[np.bool_]
FloatArray = npt.NDArray[np.floating]


@dataclass(frozen=True)
class OperatorLedger:
    """Budget accounting for one per-frame operator mask."""

    operator_plan: str
    operator_budget_mode: str
    reserved_positions_per_frame: list[int]
    complement_size_per_frame: list[int]
    operator_overlap_count_per_frame: list[int]
    static_floor_overflow: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "operator_plan": self.operator_plan,
            "operator_budget_mode": self.operator_budget_mode,
            "reserved_positions_per_frame": self.reserved_positions_per_frame,
            "complement_size_per_frame": self.complement_size_per_frame,
            "operator_overlap_count_per_frame": self.operator_overlap_count_per_frame,
            "static_floor_overflow": self.static_floor_overflow,
        }


def keep_count(valid_count: int, keep_rate: float) -> int:
    if valid_count <= 0:
        raise ValueError(f"valid_count must be positive, got {valid_count}")
    if not (0.0 < keep_rate <= 1.0):
        raise ValueError(f"keep_rate must be in (0, 1], got {keep_rate}")
    return max(1, int(valid_count * keep_rate))


def grid_shape_from_valid_positions(positions_row: npt.NDArray[Any]) -> tuple[int, int]:
    row = np.asarray(positions_row, dtype=np.int64)
    if row.ndim != 2 or row.shape[1] != 2:
        raise ValueError(f"positions row must be [L,2], got {row.shape}")
    valid = (row[:, 0] >= 0) & (row[:, 1] >= 0)
    if not bool(valid.any()):
        raise ValueError("positions row has no valid entries")
    width = int(row[valid, 0].max()) + 1
    height = int(row[valid, 1].max()) + 1
    if int(valid.sum()) != width * height:
        raise ValueError(
            f"valid positions are not a dense grid: count={int(valid.sum())}, "
            f"shape=({height}, {width})"
        )
    return height, width


def static_floor_indices_for_grid(
    grid_shape: tuple[int, int], stride: int
) -> npt.NDArray[np.int64]:
    rows, cols = grid_shape
    if rows <= 0 or cols <= 0:
        raise ValueError(f"grid_shape must be positive, got {grid_shape}")
    if stride <= 0:
        raise ValueError(f"stride must be positive, got {stride}")
    coords: list[int] = []
    for y in range(0, rows, stride):
        for x in range(0, cols, stride):
            coords.append(y * cols + x)
    return np.asarray(coords, dtype=np.int64)


def fixed_uniform_mask_for_positions(
    positions: npt.NDArray[Any], *, keep_rate: float
) -> tuple[BoolArray, OperatorLedger]:
    pos = np.asarray(positions, dtype=np.int64)
    if pos.ndim != 3 or pos.shape[-1] != 2:
        raise ValueError(f"positions must be [B,L,2], got {pos.shape}")
    mask = np.zeros(pos.shape[:2], dtype=bool)
    reserved: list[int] = []
    complement: list[int] = []
    for row_idx, row in enumerate(pos):
        valid_idx = np.flatnonzero((row[:, 0] >= 0) & (row[:, 1] >= 0))
        k = keep_count(int(valid_idx.size), keep_rate)
        ranks = np.floor((np.arange(k, dtype=np.float64) + 0.5) * valid_idx.size / k).astype(
            np.int64
        )
        chosen = valid_idx[ranks]
        mask[row_idx, chosen] = True
        reserved.append(0)
        complement.append(int(valid_idx.size))
    return mask, OperatorLedger(
        operator_plan="fixed_uniform",
        operator_budget_mode="per_frame",
        reserved_positions_per_frame=reserved,
        complement_size_per_frame=complement,
        operator_overlap_count_per_frame=[0] * int(pos.shape[0]),
    )


def random_valid_mask_for_positions(
    positions: npt.NDArray[Any], *, keep_rate: float, seed: int
) -> tuple[BoolArray, OperatorLedger]:
    pos = np.asarray(positions, dtype=np.int64)
    if pos.ndim != 3 or pos.shape[-1] != 2:
        raise ValueError(f"positions must be [B,L,2], got {pos.shape}")
    mask = np.zeros(pos.shape[:2], dtype=bool)
    for row_idx, row in enumerate(pos):
        valid_idx = np.flatnonzero((row[:, 0] >= 0) & (row[:, 1] >= 0))
        k = keep_count(int(valid_idx.size), keep_rate)
        digest = hashlib.sha256(f"{seed}:{row_idx}".encode()).digest()
        row_seed = int.from_bytes(digest[:8], "little", signed=False)
        rng = np.random.default_rng(row_seed)
        chosen = np.sort(rng.choice(valid_idx, size=k, replace=False))
        mask[row_idx, chosen] = True
    return mask, OperatorLedger(
        operator_plan="random_valid_position",
        operator_budget_mode="per_frame",
        reserved_positions_per_frame=[0] * int(pos.shape[0]),
        complement_size_per_frame=[int(((row[:, 0] >= 0) & (row[:, 1] >= 0)).sum()) for row in pos],
        operator_overlap_count_per_frame=[0] * int(pos.shape[0]),
    )


def _top_k(scores: npt.NDArray[np.float32], k: int) -> npt.NDArray[np.int64]:
    if k <= 0:
        return np.asarray([], dtype=np.int64)
    order = np.lexsort((np.arange(scores.size), -scores))
    return order[:k].astype(np.int64)


def rlt_static_floor_mask_for_positions(
    result: RLTMaskResult,
    *,
    positions: npt.NDArray[Any],
    keep_rate: float,
    floor_stride: int,
) -> tuple[BoolArray, OperatorLedger]:
    """Reserve a static spatial floor, then fill remaining K by RLT scores."""

    pos = np.asarray(positions, dtype=np.int64)
    if pos.ndim != 3 or pos.shape[-1] != 2:
        raise ValueError(f"positions must be [B,L,2], got {pos.shape}")
    if pos.shape[0] != result.frame_count:
        raise ValueError(f"position rows {pos.shape[0]} must match RLT frames {result.frame_count}")
    frame_scores = np.repeat(result.tubelet_scores, result.config.tubelet_size, axis=0)
    frame_scores = frame_scores[: result.frame_count]
    mask = np.zeros(pos.shape[:2], dtype=bool)
    reserved_counts: list[int] = []
    complement_counts: list[int] = []
    overlap_counts: list[int] = []
    static_floor_overflow = False
    for row_idx, row in enumerate(pos):
        valid = (row[:, 0] >= 0) & (row[:, 1] >= 0)
        valid_idx = np.flatnonzero(valid)
        k = keep_count(int(valid_idx.size), keep_rate)
        grid_shape = grid_shape_from_valid_positions(row)
        floor_raster = static_floor_indices_for_grid(grid_shape, floor_stride)
        rows, cols = grid_shape
        raster_to_token: dict[int, int] = {
            int(y) * cols + int(x): int(idx) for idx, (x, y) in enumerate(row) if x >= 0 and y >= 0
        }
        floor_tokens = np.asarray([raster_to_token[int(r)] for r in floor_raster], dtype=np.int64)
        overflow = bool(floor_tokens.size > k)
        if overflow:
            ranks = np.floor((np.arange(k, dtype=np.float64) + 0.5) * floor_tokens.size / k).astype(
                np.int64
            )
            floor_tokens = floor_tokens[ranks]
        score_grid = project_float_grid(frame_scores[row_idx], grid_shape)
        token_scores = np.full((row.shape[0],), -np.inf, dtype=np.float32)
        token_scores[valid] = score_grid[row[valid, 1], row[valid, 0]]
        token_scores[floor_tokens] = -np.inf
        fill = _top_k(token_scores, k - int(floor_tokens.size))
        mask[row_idx, floor_tokens] = True
        mask[row_idx, fill] = True
        reserved_counts.append(int(floor_tokens.size))
        complement_counts.append(int(valid_idx.size - floor_tokens.size))
        overlap_counts.append(0)
        static_floor_overflow = overflow if row_idx == 0 else static_floor_overflow or overflow
    return mask, OperatorLedger(
        operator_plan="rlt_topk_static_floor",
        operator_budget_mode="per_frame",
        reserved_positions_per_frame=reserved_counts,
        complement_size_per_frame=complement_counts,
        operator_overlap_count_per_frame=overlap_counts,
        static_floor_overflow=static_floor_overflow,
    )


def endpoint_anchor_budget(
    *,
    frame_count: int,
    valid_positions_per_frame: int,
    keep_rate: float,
    anchor_frames: tuple[int, ...] = (0, -1),
) -> dict[str, int | list[int]]:
    if frame_count <= 0:
        raise ValueError(f"frame_count must be positive, got {frame_count}")
    anchors = {frame if frame >= 0 else frame_count + frame for frame in anchor_frames}
    if any(frame < 0 or frame >= frame_count for frame in anchors):
        raise ValueError(
            f"anchor_frames out of range for frame_count={frame_count}: {anchor_frames}"
        )
    total_budget = frame_count * keep_count(valid_positions_per_frame, keep_rate)
    anchor_debit = len(anchors) * valid_positions_per_frame
    remaining_frames = frame_count - len(anchors)
    remaining_budget = total_budget - anchor_debit
    if remaining_budget < 0:
        raise ValueError(
            f"endpoint anchors debit {anchor_debit} positions but total budget is {total_budget}"
        )
    base = remaining_budget // remaining_frames if remaining_frames else 0
    remainder = remaining_budget % remaining_frames if remaining_frames else 0
    per_remaining_frame = [base + (1 if idx < remainder else 0) for idx in range(remaining_frames)]
    return {
        "total_budget": total_budget,
        "anchor_debit": anchor_debit,
        "remaining_frames": remaining_frames,
        "remaining_budget": remaining_budget,
        "per_remaining_frame_min": base,
        "per_remaining_frame_max": base + (1 if remainder else 0),
        "remaining_budget_remainder": remainder,
        "remaining_budget_per_frame": per_remaining_frame,
    }
