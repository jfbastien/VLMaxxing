#!/usr/bin/env python3
"""Analyze RLT mask-profile artifacts and emit early-cancel decisions."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "rlt_mask_profile_analysis_v2"
POSITIVE_CONTROL_KINDS = {"fixed_camera_positive"}
STATIC_KINDS = {"exact_static", "single_frame_repeat", "fixed_camera_positive"}
MOTION_KINDS = {"all_motion", "camera_pan"}
SYNTHETIC_KEEP_RATE_TOLERANCE = 1e-6


def _load_jsonl(path: Path) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    schema: dict[str, Any] | None = None
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            payload = json.loads(stripped)
            if payload.get("kind") == "schema":
                schema = payload
            elif payload.get("kind") == "item":
                rows.append(payload)
            else:
                raise ValueError(f"unexpected row kind in {path}: {payload.get('kind')!r}")
    if schema is None:
        raise ValueError(f"{path} is missing row-0 schema metadata")
    if not rows:
        raise ValueError(f"{path} has no item rows")
    return schema, rows


def _kind(row: dict[str, Any]) -> str:
    meta = row.get("item_meta")
    if isinstance(meta, dict):
        synthetic_kind = meta.get("synthetic_kind")
        if synthetic_kind is not None:
            return str(synthetic_kind)
        group = meta.get("group")
        if group is not None:
            return str(group)
    return "unknown"


def _median(values: list[float]) -> float | None:
    return float(statistics.median(values)) if values else None


def _mean(values: list[float]) -> float | None:
    return float(sum(values) / len(values)) if values else None


def _reductions(rows: list[dict[str, Any]]) -> list[float]:
    return [1.0 - float(row["keep_rate"]) for row in rows]


def _rows_for_kinds(rows: list[dict[str, Any]], kinds: set[str]) -> list[dict[str, Any]]:
    return [row for row in rows if _kind(row) in kinds]


def _jaccards(rows: list[dict[str, Any]]) -> list[float]:
    return [
        float(row["pixel_novelty_jaccard"])
        for row in rows
        if row.get("pixel_novelty_jaccard") is not None
    ]


def _feature_scorer_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if row.get("feature_scorer_jaccard") is not None]


def _feature_scorer_summary(
    rows: list[dict[str, Any]],
    *,
    feature_jaccard_gate: float,
    feature_time_reduction_gate: float,
) -> dict[str, Any]:
    feature_rows = _feature_scorer_rows(rows)
    by_frame_count: dict[int, list[dict[str, Any]]] = {}
    for row in feature_rows:
        by_frame_count.setdefault(int(row["frame_count"]), []).append(row)

    cells: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []
    for frame_count, cell_rows in sorted(by_frame_count.items()):
        jaccards = [float(row["feature_scorer_jaccard"]) for row in cell_rows]
        scorer_ms = [
            float(row["feature_scorer_ms"])
            for row in cell_rows
            if row.get("feature_scorer_ms") is not None
        ]
        mask_ms = [float(row["mask_compute_ms"]) for row in cell_rows]
        mean_jaccard = _mean(jaccards)
        mean_scorer_ms = _mean(scorer_ms)
        mean_mask_ms = _mean(mask_ms)
        time_reduction_fraction = (
            1.0 - (mean_mask_ms / mean_scorer_ms)
            if mean_scorer_ms is not None and mean_scorer_ms > 0.0 and mean_mask_ms is not None
            else None
        )
        jaccard_pass = mean_jaccard is not None and mean_jaccard >= feature_jaccard_gate
        time_pass = (
            time_reduction_fraction is not None
            and time_reduction_fraction >= feature_time_reduction_gate
        )
        cell_pass = jaccard_pass and time_pass
        cell = {
            "n": len(cell_rows),
            "mean_feature_scorer_jaccard": mean_jaccard,
            "mean_feature_scorer_ms": mean_scorer_ms,
            "mean_rlt_mask_compute_ms": mean_mask_ms,
            "time_reduction_fraction": time_reduction_fraction,
            "jaccard_pass": jaccard_pass,
            "time_pass": time_pass,
            "pass": cell_pass,
        }
        cells[str(frame_count)] = cell
        if not cell_pass:
            failures.append({"frame_count": frame_count, **cell})

    mechanism_pass = all(cell["pass"] for cell in cells.values()) if cells else None
    return {
        "h1_5_feature_prior_present": bool(cells),
        "h1_5_feature_prior_pass": mechanism_pass,
        "h1_5_feature_prior_cells": cells,
        "h1_5_feature_prior_failures": failures,
    }


def _is_synthetic(row: dict[str, Any]) -> bool:
    meta = row.get("item_meta")
    return isinstance(meta, dict) and meta.get("source") == "synthetic"


def _has_non_synthetic_jaccard(rows: list[dict[str, Any]]) -> bool:
    for row in rows:
        if row.get("pixel_novelty_jaccard") is None:
            continue
        if not _is_synthetic(row):
            return True
    return False


def _expected_static_keep_rate(row: dict[str, Any]) -> float:
    frame_count = int(row["frame_count"])
    config = row.get("mask_config")
    if not isinstance(config, dict):
        raise ValueError(f"missing mask_config in {row.get('item_id')}")
    tubelet_size = int(config["tubelet_size"])
    if frame_count <= 0:
        raise ValueError(f"invalid frame_count in {row.get('item_id')}: {frame_count}")
    return tubelet_size / frame_count


def _synthetic_gate_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    checks: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []
    for kind in ("exact_static", "single_frame_repeat", "all_motion"):
        kind_rows = _rows_for_kinds(rows, {kind})
        if not kind_rows:
            checks[kind] = {"present": False, "pass": False}
            failures.append({"kind": kind, "reason": "missing"})
            continue
        expected = 1.0 if kind == "all_motion" else _expected_static_keep_rate(kind_rows[0])
        observed = [float(row["keep_rate"]) for row in kind_rows]
        passed = all(abs(value - expected) <= SYNTHETIC_KEEP_RATE_TOLERANCE for value in observed)
        checks[kind] = {
            "present": True,
            "pass": passed,
            "expected_keep_rate": expected,
            "observed_keep_rates": observed,
        }
        if not passed:
            failures.append(
                {
                    "kind": kind,
                    "expected_keep_rate": expected,
                    "observed_keep_rates": observed,
                }
            )
    return {
        "synthetic_gate_pass": not failures,
        "synthetic_gate_checks": checks,
        "synthetic_gate_failures": failures,
    }


def analyze(
    rows: list[dict[str, Any]],
    *,
    positive_reduction_gate: float,
    co_cover_jaccard_gate: float,
    strong_co_cover_jaccard_gate: float,
    min_static_motion_gap: float,
    feature_jaccard_gate: float,
    feature_time_reduction_gate: float,
) -> dict[str, Any]:
    positive_rows = _rows_for_kinds(rows, POSITIVE_CONTROL_KINDS)
    real_positive_rows = [row for row in positive_rows if not _is_synthetic(row)]
    static_rows = _rows_for_kinds(rows, STATIC_KINDS)
    motion_rows = _rows_for_kinds(rows, MOTION_KINDS)
    positive_reductions = _reductions(positive_rows)
    real_positive_reductions = _reductions(real_positive_rows)
    static_reductions = _reductions(static_rows)
    motion_reductions = _reductions(motion_rows)
    jaccards = _jaccards(rows)
    has_non_synthetic_jaccard = _has_non_synthetic_jaccard(rows)
    synthetic_gates = _synthetic_gate_summary(rows)
    feature_prior = _feature_scorer_summary(
        rows,
        feature_jaccard_gate=feature_jaccard_gate,
        feature_time_reduction_gate=feature_time_reduction_gate,
    )

    median_positive_reduction = _median(positive_reductions)
    median_real_positive_reduction = _median(real_positive_reductions)
    median_static_reduction = _median(static_reductions)
    median_motion_reduction = _median(motion_reductions)
    static_motion_gap = (
        median_static_reduction - median_motion_reduction
        if median_static_reduction is not None and median_motion_reduction is not None
        else None
    )
    mean_jaccard = _mean(jaccards)
    median_jaccard = _median(jaccards)

    positive_control_pass = (
        median_positive_reduction is not None
        and median_positive_reduction >= positive_reduction_gate
    )
    real_positive_control_pass = (
        median_real_positive_reduction is not None
        and median_real_positive_reduction >= positive_reduction_gate
    )
    positive_control_missing = median_positive_reduction is None
    co_cover_null = (
        mean_jaccard is not None
        and has_non_synthetic_jaccard
        and mean_jaccard >= co_cover_jaccard_gate
    )
    strong_co_cover_null = (
        mean_jaccard is not None
        and has_non_synthetic_jaccard
        and mean_jaccard >= strong_co_cover_jaccard_gate
    )
    synthetic_co_cover_diagnostic = (
        mean_jaccard is not None
        and not has_non_synthetic_jaccard
        and mean_jaccard >= co_cover_jaccard_gate
    )
    bucket_gap_pass = static_motion_gap is not None and static_motion_gap >= min_static_motion_gap

    decisions: list[dict[str, Any]] = []
    skip_phases: list[str] = []
    if not synthetic_gates["synthetic_gate_pass"]:
        decisions.append(
            {
                "decision": "stop",
                "reason": "synthetic_mask_gate_failed",
                "details": synthetic_gates["synthetic_gate_failures"],
            }
        )
        skip_phases.extend(["RLT-2G", "RLT-3G-A", "RLT-3G-B", "RLT-4Q", "RLT-5G", "RLT-5Q"])
    if not positive_control_missing and not positive_control_pass:
        decisions.append(
            {
                "decision": "stop",
                "reason": "positive_control_reduction_failed",
                "details": {
                    "median_positive_reduction": median_positive_reduction,
                    "gate": positive_reduction_gate,
                },
            }
        )
        skip_phases.extend(["RLT-2G", "RLT-3G-A", "RLT-3G-B", "RLT-4Q", "RLT-5G", "RLT-5Q"])
    if median_real_positive_reduction is not None and not real_positive_control_pass:
        decisions.append(
            {
                "decision": "stop",
                "reason": "real_positive_control_reduction_failed",
                "details": {
                    "median_real_positive_reduction": median_real_positive_reduction,
                    "gate": positive_reduction_gate,
                },
            }
        )
        skip_phases.extend(["RLT-2G", "RLT-3G-A", "RLT-3G-B", "RLT-4Q", "RLT-5G", "RLT-5Q"])
    if strong_co_cover_null:
        decisions.append(
            {
                "decision": "stop",
                "reason": "rlt_pixel_novelty_strong_co_cover",
                "details": {"mean_jaccard": mean_jaccard, "gate": strong_co_cover_jaccard_gate},
            }
        )
        skip_phases.extend(["RLT-2G", "RLT-3G-A", "RLT-3G-B", "RLT-4Q", "RLT-5G", "RLT-5Q"])
    elif co_cover_null:
        decisions.append(
            {
                "decision": "skip_h1_5b",
                "reason": "rlt_pixel_novelty_co_cover",
                "details": {"mean_jaccard": mean_jaccard, "gate": co_cover_jaccard_gate},
            }
        )
        skip_phases.append("RLT-1.5b")
    if static_motion_gap is not None and not bucket_gap_pass:
        decisions.append(
            {
                "decision": "downgrade",
                "reason": "static_motion_bucket_gap_null",
                "details": {"static_motion_gap": static_motion_gap, "gate": min_static_motion_gap},
            }
        )
        skip_phases.append("RLT-4Q")
    if feature_prior["h1_5_feature_prior_present"] and not feature_prior["h1_5_feature_prior_pass"]:
        decisions.append(
            {
                "decision": "skip_h1_5b",
                "reason": "feature_prior_mechanism_failed",
                "details": feature_prior["h1_5_feature_prior_failures"],
            }
        )
        skip_phases.append("RLT-1.5b")
    if not decisions:
        decisions.append({"decision": "continue", "reason": "no_early_cancel_gate_fired"})

    return {
        "n_items": len(rows),
        **synthetic_gates,
        "bucket_counts": {
            "positive_control": len(positive_rows),
            "real_positive_control": len(real_positive_rows),
            "static": len(static_rows),
            "motion": len(motion_rows),
            "pixel_novelty_jaccard": len(jaccards),
            "feature_scorer_jaccard": len(_feature_scorer_rows(rows)),
        },
        **feature_prior,
        "median_positive_reduction": median_positive_reduction,
        "median_real_positive_reduction": median_real_positive_reduction,
        "positive_control_missing": positive_control_missing,
        "positive_control_pass": positive_control_pass if not positive_control_missing else None,
        "real_positive_control_pass": real_positive_control_pass
        if median_real_positive_reduction is not None
        else None,
        "median_static_reduction": median_static_reduction,
        "median_motion_reduction": median_motion_reduction,
        "static_motion_gap": static_motion_gap,
        "bucket_gap_pass": bucket_gap_pass if static_motion_gap is not None else None,
        "mean_pixel_novelty_jaccard": mean_jaccard,
        "median_pixel_novelty_jaccard": median_jaccard,
        "has_non_synthetic_jaccard": has_non_synthetic_jaccard,
        "synthetic_co_cover_diagnostic": synthetic_co_cover_diagnostic,
        "co_cover_null": co_cover_null,
        "strong_co_cover_null": strong_co_cover_null,
        "decisions": decisions,
        "skip_phases": sorted(set(skip_phases)),
        "ordered_next_tests": [
            "RLT-1 positive-control and pixel-novelty co-cover analysis",
            "RLT-2G Gemma admission smoke only if RLT-1 gates survive",
            "RLT-3G-A scorer-stacking only if Gemma RLT admission survives",
            "RLT-3G-B denominator-separation only after prefill-split smoke artifact",
            "RLT-4Q/RLT-5Q only after Gemma evidence avoids early nulls",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile-jsonl", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--positive-reduction-gate", type=float, default=0.50)
    parser.add_argument("--co-cover-jaccard-gate", type=float, default=0.90)
    parser.add_argument("--strong-co-cover-jaccard-gate", type=float, default=0.95)
    parser.add_argument("--min-static-motion-gap", type=float, default=0.05)
    parser.add_argument("--feature-jaccard-gate", type=float, default=0.80)
    parser.add_argument("--feature-time-reduction-gate", type=float, default=0.50)
    args = parser.parse_args()

    schema, rows = _load_jsonl(args.profile_jsonl)
    analysis = analyze(
        rows,
        positive_reduction_gate=args.positive_reduction_gate,
        co_cover_jaccard_gate=args.co_cover_jaccard_gate,
        strong_co_cover_jaccard_gate=args.strong_co_cover_jaccard_gate,
        min_static_motion_gap=args.min_static_motion_gap,
        feature_jaccard_gate=args.feature_jaccard_gate,
        feature_time_reduction_gate=args.feature_time_reduction_gate,
    )
    payload = {
        "schema_version": SCHEMA_VERSION,
        "profile_jsonl": str(args.profile_jsonl),
        "profile_schema": schema,
        "gates": {
            "positive_reduction_gate": args.positive_reduction_gate,
            "co_cover_jaccard_gate": args.co_cover_jaccard_gate,
            "strong_co_cover_jaccard_gate": args.strong_co_cover_jaccard_gate,
            "min_static_motion_gap": args.min_static_motion_gap,
            "feature_jaccard_gate": args.feature_jaccard_gate,
            "feature_time_reduction_gate": args.feature_time_reduction_gate,
        },
        **analysis,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "decisions": payload["decisions"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
