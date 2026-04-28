#!/usr/bin/env python3
"""Summarize Qwen Track B 16f keep-rate bracket cells."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast


def _load(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text()))


def _cell(keep_rate: float, summary_path: Path) -> dict[str, Any]:
    payload = _load(summary_path)
    all_summary = payload["all"]
    return {
        "keep_rate": keep_rate,
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
        "choice_agreement": all_summary["choice_agreement"],
        "vision_reduction": all_summary["vision_reduction"],
        "vision_share_dense": all_summary["vision_share_dense"],
        "actual_e2e_speedup": all_summary["actual_e2e_speedup_dense_over_sparse"],
        "predicted_e2e_speedup": all_summary["predicted_e2e_speedup_from_vision_only"],
        "actual_minus_predicted": all_summary["actual_minus_predicted_e2e_speedup"],
        "mean_keep_rate": all_summary["mean_keep_rate"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", default="1.63I")
    parser.add_argument(
        "--cell",
        action="append",
        nargs=2,
        metavar=("KEEP_RATE", "PAIR_SUMMARY"),
        required=True,
        help="Keep rate and pair_summary.json path. Repeat for each cell.",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    cells = [_cell(float(keep_rate), Path(path)) for keep_rate, path in args.cell]
    cells.sort(key=lambda cell: float(cell["keep_rate"]))
    complete = all(cell["pass_complete_pairing"] and cell["pass_format"] for cell in cells)
    full_pass_cells = [
        cell
        for cell in cells
        if cell["pass_complete_pairing"]
        and cell["pass_format"]
        and cell["pass_fidelity"]
        and cell["pass_sparse_vision"]
        and cell["pass_e2e_positive"]
        and cell["pass_ceiling_explained"]
    ]
    fidelity_safe_cells = [
        cell
        for cell in cells
        if cell["pass_complete_pairing"]
        and cell["pass_format"]
        and cell["pass_fidelity"]
        and cell["pass_e2e_positive"]
        and cell["pass_ceiling_explained"]
    ]
    payload = {
        "phase": args.phase,
        "complete": complete,
        "headline_pass": bool(full_pass_cells),
        "n_cells": len(cells),
        "keep_rates": [cell["keep_rate"] for cell in cells],
        "cells": cells,
        "passing_keep_rates": [cell["keep_rate"] for cell in full_pass_cells],
        "fidelity_safe_keep_rates": [cell["keep_rate"] for cell in fidelity_safe_cells],
        "best_full_pass_keep_rate": (
            min(cell["keep_rate"] for cell in full_pass_cells) if full_pass_cells else None
        ),
        "best_fidelity_safe_keep_rate": (
            min(cell["keep_rate"] for cell in fidelity_safe_cells) if fidelity_safe_cells else None
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"[{args.phase}] wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
