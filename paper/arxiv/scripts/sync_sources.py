#!/usr/bin/env python3
"""Generate manuscript-ready assets from repo evidence.

This script is intentionally conservative:

- it reads canonical, checked-in artifacts only
- it emits small diffable files under ``paper/arxiv/generated/``
- it keeps the default manuscript snapshot restricted to audited artifact,
  paper-grade evidence
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
os.environ.setdefault("MPLCONFIGDIR", str(REPO_ROOT / ".tmp" / "matplotlib"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.patches as mpatches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

MANUSCRIPT_ROOT = REPO_ROOT / "paper" / "arxiv"
GENERATED = MANUSCRIPT_ROOT / "generated"
ARTIFACTS = REPO_ROOT / "research" / "experiments" / "2026" / "artifacts"


def _run(cmd: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(
        cmd,
        cwd=cwd or REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _git_info(repo: Path) -> dict[str, str]:
    if not repo.exists():
        return {"sha": "missing", "commit_date": "missing"}
    sha = _run(["git", "rev-parse", "HEAD"], cwd=repo)
    commit_date = _run(["git", "show", "-s", "--format=%cs", "HEAD"], cwd=repo)
    if _run(["git", "status", "--short"], cwd=repo):
        sha = f"{sha}-dirty"
    return {"sha": sha, "commit_date": commit_date}


def _short_sha(sha: str, length: int = 7) -> str:
    if sha == "missing":
        return sha
    suffix = "-dirty" if sha.endswith("-dirty") else ""
    base = sha.removesuffix("-dirty")
    return f"{base[:length]}{suffix}"


def _ensure_dirs() -> None:
    for path in [
        REPO_ROOT / ".tmp" / "matplotlib",
        GENERATED,
        GENERATED / "figures",
        GENERATED / "tables",
        GENERATED / "tex",
        GENERATED / "data",
    ]:
        path.mkdir(parents=True, exist_ok=True)


def _sync_curated_paper_figures() -> None:
    figure_stems = [
        "v_share_v_red_ceiling",
        "c_persist_safe_budget",
        "anti_recomputation_overview",
    ]
    for stem in figure_stems:
        source_png = REPO_ROOT / "paper" / "figures" / f"{stem}.png"
        if source_png.exists():
            (GENERATED / "figures" / source_png.name).write_bytes(source_png.read_bytes())
        source_json = REPO_ROOT / "paper" / "figures" / f"{stem}_data.json"
        if source_json.exists():
            (GENERATED / "data" / source_json.name).write_text(source_json.read_text())


def _draw_overview_box(
    ax,
    xy: tuple[float, float],
    width: float,
    height: float,
    *,
    face: str,
    edge: str = "#1f2933",
    text: str = "",
    size: float = 9,
    weight: str = "normal",
    linestyle: str = "solid",
):
    rect = mpatches.FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle="round,pad=0.02,rounding_size=0.035",
        linewidth=1.0,
        edgecolor=edge,
        facecolor=face,
        linestyle=linestyle,
    )
    ax.add_patch(rect)
    if text:
        ax.text(
            xy[0] + width / 2,
            xy[1] + height / 2,
            text,
            ha="center",
            va="center",
            fontsize=size,
            weight=weight,
        )
    return rect


def _draw_overview_arrow(
    ax,
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    color: str = "#374151",
    lw: float = 1.4,
) -> None:
    ax.annotate(
        "",
        xy=end,
        xytext=start,
        arrowprops=dict(arrowstyle="->", color=color, lw=lw, shrinkA=0, shrinkB=0),
    )


def _render_regime_overview_figure(snapshot: dict) -> None:
    """Render a compact conceptual map of the paper's denominator regimes."""

    repair = snapshot["selective_reprefill"]["adaptive"]
    persistent = snapshot["persistent_kv"]
    qwen_16f = next(row for row in persistent["rows"] if int(row["frame_count"]) == 16)

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )
    fig, ax = plt.subplots(figsize=(7.4, 3.8))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(0.04, 0.925, "Video state over time", fontsize=10.0, weight="bold")
    ax.text(
        0.04,
        0.855,
        "Stable state persists;\nmotion is the residual.",
        fontsize=7.8,
        color="#4b5563",
    )

    frame_w = 0.12
    frame_h = 0.39
    for idx in range(4):
        x = 0.055 + idx * 0.074
        y = 0.24 + idx * 0.041
        _draw_overview_box(ax, (x, y), frame_w, frame_h, face="#f8fafc", edge="#64748b")
        ax.add_patch(
            mpatches.Rectangle(
                (x + 0.015, y + 0.04),
                frame_w - 0.03,
                frame_h - 0.08,
                facecolor="#dbeafe",
                alpha=0.55,
                edgecolor="none",
            )
        )
        ax.add_patch(
            mpatches.Rectangle(
                (x + 0.06 + 0.018 * idx, y + 0.17 + 0.01 * idx),
                0.055,
                0.10,
                facecolor="#f97316",
                alpha=0.90,
                edgecolor="#9a3412",
                linewidth=0.6,
            )
        )
        ax.text(x + frame_w / 2, y - 0.035, f"t+{idx}", ha="center", fontsize=8)

    ax.text(0.07, 0.15, "stable state", fontsize=7.5, color="#1d4ed8", weight="bold")
    ax.text(0.07, 0.126, "reuse/cache", fontsize=7.0, color="#1d4ed8")
    ax.text(0.25, 0.15, "fresh residual", fontsize=7.5, color="#c2410c", weight="bold")
    ax.text(0.25, 0.126, "spend work", fontsize=7.0, color="#c2410c")
    _draw_overview_arrow(ax, (0.16, 0.17), (0.13, 0.32), color="#1d4ed8", lw=1.2)
    _draw_overview_arrow(ax, (0.33, 0.17), (0.34, 0.52), color="#c2410c", lw=1.2)

    ax.plot([0.41, 0.41], [0.08, 0.91], color="#cbd5e1", linewidth=1.0)
    ax.text(0.435, 0.91, "Regime denominators", fontsize=10.0, weight="bold")
    ax.text(0.435, 0.855, "Regime", fontsize=7.4, color="#475569", weight="bold")
    ax.text(0.58, 0.855, "Touched work", fontsize=7.4, color="#475569", weight="bold")
    ax.text(0.745, 0.855, "Denominator / status", fontsize=7.4, color="#475569", weight="bold")

    rails = [
        (
            0.76,
            "C-VISION",
            "vision tower",
            "first-query E2E; share-limited",
            "#e0f2fe",
            "#0284c7",
            "solid",
        ),
        (
            0.635,
            "C-PERSIST",
            "prompt + KV",
            "same-video follow-up; first query paid",
            "#dcfce7",
            "#16a34a",
            "solid",
        ),
        (
            0.51,
            "Routing",
            "frame choice",
            "quality frontier; dense backend control",
            "#f1f5f9",
            "#64748b",
            "dashed",
        ),
        (
            0.385,
            "Streaming",
            "live state",
            "candidate C-STREAM;\npending artifact bundle",
            "#fff7ed",
            "#d97706",
            "dashed",
        ),
    ]
    for y, label, mechanism, denom, face, edge, linestyle in rails:
        _draw_overview_box(
            ax,
            (0.435, y),
            0.12,
            0.068,
            face=face,
            edge=edge,
            text=label,
            size=7.4,
            weight="bold",
            linestyle=linestyle,
        )
        _draw_overview_arrow(ax, (0.565, y + 0.034), (0.58, y + 0.034), color=edge)
        _draw_overview_box(
            ax,
            (0.59, y),
            0.13,
            0.068,
            face="#ffffff",
            edge=edge,
            text=mechanism,
            size=7.1,
            linestyle=linestyle,
        )
        ax.text(0.745, y + 0.034, denom, fontsize=6.8, color="#334155", va="center")

    ax.text(0.435, 0.255, "C-CEILING", fontsize=9.6, weight="bold")
    ax.text(0.435, 0.225, "Do not multiply rows; denominators differ.", fontsize=7.6)
    _draw_overview_box(
        ax,
        (0.435, 0.12),
        0.48,
        0.068,
        face="#eef2ff",
        edge="#4f46e5",
        text=(
            "general: E2E = 1 / (fixed + accelerated / s)\nvision case: 1 / (1 - V_share * V_red)"
        ),
        size=6.7,
    )

    fig.suptitle(
        "Anti-recomputation regimes: reuse stable state, buy fresh evidence",
        fontsize=10.5,
        weight="bold",
        y=0.985,
    )
    fig.tight_layout()
    out_png = GENERATED / "figures" / "regime_overview.png"
    out_pdf = GENERATED / "figures" / "regime_overview.pdf"
    fig.savefig(out_png, dpi=220, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    overview = {
        "figure": "regime_overview",
        "purpose": "conceptual denominator map for anti-recomputation regimes",
        "c_vision": {"speedup_range": "1.113--1.407x", "denominator": "first-query E2E"},
        "c_persist": {
            "raw_16f_speedup": qwen_16f["speedup"],
            "adaptive_all_query_speedup_min": repair["all_query_speedup_min"],
            "adaptive_all_query_speedup_max": repair["all_query_speedup_max"],
            "denominator": "after-ingest follow-up / repaired-session latency",
        },
        "routing": {
            "denominator": "effective fresh frames under dense backend",
            "speedup_claim": False,
        },
        "streaming": {
            "denominator": "scale-out component counters and E2E timing",
            "artifact_harmonization_pending": True,
            "gemma_26b_followup_status": "blocked_by_cache_correctness_smoke",
        },
    }
    (GENERATED / "data" / "regime_overview_snapshot.json").write_text(
        json.dumps(overview, indent=2) + "\n"
    )


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _artifact_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"missing canonical artifact: {path}")
    return _load_json(path)


def _render_c_persist_timeline_figure() -> None:
    """Render the adaptive C-PERSIST timing mechanism as a focused timeline."""

    summary = _artifact_json(ARTIFACTS / "phase1_55F_stage_timing" / "stage_timing_summary.json")
    fixed_q2 = summary["fixed_k1"]["q_index"]["q2"]
    fixed_q3 = summary["fixed_k1"]["q_index"]["q3"]
    adaptive_q2 = summary["adaptive"]["q_index"]["q2"]
    adaptive_q3 = summary["adaptive"]["q_index"]["q3"]
    paired = summary["paired_q3"]

    fixed_q3_s = fixed_q3["median_elapsed_ms"] / 1000.0
    adaptive_q3_s = adaptive_q3["median_elapsed_ms"] / 1000.0
    speedup = paired["median_fixed_over_adaptive_speedup"]
    token_reduction = paired["median_tail_token_reduction"] * 100.0

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )
    fig, ax = plt.subplots(figsize=(7.4, 3.2))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(
        0.02,
        0.93,
        "Adaptive C-PERSIST: repair once, reuse the repaired state",
        fontsize=11,
        weight="bold",
    )
    ax.text(
        0.02,
        0.86,
        "The visual tail is bought at Q2. Fixed K=1 buys it again at Q3; "
        "adaptive Q3 mostly appends text.",
        fontsize=7.6,
        color="#475569",
    )

    xs = {"q0": 0.12, "q2": 0.42, "q3": 0.72}
    for key, label in [
        ("q0", "Q0/Q1 first query"),
        ("q2", "Q2 repair"),
        ("q3", "Q3 follow-up"),
    ]:
        ax.text(xs[key], 0.78, label, fontsize=8.0, weight="bold", ha="center", color="#334155")

    def bar(
        x: float,
        y: float,
        *,
        cached_w: float,
        tail_w: float,
        tail_color: str,
        label: str,
        tail_label: str,
    ) -> None:
        ax.add_patch(
            mpatches.FancyBboxPatch(
                (x, y),
                cached_w,
                0.075,
                boxstyle="round,pad=0.01,rounding_size=0.018",
                facecolor="#dcfce7",
                edgecolor="#16a34a",
                linewidth=1.0,
            )
        )
        ax.add_patch(
            mpatches.FancyBboxPatch(
                (x + cached_w + 0.006, y),
                tail_w,
                0.075,
                boxstyle="round,pad=0.01,rounding_size=0.018",
                facecolor=tail_color,
                edgecolor="#c2410c",
                linewidth=1.0,
            )
        )
        ax.text(x + cached_w / 2, y + 0.038, label, fontsize=6.6, ha="center", va="center")
        ax.text(
            x + cached_w + 0.006 + tail_w / 2,
            y + 0.038,
            tail_label,
            fontsize=6.3,
            ha="center",
            va="center",
        )

    def arrow(start: tuple[float, float], end: tuple[float, float], color: str = "#64748b") -> None:
        ax.annotate(
            "",
            xy=end,
            xytext=start,
            arrowprops=dict(arrowstyle="->", lw=1.1, color=color, shrinkA=0, shrinkB=0),
        )

    # Q0/Q1 establishes the long reusable prefix; both policies share this part.
    ax.add_patch(
        mpatches.FancyBboxPatch(
            (0.035, 0.53),
            0.18,
            0.13,
            boxstyle="round,pad=0.012,rounding_size=0.025",
            facecolor="#f8fafc",
            edgecolor="#64748b",
            linewidth=1.0,
        )
    )
    ax.text(0.125, 0.595, "full prefill\n~8.1k tokens", fontsize=7.0, ha="center", va="center")

    ax.text(0.02, 0.64, "Fixed K=1", fontsize=8.2, weight="bold", color="#14532d")
    ax.text(0.02, 0.40, "Adaptive", fontsize=8.2, weight="bold", color="#14532d")

    # Q2 repair is the same operation in both rows.
    bar(
        xs["q2"] - 0.13,
        0.60,
        cached_w=0.105,
        tail_w=0.11,
        tail_color="#fed7aa",
        label="cache",
        tail_label=f"{fixed_q2['median_tail_prompt_tokens']:.0f} tok",
    )
    bar(
        xs["q2"] - 0.13,
        0.36,
        cached_w=0.105,
        tail_w=0.11,
        tail_color="#fed7aa",
        label="cache",
        tail_label=f"{adaptive_q2['median_tail_prompt_tokens']:.0f} tok",
    )

    # Q3 is where the adaptive mechanism appears.
    bar(
        xs["q3"] - 0.14,
        0.60,
        cached_w=0.105,
        tail_w=0.11,
        tail_color="#fb923c",
        label="cache",
        tail_label=f"{fixed_q3['median_tail_prompt_tokens']:.0f} tok",
    )
    bar(
        xs["q3"] - 0.14,
        0.36,
        cached_w=0.17,
        tail_w=0.025,
        tail_color="#fdba74",
        label="post-Q2 repaired cache",
        tail_label=f"{adaptive_q3['median_tail_prompt_tokens']:.0f}",
    )

    arrow((0.22, 0.595), (0.285, 0.635))
    arrow((0.22, 0.595), (0.285, 0.395))
    arrow((0.515, 0.638), (0.58, 0.638), "#16a34a")
    arrow((0.515, 0.398), (0.58, 0.398), "#16a34a")

    ax.text(
        0.67,
        0.70,
        f"Q3: {fixed_q3_s:.2f}s\nrepeat tail",
        fontsize=7.0,
        ha="center",
        color="#7c2d12",
    )
    ax.text(
        0.68,
        0.28,
        f"Q3: {adaptive_q3_s:.3f}s\nreuse repaired cache",
        fontsize=7.0,
        ha="center",
        color="#14532d",
    )

    ax.add_patch(
        mpatches.FancyBboxPatch(
            (0.80, 0.33),
            0.17,
            0.24,
            boxstyle="round,pad=0.018,rounding_size=0.03",
            facecolor="#ecfdf5",
            edgecolor="#16a34a",
            linewidth=1.2,
        )
    )
    ax.text(
        0.885,
        0.49,
        f"{speedup:.2f}x\npaired Q3\nspeedup",
        fontsize=8.8,
        weight="bold",
        ha="center",
        va="center",
        color="#14532d",
    )
    ax.text(
        0.885,
        0.39,
        f"{token_reduction:.1f}% fewer\nQ3 tail tokens",
        fontsize=7.2,
        ha="center",
        va="center",
        color="#166534",
    )

    ax.text(0.05, 0.16, "green = cached prefix/state", fontsize=7.2, color="#166534")
    ax.text(0.28, 0.16, "orange = newly bought tail work", fontsize=7.2, color="#c2410c")
    ax.text(
        0.02,
        0.08,
        "Timing attribution from existing 1.55F/1.55D short-slice artifacts; "
        "fidelity breadth is reported separately.",
        fontsize=6.8,
        color="#475569",
    )

    fig.tight_layout()
    out_png = GENERATED / "figures" / "c_persist_timeline.png"
    out_pdf = GENERATED / "figures" / "c_persist_timeline.pdf"
    fig.savefig(out_png, dpi=220, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    plt.close(fig)
    (GENERATED / "data" / "c_persist_timeline_snapshot.json").write_text(
        json.dumps(
            {
                "phase": summary["phase"],
                "fixed_q3_elapsed_s": fixed_q3_s,
                "adaptive_q3_elapsed_s": adaptive_q3_s,
                "fixed_q3_tail_prompt_tokens": fixed_q3["median_tail_prompt_tokens"],
                "adaptive_q3_tail_prompt_tokens": adaptive_q3["median_tail_prompt_tokens"],
                "paired_q3_fixed_over_adaptive_speedup": speedup,
                "paired_q3_tail_token_reduction": paired["median_tail_token_reduction"],
                "source": (
                    "research/experiments/2026/artifacts/"
                    "phase1_55F_stage_timing/stage_timing_summary.json"
                ),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def _source_path_label(path: Path) -> str:
    path = path.resolve()
    try:
        return path.relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        pass
    return path.name


def _effective_fresh_frames(payload: dict) -> float:
    frame_count = int(payload["frame_count"])
    reuse = payload.get("reuse_ratio_mean_active")
    if reuse is None:
        raise ValueError(f"summary lacks reuse_ratio_mean_active: {payload}")
    return 1.0 + (frame_count - 1) * (1.0 - float(reuse))


def _cached_point(path: Path) -> dict[str, object]:
    payload = _artifact_json(path)
    return {
        "cached_accuracy": float(payload["cached_accuracy"]),
        "agreement": float(payload["agreement"]),
        "effective_fresh_frames": _effective_fresh_frames(payload),
        "git_sha": payload["environment"]["git_sha"],
        "git_dirty": bool(payload["environment"]["git_dirty"]),
        "artifact": path.relative_to(REPO_ROOT).as_posix(),
    }


def _dense_curve(prefix: str, frame_counts: list[int]) -> dict[str, float]:
    values: dict[str, float] = {}
    for frame_count in frame_counts:
        payload = _artifact_json(ARTIFACTS / prefix / f"frame_{frame_count}_summary.json")
        values[f"{float(frame_count):.1f}"] = float(payload["dense_accuracy"])
    return values


def _lane_a_snapshot() -> dict:
    tomato_base_path = (
        ARTIFACTS
        / "phase1_20_tomato_motion_holdout_v2_cached_clean"
        / "max_abs-8.0-32.0-static+shifted-age4_summary.json"
    )
    mvbench_base_path = (
        ARTIFACTS
        / "phase1_21_mvbench_motion_holdout_v2_cached_nosticky"
        / "max_abs-8.0-32.0-static+shifted-age4_summary.json"
    )
    mvbench_sticky_path = (
        ARTIFACTS
        / "phase1_21_mvbench_motion_holdout_v2_cached"
        / "max_abs-8.0-32.0-static+shifted-age4-sticky4_summary.json"
    )
    sticky_payload = _artifact_json(mvbench_sticky_path)

    return {
        "tomato": {
            "cached_base": _cached_point(tomato_base_path),
            "uniform_dense": _dense_curve(
                "phase1_20_tomato_motion_holdout_v2_dense",
                [4, 6, 8],
            ),
        },
        "mvbench": {
            "cached_base": _cached_point(mvbench_base_path),
            "uniform_dense": _dense_curve(
                "phase1_21_mvbench_motion_holdout_v2_dense",
                [4, 6, 8],
            ),
        },
        "supplementary": {
            "mvbench_sticky4": {
                **_cached_point(mvbench_sticky_path),
                "status": "supplementary_dirty_tree_rerun_required",
                "reason": (
                    "The sticky4 MVBench holdout artifact is still dirty-tree and "
                    "remains supplementary until rerun clean."
                ),
            }
        },
        "source_policy": {
            "default_snapshot": "clean_tree_only",
            "supplementary_excluded_from_main_figure": True,
            "sticky4_git_dirty": bool(sticky_payload["environment"]["git_dirty"]),
        },
    }


def _render_lane_a_figure(snapshot: dict) -> None:
    plt.rcParams.update(
        {
            "font.size": 11,
            "axes.titlesize": 12,
            "axes.labelsize": 11,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )

    colors = {
        "dense": "#1d3557",
        "base": "#9b2226",
    }

    fig, axes = plt.subplots(1, 2, figsize=(11.8, 5.2))
    panels = [
        (
            "TOMATO motion holdout (N=30)",
            snapshot["tomato"],
            "ties dense-8\nat 44% budget",
            4.6,
        ),
        (
            "MVBench motion holdout (N=30)",
            snapshot["mvbench"],
            "beats dense-6\nat lower budget",
            4.9,
        ),
    ]

    for ax, (title, payload, note, note_x) in zip(axes, panels, strict=True):
        dense = payload["uniform_dense"]
        dense_x = [float(x) for x in dense]
        dense_y = list(dense.values())

        ax.plot(
            dense_x,
            dense_y,
            color=colors["dense"],
            marker="o",
            linewidth=2.2,
            markersize=6,
            label="uniform dense-N",
        )

        base = payload["cached_base"]
        ax.scatter(
            [base["effective_fresh_frames"]],
            [base["cached_accuracy"]],
            color=colors["base"],
            s=110,
            marker="*",
            edgecolors="black",
            linewidths=0.7,
            zorder=5,
            label="planner base",
        )
        ax.annotate(
            note,
            xy=(base["effective_fresh_frames"], base["cached_accuracy"]),
            xytext=(note_x, base["cached_accuracy"] + 0.06),
            fontsize=9,
            arrowprops={"arrowstyle": "-", "color": colors["base"], "lw": 1.0},
        )

        ax.set_title(title)
        ax.set_xlabel("effective fresh frames")
        ax.set_ylabel("accuracy")
        ax.grid(True, axis="y", alpha=0.25, linewidth=0.8)
        ax.set_xlim(0, 8.6)
        ax.set_ylim(0.1, 0.72)
        ax.legend(frameon=False, loc="lower right", fontsize=9)

    fig.suptitle("Training-free temporal routing: audited holdout snapshot", fontsize=13)
    fig.tight_layout()
    png_path = GENERATED / "figures" / "lane_a_pareto.png"
    pdf_path = GENERATED / "figures" / "lane_a_pareto.pdf"
    fig.savefig(png_path, dpi=220, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    plt.close(fig)

    (GENERATED / "data" / "lane_a_snapshot.json").write_text(
        json.dumps(snapshot, indent=2, sort_keys=True) + "\n"
    )


def _write_lane_a_table(snapshot: dict) -> None:
    rows = [
        (
            "TOMATO",
            "planner base",
            snapshot["tomato"]["cached_base"]["cached_accuracy"],
            snapshot["tomato"]["cached_base"]["effective_fresh_frames"],
            "dense-8",
            snapshot["tomato"]["uniform_dense"]["8.0"],
            8.0,
            "tie",
        ),
        (
            "MVBench",
            "planner base",
            snapshot["mvbench"]["cached_base"]["cached_accuracy"],
            snapshot["mvbench"]["cached_base"]["effective_fresh_frames"],
            "dense-6",
            snapshot["mvbench"]["uniform_dense"]["6.0"],
            6.0,
            "frontier",
        ),
    ]

    lines = [
        r"\begin{table}[H]",
        r"\centering",
        (
            r"\caption{Clean-tree automated snapshot of the Qwen holdout "
            r"frontier from canonical artifact summaries. Dirty-tree "
            r"supplementary variants are intentionally excluded.}"
        ),
        r"\label{tab:lane-a-holdout}",
        r"\begin{tabular}{lllrrrl}",
        r"\toprule",
        r"Benchmark & Policy & Relation & Acc. & Fresh & Comparator & Comparator acc. \\",
        r"\midrule",
    ]
    for benchmark, policy, acc, fresh, comp, comp_acc, comp_fresh, relation in rows:
        lines.append(
            f"{benchmark} & {policy} & {relation} & {acc:.3f} & {fresh:.2f} & "
            f"{comp} ({comp_fresh:.0f}) & {comp_acc:.3f} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    (GENERATED / "tables" / "lane_a_holdout.tex").write_text("\n".join(lines) + "\n")


def _paired_pruning_snapshot(
    reference_path: Path,
    patched_path: Path,
    *,
    benchmark: str,
    frame_count: int,
    status: str,
    advisory_note: str | None = None,
) -> dict[str, object]:
    reference = _artifact_json(reference_path)
    patched = _artifact_json(patched_path)
    observed_e2e = float(reference["mean_dense_end_to_end_ms"]) / float(
        patched["mean_pruned_end_to_end_ms"]
    )
    v_red = (
        float(reference["mean_dense_vision_ms"]) - float(patched["mean_dense_vision_ms"])
    ) / float(reference["mean_dense_vision_ms"])
    v_share = float(reference["mean_dense_vision_ms"]) / float(
        reference["mean_dense_end_to_end_ms"]
    )
    predicted_e2e = 1.0 / (1.0 - v_share * v_red)
    acc_delta = float(patched["pruned_accuracy"]) - float(reference["dense_accuracy"])
    decode_delta_ms = float(patched["mean_decode_ms"]) - float(reference["mean_decode_ms"])
    decode_delta_rel = decode_delta_ms / float(reference["mean_decode_ms"])
    return {
        "benchmark": benchmark,
        "frame_count": frame_count,
        "observed_e2e": observed_e2e,
        "predicted_e2e": predicted_e2e,
        "v_red": v_red,
        "v_share": v_share,
        "acc_delta": acc_delta,
        "decode_delta_ms": decode_delta_ms,
        "decode_delta_rel": decode_delta_rel,
        "status": status,
        "advisory_note": advisory_note or "",
        "reference_source": _source_path_label(reference_path),
        "patched_source": _source_path_label(patched_path),
    }


def _c_vision_snapshot() -> dict[str, object]:
    rows = [
        _paired_pruning_snapshot(
            ARTIFACTS / "phase1_51V_session3" / "exp17_videomme_holdout_8f_unpatched_summary.json",
            ARTIFACTS / "phase1_51V_session3" / "exp18_videomme_holdout_8f_L2_kr050_summary.json",
            benchmark="VideoMME",
            frame_count=8,
            status="clean-holdout",
        ),
        _paired_pruning_snapshot(
            ARTIFACTS / "phase1_51V_session4" / "exp19_mvbench_holdout_8f_unpatched_summary.json",
            ARTIFACTS / "phase1_51V_session4" / "exp20_mvbench_holdout_8f_L2_kr050_summary.json",
            benchmark="MVBench",
            frame_count=8,
            status="advisory-holdout",
            advisory_note="50 ms decode delta on a 432 ms window; interpreted as OS-jitter scale.",
        ),
    ]
    rows.append(
        _paired_pruning_snapshot(
            ARTIFACTS / "phase1_51V_session5" / "exp23_tomato_holdout_8f_unpatched_summary.json",
            ARTIFACTS / "phase1_51V_session5" / "exp24_tomato_holdout_8f_L2_kr050_summary.json",
            benchmark="TOMATO",
            frame_count=8,
            status="advisory-holdout",
            advisory_note=(
                "Revised thermal gate misses by 19 ms in the favorable direction; "
                "source artifacts are checked into this repo."
            ),
        )
    )

    return {"rows": rows}


def _measured_sparse_execution_snapshot() -> dict[str, object]:
    """Return artifact-backed measured sparse-vision execution cells.

    These rows are deliberately separate from the older semantic C-VISION
    holdouts. They time real skipped vision-tower work and therefore carry a
    different evidence class and a different failure surface.
    """

    gemma_dir = ARTIFACTS / "phase1_63G_gemma_track_b"
    qwen_dir = ARTIFACTS / "phase1_63H_16f_kr_sweep"
    qwen_e_dir = ARTIFACTS / "phase1_63E_track_b_frame_scaling"

    gemma_scaling = _artifact_json(gemma_dir / "scaling_summary.json")
    gemma_rows = []
    for cell in gemma_scaling["cells"]:
        frame_count = int(cell["frame_count"])
        pair = _artifact_json(gemma_dir / f"pair_summary_{frame_count}f.json")
        all_row = pair["all"]
        gemma_rows.append(
            {
                "model": "Gemma 4-E4B",
                "frame_count": frame_count,
                "n": int(cell["n_paired_items"]),
                "accuracy_delta": float(cell["accuracy_delta"]),
                "choice_agreement": float(all_row["choice_agreement"]),
                "dense_parse_failures": int(all_row["dense_parse_failures"]),
                "sparse_parse_failures": int(all_row["sparse_parse_failures"]),
                "vision_reduction": float(cell["vision_reduction"]),
                "vision_share_dense": float(cell["vision_share_dense"]),
                "observed_e2e": float(cell["actual_e2e_speedup"]),
                "predicted_e2e": float(cell["predicted_e2e_speedup"]),
                "residual": float(cell["actual_minus_predicted"]),
                "pass_format": bool(cell["pass_format"]),
                "pass_ceiling": bool(cell["pass_ceiling_explained"]),
                "source": _source_path_label(gemma_dir / f"pair_summary_{frame_count}f.json"),
            }
        )

    gemma_32f = _artifact_json(gemma_dir / "pair_summary_32f.json")
    gemma_32f_short = gemma_32f["by_group"]["short"]

    qwen_rows = []
    qwen_8f = _artifact_json(qwen_e_dir / "pair_summary_8f.json")["all"]
    qwen_rows.append(
        {
            "model": "Qwen2.5-VL-7B",
            "setting": "8f, kr=0.50",
            "n": int(qwen_8f["n"]),
            "accuracy_delta": float(qwen_8f["accuracy_delta_sparse_minus_dense"]),
            "choice_agreement": float(qwen_8f["choice_agreement"]),
            "sparse_parse_failures": int(qwen_8f["sparse_parse_failures"]),
            "vision_reduction": float(qwen_8f["vision_reduction"]),
            "observed_e2e": float(qwen_8f["actual_e2e_speedup_dense_over_sparse"]),
            "predicted_e2e": float(qwen_8f["predicted_e2e_speedup_from_vision_only"]),
            "residual": float(qwen_8f["actual_minus_predicted_e2e_speedup"]),
            "interpretation": "ceiling-validating fidelity fail",
            "source": _source_path_label(qwen_e_dir / "pair_summary_8f.json"),
        }
    )
    for kr_label, keep_rate in [("0.65", "065"), ("0.75", "075"), ("0.85", "085")]:
        path = qwen_dir / f"pair_summary_kr{keep_rate}_16f.json"
        row = _artifact_json(path)["all"]
        qwen_rows.append(
            {
                "model": "Qwen2.5-VL-7B",
                "setting": f"16f, kr={kr_label}",
                "n": int(row["n"]),
                "accuracy_delta": float(row["accuracy_delta_sparse_minus_dense"]),
                "choice_agreement": float(row["choice_agreement"]),
                "sparse_parse_failures": int(row["sparse_parse_failures"]),
                "vision_reduction": float(row["vision_reduction"]),
                "observed_e2e": float(row["actual_e2e_speedup_dense_over_sparse"]),
                "predicted_e2e": float(row["predicted_e2e_speedup_from_vision_only"]),
                "residual": float(row["actual_minus_predicted_e2e_speedup"]),
                "interpretation": (
                    "fidelity-safe low-gain boundary" if kr_label == "0.85" else "recovery sweep"
                ),
                "source": _source_path_label(path),
            }
        )

    return {
        "gemma_rows": gemma_rows,
        "gemma_32f_short": {
            "n": int(gemma_32f_short["n"]),
            "accuracy_delta": float(gemma_32f_short["accuracy_delta_sparse_minus_dense"]),
            "choice_agreement": float(gemma_32f_short["choice_agreement"]),
            "dense_parse_failures": int(gemma_32f_short["dense_parse_failures"]),
            "sparse_parse_failures": int(gemma_32f_short["sparse_parse_failures"]),
            "vision_reduction": float(gemma_32f_short["vision_reduction"]),
            "vision_share_dense": float(gemma_32f_short["vision_share_dense"]),
            "observed_e2e": float(gemma_32f_short["actual_e2e_speedup_dense_over_sparse"]),
            "predicted_e2e": float(gemma_32f_short["predicted_e2e_speedup_from_vision_only"]),
            "residual": float(gemma_32f_short["actual_minus_predicted_e2e_speedup"]),
            "source": _source_path_label(gemma_dir / "pair_summary_32f.json"),
        },
        "qwen_rows": qwen_rows,
    }


def _persistent_kv_snapshot() -> dict[str, object]:
    summary_paths = {
        8: (
            ARTIFACTS
            / "loop_queue_20260419_155108"
            / "phase1_55A_persistent_kv_qwen"
            / "summary.json"
        ),
        16: ARTIFACTS / "phase1_55A_16f_frame_scaling" / "summary.json",
        18: ARTIFACTS / "phase1_55A_18f_frame_scaling" / "summary.json",
        20: ARTIFACTS / "phase1_55A_20f_frame_scaling" / "summary.json",
        24: ARTIFACTS / "phase1_55A_24f_frame_scaling" / "summary.json",
        32: ARTIFACTS / "phase1_55A_32f_frame_scaling" / "summary.json",
    }

    rows: list[dict[str, object]] = []
    for frame_count, path in summary_paths.items():
        payload = _artifact_json(path)
        rows.append(
            {
                "frame_count": frame_count,
                "speedup": float(payload["speedup_first_over_follow"]),
                "follow_up_median_s": (
                    float(payload["session_follow_up"]["median_elapsed_ms"]) / 1000.0
                ),
                "accuracy_delta": float(payload["accuracy_delta_session_minus_baseline"]),
                "prefix_coverage": float(payload["mean_follow_up_prefix_coverage"]),
                "source": _source_path_label(path),
            }
        )
    return {"rows": rows}


def _selective_reprefill_cell(
    *,
    label: str,
    regime: str,
    policy: str,
    metrics_path: Path,
    summary_path: Path,
) -> dict:
    metrics = _artifact_json(metrics_path)
    summary = _artifact_json(summary_path)
    return {
        "label": label,
        "regime": regime,
        "policy": policy,
        "n_sessions": int(metrics["n_sessions"]),
        "n_pairs": int(metrics["n_pairs"]),
        "n_follow_up_pairs": int(metrics["n_follow_up_pairs"]),
        "n_q3_pairs": int(metrics["q_index_breakdown"]["q3"]["n"]),
        "paired_correctness_diffs": int(metrics["paired_correctness_diffs"]),
        "paired_choice_diffs": int(metrics["paired_choice_diffs"]),
        "pathological_follow_up_hits": int(metrics["pathological_follow_up_hits"]),
        "pathological_q3_hits": int(metrics["pathological_q3_hits"]),
        "speedup": float(metrics["speedup_follow_up_median_cold_over_session"]),
        "all_query_speedup": float(metrics["speedup_all_query_median_cold_over_session_follow_up"]),
        "session_follow_up_median_s": float(metrics["session_follow_up_median_ms"]) / 1000.0,
        "setup_inclusive_available": "session_follow_up_setup_amortized_median_ms" in metrics,
        "setup_inclusive_follow_up_median_s": (
            float(metrics["session_follow_up_setup_amortized_median_ms"]) / 1000.0
            if "session_follow_up_setup_amortized_median_ms" in metrics
            else None
        ),
        "setup_inclusive_speedup": (
            float(metrics["speedup_follow_up_median_cold_over_session_setup_amortized"])
            if "speedup_follow_up_median_cold_over_session_setup_amortized" in metrics
            else None
        ),
        "baseline_accuracy": float(summary["baseline"]["accuracy"]),
        "peak_rss_gb": float(summary["peak_rss_gb"]),
        "metrics_source": _source_path_label(metrics_path),
        "summary_source": _source_path_label(summary_path),
    }


def _sum_reprefill_cells(cells: list[dict]) -> dict:
    speedups = [float(cell["speedup"]) for cell in cells]
    all_query_speedups = [float(cell["all_query_speedup"]) for cell in cells]
    rss = [float(cell["peak_rss_gb"]) for cell in cells]
    latencies = [float(cell["session_follow_up_median_s"]) for cell in cells]
    return {
        "n_pairs": sum(int(cell["n_pairs"]) for cell in cells),
        "n_sessions": sum(int(cell["n_sessions"]) for cell in cells),
        "n_follow_up_pairs": sum(int(cell["n_follow_up_pairs"]) for cell in cells),
        "n_q3_pairs": sum(int(cell["n_q3_pairs"]) for cell in cells),
        "paired_correctness_diffs": sum(int(cell["paired_correctness_diffs"]) for cell in cells),
        "paired_choice_diffs": sum(int(cell["paired_choice_diffs"]) for cell in cells),
        "pathological_follow_up_hits": sum(
            int(cell["pathological_follow_up_hits"]) for cell in cells
        ),
        "pathological_q3_hits": sum(int(cell["pathological_q3_hits"]) for cell in cells),
        "speedup_min": min(speedups),
        "speedup_max": max(speedups),
        "all_query_speedup_min": min(all_query_speedups),
        "all_query_speedup_max": max(all_query_speedups),
        "latency_min_s": min(latencies),
        "latency_max_s": max(latencies),
        "rss_min": min(rss),
        "rss_max": max(rss),
        "setup_inclusive_available": all(bool(cell["setup_inclusive_available"]) for cell in cells),
    }


def _selective_reprefill_snapshot() -> dict:
    fixed_cells = [
        _selective_reprefill_cell(
            label="1.55D",
            regime="20f short",
            policy="fixed K=1",
            metrics_path=ARTIFACTS
            / "phase1_55D_selective_reprefill_v2"
            / "pair_metrics_k1_n7.json",
            summary_path=ARTIFACTS / "phase1_55D_selective_reprefill_v2" / "summary_k1_n7.json",
        ),
        _selective_reprefill_cell(
            label="1.55G",
            regime="20f medium",
            policy="fixed K=1",
            metrics_path=ARTIFACTS
            / "phase1_55G_k1_medium_replication"
            / "pair_metrics_k1_n10.json",
            summary_path=ARTIFACTS / "phase1_55G_k1_medium_replication" / "summary_k1_n10.json",
        ),
        _selective_reprefill_cell(
            label="1.55I",
            regime="20f long",
            policy="fixed K=1",
            metrics_path=ARTIFACTS / "phase1_55I_k1_long_replication" / "pair_metrics_k1_n7.json",
            summary_path=ARTIFACTS / "phase1_55I_k1_long_replication" / "summary_k1_n7.json",
        ),
        _selective_reprefill_cell(
            label="1.55H",
            regime="32f short",
            policy="fixed K=1",
            metrics_path=ARTIFACTS / "phase1_55H_k1_32f_short_probe" / "pair_metrics_k1_n7.json",
            summary_path=ARTIFACTS / "phase1_55H_k1_32f_short_probe" / "summary_k1_n7.json",
        ),
    ]
    adaptive_cells = [
        _selective_reprefill_cell(
            label="1.55F",
            regime="20f short",
            policy="adaptive Q2 K=1, Q3 post-Q2 K=0",
            metrics_path=ARTIFACTS / "phase1_55F_q3_post_q2_state" / "pair_metrics_k1_n7.json",
            summary_path=ARTIFACTS / "phase1_55F_q3_post_q2_state" / "summary_k1_n7.json",
        ),
        _selective_reprefill_cell(
            label="1.55F-medium",
            regime="20f medium",
            policy="adaptive Q2 K=1, Q3 post-Q2 K=0",
            metrics_path=ARTIFACTS
            / "phase1_55F_medium_adaptive_replication"
            / "pair_metrics_k1_n10.json",
            summary_path=ARTIFACTS
            / "phase1_55F_medium_adaptive_replication"
            / "summary_k1_n10.json",
        ),
        _selective_reprefill_cell(
            label="1.55F-long",
            regime="20f long",
            policy="adaptive Q2 K=1, Q3 post-Q2 K=0",
            metrics_path=ARTIFACTS
            / "phase1_55F_long_adaptive_replication"
            / "pair_metrics_k1_n7.json",
            summary_path=ARTIFACTS / "phase1_55F_long_adaptive_replication" / "summary_k1_n7.json",
        ),
        _selective_reprefill_cell(
            label="1.55F-32f",
            regime="32f short",
            policy="adaptive Q2 K=1, Q3 post-Q2 K=0",
            metrics_path=ARTIFACTS
            / "phase1_55F_32f_short_adaptive_replication"
            / "pair_metrics_k1_n7.json",
            summary_path=ARTIFACTS
            / "phase1_55F_32f_short_adaptive_replication"
            / "summary_k1_n7.json",
        ),
    ]
    return {
        "fixed_cells": fixed_cells,
        "fixed": _sum_reprefill_cells(fixed_cells),
        "adaptive_cells": adaptive_cells,
        "adaptive": _sum_reprefill_cells(adaptive_cells),
    }


def _paired_drift_snapshot() -> dict:
    path = ARTIFACTS / "phase1_61_per_item_drift_summary.json"
    payload = _artifact_json(path)
    return {
        "phase": payload["phase"],
        "title": payload["title"],
        "source": _source_path_label(path),
        "panels": payload["panels"],
    }


def _paired_drift_interpretation(label: str) -> str:
    if label.startswith("1.30"):
        return "first-query admission damage"
    if label.startswith("1.42"):
        return "aggregate tie hides answer drift"
    if label.startswith("1.55A"):
        return "follow-up cache basin"
    raise ValueError(f"unknown paired-drift panel label: {label}")


def _paired_drift_public_label(label: str) -> str:
    if label.startswith("1.30"):
        return "C-VISION Q0 scout"
    if label.startswith("1.42"):
        return "Gemma MVBench holdout"
    if label.startswith("1.55A"):
        return "unrepaired persistent-KV 20f"
    raise ValueError(f"unknown paired-drift panel label: {label}")


def _paired_drift_extra(panel: dict) -> str:
    if "pathological_like" in panel:
        return f"; pathological-like {int(panel['pathological_like'])}/{int(panel['n'])}"
    if "dense_accuracy" in panel and "cached_accuracy" in panel:
        dense = float(panel["dense_accuracy"])
        cached = float(panel["cached_accuracy"])
        return f"; dense/cached acc. {dense:.3f}/{cached:.3f}"
    return ""


def _write_paired_drift_table(snapshot: dict) -> None:
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        (
            r"\caption{Paired-drift audit. Aggregate accuracy can preserve a point "
            r"estimate while answer identity, correctness on individual examples, or "
            r"output format changes.}"
        ),
        r"\label{tab:paired-drift}",
        r"\small",
        r"\renewcommand{\arraystretch}{1.12}",
        r"\begin{tabularx}{\linewidth}{@{}X r r r X@{}}",
        r"\toprule",
        r"Source & \(N\) & Choice drift & Correctness drift & Mechanism signal \\",
        r"\midrule",
    ]
    for panel in snapshot["panels"]:
        n = int(panel["n"])
        choice_changed = int(panel["choice_changed"])
        correctness_changed = int(panel["correctness_changed"])
        interpretation = _paired_drift_interpretation(str(panel["label"]))
        label = _paired_drift_public_label(str(panel["label"]))
        extra = _paired_drift_extra(panel)
        lines.append(
            f"{label} & {n} & {choice_changed}/{n} & "
            f"{correctness_changed}/{n} & {interpretation}{extra} \\\\"
        )
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabularx}",
            r"\end{table}",
        ]
    )
    (GENERATED / "tables" / "paired_drift.tex").write_text("\n".join(lines) + "\n")
    (GENERATED / "data" / "paired_drift_snapshot.json").write_text(
        json.dumps(snapshot, indent=2, sort_keys=True) + "\n"
    )


def _write_c_persist_repair_table(snapshot: dict) -> None:
    repair = snapshot["selective_reprefill"]
    fixed = repair["fixed"]
    adaptive = repair["adaptive"]
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        (
            r"\caption{Selective re-prefill repair frontier. Fixed \(K=1\) is "
            r"the no-coordination baseline; the adaptive post-\(Q2\) state "
            r"policy is the primary broad repair result. Gains are reported as "
            r"cold follow-up or all-query latency divided by repaired-session "
            r"latency. Setup-inclusive fields are emitted when artifacts record "
            r"cache-build setup time; these checked-in cells predate that field.}"
        ),
        r"\label{tab:c-persist-repair}",
        r"\scriptsize",
        r"\renewcommand{\arraystretch}{1.20}",
        (
            r"\begin{tabularx}{\linewidth}"
            r"{@{}l X >{\raggedright\arraybackslash}p{0.17\linewidth} c X@{}}"
        ),
        r"\toprule",
        (
            r"Policy & Scope & session FU median; cold/session gain & "
            r"Paired drift & Mechanism signal \\"
        ),
        r"\midrule",
        (
            r"Fixed \(K=1\) & 20f short/medium/long + 32f short & "
            f"{fixed['latency_min_s']:.2f}--{fixed['latency_max_s']:.2f}s / "
            f"{fixed['speedup_min']:.2f}--{fixed['speedup_max']:.2f}$\\times$ & "
            f"sessions {fixed['paired_correctness_diffs']}/{fixed['n_sessions']}; "
            f"choice {fixed['paired_choice_diffs']}/{fixed['n_pairs']}; "
            f"correct {fixed['paired_correctness_diffs']}/{fixed['n_pairs']} & "
            f"pathological follow-ups {fixed['pathological_follow_up_hits']}/"
            f"{fixed['n_follow_up_pairs']}; drift rule-of-three over "
            f"n={fixed['n_pairs']}: \\(\\leq\\)3.2\\% \\\\"
        ),
        (
            r"Adaptive post-\(Q2\) & 20f short/medium/long + 32f short & "
            f"{adaptive['latency_min_s']:.2f}--{adaptive['latency_max_s']:.2f}s; "
            f"{adaptive['speedup_min']:.2f}--"
            f"{adaptive['speedup_max']:.2f}$\\times$ same-class; "
            f"{adaptive['all_query_speedup_min']:.2f}--"
            f"{adaptive['all_query_speedup_max']:.2f}$\\times$ all-query & "
            f"sessions {adaptive['paired_correctness_diffs']}/{adaptive['n_sessions']}; "
            f"choice {adaptive['paired_choice_diffs']}/{adaptive['n_pairs']}; "
            f"correct {adaptive['paired_correctness_diffs']}/{adaptive['n_pairs']} & "
            "Q3 inherits post-Q2 repaired state; paired Q3 fixed/adaptive "
            "speedup 9.50$\\times$ \\\\"
        ),
        r"\bottomrule",
        r"\end{tabularx}",
        r"\end{table}",
    ]
    (GENERATED / "tables" / "c_persist_repair.tex").write_text("\n".join(lines) + "\n")


def _qwen_bridge_boundary_row(label: str, path: Path) -> dict:
    payload = _artifact_json(path)
    return {
        "label": label,
        "n": int(payload["n_paired_queries"]),
        "sessions": int(payload.get("n_paired_sessions", payload["n_paired_queries"] // 3)),
        "delta": float(payload["accuracy_delta_streaming_minus_cold"]),
        "q0_delta": float(payload["q0_accuracy_delta_streaming_minus_cold"]),
        "follow_up_delta": float(payload["follow_up_accuracy_delta_streaming_minus_cold"]),
        "speedup": float(payload["amortized_speedup_cold_over_streaming"]),
        "active_fraction": payload["streaming_follow_up_vision_pruning_active_fraction"],
        "degenerates": int(payload.get("streaming_degenerate_count", 0)),
        "source": _source_path_label(path),
    }


def _qwen_bridge_boundary_snapshot() -> dict:
    rows = [
        _qwen_bridge_boundary_row(
            "cache reuse",
            ARTIFACTS / "phase1_30AD_instrumented_w_rerun" / "pair_summary.json",
        ),
        _qwen_bridge_boundary_row(
            "cache invalidated",
            ARTIFACTS / "phase1_30AC_cache_invalidated_followups" / "pair_summary.json",
        ),
        _qwen_bridge_boundary_row(
            "dense Q0 reference",
            ARTIFACTS / "phase1_30W_q0_dense_followup_pruned_full" / "pair_summary.json",
        ),
        _qwen_bridge_boundary_row(
            "long kr=0.67",
            ARTIFACTS / "phase1_30Z_long_q0_kr067_20260424" / "pair_summary.json",
        ),
        _qwen_bridge_boundary_row(
            "long kr=0.75",
            ARTIFACTS / "phase1_30AB_long_q0_kr075" / "pair_summary.json",
        ),
        _qwen_bridge_boundary_row(
            "long kr=0.80",
            ARTIFACTS / "phase1_30AB_long_q0_kr080" / "pair_summary.json",
        ),
        _qwen_bridge_boundary_row(
            "long kr=0.85",
            ARTIFACTS / "phase1_30AB_long_q0_kr085" / "pair_summary.json",
        ),
        _qwen_bridge_boundary_row(
            "long kr=0.90",
            ARTIFACTS / "phase1_30AB_long_q0_kr090" / "pair_summary.json",
        ),
    ]
    return {"rows": rows}


def _format_optional_fraction(value: object) -> str:
    if value is None:
        return "--"
    return f"{float(value):.1f}"


def _write_qwen_bridge_boundary_table(snapshot: dict) -> None:
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        (
            r"\caption{Qwen composition boundary. The tested admission family "
            r"does not produce a deployable composition point. Dense-Q0 cache "
            r"reuse and cache invalidation reach the same net aggregate loss "
            r"through different any-paired-drift sets; only cache reuse preserves "
            r"the three-query speed profile. The speedup column is paired "
            r"three-query amortized end-to-end speedup versus cold all-query "
            r"execution. Follow-up V active is the measured follow-up "
            r"vision-pruning activity fraction; -- means the row was not "
            r"instrumented.}"
        ),
        r"\label{tab:qwen-bridge-boundary}",
        r"\small",
        r"\renewcommand{\arraystretch}{1.18}",
        r"\resizebox{\linewidth}{!}{%",
        r"\begin{tabular}{@{}l r r r r r r r r@{}}",
        r"\toprule",
        (
            r"Policy & Sessions & Queries & \(\Delta\)acc & Q0 \(\Delta\) & "
            r"Follow-up \(\Delta\) & 3-query E2E & Follow-up V active & Degens \\"
        ),
        r"\midrule",
    ]
    for row in snapshot["rows"]:
        lines.append(
            f"{row['label']} & {row['sessions']} & {row['n']} & {row['delta']:+.3f} & "
            f"{row['q0_delta']:+.3f} & {row['follow_up_delta']:+.3f} & "
            f"{row['speedup']:.2f}$\\times$ & "
            f"{_format_optional_fraction(row['active_fraction'])} & "
            f"{row['degenerates']} \\\\"
        )
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}%",
            r"}",
            r"\end{table}",
        ]
    )
    (GENERATED / "tables" / "qwen_bridge_boundary.tex").write_text("\n".join(lines) + "\n")
    (GENERATED / "data" / "qwen_bridge_boundary_snapshot.json").write_text(
        json.dumps(snapshot, indent=2, sort_keys=True) + "\n"
    )


def _headline_snapshot() -> dict[str, object]:
    return {
        "c_vision": _c_vision_snapshot(),
        "measured_sparse_execution": _measured_sparse_execution_snapshot(),
        "persistent_kv": _persistent_kv_snapshot(),
        "selective_reprefill": _selective_reprefill_snapshot(),
    }


def _render_headline_figure(snapshot: dict) -> None:
    plt.rcParams.update(
        {
            "font.size": 10.5,
            "axes.titlesize": 12,
            "axes.labelsize": 10.5,
            "axes.spines.top": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )

    fig, axes = plt.subplots(1, 2, figsize=(13.2, 5.2))
    left, right = axes

    status_styles = {
        "clean-holdout": {"facecolor": "#dfe7f2", "edgecolor": "#1d3557", "hatch": ""},
        "advisory-holdout": {"facecolor": "#f3ebd3", "edgecolor": "#8d6e00", "hatch": "///"},
        "dev-only": {"facecolor": "#eef0f2", "edgecolor": "#6c757d", "hatch": ".."},
    }

    cvision_rows = snapshot["c_vision"]["rows"]
    xs = list(range(len(cvision_rows)))
    observed = [row["observed_e2e"] for row in cvision_rows]
    predicted = [row["predicted_e2e"] for row in cvision_rows]
    labels = [f"{row['benchmark']}\n{int(row['frame_count'])}f" for row in cvision_rows]

    for x, row in zip(xs, cvision_rows, strict=True):
        style = status_styles[row["status"]]
        left.bar(
            x,
            row["observed_e2e"] - 1.0,
            bottom=1.0,
            width=0.62,
            color=style["facecolor"],
            edgecolor=style["edgecolor"],
            hatch=style["hatch"],
            linewidth=1.4,
            zorder=3,
        )
        left.scatter([x], [row["predicted_e2e"]], color="#9b2226", marker="D", s=48, zorder=5)
        left.text(
            x,
            row["observed_e2e"] + 0.02,
            f"{row['observed_e2e']:.3f}x",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    left.axhline(1.0, color="#666666", linewidth=0.9)
    left.set_xticks(xs, labels)
    left.set_ylabel("end-to-end speedup (x)")
    left.set_ylim(1.0, max(max(observed), max(predicted)) + 0.18)
    left.set_title("First-pass vision pruning")
    left.grid(True, axis="y", alpha=0.22, linewidth=0.8, zorder=0)
    left.legend(
        handles=[
            mpatches.Patch(facecolor="#dfe7f2", edgecolor="#1d3557", label="clean holdout"),
            mpatches.Patch(
                facecolor="#f3ebd3",
                edgecolor="#8d6e00",
                hatch="///",
                label="advisory holdout",
            ),
            mpatches.Patch(
                facecolor="#eef0f2",
                edgecolor="#6c757d",
                hatch="..",
                label="dev-only fallback",
            ),
            plt.Line2D(
                [0],
                [0],
                marker="D",
                color="w",
                markerfacecolor="#9b2226",
                markersize=7,
                label="ceiling prediction",
            ),
        ],
        frameon=False,
        loc="upper left",
        fontsize=8.8,
    )

    kv_rows = snapshot["persistent_kv"]["rows"]
    frames = [row["frame_count"] for row in kv_rows]
    speedups = [row["speedup"] for row in kv_rows]
    deltas = [row["accuracy_delta"] for row in kv_rows]
    follow_up = [row["follow_up_median_s"] for row in kv_rows]

    right.plot(
        frames,
        speedups,
        color="#1d3557",
        marker="o",
        linewidth=2.0,
        markersize=5.8,
    )
    right.set_yscale("log")
    right.set_xlabel("frame count")
    right.set_ylabel("follow-up speedup vs first query (x)")
    right.set_title("Same-video follow-up reuse")
    right.grid(True, axis="y", alpha=0.22, linewidth=0.8)
    right.axvspan(7.5, 16.5, color="#8ecae6", alpha=0.12, lw=0)
    right.text(8.2, 18, "tested tolerance\n(<=16f)", color="#1d3557", fontsize=8.7)

    right_twin = right.twinx()
    right_twin.plot(
        frames,
        deltas,
        color="#9b2226",
        marker="s",
        linestyle="--",
        linewidth=1.6,
        markersize=5,
    )
    right_twin.axhline(0.0, color="#9b2226", linewidth=0.8, alpha=0.5)
    right_twin.set_ylabel("accuracy delta")
    right_twin.set_ylim(min(deltas) - 0.05, 0.05)

    for frame_count, speedup, median_s in zip(frames, speedups, follow_up, strict=True):
        right.annotate(
            f"{speedup:.0f}x\n{median_s:.2f}s",
            xy=(frame_count, speedup),
            xytext=(0, 8),
            textcoords="offset points",
            ha="center",
            fontsize=8.2,
        )

    fig.suptitle("Anti-recomputation gains are regime-dependent", fontsize=13)
    fig.tight_layout()
    (GENERATED / "figures" / "headline_results.png").parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(GENERATED / "figures" / "headline_results.png", dpi=220, bbox_inches="tight")
    fig.savefig(GENERATED / "figures" / "headline_results.pdf", bbox_inches="tight")
    plt.close(fig)

    (GENERATED / "data" / "headline_snapshot.json").write_text(
        json.dumps(snapshot, indent=2, sort_keys=True) + "\n"
    )


def _write_headline_table(snapshot: dict) -> None:
    cvision_rows = snapshot["c_vision"]["rows"]
    measured_sparse = snapshot["measured_sparse_execution"]
    gemma_sparse_short = measured_sparse["gemma_32f_short"]
    qwen_sparse_safe = measured_sparse["qwen_rows"][-1]
    kv_by_frame = {row["frame_count"]: row for row in snapshot["persistent_kv"]["rows"]}
    repair = snapshot["selective_reprefill"]
    fixed_repair = repair["fixed"]
    adaptive_repair = repair["adaptive"]

    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\caption{Headline anti-recomputation results by regime.}",
        r"\label{tab:headline-results}",
        r"\scriptsize",
        r"\renewcommand{\arraystretch}{1.14}",
        r"\begin{tabularx}{\linewidth}{@{}l X p{0.14\linewidth} c X l@{}}",
        r"\toprule",
        r"Regime & Setting & Denom. & Gain & Fidelity & Evidence \\",
        r"\midrule",
        (
            "After-ingest & Qwen same-video follow-up, 16f & "
            "cold/cached follow-up & "
            f"{kv_by_frame[16]['speedup']:.1f}$\\times$ & "
            f"{kv_by_frame[16]['follow_up_median_s']:.3f}\\,s median; "
            f"$\\Delta$acc {kv_by_frame[16]['accuracy_delta']:+.3f} & local clean \\\\"
        ),
        (
            "After-ingest & Qwen same-video follow-up, 8f & "
            "cold/cached follow-up & "
            f"{kv_by_frame[8]['speedup']:.1f}$\\times$ & "
            f"{kv_by_frame[8]['follow_up_median_s']:.3f}\\,s median; "
            f"$\\Delta$acc {kv_by_frame[8]['accuracy_delta']:+.3f} & local within criterion \\\\"
        ),
        (
            "After-ingest & Qwen adaptive re-prefill, 20f/32f breadth & "
            "cold/repaired follow-up median & "
            f"{adaptive_repair['speedup_min']:.2f}--"
            f"{adaptive_repair['speedup_max']:.2f}$\\times$ & "
            f"choice/correct diffs {adaptive_repair['paired_choice_diffs']}/"
            f"{adaptive_repair['n_pairs']}; cold-all-query ratio "
            f"{adaptive_repair['all_query_speedup_min']:.2f}--"
            f"{adaptive_repair['all_query_speedup_max']:.2f}$\\times$ & "
            "local repair breadth \\\\"
        ),
        (
            "After-ingest & Qwen fixed K=1 re-prefill, 20f/32f breadth & "
            "cold/repaired follow-up & "
            f"{fixed_repair['speedup_min']:.2f}--"
            f"{fixed_repair['speedup_max']:.2f}$\\times$ & "
            f"choice/correct diffs {fixed_repair['paired_choice_diffs']}/"
            f"{fixed_repair['n_pairs']}; pathological follow-ups "
            f"{fixed_repair['pathological_follow_up_hits']}/"
            f"{fixed_repair['n_follow_up_pairs']} & local repair breadth \\\\"
        ),
        (
            "First-pass & Gemma VideoMME 8f holdout & "
            "first-query E2E & "
            f"{cvision_rows[0]['observed_e2e']:.3f}$\\times$ "
            f"& $\\Delta$acc {cvision_rows[0]['acc_delta']:+.3f} & clean local \\\\"
        ),
        (
            "First-pass & Gemma measured sparse vision, 32f short & "
            "first-query E2E & "
            f"{gemma_sparse_short['observed_e2e']:.3f}$\\times$ & "
            f"choice agreement {gemma_sparse_short['choice_agreement'] * 100:.0f}\\%; "
            f"$\\Delta$acc {gemma_sparse_short['accuracy_delta']:+.3f}; "
            "parse failures 0/0 & clean sparse-execution cell \\\\"
        ),
        (
            "First-pass & Gemma MVBench 8f holdout & "
            "first-query E2E & "
            f"{cvision_rows[1]['observed_e2e']:.3f}$\\times$ & "
            f"$\\Delta$acc {cvision_rows[1]['acc_delta']:+.3f}; "
            "favorable timing caveat & advisory local \\\\"
        ),
        (
            "First-pass & Qwen measured sparse vision, 16f kr=0.85 & "
            "first-query E2E & "
            f"{qwen_sparse_safe['observed_e2e']:.3f}$\\times$ & "
            f"$\\Delta$acc {qwen_sparse_safe['accuracy_delta']:+.3f}; "
            f"vision reduction {qwen_sparse_safe['vision_reduction'] * 100:.1f}\\%; "
            "parse failures 0 & fidelity-safe low-gain boundary \\\\"
        ),
        r"\bottomrule",
        r"\end{tabularx}",
        r"\end{table}",
    ]
    (GENERATED / "tables" / "headline_results.tex").write_text("\n".join(lines) + "\n")


def _write_measured_sparse_execution_tables(snapshot: dict) -> None:
    measured = snapshot["measured_sparse_execution"]

    gemma_lines = [
        r"\begin{table}[H]",
        r"\centering",
        (
            r"\caption{Measured sparse vision execution on Gemma. The timed "
            r"path skips real vision-tower work. All three frame budgets have "
            r"zero paired accuracy delta and 100\% choice agreement, but the "
            r"full sweep is not format-clean because dense and sparse arms "
            r"share parse failures; the clean operating point is the 32f short "
            r"bucket described in the text.}"
        ),
        r"\label{tab:gemma-measured-sparse-vision}",
        r"\scriptsize",
        r"\renewcommand{\arraystretch}{1.12}",
        r"\begin{tabularx}{\linewidth}{@{}l r r r r r r r X@{}}",
        r"\toprule",
        (
            r"Frames & \(n\) & \(\Delta\)acc & Agree & Parse & "
            r"\(V_{\mathrm{red}}\) & Obs. & Gap & Interpretation \\"
        ),
        r"\midrule",
    ]
    for row in measured["gemma_rows"]:
        parse = f"{row['dense_parse_failures']}/{row['sparse_parse_failures']}"
        if row["pass_ceiling"] and row["pass_format"]:
            interp = "clean ceiling cell"
        elif row["pass_ceiling"]:
            interp = "ceiling-consistent; matched parse failures"
        else:
            interp = "ceiling miss"
            if not row["pass_format"]:
                interp += "; matched parse failures"
        gemma_lines.append(
            f"{row['frame_count']}f & {row['n']} & "
            f"{row['accuracy_delta']:+.3f} & "
            f"{row['choice_agreement'] * 100:.0f}\\% & {parse} & "
            f"{row['vision_reduction'] * 100:.1f}\\% & "
            f"{row['observed_e2e']:.3f}$\\times$ & "
            f"{row['residual']:+.3f} & {interp} \\\\"
        )
    gemma_lines.extend([r"\bottomrule", r"\end{tabularx}", r"\end{table}"])

    qwen_lines = [
        r"\begin{table}[H]",
        r"\centering",
        (
            r"\caption{Measured sparse vision execution on Qwen. The 8f point "
            r"validates the timing model but fails fidelity. At 16f, increasing "
            r"the keep rate monotonically recovers accuracy and format, ending "
            r"at a fidelity-safe but low-gain point that no longer clears the "
            r"vision-reduction gate.}"
        ),
        r"\label{tab:qwen-measured-sparse-vision}",
        r"\scriptsize",
        r"\renewcommand{\arraystretch}{1.12}",
        r"\begin{tabularx}{\linewidth}{@{}l r r r r r r r X@{}}",
        r"\toprule",
        (
            r"Setting & \(n\) & \(\Delta\)acc & Agree & Parse & "
            r"\(V_{\mathrm{red}}\) & Obs. & Gap & Interpretation \\"
        ),
        r"\midrule",
    ]
    for row in measured["qwen_rows"]:
        qwen_lines.append(
            f"{row['setting']} & {row['n']} & {row['accuracy_delta']:+.3f} & "
            f"{row['choice_agreement'] * 100:.1f}\\% & "
            f"{row['sparse_parse_failures']} & "
            f"{row['vision_reduction'] * 100:.1f}\\% & "
            f"{row['observed_e2e']:.3f}$\\times$ & "
            f"{row['residual']:+.3f} & {row['interpretation']} \\\\"
        )
    qwen_lines.extend([r"\bottomrule", r"\end{tabularx}", r"\end{table}"])

    out = GENERATED / "tables"
    out.joinpath("gemma_measured_sparse_vision.tex").write_text("\n".join(gemma_lines) + "\n")
    out.joinpath("qwen_measured_sparse_vision.tex").write_text("\n".join(qwen_lines) + "\n")
    (GENERATED / "data" / "measured_sparse_execution_snapshot.json").write_text(
        json.dumps(measured, indent=2, sort_keys=True) + "\n"
    )


def _write_c_persist_sampler_table() -> None:
    summary = _artifact_json(
        ARTIFACTS / "phase1_55K_adaptive_temperature_sweep" / "temperature_sweep_summary.json"
    )
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        (
            r"\caption{Adaptive C-PERSIST sampler-temperature sweep on the "
            r"short-slice mechanism cell. This is reviewer-defense evidence "
            r"against a greedy-decoding artifact, not the full 0/93 breadth "
            r"claim and not a universal stochastic robustness theorem.}"
        ),
        r"\label{tab:c-persist-sampler-stability}",
        r"\small",
        r"\begin{tabular}{@{}r r r r r r@{}}",
        r"\toprule",
        (
            r"\(T\) & Baseline & Session & \(\Delta\)acc & "
            r"Choice/correct diffs & Speedup \\"
        ),
        r"\midrule",
    ]
    for row in summary["cells"]:
        lines.append(
            f"{row['temperature']:.1f} & "
            f"{row['baseline_n_correct']}/{row['n_pairs']} & "
            f"{row['session_n_correct']}/{row['n_pairs']} & "
            f"{row['accuracy_delta_session_minus_baseline']:+.3f} & "
            f"{row['paired_choice_diffs']}/{row['paired_correctness_diffs']} & "
            f"{row['speedup_all_query_median_cold_over_session_follow_up']:.2f}"
            r"$\times$ \\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    (GENERATED / "tables" / "c_persist_sampler_stability.tex").write_text("\n".join(lines) + "\n")


def _write_memory_characterization_table() -> None:
    summary = _artifact_json(
        ARTIFACTS / "phase1_66_memory_characterization" / "memory_characterization_summary.json"
    )
    family_labels = {
        "C-PERSIST/1.55": "After-ingest follow-up reuse",
        "C-VISION/1.30": "Composition/admission boundary",
        "Track-B/1.63": "Measured sparse vision execution",
    }
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        (
            r"\caption{Memory characterization across landed cells. The "
            r"runtime mitigation configures an MLX allocation cap and avoided "
            r"kernel panics in the clean queue, but observed process working-set "
            r"peaks still reached 13.6\,GB.}"
        ),
        r"\label{tab:memory-characterization}",
        r"\small",
        r"\begin{tabularx}{\linewidth}{@{}X r r r X@{}}",
        r"\toprule",
        r"Family & Cells & Max peak & Cells \(>10\)GB & Paper meaning \\",
        r"\midrule",
    ]
    for family, row in summary["by_family"].items():
        label = family_labels.get(family, family)
        lines.append(
            f"{label} & {row['n_cells']} & {row['max_peak_observed_gb']:.2f}\\,GB & "
            f"{row['n_cells_over_10gb']} & observed envelope \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}", r"\end{table}"])
    (GENERATED / "tables" / "memory_characterization.tex").write_text("\n".join(lines) + "\n")


def _write_build_meta(primary: dict[str, str]) -> None:
    lines = [
        f"\\newcommand{{\\PrimaryRepoSHA}}{{{_short_sha(primary['sha'])}}}",
        f"\\newcommand{{\\PrimaryRepoCommitDate}}{{{primary['commit_date']}}}",
        r"\newcommand{\UpstreamRepoSHA}{not used}",
        r"\newcommand{\UpstreamRepoCommitDate}{not used}",
        r"\newcommand{\ScaleoutRepoSHA}{pending artifact bundle}",
        r"\newcommand{\ScaleoutRepoCommitDate}{pending artifact bundle}",
    ]
    (GENERATED / "tex" / "build_meta.tex").write_text("\n".join(lines) + "\n")


def _write_repo_provenance_table(primary: dict[str, str]) -> None:
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        (
            r"\caption{Repo provenance captured by the manuscript sync step. "
            r"Regenerate from a clean release tag for the frozen artifact "
            r"bundle.}"
        ),
        r"\label{tab:repo-provenance}",
        r"\begin{tabular}{lll}",
        r"\toprule",
        r"Repo & Commit & Commit date \\",
        r"\midrule",
        f"codec-through-2 & {_short_sha(primary['sha'], 12)} & {primary['commit_date']} \\\\",
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ]
    (GENERATED / "tables" / "repo_provenance.tex").write_text("\n".join(lines) + "\n")


def main() -> int:
    _ensure_dirs()
    snapshot = _lane_a_snapshot()
    _render_lane_a_figure(snapshot)
    _write_lane_a_table(snapshot)
    headline_snapshot = _headline_snapshot()
    _render_regime_overview_figure(headline_snapshot)
    _render_headline_figure(headline_snapshot)
    _write_headline_table(headline_snapshot)
    _write_measured_sparse_execution_tables(headline_snapshot)
    _write_c_persist_repair_table(headline_snapshot)
    _write_c_persist_sampler_table()
    _write_memory_characterization_table()
    _render_c_persist_timeline_figure()
    qwen_bridge_snapshot = _qwen_bridge_boundary_snapshot()
    _write_qwen_bridge_boundary_table(qwen_bridge_snapshot)
    paired_drift_snapshot = _paired_drift_snapshot()
    _write_paired_drift_table(paired_drift_snapshot)
    _sync_curated_paper_figures()
    primary = _git_info(REPO_ROOT)
    _write_build_meta(primary)
    _write_repo_provenance_table(primary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
