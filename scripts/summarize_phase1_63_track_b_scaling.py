#!/usr/bin/env python3
"""Summarize Track B sparse-ViT scaling across frame budgets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast


def _load(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text()))


def _cell(frame_count: int, summary_path: Path) -> dict[str, Any]:
    payload = _load(summary_path)
    all_summary = payload["all"]
    return {
        "frame_count": frame_count,
        "summary_path": summary_path.as_posix(),
        "n_paired_items": payload["n_paired_items"],
        "pass_complete_pairing": payload["pass_complete_pairing"],
        "pass_format": payload["pass_format"],
        "pass_fidelity": payload["pass_fidelity"],
        "pass_sparse_vision": payload["pass_sparse_vision"],
        "pass_e2e_positive": payload["pass_e2e_positive"],
        "pass_ceiling_explained": payload["pass_ceiling_explained"],
        "accuracy_delta": all_summary["accuracy_delta_sparse_minus_dense"],
        "accuracy_delta_ci95": all_summary["accuracy_delta_sparse_minus_dense_ci95"],
        "vision_reduction": all_summary["vision_reduction"],
        "vision_share_dense": all_summary["vision_share_dense"],
        "actual_e2e_speedup": all_summary["actual_e2e_speedup_dense_over_sparse"],
        "predicted_e2e_speedup": all_summary["predicted_e2e_speedup_from_vision_only"],
        "actual_minus_predicted": all_summary["actual_minus_predicted_e2e_speedup"],
        "mean_keep_rate": all_summary["mean_keep_rate"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cell",
        action="append",
        nargs=2,
        metavar=("FRAME_COUNT", "PAIR_SUMMARY"),
        required=True,
        help="Frame count and pair_summary.json path. Repeat for each cell.",
    )
    parser.add_argument(
        "--reference-frame-count",
        action="append",
        type=int,
        default=[],
        help="Frame count to summarize but exclude from the headline gate.",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    cells = [_cell(int(frame), Path(path)) for frame, path in args.cell]
    cells.sort(key=lambda cell: int(cell["frame_count"]))
    complete = all(cell["pass_complete_pairing"] and cell["pass_format"] for cell in cells)
    reference_frame_counts = set(args.reference_frame_count)
    headline_cells = [
        cell for cell in cells if int(cell["frame_count"]) not in reference_frame_counts
    ]
    if not headline_cells:
        headline_cells = cells
    headline_pass = all(
        cell["pass_fidelity"]
        and cell["pass_sparse_vision"]
        and cell["pass_e2e_positive"]
        and cell["pass_ceiling_explained"]
        for cell in headline_cells
    )
    payload = {
        "phase": "1.63E",
        "complete": complete,
        "headline_pass": headline_pass,
        "n_cells": len(cells),
        "frame_counts": [cell["frame_count"] for cell in cells],
        "reference_frame_counts": sorted(reference_frame_counts),
        "headline_frame_counts": [cell["frame_count"] for cell in headline_cells],
        "cells": cells,
        "max_abs_actual_minus_predicted": max(
            abs(float(cell["actual_minus_predicted"]))
            for cell in cells
            if cell["actual_minus_predicted"] is not None
        ),
        "headline_max_abs_actual_minus_predicted": max(
            abs(float(cell["actual_minus_predicted"]))
            for cell in headline_cells
            if cell["actual_minus_predicted"] is not None
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"[1.63E] wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
