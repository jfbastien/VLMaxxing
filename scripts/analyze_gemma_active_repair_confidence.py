#!/usr/bin/env python3
"""Evaluate whether first-pass confidence can gate one-step Gemma repair.

Input rows are paired JSONL records from ``analyze_gemma_full_composition.py``.
The simulated policy is:

1. run the cheap composed/pruned pass;
2. if the composed confidence margin is at or below a threshold, retry the
   same item with the dense branch;
3. otherwise keep the composed answer.

This script does not run a model. It is a preregistration/probe tool for the
active-repair branch: it tests whether a recorded confidence signal separates
items harmed by pruning/admission from items preserved by the cheap pass, and
what speed/accuracy frontier a one-step retry policy would have achieved. The
default margin is candidate-letter top-2 margin, not full-vocabulary top-2,
because the latter can be dominated by output-format tokens.
"""

from __future__ import annotations

import argparse
import json
import math
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import numpy as np

SCHEMA_VERSION = "gemma_active_repair_confidence_v1"


def _read_paired_rows(paths: Iterable[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        with path.open("r", encoding="utf-8") as handle:
            for lineno, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError(f"{path}:{lineno} is not a JSON object")
                row["_source_path"] = str(path)
                row["_source_lineno"] = lineno
                rows.append(row)
    if not rows:
        raise ValueError("no paired rows loaded")
    return rows


def _required_float(row: dict[str, Any], field: str) -> float:
    value = row.get(field)
    if value is None:
        raise ValueError(
            f"{row.get('_source_path')}:{row.get('_source_lineno')} "
            f"{row.get('item_id')} missing {field}"
        )
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{row.get('item_id')} has non-finite {field}: {value!r}")
    return number


def _required_nonnegative_float(row: dict[str, Any], field: str) -> float:
    number = _required_float(row, field)
    if number < 0.0:
        raise ValueError(f"{row.get('item_id')} has negative {field}: {number}")
    return number


def _required_positive_float(row: dict[str, Any], field: str) -> float:
    number = _required_float(row, field)
    if number <= 0.0:
        raise ValueError(f"{row.get('item_id')} has nonpositive {field}: {number}")
    return number


def _mean(values: list[float]) -> float | None:
    return float(np.mean(values)) if values else None


def _median(values: list[float]) -> float | None:
    return float(np.median(values)) if values else None


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 2:
        return None
    x = np.asarray(xs, dtype=np.float64)
    y = np.asarray(ys, dtype=np.float64)
    if float(np.std(x)) == 0.0 or float(np.std(y)) == 0.0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def _risk_auc_harmed_lower(harmed_margins: list[float], safe_margins: list[float]) -> float | None:
    """Return P(harmed margin < safe margin) + 0.5*ties."""

    if not harmed_margins or not safe_margins:
        return None
    wins = 0.0
    total = 0
    for harmed in harmed_margins:
        for safe in safe_margins:
            total += 1
            if harmed < safe:
                wins += 1.0
            elif harmed == safe:
                wins += 0.5
    return wins / total


def _accuracy(rows: list[dict[str, Any]], field: str) -> float:
    return sum(bool(row[field]) for row in rows) / len(rows)


def _threshold_candidates(margins: list[float]) -> list[float]:
    unique = sorted(set(margins))
    if not unique:
        return []
    return [unique[0] - 1e-9, *unique, unique[-1] + 1e-9]


def _simulate_threshold(
    rows: list[dict[str, Any]],
    *,
    margin_field: str,
    threshold: float,
) -> dict[str, Any]:
    retry_count = 0
    active_correct = 0
    active_ms = 0.0
    dense_ms = 0.0
    composed_ms = 0.0
    dense_confidence_capture_ms = 0.0
    composed_confidence_capture_ms = 0.0
    harmed_retried = 0
    preserved_correct_retried = 0
    unchanged_wrong_retried = 0
    recovered_retried = 0
    for row in rows:
        margin = _required_float(row, margin_field)
        retry = margin <= threshold
        retry_count += int(retry)
        dense_correct = bool(row["dense_correct"])
        composed_correct = bool(row["composed_correct"])
        dense_capture_ms = _required_nonnegative_float(
            row, "dense_first_generated_confidence_capture_ms"
        )
        composed_capture_ms = _required_nonnegative_float(
            row, "composed_first_generated_confidence_capture_ms"
        )
        dense_end_to_end_ms = _required_positive_float(row, "dense_end_to_end_ms")
        composed_pass_ms = _required_positive_float(row, "composed_end_to_end_ms")
        dense_retry_ms = dense_end_to_end_ms - dense_capture_ms
        if dense_retry_ms <= 0.0:
            raise ValueError(
                f"{row.get('item_id')} has nonpositive confidence-adjusted dense retry time"
            )
        if retry:
            active_correct += int(dense_correct)
            active_ms += composed_pass_ms + dense_retry_ms
            transition = str(row.get("correctness_transition"))
            harmed_retried += int(transition == "harmed")
            preserved_correct_retried += int(transition == "preserved_correct")
            unchanged_wrong_retried += int(transition == "unchanged_wrong")
            recovered_retried += int(transition == "recovered")
        else:
            active_correct += int(composed_correct)
            active_ms += composed_pass_ms
        dense_ms += dense_retry_ms
        composed_ms += composed_pass_ms
        dense_confidence_capture_ms += dense_capture_ms
        composed_confidence_capture_ms += composed_capture_ms
    accuracy = active_correct / len(rows)
    dense_accuracy = _accuracy(rows, "dense_correct")
    return {
        "threshold": threshold,
        "retry_count": retry_count,
        "retry_rate": retry_count / len(rows),
        "active_accuracy": accuracy,
        "accuracy_delta_vs_dense": accuracy - dense_accuracy,
        "dense_total_ms": dense_ms,
        "composed_total_ms": composed_ms,
        "active_total_ms": active_ms,
        "dense_confidence_capture_ms_subtracted": dense_confidence_capture_ms,
        "composed_confidence_capture_ms_charged": composed_confidence_capture_ms,
        "speedup_dense_over_active": dense_ms / active_ms if active_ms > 0.0 else 0.0,
        "speedup_composed_over_active": composed_ms / active_ms if active_ms > 0.0 else 0.0,
        "harmed_retried": harmed_retried,
        "preserved_correct_retried": preserved_correct_retried,
        "unchanged_wrong_retried": unchanged_wrong_retried,
        "recovered_retried": recovered_retried,
    }


def analyze(
    rows: list[dict[str, Any]],
    *,
    margin_field: str,
    quality_delta_floor: float,
    min_speedup: float,
) -> dict[str, Any]:
    margins = [_required_float(row, margin_field) for row in rows]
    harm_labels = [1.0 if row.get("correctness_transition") == "harmed" else 0.0 for row in rows]
    harmed = [
        margin
        for row, margin in zip(rows, margins, strict=True)
        if row["correctness_transition"] == "harmed"
    ]
    preserved = [
        margin
        for row, margin in zip(rows, margins, strict=True)
        if row["correctness_transition"] == "preserved_correct"
    ]
    thresholds = [
        _simulate_threshold(rows, margin_field=margin_field, threshold=threshold)
        for threshold in _threshold_candidates(margins)
    ]
    viable = [
        row
        for row in thresholds
        if row["accuracy_delta_vs_dense"] >= quality_delta_floor
        and row["speedup_dense_over_active"] > min_speedup
        and row["harmed_retried"] > 0
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "margin_field": margin_field,
        "timing_policy": (
            "charge composed confidence capture because the gate needs it; subtract dense "
            "confidence capture because dense retry would not rescore confidence"
        ),
        "n_items": len(rows),
        "dense_accuracy": _accuracy(rows, "dense_correct"),
        "composed_accuracy": _accuracy(rows, "composed_correct"),
        "harmed_count": len(harmed),
        "preserved_correct_count": len(preserved),
        "harmed_margin_mean": _mean(harmed),
        "preserved_correct_margin_mean": _mean(preserved),
        "harmed_margin_median": _median(harmed),
        "preserved_correct_margin_median": _median(preserved),
        "pearson_margin_vs_harmed": _pearson(margins, harm_labels),
        "risk_auc_harmed_lower_margin": _risk_auc_harmed_lower(harmed, preserved),
        "quality_delta_floor": quality_delta_floor,
        "min_speedup": min_speedup,
        "viable_threshold_count": len(viable),
        "best_viable_by_speedup": max(
            viable,
            key=lambda row: (row["speedup_dense_over_active"], row["active_accuracy"]),
            default=None,
        ),
        "thresholds": thresholds,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paired-items", type=Path, required=True, action="append")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--margin-field",
        default="composed_first_generated_candidate_top2_margin",
        help=(
            "Paired-row margin used for retry gating. Candidate-letter margin is the "
            "default because full-vocab top-2 can be dominated by format tokens."
        ),
    )
    parser.add_argument("--quality-delta-floor", type=float, default=-0.05)
    parser.add_argument("--min-speedup", type=float, default=1.0)
    args = parser.parse_args()

    payload = analyze(
        _read_paired_rows(args.paired_items),
        margin_field=str(args.margin_field),
        quality_delta_floor=float(args.quality_delta_floor),
        min_speedup=float(args.min_speedup),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
