
from __future__ import annotations

"""
Expanded codec-inspired design-space tools for video VLM acceleration.

This module extends the reference Codec-Through implementation with:
1. Color-aware planning (luma/chroma split, task-conditioned chroma refresh).
2. Adaptive quadtree partitioning (codec-style variable block sizes).
3. Attention cost estimation for changed-block-focused attention schedules.
4. Prompt/task-aware policy presets for practical experimentation.
5. FFmpeg motion-vector extraction command scaffolds for real-video pipelines.

The goal is not to bind to a specific model implementation. Instead, it provides
planners and estimators that can be wired into MLX-VLM, PyTorch VLMs, or custom
serving backends.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import math
import numpy as np

try:
    # Prefer importing the previously-created reference module if available.
    from codec_through_reference import TokenClass
except Exception:  # pragma: no cover
    class TokenClass(int, Enum):  # fallback
        STATIC = 0
        SHIFTED = 1
        NOVEL = 2


# -----------------------------------------------------------------------------
# Task profiles and policy presets
# -----------------------------------------------------------------------------

class TaskProfile(str, Enum):
    GENERAL = "general"
    MOTION = "motion"
    COLOR = "color"
    OCR = "ocr"
    LOCALIZATION = "localization"
    SCREEN_CONTENT = "screen_content"


@dataclass(frozen=True)
class PromptAwarePolicy:
    """
    Simple preset describing how aggressively we can compress for a task type.
    """
    task: TaskProfile
    target_resolution: int
    allow_luma_only_screening: bool
    preserve_full_chroma: bool
    preferred_attention_strategy: str
    roi_bias: str
    notes: str = ""


def recommend_policy(task: TaskProfile) -> PromptAwarePolicy:
    if task == TaskProfile.COLOR:
        return PromptAwarePolicy(
            task=task,
            target_resolution=280,
            allow_luma_only_screening=False,
            preserve_full_chroma=True,
            preferred_attention_strategy="changed_queries_full_context",
            roi_bias="protect explicitly color-relevant regions",
            notes="Color questions should not rely on luma-only screening.",
        )
    if task == TaskProfile.OCR:
        return PromptAwarePolicy(
            task=task,
            target_resolution=336,
            allow_luma_only_screening=False,
            preserve_full_chroma=True,
            preferred_attention_strategy="changed_queries_full_context",
            roi_bias="protect text regions and UI overlays",
            notes="OCR is highly sensitive to resolution, edges, and local detail.",
        )
    if task == TaskProfile.SCREEN_CONTENT:
        return PromptAwarePolicy(
            task=task,
            target_resolution=336,
            allow_luma_only_screening=False,
            preserve_full_chroma=True,
            preferred_attention_strategy="changed_queries_plus_summary",
            roi_bias="protect text, cursors, toolbars, highlighted windows",
            notes="Screen/video calls benefit from palette and exact-copy style logic.",
        )
    if task == TaskProfile.LOCALIZATION:
        return PromptAwarePolicy(
            task=task,
            target_resolution=280,
            allow_luma_only_screening=True,
            preserve_full_chroma=False,
            preferred_attention_strategy="changed_queries_full_context",
            roi_bias="protect queried objects, hands, and contact zones",
            notes="Localization needs detail where small objects may move.",
        )
    if task == TaskProfile.MOTION:
        return PromptAwarePolicy(
            task=task,
            target_resolution=224,
            allow_luma_only_screening=True,
            preserve_full_chroma=False,
            preferred_attention_strategy="changed_queries_plus_summary",
            roi_bias="protect moving actors and global motion summaries",
            notes="Motion-heavy tasks often tolerate lower chroma fidelity.",
        )
    return PromptAwarePolicy(
        task=task,
        target_resolution=224,
        allow_luma_only_screening=True,
        preserve_full_chroma=False,
        preferred_attention_strategy="changed_queries_plus_summary",
        roi_bias="minimal ROI protection unless prompted",
        notes="Default policy is conservative but efficient.",
    )


# -----------------------------------------------------------------------------
# Color-aware planning
# -----------------------------------------------------------------------------

@dataclass
class ColorAwareConfig:
    patch_size: int = 16
    luma_static_threshold: float = 0.012
    luma_shifted_threshold: float = 0.040
    chroma_static_threshold: float = 0.015
    chroma_novel_threshold: float = 0.040
    color_task_chroma_refresh_threshold: float = 0.020
    periodic_chroma_refresh: int = 4


@dataclass
class ColorAwarePlan:
    labels: np.ndarray  # [grid_h, grid_w]
    y_diff: np.ndarray
    cbcr_diff: np.ndarray
    novel_mask: np.ndarray
    reuse_mask: np.ndarray
    task: TaskProfile
    forced_chroma_refresh: bool = False

    @property
    def novel_ratio(self) -> float:
        return float(self.novel_mask.mean())

    @property
    def reuse_ratio(self) -> float:
        return float(self.reuse_mask.mean())

    def summary(self) -> Dict[str, float]:
        return {
            "novel_pct": 100.0 * self.novel_ratio,
            "reuse_pct": 100.0 * self.reuse_ratio,
            "mean_y_diff": float(self.y_diff.mean()),
            "mean_cbcr_diff": float(self.cbcr_diff.mean()),
            "forced_chroma_refresh": bool(self.forced_chroma_refresh),
        }


def rgb_to_ycbcr(frame: np.ndarray) -> np.ndarray:
    """
    Convert RGB in [0, 1] to YCbCr-like channels in [0, 1].
    """
    x = np.asarray(frame, dtype=np.float32)
    if x.max() > 1.0 or x.min() < 0.0:
        x = np.clip(x, 0.0, 255.0) / 255.0

    r = x[..., 0]
    g = x[..., 1]
    b = x[..., 2]

    y = 0.299 * r + 0.587 * g + 0.114 * b
    cb = 0.564 * (b - y) + 0.5
    cr = 0.713 * (r - y) + 0.5
    out = np.stack([y, cb, cr], axis=-1)
    return np.clip(out, 0.0, 1.0)


def ycbcr_to_rgb(frame: np.ndarray) -> np.ndarray:
    """
    Inverse of the simple YCbCr transform above. Useful for synthetic tests.
    """
    x = np.asarray(frame, dtype=np.float32)
    y = x[..., 0]
    cb = x[..., 1] - 0.5
    cr = x[..., 2] - 0.5

    r = y + 1.403 * cr
    b = y + 1.773 * cb
    g = y - 0.344 * cb - 0.714 * cr
    out = np.stack([r, g, b], axis=-1)
    return np.clip(out, 0.0, 1.0)


def _patch_grid(frame: np.ndarray, patch_size: int) -> Tuple[int, int]:
    h, w = frame.shape[:2]
    if h % patch_size != 0 or w % patch_size != 0:
        raise ValueError(
            f"frame shape {frame.shape[:2]} must be divisible by patch_size={patch_size}"
        )
    return h // patch_size, w // patch_size


def plan_color_aware(
    prev_frame: np.ndarray,
    curr_frame: np.ndarray,
    *,
    task: TaskProfile = TaskProfile.GENERAL,
    config: Optional[ColorAwareConfig] = None,
    frames_since_chroma_refresh: int = 0,
) -> ColorAwarePlan:
    """
    Classify token regions with separate luma/chroma signals.

    The key use case is to safely exploit luma dominance for many tasks while
    still protecting color-sensitive tasks from chroma-only failures.
    """
    cfg = config or ColorAwareConfig()
    prev = rgb_to_ycbcr(prev_frame)
    curr = rgb_to_ycbcr(curr_frame)

    if prev.shape != curr.shape:
        raise ValueError("prev_frame and curr_frame must have identical shapes")

    grid_h, grid_w = _patch_grid(prev, cfg.patch_size)

    labels = np.full((grid_h, grid_w), TokenClass.STATIC, dtype=np.int32)
    y_diff = np.zeros((grid_h, grid_w), dtype=np.float32)
    cbcr_diff = np.zeros((grid_h, grid_w), dtype=np.float32)

    for gy in range(grid_h):
        for gx in range(grid_w):
            y0 = gy * cfg.patch_size
            x0 = gx * cfg.patch_size
            y1 = y0 + cfg.patch_size
            x1 = x0 + cfg.patch_size

            prev_patch = prev[y0:y1, x0:x1]
            curr_patch = curr[y0:y1, x0:x1]

            dy = float(np.mean(np.abs(prev_patch[..., 0] - curr_patch[..., 0])))
            dc = float(np.mean(np.abs(prev_patch[..., 1:] - curr_patch[..., 1:])))

            y_diff[gy, gx] = dy
            cbcr_diff[gy, gx] = dc

            if dy < cfg.luma_static_threshold and dc < cfg.chroma_static_threshold:
                labels[gy, gx] = int(TokenClass.STATIC)
                continue

            if dy < cfg.luma_static_threshold:
                # Pure/small chroma change. Safe to ignore for some tasks, dangerous for others.
                if task in (TaskProfile.COLOR, TaskProfile.SCREEN_CONTENT):
                    if dc >= cfg.color_task_chroma_refresh_threshold:
                        labels[gy, gx] = int(TokenClass.NOVEL)
                    else:
                        labels[gy, gx] = int(TokenClass.STATIC)
                else:
                    labels[gy, gx] = int(TokenClass.STATIC)
                continue

            if dy < cfg.luma_shifted_threshold and dc < cfg.chroma_novel_threshold:
                labels[gy, gx] = int(TokenClass.SHIFTED)
            else:
                labels[gy, gx] = int(TokenClass.NOVEL)

    forced_chroma_refresh = False
    if task in (TaskProfile.COLOR, TaskProfile.SCREEN_CONTENT) and frames_since_chroma_refresh >= cfg.periodic_chroma_refresh:
        forced_chroma_refresh = True
        labels[cbcr_diff >= cfg.chroma_static_threshold] = int(TokenClass.NOVEL)

    novel_mask = labels == int(TokenClass.NOVEL)
    reuse_mask = ~novel_mask

    return ColorAwarePlan(
        labels=labels,
        y_diff=y_diff,
        cbcr_diff=cbcr_diff,
        novel_mask=novel_mask,
        reuse_mask=reuse_mask,
        task=task,
        forced_chroma_refresh=forced_chroma_refresh,
    )


# -----------------------------------------------------------------------------
# Adaptive partitioning (codec-style variable block sizes)
# -----------------------------------------------------------------------------

@dataclass
class AdaptivePartitionConfig:
    max_block: int = 64
    min_block: int = 8
    variance_threshold: float = 0.002
    channel: str = "y"  # "y" or "rgb"


@dataclass
class QuadtreeNode:
    x: int
    y: int
    size: int
    depth: int
    score: float
    children: Optional[List["QuadtreeNode"]] = None

    @property
    def is_leaf(self) -> bool:
        return not self.children


def _channel_view(frame: np.ndarray, channel: str) -> np.ndarray:
    if channel == "y":
        return rgb_to_ycbcr(frame)[..., 0]
    if channel == "rgb":
        return np.asarray(frame, dtype=np.float32).mean(axis=-1)
    raise ValueError(f"unsupported channel={channel!r}")


def _block_score(block: np.ndarray) -> float:
    # Variance is simple and stable for synthetic and real images.
    return float(np.var(block))


def build_quadtree(
    frame: np.ndarray,
    *,
    config: Optional[AdaptivePartitionConfig] = None,
) -> QuadtreeNode:
    cfg = config or AdaptivePartitionConfig()
    view = _channel_view(frame, cfg.channel)
    h, w = view.shape
    if h != w:
        raise ValueError("quadtree helper expects a square image")
    if h & (h - 1) != 0:
        raise ValueError("quadtree helper expects power-of-two image size")
    if cfg.max_block > h:
        raise ValueError("max_block cannot exceed image size")
    if cfg.min_block <= 0 or cfg.max_block <= 0 or cfg.min_block > cfg.max_block:
        raise ValueError("invalid block sizes")
    if cfg.max_block & (cfg.max_block - 1) != 0 or cfg.min_block & (cfg.min_block - 1) != 0:
        raise ValueError("block sizes must be powers of two")

    def build_node(x: int, y: int, size: int, depth: int) -> QuadtreeNode:
        block = view[y:y+size, x:x+size]
        score = _block_score(block)
        if size <= cfg.min_block or score < cfg.variance_threshold:
            return QuadtreeNode(x=x, y=y, size=size, depth=depth, score=score, children=None)

        half = size // 2
        children = [
            build_node(x, y, half, depth + 1),
            build_node(x + half, y, half, depth + 1),
            build_node(x, y + half, half, depth + 1),
            build_node(x + half, y + half, half, depth + 1),
        ]
        return QuadtreeNode(x=x, y=y, size=size, depth=depth, score=score, children=children)

    # Wrap with max_block tiles if the full image is larger.
    if h == cfg.max_block:
        return build_node(0, 0, h, 0)

    # Create a virtual root over max_block chunks.
    tiles: List[QuadtreeNode] = []
    for y in range(0, h, cfg.max_block):
        for x in range(0, w, cfg.max_block):
            tiles.append(build_node(x, y, cfg.max_block, 1))
    return QuadtreeNode(x=0, y=0, size=h, depth=0, score=float(np.var(view)), children=tiles)


def collect_leaf_nodes(node: QuadtreeNode) -> List[QuadtreeNode]:
    if node.children is None:
        return [node]
    leaves: List[QuadtreeNode] = []
    for child in node.children:
        leaves.extend(collect_leaf_nodes(child))
    return leaves


def quadtree_token_equivalents(
    leaves: Sequence[QuadtreeNode],
    *,
    baseline_patch: int = 16,
) -> Dict[str, float]:
    """
    Estimate how many baseline-size patch tokens a quadtree partition would map to
    if coarse leaves were represented by one token each and fine leaves expanded
    down to the baseline patch size.
    """
    leaf_count = len(leaves)
    baseline_tokens = 0
    coarse_tokenized = 0
    for node in leaves:
        baseline_tokens += max(1, (node.size // baseline_patch) ** 2)
        coarse_tokenized += 1
    return {
        "leaf_count": float(leaf_count),
        "baseline_equivalent_tokens": float(baseline_tokens),
        "coarse_tokenized_tokens": float(coarse_tokenized),
        "compression_vs_baseline": float(baseline_tokens / max(coarse_tokenized, 1)),
    }


# -----------------------------------------------------------------------------
# Changed-block-focused attention cost estimation
# -----------------------------------------------------------------------------

@dataclass
class AttentionEstimate:
    strategy: str
    n_tokens: int
    dynamic_tokens: int
    static_tokens: int
    approx_attention_ops: int
    dense_attention_ops: int
    reduction_x: float
    parameters: Dict[str, int]

    def summary(self) -> Dict[str, float]:
        return {
            "strategy": self.strategy,
            "n_tokens": self.n_tokens,
            "dynamic_tokens": self.dynamic_tokens,
            "static_tokens": self.static_tokens,
            "approx_attention_ops": self.approx_attention_ops,
            "dense_attention_ops": self.dense_attention_ops,
            "reduction_x": self.reduction_x,
        }


def estimate_attention_cost(
    *,
    n_tokens: int,
    dynamic_ratio: float,
    local_context_tokens: int = 9,
    summary_tokens: int = 8,
    strategy: str = "changed_queries_full_context",
) -> AttentionEstimate:
    """
    Crude but useful cost model for attention schedules.

    Assumes a single attention layer and ignores head count/constants, focusing on
    QK-style interaction count.
    """
    if not (0.0 <= dynamic_ratio <= 1.0):
        raise ValueError("dynamic_ratio must be in [0, 1]")

    nd = int(round(n_tokens * dynamic_ratio))
    nd = max(1, min(n_tokens, nd))
    ns = n_tokens - nd
    dense = n_tokens * n_tokens

    if strategy == "dense_global":
        approx = dense

    elif strategy == "changed_queries_full_context":
        # Dynamic queries see everything. Static queries only refresh locally.
        approx = nd * n_tokens + ns * local_context_tokens + summary_tokens * n_tokens

    elif strategy == "changed_queries_plus_summary":
        # Dynamic queries mostly see dynamic tokens + small global summaries.
        approx = nd * (nd + summary_tokens + local_context_tokens) + ns * local_context_tokens + summary_tokens * n_tokens

    elif strategy == "dynamic_only_global":
        # Extreme option: only dynamic tokens run global attention; static regions are frozen.
        approx = nd * n_tokens + summary_tokens * n_tokens

    else:
        raise ValueError(f"unknown strategy={strategy!r}")

    reduction = float(dense / max(approx, 1))
    return AttentionEstimate(
        strategy=strategy,
        n_tokens=n_tokens,
        dynamic_tokens=nd,
        static_tokens=ns,
        approx_attention_ops=int(approx),
        dense_attention_ops=int(dense),
        reduction_x=reduction,
        parameters={
            "local_context_tokens": int(local_context_tokens),
            "summary_tokens": int(summary_tokens),
        },
    )


def attention_savings_curve(
    *,
    n_tokens: int,
    dynamic_ratios: Sequence[float],
    strategies: Sequence[str],
    local_context_tokens: int = 9,
    summary_tokens: int = 8,
) -> List[AttentionEstimate]:
    out: List[AttentionEstimate] = []
    for ratio in dynamic_ratios:
        for strategy in strategies:
            out.append(
                estimate_attention_cost(
                    n_tokens=n_tokens,
                    dynamic_ratio=float(ratio),
                    local_context_tokens=local_context_tokens,
                    summary_tokens=summary_tokens,
                    strategy=strategy,
                )
            )
    return out


# -----------------------------------------------------------------------------
# FFmpeg / real-video command scaffolds
# -----------------------------------------------------------------------------

def build_ffprobe_motion_vector_command(video_path: str | Path) -> List[str]:
    """
    Build an ffprobe command that requests motion-vector side-data when supported.
    """
    path = str(video_path)
    return [
        "ffprobe",
        "-flags2", "+export_mvs",
        "-export_side_data", "mvs",
        "-select_streams", "v:0",
        "-show_frames",
        "-show_entries", "frame=pts_time,pict_type,width,height,side_data_list",
        "-of", "json",
        path,
    ]


def build_ffmpeg_extract_mvs_example_command(video_path: str | Path) -> str:
    """
    Build a reminder command for the upstream FFmpeg extract_mvs example route.
    """
    return (
        "Use FFmpeg's doc/examples/extract_mvs.c against "
        f"{video_path!s} after decoding with export_mvs enabled."
    )


def build_ffmpeg_lowres_gray_decode_command(
    video_path: str | Path,
    output_pattern: str = "frame_%05d.png",
    *,
    lowres: int = 1,
    gray: bool = False,
    fps: float = 1.0,
) -> List[str]:
    """
    Practical helper for low-resolution or grayscale decode sweeps.
    lowres=1 -> 1/2 resolution, 2 -> 1/4, 3 -> 1/8 for codecs that support it.
    """
    cmd = [
        "ffmpeg",
        "-i", str(video_path),
        "-vf", f"fps={fps}",
    ]
    if gray:
        cmd.extend(["-pix_fmt", "gray"])
    cmd.extend(["-start_number", "0", output_pattern])
    return cmd


__all__ = [
    "TaskProfile",
    "PromptAwarePolicy",
    "recommend_policy",
    "ColorAwareConfig",
    "ColorAwarePlan",
    "rgb_to_ycbcr",
    "ycbcr_to_rgb",
    "plan_color_aware",
    "AdaptivePartitionConfig",
    "QuadtreeNode",
    "build_quadtree",
    "collect_leaf_nodes",
    "quadtree_token_equivalents",
    "AttentionEstimate",
    "estimate_attention_cost",
    "attention_savings_curve",
    "build_ffprobe_motion_vector_command",
    "build_ffmpeg_extract_mvs_example_command",
    "build_ffmpeg_lowres_gray_decode_command",
]
