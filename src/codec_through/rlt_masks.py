"""Run-length-tokenization style video masks.

This module ports the small RLT mask primitive by inspection, not the RLT
training stack. It is intentionally NumPy/Pillow only:

- no import from the local ``rlt/`` clone,
- no PyTorch/decord/xformers dependency,
- no model-side length encoding or variable-length packed attention.

The mask kernel mirrors RLT's endpoint comparison: for ``tubelet_size=2`` it
compares frame 3 against frame 0, frame 5 against frame 2, and so on. The first
temporal tubelet is always kept. Later tubelets keep a spatial token when the
mean absolute, ImageNet-normalized pixel change for that spatial cell exceeds
``threshold``.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
import numpy.typing as npt
from PIL import Image

NormalizeMode = Literal["imagenet", "none", "pre_normalized_imagenet"]
FloatArray = npt.NDArray[np.floating[Any]]
BoolArray = npt.NDArray[np.bool_]
IntArray = npt.NDArray[np.integer[Any]]

IMAGENET_MEAN = np.asarray([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.asarray([0.229, 0.224, 0.225], dtype=np.float32)


@dataclass(frozen=True, slots=True)
class RLTMaskConfig:
    """Configuration for the local RLT-style mask helper."""

    threshold: float = 0.1
    tubelet_size: int = 2
    image_size: tuple[int, int] = (224, 224)
    grid_shape: tuple[int, int] = (16, 16)
    normalize_mode: NormalizeMode = "imagenet"
    per_frame_min_keep: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "threshold": self.threshold,
            "tubelet_size": self.tubelet_size,
            "image_size": list(self.image_size),
            "grid_shape": list(self.grid_shape),
            "normalize_mode": self.normalize_mode,
            "per_frame_min_keep": self.per_frame_min_keep,
        }


@dataclass(frozen=True, slots=True)
class RLTMaskResult:
    """Mask output plus bookkeeping needed by profilers and runners."""

    config: RLTMaskConfig
    tubelet_keep_mask: BoolArray
    frame_keep_mask: BoolArray
    floor_active_frame_mask: BoolArray
    tubelet_scores: FloatArray
    tubelet_run_lengths: IntArray
    frame_run_lengths: IntArray
    first_tubelet_token_count: int
    threshold_active_token_count: int
    floor_active_token_count: int

    @property
    def frame_count(self) -> int:
        return int(self.frame_keep_mask.shape[0])

    @property
    def tubelet_count(self) -> int:
        return int(self.tubelet_keep_mask.shape[0])

    @property
    def tokens_per_frame(self) -> int:
        return int(self.frame_keep_mask.shape[1] * self.frame_keep_mask.shape[2])

    @property
    def kept_token_count(self) -> int:
        return int(self.frame_keep_mask.sum())

    @property
    def keep_rate(self) -> float:
        total = self.frame_count * self.tokens_per_frame
        return float(self.kept_token_count / total) if total else 0.0

    @property
    def floor_active(self) -> bool:
        return self.floor_active_token_count > 0

    def per_frame_keep_counts(self) -> list[int]:
        return [int(v) for v in self.frame_keep_mask.reshape(self.frame_count, -1).sum(axis=1)]

    def run_length_histogram(self) -> dict[str, int]:
        lengths = self.tubelet_run_lengths[self.tubelet_run_lengths > 0]
        values, counts = np.unique(lengths, return_counts=True)
        return {str(int(value)): int(count) for value, count in zip(values, counts, strict=True)}


def artifact_config_hash(payload: dict[str, Any]) -> str:
    """Stable hash for resumable artifact compatibility checks."""

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def coerce_frames_to_array(
    frames: Sequence[Image.Image | npt.NDArray[Any]],
    *,
    image_size: tuple[int, int],
    normalize_mode: NormalizeMode,
) -> FloatArray:
    """Convert PIL/NumPy frames to ``(T, H, W, 3)`` float32.

    ``image_size`` is ``(height, width)``. PIL frames and raw NumPy frames are
    resized through Pillow. Pre-normalized arrays must already have the target
    size; resizing negative normalized values as RGB would corrupt the domain.
    """

    if not frames:
        raise ValueError("at least one frame is required")

    height, width = image_size
    if height <= 0 or width <= 0:
        raise ValueError(f"image_size must be positive, got {image_size}")

    arrays: list[npt.NDArray[np.float32]] = []
    for frame in frames:
        if isinstance(frame, Image.Image):
            if normalize_mode == "pre_normalized_imagenet":
                raise ValueError("PIL frames cannot be declared pre_normalized_imagenet")
            image = frame.convert("RGB").resize((width, height), Image.Resampling.BICUBIC)
            arrays.append(np.asarray(image, dtype=np.float32))
            continue

        arr = np.asarray(frame)
        if arr.ndim != 3 or arr.shape[2] != 3:
            raise ValueError(f"array frames must have shape (H, W, 3), got {arr.shape}")
        if normalize_mode == "pre_normalized_imagenet":
            if arr.shape[:2] != (height, width):
                raise ValueError(
                    "pre_normalized_imagenet arrays must already match image_size; "
                    f"got {arr.shape[:2]} vs {(height, width)}"
                )
            arrays.append(arr.astype(np.float32, copy=False))
        else:
            image = Image.fromarray(_raw_frame_to_uint8(arr))
            image = image.resize((width, height), Image.Resampling.BICUBIC)
            arrays.append(np.asarray(image, dtype=np.float32))

    stacked = np.stack(arrays, axis=0).astype(np.float32, copy=False)
    return normalize_frame_array(stacked, mode=normalize_mode)


def normalize_frame_array(frames: FloatArray, *, mode: NormalizeMode) -> FloatArray:
    """Normalize or validate a ``(T, H, W, 3)`` frame tensor."""

    arr = np.asarray(frames, dtype=np.float32)
    if arr.ndim != 4 or arr.shape[3] != 3:
        raise ValueError(f"frames must be (T, H, W, 3), got {arr.shape}")
    if arr.shape[0] == 0:
        raise ValueError("at least one frame is required")

    finite = np.isfinite(arr)
    if not bool(finite.all()):
        raise ValueError("frames contain NaN or infinite values")

    min_value = float(arr.min())
    max_value = float(arr.max())

    if mode == "none":
        if min_value < 0.0 or max_value > 255.0:
            raise ValueError(
                f"normalize_mode='none' expects raw nonnegative pixels, got range "
                f"[{min_value:.3f}, {max_value:.3f}]"
            )
        return arr

    if mode == "imagenet":
        if min_value < 0.0 or max_value > 255.0:
            raise ValueError(
                "normalize_mode='imagenet' expects raw RGB pixels in [0, 255] "
                f"or [0, 1], got range [{min_value:.3f}, {max_value:.3f}]"
            )
        scaled = arr / 255.0 if max_value > 1.5 else arr.copy()
        return (scaled - IMAGENET_MEAN.reshape(1, 1, 1, 3)) / IMAGENET_STD.reshape(1, 1, 1, 3)

    if mode == "pre_normalized_imagenet":
        if min_value >= -0.25 and max_value <= 1.25:
            raise ValueError(
                "pre_normalized_imagenet expects ImageNet-normalized values, "
                f"not raw/float01 range [{min_value:.3f}, {max_value:.3f}]"
            )
        if min_value < -10.0 or max_value > 10.0:
            raise ValueError(
                "pre_normalized_imagenet values are outside a plausible range: "
                f"[{min_value:.3f}, {max_value:.3f}]"
            )
        return arr

    raise ValueError(f"unknown normalize mode {mode!r}")


def compute_rlt_keep_mask_from_frames(
    frames: Sequence[Image.Image | npt.NDArray[Any]],
    *,
    config: RLTMaskConfig,
) -> RLTMaskResult:
    """Compute an RLT-style keep mask from RGB frames."""

    arr = coerce_frames_to_array(
        frames,
        image_size=config.image_size,
        normalize_mode=config.normalize_mode,
    )
    return compute_rlt_keep_mask_from_array(arr, config=config, frames_are_normalized=True)


def compute_rlt_keep_mask_from_array(
    frames: FloatArray,
    *,
    config: RLTMaskConfig,
    frames_are_normalized: bool = False,
) -> RLTMaskResult:
    """Compute an RLT-style keep mask from an array.

    When ``frames_are_normalized`` is false, the array is interpreted according
    to ``config.normalize_mode`` and validated/normalized first.
    """

    arr = np.asarray(frames, dtype=np.float32)
    if not frames_are_normalized:
        arr = normalize_frame_array(arr, mode=config.normalize_mode)
    _validate_config_against_frames(config, arr)

    tubelet_size = config.tubelet_size
    frame_count = int(arr.shape[0])
    tubelet_count = frame_count // tubelet_size
    rows, cols = config.grid_shape

    tubelet_scores = np.zeros((tubelet_count, rows, cols), dtype=np.float32)
    tubelet_keep = np.zeros((tubelet_count, rows, cols), dtype=bool)
    tubelet_keep[0] = True

    for tubelet_idx in range(1, tubelet_count):
        prev_start = (tubelet_idx - 1) * tubelet_size
        curr_end = tubelet_idx * tubelet_size + tubelet_size - 1
        diff = np.abs(arr[curr_end] - arr[prev_start]).mean(axis=2)
        scores = aggregate_to_grid(diff, config.grid_shape)
        tubelet_scores[tubelet_idx] = scores
        tubelet_keep[tubelet_idx] = scores > config.threshold

    threshold_active = int(tubelet_keep[1:].sum() * tubelet_size)
    tubelet_run_lengths = compute_tubelet_run_lengths(tubelet_keep)
    frame_keep = np.repeat(tubelet_keep, tubelet_size, axis=0)
    frame_run_lengths = np.repeat(tubelet_run_lengths * tubelet_size, tubelet_size, axis=0)
    frame_keep, floor_mask = apply_per_frame_floor(
        frame_keep,
        scores=np.repeat(tubelet_scores, tubelet_size, axis=0),
        per_frame_min_keep=config.per_frame_min_keep,
    )

    return RLTMaskResult(
        config=config,
        tubelet_keep_mask=tubelet_keep,
        frame_keep_mask=frame_keep,
        floor_active_frame_mask=floor_mask,
        tubelet_scores=tubelet_scores,
        tubelet_run_lengths=tubelet_run_lengths,
        frame_run_lengths=frame_run_lengths,
        first_tubelet_token_count=rows * cols * tubelet_size,
        threshold_active_token_count=threshold_active,
        floor_active_token_count=int(floor_mask.sum()),
    )


def aggregate_to_grid(per_pixel: FloatArray, grid_shape: tuple[int, int]) -> FloatArray:
    """Mean-pool a 2D pixel plane into arbitrary grid cells."""

    plane = np.asarray(per_pixel, dtype=np.float32)
    if plane.ndim != 2:
        raise ValueError(f"per_pixel must be 2D, got {plane.shape}")
    rows, cols = grid_shape
    height, width = plane.shape
    if rows <= 0 or cols <= 0:
        raise ValueError(f"grid_shape must be positive, got {grid_shape}")
    if rows > height or cols > width:
        raise ValueError(f"grid_shape {grid_shape} cannot exceed pixel shape {plane.shape}")

    y_edges = _cell_edges(height, rows)
    x_edges = _cell_edges(width, cols)
    out = np.zeros((rows, cols), dtype=np.float32)
    for row in range(rows):
        y0, y1 = int(y_edges[row]), int(y_edges[row + 1])
        for col in range(cols):
            x0, x1 = int(x_edges[col]), int(x_edges[col + 1])
            out[row, col] = float(plane[y0:y1, x0:x1].mean())
    return out


def compute_tubelet_run_lengths(tubelet_keep_mask: BoolArray) -> IntArray:
    """Return duration in tubelets represented by each kept token.

    Non-kept positions receive zero.
    """

    keep = np.asarray(tubelet_keep_mask, dtype=bool)
    if keep.ndim != 3:
        raise ValueError(f"tubelet_keep_mask must be 3D, got {keep.shape}")
    tubelets, rows, cols = keep.shape
    lengths = np.zeros((tubelets, rows, cols), dtype=np.int32)
    for row in range(rows):
        for col in range(cols):
            kept = np.flatnonzero(keep[:, row, col])
            for idx, start in enumerate(kept):
                end = int(kept[idx + 1]) if idx + 1 < len(kept) else tubelets
                lengths[int(start), row, col] = end - int(start)
    return lengths


def apply_per_frame_floor(
    frame_keep_mask: BoolArray,
    *,
    scores: FloatArray,
    per_frame_min_keep: int,
) -> tuple[BoolArray, BoolArray]:
    """Ensure each frame keeps at least ``per_frame_min_keep`` tokens."""

    keep = np.asarray(frame_keep_mask, dtype=bool).copy()
    score_arr = np.asarray(scores, dtype=np.float32)
    if keep.ndim != 3:
        raise ValueError(f"frame_keep_mask must be 3D, got {keep.shape}")
    if score_arr.shape != keep.shape:
        raise ValueError(f"scores shape {score_arr.shape} must match keep mask {keep.shape}")
    if per_frame_min_keep < 0:
        raise ValueError("per_frame_min_keep must be nonnegative")
    floor = np.zeros_like(keep, dtype=bool)
    if per_frame_min_keep == 0:
        return keep, floor

    frames, rows, cols = keep.shape
    token_count = rows * cols
    if per_frame_min_keep > token_count:
        raise ValueError(
            f"per_frame_min_keep {per_frame_min_keep} exceeds tokens per frame {token_count}"
        )

    for frame_idx in range(frames):
        flat_keep = keep[frame_idx].reshape(token_count)
        need = per_frame_min_keep - int(flat_keep.sum())
        if need <= 0:
            continue
        flat_scores = score_arr[frame_idx].reshape(token_count)
        candidate_scores = np.where(flat_keep, -np.inf, flat_scores)
        fill_indices = _top_k_indices(candidate_scores, need)
        flat_keep[fill_indices] = True
        flat_floor = floor[frame_idx].reshape(token_count)
        flat_floor[fill_indices] = True
    return keep, floor


def project_bool_grid(mask: BoolArray, out_grid_shape: tuple[int, int]) -> BoolArray:
    """Nearest-neighbor project a ``(..., rows, cols)`` boolean grid."""

    arr = np.asarray(mask, dtype=bool)
    if arr.ndim < 2:
        raise ValueError(f"mask must have at least 2 dimensions, got {arr.shape}")
    in_rows, in_cols = int(arr.shape[-2]), int(arr.shape[-1])
    out_rows, out_cols = out_grid_shape
    if out_rows <= 0 or out_cols <= 0:
        raise ValueError(f"out_grid_shape must be positive, got {out_grid_shape}")
    row_idx = _nearest_indices(in_rows, out_rows)
    col_idx = _nearest_indices(in_cols, out_cols)
    return arr[..., row_idx, :][..., :, col_idx]


def project_float_grid(scores: FloatArray, out_grid_shape: tuple[int, int]) -> FloatArray:
    """Nearest-neighbor project a ``(..., rows, cols)`` float grid."""

    arr = np.asarray(scores, dtype=np.float32)
    if arr.ndim < 2:
        raise ValueError(f"scores must have at least 2 dimensions, got {arr.shape}")
    in_rows, in_cols = int(arr.shape[-2]), int(arr.shape[-1])
    out_rows, out_cols = out_grid_shape
    if out_rows <= 0 or out_cols <= 0:
        raise ValueError(f"out_grid_shape must be positive, got {out_grid_shape}")
    row_idx = _nearest_indices(in_rows, out_rows)
    col_idx = _nearest_indices(in_cols, out_cols)
    return arr[..., row_idx, :][..., :, col_idx]


def jaccard(a: BoolArray, b: BoolArray) -> float:
    """Jaccard overlap for two boolean masks."""

    left = np.asarray(a, dtype=bool)
    right = np.asarray(b, dtype=bool)
    if left.shape != right.shape:
        raise ValueError(f"mask shapes differ: {left.shape} vs {right.shape}")
    union = int(np.logical_or(left, right).sum())
    if union == 0:
        return 1.0
    return float(np.logical_and(left, right).sum() / union)


def mask_summary(result: RLTMaskResult) -> dict[str, Any]:
    """JSON-serializable per-item summary."""

    return {
        "frame_count": result.frame_count,
        "tubelet_count": result.tubelet_count,
        "tokens_per_frame": result.tokens_per_frame,
        "kept_token_count": result.kept_token_count,
        "keep_rate": result.keep_rate,
        "floor_active": result.floor_active,
        "first_tubelet_token_count": result.first_tubelet_token_count,
        "threshold_active_token_count": result.threshold_active_token_count,
        "floor_active_token_count": result.floor_active_token_count,
        "per_frame_keep_counts": result.per_frame_keep_counts(),
        "run_length_histogram": result.run_length_histogram(),
    }


def _validate_config_against_frames(config: RLTMaskConfig, frames: FloatArray) -> None:
    if config.threshold < 0.0:
        raise ValueError(f"threshold must be nonnegative, got {config.threshold}")
    if config.tubelet_size <= 0:
        raise ValueError(f"tubelet_size must be positive, got {config.tubelet_size}")
    if config.per_frame_min_keep < 0:
        raise ValueError("per_frame_min_keep must be nonnegative")
    if frames.ndim != 4 or frames.shape[3] != 3:
        raise ValueError(f"frames must be (T, H, W, 3), got {frames.shape}")
    if frames.shape[0] < 2 * config.tubelet_size:
        raise ValueError(
            f"frame_count {frames.shape[0]} cannot form two tubelets of size {config.tubelet_size}"
        )
    if frames.shape[0] % config.tubelet_size != 0:
        raise ValueError(
            f"frame_count {frames.shape[0]} must be divisible by tubelet_size {config.tubelet_size}"
        )
    rows, cols = config.grid_shape
    if rows <= 0 or cols <= 0:
        raise ValueError(f"grid_shape must be positive, got {config.grid_shape}")
    if rows > frames.shape[1] or cols > frames.shape[2]:
        raise ValueError(
            f"grid_shape {config.grid_shape} cannot exceed frame size {frames.shape[1:3]}"
        )
    if config.per_frame_min_keep > rows * cols:
        raise ValueError(
            f"per_frame_min_keep {config.per_frame_min_keep} exceeds tokens per frame {rows * cols}"
        )


def _raw_frame_to_uint8(arr: npt.NDArray[Any]) -> npt.NDArray[np.uint8]:
    numeric = np.asarray(arr)
    if not np.issubdtype(numeric.dtype, np.number):
        raise ValueError(f"array frame must be numeric, got {numeric.dtype}")
    numeric_f = numeric.astype(np.float32, copy=False)
    min_value = float(numeric_f.min())
    max_value = float(numeric_f.max())
    if min_value < 0.0 or max_value > 255.0:
        raise ValueError(
            f"raw frame arrays must be in [0, 255] or [0, 1], got "
            f"[{min_value:.3f}, {max_value:.3f}]"
        )
    scaled = numeric_f * 255.0 if max_value <= 1.5 else numeric_f
    return np.clip(np.rint(scaled), 0, 255).astype(np.uint8)


def _cell_edges(size: int, cells: int) -> npt.NDArray[np.int64]:
    edges = np.linspace(0, size, cells + 1)
    rounded = np.rint(edges).astype(np.int64)
    for idx in range(cells):
        if rounded[idx + 1] <= rounded[idx]:
            rounded[idx + 1] = rounded[idx] + 1
    rounded[-1] = size
    return rounded


def _nearest_indices(in_size: int, out_size: int) -> npt.NDArray[np.int64]:
    if in_size <= 0 or out_size <= 0:
        raise ValueError("grid sizes must be positive")
    centers = (np.arange(out_size, dtype=np.float64) + 0.5) * in_size / out_size
    return np.clip(np.floor(centers).astype(np.int64), 0, in_size - 1)


def _top_k_indices(scores: FloatArray, k: int) -> npt.NDArray[np.int64]:
    flat = np.asarray(scores, dtype=np.float32).reshape(-1)
    if k < 0:
        raise ValueError("k must be nonnegative")
    if k == 0:
        return np.zeros((0,), dtype=np.int64)
    if k > flat.size:
        raise ValueError(f"k {k} exceeds score count {flat.size}")
    order = np.lexsort((np.arange(flat.size), -flat))
    return order[:k].astype(np.int64)
