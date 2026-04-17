"""Paper-grade Pareto plot: cached_accuracy vs effective_fresh_frames.

Emits `paper/figures/pareto_holdout_n30.png` showing TOMATO and MVBench
motion holdout N=30 side-by-side:

- Uniform dense-N baseline (line)
- Novelty-ranked dense-N baseline (line; phase 1.34)
- Planner 2.0 base cached (point; age=4, no sticky)
- Planner 2.0 + sticky_window=4 cached (point; MVBench only, phase 1.26.B)

X axis: effective_fresh_frames = 1 + (N-1) * (1 - reuse_ratio_mean_active)
Y axis: cached_accuracy (for cached) / accuracy (for dense baselines)

Numbers are loaded from the canonical summary JSONs under
`research/experiments/2026/artifacts/...`. The script refuses to plot if
any required file is missing so the figure always tracks artifact state.

Run:
    uv run python scripts/plot_pareto_paper.py
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS = REPO_ROOT / "research" / "experiments" / "2026" / "artifacts"
NOVELTY = REPO_ROOT / "results" / "novelty_ranked_dense"
FIGURES = REPO_ROOT / "paper" / "figures"


@dataclass(frozen=True)
class CachedPoint:
    label: str
    cached_accuracy: float
    effective_fresh_frames: float
    marker: str
    color: str


@dataclass(frozen=True)
class DenseLine:
    label: str
    xs: list[float]
    ys: list[float]
    marker: str
    color: str
    linestyle: str


def load_cached_summary(path: Path, label: str, *, marker: str, color: str) -> CachedPoint:
    if not path.exists():
        raise FileNotFoundError(f"missing cached summary: {path}")
    payload = json.loads(path.read_text())
    cached_accuracy = float(payload["cached_accuracy"])
    active = float(payload["reuse_ratio_mean_active"])
    frame_count = int(payload["frame_count"])
    effective_fresh = 1.0 + (frame_count - 1) * (1.0 - active)
    return CachedPoint(
        label=label,
        cached_accuracy=cached_accuracy,
        effective_fresh_frames=effective_fresh,
        marker=marker,
        color=color,
    )


def load_novelty_points(benchmark: str, frame_counts: list[int]) -> DenseLine:
    xs: list[float] = []
    ys: list[float] = []
    for n in frame_counts:
        path = NOVELTY / f"{benchmark}_holdout_n{n}.json"
        if not path.exists():
            raise FileNotFoundError(f"missing novelty summary: {path}")
        payload = json.loads(path.read_text())
        xs.append(float(n))
        ys.append(float(payload["accuracy"]))
    return DenseLine(
        label="novelty-ranked dense-N",
        xs=xs,
        ys=ys,
        marker="s",
        color="tab:orange",
        linestyle="--",
    )


UNIFORM_DENSE: dict[str, DenseLine] = {
    "tomato": DenseLine(
        label="uniform dense-N (phase 1.20)",
        xs=[4.0, 6.0, 8.0],
        ys=[0.133, 0.267, 0.333],
        marker="o",
        color="tab:blue",
        linestyle="-",
    ),
    "mvbench": DenseLine(
        label="uniform dense-N (phase 1.21)",
        xs=[4.0, 6.0, 8.0],
        ys=[0.500, 0.567, 0.633],
        marker="o",
        color="tab:blue",
        linestyle="-",
    ),
}


def plot_benchmark(
    ax: plt.Axes,
    *,
    title: str,
    uniform: DenseLine,
    novelty: DenseLine,
    cached: list[CachedPoint],
) -> None:
    for line in (uniform, novelty):
        ax.plot(
            line.xs,
            line.ys,
            marker=line.marker,
            color=line.color,
            linestyle=line.linestyle,
            label=line.label,
        )
    for point in cached:
        ax.plot(
            [point.effective_fresh_frames],
            [point.cached_accuracy],
            marker=point.marker,
            color=point.color,
            markersize=10,
            linestyle="none",
            label=(
                f"{point.label} ({point.cached_accuracy:.3f} @ {point.effective_fresh_frames:.2f})"
            ),
        )
    ax.set_title(title)
    ax.set_xlabel("effective fresh frames (1 + (N-1)(1 - reuse))")
    ax.set_ylabel("cached accuracy")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower right", fontsize=8)
    ax.set_xlim(left=0)


def main() -> None:
    tomato_base = load_cached_summary(
        ARTIFACTS
        / "phase1_20_tomato_motion_holdout_v2_cached_clean"
        / "max_abs-8.0-32.0-static+shifted-age4_summary.json",
        label="Planner 2.0 base (age=4)",
        marker="*",
        color="tab:red",
    )
    mvbench_base = load_cached_summary(
        ARTIFACTS
        / "phase1_21_mvbench_motion_holdout_v2_cached_nosticky"
        / "max_abs-8.0-32.0-static+shifted-age4_summary.json",
        label="Planner 2.0 base (age=4)",
        marker="*",
        color="tab:red",
    )
    mvbench_sticky = load_cached_summary(
        ARTIFACTS
        / "phase1_21_mvbench_motion_holdout_v2_cached"
        / "max_abs-8.0-32.0-static+shifted-age4-sticky4_summary.json",
        label="Planner 2.0 + sticky_window=4 (phase 1.26.B)",
        marker="D",
        color="tab:green",
    )

    tomato_novelty = load_novelty_points("tomato", [4, 6, 8])
    mvbench_novelty = load_novelty_points("mvbench", [4, 6, 8])

    fig, axes = plt.subplots(1, 2, figsize=(12, 5.5), sharey=False)

    plot_benchmark(
        axes[0],
        title="TOMATO motion holdout N=30",
        uniform=UNIFORM_DENSE["tomato"],
        novelty=tomato_novelty,
        cached=[tomato_base],
    )
    plot_benchmark(
        axes[1],
        title="MVBench motion holdout N=30",
        uniform=UNIFORM_DENSE["mvbench"],
        novelty=mvbench_novelty,
        cached=[mvbench_base, mvbench_sticky],
    )

    fig.suptitle(
        "Training-free temporal routing on Qwen 2.5-VL-7B-4bit (MLX)\n"
        "Pareto frontier: cached_accuracy vs effective_fresh_frames",
        fontsize=12,
    )
    fig.tight_layout()

    FIGURES.mkdir(parents=True, exist_ok=True)
    out_path = FIGURES / "pareto_holdout_n30.png"
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    print(f"Wrote {out_path}")

    summary = {
        "tomato": {
            "cached_base": {
                "cached_accuracy": tomato_base.cached_accuracy,
                "effective_fresh_frames": tomato_base.effective_fresh_frames,
            },
            "uniform_dense": dict(
                zip(UNIFORM_DENSE["tomato"].xs, UNIFORM_DENSE["tomato"].ys, strict=True)
            ),
            "novelty_dense": dict(zip(tomato_novelty.xs, tomato_novelty.ys, strict=True)),
        },
        "mvbench": {
            "cached_base": {
                "cached_accuracy": mvbench_base.cached_accuracy,
                "effective_fresh_frames": mvbench_base.effective_fresh_frames,
            },
            "cached_sticky4": {
                "cached_accuracy": mvbench_sticky.cached_accuracy,
                "effective_fresh_frames": mvbench_sticky.effective_fresh_frames,
            },
            "uniform_dense": dict(
                zip(UNIFORM_DENSE["mvbench"].xs, UNIFORM_DENSE["mvbench"].ys, strict=True)
            ),
            "novelty_dense": dict(zip(mvbench_novelty.xs, mvbench_novelty.ys, strict=True)),
        },
    }
    summary_path = FIGURES / "pareto_holdout_n30_data.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    print(f"Wrote {summary_path}")


if __name__ == "__main__":
    main()
