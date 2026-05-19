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


def _optional_finite(payload: dict[str, Any], field: str, *, label: str) -> float | None:
    if field not in payload or payload[field] is None:
        return None
    return _finite(payload, field, label=label)


def _nonnegative_int(payload: dict[str, Any], field: str, *, label: str) -> int:
    value = payload.get(field)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label}: summary.{field} must be a non-negative integer")
    return value


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
    n = _nonnegative_int(summary, "n", label=label)
    harmed_count = _nonnegative_int(summary, "harmed_count", label=label)
    if n <= 0:
        raise ValueError(f"{label}: summary.n must be positive")
    if harmed_count < 0 or harmed_count > n:
        raise ValueError(f"{label}: summary.harmed_count must be between 0 and n")
    observed = _finite_positive(summary, "e2e_speedup_dense_over_composed", label=label)
    prefill_ceiling = _finite_positive(summary, "prefill_only_e2e_ceiling_speedup", label=label)
    prefill_vision_ceiling = _finite_positive(
        summary,
        "prefill_plus_vision_e2e_ceiling_speedup",
        label=label,
    )
    tail_audit = summary.get("tail_audit")
    if tail_audit is not None and not isinstance(tail_audit, dict):
        raise ValueError(f"{label}: summary.tail_audit must be an object or null")
    text_ceiling = (
        _optional_finite(
            tail_audit,
            "prefill_plus_vision_plus_text_generation_e2e_ceiling_speedup",
            label=label,
        )
        if isinstance(tail_audit, dict)
        else None
    )
    return {
        "label": label,
        "source_path": str(path),
        "n": n,
        "observed_e2e_speedup": observed,
        "prefill_only_ceiling_speedup": prefill_ceiling,
        "prefill_plus_vision_ceiling_speedup": prefill_vision_ceiling,
        "prefill_plus_vision_plus_text_generation_ceiling_speedup": text_ceiling,
        "prefill_only_relative_error": (observed - prefill_ceiling) / prefill_ceiling,
        "prefill_plus_vision_relative_error": (observed - prefill_vision_ceiling)
        / prefill_vision_ceiling,
        "prefill_plus_vision_plus_text_generation_relative_error": (
            ((observed - text_ceiling) / text_ceiling) if text_ceiling is not None else None
        ),
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
        "harmed_count": harmed_count,
        "harm_rate": harmed_count / n,
        "tail_audit": tail_audit,
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


def _pearson(x_values: list[float], y_values: list[float]) -> float | None:
    if len(x_values) != len(y_values) or len(x_values) < 2:
        return None
    x_mean = _mean(x_values)
    y_mean = _mean(y_values)
    ss_x = sum((x - x_mean) ** 2 for x in x_values)
    ss_y = sum((y - y_mean) ** 2 for y in y_values)
    if ss_x == 0.0 or ss_y == 0.0:
        return None
    return sum(
        (x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values, strict=True)
    ) / math.sqrt(ss_x * ss_y)


def _ols_multi(features: list[list[float]], y_values: list[float]) -> dict[str, Any]:
    if len(features) != len(y_values) or not features:
        raise ValueError("multi-feature OLS requires paired rows")
    n = len(y_values)
    p = len(features[0])
    if any(len(row) != p for row in features):
        raise ValueError("multi-feature OLS rows have inconsistent width")
    if n <= p + 1:
        raise ValueError("multi-feature OLS requires more rows than parameters")

    # The fitted models here are intentionally tiny. Normal equations keep the
    # script dependency-free; singular matrices hard-fail instead of silently
    # regularizing an exploratory audit.
    matrix = [[1.0, *row] for row in features]
    xtx = [
        [sum(matrix[row][i] * matrix[row][j] for row in range(n)) for j in range(p + 1)]
        for i in range(p + 1)
    ]
    xty = [sum(matrix[row][i] * y_values[row] for row in range(n)) for i in range(p + 1)]
    beta = _solve_linear_system(xtx, xty)
    predictions = [sum(beta[col] * matrix[row][col] for col in range(p + 1)) for row in range(n)]
    residuals = [y - y_hat for y, y_hat in zip(y_values, predictions, strict=True)]
    y_mean = _mean(y_values)
    ss_res = sum(residual**2 for residual in residuals)
    ss_tot = sum((y - y_mean) ** 2 for y in y_values)
    return {
        "coefficients": beta,
        "r2": 1.0 - (ss_res / ss_tot) if ss_tot else 1.0,
        "rmse": math.sqrt(ss_res / n),
        "max_abs_error": max(abs(residual) for residual in residuals),
    }


def _solve_linear_system(matrix: list[list[float]], vector: list[float]) -> list[float]:
    n = len(vector)
    augmented = [row[:] + [rhs] for row, rhs in zip(matrix, vector, strict=True)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda row: abs(augmented[row][col]))
        if abs(augmented[pivot][col]) < 1e-12:
            raise ValueError("multi-feature OLS design matrix is singular")
        augmented[col], augmented[pivot] = augmented[pivot], augmented[col]
        pivot_value = augmented[col][col]
        for idx in range(col, n + 1):
            augmented[col][idx] /= pivot_value
        for row in range(n):
            if row == col:
                continue
            factor = augmented[row][col]
            for idx in range(col, n + 1):
                augmented[row][idx] -= factor * augmented[col][idx]
    return [augmented[row][n] for row in range(n)]


def _loocv_rmse(features: list[list[float]], y_values: list[float]) -> float:
    if len(features) <= len(features[0]) + 2:
        raise ValueError("LOOCV requires enough rows to leave one out")
    squared_errors: list[float] = []
    for held_out in range(len(y_values)):
        train_features = [row for idx, row in enumerate(features) if idx != held_out]
        train_y = [value for idx, value in enumerate(y_values) if idx != held_out]
        model = _ols_multi(train_features, train_y)
        beta = [float(value) for value in model["coefficients"]]
        prediction = beta[0] + sum(
            beta[idx + 1] * features[held_out][idx] for idx in range(len(features[held_out]))
        )
        squared_errors.append((y_values[held_out] - prediction) ** 2)
    return math.sqrt(_mean(squared_errors))


def _error_summary(rows: list[dict[str, Any]], *, field: str) -> dict[str, float]:
    errors = [float(row[field]) for row in rows if row[field] is not None]
    return {
        "mean_relative_error": _mean(errors),
        "mean_abs_relative_error": _mean([abs(error) for error in errors]),
        "max_abs_relative_error": max(abs(error) for error in errors),
    }


def _residual_audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    residual_rows = []
    for row in rows:
        residual = float(row["prefill_plus_vision_relative_error"])
        tail_audit = row.get("tail_audit")
        residual_rows.append(
            {
                "label": row["label"],
                "observed_e2e_speedup": row["observed_e2e_speedup"],
                "prefill_plus_vision_ceiling_speedup": row["prefill_plus_vision_ceiling_speedup"],
                "prefill_plus_vision_relative_error": residual,
                "harm_rate": row["harm_rate"],
                "tail_audit": tail_audit,
            }
        )
    harm_rates = [float(row["harm_rate"]) for row in rows]
    relative_errors = [float(row["prefill_plus_vision_relative_error"]) for row in rows]
    payload: dict[str, Any] = {
        "rows_by_abs_prefill_plus_vision_error": sorted(
            residual_rows,
            key=lambda row: abs(float(row["prefill_plus_vision_relative_error"])),
            reverse=True,
        ),
        "pearson_harm_rate_vs_prefill_plus_vision_relative_error": _pearson(
            harm_rates,
            relative_errors,
        ),
        "interpretation": (
            "exploratory: harm-rate residual correlation is useful for diagnosis, "
            "but too small-n for a confirmatory fitted speedup claim"
        ),
    }
    if len(rows) >= 5:
        observed = [float(row["observed_e2e_speedup"]) for row in rows]
        prefill_plus_vision = [float(row["prefill_plus_vision_ceiling_speedup"]) for row in rows]
        base_features = [[value] for value in prefill_plus_vision]
        harm_features = [
            [float(row["prefill_plus_vision_ceiling_speedup"]), float(row["harm_rate"])]
            for row in rows
        ]
        exploratory_key = "exploratory_ols_observed_e2e_vs_prefill_plus_vision_and_harm_rate"
        payload[exploratory_key] = {
            "feature_names": [
                "intercept",
                "prefill_plus_vision_ceiling_speedup",
                "harm_rate",
            ],
        }
        try:
            payload[exploratory_key].update(
                {
                    "fit": _ols_multi(harm_features, observed),
                    "baseline_prefill_plus_vision_loocv_rmse": _loocv_rmse(
                        base_features,
                        observed,
                    ),
                    "harm_augmented_loocv_rmse": _loocv_rmse(harm_features, observed),
                    "skipped_reason": None,
                }
            )
        except ValueError as exc:
            payload[exploratory_key]["fit"] = None
            payload[exploratory_key]["baseline_prefill_plus_vision_loocv_rmse"] = None
            payload[exploratory_key]["harm_augmented_loocv_rmse"] = None
            payload[exploratory_key]["skipped_reason"] = str(exc)
    return payload


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
        "residual_audit": _residual_audit(rows),
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
