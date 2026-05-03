#!/usr/bin/env python3
"""Render supporting Figure 1 review views that are too detailed for Figure 1."""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path
from typing import Any


def _find_manuscript_root() -> Path:
    """Support both the repo tree and the flattened arXiv source bundle."""

    here = Path(__file__).resolve()
    for parent in (here.parent, *here.parents):
        if (parent / "main.tex").exists() and (parent / "generated").exists():
            return parent
        nested = parent / "paper" / "arxiv"
        if (nested / "main.tex").exists() and (nested / "generated").exists():
            return nested
    return here.parents[1]


MANUSCRIPT_ROOT = _find_manuscript_root()
REPO_ROOT = (
    MANUSCRIPT_ROOT.parents[1]
    if MANUSCRIPT_ROOT.name == "arxiv" and MANUSCRIPT_ROOT.parent.name == "paper"
    else MANUSCRIPT_ROOT
)
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

os.environ.setdefault("MPLCONFIGDIR", str(REPO_ROOT / ".tmp" / "matplotlib"))

import matplotlib.patches as mpatches  # noqa: E402
from fig1_primitives import (  # noqa: E402
    THEME,
    arrow,
    brick_row,
    draw_highlight_regions,
    draw_raster_frame,
    label,
    new_canvas,
    reuse_bar,
    rounded_panel,
    runtime_bar,
    save_figure,
)
from PIL import Image  # noqa: E402

GENERATED = MANUSCRIPT_ROOT / "generated"
DEFAULT_CANDIDATES = GENERATED / "figures" / "fig1_candidates" / "planner_selected_candidates.json"
DEFAULT_OUT = GENERATED / "figures" / "fig1_appendix_broadened"
HEADLINE_SNAPSHOT = GENERATED / "data" / "headline_snapshot.json"
CEILING_DATA = GENERATED / "data" / "v_share_v_red_ceiling_data.json"


def safe_rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def resolve_asset_path(path: str) -> Path:
    rel = Path(path)
    candidates = [REPO_ROOT / rel, MANUSCRIPT_ROOT / rel]
    prefix = Path("paper") / "arxiv"
    if len(rel.parts) >= 2 and Path(*rel.parts[:2]) == prefix:
        stripped = Path(*rel.parts[2:])
        candidates.extend([MANUSCRIPT_ROOT / stripped, REPO_ROOT / stripped])
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def load_candidates(path: Path, top_k: int, candidate_ids: set[str] | None) -> list[dict[str, Any]]:
    candidates = load_json(path)["candidates"]
    if candidate_ids:
        candidates = [
            candidate for candidate in candidates if candidate["candidate_id"] in candidate_ids
        ]
    return candidates[:top_k]


def load_candidate_pool(
    paths: list[Path],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any] | None]:
    pool: dict[str, dict[str, Any]] = {}
    policy: dict[str, Any] | None = None
    for path in paths:
        data = load_json(path)
        policy = policy or data.get("visualization_policy")
        for candidate in data.get("candidates", []):
            pool.setdefault(str(candidate["candidate_id"]), candidate)
    return pool, policy


def require_candidate(pool: dict[str, dict[str, Any]], candidate_id: str) -> dict[str, Any]:
    if candidate_id not in pool:
        available = ", ".join(sorted(pool)[:8])
        raise KeyError(f"candidate {candidate_id!r} not found; examples include {available}")
    return pool[candidate_id]


def write_selected_manifest(
    candidates: list[dict[str, Any]], policy: dict[str, Any] | None, path: Path
) -> None:
    seen: set[str] = set()
    selected = []
    for candidate in candidates:
        candidate_id = str(candidate["candidate_id"])
        if candidate_id in seen:
            continue
        seen.add(candidate_id)
        selected.append(candidate)
    payload: dict[str, Any] = {
        "description": (
            "Selected checked derivative assets used by the publication/review planner "
            "appendix figures."
        ),
        "candidates": selected,
    }
    if policy is not None:
        normalized_policy = dict(policy)
        purpose = str(normalized_policy.get("purpose", ""))
        if "Track-A" in purpose or "Track A" in purpose:
            normalized_policy["purpose"] = (
                "Selected candidate windows are rendered with the audited Qwen "
                "routing-budget visualization policy; source_jsonl only supplies "
                "the video path and row metadata."
            )
        payload["visualization_policy"] = normalized_policy
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def open_images(paths: list[str]) -> list[Image.Image]:
    return [Image.open(resolve_asset_path(path)).convert("RGB") for path in paths]


def headline_values() -> dict[str, Any]:
    snapshot = load_json(HEADLINE_SNAPSHOT)
    repair = snapshot["selective_reprefill"]["adaptive"]
    measured = snapshot["measured_sparse_execution"]["gemma_32f_short"]
    qwen_16f = next(
        row for row in snapshot["persistent_kv"]["rows"] if int(row["frame_count"]) == 16
    )
    composition = load_json(CEILING_DATA)["composition_cells"][0]
    return {
        "persist_min": float(repair["speedup_min"]),
        "persist_max": float(repair["speedup_max"]),
        "persist_drift": int(repair["paired_choice_diffs"]),
        "persist_n": int(repair["n_pairs"]),
        "raw_16f": float(qwen_16f["speedup"]),
        "vision_e2e": float(measured["observed_e2e"]),
        "vision_n": int(measured["n"]),
        "vision_v_share": float(measured["vision_share_dense"]),
        "vision_v_red": float(measured["vision_reduction"]),
        "composition_observed": float(composition["observed_e2e"]),
        "composition_pred": float(composition["predicted_e2e"]),
    }


def frame_slots(
    x: float, y: float, w: float, h: float, n: int
) -> list[tuple[float, float, float, float]]:
    gap = 0.012
    fw = (w - gap * (n - 1)) / n
    return [(x + idx * (fw + gap), y, fw, h) for idx in range(n)]


def draw_image_row(
    ax,
    title: str,
    images: list[Image.Image],
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    color: str = THEME.ink,
) -> list[tuple[float, float, float, float]]:
    label(ax, x, y + h / 2, title, fs=6.2, color=color, weight="bold", va="center")
    slots = frame_slots(x + 0.145, y, w - 0.145, h, len(images))
    for image, slot in zip(images, slots, strict=True):
        draw_raster_frame(ax, image, *slot, z=2)
    return slots


def _benchmark_label(candidate: dict[str, Any]) -> str:
    benchmark = str(candidate["benchmark"])
    return {"tomato": "TOMATO", "videomme": "VideoMME", "mvbench": "MVBench"}.get(
        benchmark, benchmark.upper()
    )


def _box_fraction(boxes: list[list[float]] | list[tuple[float, float, float, float]]) -> float:
    return float(sum(max(0.0, x1 - x0) * max(0.0, y1 - y0) for x0, y0, x1, y1 in boxes))


def _fresh_policy_note(candidate: dict[str, Any]) -> str:
    transitions = candidate["assets"].get("transitions", [])
    stale_values = []
    for transition in transitions:
        if "stale_fraction_active" in transition:
            stale_values.append(float(transition["stale_fraction_active"]))
        else:
            stale_values.append(_box_fraction(transition.get("stale_boxes", [])))
    stale_mean = sum(stale_values) / max(1, len(stale_values))
    if stale_mean <= 1e-9:
        age_note = "no age-expired refresh in this window"
    else:
        age_note = f"age-expired refresh avg {stale_mean:.1%}"
    return (
        f"max_abs thresholds 8/32; reused = static+shifted; fresh = novel+age-expired; {age_note}"
    )


def image_row(
    ax,
    title: str,
    images: list[Image.Image],
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    color: str = THEME.ink,
    subtitle: str | None = None,
) -> list[tuple[float, float, float, float]]:
    label(ax, x, y + h * 0.63, title, fs=6.1, color=color, weight="bold", va="center")
    if subtitle:
        label(ax, x, y + h * 0.31, subtitle, fs=4.9, color=THEME.muted, va="center")
    slots = frame_slots(x + 0.155, y, w - 0.155, h, len(images))
    for image, slot in zip(images, slots, strict=True):
        draw_raster_frame(ax, image, *slot, z=2)
    return slots


def legend_swatch(ax, x: float, y: float, text: str, color: str) -> None:
    ax.add_patch(
        mpatches.Rectangle(
            (x, y - 0.007), 0.016, 0.014, facecolor=color, edgecolor="none", zorder=10
        )
    )
    label(ax, x + 0.021, y, text, fs=5.2, color=THEME.muted, va="center")


def transition_stats(transition: dict[str, Any]) -> tuple[float, float, float]:
    reuse = float(transition.get("reuse_ratio_active", 0.0))
    fresh = float(
        transition.get(
            "fresh_fraction_active", transition.get("novel_fraction_active", 1.0 - reuse)
        )
    )
    stale = float(transition.get("stale_fraction_active", 0.0))
    return reuse, fresh, stale


def budget_percent_pair(reuse: float) -> tuple[int, int]:
    """Integer labels for figure cards; displayed reuse + fresh sums to 100."""

    reuse_pct = int(math.floor(max(0.0, min(1.0, reuse)) * 100.0 + 0.5))
    return reuse_pct, 100 - reuse_pct


def class_composition_line(transition: dict[str, Any]) -> str:
    static = len(transition.get("static_boxes", []))
    shifted = len(transition.get("shifted_boxes", []))
    fresh = len(transition.get("fresh_boxes", []))
    total = max(1, static + shifted + fresh)
    static_pct = int(math.floor(static / total * 100.0 + 0.5))
    shifted_pct = int(math.floor(shifted / total * 100.0 + 0.5))
    fresh_pct = max(0, 100 - static_pct - shifted_pct)
    return f"static {static_pct}% + shifted {shifted_pct}% → reused; fresh {fresh_pct}%"


def average_reuse(candidate: dict[str, Any]) -> float:
    transitions = candidate["assets"].get("transitions", [])
    if not transitions:
        return 0.0
    return sum(transition_stats(transition)[0] for transition in transitions) / len(transitions)


def average_fresh(candidate: dict[str, Any]) -> float:
    transitions = candidate["assets"].get("transitions", [])
    if not transitions:
        return 0.0
    return sum(transition_stats(transition)[1] for transition in transitions) / len(transitions)


def most_fresh_transition_index(candidate: dict[str, Any]) -> int:
    transitions = candidate["assets"].get("transitions", [])
    if not transitions:
        return 0
    return max(range(len(transitions)), key=lambda idx: transition_stats(transitions[idx])[1])


def candidate_heading(candidate: dict[str, Any]) -> str:
    return f"{_benchmark_label(candidate)} {candidate['video_id']}"


def draw_class_overlay(
    ax,
    image: Image.Image,
    x: float,
    y: float,
    w: float,
    h: float,
    transition: dict[str, Any],
    *,
    z: int = 2,
) -> None:
    draw_raster_frame(ax, image, x, y, w, h, z=z)
    for boxes, fill, edge, alpha, lw in [
        (transition.get("static_boxes", []), THEME.cache, THEME.cache, 0.045, 0.05),
        (transition.get("shifted_boxes", []), "#eab308", "#a16207", 0.075, 0.08),
        (transition.get("fresh_boxes", []), "#ff5a1f", "#b42318", 0.460, 0.42),
    ]:
        draw_highlight_regions(
            ax, x, y, w, h, boxes, fill=fill, edge=edge, alpha=alpha, lw=lw, z=z + 3
        )


def render_planner_trace(candidate: dict[str, Any], out_dir: Path) -> None:
    """Explain one actual Qwen routing-budget decision on real frames."""

    fig, ax = new_canvas(
        figsize=(7.45, 3.10), hashsalt=f"codec-through-planner-trace-{candidate['candidate_id']}"
    )
    assets = candidate["assets"]
    frames = open_images(assets["frames"])
    transition = assets["transitions"][0]
    reuse, fresh, stale = transition_stats(transition)

    label(ax, 0.045, 0.955, "Qwen routing-budget trace: how to read it", fs=14.0, weight="bold")
    label(
        ax,
        0.045,
        0.902,
        (
            "This visualizes the effective fresh-frame budget behind the Section 6 "
            "Qwen routing frontier."
        ),
        fs=7.0,
        color=THEME.muted,
    )
    label(ax, 0.045, 0.835, "One transition: what the planner decides", fs=10.0, weight="bold")
    label(
        ax,
        0.045,
        0.796,
        (
            f"{candidate_heading(candidate)} · "
            f"{candidate['start_s']:.2f}-{candidate['end_s']:.2f}s · "
            "max_abs thresholds 8/32"
        ),
        fs=6.3,
        color=THEME.muted,
    )

    y = 0.548
    h = 0.155
    w = 0.205
    xs = [0.045, 0.290, 0.535]
    labels = ["previous frame", "current frame", "planner classes"]
    for idx, (x, title) in enumerate(zip(xs, labels, strict=True)):
        label(ax, x, y + h + 0.030, title, fs=6.4, color=THEME.muted)
        if idx < 2:
            draw_raster_frame(ax, frames[idx], x, y, w, h, z=2)
        else:
            draw_class_overlay(ax, frames[1], x, y, w, h, transition)
        if idx < 2:
            arrow(ax, x + w + 0.012, y + h / 2, xs[idx + 1] - 0.014, y + h / 2, lw=1.0)
    arrow(ax, xs[2] + w + 0.012, y + h / 2, 0.765, y + h / 2, lw=1.0)

    card_x, card_y, card_w, card_h = 0.775, 0.535, 0.180, 0.185
    rounded_panel(
        ax, card_x, card_y, card_w, card_h, face="#ffffff", edge=THEME.faint, lw=1.2, radius=0.008
    )
    label(
        ax,
        card_x + 0.018,
        card_y + card_h - 0.042,
        f"{reuse:.0%} reused",
        fs=9.4,
        color=THEME.cache,
        weight="bold",
    )
    label(
        ax,
        card_x + 0.018,
        card_y + card_h - 0.082,
        f"{fresh:.0%} fresh",
        fs=8.7,
        color=THEME.fresh,
        weight="bold",
    )
    label(
        ax,
        card_x + 0.018,
        card_y + card_h - 0.121,
        f"age-expired: {stale:.0%}",
        fs=6.1,
        color=THEME.muted,
    )
    reuse_bar(ax, card_x + 0.020, card_y + 0.030, card_w - 0.040, 0.012, reuse)

    legend_y = 0.385
    legend_swatch(ax, 0.045, legend_y, "static: reused", THEME.cache)
    legend_swatch(ax, 0.222, legend_y, "shifted: reused", "#eab308")
    legend_swatch(ax, 0.405, legend_y, "fresh: bought", THEME.fresh)
    label(
        ax,
        0.045,
        0.255,
        "Rule: reused = static + shifted while age < 4; fresh = novel + age-expired.",
        fs=7.0,
        color=THEME.ink,
        weight="bold",
    )
    label(
        ax,
        0.045,
        0.195,
        (
            "This is a freshness budget for the fixed-backend routing result, "
            "not object localization or KV-cache timing."
        ),
        fs=6.5,
        color=THEME.muted,
    )
    save_figure(fig, out_dir, "planner_trace_real_clip", dpi=260)


def render_planner_examples_gallery(candidates: list[dict[str, Any]], out_dir: Path) -> None:
    """Show the same planner policy across a few real windows."""

    fig, ax = new_canvas(figsize=(7.45, 4.55), hashsalt="codec-through-planner-examples-gallery-v3")
    label(
        ax,
        0.045,
        0.955,
        "Qwen routing examples: same rule, different budgets",
        fs=12.8,
        weight="bold",
    )
    label(
        ax,
        0.045,
        0.908,
        (
            "Each row shows how active-region blocks become reused/fresh budget "
            "for the Section 6 routing frontier."
        ),
        fs=6.8,
        color=THEME.muted,
    )
    label(ax, 0.245, 0.835, "previous frame", fs=5.8, color=THEME.muted)
    label(ax, 0.430, 0.835, "planner classes on current frame", fs=5.8, color=THEME.muted)
    label(ax, 0.700, 0.835, "window decision budget", fs=5.8, color=THEME.muted)

    row_ys = [0.655, 0.405, 0.155]
    image_w = 0.160
    image_h = 0.092
    for row_idx, (candidate, y) in enumerate(zip(candidates, row_ys, strict=True)):
        frames = open_images(candidate["assets"]["frames"])
        transitions = candidate["assets"]["transitions"]
        avg_reuse = average_reuse(candidate)
        avg_fresh = average_fresh(candidate)
        fresh_idx = most_fresh_transition_index(candidate)
        shown_reuse, shown_fresh, shown_stale = transition_stats(transitions[fresh_idx])

        role = ["high reuse", "paper anchor", "lower reuse"][row_idx]
        label(ax, 0.045, y + 0.092, candidate_heading(candidate), fs=8.3, weight="bold")
        label(ax, 0.045, y + 0.058, role, fs=5.8, color=THEME.muted)
        label(
            ax,
            0.045,
            y + 0.029,
            f"{candidate['start_s']:.2f}-{candidate['end_s']:.2f}s",
            fs=5.7,
            color=THEME.muted,
        )

        prev_x = 0.245
        class_x = 0.430
        draw_raster_frame(ax, frames[fresh_idx], prev_x, y + 0.020, image_w, image_h, z=2)
        arrow(ax, prev_x + image_w + 0.006, y + 0.066, class_x - 0.006, y + 0.066, lw=0.85)
        draw_class_overlay(
            ax, frames[fresh_idx + 1], class_x, y + 0.020, image_w, image_h, transitions[fresh_idx]
        )

        card_x, card_y, card_w, card_h = 0.660, y + 0.002, 0.285, 0.132
        rounded_panel(
            ax,
            card_x,
            card_y,
            card_w,
            card_h,
            face="#ffffff",
            edge=THEME.faint,
            lw=0.9,
            radius=0.008,
        )
        label(
            ax,
            card_x + 0.020,
            card_y + card_h - 0.033,
            f"{avg_reuse:.0%} reused",
            fs=8.0,
            color=THEME.cache,
            weight="bold",
        )
        label(
            ax,
            card_x + card_w - 0.020,
            card_y + card_h - 0.033,
            f"{avg_fresh:.0%} fresh",
            fs=8.0,
            color=THEME.fresh,
            weight="bold",
            ha="right",
        )
        reuse_bar(ax, card_x + 0.020, card_y + 0.056, card_w - 0.040, 0.020, avg_reuse)
        label(
            ax,
            card_x + 0.020,
            card_y + 0.026,
            (
                f"shown transition: {shown_reuse:.0%} reused / "
                f"{shown_fresh:.0%} fresh; age-expired {shown_stale:.0%}"
            ),
            fs=4.9,
            color=THEME.muted,
        )

    legend_swatch(ax, 0.045, 0.055, "static/shifted reused", THEME.cache)
    legend_swatch(ax, 0.245, 0.055, "fresh bought", "#ff5a1f")
    label(
        ax,
        0.555,
        0.055,
        "Class overlays are audit views; budget cards are readable summaries.",
        fs=6.2,
        color=THEME.muted,
    )
    save_figure(fig, out_dir, "planner_examples_gallery", dpi=260)


def render_routing_budget_combined(candidates: list[dict[str, Any]], out_dir: Path) -> None:
    """Publication appendix figure: one trace plus three real-window examples."""

    fig, ax = new_canvas(
        figsize=(7.45, 4.65),
        hashsalt="codec-through-routing-budget-combined-v2",
    )
    label(ax, 0.040, 0.965, "Qwen routing-budget visualized", fs=12.0, weight="bold")
    label(
        ax,
        0.040,
        0.925,
        (
            "A fixed-backend routing example: block classes become a reused/fresh "
            "visual budget, not a speedup claim."
        ),
        fs=6.1,
        color=THEME.muted,
    )

    # Panel A: one transition trace.
    trace = candidates[0]
    frames = open_images(trace["assets"]["frames"])
    transition = trace["assets"]["transitions"][0]
    reuse, _, stale = transition_stats(transition)
    reuse_pct, fresh_pct = budget_percent_pair(reuse)

    label(
        ax,
        0.040,
        0.855,
        "A. One real transition: planner rule → decision budget",
        fs=8.0,
        weight="bold",
    )
    y = 0.665
    h = 0.104
    w = 0.160
    xs = [0.040, 0.250, 0.460]
    for x, title in zip(xs, ["previous", "current", "classes"], strict=True):
        label(ax, x, y + h + 0.024, title, fs=5.5, color=THEME.muted)
    draw_raster_frame(ax, frames[0], xs[0], y, w, h, z=2)
    arrow(ax, xs[0] + w + 0.011, y + h / 2, xs[1] - 0.012, y + h / 2, lw=0.85)
    draw_raster_frame(ax, frames[1], xs[1], y, w, h, z=2)
    arrow(ax, xs[1] + w + 0.011, y + h / 2, xs[2] - 0.012, y + h / 2, lw=0.85)
    draw_class_overlay(ax, frames[1], xs[2], y, w, h, transition)
    arrow(ax, xs[2] + w + 0.012, y + h / 2, 0.685, y + h / 2, lw=0.85)

    card_x, card_y, card_w, card_h = 0.700, 0.642, 0.255, 0.150
    rounded_panel(
        ax,
        card_x,
        card_y,
        card_w,
        card_h,
        face="#ffffff",
        edge=THEME.faint,
        lw=1.0,
        radius=0.008,
    )
    label(
        ax,
        card_x + 0.018,
        card_y + card_h - 0.034,
        f"{reuse_pct}% reused",
        fs=9.6,
        color=THEME.cache,
        weight="bold",
    )
    label(
        ax,
        card_x + 0.018,
        card_y + card_h - 0.069,
        f"{fresh_pct}% fresh",
        fs=8.6,
        color=THEME.fresh,
        weight="bold",
    )
    label(
        ax,
        card_x + 0.018,
        card_y + card_h - 0.098,
        f"age-expired: {int(round(stale * 100))}%",
        fs=5.5,
        color=THEME.muted,
    )
    reuse_bar(ax, card_x + 0.018, card_y + 0.024, card_w - 0.036, 0.012, reuse)

    label(
        ax,
        0.040,
        0.617,
        class_composition_line(transition),
        fs=5.8,
        color=THEME.ink,
        weight="bold",
    )
    label(
        ax,
        0.040,
        0.586,
        "Rule: reused = static + shifted while age < 4; fresh = novel + age-expired.",
        fs=5.8,
        color=THEME.ink,
    )
    legend_swatch(ax, 0.040, 0.552, "static / shifted reused", THEME.cache)
    legend_swatch(ax, 0.255, 0.552, "fresh bought", THEME.fresh)
    label(
        ax,
        0.520,
        0.552,
        "Block classes are freshness evidence; object relevance is still decided "
        "by the model/task.",
        fs=5.15,
        color=THEME.muted,
    )

    # Panel B: examples gallery.
    label(ax, 0.040, 0.493, "B. Same policy on three real windows", fs=8.0, weight="bold")
    label(
        ax,
        0.040,
        0.465,
        (
            "Selected real windows rendered with the same routing policy; budgets are "
            "visualization summaries, not speedup claims."
        ),
        fs=5.8,
        color=THEME.muted,
    )
    label(ax, 0.285, 0.430, "previous", fs=5.2, color=THEME.muted)
    label(ax, 0.445, 0.430, "classes", fs=5.2, color=THEME.muted)
    label(ax, 0.695, 0.430, "window average", fs=5.2, color=THEME.muted)

    row_ys = [0.328, 0.198, 0.068]
    roles = ["high-reuse routing example", "VideoMME visual anchor", "lower-reuse boundary"]
    for row_idx, (candidate, row_y) in enumerate(zip(candidates, row_ys, strict=True)):
        frames = open_images(candidate["assets"]["frames"])
        transitions = candidate["assets"]["transitions"]
        fresh_idx = most_fresh_transition_index(candidate)
        avg_reuse = average_reuse(candidate)
        avg_reuse_pct, avg_fresh_pct = budget_percent_pair(avg_reuse)
        shown_reuse, _, shown_stale = transition_stats(transitions[fresh_idx])
        shown_reuse_pct, shown_fresh_pct = budget_percent_pair(shown_reuse)

        label(ax, 0.040, row_y + 0.071, candidate_heading(candidate), fs=7.0, weight="bold")
        label(ax, 0.040, row_y + 0.044, roles[row_idx], fs=5.2, color=THEME.muted)
        label(
            ax,
            0.040,
            row_y + 0.021,
            f"{candidate['start_s']:.2f}-{candidate['end_s']:.2f}s",
            fs=5.0,
            color=THEME.muted,
        )

        draw_raster_frame(ax, frames[fresh_idx], 0.285, row_y + 0.010, 0.120, 0.064, z=2)
        arrow(ax, 0.410, row_y + 0.042, 0.435, row_y + 0.042, lw=0.75)
        draw_class_overlay(
            ax,
            frames[fresh_idx + 1],
            0.445,
            row_y + 0.010,
            0.120,
            0.064,
            transitions[fresh_idx],
        )

        card_x, card_y, card_w, card_h = 0.675, row_y, 0.280, 0.096
        rounded_panel(
            ax,
            card_x,
            card_y,
            card_w,
            card_h,
            face="#ffffff",
            edge=THEME.faint,
            lw=0.85,
            radius=0.007,
        )
        label(
            ax,
            card_x + 0.020,
            card_y + card_h - 0.025,
            f"{avg_reuse_pct}% reused",
            fs=7.1,
            color=THEME.cache,
            weight="bold",
        )
        label(
            ax,
            card_x + card_w - 0.020,
            card_y + card_h - 0.025,
            f"{avg_fresh_pct}% fresh",
            fs=7.1,
            color=THEME.fresh,
            weight="bold",
            ha="right",
        )
        reuse_bar(ax, card_x + 0.020, card_y + 0.042, card_w - 0.040, 0.011, avg_reuse)
        label(
            ax,
            card_x + 0.020,
            card_y + 0.026,
            f"shown transition: {shown_reuse_pct}% / {shown_fresh_pct}%",
            fs=4.8,
            color=THEME.muted,
        )
        label(
            ax,
            card_x + 0.020,
            card_y + 0.011,
            f"age-expired: {int(round(shown_stale * 100))}%",
            fs=4.8,
            color=THEME.muted,
        )

    save_figure(fig, out_dir, "qwen_routing_budget_visualized", dpi=260)


def render_algorithm_comparison(candidate: dict[str, Any], out_dir: Path) -> None:
    fig, ax = new_canvas(
        figsize=(7.45, 5.45), hashsalt=f"codec-through-fig1-appendix-{candidate['candidate_id']}"
    )
    assets = candidate["assets"]
    frames = open_images(assets["frames"])
    exact = open_images(assets["exact_overlays"])

    label(ax, 0.045, 0.963, "Qwen routing-budget visualization", fs=12.8, weight="bold")
    label(
        ax,
        0.045,
        0.922,
        (
            f"{_benchmark_label(candidate)} {candidate['video_id']} · "
            f"{candidate['start_s']:.2f}-{candidate['end_s']:.2f}s · "
            "fixed-backend routing view only"
        ),
        fs=6.1,
        color=THEME.muted,
    )
    label(ax, 0.045, 0.895, _fresh_policy_note(candidate), fs=5.1, color=THEME.muted)

    image_row(ax, "clean frames", frames, 0.045, 0.750, 0.905, 0.105)
    slots = image_row(
        ax,
        "fresh blocks",
        frames,
        0.045,
        0.595,
        0.905,
        0.105,
        color=THEME.fresh,
        subtitle="block budget; not localization",
    )
    for idx in range(1, len(frames)):
        sx, sy, sw, sh = slots[idx]
        draw_highlight_regions(
            ax,
            sx,
            sy,
            sw,
            sh,
            assets["transitions"][idx - 1].get("fresh_boxes", []),
            fill="#ff5a1f",
            edge="#ff5a1f",
            alpha=0.25,
            lw=0.0,
        )

    slots = image_row(ax, "reuse bars", frames, 0.045, 0.440, 0.905, 0.105, color=THEME.cache)
    legend_swatch(ax, 0.205, 0.414, "reused", THEME.cache)
    legend_swatch(ax, 0.300, 0.414, "fresh", "#ff5a1f")
    for idx in range(1, len(frames)):
        sx, sy, sw, _ = slots[idx]
        reuse = float(assets["transitions"][idx - 1]["reuse_ratio_active"])
        reuse_bar(ax, sx, sy - 0.022, sw, 0.010, reuse)
        label(
            ax,
            sx + sw / 2,
            sy - 0.038,
            f"{reuse:.0%} reused",
            fs=4.8,
            color=THEME.muted,
            ha="center",
        )

    image_row(
        ax,
        "audit grid",
        exact,
        0.045,
        0.245,
        0.905,
        0.105,
        color=THEME.waste,
        subtitle="exact block classes",
    )

    # One class-aware transition inset: static and shifted are reusable; fresh is bought.
    label(ax, 0.045, 0.190, "one transition: planner classes", fs=6.0, weight="bold")
    inset_x, inset_y, inset_w, inset_h = 0.245, 0.060, 0.155, 0.115
    draw_raster_frame(ax, frames[1], inset_x, inset_y, inset_w, inset_h, z=2)
    transition = assets["transitions"][0]
    for boxes, fill, edge, alpha in [
        (transition["static_boxes"], THEME.cache, THEME.cache, 0.07),
        (transition["shifted_boxes"], "#eab308", "#a16207", 0.10),
        (transition["fresh_boxes"], "#ff5a1f", "#b42318", 0.46),
    ]:
        draw_highlight_regions(
            ax,
            inset_x,
            inset_y,
            inset_w,
            inset_h,
            boxes,
            fill=fill,
            edge=edge,
            alpha=alpha,
            lw=0.16,
        )
    legend_swatch(ax, 0.430, 0.145, "static: reused", THEME.cache)
    legend_swatch(ax, 0.430, 0.112, "shifted: reused", "#eab308")
    legend_swatch(ax, 0.430, 0.079, "fresh: bought", "#ff5a1f")
    label(
        ax,
        0.620,
        0.118,
        "fixed-backend routing budget, not a KV-cache timing claim",
        fs=5.7,
        color=THEME.muted,
    )

    safe_video = "".join(ch if ch.isalnum() else "_" for ch in str(candidate["video_id"]))
    stem = f"planner_visualization_{candidate['benchmark']}_{safe_video}_r{assets['rank']:02d}"
    if str(candidate["benchmark"]) == "tomato" and str(candidate["video_id"]) == "0298-00":
        stem = "planner_visualization_tomato_0298_00"
    save_figure(fig, out_dir, stem, dpi=260)


def draw_token_grid(ax, x: float, y: float, w: float, h: float) -> None:
    rows, cols = 4, 7
    gap = 0.0026
    tw = (w - gap * (cols - 1)) / cols
    th = (h - gap * (rows - 1)) / rows
    keep = {(0, 2), (0, 5), (1, 1), (1, 4), (2, 3), (3, 0), (3, 5)}
    for r in range(rows):
        for c in range(cols):
            face = THEME.question if (r, c) in keep else THEME.question_soft
            alpha = 0.95 if (r, c) in keep else 0.30
            ax.add_patch(
                mpatches.Rectangle(
                    (x + c * (tw + gap), y + (rows - 1 - r) * (th + gap)),
                    tw,
                    th,
                    facecolor=face,
                    edgecolor="#bfdbfe",
                    lw=0.25,
                    alpha=alpha,
                    zorder=3,
                )
            )


def render_regime_matrix(values: dict[str, Any], out_dir: Path) -> None:
    fig, ax = new_canvas(figsize=(7.45, 4.30), hashsalt="codec-through-fig1-regime-matrix-v2")
    label(ax, 0.045, 0.955, "Support: speedup regimes are not pixel masks", fs=12.2, weight="bold")
    label(
        ax,
        0.045,
        0.914,
        (
            "Planner masks visualize routing only; C-PERSIST, C-VISION, and "
            "C-CEILING use different denominators."
        ),
        fs=6.0,
        color=THEME.muted,
    )
    cards = [
        (0.045, 0.515, 0.430, 0.300, "Baseline VLM", THEME.waste, THEME.waste_soft),
        (0.525, 0.515, 0.430, 0.300, "C-PERSIST", THEME.cache, THEME.cache_soft),
        (0.045, 0.145, 0.430, 0.300, "C-VISION", THEME.question, THEME.question_soft),
        (0.525, 0.145, 0.430, 0.300, "C-CEILING", THEME.guard, THEME.guard_soft),
    ]
    for x, y, w, h, title, edge, face in cards:
        rounded_panel(ax, x, y, w, h, face=face, edge=edge, lw=0.9, radius=0.010)
        label(ax, x + 0.018, y + h - 0.035, title, fs=7.5, color=edge, weight="bold")

    # Baseline.
    x, y, w, h = cards[0][:4]
    for idx, q in enumerate(("Q1", "Q2", "Q3")):
        bx = x + 0.038 + idx * 0.128
        rounded_panel(
            ax, bx, y + 0.105, 0.095, 0.085, face="#fff", edge=THEME.waste, lw=0.75, radius=0.007
        )
        label(ax, bx + 0.0475, y + 0.160, q, fs=6.6, color=THEME.waste, weight="bold", ha="center")
        label(ax, bx + 0.0475, y + 0.128, "rebuild", fs=5.0, color=THEME.waste, ha="center")
        if idx < 2:
            arrow(ax, bx + 0.101, y + 0.148, bx + 0.123, y + 0.148, lw=0.6)
    label(
        ax,
        x + 0.038,
        y + 0.058,
        "same visual state is paid again for every question",
        fs=5.8,
        color=THEME.muted,
    )

    # C-PERSIST.
    x, y, w, h = cards[1][:4]
    for idx, (q, action, _note) in enumerate(
        (
            ("Q1", "buy full prefix", "made"),
            ("Q2", "repair tail", "repaired"),
            ("Q3", "append question", "inherited"),
        )
    ):
        yy = y + 0.190 - idx * 0.058
        label(ax, x + 0.038, yy + 0.010, q, fs=6.2, color=THEME.cache, weight="bold")
        label(ax, x + 0.083, yy + 0.031, action, fs=4.55, color=THEME.muted)
        if q == "Q1":
            brick_row(
                ax,
                x + 0.083,
                yy,
                n=10,
                filled=10,
                fresh_tail=0,
                w=0.120,
                h=0.018,
                fill_color=THEME.fresh,
            )
            arrow(ax, x + 0.213, yy + 0.009, x + 0.248, yy + 0.009, color=THEME.cache, lw=0.55)
            brick_row(
                ax,
                x + 0.260,
                yy,
                n=10,
                filled=10,
                fresh_tail=0,
                w=0.120,
                h=0.018,
                fill_color=THEME.cache,
            )
        elif q == "Q2":
            brick_row(
                ax,
                x + 0.083,
                yy,
                n=10,
                filled=10,
                fresh_tail=2,
                w=0.120,
                h=0.018,
                fill_color=THEME.cache,
            )
            arrow(ax, x + 0.213, yy + 0.009, x + 0.248, yy + 0.009, color=THEME.cache, lw=0.55)
            brick_row(
                ax,
                x + 0.260,
                yy,
                n=10,
                filled=10,
                fresh_tail=0,
                w=0.120,
                h=0.018,
                fill_color=THEME.cache,
            )
        else:
            brick_row(
                ax,
                x + 0.083,
                yy,
                n=10,
                filled=10,
                fresh_tail=0,
                w=0.120,
                h=0.018,
                fill_color=THEME.cache,
            )
            ax.add_patch(
                mpatches.Rectangle(
                    (x + 0.214, yy),
                    0.022,
                    0.018,
                    facecolor=THEME.question,
                    edgecolor=THEME.question,
                    lw=0.35,
                    zorder=4,
                )
            )
            arrow(ax, x + 0.246, yy + 0.009, x + 0.248, yy + 0.009, color=THEME.cache, lw=0.55)
            brick_row(
                ax,
                x + 0.260,
                yy,
                n=10,
                filled=10,
                fresh_tail=0,
                w=0.120,
                h=0.018,
                fill_color=THEME.cache,
            )
    label(
        ax,
        x + 0.038,
        y + 0.046,
        (
            f"{values['persist_min']:.2f}-{values['persist_max']:.2f}x after-ingest; "
            f"{values['persist_drift']}/{values['persist_n']} paired drift"
        ),
        fs=5.7,
        color=THEME.cache,
        weight="bold",
    )

    # C-VISION.
    x, y, w, h = cards[2][:4]
    draw_token_grid(ax, x + 0.045, y + 0.108, 0.135, 0.120)
    arrow(ax, x + 0.200, y + 0.168, x + 0.255, y + 0.168, color=THEME.question, lw=0.9)
    draw_token_grid(ax, x + 0.275, y + 0.125, 0.095, 0.085)
    label(
        ax,
        x + 0.045,
        y + 0.066,
        f"{values['vision_e2e']:.3f}x first-query measured sparse vision",
        fs=5.8,
        color=THEME.question,
        weight="bold",
    )
    label(
        ax,
        x + 0.045,
        y + 0.040,
        "schematic mask: no checked per-example keep mask",
        fs=5.0,
        color=THEME.muted,
    )

    # C-CEILING / C-STREAM.
    x, y, w, h = cards[3][:4]
    runtime_bar(
        ax,
        x + 0.040,
        y + 0.185,
        0.260,
        0.030,
        [
            ("vision", values["vision_v_share"], THEME.question),
            ("other", 1.0 - values["vision_v_share"], "#94a3b8"),
        ],
        fs=4.6,
    )
    label(
        ax,
        x + 0.040,
        y + 0.146,
        f"composition audit {values['composition_observed']:.3f}x ≈ share ceiling",
        fs=5.7,
        color=THEME.guard,
        weight="bold",
    )
    label(
        ax,
        x + 0.040,
        y + 0.103,
        "C-STREAM: state updates at native rate",
        fs=5.6,
        color=THEME.guard,
        weight="bold",
    )
    label(
        ax, x + 0.040, y + 0.077, "candidate target, not headline result", fs=5.1, color=THEME.muted
    )

    save_figure(fig, out_dir, "fig1_regime_matrix_support", dpi=260)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-manifest", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--extra-candidate-manifest", type=Path, action="append", default=[])
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--candidate-id", action="append", default=[])
    parser.add_argument("--trace-candidate-id", default="0298_00_000p00_002p00_1d0e3c62")
    parser.add_argument(
        "--gallery-candidate-id",
        action="append",
        default=[],
        help=(
            "Candidate ids for planner_examples_gallery; defaults to TOMATO 0298, "
            "VideoMME 380, and VideoMME 267."
        ),
    )
    parser.add_argument(
        "--selected-manifest",
        type=Path,
        default=GENERATED / "figures" / "fig1_candidates" / "planner_selected_candidates.json",
    )
    parser.add_argument("--render-legacy-comparison", action="store_true")
    parser.add_argument(
        "--render-regime-matrix",
        action="store_true",
        help="Also render the review-only support matrix. Requires generated data snapshots.",
    )
    parser.add_argument(
        "--render-split-planner-figures",
        action="store_true",
        help="Also render the older separate trace/gallery figures for review.",
    )
    args = parser.parse_args()

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    pool, policy = load_candidate_pool([args.candidate_manifest, *args.extra_candidate_manifest])
    trace_candidate = require_candidate(pool, args.trace_candidate_id)
    gallery_ids = args.gallery_candidate_id or [
        args.trace_candidate_id,
        "380_206p39_207p89_c358a09d",
        "267_000p00_001p00_1fbfd15b",
    ]
    gallery_candidates = [require_candidate(pool, candidate_id) for candidate_id in gallery_ids]

    render_routing_budget_combined(gallery_candidates, out_dir)
    if args.render_split_planner_figures:
        render_planner_trace(trace_candidate, out_dir)
        render_planner_examples_gallery(gallery_candidates, out_dir)
    write_selected_manifest([trace_candidate, *gallery_candidates], policy, args.selected_manifest)

    if args.render_legacy_comparison:
        candidate_ids = set(args.candidate_id) if args.candidate_id else None
        candidates = load_candidates(args.candidate_manifest, args.top_k, candidate_ids)
        for candidate in candidates:
            render_algorithm_comparison(candidate, out_dir)
    if args.render_regime_matrix:
        values = headline_values()
        render_regime_matrix(values, out_dir)
    print(f"rendered appendix/support figures to {safe_rel(out_dir)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
