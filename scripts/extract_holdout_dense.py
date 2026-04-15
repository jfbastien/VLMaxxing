#!/usr/bin/env python3
"""Extract the holdout slice of a phase-1.8 nested frame-budget summary into
a flat phase-1.9-shaped JSON so downstream Pareto analyzers consume it.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def _wilson_interval(k: int, n: int, *, z: float = 1.959963984540054) -> tuple[float, float]:
    if n <= 0:
        return 0.0, 0.0
    p = k / n
    denom = 1.0 + (z**2) / n
    center = (p + (z**2) / (2.0 * n)) / denom
    margin = z * math.sqrt((p * (1.0 - p) / n) + ((z**2) / (4.0 * n * n))) / denom
    return (center - margin, center + margin)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--slice", choices=["dev", "holdout"], default="holdout")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    payload = json.loads(args.source.read_text())
    block = payload[args.slice]
    runs = []
    for entry in block["dense_curve"]:
        n = int(entry.get("count") or entry.get("n") or 0)
        acc = float(entry.get("dense_accuracy") or entry.get("accuracy") or 0.0)
        if n > 0:
            k = round(acc * n)
            ci = _wilson_interval(k, n)
        else:
            ci = (0.0, 1.0)
        runs.append(
            {
                "frame_count": int(entry["frame_count"]),
                "dense_accuracy": acc,
                "dense_accuracy_ci95": list(ci),
                "count": n,
            }
        )
    out = {
        "benchmark": payload.get("benchmark", "tomato"),
        "manifest_path": block.get("manifest_path"),
        "source_path": str(args.source),
        "slice": args.slice,
        "runs": runs,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(f"Wrote {args.out} with {len(runs)} dense points (slice={args.slice})")


if __name__ == "__main__":
    main()
