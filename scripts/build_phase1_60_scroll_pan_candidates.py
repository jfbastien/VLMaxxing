#!/usr/bin/env python3
"""Rank shifted-fraction candidates for the Phase 1.60 scroll/pan probe."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _shifted_fraction(item: dict[str, Any]) -> float:
    counts = item["class_counts"]
    total = int(counts["static"]) + int(counts["shifted"]) + int(counts["novel"])
    if total <= 0:
        return 0.0
    return float(counts["shifted"]) / float(total)


def _load_ranked_rows(summary_paths: list[Path]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for path in summary_paths:
        payload = json.loads(path.read_text())
        frame_count = int(payload["frame_count"])
        for item in payload["per_item"]:
            item_id = str(item["item_id"])
            record = by_id.setdefault(
                item_id,
                {
                    "item_id": item_id,
                    "benchmark": item["benchmark"],
                    "group": item["group"],
                    "shifted_fraction_by_frame_count": {},
                },
            )
            record["shifted_fraction_by_frame_count"][str(frame_count)] = _shifted_fraction(item)
    rows: list[dict[str, Any]] = []
    for record in by_id.values():
        fractions = list(record["shifted_fraction_by_frame_count"].values())
        record["mean_shifted_fraction"] = sum(fractions) / len(fractions)
        record["max_shifted_fraction"] = max(fractions)
        rows.append(record)
    rows.sort(key=lambda row: (-float(row["max_shifted_fraction"]), row["item_id"]))
    return rows


def _write_manifest(path: Path, *, item_ids: list[str], source_summaries: list[Path]) -> None:
    lines = [
        'benchmark = "videomme"',
        (
            'description = "Phase 1.60 scroll/pan candidate manifest '
            f'({len(item_ids)} items from shifted-fraction ranking)"'
        ),
        "item_ids = [",
    ]
    for item_id in item_ids:
        lines.append(f'    "{item_id}",')
    lines.append("]")
    lines.append("")
    lines.append("# source summaries:")
    for path in source_summaries:
        lines.append(f"# - {path.as_posix()}")
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, action="append", required=True)
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--min-shifted-fraction", type=float, default=0.30)
    parser.add_argument(
        "--selection-metric",
        choices=("max", "mean"),
        default="max",
        help="Rank/filter on max or mean shifted fraction across summaries.",
    )
    parser.add_argument("--json-out", type=Path, required=True)
    parser.add_argument("--manifest-out", type=Path, default=None)
    args = parser.parse_args()

    rows = _load_ranked_rows(args.summary)
    metric_key = (
        "max_shifted_fraction" if args.selection_metric == "max" else "mean_shifted_fraction"
    )
    selected = [
        row for row in rows if float(row[metric_key]) >= float(args.min_shifted_fraction)
    ][: args.top_k]

    payload = {
        "phase": "1.60",
        "selection_metric": args.selection_metric,
        "min_shifted_fraction": args.min_shifted_fraction,
        "top_k": args.top_k,
        "source_summaries": [path.as_posix() for path in args.summary],
        "n_ranked": len(rows),
        "n_selected": len(selected),
        "selected_item_ids": [row["item_id"] for row in selected],
        "rows": rows,
    }
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    if args.manifest_out is not None:
        args.manifest_out.parent.mkdir(parents=True, exist_ok=True)
        _write_manifest(
            args.manifest_out,
            item_ids=[row["item_id"] for row in selected],
            source_summaries=args.summary,
        )

    print(f"Wrote {args.json_out}")
    if args.manifest_out is not None:
        print(f"Wrote {args.manifest_out}")
    if selected:
        print("Top shifted-fraction candidates:")
        for row in selected:
            print(
                f"  {row['item_id']:<24} group={row['group']:<6} "
                f"max_sf={float(row['max_shifted_fraction']):.3f} "
                f"mean_sf={float(row['mean_shifted_fraction']):.3f}"
            )
    else:
        print("No candidates met the shifted-fraction threshold.")


if __name__ == "__main__":
    main()
