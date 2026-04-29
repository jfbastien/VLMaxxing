"""Novelty-pruning token selection for phase 1.51 / 1.51R.

Pure-numpy implementations of the five anchor-preservation arms preregistered
in `research/experiments/2026/2026-04-17-phase-1_51-novelty-pruning-gemma-prereg.md`:

- `none` — pure top-K novelty rank (FastV-style baseline).
- `cls_attention_proxy` — top-K by a scalar proxy for CLS-attention. The
  callsite supplies the proxy tensor (FasterVLM / HiPrune family: real
  CLS-attention; codec-through v0: per-token L2-norm of post-pool features
  because Gemma vision-tower attention instrumentation has not been landed
  yet). Results from this arm are **not eligible for winner promotion** until
  real attention is wired (see prereg §Phase B caveat). Kept in the grid to
  preserve the literature-baseline column and sanity-check the proxy.
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
- Anchor arms that need per-token attention-like weights
  (`cls_attention_proxy`) take them as an explicit input rather than
  computing them here — the module is the masking math, not the model
  forward.

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
    "cls_attention_proxy",
    "nuwa_pillar",
    "max_min_diversity",
    "gemma_structural",
]

ANCHOR_ARMS: tuple[AnchorArm, ...] = (
    "none",
    "cls_attention_proxy",
    "nuwa_pillar",
    "max_min_diversity",
    "gemma_structural",
)

# Arms whose result is eligible for winner promotion to the 1.51R holdout.
# `cls_attention_proxy` is excluded because its proxy signal (per-token L2
# norm) is not a faithful cls-attention reading on Gemma. Re-include once
# real vision-tower attention instrumentation lands.
PROMOTABLE_ARMS: tuple[AnchorArm, ...] = (
    "none",
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
            raise ValueError(f"token_count {token_count} is not square; pass grid_shape instead")
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
    # Sort by descending score, then ascending index, so documented tie
    # behavior does not depend on argpartition's unspecified tie ordering.
    top_idx = np.lexsort((np.arange(n), -scores))[:k]
    mask = np.zeros(n, dtype=bool)
    mask[top_idx] = True
    return mask


def _fill_novelty(keep_mask: BoolArray, novelty_scores: FloatArray, target_k: int) -> BoolArray:
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
        raise ValueError(f"nuwa_cell_side {m} must divide both grid dims {grid_shape}")
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


def _arm_cls_attention_proxy_frame_mask(
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
            by highest novelty. `max_min_diversity` and `cls_attention_proxy`
            ignore novelty when selecting tokens (they fully occupy the
            budget by their own criterion).
        config: pruning policy.
        features: `(F, T, D)` post-pool visual features. Required for
            `nuwa_pillar` (uses L2 key-norm per token) and
            `max_min_diversity` (uses feature-space distance + L1 key-norm).
            Optional otherwise.
        cls_attention: `(F, T)` per-token scalar used as a cls-attention
            proxy (v0: callsite passes per-token feature L2-norm). Required
            for the `cls_attention_proxy` arm; optional otherwise. When real
            Gemma vision-tower attention instrumentation lands, this will
            become the genuine first-layer attention-received-from-CLS
            signal and the arm will become promotable.

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
    if config.anchor_arm == "cls_attention_proxy" and cls_attention is None:
        raise ValueError("anchor_arm='cls_attention_proxy' requires cls_attention input")
    if features is not None and (features.ndim != 3 or features.shape[:2] != (f_count, t_count)):
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
        elif config.anchor_arm == "cls_attention_proxy":
            assert cls_attention is not None
            keep_mask[f] = _arm_cls_attention_proxy_frame_mask(cls_attention[f], keep_count)
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


def _diff_plane(frame_a: FloatArray, frame_b: FloatArray) -> FloatArray:
    """Mean absolute channel-wise error between two frames (H, W) or (H, W, C)."""
    if frame_a.shape != frame_b.shape:
        raise ValueError(
            f"frame shapes must match exactly, got {frame_a.shape} and {frame_b.shape}"
        )
    if frame_a.ndim not in (2, 3):
        raise ValueError("expected 2D grayscale or 3D color frames")
    diff = np.abs(frame_a.astype(np.float32) - frame_b.astype(np.float32))
    if diff.ndim == 3:
        return np.asarray(diff.mean(axis=2), dtype=np.float32)
    return np.asarray(diff, dtype=np.float32)


def _aggregate_to_grid(per_pixel: FloatArray, grid_shape: tuple[int, int]) -> FloatArray:
    """Block-mean-pool a 2D per-pixel array into `grid_shape` cells.

    Requires the pixel dimensions to be exact multiples of the grid dims. For
    the current Gemma MLX path the validated case is 560×560 pixel frames with
    a 16×16 soft-token grid (256 tokens/frame); older 14×20 / 280-token notes
    in prereg drafts came from a stale metadata attribute and are incorrect for
    the driver path we actually run.
    """
    rows, cols = grid_shape
    h, w = per_pixel.shape
    if h % rows != 0 or w % cols != 0:
        raise ValueError(f"frame dims {(h, w)} must be divisible by grid_shape {(rows, cols)}")
    cell_h = h // rows
    cell_w = w // cols
    reshaped = per_pixel.reshape(rows, cell_h, cols, cell_w)
    return np.asarray(reshaped.mean(axis=(1, 3)), dtype=np.float32)


FirstFrameMode = Literal["mirror", "zero", "max"]


def compute_pixel_novelty(
    frames: FloatArray,
    *,
    grid_shape: tuple[int, int],
    first_frame: FirstFrameMode = "mirror",
) -> FloatArray:
    """Compute per-(frame, token) novelty via pixel-difference aggregation.

    Args:
        frames: `(F, H, W)` or `(F, H, W, C)` pixel array. Channels are averaged
            the same way `codec_through.temporal._diff_plane` averages them, so
            thresholds calibrated against that function transfer here.
        grid_shape: `(rows, cols)` of the target post-pool token grid. H and W
            must be exact multiples of `rows` and `cols` respectively.
        first_frame: how to populate novelty for frame 0 (which has no
            predecessor). `"mirror"` uses the diff against frame 1 (symmetric);
            `"zero"` emits zero novelty (the arm's fallbacks then pick tokens
            by position only); `"max"` emits per-token max of frames 1..F-1
            novelties (treats frame 0 as maximally novel per position).

    Returns:
        `(F, rows * cols)` float32 novelty, higher = more pixel-level change.
    """
    if frames.ndim not in (3, 4):
        raise ValueError(f"frames must be (F, H, W) or (F, H, W, C); got shape {frames.shape}")
    f_count = frames.shape[0]
    if f_count == 0:
        return np.zeros((0, grid_shape[0] * grid_shape[1]), dtype=np.float32)
    rows, cols = grid_shape
    t_count = rows * cols
    novelty = np.zeros((f_count, t_count), dtype=np.float32)
    if f_count == 1:
        # Degenerate single-frame case: no diff available, leave zeros.
        return novelty
    for f in range(1, f_count):
        per_pixel = _diff_plane(frames[f], frames[f - 1])
        novelty[f] = _aggregate_to_grid(per_pixel, grid_shape).reshape(t_count)
    if first_frame == "mirror":
        novelty[0] = novelty[1]
    elif first_frame == "zero":
        pass  # leave zeros
    elif first_frame == "max":
        novelty[0] = novelty[1:].max(axis=0)
    else:  # pragma: no cover — exhaustiveness guard
        raise ValueError(f"unknown first_frame mode {first_frame!r}")
    return novelty


IntArray = npt.NDArray[np.integer]


@dataclass(frozen=True, slots=True)
class PrunedPrefill:
    """Result of :func:`prune_image_placeholders`.

    Attributes:
        input_ids: shortened input ids, shape ``(new_seq_len,)`` with the
            caller's original dtype preserved.
        feature_indices: flat int64 indices into the ORIGINAL ``(F, T)``
            visual-feature matrix that survive pruning, in the emission order
            required by the LLM prefill (frame-major, intra-frame
            left-to-right). Length equals the number of image-token
            placeholders in ``input_ids``.
        kept_per_frame: int64 count of tokens retained per frame, length ``F``.
    """

    input_ids: IntArray
    feature_indices: npt.NDArray[np.int64]
    kept_per_frame: npt.NDArray[np.int64]


def prune_image_placeholders(
    input_ids: IntArray,
    keep_mask: BoolArray,
    *,
    image_token_id: int,
) -> PrunedPrefill:
    """Shorten ``input_ids`` by removing image-token placeholders that
    correspond to pruned-away visual tokens.

    The LLM prefill path (Gemma 4, Qwen 2.5-VL, etc.) splices visual features
    into positions where ``input_ids == image_token_id``. The splice is
    positional and count-sensitive: ``sum(input_ids == image_token_id)`` MUST
    equal the number of visual feature tokens. When novelty-pruning drops
    ``(F*T) - sum(keep_mask)`` visual tokens, we must drop the same number of
    placeholder tokens from ``input_ids`` to keep the counts aligned.

    This function walks ``input_ids`` once, keeping every non-image token and
    every image-token whose corresponding ``keep_mask[f, t]`` is True. The
    placeholder-to-feature binding assumes the processor emits all ``T``
    placeholders for frame 0, then all ``T`` for frame 1, etc. (the standard
    mlx-vlm layout — ``Gemma4Processor`` and ``Qwen2.5-VL``'s chat-template
    both emit placeholders in frame-major order).

    Args:
        input_ids: original token IDs, shape ``(seq_len,)``. Must contain
            exactly ``F * T`` occurrences of ``image_token_id``.
        keep_mask: boolean mask ``(F, T)`` from :func:`compute_keep_mask`
            indicating which visual tokens survive pruning.
        image_token_id: the token ID used as a visual placeholder (model-
            specific; e.g., Gemma 4's ``image_token_id`` from its config).

    Returns:
        :class:`PrunedPrefill` with the shortened ``input_ids`` and the flat
        feature indices that should be scattered into the placeholder slots.
        The caller uses ``feature_indices`` to gather a ``(K, D)`` feature
        tensor from the ``(F*T, D)`` vision-tower output before calling
        ``masked_scatter``.

    Raises:
        ValueError: if ``keep_mask.sum()`` doesn't match the placeholder count,
            if ``input_ids`` is not 1-D, or if ``keep_mask`` is not 2-D.
    """
    if input_ids.ndim != 1:
        raise ValueError(f"input_ids must be 1-D, got shape {input_ids.shape}")
    if keep_mask.ndim != 2:
        raise ValueError(f"keep_mask must be 2-D (F, T), got shape {keep_mask.shape}")
    f_count, t_count = keep_mask.shape
    expected_placeholders = f_count * t_count
    actual_placeholders = int((input_ids == image_token_id).sum())
    if actual_placeholders != expected_placeholders:
        raise ValueError(
            f"input_ids has {actual_placeholders} image-token placeholders but "
            f"keep_mask covers {expected_placeholders} (F={f_count} * T={t_count})"
        )

    flat_keep = keep_mask.reshape(-1).astype(bool)
    feature_indices = np.nonzero(flat_keep)[0].astype(np.int64)
    kept_per_frame = keep_mask.sum(axis=1).astype(np.int64)

    # Walk input_ids once, emitting non-image tokens unconditionally and image
    # tokens only when the corresponding keep_mask entry is True. Track runs
    # of consecutive image tokens so we can validate the per-frame grid
    # layout — the flat placeholder_cursor indexing into keep_mask.reshape(-1)
    # is correct only if the processor emits exactly t_count placeholders per
    # frame, frame-major. A total-count match (checked above) is necessary but
    # not sufficient; a processor variant emitting T-1 placeholders for one
    # frame and T+1 for another would pass the total check yet mis-bind the
    # kept features to the wrong frame.
    kept_tokens: list[np.int64] = []
    placeholder_cursor = 0
    run_length = 0
    run_count = 0
    for tid in input_ids:
        if tid == image_token_id:
            if flat_keep[placeholder_cursor]:
                kept_tokens.append(tid)
            placeholder_cursor += 1
            run_length += 1
        else:
            if run_length > 0:
                if run_length != t_count:
                    raise ValueError(
                        f"image-token run {run_count} has length {run_length},"
                        f" expected {t_count} (keep_mask second dim)"
                    )
                run_count += 1
                run_length = 0
            kept_tokens.append(tid)
    # Flush a trailing run if input_ids ends with image tokens (unusual but
    # technically possible on some chat templates).
    if run_length > 0:
        if run_length != t_count:
            raise ValueError(
                f"image-token run {run_count} has length {run_length},"
                f" expected {t_count} (keep_mask second dim)"
            )
        run_count += 1
    if run_count != f_count:
        raise ValueError(
            f"input_ids contains {run_count} image-token runs,"
            f" expected {f_count} (keep_mask first dim)"
        )
    new_input_ids = np.asarray(kept_tokens, dtype=input_ids.dtype)
    return PrunedPrefill(
        input_ids=new_input_ids,
        feature_indices=feature_indices,
        kept_per_frame=kept_per_frame,
    )
