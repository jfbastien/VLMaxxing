#!/usr/bin/env python3
"""Summarize adaptive C-PERSIST sampler-temperature sweep pair metrics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast


def _load(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text()))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open() as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def _paired_queries_path(metrics_path: Path) -> Path:
    return metrics_path.with_name(
        metrics_path.name.replace("pair_metrics", "paired_queries").replace(".json", ".jsonl")
    )


def _accuracy_fields(metrics: dict[str, Any], metrics_path: Path) -> dict[str, Any]:
    if "baseline_accuracy" in metrics:
        return {
            "session_n_correct": metrics["session_n_correct"],
            "baseline_n_correct": metrics["baseline_n_correct"],
            "session_accuracy": metrics["session_accuracy"],
            "baseline_accuracy": metrics["baseline_accuracy"],
        }
    paired_path = _paired_queries_path(metrics_path)
    if not paired_path.exists():
        raise FileNotFoundError(
            f"{metrics_path} lacks baseline_accuracy and fallback {paired_path} is missing"
        )
    rows = _load_jsonl(paired_path)
    session_n_correct = sum(bool(row["session_correct"]) for row in rows)
    baseline_n_correct = sum(bool(row["baseline_correct"]) for row in rows)
    n = len(rows)
    return {
        "session_n_correct": session_n_correct,
        "baseline_n_correct": baseline_n_correct,
        "session_accuracy": session_n_correct / n if n else None,
        "baseline_accuracy": baseline_n_correct / n if n else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cell",
        action="append",
        nargs=2,
        metavar=("TEMPERATURE", "PAIR_METRICS"),
        required=True,
    )
    parser.add_argument(
        "--baseline-accuracy-floor",
        type=float,
        default=14 / 21,
        help=(
            "Minimum absolute baseline accuracy required for a sampler cell to "
            "support a robustness claim. Default 14/21 matches the prereg floor."
        ),
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    cells: list[dict[str, Any]] = []
    for temperature, path_text in args.cell:
        metrics_path = Path(path_text)
        metrics = _load(metrics_path)
        accuracy_fields = _accuracy_fields(metrics, metrics_path)
        cells.append(
            {
                "temperature": float(temperature),
                "pair_metrics": metrics_path.as_posix(),
                "n_pairs": metrics["n_pairs"],
                **accuracy_fields,
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
        "baseline_accuracy_floor": args.baseline_accuracy_floor,
        "pass_baseline_quality": all(
            cell["baseline_accuracy"] is not None
            and float(cell["baseline_accuracy"]) >= args.baseline_accuracy_floor
            for cell in cells
        ),
        "pass_sampler_stability": all(
            int(cell["paired_correctness_diffs"]) <= 2
            and int(cell["paired_choice_diffs"]) <= 3
            and int(cell["pathological_follow_up_hits"]) <= 2
            and cell["baseline_accuracy"] is not None
            and float(cell["baseline_accuracy"]) >= args.baseline_accuracy_floor
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
