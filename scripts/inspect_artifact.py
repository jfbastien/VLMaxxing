#!/usr/bin/env python3
"""Lightweight inspection helper for checked-in benchmark/calibration JSON files.

Several analyses in the round-7 tranche want a quick stdout view of artifact
shape without ad-hoc shell-escaped heredocs. This script provides a small
set of sub-commands that read a JSON artifact and print a compact summary.

Usage:
    uv run python scripts/inspect_artifact.py frame-budget <summary.json>
    uv run python scripts/inspect_artifact.py calibration <calibration.json>
    uv run python scripts/inspect_artifact.py grid-summary <grid_summary.json>
    uv run python scripts/inspect_artifact.py pareto <pareto.json>
    uv run python scripts/inspect_artifact.py benchmark-subset <subset_summary.json>
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def _cmd_frame_budget(args: argparse.Namespace) -> None:
    data = json.loads(Path(args.path).read_text())
    print(f"Benchmark: {data['benchmark']}")
    print(f"Manifest: {data['manifest_path']}")
    print("frames  dense_acc  CI95          n")
    for run in data["runs"]:
        ci = run.get("dense_accuracy_ci95", [0.0, 1.0])
        print(
            f"  {run['frame_count']:>2}    {run['dense_accuracy']:.3f}     "
            f"[{ci[0]:.3f}, {ci[1]:.3f}]  {run['count']}"
        )
    # per-group at the highest frame count
    if data["runs"]:
        highest = max(data["runs"], key=lambda r: int(r["frame_count"]))
        per_group = highest.get("per_group_dense_accuracy") or {}
        if per_group:
            print(f"\nPer-group detail at {highest['frame_count']} frames:")
            for group, row in sorted(per_group.items()):
                print(f"  {group:>24}: dense={row['dense_accuracy']:.3f}")


def _cmd_calibration(args: argparse.Namespace) -> None:
    data = json.loads(Path(args.path).read_text())
    print(f"Manifest: {data['manifest_path']}")
    print(f"Benchmark: {data['benchmark']}")
    print(f"Frame count: {data['frame_count']}")
    print(f"Candidates: {data['candidate_count']}")
    print("Bin counts:")
    for bin_label, count in data["bin_counts"].items():
        print(f"  {bin_label}: {count}")
    # Coverage by (statistic, reuse_classes, max_age)
    coverage: Counter[tuple[str, str, str]] = Counter()
    for point in data["points"]:
        candidate = point["candidate"]
        key = (
            candidate["statistic"],
            "+".join(candidate["reuse_classes"]),
            str(candidate.get("max_age")),
        )
        coverage[key] += 1
    print("\nCoverage (statistic | reuse | max_age):")
    for key, count in sorted(coverage.items()):
        print(f"  {key[0]:<24} {key[1]:<18} age={key[2]:<6} -> {count}")


def _cmd_grid_summary(args: argparse.Namespace) -> None:
    data = json.loads(Path(args.path).read_text())
    print(f"Manifest: {data['manifest_path']}")
    print(f"Benchmark: {data['benchmark']}")
    print(f"Policies evaluated: {len(data['results'])}")
    rows: list[dict[str, Any]] = []
    for res in data["results"]:
        if "error" in res:
            continue
        summary_path = Path(res["summary_path"])
        if not summary_path.exists():
            continue
        s = json.loads(summary_path.read_text())
        rows.append(
            {
                "label": res["candidate"]["label"],
                "cached_acc": float(s["cached_accuracy"]),
                "dense_acc": float(s["dense_accuracy"]),
                "agreement": float(s["agreement"]),
                "reuse": float(s.get("reuse_ratio_mean_active") or s.get("reuse_ratio_mean", 0.0)),
                "cal_reuse": res.get("calibrated_mean_active_reuse"),
            }
        )
    rows.sort(key=lambda r: (-r["cached_acc"], r["reuse"]))
    print(
        f"\n{'label':<60} {'cached':>7} {'dense':>7} {'agree':>7} {'reuse':>6} {'cal':>6}"
    )
    for row in rows[: args.top]:
        cal = row["cal_reuse"] if row["cal_reuse"] is not None else 0.0
        print(
            f"  {row['label']:<58} {row['cached_acc']:>7.3f} {row['dense_acc']:>7.3f} "
            f"{row['agreement']:>7.3f} {row['reuse']:>6.3f} {cal:>6.3f}"
        )


def _cmd_pareto(args: argparse.Namespace) -> None:
    data = json.loads(Path(args.path).read_text())
    print(f"Cached source: {data['cached_source']}")
    print(f"Dense source: {data['dense_source']}")
    print(f"Total frames: {data['total_frames']}")
    print(f"N policies: {data['n_cached']}, N dense points: {data['n_dense']}")
    print(f"Pareto candidates: {data['pareto_candidate_count']}")
    print("\nDense frame-budget curve:")
    for d in data["dense_curve"]:
        print(
            f"  frames={d['frame_count']:>2}: dense={d['dense_accuracy']:.3f} "
            f"[{d['ci95_low']:.3f},{d['ci95_high']:.3f}] n={d['n']}"
        )
    print("\nTop Pareto candidates:")
    for cand in data["pareto_candidates"][: args.top]:
        print(
            f"  {cand['label']:<56} cached={cand['cached_accuracy']:.3f}  "
            f"fresh_frames={cand['effective_fresh_frames']:.2f}  "
            f"reuse={cand['mean_active_reuse']:.3f}  "
            f"agreement={cand['agreement']:.3f}"
        )


def _cmd_benchmark_subset(args: argparse.Namespace) -> None:
    data = json.loads(Path(args.path).read_text())
    print(f"Benchmark: {data.get('benchmark')}")
    for key in (
        "dense_accuracy",
        "cached_accuracy",
        "agreement",
        "cached_parse_failures",
        "reuse_ratio_mean",
        "reuse_ratio_mean_active",
        "stopped_early",
    ):
        if key in data:
            print(f"  {key}: {data[key]}")
    per_group = data.get("per_group") or {}
    if per_group:
        print("\nPer-group:")
        for group, row in sorted(per_group.items()):
            print(f"  {group}: {row}")


def main() -> None:
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers(dest="command", required=True)

    p = subs.add_parser("frame-budget")
    p.add_argument("path", type=Path)
    p.set_defaults(handler=_cmd_frame_budget)

    p = subs.add_parser("calibration")
    p.add_argument("path", type=Path)
    p.set_defaults(handler=_cmd_calibration)

    p = subs.add_parser("grid-summary")
    p.add_argument("path", type=Path)
    p.add_argument("--top", type=int, default=20)
    p.set_defaults(handler=_cmd_grid_summary)

    p = subs.add_parser("pareto")
    p.add_argument("path", type=Path)
    p.add_argument("--top", type=int, default=20)
    p.set_defaults(handler=_cmd_pareto)

    p = subs.add_parser("benchmark-subset")
    p.add_argument("path", type=Path)
    p.set_defaults(handler=_cmd_benchmark_subset)

    args = parser.parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
