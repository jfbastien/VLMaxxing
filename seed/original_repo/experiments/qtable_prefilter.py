"""Q-table pre-filter: extract JPEG quantization metadata for spatial token merge.

Reuses extract_dct_stats() from exp_b_qtable_correlation.py.
Maps 8x8 JPEG blocks to ViT token grid with area-weighted averaging.
Classifies tokens as FLAT/CANDIDATE/COMPLEX.

Usage:
    from qtable_prefilter import classify_tokens, FLAT, CANDIDATE, COMPLEX
    result = classify_tokens("image.jpg", token_h=20, token_w=20)
    if result is not None:
        classification, complexity_index = result
"""

import math

import numpy as np
from PIL import Image

try:
    import jpegio
    HAS_JPEGIO = True
except ImportError:
    HAS_JPEGIO = False

# Thresholds from exp_b empirical validation (ρ=0.932 at these boundaries)
FLAT_THRESHOLD = 3       # ≤3 surviving AC coefficients → FLAT
COMPLEX_THRESHOLD = 20   # >20 surviving AC coefficients → COMPLEX

FLAT = 0
CANDIDATE = 1
COMPLEX = 2


def extract_block_complexity(jpeg_path: str) -> dict | None:
    """Extract per-8x8-block surviving AC coefficient count from JPEG.

    Returns None if not JPEG or extraction fails (triggers fallback).
    """
    if not HAS_JPEGIO:
        return None

    try:
        jpg = jpegio.read(str(jpeg_path))
    except Exception:
        return None

    dct = jpg.coef_arrays[0]  # Y-channel
    qtable = jpg.quant_tables[0]

    h_blocks = dct.shape[0] // 8
    w_blocks = dct.shape[1] // 8

    blocks = dct[:h_blocks * 8, :w_blocks * 8].reshape(h_blocks, 8, w_blocks, 8)
    blocks = blocks.transpose(0, 2, 1, 3)  # (h_blocks, w_blocks, 8, 8)

    # Count non-zero AC coefficients per block (exclude DC at [0,0])
    ac = blocks.copy()
    ac[:, :, 0, 0] = 0
    surviving = np.count_nonzero(ac.reshape(h_blocks, w_blocks, 64), axis=2)

    # Q-table signal strength check
    qtable_range = float(qtable.max() - qtable.min())

    return {
        "surviving": surviving,  # (h_blocks, w_blocks)
        "qtable": qtable,
        "qtable_range": qtable_range,
        "h_blocks": h_blocks,
        "w_blocks": w_blocks,
    }


def aggregate_to_token_grid(
    block_scores: np.ndarray,
    token_h: int,
    token_w: int,
    patch_px: int = 28,
) -> np.ndarray:
    """Aggregate 8x8 block scores to ViT token grid with area-weighted averaging.

    For Qwen2.5-VL (28px tokens): 3.5 blocks per token → fractional overlap.
    For 16px patch models (Gemma 4, LLaVA): 2.0 blocks per token → exact.
    """
    bh, bw = block_scores.shape
    blocks_per_token = patch_px / 8.0  # 3.5 for 28px, 2.0 for 16px

    token_scores = np.zeros((token_h, token_w), dtype=np.float64)

    for tr in range(token_h):
        for tc in range(token_w):
            r_start = tr * blocks_per_token
            r_end = min((tr + 1) * blocks_per_token, bh)
            c_start = tc * blocks_per_token
            c_end = min((tc + 1) * blocks_per_token, bw)

            total_weight = 0.0
            weighted_sum = 0.0

            for br in range(int(r_start), min(math.ceil(r_end), bh)):
                for bc in range(int(c_start), min(math.ceil(c_end), bw)):
                    r_overlap = min(r_end, br + 1) - max(r_start, br)
                    c_overlap = min(c_end, bc + 1) - max(c_start, bc)
                    weight = max(0.0, r_overlap) * max(0.0, c_overlap)

                    weighted_sum += block_scores[br, bc] * weight
                    total_weight += weight

            if total_weight > 0:
                token_scores[tr, tc] = weighted_sum / total_weight

    return token_scores


def classify_tokens(
    jpeg_path: str,
    token_h: int,
    token_w: int,
    patch_px: int = 28,
) -> tuple[np.ndarray, float] | None:
    """Classify ViT tokens as FLAT/CANDIDATE/COMPLEX from JPEG Q-table.

    Returns (classification_grid, complexity_index) or None for non-JPEG fallback.
      classification_grid: (token_h, token_w) with FLAT=0, CANDIDATE=1, COMPLEX=2
      complexity_index: 0.0 (all flat) to 1.0 (all complex) for adaptive ratio
    """
    # Check if JPEG
    try:
        img = Image.open(jpeg_path)
        if img.format != "JPEG":
            return None
    except Exception:
        return None

    block_data = extract_block_complexity(jpeg_path)
    if block_data is None:
        return None

    # Weak Q-table signal → fallback
    if block_data["qtable_range"] < 3:
        return None

    # Aggregate to token grid
    token_scores = aggregate_to_token_grid(
        block_data["surviving"], token_h, token_w, patch_px
    )

    # Classify
    classification = np.full((token_h, token_w), CANDIDATE, dtype=np.int32)
    classification[token_scores <= FLAT_THRESHOLD] = FLAT
    classification[token_scores > COMPLEX_THRESHOLD] = COMPLEX

    # Image-level complexity index
    total = token_h * token_w
    flat_pct = (classification == FLAT).sum() / total
    complexity_index = 1.0 - flat_pct  # 0=all flat, 1=no flat tokens

    return classification, complexity_index
