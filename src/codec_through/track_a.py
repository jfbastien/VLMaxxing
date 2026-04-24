"""Helpers for local Track A experiment bring-up."""

from __future__ import annotations

import math
from collections.abc import Iterable

import numpy as np
import numpy.typing as npt

from .temporal import BlockClass


def resized_dimensions_for_block_multiple(
    width: int,
    height: int,
    *,
    block_size: int,
    target_height: int | None = None,
) -> tuple[int, int]:
    """Return a preserve-aspect resize aligned to a model token block size.

    The returned dimensions are integer multiples of ``block_size``. If the
    incoming image is already aligned and ``target_height`` is ``None``, the
    original size is preserved.
    """

    if width <= 0 or height <= 0:
        raise ValueError("width and height must be positive")
    if block_size <= 0:
        raise ValueError("block_size must be positive")
    if target_height is not None and (target_height <= 0 or target_height % block_size != 0):
        raise ValueError("target_height must be a positive multiple of block_size")

    if target_height is None and width % block_size == 0 and height % block_size == 0:
        return width, height

    resolved_target_height = (
        target_height if target_height is not None else round(height / block_size) * block_size
    )
    if resolved_target_height <= 0:
        raise ValueError("resolved target height must be positive")

    scale = resolved_target_height / height
    resized_width = round((width * scale) / block_size) * block_size
    if resized_width <= 0:
        raise ValueError("resolved width must be positive")
    return resized_width, resolved_target_height


def qwen_merged_token_counts(
    image_grid_thw: npt.NDArray[np.integer],
    *,
    spatial_merge_size: int,
) -> list[int]:
    """Return per-frame merged-token counts from Qwen image grid metadata."""

    return [
        height * width
        for height, width in qwen_merged_grid_shapes(
            image_grid_thw, spatial_merge_size=spatial_merge_size
        )
    ]


def qwen_merged_grid_shapes(
    image_grid_thw: npt.NDArray[np.integer],
    *,
    spatial_merge_size: int,
) -> list[tuple[int, int]]:
    """Return per-frame merged-token grid shapes from Qwen image metadata."""

    if spatial_merge_size <= 0:
        raise ValueError("spatial_merge_size must be positive")
    if image_grid_thw.ndim != 2 or image_grid_thw.shape[1] != 3:
        raise ValueError("image_grid_thw must be shaped [num_images, 3]")

    shapes: list[tuple[int, int]] = []
    for row in image_grid_thw:
        temporal, height, width = (int(value) for value in row)
        if temporal != 1:
            raise ValueError(f"expected temporal grid of 1 for image features, got {temporal}")
        if height % spatial_merge_size != 0 or width % spatial_merge_size != 0:
            raise ValueError(
                "height and width must be divisible by spatial_merge_size, "
                f"got row={tuple(int(value) for value in row)}"
            )
        shapes.append((height // spatial_merge_size, width // spatial_merge_size))
    return shapes


def square_grid_shape_from_token_count(token_count: int) -> tuple[int, int]:
    """Return a square token grid shape for a perfect-square token count."""

    if token_count <= 0:
        raise ValueError("token_count must be positive")
    side = math.isqrt(token_count)
    if side * side != token_count:
        raise ValueError(f"token_count must be a perfect square, got {token_count}")
    return side, side


def gemma_cached_token_index_grid(
    frame_size: tuple[int, int],
    *,
    patch_size: int,
    pooling_kernel_size: int,
    output_length: int,
) -> npt.NDArray[np.int32]:
    """Return the Gemma cached-feature token index for each patch cell.

    This matches the current ``mlx-vlm`` Gemma4 ``encode_image`` path, which
    pools a patch grid into a compact cached-feature sequence before those
    features are scattered into the language model. It is intentionally
    distinct from the separate novelty-pruning path, which operates on a
    different token geometry.
    """

    width, height = frame_size
    if width <= 0 or height <= 0:
        raise ValueError("frame dimensions must be positive")
    if patch_size <= 0:
        raise ValueError("patch_size must be positive")
    if pooling_kernel_size <= 0:
        raise ValueError("pooling_kernel_size must be positive")
    if output_length <= 0:
        raise ValueError("output_length must be positive")
    if width % patch_size != 0 or height % patch_size != 0:
        raise ValueError("frame dimensions must be multiples of patch_size")

    patch_cols = width // patch_size
    patch_rows = height // patch_size
    token_stride = patch_cols // pooling_kernel_size
    if token_stride <= 0:
        raise ValueError("resolved Gemma token stride must be positive")

    grid_x = (np.arange(patch_cols, dtype=np.int32) // pooling_kernel_size)[None, :]
    grid_y = (np.arange(patch_rows, dtype=np.int32) // pooling_kernel_size)[:, None]
    token_index_grid = grid_x + token_stride * grid_y

    token_count = int(token_index_grid.max()) + 1
    if token_count > output_length:
        raise ValueError(
            "Gemma cached token count exceeds configured output length: "
            f"{token_count} > {output_length}"
        )
    return token_index_grid.astype(np.int32, copy=False)


def gemma_grouped_mean(
    values: npt.NDArray[np.floating],
    token_index_grid: npt.NDArray[np.integer],
) -> npt.NDArray[np.float32]:
    """Mean-reduce a patch-grid tensor into Gemma cached-token order."""

    if values.shape != token_index_grid.shape:
        raise ValueError(
            f"values/token_index_grid shape mismatch: {values.shape} vs {token_index_grid.shape}"
        )
    flat_idx = np.asarray(token_index_grid, dtype=np.int32).reshape(-1)
    flat_values = np.asarray(values, dtype=np.float32).reshape(-1)
    token_count = int(flat_idx.max()) + 1
    sums = np.bincount(flat_idx, weights=flat_values, minlength=token_count)
    counts = np.bincount(flat_idx, minlength=token_count)
    if np.any(counts == 0):
        raise ValueError("Gemma cached-token grouping produced an empty token bucket")
    return np.asarray(sums / counts, dtype=np.float32)


def gemma_grouped_all(
    mask: npt.NDArray[np.bool_],
    token_index_grid: npt.NDArray[np.integer],
) -> npt.NDArray[np.bool_]:
    """Return True only when every patch assigned to a token is active."""

    if mask.shape != token_index_grid.shape:
        raise ValueError(
            f"mask/token_index_grid shape mismatch: {mask.shape} vs {token_index_grid.shape}"
        )
    flat_idx = np.asarray(token_index_grid, dtype=np.int32).reshape(-1)
    flat_mask = np.asarray(mask, dtype=np.bool_).reshape(-1)
    token_count = int(flat_idx.max()) + 1
    counts = np.bincount(flat_idx, minlength=token_count)
    true_counts = np.bincount(
        flat_idx,
        weights=flat_mask.astype(np.int32),
        minlength=token_count,
    )
    if np.any(counts == 0):
        raise ValueError("Gemma cached-token grouping produced an empty token bucket")
    return np.asarray(true_counts == counts, dtype=np.bool_)


def flattened_reuse_mask(
    classification: npt.NDArray[np.integer],
    *,
    reuse_classes: Iterable[BlockClass],
) -> npt.NDArray[np.bool_]:
    """Flatten a 2D classification grid into a row-major reuse mask."""

    if classification.ndim != 2:
        raise ValueError("classification must be a 2D grid")

    allowed = {int(value) for value in reuse_classes}
    return np.isin(classification, list(allowed)).reshape(-1)


def active_region_block_mask(
    frame_size: tuple[int, int],
    active_box: tuple[int, int, int, int],
    *,
    block_size: int,
) -> npt.NDArray[np.bool_]:
    """Return a row-major mask for blocks fully inside the active image region."""

    width, height = frame_size
    left, top, right, bottom = active_box
    if width <= 0 or height <= 0:
        raise ValueError("frame dimensions must be positive")
    if block_size <= 0:
        raise ValueError("block_size must be positive")
    if width % block_size != 0 or height % block_size != 0:
        raise ValueError("frame dimensions must be multiples of block_size")
    if not (0 <= left <= right <= width and 0 <= top <= bottom <= height):
        raise ValueError("active_box must lie within the frame bounds")

    rows = height // block_size
    cols = width // block_size
    mask = np.zeros((rows, cols), dtype=bool)
    for row in range(rows):
        block_top = row * block_size
        block_bottom = block_top + block_size
        for col in range(cols):
            block_left = col * block_size
            block_right = block_left + block_size
            mask[row, col] = (
                block_left >= left
                and block_right <= right
                and block_top >= top
                and block_bottom <= bottom
            )
    return mask.reshape(-1)
