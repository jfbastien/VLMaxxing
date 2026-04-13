"""Helpers for local Track A experiment bring-up."""

from __future__ import annotations

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

    if spatial_merge_size <= 0:
        raise ValueError("spatial_merge_size must be positive")
    if image_grid_thw.ndim != 2 or image_grid_thw.shape[1] != 3:
        raise ValueError("image_grid_thw must be shaped [num_images, 3]")

    divisor = spatial_merge_size**2
    counts: list[int] = []
    for row in image_grid_thw:
        temporal, height, width = (int(value) for value in row)
        merged = temporal * height * width
        if merged % divisor != 0:
            raise ValueError(
                "image grid product must be divisible by spatial_merge_size**2, "
                f"got row={tuple(int(value) for value in row)}"
            )
        counts.append(merged // divisor)
    return counts


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
