#!/usr/bin/env python3
"""Render polished Figure 1 candidates from mined real-video windows."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

os.environ.setdefault("MPLCONFIGDIR", str(REPO_ROOT / ".tmp" / "matplotlib"))

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw

from fig1_primitives import (  # noqa: E402
    THEME,
    arrow,
    brick_row,
    draw_highlight_regions,
    draw_raster_frame,
    label,
    new_canvas,
    pill,
    reuse_bar,
    rounded_panel,
    runtime_bar,
    save_figure,
)


GENERATED = REPO_ROOT / "paper" / "arxiv" / "generated"
DEFAULT_CANDIDATES = GENERATED / "figures" / "fig1_candidates" / "ranked_candidates.json"
DEFAULT_OUT = GENERATED / "figures" / "fig1_variants"
HEADLINE_SNAPSHOT = GENERATED / "data" / "headline_snapshot.json"
CEILING_DATA = GENERATED / "data" / "v_share_v_red_ceiling_data.json"


def safe_rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def load_candidates(path: Path, *, top_k: int, candidate_ids: set[str] | None) -> list[dict[str, Any]]:
    payload = load_json(path)
    candidates = payload["candidates"]
    if candidate_ids:
        candidates = [candidate for candidate in candidates if candidate["candidate_id"] in candidate_ids]
    return candidates[:top_k]


def headline_values() -> dict[str, Any]:
    snapshot = load_json(HEADLINE_SNAPSHOT)
    repair = snapshot["selective_reprefill"]["adaptive"]
    measured = snapshot["measured_sparse_execution"]["gemma_32f_short"]
    qwen_16f = next(row for row in snapshot["persistent_kv"]["rows"] if int(row["frame_count"]) == 16)
    drift = int(round(float(measured["n"]) * (1.0 - float(measured["choice_agreement"]))))
    ceiling = load_json(CEILING_DATA)
    composition = ceiling["composition_cells"][0]
    return {
        "c_persist_min": float(repair["speedup_min"]),
        "c_persist_max": float(repair["speedup_max"]),
        "c_persist_choice_drift": int(repair["paired_choice_diffs"]),
        "c_persist_n": int(repair["n_pairs"]),
        "c_persist_follow_up_n": int(repair["n_follow_up_pairs"]),
        "raw_16f_speedup": float(qwen_16f["speedup"]),
        "c_vision_e2e": float(measured["observed_e2e"]),
        "c_vision_n": int(measured["n"]),
        "c_vision_drift": drift,
        "c_vision_v_share": float(measured["vision_share_dense"]),
        "c_vision_v_red": float(measured["vision_reduction"]),
        "c_vision_pred": float(measured["predicted_e2e"]),
        "c_vision_residual": float(measured["residual"]),
        "composition_observed": float(composition["observed_e2e"]),
        "composition_pred": float(composition["predicted_e2e"]),
    }


def open_images(paths: list[str]) -> list[Image.Image]:
    return [Image.open(REPO_ROOT / path).convert("RGB") for path in paths]


def candidate_short_name(candidate: dict[str, Any]) -> str:
    return f"r{candidate['assets']['rank']:02d}_{candidate['video_id']}_{candidate['start_s']:.1f}s"


def draw_headline(ax: plt.Axes, candidate: dict[str, Any]) -> None:
    label(ax, 0.045, 0.962, "Video is mostly the same.", fs=14.6, weight="bold")
    label(ax, 0.045, 0.918, "Stop paying twice.", fs=14.6, color=THEME.waste, weight="bold")


def frame_slots(x: float, y: float, w: float, h: float, n: int) -> list[tuple[float, float, float, float]]:
    gap = 0.012
    fw = (w - gap * (n - 1)) / n
    return [(x + idx * (fw + gap), y, fw, h) for idx in range(n)]


def draw_frame_strip(
    ax: plt.Axes,
    candidate: dict[str, Any],
    *,
    variant: str,
    x: float = 0.045,
    y: float = 0.685,
    w: float = 0.575,
    h: float = 0.145,
) -> None:
    assets = candidate["assets"]
    images = open_images(assets["frames"])
    slots = frame_slots(x, y, w, h, len(images))
    label(ax, x, y + h + 0.027, "real sampled frames", fs=7.7, weight="bold")
    label(
        ax,
        x,
        y + h + 0.010,
        (
            f"{candidate['benchmark'].upper()} planner example · {candidate['item_id']} · "
            "fixed-backend routing reuse, not C-PERSIST timing"
        ),
        fs=4.55,
        color=THEME.muted,
    )
    for idx, (image, slot) in enumerate(zip(images, slots, strict=True)):
        sx, sy, sw, sh = slot
        if variant == "ghost":
            alpha = 0.45 if idx < len(images) - 1 else 1.0
            draw_raster_frame(ax, image, sx + idx * 0.006, sy - idx * 0.006, sw, sh, alpha=alpha, z=2 + idx)
        else:
            draw_raster_frame(ax, image, sx, sy, sw, sh, z=2)
        if variant in {"clean", "inset"} and idx > 0:
            boxes = assets["transitions"][idx - 1]["highlight_boxes"]
            draw_highlight_regions(ax, sx, sy, sw, sh, boxes, alpha=0.13, lw=0.8)
        label(ax, sx + sw / 2, sy - 0.014, f"t{idx}", fs=5.2, color=THEME.muted, ha="center")
    if variant == "bars":
        for idx in range(1, len(images)):
            sx, sy, sw, _ = slots[idx]
            transition = assets["transitions"][idx - 1]
            reuse = float(transition["reuse_ratio_active"])
            reuse_bar(ax, sx, sy - 0.033, sw, 0.012, reuse)
            label(ax, sx + sw / 2, sy - 0.047, f"{reuse:.0%} reused", fs=4.8, color=THEME.muted, ha="center")
    if variant == "inset":
        draw_truth_inset(ax, candidate, 0.505, 0.622, 0.115, 0.115)
    if variant == "ghost":
        label(ax, x + 0.08, y - 0.044, "persistent visual state", fs=6.1, color=THEME.cache, weight="bold")
        ax.plot([x + 0.03, x + 0.43], [y - 0.022, y - 0.022], color=THEME.cache, lw=1.8)
        label(ax, x + 0.455, y - 0.022, "repair local tail", fs=6.1, color=THEME.fresh, weight="bold")


def draw_truth_inset(ax: plt.Axes, candidate: dict[str, Any], x: float, y: float, w: float, h: float) -> None:
    assets = candidate["assets"]
    images = open_images([assets["frames"][1]])
    rounded_panel(ax, x - 0.006, y - 0.033, w + 0.012, h + 0.054, face="#ffffff", edge=THEME.faint, lw=0.7)
    draw_raster_frame(ax, images[0], x, y, w, h, z=12)
    boxes = assets["transitions"][0]["fresh_boxes"]
    draw_highlight_regions(ax, x, y, w, h, boxes, alpha=0.18, lw=0.32, z=14)
    label(ax, x + w / 2, y + h + 0.018, "exact fresh blocks", fs=4.9, color=THEME.fresh, weight="bold", ha="center")
    label(ax, x + w / 2, y - 0.018, "active blocks", fs=4.5, color=THEME.muted, ha="center")


def draw_rebuild_block(ax: plt.Axes, x: float, y: float, w: float, h: float, q: str) -> None:
    rounded_panel(ax, x, y, w, h, face=THEME.waste_soft, edge=THEME.waste, lw=0.85, radius=0.008)
    label(ax, x + 0.015, y + h * 0.67, q, fs=7.1, color=THEME.waste, weight="bold")
    label(ax, x + 0.047, y + h * 0.67, "frames", fs=5.4, color=THEME.ink)
    arrow(ax, x + 0.030, y + h * 0.40, x + w - 0.030, y + h * 0.40, color=THEME.waste, lw=0.75)
    label(ax, x + w * 0.50, y + h * 0.21, "ViT + prefix/KV", fs=5.0, color=THEME.waste, weight="bold", ha="center")


def draw_stateful_block(ax: plt.Axes, x: float, y: float, w: float, h: float, q: str, mode: str) -> None:
    if mode == "pay":
        face, edge, text = THEME.waste_soft, THEME.waste, "full ingest"
        filled, fresh_tail = 10, 10
    elif mode == "repair":
        face, edge, text = THEME.fresh_soft, THEME.fresh, "repair tail"
        filled, fresh_tail = 10, 2
    else:
        face, edge, text = THEME.cache_soft, THEME.cache, "reuse cache"
        filled, fresh_tail = 10, 1
    rounded_panel(ax, x, y, w, h, face=face, edge=edge, lw=0.85, radius=0.008)
    label(ax, x + 0.014, y + h * 0.67, q, fs=7.1, color=edge, weight="bold")
    brick_row(ax, x + 0.045, y + h * 0.52, n=10, filled=filled, fresh_tail=fresh_tail, w=w - 0.062, h=h * 0.15)
    label(ax, x + w / 2, y + h * 0.22, text, fs=5.1, color=edge, weight="bold", ha="center")


def draw_lanes(ax: plt.Axes, x: float = 0.045, y: float = 0.365, w: float = 0.575, h: float = 0.235) -> None:
    label(ax, x, y + h + 0.024, "same video, new questions", fs=7.8, weight="bold")
    label(ax, x, y + h - 0.025, "baseline VLM", fs=6.3, color=THEME.waste, weight="bold")
    label(ax, x, y + h - 0.135, "anti-recompute", fs=6.3, color=THEME.cache, weight="bold")
    block_w = 0.116
    gap = 0.030
    start_x = x + 0.145
    for idx, q in enumerate(("Q1", "Q2", "Q3")):
        bx = start_x + idx * (block_w + gap)
        draw_rebuild_block(ax, bx, y + h - 0.078, block_w, 0.070, q)
        if idx < 2:
            arrow(ax, bx + block_w + 0.006, y + h - 0.043, bx + block_w + gap - 0.006, y + h - 0.043, lw=0.7)
    for idx, (q, mode) in enumerate((("Q1", "pay"), ("Q2", "repair"), ("Q3", "reuse"))):
        bx = start_x + idx * (block_w + gap)
        draw_stateful_block(ax, bx, y + h - 0.188, block_w, 0.070, q, mode)
        if idx < 2:
            arrow(ax, bx + block_w + 0.006, y + h - 0.153, bx + block_w + gap - 0.006, y + h - 0.153, lw=0.7)
    label(ax, x + 0.145, y + 0.012, "red = pay again", fs=5.4, color=THEME.waste, weight="bold")
    label(ax, x + 0.285, y + 0.012, "green = already paid", fs=5.4, color=THEME.cache, weight="bold")
    label(ax, x + 0.455, y + 0.012, "orange = repair", fs=5.4, color=THEME.fresh, weight="bold")


def draw_token_grid(ax: plt.Axes, x: float, y: float, w: float, h: float) -> None:
    rows, cols = 3, 6
    gap = 0.003
    tw = (w - gap * (cols - 1)) / cols
    th = (h - gap * (rows - 1)) / rows
    keep = {(0, 1), (0, 4), (1, 2), (2, 3), (2, 5)}
    for r in range(rows):
        for c in range(cols):
            face = THEME.question if (r, c) in keep else "#dbeafe"
            alpha = 0.95 if (r, c) in keep else 0.35
            ax.add_patch(
                mpatches.Rectangle(
                    (x + c * (tw + gap), y + (rows - 1 - r) * (th + gap)),
                    tw,
                    th,
                    facecolor=face,
                    edgecolor="#bfdbfe",
                    lw=0.25,
                    alpha=alpha,
                    zorder=5,
                )
            )


def draw_result_cards(ax: plt.Axes, values: dict[str, Any], x: float = 0.665, y: float = 0.276, w: float = 0.290) -> None:
    # C-PERSIST hero.
    rounded_panel(ax, x, y + 0.318, w, 0.235, face="#f0fdf4", edge=THEME.cache, lw=1.0, radius=0.010)
    label(ax, x + 0.016, y + 0.523, "C-PERSIST, after ingest", fs=7.1, color=THEME.cache, weight="bold")
    label(
        ax,
        x + 0.016,
        y + 0.456,
        f"{values['c_persist_min']:.2f}-{values['c_persist_max']:.2f}x",
        fs=18.0,
        color=THEME.cache,
        weight="bold",
    )
    label(ax, x + 0.018, y + 0.412, "repaired follow-up speedup", fs=6.4, color=THEME.cache, weight="bold")
    label(
        ax,
        x + 0.018,
        y + 0.372,
        f"{values['c_persist_choice_drift']}/{values['c_persist_n']} observed paired drift",
        fs=6.4,
        color=THEME.ink,
    )
    pill(
        ax,
        x + 0.165,
        y + 0.331,
        0.102,
        0.030,
        f"raw 16f {values['raw_16f_speedup']:.1f}x",
        face="#ffffff",
        edge=THEME.cache,
        fs=5.2,
    )

    # C-VISION measured first-pass cell.
    rounded_panel(ax, x, y + 0.184, w, 0.105, face="#eff6ff", edge=THEME.question, lw=0.85, radius=0.009)
    label(ax, x + 0.016, y + 0.269, "C-VISION, fresh video", fs=6.5, color=THEME.question, weight="bold")
    label(ax, x + 0.016, y + 0.225, f"{values['c_vision_e2e']:.3f}x", fs=12.0, color=THEME.question, weight="bold")
    label(ax, x + 0.132, y + 0.229, "first-query", fs=5.4, color=THEME.question, weight="bold")
    label(ax, x + 0.132, y + 0.209, "E2E", fs=5.4, color=THEME.question, weight="bold")
    label(ax, x + 0.016, y + 0.199, f"{values['c_vision_drift']}/{values['c_vision_n']} drift · schematic mask", fs=5.1, color=THEME.muted)
    draw_token_grid(ax, x + 0.205, y + 0.205, 0.060, 0.052)

    # C-CEILING guardrail.
    rounded_panel(ax, x, y + 0.060, w, 0.095, face=THEME.guard_soft, edge=THEME.guard, lw=0.85, radius=0.009)
    label(ax, x + 0.016, y + 0.137, "C-CEILING", fs=6.5, color=THEME.guard, weight="bold")
    label(ax, x + 0.016, y + 0.112, "do not multiply local wins", fs=5.8, color=THEME.guard, weight="bold")
    label(ax, x + 0.016, y + 0.091, f"audit {values['composition_observed']:.3f}x, not a product", fs=4.9, color=THEME.muted)
    runtime_bar(
        ax,
        x + 0.016,
        y + 0.064,
        w - 0.032,
        0.021,
        [
            ("vision", values["c_vision_v_share"], THEME.question),
            ("other", 1.0 - values["c_vision_v_share"], "#94a3b8"),
        ],
        fs=4.1,
    )
    # C-STREAM note.
    rounded_panel(ax, x, y, w, 0.038, face="#faf5ff", edge=THEME.guard, lw=0.65, radius=0.008)
    label(ax, x + 0.016, y + 0.019, "C-STREAM?", fs=5.8, color=THEME.guard, weight="bold")
    label(ax, x + 0.118, y + 0.019, "native-rate target", fs=5.3, color=THEME.muted)


def draw_caption_line(ax: plt.Axes, candidate: dict[str, Any], x: float = 0.045, y: float = 0.214) -> None:
    metrics = candidate["metrics"]
    label(
        ax,
        x,
        y,
        (
            f"mined window metrics: active reuse {metrics['reuse_mean_active']:.0%} mean / "
            f"{metrics['reuse_min_active']:.0%} min, fresh {metrics['novel_fraction_mean']:.0%}, "
            f"compactness {metrics['largest_component_fraction_mean']:.0%}"
        ),
        fs=5.6,
        color=THEME.muted,
    )


def render_variant(candidate: dict[str, Any], values: dict[str, Any], out_dir: Path, variant: str) -> Path:
    hashsalt = f"codec-through-fig1-v2-{variant}-{candidate['candidate_id']}"
    fig, ax = new_canvas(hashsalt=hashsalt)
    draw_headline(ax, candidate)
    draw_frame_strip(ax, candidate, variant=variant)
    draw_lanes(ax)
    draw_result_cards(ax, values)
    stem = f"fig1_v2_{variant}_{candidate_short_name(candidate)}"
    save_figure(fig, out_dir, stem, dpi=260)
    return out_dir / f"{stem}.png"


def render_montage(png_paths: list[Path], out_dir: Path, *, columns: int = 3) -> None:
    if not png_paths:
        return
    thumbs: list[Image.Image] = []
    for path in png_paths:
        img = Image.open(path).convert("RGB")
        img.thumbnail((780, 450), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (800, 480), "white")
        canvas.paste(img, ((800 - img.width) // 2, 8))
        draw = ImageDraw.Draw(canvas)
        draw.text((12, 454), path.stem.replace("fig1_v2_", ""), fill=(71, 85, 105))
        thumbs.append(canvas)
    rows = (len(thumbs) + columns - 1) // columns
    sheet = Image.new("RGB", (800 * columns, 480 * rows), "white")
    for idx, thumb in enumerate(thumbs):
        sheet.paste(thumb, ((idx % columns) * 800, (idx // columns) * 480))
    out_dir.mkdir(parents=True, exist_ok=True)
    sheet.save(out_dir / "fig1_v2_variant_montage.png")
    sheet.save(out_dir / "fig1_v2_variant_montage.pdf")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-manifest", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--top-k", type=int, default=6)
    parser.add_argument("--candidate-id", action="append", default=[])
    parser.add_argument("--variants", default="clean,bars,inset,ghost")
    args = parser.parse_args()

    candidate_ids = set(args.candidate_id) if args.candidate_id else None
    candidates = load_candidates(args.candidate_manifest, top_k=args.top_k, candidate_ids=candidate_ids)
    values = headline_values()
    variants = [part.strip() for part in args.variants.split(",") if part.strip()]
    png_paths: list[Path] = []
    for candidate in candidates:
        for variant in variants:
            png_paths.append(render_variant(candidate, values, args.out_dir, variant))
    render_montage(png_paths, args.out_dir)
    print(f"rendered {len(png_paths)} variants to {safe_rel(args.out_dir)}")
    print(f"wrote {safe_rel(args.out_dir / 'fig1_v2_variant_montage.png')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
