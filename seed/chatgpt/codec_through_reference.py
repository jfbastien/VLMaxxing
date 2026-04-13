
"""
Codec-Through reference implementation.

This module implements a practical planning layer for training-free temporal
embedding reuse in video vision-language models (VLMs). It supports:

1. Pixel-difference planning:
   - classify each visual token as STATIC / SHIFTED / NOVEL
   - optional local-search matching for small motion
   - optional global translation compensation
   - protected regions for task-critical areas (e.g., robot gripper / object)

2. Codec-metadata planning:
   - map H.264 / HEVC-style macroblock metadata into token labels
   - use motion vectors and residual energy instead of decoding full RGB

3. Execution helpers:
   - dense validation wrapper: useful to validate output quality by splicing
     cached embeddings after a full vision-encoder pass
   - sparse window executor: the path that can actually reduce compute when
     a model/backend supports partial window recomputation

Important note
--------------
Replacing final token embeddings *after* running a standard dense ViT does
not eliminate most encoder FLOPs. That path is still useful as a correctness
/ quality ablation, but real speedups require model-specific sparse execution
(for example window-level recomputation or codec-guided pruning before the
vision encoder).

The code below is deliberately model-agnostic. It is a reference design that
can be adapted to Qwen2.5-VL, LLaVA-family models, Gemma 4, or robotics VLAs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Iterable, List, Optional, Protocol, Sequence, Tuple, Union

import math
import numpy as np

try:
    import torch
    import torch.nn as nn
except Exception:  # pragma: no cover - torch is optional for planning-only usage
    torch = None
    nn = object  # type: ignore[misc,assignment]


ArrayLike = Union[np.ndarray, "torch.Tensor"]


class TokenClass(IntEnum):
    STATIC = 0
    SHIFTED = 1
    NOVEL = 2


@dataclass(frozen=True)
class ProtectRegion:
    """
    Rectangle in pixel coordinates. By default, anything inside is forced to NOVEL
    so it will always be recomputed.
    """

    x0: int
    y0: int
    x1: int
    y1: int
    force_label: TokenClass = TokenClass.NOVEL


@dataclass(frozen=True)
class CodecMacroblock:
    """
    Generic codec-side block metadata.

    Parameters
    ----------
    x, y, w, h:
        Block rectangle in pixel coordinates.
    mv_x, mv_y:
        Motion-vector displacement in pixels. Zero motion with zero residual
        indicates a perfect copy in most predictive codecs.
    residual_energy:
        Any proxy for "new information" in the block. This can be coded block
        flag (CBF), residual norm, non-zero coefficient count, or similar.
    intra:
        True if the block is intra-coded or otherwise must be treated as NOVEL.
    """

    x: int
    y: int
    w: int
    h: int
    mv_x: float = 0.0
    mv_y: float = 0.0
    residual_energy: float = 0.0
    intra: bool = False


@dataclass
class PlannerConfig:
    """
    Hyperparameters for planning token reuse.

    All thresholds assume normalized pixel values in [0, 1]. If your frames are
    uint8, convert to float and divide by 255 first.
    """

    patch_size: int = 16
    static_threshold: float = 0.015
    shifted_threshold: float = 0.040
    search_radius_px: int = 4
    estimate_global_translation: bool = False
    global_shift_max_px: int = 8
    halo_radius_tokens: int = 1
    window_size_tokens: int = 2
    refresh_every: int = 30
    drift_threshold: float = 0.08
    min_reuse_ratio: float = 0.20
    codec_mv_static_epsilon: float = 0.0
    codec_residual_threshold: float = 0.0
    protect_regions: List[ProtectRegion] = field(default_factory=list)


@dataclass
class ReusePlan:
    """
    Output of the temporal redundancy planner.
    """

    labels: np.ndarray  # [grid_h, grid_w] TokenClass
    same_position_diff: np.ndarray  # [grid_h, grid_w]
    best_diff: np.ndarray  # [grid_h, grid_w]
    best_shift: np.ndarray  # [grid_h, grid_w, 2] in pixels (dy, dx)
    reuse_mask: np.ndarray  # True for STATIC or SHIFTED
    novel_mask: np.ndarray  # True for NOVEL
    recompute_token_mask: np.ndarray  # novel + halo-expanded token mask
    recompute_window_mask: np.ndarray  # grouped into execution windows
    global_shift: Tuple[int, int] = (0, 0)
    refresh: bool = False
    reason: str = ""
    protected_mask: Optional[np.ndarray] = None

    @property
    def grid_shape(self) -> Tuple[int, int]:
        return int(self.labels.shape[0]), int(self.labels.shape[1])

    @property
    def reuse_ratio(self) -> float:
        return float(self.reuse_mask.mean())

    @property
    def novel_ratio(self) -> float:
        return float(self.novel_mask.mean())

    @property
    def static_ratio(self) -> float:
        return float((self.labels == TokenClass.STATIC).mean())

    @property
    def shifted_ratio(self) -> float:
        return float((self.labels == TokenClass.SHIFTED).mean())

    def summary(self) -> dict:
        return {
            "static_pct": 100.0 * self.static_ratio,
            "shifted_pct": 100.0 * self.shifted_ratio,
            "novel_pct": 100.0 * self.novel_ratio,
            "reuse_pct": 100.0 * self.reuse_ratio,
            "refresh": bool(self.refresh),
            "refresh_reason": self.reason,
            "global_shift": tuple(int(x) for x in self.global_shift),
        }


class TemporalRedundancyPlanner:
    """
    Planner for Codec-Through style temporal embedding reuse.
    """

    def __init__(self, config: Optional[PlannerConfig] = None) -> None:
        self.config = config or PlannerConfig()

    # ---------------------------------------------------------------------
    # Public entry points
    # ---------------------------------------------------------------------

    def plan_from_frames(
        self,
        prev_frame: np.ndarray,
        curr_frame: np.ndarray,
        *,
        protect_regions: Optional[Sequence[ProtectRegion]] = None,
        frames_since_refresh: int = 0,
        use_local_search: bool = True,
    ) -> ReusePlan:
        """
        Build a reuse plan from raw frames.

        Parameters
        ----------
        prev_frame, curr_frame:
            H x W x C float arrays in [0, 1].
        protect_regions:
            Task-critical ROIs to force-refresh.
        frames_since_refresh:
            Age of the current cache reference.
        use_local_search:
            Whether to search small local shifts before declaring NOVEL.
        """

        prev = self._normalize_frame(prev_frame)
        curr = self._normalize_frame(curr_frame)
        self._validate_frame_pair(prev, curr)

        global_shift = (0, 0)
        shifted_prev = prev
        if self.config.estimate_global_translation:
            global_shift, _ = self.estimate_global_translation(
                prev, curr, max_shift=self.config.global_shift_max_px
            )
            shifted_prev = self.shift_frame(prev, *global_shift)

        labels, same_diff, best_diff, best_shift = self._classify_pixel_diff(
            shifted_prev,
            curr,
            use_local_search=use_local_search,
        )

        protected_mask = None
        merged_regions = list(self.config.protect_regions)
        if protect_regions:
            merged_regions.extend(protect_regions)
        if merged_regions:
            labels, protected_mask = self.apply_protect_regions(labels, merged_regions)

        plan = self._finalize_plan(
            labels=labels,
            same_position_diff=same_diff,
            best_diff=best_diff,
            best_shift=best_shift,
            global_shift=global_shift,
            protected_mask=protected_mask,
        )
        refresh, reason = self.should_refresh(plan, frames_since_refresh)
        plan.refresh = refresh
        plan.reason = reason
        return plan

    def plan_from_codec_metadata(
        self,
        *,
        frame_shape: Tuple[int, int],
        blocks: Sequence[CodecMacroblock],
        protect_regions: Optional[Sequence[ProtectRegion]] = None,
        frames_since_refresh: int = 0,
    ) -> ReusePlan:
        """
        Build a reuse plan directly from codec-side metadata.

        The conservative policy is:
          intra-coded OR residual_energy > threshold -> NOVEL
          residual-free and zero-motion              -> STATIC
          residual-free and nonzero motion           -> SHIFTED
        """

        height, width = int(frame_shape[0]), int(frame_shape[1])
        patch = self.config.patch_size
        if height % patch != 0 or width % patch != 0:
            raise ValueError(
                f"Frame shape {(height, width)} is not divisible by patch_size={patch}."
            )

        grid_h, grid_w = height // patch, width // patch
        labels = np.full((grid_h, grid_w), TokenClass.NOVEL, dtype=np.int8)
        same_diff = np.full((grid_h, grid_w), np.nan, dtype=np.float32)
        best_diff = np.full((grid_h, grid_w), np.nan, dtype=np.float32)
        best_shift = np.zeros((grid_h, grid_w, 2), dtype=np.int32)

        # Start from STATIC and elevate conservatively.
        labels.fill(int(TokenClass.STATIC))

        for block in blocks:
            block_label = self._classify_codec_block(block)
            y0 = max(0, block.y) // patch
            y1 = min(height, block.y + block.h + patch - 1) // patch
            x0 = max(0, block.x) // patch
            x1 = min(width, block.x + block.w + patch - 1) // patch
            y1 = min(y1, grid_h)
            x1 = min(x1, grid_w)
            labels[y0:y1, x0:x1] = np.maximum(labels[y0:y1, x0:x1], int(block_label))
            best_shift[y0:y1, x0:x1, 0] = int(round(block.mv_y))
            best_shift[y0:y1, x0:x1, 1] = int(round(block.mv_x))

        protected_mask = None
        merged_regions = list(self.config.protect_regions)
        if protect_regions:
            merged_regions.extend(protect_regions)
        if merged_regions:
            labels, protected_mask = self.apply_protect_regions(labels, merged_regions)

        plan = self._finalize_plan(
            labels=labels,
            same_position_diff=same_diff,
            best_diff=best_diff,
            best_shift=best_shift,
            global_shift=(0, 0),
            protected_mask=protected_mask,
        )
        refresh, reason = self.should_refresh(plan, frames_since_refresh)
        plan.refresh = refresh
        plan.reason = reason
        return plan

    # ---------------------------------------------------------------------
    # Core planning logic
    # ---------------------------------------------------------------------

    def _classify_pixel_diff(
        self,
        prev_frame: np.ndarray,
        curr_frame: np.ndarray,
        *,
        use_local_search: bool,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        patch = self.config.patch_size
        static_thr = self.config.static_threshold
        shifted_thr = self.config.shifted_threshold
        radius = self.config.search_radius_px if use_local_search else 0

        grid_h, grid_w = curr_frame.shape[0] // patch, curr_frame.shape[1] // patch
        prev_tokens = self._tokenize(prev_frame, patch)
        curr_tokens = self._tokenize(curr_frame, patch)

        labels = np.full((grid_h, grid_w), int(TokenClass.NOVEL), dtype=np.int8)
        same_diff = np.zeros((grid_h, grid_w), dtype=np.float32)
        best_diff = np.full((grid_h, grid_w), np.inf, dtype=np.float32)
        best_shift = np.zeros((grid_h, grid_w, 2), dtype=np.int32)

        for gy in range(grid_h):
            for gx in range(grid_w):
                current_patch = curr_tokens[gy, gx]
                diff0 = self.patch_l1_distance(current_patch, prev_tokens[gy, gx])
                same_diff[gy, gx] = diff0
                best = diff0
                best_shift_px = (0, 0)

                if diff0 < static_thr:
                    labels[gy, gx] = int(TokenClass.STATIC)
                    best_diff[gy, gx] = diff0
                    continue

                if radius > 0:
                    y0 = gy * patch
                    x0 = gx * patch
                    for dy in range(-radius, radius + 1):
                        for dx in range(-radius, radius + 1):
                            yy0 = y0 + dy
                            xx0 = x0 + dx
                            yy1 = yy0 + patch
                            xx1 = xx0 + patch
                            if yy0 < 0 or xx0 < 0 or yy1 > prev_frame.shape[0] or xx1 > prev_frame.shape[1]:
                                continue
                            candidate = prev_frame[yy0:yy1, xx0:xx1]
                            score = self.patch_l1_distance(current_patch, candidate)
                            if score < best:
                                best = score
                                best_shift_px = (dy, dx)

                best_diff[gy, gx] = best
                best_shift[gy, gx] = best_shift_px

                if best < shifted_thr:
                    labels[gy, gx] = (
                        int(TokenClass.SHIFTED) if best_shift_px != (0, 0) else int(TokenClass.STATIC)
                    )
                else:
                    labels[gy, gx] = int(TokenClass.NOVEL)

        return labels, same_diff, best_diff, best_shift

    def _classify_codec_block(self, block: CodecMacroblock) -> TokenClass:
        if block.intra or block.residual_energy > self.config.codec_residual_threshold:
            return TokenClass.NOVEL
        if (
            abs(block.mv_x) <= self.config.codec_mv_static_epsilon
            and abs(block.mv_y) <= self.config.codec_mv_static_epsilon
        ):
            return TokenClass.STATIC
        return TokenClass.SHIFTED

    def _finalize_plan(
        self,
        *,
        labels: np.ndarray,
        same_position_diff: np.ndarray,
        best_diff: np.ndarray,
        best_shift: np.ndarray,
        global_shift: Tuple[int, int],
        protected_mask: Optional[np.ndarray],
    ) -> ReusePlan:
        labels = labels.astype(np.int8, copy=False)
        novel_mask = labels == int(TokenClass.NOVEL)
        reuse_mask = ~novel_mask
        recompute_token_mask = self.dilate_mask(novel_mask, radius=self.config.halo_radius_tokens)
        recompute_window_mask = self.token_mask_to_window_mask(
            recompute_token_mask,
            window_size=self.config.window_size_tokens,
        )
        return ReusePlan(
            labels=labels,
            same_position_diff=same_position_diff,
            best_diff=best_diff,
            best_shift=best_shift,
            reuse_mask=reuse_mask,
            novel_mask=novel_mask,
            recompute_token_mask=recompute_token_mask,
            recompute_window_mask=recompute_window_mask,
            global_shift=global_shift,
            protected_mask=protected_mask,
        )

    def should_refresh(self, plan: ReusePlan, frames_since_refresh: int) -> Tuple[bool, str]:
        """
        Conservative heuristic. Replace with a learned gate if you have the data.
        """

        if frames_since_refresh >= self.config.refresh_every:
            return True, f"periodic refresh at age {frames_since_refresh}"
        if plan.reuse_ratio < self.config.min_reuse_ratio:
            return True, f"reuse ratio too low ({plan.reuse_ratio:.3f})"
        reused_scores = plan.best_diff[plan.reuse_mask]
        if reused_scores.size > 0:
            drift_proxy = float(np.nanmean(reused_scores))
            if drift_proxy > self.config.drift_threshold:
                return True, f"drift proxy too high ({drift_proxy:.4f})"
        return False, ""

    # ---------------------------------------------------------------------
    # Utilities
    # ---------------------------------------------------------------------

    @staticmethod
    def _normalize_frame(frame: np.ndarray) -> np.ndarray:
        arr = np.asarray(frame)
        if arr.ndim == 2:
            arr = arr[..., None]
        if arr.dtype == np.uint8:
            arr = arr.astype(np.float32) / 255.0
        else:
            arr = arr.astype(np.float32, copy=False)
            if arr.max() > 1.0 or arr.min() < 0.0:
                # Best effort normalization for common 0..255 float input.
                arr = np.clip(arr / 255.0 if arr.max() > 2.0 else arr, 0.0, 1.0)
        return arr

    def _validate_frame_pair(self, prev: np.ndarray, curr: np.ndarray) -> None:
        if prev.shape != curr.shape:
            raise ValueError(f"Frame shapes must match, got {prev.shape} vs {curr.shape}.")
        patch = self.config.patch_size
        if prev.shape[0] % patch != 0 or prev.shape[1] % patch != 0:
            raise ValueError(
                f"Frame shape {prev.shape[:2]} must be divisible by patch_size={patch}."
            )

    @staticmethod
    def patch_l1_distance(a: np.ndarray, b: np.ndarray) -> float:
        return float(np.mean(np.abs(a - b)))

    @staticmethod
    def _tokenize(frame: np.ndarray, patch_size: int) -> np.ndarray:
        h, w, c = frame.shape
        grid_h, grid_w = h // patch_size, w // patch_size
        return (
            frame.reshape(grid_h, patch_size, grid_w, patch_size, c)
            .transpose(0, 2, 1, 3, 4)
            .copy()
        )

    @staticmethod
    def dilate_mask(mask: np.ndarray, radius: int) -> np.ndarray:
        if radius <= 0:
            return mask.copy()
        out = mask.copy()
        h, w = out.shape
        for _ in range(radius):
            expanded = np.zeros_like(out)
            ys, xs = np.where(out)
            for y, x in zip(ys, xs):
                y0 = max(0, y - 1)
                y1 = min(h, y + 2)
                x0 = max(0, x - 1)
                x1 = min(w, x + 2)
                expanded[y0:y1, x0:x1] = True
            out = expanded
        return out

    @staticmethod
    def token_mask_to_window_mask(mask: np.ndarray, window_size: int) -> np.ndarray:
        if window_size <= 0:
            raise ValueError("window_size must be positive.")
        grid_h, grid_w = mask.shape
        if grid_h % window_size != 0 or grid_w % window_size != 0:
            raise ValueError(
                f"Token grid {mask.shape} must be divisible by window_size={window_size}."
            )
        win_h, win_w = grid_h // window_size, grid_w // window_size
        grouped = (
            mask.reshape(win_h, window_size, win_w, window_size)
            .transpose(0, 2, 1, 3)
        )
        return np.any(grouped, axis=(2, 3))

    @staticmethod
    def window_mask_to_token_mask(window_mask: np.ndarray, window_size: int) -> np.ndarray:
        return np.repeat(np.repeat(window_mask, window_size, axis=0), window_size, axis=1)

    def apply_protect_regions(
        self,
        labels: np.ndarray,
        regions: Sequence[ProtectRegion],
    ) -> Tuple[np.ndarray, np.ndarray]:
        protected = np.zeros_like(labels, dtype=bool)
        patch = self.config.patch_size
        out = labels.copy()
        grid_h, grid_w = out.shape
        centers_y = (np.arange(grid_h) + 0.5) * patch
        centers_x = (np.arange(grid_w) + 0.5) * patch
        for region in regions:
            mask_y = (centers_y >= region.y0) & (centers_y <= region.y1)
            mask_x = (centers_x >= region.x0) & (centers_x <= region.x1)
            if not mask_y.any() or not mask_x.any():
                continue
            protected[np.ix_(mask_y, mask_x)] = True
            out[np.ix_(mask_y, mask_x)] = int(region.force_label)
        return out, protected

    @staticmethod
    def estimate_global_translation(
        prev_frame: np.ndarray,
        curr_frame: np.ndarray,
        *,
        max_shift: int = 8,
    ) -> Tuple[Tuple[int, int], float]:
        prev_gray = prev_frame.mean(axis=2)
        curr_gray = curr_frame.mean(axis=2)
        best_shift = (0, 0)
        best_score = float("inf")
        height, width = prev_gray.shape

        for dy in range(-max_shift, max_shift + 1):
            for dx in range(-max_shift, max_shift + 1):
                y0 = max(0, dy)
                y1 = min(height, height + dy)
                x0 = max(0, dx)
                x1 = min(width, width + dx)
                yy0 = max(0, -dy)
                yy1 = min(height, height - dy)
                xx0 = max(0, -dx)
                xx1 = min(width, width - dx)
                if y1 <= y0 or x1 <= x0:
                    continue
                score = float(
                    np.mean(np.abs(prev_gray[y0:y1, x0:x1] - curr_gray[yy0:yy1, xx0:xx1]))
                )
                if score < best_score:
                    best_score = score
                    best_shift = (dy, dx)
        return best_shift, best_score

    @staticmethod
    def shift_frame(frame: np.ndarray, dy: int, dx: int) -> np.ndarray:
        height, width, channels = frame.shape
        out = np.zeros_like(frame)
        y0 = max(0, dy)
        y1 = min(height, height + dy)
        x0 = max(0, dx)
        x1 = min(width, width + dx)
        yy0 = max(0, -dy)
        yy1 = min(height, height - dy)
        xx0 = max(0, -dx)
        xx1 = min(width, width - dx)
        out[yy0:yy1, xx0:xx1] = frame[y0:y1, x0:x1]
        return out


class TemporalEmbeddingCache:
    """
    Cache for grid-structured token embeddings.

    The cache stores a single reference frame worth of tokens. This keeps the
    implementation simple and corresponds to single-hop caching. Extending to
    multi-reference caches is straightforward: store a list of references and let
    the planner choose which reference each token should pull from.
    """

    def __init__(self) -> None:
        self.tokens_grid: Optional[np.ndarray] = None
        self.frames_since_refresh: int = 0

    @staticmethod
    def _to_numpy_tokens(tokens: ArrayLike) -> np.ndarray:
        if torch is not None and isinstance(tokens, torch.Tensor):
            return tokens.detach().cpu().numpy()
        return np.asarray(tokens)

    @staticmethod
    def _to_original_type(array: np.ndarray, template: ArrayLike) -> ArrayLike:
        if torch is not None and isinstance(template, torch.Tensor):
            return torch.as_tensor(array, device=template.device, dtype=template.dtype)
        return array

    @staticmethod
    def flatten_grid(tokens_grid: np.ndarray) -> np.ndarray:
        grid_h, grid_w, dim = tokens_grid.shape
        return tokens_grid.reshape(grid_h * grid_w, dim)

    @staticmethod
    def unflatten_grid(tokens_flat: np.ndarray, grid_shape: Tuple[int, int]) -> np.ndarray:
        grid_h, grid_w = int(grid_shape[0]), int(grid_shape[1])
        num_tokens, dim = tokens_flat.shape
        expected = grid_h * grid_w
        if num_tokens != expected:
            raise ValueError(f"Expected {expected} tokens, got {num_tokens}.")
        return tokens_flat.reshape(grid_h, grid_w, dim)

    def has_cache(self) -> bool:
        return self.tokens_grid is not None

    def reset(self) -> None:
        self.tokens_grid = None
        self.frames_since_refresh = 0

    def store(self, tokens: ArrayLike, grid_shape: Optional[Tuple[int, int]] = None, *, refreshed: bool = False) -> None:
        tokens_np = self._to_numpy_tokens(tokens)
        if tokens_np.ndim == 2:
            if grid_shape is None:
                raise ValueError("grid_shape is required when storing flat tokens.")
            tokens_grid = self.unflatten_grid(tokens_np, grid_shape)
        elif tokens_np.ndim == 3:
            tokens_grid = tokens_np
        else:
            raise ValueError(f"Unsupported token tensor rank {tokens_np.ndim}; expected 2 or 3.")
        self.tokens_grid = tokens_grid.copy()
        self.frames_since_refresh = 0 if refreshed else self.frames_since_refresh + 1

    def merge_validation(self, fresh_tokens: ArrayLike, plan: ReusePlan) -> ArrayLike:
        """
        Merge cached tokens into a fresh full-frame encoding.

        This is useful for quality validation but does NOT save dense encoder compute.
        """
        if self.tokens_grid is None:
            raise RuntimeError("Cache is empty.")
        fresh_np = self._to_numpy_tokens(fresh_tokens)
        is_flat = fresh_np.ndim == 2
        fresh_grid = (
            self.unflatten_grid(fresh_np, plan.grid_shape) if is_flat else fresh_np.copy()
        )
        if fresh_grid.shape[:2] != self.tokens_grid.shape[:2]:
            raise ValueError(
                f"Grid mismatch: cache {self.tokens_grid.shape[:2]} vs fresh {fresh_grid.shape[:2]}."
            )
        merged = fresh_grid.copy()
        merged[plan.reuse_mask] = self.tokens_grid[plan.reuse_mask]
        merged_out = self.flatten_grid(merged) if is_flat else merged
        return self._to_original_type(merged_out, fresh_tokens)

    def merge_sparse_windows(
        self,
        sparse_recomputed: ArrayLike,
        plan: ReusePlan,
        *,
        window_size: int,
    ) -> ArrayLike:
        """
        Merge sparse window recomputations into the cached grid.

        The backend is expected to return a token grid with valid values in the
        selected windows. Values outside those windows are ignored.
        """
        if self.tokens_grid is None:
            raise RuntimeError("Cache is empty.")
        recomputed_np = self._to_numpy_tokens(sparse_recomputed)
        is_flat = recomputed_np.ndim == 2
        recomputed_grid = (
            self.unflatten_grid(recomputed_np, plan.grid_shape) if is_flat else recomputed_np
        )
        merged = self.tokens_grid.copy()
        token_mask = TemporalRedundancyPlanner.window_mask_to_token_mask(
            plan.recompute_window_mask, window_size=window_size
        )
        merged[token_mask] = recomputed_grid[token_mask]
        merged_out = self.flatten_grid(merged) if is_flat else merged
        return self._to_original_type(merged_out, sparse_recomputed)


class WindowedVisionBackend(Protocol):
    """
    Model-specific sparse backend.

    encode_full(frame):
        Returns the full token grid or flat token tensor.

    encode_windows(frame, window_mask):
        Recomputes only the selected windows and returns a full-sized token tensor
        whose values are valid inside those windows. Outside those windows the
        backend may return zeros or any placeholder values; they are ignored.
    """

    def encode_full(self, frame: ArrayLike) -> ArrayLike:
        ...

    def encode_windows(self, frame: ArrayLike, window_mask: np.ndarray) -> ArrayLike:
        ...


if torch is not None:

    class DenseValidationWrapper(nn.Module):
        """
        Dense reference wrapper around a vision encoder.

        This wrapper always runs the full encoder. It is intended for:
          - quality validation
          - A/B testing cached vs non-cached embeddings
          - establishing whether the downstream LLM is robust to reuse

        It does *not* provide dense-ViT speedups by itself.
        """

        def __init__(
            self,
            encoder: nn.Module,
            planner: TemporalRedundancyPlanner,
        ) -> None:
            super().__init__()
            self.encoder = encoder
            self.planner = planner
            self.cache = TemporalEmbeddingCache()

        def forward(
            self,
            frame: "torch.Tensor",
            *,
            prev_frame_for_planning: Optional[np.ndarray] = None,
            protect_regions: Optional[Sequence[ProtectRegion]] = None,
            use_local_search: bool = True,
        ) -> Tuple["torch.Tensor", Optional[ReusePlan]]:
            if prev_frame_for_planning is None or not self.cache.has_cache():
                tokens = self.encoder(frame)
                grid_shape = self._infer_grid_shape(tokens)
                self.cache.store(tokens, grid_shape=grid_shape, refreshed=True)
                return tokens, None

            curr_np = self._frame_tensor_to_numpy(frame)
            plan = self.planner.plan_from_frames(
                prev_frame_for_planning,
                curr_np,
                protect_regions=protect_regions,
                frames_since_refresh=self.cache.frames_since_refresh,
                use_local_search=use_local_search,
            )

            fresh_tokens = self.encoder(frame)
            grid_shape = self._infer_grid_shape(fresh_tokens)

            if plan.refresh:
                self.cache.store(fresh_tokens, grid_shape=grid_shape, refreshed=True)
                return fresh_tokens, plan

            merged = self.cache.merge_validation(fresh_tokens, plan)
            self.cache.store(merged, grid_shape=grid_shape, refreshed=False)
            return merged, plan

        @staticmethod
        def _frame_tensor_to_numpy(frame: "torch.Tensor") -> np.ndarray:
            arr = frame.detach().float().cpu().numpy()
            # Accept [C, H, W] or [H, W, C].
            if arr.ndim != 3:
                raise ValueError("Expected frame tensor with rank 3.")
            if arr.shape[0] in (1, 3) and arr.shape[-1] not in (1, 3):
                arr = np.transpose(arr, (1, 2, 0))
            return arr

        @staticmethod
        def _infer_grid_shape(tokens: "torch.Tensor") -> Tuple[int, int]:
            if tokens.ndim == 3:
                return int(tokens.shape[0]), int(tokens.shape[1])
            if tokens.ndim == 2:
                num_tokens = int(tokens.shape[0])
                side = int(round(math.sqrt(num_tokens)))
                if side * side != num_tokens:
                    raise ValueError(
                        "Flat tokens require a square grid or explicit reshaping in the encoder."
                    )
                return side, side
            raise ValueError(f"Unsupported token tensor rank {tokens.ndim}.")


    class SparseWindowExecutor(nn.Module):
        """
        Sparse execution wrapper for a backend that supports window recomputation.

        This is the route that can actually reduce encoder compute.
        """

        def __init__(
            self,
            backend: WindowedVisionBackend,
            planner: TemporalRedundancyPlanner,
        ) -> None:
            super().__init__()
            self.backend = backend
            self.planner = planner
            self.cache = TemporalEmbeddingCache()

        def forward(
            self,
            frame: "torch.Tensor",
            *,
            prev_frame_for_planning: Optional[np.ndarray] = None,
            protect_regions: Optional[Sequence[ProtectRegion]] = None,
            use_local_search: bool = True,
        ) -> Tuple["torch.Tensor", Optional[ReusePlan]]:
            if prev_frame_for_planning is None or not self.cache.has_cache():
                full = self.backend.encode_full(frame)
                grid_shape = self._infer_grid_shape(full)
                self.cache.store(full, grid_shape=grid_shape, refreshed=True)
                return full, None

            curr_np = DenseValidationWrapper._frame_tensor_to_numpy(frame)
            plan = self.planner.plan_from_frames(
                prev_frame_for_planning,
                curr_np,
                protect_regions=protect_regions,
                frames_since_refresh=self.cache.frames_since_refresh,
                use_local_search=use_local_search,
            )

            if plan.refresh:
                full = self.backend.encode_full(frame)
                grid_shape = self._infer_grid_shape(full)
                self.cache.store(full, grid_shape=grid_shape, refreshed=True)
                return full, plan

            sparse = self.backend.encode_windows(frame, plan.recompute_window_mask)
            grid_shape = self._infer_grid_shape(sparse)
            merged = self.cache.merge_sparse_windows(
                sparse,
                plan,
                window_size=self.planner.config.window_size_tokens,
            )
            self.cache.store(merged, grid_shape=grid_shape, refreshed=False)
            return merged, plan

        @staticmethod
        def _infer_grid_shape(tokens: "torch.Tensor") -> Tuple[int, int]:
            return DenseValidationWrapper._infer_grid_shape(tokens)


__all__ = [
    "CodecMacroblock",
    "PlannerConfig",
    "ProtectRegion",
    "ReusePlan",
    "TemporalEmbeddingCache",
    "TemporalRedundancyPlanner",
    "TokenClass",
    "WindowedVisionBackend",
]
