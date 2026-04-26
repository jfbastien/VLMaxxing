#!/usr/bin/env python3
"""Summarize a feature-drift grid emitted by measure_feature_drift.py."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast


def _load(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text()))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--groups", nargs="+", default=["short", "medium", "long"])
    parser.add_argument("--frame-counts", type=int, nargs="+", default=[8, 16, 32])
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

    payload = {
        "input_dir": args.input_dir.as_posix(),
        "model": args.model,
        "groups": args.groups,
        "frame_counts": args.frame_counts,
        "complete": not missing and len(cells) == len(args.groups) * len(args.frame_counts),
        "missing": missing,
        "cells": cells,
        "by_group": by_group,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"[feature-drift-grid] wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
