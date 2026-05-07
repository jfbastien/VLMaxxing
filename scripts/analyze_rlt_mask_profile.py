#!/usr/bin/env python3
"""Analyze RLT mask-profile artifacts and emit early-cancel decisions."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "rlt_mask_profile_analysis_v1"
POSITIVE_CONTROL_KINDS = {"fixed_camera_positive"}
STATIC_KINDS = {"exact_static", "single_frame_repeat", "fixed_camera_positive"}
MOTION_KINDS = {"all_motion", "camera_pan"}


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


def _has_non_synthetic_jaccard(rows: list[dict[str, Any]]) -> bool:
    for row in rows:
        if row.get("pixel_novelty_jaccard") is None:
            continue
        meta = row.get("item_meta")
        if not isinstance(meta, dict) or meta.get("source") != "synthetic":
            return True
    return False


def analyze(
    rows: list[dict[str, Any]],
    *,
    positive_reduction_gate: float,
    co_cover_jaccard_gate: float,
    strong_co_cover_jaccard_gate: float,
    min_static_motion_gap: float,
) -> dict[str, Any]:
    positive_rows = _rows_for_kinds(rows, POSITIVE_CONTROL_KINDS)
    static_rows = _rows_for_kinds(rows, STATIC_KINDS)
    motion_rows = _rows_for_kinds(rows, MOTION_KINDS)
    positive_reductions = _reductions(positive_rows)
    static_reductions = _reductions(static_rows)
    motion_reductions = _reductions(motion_rows)
    jaccards = _jaccards(rows)
    has_non_synthetic_jaccard = _has_non_synthetic_jaccard(rows)

    median_positive_reduction = _median(positive_reductions)
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
    if strong_co_cover_null:
        decisions.append(
            {
                "decision": "stop_or_contract",
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
    if not decisions:
        decisions.append({"decision": "continue", "reason": "no_early_cancel_gate_fired"})

    return {
        "n_items": len(rows),
        "bucket_counts": {
            "positive_control": len(positive_rows),
            "static": len(static_rows),
            "motion": len(motion_rows),
            "pixel_novelty_jaccard": len(jaccards),
        },
        "median_positive_reduction": median_positive_reduction,
        "positive_control_missing": positive_control_missing,
        "positive_control_pass": positive_control_pass if not positive_control_missing else None,
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
    args = parser.parse_args()

    schema, rows = _load_jsonl(args.profile_jsonl)
    analysis = analyze(
        rows,
        positive_reduction_gate=args.positive_reduction_gate,
        co_cover_jaccard_gate=args.co_cover_jaccard_gate,
        strong_co_cover_jaccard_gate=args.strong_co_cover_jaccard_gate,
        min_static_motion_gap=args.min_static_motion_gap,
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
        },
        **analysis,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "decisions": payload["decisions"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
