#!/usr/bin/env python3
"""Fit a simple stage-cost model over paired Gemma cost-model artifacts.

This CPU-only audit consumes JSON files produced by
``analyze_gemma_paired_cost_model.py``. It does not rerun any model. The goal is
to separate a timing-mechanism claim from a quality claim: stage ceilings can
explain wall-clock speedups even when fidelity is unacceptable.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def _finite_positive(payload: dict[str, Any], field: str, *, label: str) -> float:
    value = payload.get(field)
    if not isinstance(value, int | float) or not math.isfinite(float(value)):
        raise ValueError(f"{label}: missing or non-finite summary.{field}")
    result = float(value)
    if result <= 0.0:
        raise ValueError(f"{label}: summary.{field} must be positive")
    return result


def _finite(payload: dict[str, Any], field: str, *, label: str) -> float:
    value = payload.get(field)
    if not isinstance(value, int | float) or not math.isfinite(float(value)):
        raise ValueError(f"{label}: missing or non-finite summary.{field}")
    return float(value)


def _parse_labeled_path(raw: str) -> tuple[str, Path]:
    if "=" not in raw:
        raise ValueError(f"--cost-model-json expects LABEL=PATH, got {raw!r}")
    label, path = raw.split("=", maxsplit=1)
    if not label:
        raise ValueError(f"--cost-model-json label must be non-empty: {raw!r}")
    if not path:
        raise ValueError(f"--cost-model-json path must be non-empty: {raw!r}")
    return label, Path(path)


def _load_row(raw: str) -> dict[str, Any]:
    label, path = _parse_labeled_path(raw)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "gemma_paired_cost_model_v1":
        raise ValueError(
            f"{label}: expected gemma_paired_cost_model_v1, got {payload.get('schema')!r}"
        )
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        raise ValueError(f"{label}: missing object summary")
    observed = _finite_positive(summary, "e2e_speedup_dense_over_composed", label=label)
    prefill_ceiling = _finite_positive(summary, "prefill_only_e2e_ceiling_speedup", label=label)
    prefill_vision_ceiling = _finite_positive(
        summary,
        "prefill_plus_vision_e2e_ceiling_speedup",
        label=label,
    )
    return {
        "label": label,
        "source_path": str(path),
        "n": int(summary.get("n", 0)),
        "observed_e2e_speedup": observed,
        "prefill_only_ceiling_speedup": prefill_ceiling,
        "prefill_plus_vision_ceiling_speedup": prefill_vision_ceiling,
        "prefill_only_relative_error": (observed - prefill_ceiling) / prefill_ceiling,
        "prefill_plus_vision_relative_error": (observed - prefill_vision_ceiling)
        / prefill_vision_ceiling,
        "prefill_share": _finite(summary, "dense_prefill_share_of_e2e", label=label),
        "vision_share": _finite(summary, "dense_vision_share_of_e2e", label=label),
        "other_share": _finite(summary, "dense_other_share_of_e2e", label=label),
        "prefill_speedup": _finite_positive(
            summary,
            "prefill_speedup_dense_over_composed",
            label=label,
        ),
        "vision_speedup": _finite_positive(
            summary,
            "vision_speedup_dense_over_composed",
            label=label,
        ),
        "accuracy_delta_composed_minus_dense": _finite(
            summary,
            "accuracy_delta_composed_minus_dense",
            label=label,
        ),
        "harmed_count": int(summary.get("harmed_count", 0)),
    }


def _mean(values: list[float]) -> float:
    if not values:
        raise ValueError("cannot average empty list")
    return sum(values) / len(values)


def _ols(x_values: list[float], y_values: list[float]) -> dict[str, float]:
    if len(x_values) != len(y_values) or len(x_values) < 2:
        raise ValueError("OLS requires at least two paired points")
    x_mean = _mean(x_values)
    y_mean = _mean(y_values)
    ss_x = sum((x - x_mean) ** 2 for x in x_values)
    if ss_x == 0.0:
        raise ValueError("OLS predictor has zero variance")
    slope = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values, strict=True)) / ss_x
    intercept = y_mean - slope * x_mean
    predictions = [intercept + slope * x for x in x_values]
    residuals = [y - y_hat for y, y_hat in zip(y_values, predictions, strict=True)]
    ss_res = sum(residual**2 for residual in residuals)
    ss_tot = sum((y - y_mean) ** 2 for y in y_values)
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot else 1.0
    rmse = math.sqrt(ss_res / len(y_values))
    return {
        "intercept": intercept,
        "slope": slope,
        "r2": r2,
        "rmse": rmse,
        "max_abs_error": max(abs(residual) for residual in residuals),
    }


def _error_summary(rows: list[dict[str, Any]], *, field: str) -> dict[str, float]:
    errors = [float(row[field]) for row in rows]
    return {
        "mean_relative_error": _mean(errors),
        "mean_abs_relative_error": _mean([abs(error) for error in errors]),
        "max_abs_relative_error": max(abs(error) for error in errors),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cost-model-json",
        action="append",
        default=[],
        help="Repeated LABEL=PATH entries from analyze_gemma_paired_cost_model.py.",
    )
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    if len(args.cost_model_json) < 2:
        raise ValueError("at least two --cost-model-json entries are required")
    rows = [_load_row(raw) for raw in args.cost_model_json]
    labels = [str(row["label"]) for row in rows]
    if len(labels) != len(set(labels)):
        raise ValueError(f"duplicate labels in --cost-model-json: {labels}")

    observed = [float(row["observed_e2e_speedup"]) for row in rows]
    prefill_only = [float(row["prefill_only_ceiling_speedup"]) for row in rows]
    prefill_plus_vision = [float(row["prefill_plus_vision_ceiling_speedup"]) for row in rows]
    payload = {
        "schema": "gemma_stage_cost_model_fit_v1",
        "analysis_role": "offline_stage_cost_model_fit",
        "n_artifacts": len(rows),
        "models": {
            "observed_e2e_vs_prefill_only_ceiling": _ols(prefill_only, observed),
            "observed_e2e_vs_prefill_plus_vision_ceiling": _ols(
                prefill_plus_vision,
                observed,
            ),
        },
        "error_summaries": {
            "prefill_only_ceiling": _error_summary(
                rows,
                field="prefill_only_relative_error",
            ),
            "prefill_plus_vision_ceiling": _error_summary(
                rows,
                field="prefill_plus_vision_relative_error",
            ),
        },
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
