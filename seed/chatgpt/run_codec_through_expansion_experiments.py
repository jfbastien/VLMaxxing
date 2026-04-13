
from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from codec_through_expansions import (
    AdaptivePartitionConfig,
    TaskProfile,
    attention_savings_curve,
    build_quadtree,
    collect_leaf_nodes,
    plan_color_aware,
    quadtree_token_equivalents,
    rgb_to_ycbcr,
    ycbcr_to_rgb,
)


OUT_DIR = Path("/mnt/data")
REPORT_PATH = OUT_DIR / "codec_design_space_report.md"
ATTN_PLOT = OUT_DIR / "codec_attention_savings.png"
QUADTREE_MIXED = OUT_DIR / "codec_quadtree_mixed_detail.png"
QUADTREE_FLAT = OUT_DIR / "codec_quadtree_flat.png"
COLOR_PLOT = OUT_DIR / "codec_color_change_masks.png"


def ensure_dir() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)


def make_base_scene(size: int = 256) -> np.ndarray:
    img = np.ones((size, size, 3), dtype=np.float32) * 0.92
    # darker desk-like strip
    img[int(size * 0.70):, :] *= 0.85
    # neutral object
    img[int(size * 0.10):int(size * 0.22), int(size * 0.68):int(size * 0.86)] = np.array([0.65, 0.65, 0.68], dtype=np.float32)
    return img


def add_same_luma_chroma_square(
    image: np.ndarray,
    *,
    x0: int,
    y0: int,
    size: int,
    y_value: float,
    cb_value: float,
    cr_value: float,
) -> np.ndarray:
    out = image.copy()
    patch = np.zeros((size, size, 3), dtype=np.float32)
    patch[..., 0] = y_value
    patch[..., 1] = cb_value
    patch[..., 2] = cr_value
    out[y0:y0+size, x0:x0+size] = ycbcr_to_rgb(patch)
    return out


def add_textured_region(image: np.ndarray, *, x0: int, y0: int, w: int, h: int) -> np.ndarray:
    out = image.copy()
    for y in range(y0, y0 + h):
        for x in range(x0, x0 + w):
            v = ((x // 4) % 2) ^ ((y // 4) % 2)
            out[y, x] = np.array([0.25, 0.25, 0.25], dtype=np.float32) if v else np.array([0.85, 0.85, 0.85], dtype=np.float32)
    return out


def add_text_lines(image: np.ndarray, *, x0: int, y0: int, n_lines: int = 6) -> np.ndarray:
    out = image.copy()
    line_h = 6
    for i in range(n_lines):
        yy = y0 + i * 12
        out[yy:yy + line_h, x0:x0 + 96] = 0.15
        # holes / spaces
        for gap in range(0, 96, 24):
            out[yy + 1:yy + line_h - 1, x0 + gap + 10:x0 + gap + 15] = 0.92
    return out


def simple_rgb_novel_mask(prev: np.ndarray, curr: np.ndarray, patch_size: int = 16, threshold: float = 0.02) -> np.ndarray:
    h, w = prev.shape[:2]
    gh, gw = h // patch_size, w // patch_size
    out = np.zeros((gh, gw), dtype=bool)
    for gy in range(gh):
        for gx in range(gw):
            y0 = gy * patch_size
            x0 = gx * patch_size
            patch_prev = prev[y0:y0+patch_size, x0:x0+patch_size]
            patch_curr = curr[y0:y0+patch_size, x0:x0+patch_size]
            diff = float(np.mean(np.abs(patch_prev - patch_curr)))
            out[gy, gx] = diff >= threshold
    return out


def render_mask_overlay(frame: np.ndarray, mask: np.ndarray, patch_size: int = 16) -> np.ndarray:
    out = frame.copy()
    gh, gw = mask.shape
    for gy in range(gh):
        for gx in range(gw):
            if mask[gy, gx]:
                y0 = gy * patch_size
                x0 = gx * patch_size
                y1 = y0 + patch_size
                x1 = x0 + patch_size
                # red tint overlay
                out[y0:y1, x0:x1, 0] = np.clip(out[y0:y1, x0:x1, 0] * 0.5 + 0.5, 0.0, 1.0)
                out[y0:y1, x0:x1, 1:] *= 0.6
    return out


def render_quadtree_overlay(frame: np.ndarray, leaves, linewidth: int = 1) -> np.ndarray:
    out = (frame.copy() * 255.0).astype(np.uint8)
    h, w = out.shape[:2]
    for node in leaves:
        x0, y0, s = node.x, node.y, node.size
        x1, y1 = min(w - 1, x0 + s - 1), min(h - 1, y0 + s - 1)
        out[y0:y0+linewidth, x0:x1+1] = [255, 0, 0]
        out[y1-linewidth+1:y1+1, x0:x1+1] = [255, 0, 0]
        out[y0:y1+1, x0:x0+linewidth] = [255, 0, 0]
        out[y0:y1+1, x1-linewidth+1:x1+1] = [255, 0, 0]
    return out.astype(np.float32) / 255.0


def run_color_experiment() -> Tuple[pd.DataFrame, Dict[str, np.ndarray]]:
    prev = make_base_scene()
    curr_color = add_same_luma_chroma_square(
        prev,
        x0=96,
        y0=96,
        size=48,
        y_value=0.55,
        cb_value=0.70,
        cr_value=0.35,
    )
    curr_color_changed = add_same_luma_chroma_square(
        prev,
        x0=96,
        y0=96,
        size=48,
        y_value=0.55,  # constant luma
        cb_value=0.30,
        cr_value=0.65,
    )

    # Baselines
    rgb_mask = simple_rgb_novel_mask(curr_color, curr_color_changed, patch_size=16, threshold=0.02)
    general_plan = plan_color_aware(
        curr_color,
        curr_color_changed,
        task=TaskProfile.GENERAL,
    )
    color_plan = plan_color_aware(
        curr_color,
        curr_color_changed,
        task=TaskProfile.COLOR,
    )

    rows = [
        {
            "method": "RGB diff baseline",
            "novel_pct": 100.0 * float(rgb_mask.mean()),
            "notes": "Detects pure chroma change because RGB values moved.",
        },
        {
            "method": "Color-aware planner / GENERAL task",
            "novel_pct": 100.0 * general_plan.novel_ratio,
            "notes": "Treats chroma-only differences as reusable for non-color tasks.",
        },
        {
            "method": "Color-aware planner / COLOR task",
            "novel_pct": 100.0 * color_plan.novel_ratio,
            "notes": "Promotes chroma-only differences to NOVEL for color-sensitive questions.",
        },
    ]
    df = pd.DataFrame(rows)

    images = {
        "prev": curr_color,
        "curr": curr_color_changed,
        "rgb_mask_overlay": render_mask_overlay(curr_color_changed, rgb_mask, patch_size=16),
        "general_mask_overlay": render_mask_overlay(curr_color_changed, general_plan.novel_mask, patch_size=16),
        "color_mask_overlay": render_mask_overlay(curr_color_changed, color_plan.novel_mask, patch_size=16),
    }
    return df, images


def run_attention_experiment() -> pd.DataFrame:
    ratios = [0.01, 0.02, 0.05, 0.10, 0.20, 0.40, 0.60]
    strategies = [
        "changed_queries_full_context",
        "changed_queries_plus_summary",
        "dynamic_only_global",
    ]
    estimates = attention_savings_curve(
        n_tokens=400,
        dynamic_ratios=ratios,
        strategies=strategies,
        local_context_tokens=9,
        summary_tokens=8,
    )
    rows = []
    for est in estimates:
        rows.append(
            {
                "dynamic_ratio": est.dynamic_tokens / est.n_tokens,
                "strategy": est.strategy,
                "approx_ops": est.approx_attention_ops,
                "dense_ops": est.dense_attention_ops,
                "reduction_x": est.reduction_x,
            }
        )
    return pd.DataFrame(rows)


def run_quadtree_experiment() -> Tuple[pd.DataFrame, Dict[str, np.ndarray]]:
    base = np.ones((256, 256, 3), dtype=np.float32) * 0.93
    flat_scene = base.copy()

    mixed = base.copy()
    mixed = add_text_lines(mixed, x0=24, y0=24, n_lines=8)
    mixed = add_textured_region(mixed, x0=156, y0=136, w=64, h=64)
    mixed[190:232, 24:120] = np.array([0.22, 0.45, 0.80], dtype=np.float32)  # UI-like colored bar

    cfg = AdaptivePartitionConfig(max_block=64, min_block=16, variance_threshold=0.004, channel="y")
    flat_tree = build_quadtree(flat_scene, config=cfg)
    mixed_tree = build_quadtree(mixed, config=cfg)

    flat_leaves = collect_leaf_nodes(flat_tree)
    mixed_leaves = collect_leaf_nodes(mixed_tree)

    flat_stats = quadtree_token_equivalents(flat_leaves, baseline_patch=16)
    mixed_stats = quadtree_token_equivalents(mixed_leaves, baseline_patch=16)

    baseline_tokens = (256 // 16) ** 2

    rows = [
        {
            "scene": "flat",
            "baseline_16x16_tokens": baseline_tokens,
            "adaptive_leaves": int(flat_stats["leaf_count"]),
            "compression_vs_fixed": round(float(baseline_tokens / flat_stats["coarse_tokenized_tokens"]), 2),
        },
        {
            "scene": "mixed_detail",
            "baseline_16x16_tokens": baseline_tokens,
            "adaptive_leaves": int(mixed_stats["leaf_count"]),
            "compression_vs_fixed": round(float(baseline_tokens / mixed_stats["coarse_tokenized_tokens"]), 2),
        },
    ]
    df = pd.DataFrame(rows)

    images = {
        "flat": render_quadtree_overlay(flat_scene, flat_leaves),
        "mixed": render_quadtree_overlay(mixed, mixed_leaves),
    }
    return df, images


def save_attention_plot(df: pd.DataFrame) -> None:
    plt.figure(figsize=(7, 4.5))
    for strategy in sorted(df["strategy"].unique()):
        sub = df[df["strategy"] == strategy].sort_values("dynamic_ratio")
        plt.plot(sub["dynamic_ratio"], sub["reduction_x"], marker="o", label=strategy)
    plt.xlabel("Dynamic token ratio")
    plt.ylabel("Approx attention reduction (x)")
    plt.title("Changed-block-focused attention savings")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(ATTN_PLOT, dpi=180)
    plt.close()


def save_color_plot(images: Dict[str, np.ndarray]) -> None:
    plt.figure(figsize=(10, 6))
    titles = [
        "Previous frame",
        "Current frame",
        "RGB-diff novel mask",
        "GENERAL-task mask",
        "COLOR-task mask",
    ]
    keys = ["prev", "curr", "rgb_mask_overlay", "general_mask_overlay", "color_mask_overlay"]
    for i, (title, key) in enumerate(zip(titles, keys), start=1):
        plt.subplot(2, 3, i)
        plt.imshow(np.clip(images[key], 0.0, 1.0))
        plt.title(title)
        plt.axis("off")
    plt.tight_layout()
    plt.savefig(COLOR_PLOT, dpi=180)
    plt.close()


def save_quadtree_images(images: Dict[str, np.ndarray]) -> None:
    plt.figure(figsize=(6, 6))
    plt.imshow(np.clip(images["flat"], 0.0, 1.0))
    plt.title("Adaptive quadtree on flat scene")
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(QUADTREE_FLAT, dpi=180)
    plt.close()

    plt.figure(figsize=(6, 6))
    plt.imshow(np.clip(images["mixed"], 0.0, 1.0))
    plt.title("Adaptive quadtree on mixed-detail scene")
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(QUADTREE_MIXED, dpi=180)
    plt.close()


def df_to_markdown(df: pd.DataFrame, digits: int = 2) -> str:
    df2 = df.copy()
    for col in df2.columns:
        if pd.api.types.is_float_dtype(df2[col]):
            df2[col] = df2[col].map(lambda x: round(float(x), digits))
    return df2.to_markdown(index=False)


def build_report(
    color_df: pd.DataFrame,
    attn_df: pd.DataFrame,
    quad_df: pd.DataFrame,
) -> str:
    top_rows = (
        attn_df.sort_values(["dynamic_ratio", "reduction_x"], ascending=[True, False])
        .groupby("dynamic_ratio", as_index=False)
        .first()
    )
    lines: List[str] = []
    lines.append("# Expanded codec design-space toy experiments")
    lines.append("These experiments probe design ideas suggested by codec theory and the whitepaper, but they are synthetic and do **not** replace end-to-end VLM benchmarking.")
    lines.append("")
    lines.append("## 1) Color-aware planning")
    lines.append("This experiment creates a square whose **luma stays constant while chroma changes**. It tests a key failure mode of luma-only screening: non-color tasks may safely reuse such regions, while color-sensitive tasks should refresh them.")
    lines.append("")
    lines.append(df_to_markdown(color_df))
    lines.append("")
    lines.append("Interpretation:")
    lines.append("- A generic planner can safely ignore some chroma-only changes for many tasks.")
    lines.append("- A color-sensitive policy should explicitly promote chroma-only changes to refreshes.")
    lines.append("- This is a concrete reason to make compression **task-aware**, not just frame-aware.")
    lines.append("")
    lines.append("## 2) Attention focused on changed blocks")
    lines.append("We estimate attention interaction counts for a 400-token frame under several sparse attention schedules.")
    lines.append("")
    lines.append("Best strategy by dynamic ratio:")
    lines.append("")
    lines.append(df_to_markdown(top_rows[["dynamic_ratio", "strategy", "reduction_x"]]))
    lines.append("")
    lines.append("Interpretation:")
    lines.append("- When only 1%-10% of tokens are dynamic, changed-block-focused attention can reduce attention work by roughly an order of magnitude in this toy model.")
    lines.append("- Savings shrink as the dynamic fraction rises, which is why FPV/egomotion content needs better motion compensation and/or multi-reference caches.")
    lines.append("- This estimate only covers attention interactions; real speedups depend on implementation details, memory traffic, and how much of the encoder can skip recomputation.")
    lines.append("")
    lines.append("## 3) Adaptive codec-style partitioning")
    lines.append("This experiment uses a quadtree over luma variance to imitate variable block sizes such as codec CTUs / recursive partitions. The minimum block size is 16×16, matching the fixed-token baseline; the gain comes only from keeping flat regions coarse.")
    lines.append("")
    lines.append(df_to_markdown(quad_df))
    lines.append("")
    lines.append("Interpretation:")
    lines.append("- Large flat regions deserve coarse tokens or large skipped blocks.")
    lines.append("- Dense or text-like regions deserve finer partitions.")
    lines.append("- A variable-resolution visual frontend could therefore behave more like a modern codec: spend detail budget where entropy is concentrated.")
    lines.append("")
    lines.append("## Takeaways")
    lines.append("1. **Model changes are worth it.** The zero-change path is excellent for validation, but bigger gains appear when the encoder/attention schedule becomes change-aware.")
    lines.append("2. **Color should be conditional.** Luma-first screening is attractive, but color questions, screen content, and UI text need a more conservative policy.")
    lines.append("3. **Codec partition logic is underused.** Recursive variable block sizes look promising for VLM tokenization, especially on content with large flat regions and small dense details.")
    lines.append("4. **Attention can be guided by change maps.** Even a crude changed-query schedule offers strong theoretical savings when the dynamic token fraction is low.")
    lines.append("")
    lines.append("## Generated artifacts")
    lines.append(f"- Attention savings plot: `{ATTN_PLOT.name}`")
    lines.append(f"- Color-aware masks: `{COLOR_PLOT.name}`")
    lines.append(f"- Flat-scene quadtree: `{QUADTREE_FLAT.name}`")
    lines.append(f"- Mixed-detail quadtree: `{QUADTREE_MIXED.name}`")
    return "\n".join(lines)


def main() -> None:
    ensure_dir()

    color_df, color_images = run_color_experiment()
    attn_df = run_attention_experiment()
    quad_df, quad_images = run_quadtree_experiment()

    save_attention_plot(attn_df)
    save_color_plot(color_images)
    save_quadtree_images(quad_images)

    report = build_report(color_df, attn_df, quad_df)
    REPORT_PATH.write_text(report)

    print(f"Wrote: {REPORT_PATH}")
    print(f"Wrote: {ATTN_PLOT}")
    print(f"Wrote: {COLOR_PLOT}")
    print(f"Wrote: {QUADTREE_FLAT}")
    print(f"Wrote: {QUADTREE_MIXED}")


if __name__ == "__main__":
    main()
