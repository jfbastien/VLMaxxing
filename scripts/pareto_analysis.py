#!/usr/bin/env python3
"""Pareto analysis: compare cached planner policies against dense frame-budget baselines.

Each cached-policy run reports:

- cached_accuracy
- dense_accuracy (same slice, same items, dense path through the same runner)
- agreement
- reuse_ratio_mean_active (over active frame pairs, mask out padding)

Each dense frame-budget run reports:

- dense_accuracy at frame_count ∈ {1, 2, 3, 4, 6, 8}

To compare on a single Pareto axis, we convert cached-policy evidence into a
"fresh-token-equivalent" budget:

  effective_fresh_frames ≈ 1 + (N-1) × (1 - mean_active_reuse)

That is, the first frame always pays the full vision-encode cost, then each
additional frame pays a cost proportional to the fraction of tokens that
were NOT reused from the rolling cache. This is a Track-A heuristic only;
Track B should report measured vision-encode FLOPs/latency directly.

The Pareto frontier is: for every cached policy, check whether ANY
dense-frame baseline dominates it (dense has >= the cached accuracy at <=
the cached fresh-frame budget). If so, the cached policy is NOT on the
Pareto frontier. If not, it is a candidate for holdout evaluation.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class CachedPoint:
    label: str
    cached_accuracy: float
    dense_accuracy: float
    agreement: float
    mean_active_reuse: float
    effective_fresh_frames: float
    static_threshold: float
    shifted_threshold: float
    statistic: str
    reuse_classes: list[str]
    max_age: int | None
    n: int


@dataclass(frozen=True, slots=True)
class DensePoint:
    frame_count: int
    dense_accuracy: float
    ci95_low: float
    ci95_high: float
    n: int


def _wilson_interval(k: int, n: int, *, z: float = 1.959963984540054) -> tuple[float, float]:
    if n <= 0:
        return 0.0, 0.0
    p = k / n
    denom = 1.0 + (z**2) / n
    center = (p + (z**2) / (2.0 * n)) / denom
    margin = z * math.sqrt((p * (1.0 - p) / n) + ((z**2) / (4.0 * n * n))) / denom
    return (center - margin, center + margin)


def _effective_fresh_frames(mean_active_reuse: float, total_frames: int) -> float:
    if total_frames <= 1:
        return float(total_frames)
    return 1.0 + (total_frames - 1) * (1.0 - mean_active_reuse)


def _load_cached_points(
    grid_summary_path: Path, *, total_frames: int
) -> list[CachedPoint]:
    payload = json.loads(grid_summary_path.read_text())
    points: list[CachedPoint] = []
    for result in payload["results"]:
        if "error" in result:
            continue
        summary_path = Path(result["summary_path"])
        summary = json.loads(summary_path.read_text())
        candidate = result["candidate"]
        reuse = summary.get("reuse_ratio_mean_active") or summary.get("reuse_ratio_mean")
        if reuse is None:
            continue
        points.append(
            CachedPoint(
                label=candidate["label"],
                cached_accuracy=float(summary["cached_accuracy"]),
                dense_accuracy=float(summary["dense_accuracy"]),
                agreement=float(summary["agreement"]),
                mean_active_reuse=float(reuse),
                effective_fresh_frames=_effective_fresh_frames(float(reuse), total_frames),
                static_threshold=float(candidate["static_threshold"]),
                shifted_threshold=float(candidate["shifted_threshold"]),
                statistic=str(candidate["statistic"]),
                reuse_classes=list(candidate["reuse_classes"]),
                max_age=candidate.get("max_age"),
                n=int(
                    summary.get("requested_item_ids_count")
                    or len(summary.get("requested_item_ids", []))
                    or 0
                ),
            )
        )
    return points


def _load_dense_points(frame_budget_summary: Path) -> list[DensePoint]:
    payload = json.loads(frame_budget_summary.read_text())
    points: list[DensePoint] = []
    for run in payload["runs"]:
        ci = run.get("dense_accuracy_ci95", [0.0, 1.0])
        points.append(
            DensePoint(
                frame_count=int(run["frame_count"]),
                dense_accuracy=float(run["dense_accuracy"]),
                ci95_low=float(ci[0]),
                ci95_high=float(ci[1]),
                n=int(run["count"]),
            )
        )
    return points


def _dominates(dense_acc: float, dense_frames: int, cached_point: CachedPoint) -> bool:
    """Strict Pareto domination of a cached policy by a dense frame-budget point.

    Dense strictly dominates cached iff it has higher accuracy AND lower
    budget, OR equal on one dimension and strictly better on the other.
    Exact ties on both dimensions are treated as non-dominated (i.e. the
    cached policy stays on the Pareto frontier as a tie).
    """
    strictly_higher_acc = dense_acc > cached_point.cached_accuracy
    strictly_lower_budget = dense_frames < cached_point.effective_fresh_frames
    equal_acc = dense_acc == cached_point.cached_accuracy
    equal_budget = dense_frames == cached_point.effective_fresh_frames
    return (
        (strictly_higher_acc and (strictly_lower_budget or equal_budget))
        or (equal_acc and strictly_lower_budget)
    )


def _find_pareto_winners(
    cached_points: list[CachedPoint], dense_points: list[DensePoint]
) -> list[dict[str, Any]]:
    winners: list[dict[str, Any]] = []
    for cached in cached_points:
        dominant_dense = None
        for dense in dense_points:
            if _dominates(dense.dense_accuracy, dense.frame_count, cached):
                dominant_dense = dense
                break
        status = {
            "label": cached.label,
            "cached_accuracy": cached.cached_accuracy,
            "dense_accuracy": cached.dense_accuracy,
            "agreement": cached.agreement,
            "mean_active_reuse": cached.mean_active_reuse,
            "effective_fresh_frames": cached.effective_fresh_frames,
            "statistic": cached.statistic,
            "reuse_classes": cached.reuse_classes,
            "max_age": cached.max_age,
            "static_threshold": cached.static_threshold,
            "shifted_threshold": cached.shifted_threshold,
            "n": cached.n,
            "pareto_status": "dominated" if dominant_dense is not None else "candidate",
            "dominated_by_dense_frame": (
                dominant_dense.frame_count if dominant_dense is not None else None
            ),
        }
        winners.append(status)
    return winners


def _cmd_analyze(args: argparse.Namespace) -> None:
    cached_points = _load_cached_points(args.cached, total_frames=args.total_frames)
    dense_points = _load_dense_points(args.dense)
    winners = _find_pareto_winners(cached_points, dense_points)
    pareto_candidates = [w for w in winners if w["pareto_status"] == "candidate"]
    pareto_candidates.sort(
        key=lambda w: (-w["cached_accuracy"], w["effective_fresh_frames"])
    )
    payload = {
        "cached_source": str(args.cached),
        "dense_source": str(args.dense),
        "total_frames": args.total_frames,
        "n_cached": len(cached_points),
        "n_dense": len(dense_points),
        "dense_curve": [
            {
                "frame_count": d.frame_count,
                "dense_accuracy": d.dense_accuracy,
                "ci95_low": d.ci95_low,
                "ci95_high": d.ci95_high,
                "n": d.n,
            }
            for d in dense_points
        ],
        "policies": winners,
        "pareto_candidates": pareto_candidates,
        "pareto_candidate_count": len(pareto_candidates),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"Wrote {args.out}")
    print(f"  Cached points: {len(cached_points)}")
    print(f"  Dense points: {len(dense_points)}")
    print(f"  Pareto candidates: {len(pareto_candidates)}")
    for cand in pareto_candidates[:10]:
        print(
            f"  {cand['label']}: cached_acc={cand['cached_accuracy']:.3f} "
            f"fresh_frames={cand['effective_fresh_frames']:.2f} "
            f"reuse={cand['mean_active_reuse']:.3f} "
            f"agreement={cand['agreement']:.3f}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser(
        "analyze", help="find Pareto candidates that beat dense frame-budget baselines"
    )
    analyze.add_argument("--cached", type=Path, required=True, help="grid sweep summary json")
    analyze.add_argument("--dense", type=Path, required=True, help="frame budget summary json")
    analyze.add_argument("--total-frames", type=int, default=8)
    analyze.add_argument("--out", type=Path, required=True)
    analyze.set_defaults(handler=_cmd_analyze)

    args = parser.parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
