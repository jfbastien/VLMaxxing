"""Novelty-pruning token selection for phase 1.51 / 1.51R.

Pure-numpy implementations of the five anchor-preservation arms preregistered
in `research/experiments/2026/2026-04-17-phase-1_51-novelty-pruning-gemma-prereg.md`:

- `none` — pure top-K novelty rank (FastV-style baseline).
- `cls_attention` — top-K by CLS-attention (FasterVLM / HiPrune family).
- `nuwa_pillar` — partition the 2D grid into an M×M lattice; hard-preserve
  the top-25 % highest-L2-key-norm tokens per cell, fill rest by novelty
  (Nüwa pillar/collector adaptation).
- `max_min_diversity` — seed with the highest-L1-key-norm token, iteratively
  add the token that maximizes the minimum feature-space distance from all
  prior pivots, until the budget is met (VLM-Pruner family).
- `gemma_structural` — hard-preserve the four 2D-corner tokens and the
  center token per frame (IVC-Prune-spirit structural adaptation).

The module operates on post-pool visual features of shape `(F, T, D)` and
returns a boolean keep mask of shape `(F, T)`. The pruning itself (i.e.,
actually dropping tokens and shortening the LLM prefill) happens in the
harness; this module is the policy, not the plumbing.

Design goals:
- numpy-only so tests run on CPU without MLX (`pytest tests/`).
- Deterministic given the same inputs (`np.random` never used).
- Anchor arms that need attention weights (`cls_attention`) take them as
  an explicit input rather than computing them here — the module is the
  masking math, not the model forward.

The harness supplies `novelty_scores` of shape `(F, T)` computed from the
pixel-diff pipeline already used by `classify_blocks_with_planner`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import numpy.typing as npt

AnchorArm = Literal[
    "none",
    "cls_attention",
    "nuwa_pillar",
    "max_min_diversity",
    "gemma_structural",
]

ANCHOR_ARMS: tuple[AnchorArm, ...] = (
    "none",
    "cls_attention",
    "nuwa_pillar",
    "max_min_diversity",
    "gemma_structural",
)


@dataclass(frozen=True)
class NoveltyPruneConfig:
    """Per-run pruning policy.

    Attributes:
        anchor_arm: one of `ANCHOR_ARMS`. Selects which tokens to hard-preserve
            before the novelty-ranked fill.
        keep_rate: fraction of tokens to retain per frame. 1.0 = no pruning;
            0.0 = all tokens dropped (degenerate). Typical paper grid:
            {0.3, 0.4, 0.5, 0.6, 0.7}.
        grid_side: side length of the 2D post-pool token grid for a frame
            (i.e., tokens are reshaped to `(grid_side, grid_side)` for the
            spatial-aware arms like `nuwa_pillar` and `gemma_structural`).
            For a frame with T tokens on a square grid, `grid_side * grid_side == T`.
            Gemma produces 280 soft tokens per image which is *not* square; for
            Gemma we pass a rectangular `grid_shape` override instead.
        grid_shape: optional `(rows, cols)` override for non-square grids. If
            `None`, `(grid_side, grid_side)` is used.
        nuwa_cell_side: side length of the M×M Nüwa coarse lattice (the
            lattice partitions `grid_shape` into `nuwa_cell_side ** 2` cells).
        nuwa_pillar_frac: fraction of tokens within each Nüwa cell to
            hard-preserve as pillars (typically 0.25).
        structural_corner_count: number of corner-tokens to preserve per frame
            for `gemma_structural` (default 4 corners).
        structural_center_count: number of center tokens per frame (default 1).
    """

    anchor_arm: AnchorArm
    keep_rate: float
    grid_side: int | None = None
    grid_shape: tuple[int, int] | None = None
    nuwa_cell_side: int = 2
    nuwa_pillar_frac: float = 0.25
    structural_corner_count: int = 4
    structural_center_count: int = 1

    def resolved_grid_shape(self, token_count: int) -> tuple[int, int]:
        if self.grid_shape is not None:
            rows, cols = self.grid_shape
            if rows * cols != token_count:
                raise ValueError(
                    f"grid_shape {self.grid_shape} does not multiply to token count {token_count}"
                )
            return rows, cols
        side = self.grid_side
        if side is None:
            side = int(round(np.sqrt(token_count)))
        if side * side != token_count:
            raise ValueError(
                f"token_count {token_count} is not square; pass grid_shape instead"
            )
        return side, side


FloatArray = npt.NDArray[np.floating]
BoolArray = npt.NDArray[np.bool_]


def _keep_top_k(scores: FloatArray, k: int) -> BoolArray:
    """Return a boolean mask selecting the top-k entries of `scores` (highest first).

    Ties are broken by index (lower index wins) for determinism.
    """
    n = scores.size
    if k <= 0:
        return np.zeros(n, dtype=bool)
    if k >= n:
        return np.ones(n, dtype=bool)
    # argpartition gives us indices of the top-k unordered; mask them True.
    top_idx = np.argpartition(-scores, k - 1)[:k]
    mask = np.zeros(n, dtype=bool)
    mask[top_idx] = True
    return mask


def _fill_novelty(
    keep_mask: BoolArray, novelty_scores: FloatArray, target_k: int
) -> BoolArray:
    """Augment `keep_mask` with novelty-ranked tokens until `sum(mask) == target_k`.

    Preserves any True positions in `keep_mask` (anchor-preserved tokens) and
    fills the remaining budget with the highest-novelty un-selected tokens.

    If `target_k` is less than the current anchor count, we keep all anchors
    and warn via a ValueError — the caller should not request a budget below
    the hard-preserved floor.
    """
    current = int(keep_mask.sum())
    if target_k < current:
        raise ValueError(
            f"target budget {target_k} is below the anchor floor {current}; "
            "reduce anchor count or raise keep_rate"
        )
    if target_k == current:
        return keep_mask.copy()
    remaining_budget = target_k - current
    remaining_scores = np.where(keep_mask, -np.inf, novelty_scores)
    extra_mask = _keep_top_k(remaining_scores, remaining_budget)
    return keep_mask | extra_mask


def _arm_gemma_structural_frame_mask(
    config: NoveltyPruneConfig,
    grid_shape: tuple[int, int],
    novelty_scores_frame: FloatArray,
    keep_count: int,
) -> BoolArray:
    rows, cols = grid_shape
    mask = np.zeros(rows * cols, dtype=bool)
    corner_candidates = [
        (0, 0),
        (0, cols - 1),
        (rows - 1, 0),
        (rows - 1, cols - 1),
    ][: config.structural_corner_count]
    for r, c in corner_candidates:
        mask[r * cols + c] = True
    center_r = rows // 2
    center_c = cols // 2
    center_candidates = [
        (center_r, center_c),
    ][: config.structural_center_count]
    for r, c in center_candidates:
        mask[r * cols + c] = True
    return _fill_novelty(mask, novelty_scores_frame, keep_count)


def _arm_nuwa_pillar_frame_mask(
    config: NoveltyPruneConfig,
    grid_shape: tuple[int, int],
    features_frame: FloatArray,
    novelty_scores_frame: FloatArray,
    keep_count: int,
) -> BoolArray:
    rows, cols = grid_shape
    m = config.nuwa_cell_side
    if rows % m != 0 or cols % m != 0:
        raise ValueError(
            f"nuwa_cell_side {m} must divide both grid dims {grid_shape}"
        )
    cell_rows = rows // m
    cell_cols = cols // m
    key_norms = np.linalg.norm(features_frame, axis=1)  # (T,)
    mask = np.zeros(rows * cols, dtype=bool)
    for block_r in range(m):
        for block_c in range(m):
            cell_indices: list[int] = []
            for rr in range(cell_rows):
                for cc in range(cell_cols):
                    gr = block_r * cell_rows + rr
                    gc = block_c * cell_cols + cc
                    cell_indices.append(gr * cols + gc)
            cell_idx = np.asarray(cell_indices, dtype=np.int64)
            cell_norms = key_norms[cell_idx]
            pillar_count = max(1, int(round(len(cell_idx) * config.nuwa_pillar_frac)))
            pillar_order = np.argpartition(-cell_norms, pillar_count - 1)[:pillar_count]
            mask[cell_idx[pillar_order]] = True
    return _fill_novelty(mask, novelty_scores_frame, keep_count)


def _arm_max_min_diversity_frame_mask(
    features_frame: FloatArray,
    keep_count: int,
) -> BoolArray:
    n, _ = features_frame.shape
    if keep_count >= n:
        return np.ones(n, dtype=bool)
    norms_l1 = np.linalg.norm(features_frame, ord=1, axis=1)
    chosen: list[int] = []
    chosen_set: set[int] = set()
    first = int(np.argmax(norms_l1))
    chosen.append(first)
    chosen_set.add(first)
    min_sq_dist = np.full(n, np.inf, dtype=np.float64)
    while len(chosen) < keep_count:
        diff = features_frame - features_frame[chosen[-1]]
        sq_dist = np.sum(diff * diff, axis=1)
        min_sq_dist = np.minimum(min_sq_dist, sq_dist)
        # Don't reselect chosen tokens; mask their distance to -inf for argmax.
        candidate_scores = min_sq_dist.copy()
        for idx in chosen_set:
            candidate_scores[idx] = -np.inf
        next_idx = int(np.argmax(candidate_scores))
        chosen.append(next_idx)
        chosen_set.add(next_idx)
    mask = np.zeros(n, dtype=bool)
    mask[chosen] = True
    return mask


def _arm_cls_attention_frame_mask(
    cls_attention_frame: FloatArray,
    keep_count: int,
) -> BoolArray:
    return _keep_top_k(cls_attention_frame, keep_count)


def compute_keep_mask(
    novelty_scores: FloatArray,
    *,
    config: NoveltyPruneConfig,
    features: FloatArray | None = None,
    cls_attention: FloatArray | None = None,
) -> BoolArray:
    """Build the per-frame boolean keep mask for `novelty_scores` shape `(F, T)`.

    Args:
        novelty_scores: `(F, T)` per-token novelty score, higher = more novel.
            The `none`, `nuwa_pillar`, and `gemma_structural` arms fill budget
            by highest novelty. `max_min_diversity` and `cls_attention` ignore
            novelty when selecting tokens (they fully occupy the budget by
            their own criterion).
        config: pruning policy.
        features: `(F, T, D)` post-pool visual features. Required for
            `nuwa_pillar` (uses L2 key-norm per token) and
            `max_min_diversity` (uses feature-space distance + L1 key-norm).
            Optional otherwise.
        cls_attention: `(F, T)` per-token attention received from a CLS-like
            anchor on the first transformer block. Required for the
            `cls_attention` arm; optional otherwise.

    Returns:
        `(F, T)` boolean mask where True means "keep this token for LLM
        prefill". Counts per frame are floor(keep_rate * T); any residual is
        resolved in favor of the highest-novelty token per frame.
    """
    if novelty_scores.ndim != 2:
        raise ValueError(f"novelty_scores must be 2D (F, T); got {novelty_scores.shape}")
    f_count, t_count = novelty_scores.shape
    if not (0.0 <= config.keep_rate <= 1.0):
        raise ValueError(f"keep_rate {config.keep_rate} must be in [0, 1]")
    keep_count = int(np.floor(config.keep_rate * t_count))
    keep_count = max(1, min(t_count, keep_count))

    grid_shape: tuple[int, int] | None = None
    if config.anchor_arm in ("nuwa_pillar", "gemma_structural"):
        grid_shape = config.resolved_grid_shape(t_count)

    if config.anchor_arm in ("nuwa_pillar", "max_min_diversity") and features is None:
        raise ValueError(f"anchor_arm={config.anchor_arm!r} requires features")
    if config.anchor_arm == "cls_attention" and cls_attention is None:
        raise ValueError("anchor_arm='cls_attention' requires cls_attention input")
    if features is not None and (
        features.ndim != 3 or features.shape[:2] != (f_count, t_count)
    ):
        raise ValueError(
            f"features must have shape (F, T, D) matching novelty; got {features.shape}"
        )
    if cls_attention is not None and cls_attention.shape != (f_count, t_count):
        raise ValueError(
            f"cls_attention must match novelty shape {novelty_scores.shape}; "
            f"got {cls_attention.shape}"
        )

    keep_mask = np.zeros((f_count, t_count), dtype=bool)
    for f in range(f_count):
        frame_novelty = novelty_scores[f]
        if config.anchor_arm == "none":
            keep_mask[f] = _keep_top_k(frame_novelty, keep_count)
        elif config.anchor_arm == "cls_attention":
            assert cls_attention is not None
            keep_mask[f] = _arm_cls_attention_frame_mask(cls_attention[f], keep_count)
        elif config.anchor_arm == "nuwa_pillar":
            assert features is not None and grid_shape is not None
            keep_mask[f] = _arm_nuwa_pillar_frame_mask(
                config,
                grid_shape,
                features[f],
                frame_novelty,
                keep_count,
            )
        elif config.anchor_arm == "max_min_diversity":
            assert features is not None
            keep_mask[f] = _arm_max_min_diversity_frame_mask(features[f], keep_count)
        elif config.anchor_arm == "gemma_structural":
            assert grid_shape is not None
            keep_mask[f] = _arm_gemma_structural_frame_mask(
                config, grid_shape, frame_novelty, keep_count
            )
        else:  # pragma: no cover — exhaustiveness guard
            raise ValueError(f"unknown anchor_arm {config.anchor_arm!r}")
    return keep_mask


def reduce_features(
    features: FloatArray,
    keep_mask: BoolArray,
) -> tuple[FloatArray, npt.NDArray[np.int64]]:
    """Reduce `(F, T, D)` features to `(K, D)` where K = sum(keep_mask).

    Returns the flattened kept features in frame-major / token-major order
    (frame 0 tokens first, then frame 1, ...) and a parallel `(K,)` int64
    array of the original `(frame_index * T + token_index)` positions so the
    caller can reconstruct 2D positional embeddings downstream.
    """
    f_count, t_count, _ = features.shape
    if keep_mask.shape != (f_count, t_count):
        raise ValueError(
            f"keep_mask shape {keep_mask.shape} does not match features {(f_count, t_count)}"
        )
    flat_features = features.reshape(f_count * t_count, -1)
    flat_mask = keep_mask.reshape(f_count * t_count)
    kept_features = flat_features[flat_mask]
    kept_indices = np.nonzero(flat_mask)[0].astype(np.int64)
    return kept_features, kept_indices
