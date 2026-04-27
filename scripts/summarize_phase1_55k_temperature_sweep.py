#!/usr/bin/env python3
"""Summarize adaptive C-PERSIST sampler-temperature sweep pair metrics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast


def _load(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text()))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cell",
        action="append",
        nargs=2,
        metavar=("TEMPERATURE", "PAIR_METRICS"),
        required=True,
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    cells: list[dict[str, Any]] = []
    for temperature, path_text in args.cell:
        metrics_path = Path(path_text)
        metrics = _load(metrics_path)
        cells.append(
            {
                "temperature": float(temperature),
                "pair_metrics": metrics_path.as_posix(),
                "n_pairs": metrics["n_pairs"],
                "paired_correctness_diffs": metrics["paired_correctness_diffs"],
                "paired_choice_diffs": metrics["paired_choice_diffs"],
                "accuracy_delta_session_minus_baseline": metrics[
                    "accuracy_delta_session_minus_baseline"
                ],
                "accuracy_delta_session_minus_baseline_ci95": metrics[
                    "accuracy_delta_session_minus_baseline_ci95"
                ],
                "speedup_all_query_median_cold_over_session_follow_up": metrics[
                    "speedup_all_query_median_cold_over_session_follow_up"
                ],
                "pathological_follow_up_hits": metrics["pathological_follow_up_hits"],
                "pathological_q3_hits": metrics["pathological_q3_hits"],
            }
        )
    cells.sort(key=lambda cell: float(cell["temperature"]))
    payload = {
        "phase": "1.55K",
        "policy": "adaptive_q2_k1_q3_k0_post_q2_state",
        "n_cells": len(cells),
        "temperatures": [cell["temperature"] for cell in cells],
        "cells": cells,
        "pass_sampler_stability": all(
            int(cell["paired_correctness_diffs"]) <= 2
            and int(cell["paired_choice_diffs"]) <= 3
            and int(cell["pathological_follow_up_hits"]) <= 2
            for cell in cells
        ),
        "strict_exact_match_temperatures": [
            cell["temperature"]
            for cell in cells
            if int(cell["paired_correctness_diffs"]) == 0 and int(cell["paired_choice_diffs"]) == 0
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"[1.55K] wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
