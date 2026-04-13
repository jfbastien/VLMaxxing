"""JPEG Q-table helpers adapted from the predecessor repo's strongest spatial pre-filter."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import numpy.typing as npt
from PIL import Image

try:
    import jpegio  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - optional dependency
    jpegio = None


FLAT = 0
CANDIDATE = 1
COMPLEX = 2

FLAT_THRESHOLD = 3
COMPLEX_THRESHOLD = 20


def extract_block_complexity(jpeg_path: str) -> dict[str, Any] | None:
    """Return per-8x8 surviving-AC counts from a JPEG, or ``None`` on fallback."""

    if jpegio is None:
        return None

    try:
        jpeg = jpegio.read(jpeg_path)
    except Exception:
        return None

    dct = jpeg.coef_arrays[0]
    qtable = jpeg.quant_tables[0]
    height_blocks = dct.shape[0] // 8
    width_blocks = dct.shape[1] // 8

    blocks = dct[: height_blocks * 8, : width_blocks * 8].reshape(height_blocks, 8, width_blocks, 8)
    blocks = blocks.transpose(0, 2, 1, 3)

    ac = blocks.copy()
    ac[:, :, 0, 0] = 0
    surviving = np.count_nonzero(ac.reshape(height_blocks, width_blocks, 64), axis=2)

    return {
        "surviving": surviving,
        "qtable": qtable,
        "qtable_range": float(qtable.max() - qtable.min()),
        "h_blocks": height_blocks,
        "w_blocks": width_blocks,
    }


def aggregate_to_token_grid(
    block_scores: npt.NDArray[np.integer[Any] | np.floating[Any]],
    *,
    token_h: int,
    token_w: int,
    patch_px: int = 28,
) -> npt.NDArray[np.float64]:
    """Map 8x8 JPEG-block scores onto a token grid with area-weighted overlap."""

    if token_h <= 0 or token_w <= 0:
        raise ValueError("token grid dimensions must be positive")
    if patch_px <= 0:
        raise ValueError("patch_px must be positive")

    block_h, block_w = block_scores.shape
    blocks_per_token = patch_px / 8.0
    token_scores = np.zeros((token_h, token_w), dtype=np.float64)

    for token_row in range(token_h):
        for token_col in range(token_w):
            row_start = token_row * blocks_per_token
            row_end = min((token_row + 1) * blocks_per_token, block_h)
            col_start = token_col * blocks_per_token
            col_end = min((token_col + 1) * blocks_per_token, block_w)

            total_weight = 0.0
            weighted_sum = 0.0

            for block_row in range(int(row_start), min(math.ceil(row_end), block_h)):
                for block_col in range(int(col_start), min(math.ceil(col_end), block_w)):
                    row_overlap = min(row_end, block_row + 1) - max(row_start, block_row)
                    col_overlap = min(col_end, block_col + 1) - max(col_start, block_col)
                    weight = max(0.0, row_overlap) * max(0.0, col_overlap)
                    weighted_sum += float(block_scores[block_row, block_col]) * weight
                    total_weight += weight

            if total_weight > 0:
                token_scores[token_row, token_col] = weighted_sum / total_weight

    return token_scores


def classify_tokens(
    jpeg_path: str,
    *,
    token_h: int,
    token_w: int,
    patch_px: int = 28,
) -> tuple[npt.NDArray[np.int32], float] | None:
    """Return token classes and an image-level complexity index, or ``None`` on fallback."""

    try:
        with Image.open(jpeg_path) as image:
            if image.format != "JPEG":
                return None
    except Exception:
        return None

    block_data = extract_block_complexity(jpeg_path)
    if block_data is None or block_data["qtable_range"] < 3:
        return None

    token_scores = aggregate_to_token_grid(
        block_data["surviving"],
        token_h=token_h,
        token_w=token_w,
        patch_px=patch_px,
    )

    classification = np.full((token_h, token_w), CANDIDATE, dtype=np.int32)
    classification[token_scores <= FLAT_THRESHOLD] = FLAT
    classification[token_scores > COMPLEX_THRESHOLD] = COMPLEX

    flat_fraction = float((classification == FLAT).sum() / classification.size)
    complexity_index = 1.0 - flat_fraction
    return classification, complexity_index
