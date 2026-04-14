#!/usr/bin/env python3
"""Build a partial grid-sweep aggregate JSON from whatever per-policy
summaries already landed. Useful while a long-running sweep is in flight.

Emits the same shape as `planner_grid_search.py sweep` writes at the end,
so `pareto_analysis.py analyze` can consume it mid-sweep.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _cmd_aggregate(args: argparse.Namespace) -> None:
    calibration = json.loads(Path(args.calibration).read_text())
    cal_by_label = {p["candidate"]["label"]: p for p in calibration["points"]}

    results = []
    skipped = 0
    for summary_path in sorted(args.grid_dir.glob("*_summary.json")):
        label = summary_path.name.replace("_summary.json", "")
        cal_entry = cal_by_label.get(label)
        if cal_entry is None:
            continue
        summary = json.loads(summary_path.read_text())
        # Only include summaries where every requested item has completed.
        # The benchmark runner writes the summary file incrementally as
        # chunks complete, so a partial summary reflects only the items
        # processed so far and produces misleading aggregates.
        requested = summary.get("requested_item_ids") or []
        completed = summary.get("completed_item_ids") or []
        if not requested or len(completed) < len(requested):
            skipped += 1
            continue
        jsonl_path = args.grid_dir / f"{label}.jsonl"
        results.append(
            {
                "candidate": cal_entry["candidate"],
                "jsonl_path": str(jsonl_path),
                "summary_path": str(summary_path),
                "summary": summary,
                "calibrated_mean_active_reuse": cal_entry["mean_active_reuse"],
            }
        )
    if skipped:
        print(f"  (skipped {skipped} in-flight policies)", flush=True)

    payload = {
        "manifest_path": calibration["manifest_path"],
        "benchmark": calibration["benchmark"],
        "frame_count": calibration["frame_count"],
        "calibration_path": str(args.calibration),
        "results": results,
        "partial": True,
        "result_count": len(results),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"Wrote {args.out} with {len(results)} partial results")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--calibration", type=Path, required=True)
    parser.add_argument("--grid-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.set_defaults(handler=_cmd_aggregate)
    args = parser.parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
