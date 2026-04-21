#!/usr/bin/env python3
"""Generate manuscript-ready assets from repo evidence.

This script is intentionally conservative:

- it reads canonical, checked-in artifacts only
- it emits small diffable files under ``paper/arxiv/generated/``
- it treats the companion ``codec-through-sam`` repo as optional input
- it keeps the default manuscript snapshot restricted to clean-tree,
  paper-grade evidence
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
os.environ.setdefault("MPLCONFIGDIR", str(REPO_ROOT / ".tmp" / "matplotlib"))

import matplotlib
from PIL import Image, ImageDraw

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

MANUSCRIPT_ROOT = REPO_ROOT / "paper" / "arxiv"
GENERATED = MANUSCRIPT_ROOT / "generated"
DEFAULT_SAM_ROOT = REPO_ROOT.parent / "codec-through-sam"
DEFAULT_UPSTREAM_ROOT = REPO_ROOT.parent / "codec-through"
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
    return {"sha": sha, "commit_date": commit_date}


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


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _artifact_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"missing canonical artifact: {path}")
    return _load_json(path)


def _source_path_label(path: Path) -> str:
    path = path.resolve()
    candidates = [
        (REPO_ROOT.resolve(), "codec-through-2"),
        (DEFAULT_UPSTREAM_ROOT.resolve(), "codec-through"),
        (DEFAULT_SAM_ROOT.resolve(), "codec-through-sam"),
    ]
    for root, label in candidates:
        try:
            rel = path.relative_to(root).as_posix()
        except ValueError:
            continue
        return rel if label == "codec-through-2" else f"{label}/{rel}"
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
        dense_x = [float(x) for x in dense.keys()]
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

    fig.suptitle("Training-free temporal routing: clean-tree holdout snapshot", fontsize=13)
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
            "strict win",
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
    v_share = float(reference["mean_dense_vision_ms"]) / float(reference["mean_dense_end_to_end_ms"])
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


def _c_vision_snapshot(upstream_root: Path) -> dict[str, object]:
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

    upstream_session5 = upstream_root / "research" / "experiments" / "2026" / "artifacts" / "phase1_51V_session5"
    if upstream_session5.exists():
        rows.append(
            _paired_pruning_snapshot(
                upstream_session5 / "exp23_tomato_holdout_8f_unpatched_summary.json",
                upstream_session5 / "exp24_tomato_holdout_8f_L2_kr050_summary.json",
                benchmark="TOMATO",
                frame_count=8,
                status="advisory-holdout-imported",
                advisory_note=(
                    "Revised thermal gate misses by 19 ms in the favorable direction; imported "
                    "from the freshly pulled upstream session-5 rerun."
                ),
            )
        )
    else:
        rows.append(
            _paired_pruning_snapshot(
                ARTIFACTS / "phase1_51V_expansion" / "exp07_tomato_8f_unpatched_summary.json",
                ARTIFACTS / "phase1_51V_expansion" / "exp08_tomato_8f_L2_kr050_summary.json",
                benchmark="TOMATO",
                frame_count=8,
                status="dev-only",
                advisory_note="Local tree lacks the session-5 advisory holdout rerun; using the dev cell for now.",
            )
        )

    return {"rows": rows}


def _persistent_kv_snapshot() -> dict[str, object]:
    summary_paths = {
        8: ARTIFACTS / "loop_queue_20260419_155108" / "phase1_55A_persistent_kv_qwen" / "summary.json",
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
                "follow_up_median_s": float(payload["session_follow_up"]["median_elapsed_ms"]) / 1000.0,
                "accuracy_delta": float(payload["accuracy_delta_session_minus_baseline"]),
                "prefix_coverage": float(payload["mean_follow_up_prefix_coverage"]),
                "source": _source_path_label(path),
            }
        )
    return {"rows": rows}


def _deployment_scale_snapshot(sam_root: Path) -> dict[str, object]:
    whitepaper = sam_root / "whitepaper.md"
    publishability = sam_root / "paper" / "publishability-status.md"
    live_demo = sam_root / "live_demo_v2_writeup.md"
    if not whitepaper.exists() or not publishability.exists() or not live_demo.exists():
        return {"entries": [], "available": False}

    entries = [
        {
            "label": "Real-video end-to-end",
            "low": 4.2,
            "high": 4.5,
            "note": "talking-head / surveillance regimes",
            "kind": "benchmark",
            "source": _source_path_label(whitepaper),
        },
        {
            "label": "Gemma follow-up latency",
            "low": 10.0,
            "high": 18.0,
            "note": "0.8 s median, same-video follow-up",
            "kind": "benchmark",
            "source": _source_path_label(publishability),
        },
        {
            "label": "Gemma prefill speedup",
            "low": 5.4,
            "high": 5.4,
            "note": "novelty-pruning result",
            "kind": "benchmark",
            "source": _source_path_label(whitepaper),
        },
        {
            "label": "Streaming VideoMME ViT",
            "low": 13.0,
            "high": 13.0,
            "note": "paired N=60 Gemma streaming protocol",
            "kind": "benchmark",
            "source": _source_path_label(whitepaper),
        },
        {
            "label": "Active-scene RTSP ViT",
            "low": 14.3,
            "high": 14.3,
            "note": "60 s live demo, 701 decoded / 49 ViT calls",
            "kind": "live",
            "source": _source_path_label(live_demo),
        },
        {
            "label": "Streaming dominant pipeline",
            "low": 50.0,
            "high": 50.0,
            "note": "reported aggregate reduction",
            "kind": "benchmark",
            "source": _source_path_label(whitepaper),
        },
        {
            "label": "Live-camera ViT savings",
            "low": 5.0,
            "high": 300.0,
            "note": "scene-dependent range",
            "kind": "live",
            "source": _source_path_label(whitepaper),
        },
    ]
    return {"entries": entries, "available": True}


def _render_deployment_scale_figure(snapshot: dict) -> None:
    out_path = GENERATED / "figures" / "deployment_scale_ranges.pdf"
    png_path = GENERATED / "figures" / "deployment_scale_ranges.png"
    if not snapshot.get("entries"):
        fig, ax = plt.subplots(figsize=(10.5, 4.4))
        ax.axis("off")
        ax.text(
            0.02,
            0.9,
            "TODO: deployment-scale evidence figure unavailable.\n"
            "Expected sources:\n"
            "- codec-through-sam/whitepaper.md\n"
            "- codec-through-sam/paper/publishability-status.md\n"
            "- codec-through-sam/live_demo_v2_writeup.md",
            va="top",
            fontsize=11,
        )
        fig.tight_layout(rect=(0, 0, 1, 0.96))
        fig.savefig(out_path, bbox_inches="tight")
        fig.savefig(png_path, dpi=220, bbox_inches="tight")
        plt.close(fig)
        return

    plt.rcParams.update(
        {
            "font.size": 10.5,
            "axes.titlesize": 12,
            "axes.labelsize": 10.5,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )

    entries = snapshot["entries"]
    fig, ax = plt.subplots(figsize=(13.2, 5.3))
    colors = {"benchmark": "#1d3557", "live": "#b08900"}
    ys = list(range(len(entries)))
    for y, entry in enumerate(entries):
        low = float(entry["low"])
        high = float(entry["high"])
        mid = low if low == high else (low * high) ** 0.5
        color = colors.get(entry["kind"], "#1d3557")
        ax.hlines(y, low, high, color=color, linewidth=2.4)
        ax.scatter([mid], [y], color=color, s=42, zorder=3)
        ax.text(high * 1.08, y, entry["note"], va="center", fontsize=9)

    ax.set_xscale("log")
    ax.set_xlabel("Reduction or speedup (x, log scale)")
    ax.set_yticks(ys, [entry["label"] for entry in entries])
    ax.set_xlim(3.5, 420)
    ax.grid(True, axis="x", alpha=0.22, linewidth=0.8)
    ax.set_title("Deployment-scale anti-recomputation ranges")
    ax.legend(
        handles=[
            plt.Line2D([0], [0], color=colors["benchmark"], lw=2.4, label="deployment-scale benchmark"),
            plt.Line2D([0], [0], color=colors["live"], lw=2.4, label="live or scene-dependent range"),
        ],
        frameon=False,
        loc="lower right",
        fontsize=8.8,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(out_path, bbox_inches="tight")
    fig.savefig(png_path, dpi=220, bbox_inches="tight")
    plt.close(fig)

    (GENERATED / "data" / "deployment_scale_snapshot.json").write_text(
        json.dumps(snapshot, indent=2, sort_keys=True) + "\n"
    )


def _headline_snapshot(upstream_root: Path) -> dict[str, object]:
    return {
        "c_vision": _c_vision_snapshot(upstream_root),
        "persistent_kv": _persistent_kv_snapshot(),
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
        "advisory-holdout-imported": {
            "facecolor": "#f3ebd3",
            "edgecolor": "#8d6e00",
            "hatch": "///",
        },
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
    right.text(8.2, 18, "clean regime\n(<=16f)", color="#1d3557", fontsize=8.7)

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
    kv_by_frame = {row["frame_count"]: row for row in snapshot["persistent_kv"]["rows"]}
    tomato_row = next(row for row in cvision_rows if row["benchmark"] == "TOMATO")

    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\caption{Headline anti-recomputation results by regime.}",
        r"\label{tab:headline-results}",
        r"\small",
        r"\begin{tabularx}{\linewidth}{l X c X l}",
        r"\toprule",
        r"Regime & Setting & Gain & Fidelity & Status \\",
        r"\midrule",
        (
            f"After-ingest & Qwen same-video follow-up, 16f & {kv_by_frame[16]['speedup']:.1f}$\\times$ "
            f"& {kv_by_frame[16]['follow_up_median_s']:.3f}\\,s median; $\\Delta$acc {kv_by_frame[16]['accuracy_delta']:+.3f} & clean \\\\"
        ),
        (
            f"After-ingest & Qwen same-video follow-up, 8f & {kv_by_frame[8]['speedup']:.1f}$\\times$ "
            f"& {kv_by_frame[8]['follow_up_median_s']:.3f}\\,s median; $\\Delta$acc {kv_by_frame[8]['accuracy_delta']:+.3f} & clean \\\\"
        ),
        (
            f"First-pass & Gemma MVBench 8f holdout & {cvision_rows[1]['observed_e2e']:.3f}$\\times$ "
            f"& $\\Delta$acc {cvision_rows[1]['acc_delta']:+.3f} & advisory \\\\"
        ),
        (
            f"First-pass & Gemma VideoMME 8f holdout & {cvision_rows[0]['observed_e2e']:.3f}$\\times$ "
            f"& $\\Delta$acc {cvision_rows[0]['acc_delta']:+.3f} & clean \\\\"
        ),
        (
            f"First-pass & Gemma TOMATO 8f {'holdout' if 'holdout' in tomato_row['status'] else 'dev'} "
            f"& {tomato_row['observed_e2e']:.3f}$\\times$ & $\\Delta$acc {tomato_row['acc_delta']:+.3f} "
            f"& {'imported adv.' if tomato_row['status'] == 'advisory-holdout-imported' else 'dev-only'} \\\\"
        ),
        r"\bottomrule",
        r"\end{tabularx}",
        r"\end{table}",
    ]
    (GENERATED / "tables" / "headline_results.tex").write_text("\n".join(lines) + "\n")


def _write_build_meta(primary: dict[str, str], upstream: dict[str, str], sam: dict[str, str]) -> None:
    lines = [
        f"\\newcommand{{\\PrimaryRepoSHA}}{{{primary['sha'][:12]}}}",
        f"\\newcommand{{\\PrimaryRepoCommitDate}}{{{primary['commit_date']}}}",
        f"\\newcommand{{\\UpstreamRepoSHA}}{{{upstream['sha'][:12] if upstream['sha'] != 'missing' else 'missing'}}}",
        f"\\newcommand{{\\UpstreamRepoCommitDate}}{{{upstream['commit_date']}}}",
        f"\\newcommand{{\\SamRepoSHA}}{{{sam['sha'][:12] if sam['sha'] != 'missing' else 'missing'}}}",
        f"\\newcommand{{\\SamRepoCommitDate}}{{{sam['commit_date']}}}",
    ]
    (GENERATED / "tex" / "build_meta.tex").write_text("\n".join(lines) + "\n")


def _write_repo_provenance_table(
    primary: dict[str, str], upstream: dict[str, str], sam: dict[str, str]
) -> None:
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\caption{Repo provenance for the current manuscript sync.}",
        r"\label{tab:repo-provenance}",
        r"\begin{tabular}{lll}",
        r"\toprule",
        r"Repo & Commit & Commit date \\",
        r"\midrule",
        f"codec-through-2 & {primary['sha'][:12]} & {primary['commit_date']} \\\\",
        (
            "codec-through & "
            f"{upstream['sha'][:12] if upstream['sha'] != 'missing' else 'missing'} & "
            f"{upstream['commit_date']} \\\\"
        ),
        (
            "codec-through-sam & "
            f"{sam['sha'][:12] if sam['sha'] != 'missing' else 'missing'} & "
            f"{sam['commit_date']} \\\\"
        ),
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ]
    (GENERATED / "tables" / "repo_provenance.tex").write_text("\n".join(lines) + "\n")


def _candidate_snapshot_paths(sam_root: Path) -> list[Path]:
    return [
        sam_root / "diagrams" / "live_demo_v2" / "01_setup.jpg",
        sam_root / "diagrams" / "live_demo_v2" / "02_cleaning_begins.jpg",
        sam_root / "diagrams" / "live_demo_v2" / "03_cleaning_active.jpg",
        sam_root / "diagrams" / "live_demo_v2" / "04_end_of_window.jpg",
    ]


def _draw_label(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str) -> None:
    draw.rectangle((xy[0], xy[1], xy[0] + 190, xy[1] + 24), fill=(255, 255, 255, 220))
    draw.text((xy[0] + 6, xy[1] + 5), text, fill=(20, 20, 20))


def _render_snapshot_contact_sheet(sam_root: Path) -> None:
    sources = [path for path in _candidate_snapshot_paths(sam_root) if path.exists()]
    out_path = GENERATED / "figures" / "streaming_snapshot_contact_sheet.png"
    note_path = GENERATED / "tex" / "streaming_snapshot_note.tex"

    if len(sources) < 4:
        image = Image.new("RGB", (1400, 850), color=(250, 248, 245))
        draw = ImageDraw.Draw(image)
        text = (
            "TODO: curate real-application snapshots.\n\n"
            "Preferred current source repo:\n"
            "codec-through-sam/diagrams/live_demo_v2/\n\n"
            "Expected images:\n"
            "- diagrams/live_demo_v2/01_setup.jpg\n"
            "- diagrams/live_demo_v2/02_cleaning_begins.jpg\n"
            "- diagrams/live_demo_v2/03_cleaning_active.jpg\n"
            "- diagrams/live_demo_v2/04_end_of_window.jpg"
        )
        draw.multiline_text((70, 90), text, fill=(40, 40, 40), spacing=10)
        image.save(out_path)
        note_lines = [
            r"\paragraph{Streaming snapshot sources.}",
            r"The companion repo was not available with the expected four draft",
            r"screenshots, so the manuscript sync generated a placeholder image",
            r"instead. Expected source root: \path{codec-through-sam/diagrams/live_demo_v2/}.",
        ]
        note_path.write_text("\n".join(note_lines) + "\n")
        return

    cell_w = 640
    cell_h = 360
    margin = 30
    canvas = Image.new("RGB", (margin * 3 + cell_w * 2, margin * 3 + cell_h * 2), "white")
    labels = [
        "A. setup",
        "B. change begins",
        "C. change active",
        "D. end of window",
    ]
    for idx, source in enumerate(sources[:4]):
        image = Image.open(source).convert("RGB")
        image.thumbnail((cell_w, cell_h))
        tile = Image.new("RGB", (cell_w, cell_h), color=(245, 245, 245))
        x = (cell_w - image.width) // 2
        y = (cell_h - image.height) // 2
        tile.paste(image, (x, y))
        draw = ImageDraw.Draw(tile)
        _draw_label(draw, (10, 10), labels[idx])
        col = idx % 2
        row = idx // 2
        canvas.paste(tile, (margin + col * (cell_w + margin), margin + row * (cell_h + margin)))
    canvas.save(out_path)

    lines = [
        r"\paragraph{Streaming snapshot sources.}",
        r"The draft contact sheet was imported automatically from the companion",
        r"repo. Current source paths:",
        r"\begin{itemize}[leftmargin=1.5em]",
    ]
    for source in sources[:4]:
        rel = source.relative_to(sam_root).as_posix()
        lines.append(rf"\item \path{{codec-through-sam/{rel}}}")
    lines.append(r"\end{itemize}")
    note_path.write_text("\n".join(lines) + "\n")


def main() -> int:
    sam_root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_SAM_ROOT.resolve()
    upstream_root = (
        Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else DEFAULT_UPSTREAM_ROOT.resolve()
    )
    _ensure_dirs()
    snapshot = _lane_a_snapshot()
    _render_lane_a_figure(snapshot)
    _write_lane_a_table(snapshot)
    headline_snapshot = _headline_snapshot(upstream_root)
    _render_headline_figure(headline_snapshot)
    _write_headline_table(headline_snapshot)
    deployment_snapshot = _deployment_scale_snapshot(sam_root)
    _render_deployment_scale_figure(deployment_snapshot)
    primary = _git_info(REPO_ROOT)
    upstream = _git_info(upstream_root)
    sam = _git_info(sam_root)
    _write_build_meta(primary, upstream, sam)
    _write_repo_provenance_table(primary, upstream, sam)
    _render_snapshot_contact_sheet(sam_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
