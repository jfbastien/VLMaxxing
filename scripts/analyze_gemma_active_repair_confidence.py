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

SCHEMA_VERSION = "gemma_active_repair_confidence_v2"
QUALITY_EPSILON = 1e-12
REFERENCE_FIELDS = (
    "benchmark",
    "group",
    "answer_index",
    "dense_choice",
    "dense_correct",
    "dense_parse_failure",
)


def _read_paired_rows(paths: Iterable[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen_row_keys: dict[tuple[str, str], str] = {}
    cell_types: set[str] = set()
    for path in paths:
        with path.open("r", encoding="utf-8") as handle:
            for lineno, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError(f"{path}:{lineno} is not a JSON object")
                item_id = row.get("item_id")
                if not isinstance(item_id, str) or not item_id:
                    raise ValueError(f"{path}:{lineno} missing string item_id")
                source = f"{path}:{lineno}"
                namespace = str(path)
                cell_type = row.get("cell_type")
                if cell_type is not None:
                    if not isinstance(cell_type, str) or not cell_type:
                        raise ValueError(f"{path}:{lineno} has non-string cell_type")
                    cell_types.add(cell_type)
                    namespace = cell_type
                row_key = (namespace, item_id)
                previous_source = seen_row_keys.get(row_key)
                if previous_source is not None:
                    raise ValueError(
                        f"duplicate row key {row_key!r} in {source}; "
                        f"already seen at {previous_source}"
                    )
                seen_row_keys[row_key] = source
                row["_analysis_row_key"] = f"{namespace}:{item_id}"
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


def _margins_by_transition(
    rows: list[dict[str, Any]], margin_field: str
) -> tuple[list[float], list[float]]:
    harmed = [
        _required_float(row, margin_field)
        for row in rows
        if row["correctness_transition"] == "harmed"
    ]
    preserved = [
        _required_float(row, margin_field)
        for row in rows
        if row["correctness_transition"] == "preserved_correct"
    ]
    return harmed, preserved


def _risk_auc_harmed_lower_ci_for_rows(
    rows: list[dict[str, Any]],
    *,
    margin_field: str,
    n_bootstrap: int,
    seed: int,
) -> dict[str, Any]:
    harmed_margins, safe_margins = _margins_by_transition(rows, margin_field)
    point = _risk_auc_harmed_lower(harmed_margins, safe_margins)
    clusters: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        item_id = row.get("item_id")
        if not isinstance(item_id, str) or not item_id:
            raise ValueError(
                f"{row.get('_source_path')}:{row.get('_source_lineno')} missing item_id"
            )
        clusters.setdefault(item_id, []).append(row)
    payload: dict[str, Any] = {
        "point": point,
        "lower_95": None,
        "upper_95": None,
        "n_bootstrap": 0,
        "n_bootstrap_requested": n_bootstrap,
        "seed": seed,
        "bootstrap_unit": "item_id_cluster",
        "unique_item_count": len(clusters),
    }
    if point is None:
        return payload
    rng = np.random.default_rng(seed)
    cluster_ids = np.asarray(sorted(clusters), dtype=object)
    samples: list[float] = []
    attempts = 0
    max_attempts = n_bootstrap * 20
    while len(samples) < n_bootstrap and attempts < max_attempts:
        attempts += 1
        sampled = cluster_ids[rng.integers(0, len(cluster_ids), size=len(cluster_ids))]
        sample_rows: list[dict[str, Any]] = []
        for cluster_id in sampled:
            sample_rows.extend(clusters[str(cluster_id)])
        harmed_sample, safe_sample = _margins_by_transition(sample_rows, margin_field)
        sample_auc = _risk_auc_harmed_lower(harmed_sample, safe_sample)
        if sample_auc is not None:
            samples.append(sample_auc)
    if not samples:
        return payload
    payload.update(
        {
            "lower_95": float(np.quantile(samples, 0.025)),
            "upper_95": float(np.quantile(samples, 0.975)),
            "n_bootstrap": len(samples),
            "bootstrap_attempts": attempts,
        }
    )
    return payload


def _per_cell_type_auc(rows: list[dict[str, Any]], margin_field: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        cell_type = row.get("cell_type")
        key = str(cell_type) if cell_type is not None else str(row["_source_path"])
        grouped.setdefault(key, []).append(row)
    summaries = []
    for cell_type, group_rows in sorted(grouped.items()):
        harmed, preserved = _margins_by_transition(group_rows, margin_field)
        summaries.append(
            {
                "cell_type": cell_type,
                "n_items": len(group_rows),
                "unique_item_count": len({str(row["item_id"]) for row in group_rows}),
                "harmed_count": len(harmed),
                "preserved_correct_count": len(preserved),
                "risk_auc_harmed_lower_margin": _risk_auc_harmed_lower(harmed, preserved),
            }
        )
    return summaries


def _pooled_status(
    rows: list[dict[str, Any]],
    *,
    per_cell_type_auc: list[dict[str, Any]],
) -> dict[str, Any]:
    cell_types = sorted({str(row["cell_type"]) for row in rows if row.get("cell_type") is not None})
    group_count = len(per_cell_type_auc)
    unique_item_count = len({str(row["item_id"]) for row in rows})
    warnings: list[str] = []
    role = "per_arm_primary"
    if group_count > 1:
        role = "supportive_pooled"
        warnings.append("pooled_supportive_only_multiple_sources")
    if unique_item_count < len(rows):
        warnings.append("pooled_reuses_item_ids")
    if group_count > 1 and any(
        int(summary["harmed_count"]) == 0 or int(summary["preserved_correct_count"]) == 0
        for summary in per_cell_type_auc
    ):
        warnings.append("per_arm_underpowered_or_missing_class")
    auc_points = [
        float(summary["risk_auc_harmed_lower_margin"])
        for summary in per_cell_type_auc
        if summary["risk_auc_harmed_lower_margin"] is not None
    ]
    if auc_points and min(auc_points) < 0.5 < max(auc_points):
        warnings.append("per_arm_auc_direction_conflict")
    return {
        "analysis_role": role,
        "supportive_only": role == "supportive_pooled",
        "warnings": warnings,
        "cell_type_count": len(cell_types),
        "group_count": group_count,
        "unique_item_count": unique_item_count,
        "row_count": len(rows),
    }


def _accuracy(rows: list[dict[str, Any]], field: str) -> float:
    return sum(bool(row[field]) for row in rows) / len(rows)


def _threshold_candidates(margins: list[float]) -> list[float]:
    return sorted(set(margins))


def _simulate_threshold(
    rows: list[dict[str, Any]],
    *,
    margin_field: str,
    threshold: float | None,
    policy_label: str | None = None,
    force_retry: bool | None = None,
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
        if force_retry is None:
            if threshold is None:
                raise ValueError("threshold is required unless force_retry is set")
            retry = margin <= threshold
        else:
            retry = force_retry
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
        "policy_label": policy_label,
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


def _baseline_summary(rows: list[dict[str, Any]], *, label: str) -> dict[str, Any]:
    dense_confidence_capture_ms = sum(
        (
            _required_nonnegative_float(row, "dense_first_generated_confidence_capture_ms")
            if row.get("dense_first_generated_confidence_capture_ms") is not None
            else 0.0
        )
        for row in rows
    )
    dense_total_raw_ms = sum(_required_positive_float(row, "dense_end_to_end_ms") for row in rows)
    dense_total_ms = dense_total_raw_ms - dense_confidence_capture_ms
    if dense_total_ms <= 0.0:
        raise ValueError("external baseline has nonpositive confidence-adjusted dense time")
    baseline_confidence_capture_ms = sum(
        (
            _required_nonnegative_float(row, "composed_first_generated_confidence_capture_ms")
            if row.get("composed_first_generated_confidence_capture_ms") is not None
            else 0.0
        )
        for row in rows
    )
    baseline_total_raw_ms = sum(
        _required_positive_float(row, "composed_end_to_end_ms") for row in rows
    )
    baseline_total_ms = baseline_total_raw_ms - baseline_confidence_capture_ms
    if baseline_total_ms <= 0.0:
        raise ValueError("external baseline has nonpositive confidence-adjusted total time")
    dense_accuracy = _accuracy(rows, "dense_correct")
    baseline_accuracy = _accuracy(rows, "composed_correct")
    return {
        "label": label,
        "n_items": len(rows),
        "source_paths": sorted({str(row["_source_path"]) for row in rows}),
        "cell_types": sorted(
            {str(row["cell_type"]) for row in rows if row.get("cell_type") is not None}
        ),
        "timing_policy": (
            "external no-retry baseline uses paired dense/composed end_to_end_ms "
            "and subtracts dense/composed confidence-capture time when present "
            "because a no-retry baseline would not compute a repair gate"
        ),
        "dense_accuracy": dense_accuracy,
        "baseline_accuracy": baseline_accuracy,
        "accuracy_delta_vs_dense": baseline_accuracy - dense_accuracy,
        "speedup_dense_over_baseline": dense_total_ms / baseline_total_ms,
        "baseline_total_ms": baseline_total_ms,
        "baseline_total_raw_ms": baseline_total_raw_ms,
        "baseline_confidence_capture_ms_subtracted": baseline_confidence_capture_ms,
        "dense_total_raw_ms": dense_total_raw_ms,
        "dense_confidence_capture_ms_subtracted": dense_confidence_capture_ms,
        "dense_total_ms": dense_total_ms,
    }


def _paired_item_keys(rows: list[dict[str, Any]]) -> set[str]:
    keys: set[str] = set()
    for row in rows:
        key = row.get("paired_row_key", row.get("item_id"))
        if not isinstance(key, str) or not key:
            raise ValueError(
                f"{row.get('_source_path')}:{row.get('_source_lineno')} "
                "missing string paired_row_key/item_id"
            )
        keys.add(key)
    return keys


def _reference_signature(row: dict[str, Any]) -> tuple[Any, ...]:
    values: list[Any] = []
    for field in REFERENCE_FIELDS:
        if field not in row:
            raise ValueError(
                f"{row.get('_source_path')}:{row.get('_source_lineno')} "
                f"{row.get('item_id')} missing reference field {field}"
            )
        values.append(row[field])
    return tuple(values)


def _reference_signatures_by_key(
    rows: list[dict[str, Any]], *, allow_duplicates: bool
) -> dict[str, tuple[Any, ...]]:
    signatures: dict[str, tuple[Any, ...]] = {}
    for row in rows:
        key = row.get("paired_row_key", row.get("item_id"))
        if not isinstance(key, str) or not key:
            raise ValueError(
                f"{row.get('_source_path')}:{row.get('_source_lineno')} "
                "missing string paired_row_key/item_id"
            )
        signature = _reference_signature(row)
        previous = signatures.get(key)
        if previous is not None:
            if not allow_duplicates:
                raise ValueError(f"baseline-paired-items has duplicate item key {key!r}")
            if previous != signature:
                raise ValueError(
                    f"active paired rows disagree on reference fields for item key {key!r}"
                )
        signatures[key] = signature
    return signatures


def _validate_baseline_matches_rows(
    rows: list[dict[str, Any]], baseline_rows: list[dict[str, Any]] | None
) -> None:
    if baseline_rows is None:
        return
    active_signatures = _reference_signatures_by_key(rows, allow_duplicates=True)
    baseline_signatures = _reference_signatures_by_key(baseline_rows, allow_duplicates=False)
    active_keys = set(active_signatures)
    baseline_keys = set(baseline_signatures)
    missing_from_baseline = sorted(active_keys - baseline_keys)
    extra_in_baseline = sorted(baseline_keys - active_keys)
    if missing_from_baseline or extra_in_baseline:
        raise ValueError(
            "baseline-paired-items item set does not match active paired rows: "
            f"missing_from_baseline={missing_from_baseline[:5]!r}, "
            f"extra_in_baseline={extra_in_baseline[:5]!r}"
        )
    reference_mismatches = [
        key for key in sorted(active_keys) if active_signatures[key] != baseline_signatures[key]
    ]
    if reference_mismatches:
        raise ValueError(
            "baseline-paired-items reference fields do not match active paired rows: "
            f"mismatched_item_keys={reference_mismatches[:5]!r}"
        )


def _attach_baseline_comparison(
    rows: list[dict[str, Any]], baseline: dict[str, Any] | None
) -> None:
    if baseline is None:
        return
    baseline_speedup = float(baseline["speedup_dense_over_baseline"])
    baseline_acc_delta = float(baseline["accuracy_delta_vs_dense"])
    for row in rows:
        row["accuracy_delta_vs_baseline"] = row["accuracy_delta_vs_dense"] - baseline_acc_delta
        row["active_speedup_vs_baseline"] = (
            row["speedup_dense_over_active"] / baseline_speedup if baseline_speedup > 0.0 else 0.0
        )


def analyze(
    rows: list[dict[str, Any]],
    *,
    margin_field: str,
    quality_delta_floor: float,
    min_speedup: float,
    max_retry_rate: float,
    min_harmed_retried: int,
    min_auc_lower_ci: float,
    n_bootstrap: int,
    bootstrap_seed: int,
    baseline_rows: list[dict[str, Any]] | None = None,
    baseline_accuracy_margin: float = 0.02,
) -> dict[str, Any]:
    _validate_baseline_matches_rows(rows, baseline_rows)
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
    candidates = _threshold_candidates(margins)
    no_retry = _simulate_threshold(
        rows,
        margin_field=margin_field,
        threshold=None,
        policy_label="no_retry_composed_only",
        force_retry=False,
    )
    retry_all = _simulate_threshold(
        rows,
        margin_field=margin_field,
        threshold=None,
        policy_label="retry_all_dense",
        force_retry=True,
    )
    thresholds = [
        _simulate_threshold(rows, margin_field=margin_field, threshold=threshold)
        for threshold in candidates
    ]
    comparison_baseline = (
        _baseline_summary(
            baseline_rows,
            label="external_no_retry_baseline",
        )
        if baseline_rows is not None
        else None
    )
    _attach_baseline_comparison(thresholds, comparison_baseline)
    _attach_baseline_comparison([no_retry, retry_all], comparison_baseline)
    auc_ci = _risk_auc_harmed_lower_ci_for_rows(
        rows,
        margin_field=margin_field,
        n_bootstrap=n_bootstrap,
        seed=bootstrap_seed,
    )
    auc_lower = auc_ci["lower_95"]
    auc_gate_passed = (
        auc_lower is not None and float(auc_lower) + QUALITY_EPSILON >= min_auc_lower_ci
    )
    viable = [
        row
        for row in thresholds
        if auc_gate_passed
        and row["accuracy_delta_vs_dense"] + QUALITY_EPSILON >= quality_delta_floor
        and row["speedup_dense_over_active"] + QUALITY_EPSILON >= min_speedup
        and row["retry_rate"] <= max_retry_rate + QUALITY_EPSILON
        and row["harmed_retried"] >= min_harmed_retried
        and (
            comparison_baseline is None
            or row["accuracy_delta_vs_baseline"] + QUALITY_EPSILON >= -baseline_accuracy_margin
        )
        and (
            comparison_baseline is None
            or row["active_speedup_vs_baseline"] + QUALITY_EPSILON >= 1.0
        )
    ]
    per_cell_type_auc = _per_cell_type_auc(rows, margin_field)
    return {
        "schema_version": SCHEMA_VERSION,
        "margin_field": margin_field,
        "timing_policy": (
            "charge composed confidence capture because the gate needs it; subtract dense "
            "confidence capture because dense retry would not rescore confidence"
        ),
        "n_items": len(rows),
        "source_paths": sorted({str(row["_source_path"]) for row in rows}),
        "cell_types": sorted(
            {str(row["cell_type"]) for row in rows if row.get("cell_type") is not None}
        ),
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
        "risk_auc_harmed_lower_margin_ci95": auc_ci,
        "per_cell_type_auc": per_cell_type_auc,
        "pooled_status": _pooled_status(rows, per_cell_type_auc=per_cell_type_auc),
        "min_auc_lower_ci": min_auc_lower_ci,
        "auc_gate_passed": auc_gate_passed,
        "quality_delta_floor": quality_delta_floor,
        "min_speedup": min_speedup,
        "max_retry_rate": max_retry_rate,
        "min_harmed_retried": min_harmed_retried,
        "baseline_accuracy_margin": baseline_accuracy_margin,
        "comparison_baseline": comparison_baseline,
        "viable_threshold_count": len(viable),
        "best_viable_by_speedup": max(
            viable,
            key=lambda row: (row["speedup_dense_over_active"], row["active_accuracy"]),
            default=None,
        ),
        "baseline_no_retry": no_retry,
        "baseline_retry_all": retry_all,
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
    parser.add_argument("--quality-delta-floor", type=float, default=-0.02)
    parser.add_argument("--min-speedup", type=float, default=1.254)
    parser.add_argument("--max-retry-rate", type=float, default=0.50)
    parser.add_argument("--min-harmed-retried", type=int, default=2)
    parser.add_argument("--min-auc-lower-ci", type=float, default=0.65)
    parser.add_argument("--n-bootstrap", type=int, default=2000)
    parser.add_argument("--bootstrap-seed", type=int, default=20260519)
    parser.add_argument(
        "--baseline-paired-items",
        type=Path,
        action="append",
        help=(
            "Optional no-retry baseline paired rows, usually the Q1 random_seed11 "
            "admission-off or best accepted cheap-pass baseline. Viable thresholds "
            "must match its accuracy delta within --baseline-accuracy-margin and "
            "beat its dense-normalized speedup."
        ),
    )
    parser.add_argument("--baseline-accuracy-margin", type=float, default=0.02)
    args = parser.parse_args()
    quality_delta_floor = float(args.quality_delta_floor)
    min_speedup = float(args.min_speedup)
    max_retry_rate = float(args.max_retry_rate)
    min_auc_lower_ci = float(args.min_auc_lower_ci)
    if not math.isfinite(quality_delta_floor):
        raise ValueError("--quality-delta-floor must be finite")
    if not math.isfinite(min_speedup):
        raise ValueError("--min-speedup must be finite")
    if not math.isfinite(max_retry_rate) or max_retry_rate < 0.0 or max_retry_rate > 1.0:
        raise ValueError("--max-retry-rate must be finite and in [0, 1]")
    if args.min_harmed_retried < 1:
        raise ValueError("--min-harmed-retried must be at least 1")
    if not math.isfinite(min_auc_lower_ci) or min_auc_lower_ci < 0.0 or min_auc_lower_ci > 1.0:
        raise ValueError("--min-auc-lower-ci must be finite and in [0, 1]")
    if args.n_bootstrap < 1:
        raise ValueError("--n-bootstrap must be at least 1")
    baseline_accuracy_margin = float(args.baseline_accuracy_margin)
    if not math.isfinite(baseline_accuracy_margin) or baseline_accuracy_margin < 0.0:
        raise ValueError("--baseline-accuracy-margin must be finite and nonnegative")

    payload = analyze(
        _read_paired_rows(args.paired_items),
        margin_field=str(args.margin_field),
        quality_delta_floor=quality_delta_floor,
        min_speedup=min_speedup,
        max_retry_rate=max_retry_rate,
        min_harmed_retried=int(args.min_harmed_retried),
        min_auc_lower_ci=min_auc_lower_ci,
        n_bootstrap=int(args.n_bootstrap),
        bootstrap_seed=int(args.bootstrap_seed),
        baseline_rows=(
            _read_paired_rows(args.baseline_paired_items)
            if args.baseline_paired_items is not None
            else None
        ),
        baseline_accuracy_margin=baseline_accuracy_margin,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
