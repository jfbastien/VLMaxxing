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
