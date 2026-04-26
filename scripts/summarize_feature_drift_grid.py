#!/usr/bin/env python3
"""Summarize a feature-drift grid emitted by measure_feature_drift.py."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast


def _load(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text()))


def _weighted_group_static_mean(path: Path, group: str) -> float | None:
    payload = _load(path)
    weighted_sum = 0.0
    weight = 0
    for item in payload.get("per_item", []):
        if str(item.get("group")) != group:
            continue
        static = item.get("per_class_cos", {}).get("static", {})
        n = int(static.get("n", 0))
        if n <= 0 or static.get("mean_cos") is None:
            continue
        weighted_sum += float(static["mean_cos"]) * n
        weight += n
    if weight == 0:
        return None
    return weighted_sum / weight


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--groups", nargs="+", default=["short", "medium", "long"])
    parser.add_argument("--frame-counts", type=int, nargs="+", default=[8, 16, 32])
    parser.add_argument(
        "--qwen-reference-dir",
        type=Path,
        default=None,
        help=(
            "Optional phase 1.57 Qwen reference directory containing "
            "qwen_<frame>f_dev30.json artifacts."
        ),
    )
    parser.add_argument("--matched-threshold", type=float, default=0.05)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    cells: list[dict[str, Any]] = []
    missing: list[str] = []
    for group in args.groups:
        for frame_count in args.frame_counts:
            path = args.input_dir / f"{args.model}_{frame_count}f_{group}.json"
            if not path.exists():
                missing.append(path.as_posix())
                continue
            payload = _load(path)
            aggregate = payload.get("aggregate", {})
            cells.append(
                {
                    "group": group,
                    "frame_count": frame_count,
                    "path": path.as_posix(),
                    "n_items": payload.get("n_items"),
                    "n_samples": payload.get("n_samples"),
                    "cache_hits": payload.get("cache_hits"),
                    "cache_misses": payload.get("cache_misses"),
                    "static_mean_cos": aggregate.get("static", {}).get("mean_cos"),
                    "static_median_cos": aggregate.get("static", {}).get("median_cos"),
                    "shifted_mean_cos": aggregate.get("shifted", {}).get("mean_cos"),
                    "novel_mean_cos": aggregate.get("novel", {}).get("mean_cos"),
                }
            )

    by_group: dict[str, list[dict[str, Any]]] = {}
    for group in args.groups:
        by_group[group] = [cell for cell in cells if cell["group"] == group]

    cross_arch: dict[str, Any] | None = None
    if args.qwen_reference_dir is not None:
        comparisons: list[dict[str, Any]] = []
        for cell in cells:
            group = str(cell["group"])
            frame_count = int(cell["frame_count"])
            qwen_path = args.qwen_reference_dir / f"qwen_{frame_count}f_dev30.json"
            qwen_static = (
                _weighted_group_static_mean(qwen_path, group) if qwen_path.exists() else None
            )
            gemma_static = cell.get("static_mean_cos")
            abs_diff = (
                abs(float(gemma_static) - float(qwen_static))
                if gemma_static is not None and qwen_static is not None
                else None
            )
            comparisons.append(
                {
                    "group": group,
                    "frame_count": frame_count,
                    "gemma_static_mean_cos": gemma_static,
                    "qwen_static_mean_cos": qwen_static,
                    "abs_diff": abs_diff,
                    "matched": abs_diff is not None and abs_diff <= args.matched_threshold,
                    "qwen_reference_path": qwen_path.as_posix(),
                }
            )
        missing_reference = [
            comparison
            for comparison in comparisons
            if comparison["qwen_static_mean_cos"] is None
            or comparison["gemma_static_mean_cos"] is None
        ]
        exceeded = [
            comparison
            for comparison in comparisons
            if comparison["abs_diff"] is not None
            and float(comparison["abs_diff"]) > args.matched_threshold
        ]
        cross_arch = {
            "qwen_reference_dir": args.qwen_reference_dir.as_posix(),
            "matched_threshold": args.matched_threshold,
            "complete": not missing_reference and len(comparisons) == len(cells),
            "matched_geometry": not missing_reference and not exceeded,
            "comparisons": comparisons,
            "missing_reference": missing_reference,
            "exceeded_threshold": exceeded,
        }

    payload = {
        "input_dir": args.input_dir.as_posix(),
        "model": args.model,
        "groups": args.groups,
        "frame_counts": args.frame_counts,
        "complete": not missing and len(cells) == len(args.groups) * len(args.frame_counts),
        "missing": missing,
        "cells": cells,
        "by_group": by_group,
        "cross_arch": cross_arch,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"[feature-drift-grid] wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
