
"""
Toy experiments for Codec-Through-style temporal embedding reuse.

These are not benchmark replacements. They are fast synthetic stress tests
designed to illuminate failure modes and design choices:

- talking-head / conferencing regime
- parking-lot / mostly static surveillance regime
- FPV / strong egomotion regime
- robotics manipulation scene with protected task-critical ROI

The script saves:
  - JSON summary
  - markdown report
  - PNG plots
  - toy scene montage
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw

from codec_through_reference import PlannerConfig, ProtectRegion, TemporalRedundancyPlanner


OUT_DIR = Path("/mnt/data")


def smooth_noise(h: int, w: int, *, scale: int = 16, channels: int = 3, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    small = rng.random((max(1, h // scale + 2), max(1, w // scale + 2), channels))
    arr = np.kron(small, np.ones((scale, scale, 1)))[:h, :w]
    for _ in range(2):
        arr = (
            arr
            + np.roll(arr, 1, 0)
            + np.roll(arr, -1, 0)
            + np.roll(arr, 1, 1)
            + np.roll(arr, -1, 1)
        ) / 5.0
    return arr


def draw_rect(img: np.ndarray, x0: int, y0: int, x1: int, y1: int, color: np.ndarray) -> None:
    img[max(0, y0):min(img.shape[0], y1), max(0, x0):min(img.shape[1], x1)] = color


def draw_circle(img: np.ndarray, cx: int, cy: int, r: int, color: np.ndarray) -> None:
    yy, xx = np.ogrid[:img.shape[0], :img.shape[1]]
    mask = (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r
    img[mask] = color


def make_talking_head_frame(t: int, h: int = 224, w: int = 224) -> np.ndarray:
    img = smooth_noise(h, w, scale=32, seed=1) * 0.5 + 0.2
    img *= np.array([1.0, 0.95, 0.9])
    draw_rect(img, 70, 120, 154, 223, np.array([0.15, 0.2, 0.35]))
    cx = 112 + int(2 * np.sin(t / 5))
    cy = 90 + int(1 * np.sin(t / 7))
    draw_circle(img, cx, cy, 28, np.array([0.9, 0.78, 0.68]))
    draw_circle(img, cx, cy - 10, 30, np.array([0.15, 0.08, 0.04]))
    draw_circle(img, cx, cy + 3, 24, np.array([0.9, 0.78, 0.68]))
    blink = (t % 11 in [0, 1])
    eye_h = 1 if blink else 3
    draw_rect(img, cx - 12, cy - 5, cx - 4, cy - 5 + eye_h, np.array([0.05, 0.05, 0.05]))
    draw_rect(img, cx + 4, cy - 5, cx + 12, cy - 5 + eye_h, np.array([0.05, 0.05, 0.05]))
    mouth_w = 10 + int(3 * np.sin(t / 2))
    mouth_h = 2 + int((np.sin(t / 2) + 1))
    draw_rect(img, cx - mouth_w // 2, cy + 10, cx + mouth_w // 2, cy + 10 + mouth_h, np.array([0.5, 0.1, 0.15]))
    hx = 60 + int(3 * np.sin(t / 3))
    hy = 145 + int(2 * np.cos(t / 4))
    draw_circle(img, hx, hy, 8, np.array([0.9, 0.78, 0.68]))
    return np.clip(img, 0.0, 1.0)


def make_surveillance_frame(t: int, h: int = 224, w: int = 224) -> np.ndarray:
    img = smooth_noise(h, w, scale=48, seed=2) * 0.3 + 0.35
    img *= np.array([0.8, 0.85, 0.9])
    for x in [40, 90, 140, 190]:
        draw_rect(img, x, 40, x + 2, 200, np.array([0.9, 0.9, 0.7]))
    draw_rect(img, 0, 0, 224, 35, np.array([0.25, 0.25, 0.3]))
    car_positions = [(20 + t * 2, 70), (200 - t, 130)]
    colors = [np.array([0.8, 0.1, 0.1]), np.array([0.1, 0.2, 0.8])]
    for (x, y), c in zip(car_positions, colors):
        draw_rect(img, int(x), y, int(x) + 18, y + 10, c)
        draw_rect(img, int(x) + 3, y - 2, int(x) + 15, y + 3, c * 0.9 + 0.1)
    px = 110 + int(5 * np.sin(t / 3))
    py = 170
    draw_rect(img, px, py, px + 3, py + 8, np.array([0.1, 0.1, 0.1]))
    return np.clip(img, 0.0, 1.0)


def make_base_landscape(h: int = 640, w: int = 640) -> np.ndarray:
    img = smooth_noise(h, w, scale=20, seed=3) * 0.5 + 0.25
    for i in range(0, h, 24):
        img[i:i + 12] *= np.array([0.8, 1.0, 0.8])
    for x in range(0, w, 40):
        draw_rect(img, x, 0, x + 2, h, np.array([0.3, 0.4, 0.3]))
    rng = np.random.default_rng(3)
    for _ in range(60):
        cx = int(rng.integers(0, w))
        cy = int(rng.integers(0, h))
        r = int(rng.integers(3, 8))
        draw_circle(img, cx, cy, r, np.array([0.45, 0.4, 0.35]))
    return np.clip(img, 0.0, 1.0)


BASE_LAND = make_base_landscape()


def make_fpv_frame(t: int, h: int = 224, w: int = 224) -> np.ndarray:
    x = 20 + int(t * 4 + 6 * np.sin(t / 4))
    y = 10 + int(t * 3 + 4 * np.cos(t / 5))
    x = min(max(0, x), BASE_LAND.shape[1] - w)
    y = min(max(0, y), BASE_LAND.shape[0] - h)
    crop = BASE_LAND[y:y + h, x:x + w].copy()
    bx = 180 - int(7 * np.sin(t / 2))
    by = 60 + int(3 * np.cos(t / 3))
    draw_rect(crop, bx, by, bx + 20, by + 4, np.array([0.2, 0.1, 0.05]))
    ox = 50 + int(20 * np.sin(t / 5))
    oy = 150 + int(10 * np.cos(t / 3))
    draw_rect(crop, ox, oy, ox + 15, oy + 15, np.array([0.1, 0.1, 0.1]))
    return np.clip(crop, 0.0, 1.0)


def make_robot_scene_frame(t: int, h: int = 224, w: int = 224) -> Tuple[np.ndarray, Tuple[int, int], Tuple[int, int, int, int]]:
    img = smooth_noise(h, w, scale=40, seed=4) * 0.15 + 0.75
    draw_rect(img, 20, 90, 204, 200, np.array([0.68, 0.62, 0.55]))
    draw_rect(img, 10, 20, 60, 80, np.array([0.3, 0.5, 0.8]))
    draw_rect(img, 164, 20, 214, 80, np.array([0.8, 0.5, 0.3]))
    draw_rect(img, 90, 200, 134, 223, np.array([0.3, 0.3, 0.35]))
    base = (112, 200)
    theta1 = -1.3 + 0.2 * np.sin(t / 6)
    theta2 = 0.9 + 0.3 * np.sin(t / 5 + 1)
    l1 = 55
    l2 = 45
    joint = (int(base[0] + l1 * np.cos(theta1)), int(base[1] + l1 * np.sin(theta1)))
    tip = (int(joint[0] + l2 * np.cos(theta1 + theta2)), int(joint[1] + l2 * np.sin(theta1 + theta2)))

    def draw_line_thick(img: np.ndarray, p0: Tuple[int, int], p1: Tuple[int, int], width: int, color: np.ndarray) -> None:
        length = int(np.hypot(p1[0] - p0[0], p1[1] - p0[1])) + 1
        for k in range(length + 1):
            a = k / max(1, length)
            x = int(round(p0[0] * (1 - a) + p1[0] * a))
            y = int(round(p0[1] * (1 - a) + p1[1] * a))
            draw_circle(img, x, y, width, color)

    draw_line_thick(img, base, joint, 5, np.array([0.55, 0.55, 0.6]))
    draw_line_thick(img, joint, tip, 4, np.array([0.55, 0.55, 0.6]))
    draw_circle(img, tip[0], tip[1], 6, np.array([0.1, 0.1, 0.1]))
    ox = 110 + (t // 10) * 12 + int(2 * np.sin(t / 3))
    oy = 120 + int(1 * np.cos(t / 4))
    draw_rect(img, ox, oy, ox + 14, oy + 14, np.array([0.1, 0.7, 0.2]))
    return np.clip(img, 0.0, 1.0), tip, (ox, oy, ox + 14, oy + 14)


def token_mask_to_window_ratio(mask: np.ndarray, window_mask: np.ndarray) -> float:
    del mask
    return 100.0 * float(window_mask.mean())


def run_regime(planner: TemporalRedundancyPlanner, make_fn: Callable[[int], np.ndarray], *,
               n_frames: int = 30, use_local_search: bool = True, global_translation: bool = False) -> Dict[str, float]:
    static_vals: List[float] = []
    shifted_vals: List[float] = []
    novel_vals: List[float] = []
    reuse_vals: List[float] = []
    halo_vals: List[float] = []

    old_global_flag = planner.config.estimate_global_translation
    planner.config.estimate_global_translation = global_translation
    try:
        for t in range(1, n_frames):
            prev = make_fn(t - 1)
            curr = make_fn(t)
            plan = planner.plan_from_frames(prev, curr, use_local_search=use_local_search)
            static_vals.append(100.0 * plan.static_ratio)
            shifted_vals.append(100.0 * plan.shifted_ratio)
            novel_vals.append(100.0 * plan.novel_ratio)
            reuse_vals.append(100.0 * plan.reuse_ratio)
            halo_vals.append(token_mask_to_window_ratio(plan.recompute_token_mask, plan.recompute_window_mask))
    finally:
        planner.config.estimate_global_translation = old_global_flag

    return {
        "static_pct": float(np.mean(static_vals)),
        "shifted_pct": float(np.mean(shifted_vals)),
        "novel_pct": float(np.mean(novel_vals)),
        "reuse_pct": float(np.mean(reuse_vals)),
        "halo1_windows_pct": float(np.mean(halo_vals)),
    }


def run_robot_roi(planner: TemporalRedundancyPlanner, *, n_frames: int = 30, protect_radius_px: int = 24) -> pd.DataFrame:
    rows = []
    for protect in [False, True]:
        novel_vals: List[float] = []
        halo_vals: List[float] = []
        for t in range(1, n_frames):
            prev, _, _ = make_robot_scene_frame(t - 1)
            curr, tip, box = make_robot_scene_frame(t)

            protect_regions = None
            if protect:
                cx, cy = tip
                bx0, by0, bx1, by1 = box
                protect_regions = [
                    ProtectRegion(cx - protect_radius_px, cy - protect_radius_px, cx + protect_radius_px, cy + protect_radius_px),
                    ProtectRegion(bx0 - protect_radius_px // 2, by0 - protect_radius_px // 2, bx1 + protect_radius_px // 2, by1 + protect_radius_px // 2),
                ]

            plan = planner.plan_from_frames(prev, curr, protect_regions=protect_regions, use_local_search=True)
            novel_vals.append(100.0 * plan.novel_ratio)
            halo_vals.append(token_mask_to_window_ratio(plan.recompute_token_mask, plan.recompute_window_mask))
        rows.append({
            "setting": "protect gripper+object ROI" if protect else "no protected ROI",
            "novel_tokens_pct": float(np.mean(novel_vals)),
            "halo1_windows_pct": float(np.mean(halo_vals)),
        })
    return pd.DataFrame(rows)


def save_plots(df: pd.DataFrame, robot_df: pd.DataFrame) -> Dict[str, str]:
    files: Dict[str, str] = {}

    regime_order = ["talking_head", "parking_lot", "fpv_motion"]
    regime_labels = ["Talking head", "Parking lot", "FPV / egomotion"]
    method_order = ["same_position", "local_search", "global_translation"]
    offsets = {"same_position": -0.22, "local_search": 0.0, "global_translation": 0.22}
    width = 0.22
    x = np.arange(len(regime_order))

    fig = plt.figure(figsize=(10, 4.8))
    ax = fig.add_subplot(111)
    for method in method_order:
        values = []
        for regime in regime_order:
            sub = df[(df["regime"] == regime) & (df["method"] == method)]["reuse_pct"]
            values.append(sub.iloc[0] if len(sub) else np.nan)
        ax.bar(x + offsets[method], values, width=width, label=method.replace("_", " "))
    ax.set_xticks(x)
    ax.set_xticklabels(regime_labels)
    ax.set_ylabel("Reusable tokens (%)")
    ax.set_ylim(0, 105)
    ax.set_title("Toy redundancy study: token reuse by regime and method")
    ax.legend(frameon=False)
    fig.tight_layout()
    path = OUT_DIR / "codec_through_reuse_regimes.png"
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    files["reuse_regimes_png"] = str(path)

    fig = plt.figure(figsize=(10, 4.8))
    ax = fig.add_subplot(111)
    for method in method_order:
        values = []
        for regime in regime_order:
            sub = df[(df["regime"] == regime) & (df["method"] == method)]["halo1_windows_pct"]
            values.append(sub.iloc[0] if len(sub) else np.nan)
        ax.bar(x + offsets[method], values, width=width, label=method.replace("_", " "))
    ax.set_xticks(x)
    ax.set_xticklabels(regime_labels)
    ax.set_ylabel("Windows recomputed with 1-hop halo (%)")
    ax.set_ylim(0, 105)
    ax.set_title("Novelty understates real work once locality / halo are accounted for")
    ax.legend(frameon=False)
    fig.tight_layout()
    path = OUT_DIR / "codec_through_window_recompute.png"
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    files["window_recompute_png"] = str(path)

    fig = plt.figure(figsize=(6.5, 4.4))
    ax = fig.add_subplot(111)
    ax.bar(np.arange(len(robot_df)), robot_df["halo1_windows_pct"].to_numpy(), width=0.55)
    ax.set_xticks(np.arange(len(robot_df)))
    ax.set_xticklabels(robot_df["setting"].tolist())
    ax.set_ylabel("Windows recomputed with 1-hop halo (%)")
    ax.set_title("Toy robotics scene: safety ROI vs efficiency")
    ax.set_ylim(0, max(robot_df["halo1_windows_pct"]) * 1.25)
    fig.tight_layout()
    path = OUT_DIR / "codec_through_robot_roi.png"
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    files["robot_roi_png"] = str(path)

    return files


def save_scene_montage() -> str:
    frames = [
        ("Talking head", make_talking_head_frame(0)),
        ("Parking lot", make_surveillance_frame(0)),
        ("FPV / egomotion", make_fpv_frame(0)),
        ("Robot manipulation", make_robot_scene_frame(0)[0]),
    ]
    pil_frames = [Image.fromarray((np.clip(frame, 0, 1) * 255).astype(np.uint8)) for _, frame in frames]
    w, h = pil_frames[0].size
    canvas = Image.new("RGB", (2 * w, 2 * h + 50), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    positions = [(0, 50), (w, 50), (0, 50 + h), (w, 50 + h)]
    for (title, _), img, pos in zip(frames, pil_frames, positions):
        canvas.paste(img, pos)
        draw.text((pos[0] + 10, pos[1] - 25), title, fill=(0, 0, 0))
    path = OUT_DIR / "codec_through_toy_scenes.png"
    canvas.save(path)
    return str(path)


def main() -> None:
    planner = TemporalRedundancyPlanner(
        PlannerConfig(
            patch_size=16,
            static_threshold=0.015,
            shifted_threshold=0.040,
            search_radius_px=4,
            halo_radius_tokens=1,
            window_size_tokens=2,
            estimate_global_translation=False,
        )
    )

    rows = []
    regimes = {
        "talking_head": make_talking_head_frame,
        "parking_lot": make_surveillance_frame,
        "fpv_motion": make_fpv_frame,
    }
    for regime_name, fn in regimes.items():
        rows.append({
            "regime": regime_name,
            "method": "same_position",
            **run_regime(planner, fn, use_local_search=False, global_translation=False),
        })
        rows.append({
            "regime": regime_name,
            "method": "local_search",
            **run_regime(planner, fn, use_local_search=True, global_translation=False),
        })

    rows.append({
        "regime": "fpv_motion",
        "method": "global_translation",
        **run_regime(planner, make_fpv_frame, use_local_search=False, global_translation=True),
    })

    df = pd.DataFrame(rows)
    robot_df = run_robot_roi(planner)
    files = save_plots(df, robot_df)
    files["scene_montage_png"] = save_scene_montage()

    json_path = OUT_DIR / "codec_through_toy_results.json"
    report_path = OUT_DIR / "codec_through_toy_report.md"

    payload = {
        "regime_results": df.to_dict(orient="records"),
        "robot_results": robot_df.to_dict(orient="records"),
        "files": files,
        "notes": [
            "Synthetic scenes are only stress tests; they are not substitutes for TOMATO/MVBench or real codec metadata.",
            "The FPV case demonstrates why egomotion compensation or local search is important.",
            "The robotics ROI experiment demonstrates a practical safety/efficiency trade-off for VLA deployment.",
        ],
    }
    json_path.write_text(json.dumps(payload, indent=2))

    report = []
    report.append("# Codec-Through toy experiments\n")
    report.append("These results come from synthetic scenes built to probe design choices, not from a real VLM benchmark.\n")
    report.append("## Regime results\n")
    report.append(df.round(2).to_markdown(index=False))
    report.append("\n\n## Robot ROI results\n")
    report.append(robot_df.round(2).to_markdown(index=False))
    report.append(
        "\n\n## Interpretation\n"
        "- Same-position differencing works extremely well when the camera is mostly fixed.\n"
        "- FPV / egomotion breaks naive caching, but small-motion local search or global compensation recovers large reuse.\n"
        "- Once a 1-hop halo and window grouping are added, the true recompute rate is higher than raw NOVEL token percentage.\n"
        "- In robotics, protecting the gripper/object ROI raises compute noticeably but is still far cheaper than recomputing the full frame.\n"
    )
    report_path.write_text("".join(report))

    print(json.dumps({
        "json": str(json_path),
        "report": str(report_path),
        **files,
    }, indent=2))


if __name__ == "__main__":
    main()
