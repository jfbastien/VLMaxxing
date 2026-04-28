#!/usr/bin/env python3
"""Summarize 1.55K extended temperature-by-seed sweeps."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--correctness-limit", type=int, default=2)
    parser.add_argument("--choice-limit", type=int, default=3)
    parser.add_argument("--baseline-accuracy-floor", type=float, default=14 / 21)
    args = parser.parse_args()

    seed_summaries = sorted(args.artifact_dir.glob("seed*_temperature_sweep_summary.json"))
    if not seed_summaries:
        raise SystemExit(f"no seed summaries found in {args.artifact_dir}")

    cells: list[dict[str, Any]] = []
    for path in seed_summaries:
        seed_text = path.name.removeprefix("seed").removesuffix("_temperature_sweep_summary.json")
        seed = int(seed_text)
        summary = _load(path)
        for cell in summary["cells"]:
            cells.append(
                {
                    "seed": seed,
                    "temperature": cell["temperature"],
                    "n_pairs": cell["n_pairs"],
                    "baseline_accuracy": cell["baseline_accuracy"],
                    "session_accuracy": cell["session_accuracy"],
                    "accuracy_delta_session_minus_baseline": cell[
                        "accuracy_delta_session_minus_baseline"
                    ],
                    "paired_correctness_diffs": cell["paired_correctness_diffs"],
                    "paired_choice_diffs": cell["paired_choice_diffs"],
                    "pathological_follow_up_hits": cell["pathological_follow_up_hits"],
                    "pathological_q3_hits": cell["pathological_q3_hits"],
                    "speedup_all_query_median_cold_over_session_follow_up": cell[
                        "speedup_all_query_median_cold_over_session_follow_up"
                    ],
                    "pass_cell": (
                        cell["paired_correctness_diffs"] <= args.correctness_limit
                        and cell["paired_choice_diffs"] <= args.choice_limit
                        and cell["baseline_accuracy"] >= args.baseline_accuracy_floor
                        and cell["pathological_follow_up_hits"] == 0
                        and cell["pathological_q3_hits"] == 0
                    ),
                }
            )

    by_temperature: dict[str, dict[str, Any]] = {}
    for temperature in sorted({float(cell["temperature"]) for cell in cells}):
        temp_cells = [cell for cell in cells if float(cell["temperature"]) == temperature]
        deltas = [float(cell["accuracy_delta_session_minus_baseline"]) for cell in temp_cells]
        by_temperature[str(temperature)] = {
            "n_seed_cells": len(temp_cells),
            "max_paired_correctness_diffs": max(
                int(cell["paired_correctness_diffs"]) for cell in temp_cells
            ),
            "max_paired_choice_diffs": max(int(cell["paired_choice_diffs"]) for cell in temp_cells),
            "min_baseline_accuracy": min(float(cell["baseline_accuracy"]) for cell in temp_cells),
            "min_accuracy_delta": min(deltas),
            "max_accuracy_delta": max(deltas),
            "all_cells_pass": all(bool(cell["pass_cell"]) for cell in temp_cells),
        }

    payload = {
        "phase": "1.55K-extended",
        "artifact_dir": args.artifact_dir.as_posix(),
        "n_cells": len(cells),
        "seeds": sorted({int(cell["seed"]) for cell in cells}),
        "temperatures": sorted({float(cell["temperature"]) for cell in cells}),
        "cells": cells,
        "by_temperature": by_temperature,
        "pass_extended_sampler_stability": all(bool(cell["pass_cell"]) for cell in cells),
        "correctness_limit": args.correctness_limit,
        "choice_limit": args.choice_limit,
        "baseline_accuracy_floor": args.baseline_accuracy_floor,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"[1.55K-ext] wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
