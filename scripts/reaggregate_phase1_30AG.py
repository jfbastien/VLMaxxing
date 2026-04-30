#!/usr/bin/env python3
"""MLX-free reaggregator for Phase 1.30AG K/V cache-distance summary.

The probe driver (``run_phase1_30AG_kcache_distance_probe.py``) imports
mlx.core at module load, which initializes Metal and blocks under sandbox
mode. This script reads ``kcache_distance_rows.jsonl`` and re-emits
``kcache_distance_summary.json`` using only stdlib + numpy, so the summary
can be regenerated without re-running the 30-min capture or punching the
sandbox out.

The aggregation logic mirrors ``_emit_summary`` in the probe driver but
sources the headline numbers from ``cosine_fp32`` (which is finite at every
layer × row × arm) rather than the native fp16/bf16 ``cosine`` column
(which overflows on ~3M-element flattened cache windows).
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import numpy as np

DEFAULT_DIR = Path("research/experiments/2026/artifacts/phase1_30AG_kcache_distance_probe")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _clamped_cosine(value: float | None) -> float | None:
    if value is None:
        return None
    if value > 1.0:
        return 1.0
    if value < -1.0:
        return -1.0
    return float(value)


def _path_mean(rows: list[dict[str, Any]], path: str) -> float | None:
    values: list[float] = []
    for row in rows:
        cursor: Any = row
        try:
            for part in path.split("."):
                cursor = cursor[part]
        except (KeyError, TypeError):
            cursor = None
        if cursor is None:
            continue
        try:
            values.append(float(cursor))
        except (TypeError, ValueError):
            continue
    if not values:
        return None
    return float(np.mean(values))


def _relative_gap(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    denom = max(abs(left), abs(right), 1e-12)
    return abs(left - right) / denom


def _class_summary(class_rows: list[dict[str, Any]], class_name: str) -> dict[str, Any]:
    if not class_rows:
        return {"drift_class": class_name, "n": 0}
    return {
        "drift_class": class_name,
        "n": len(class_rows),
        "mean_reuse_keys_cosine": _path_mean(class_rows, "reuse_vs_dense.keys_mean_cosine"),
        "mean_pruned_keys_cosine": _path_mean(class_rows, "pruned_vs_dense.keys_mean_cosine"),
        "mean_reuse_values_cosine": _path_mean(class_rows, "reuse_vs_dense.values_mean_cosine"),
        "mean_pruned_values_cosine": _path_mean(class_rows, "pruned_vs_dense.values_mean_cosine"),
        "mean_reuse_keys_cosine_distance": _path_mean(
            class_rows, "reuse_vs_dense.keys_mean_cosine_distance"
        ),
        "mean_pruned_keys_cosine_distance": _path_mean(
            class_rows, "pruned_vs_dense.keys_mean_cosine_distance"
        ),
        "mean_reuse_values_cosine_distance": _path_mean(
            class_rows, "reuse_vs_dense.values_mean_cosine_distance"
        ),
        "mean_pruned_values_cosine_distance": _path_mean(
            class_rows, "pruned_vs_dense.values_mean_cosine_distance"
        ),
        "mean_reuse_keys_cosine_fp32": _clamped_cosine(
            _path_mean(class_rows, "reuse_vs_dense.keys_mean_cosine_fp32")
        ),
        "mean_pruned_keys_cosine_fp32": _clamped_cosine(
            _path_mean(class_rows, "pruned_vs_dense.keys_mean_cosine_fp32")
        ),
        "mean_reuse_values_cosine_fp32": _clamped_cosine(
            _path_mean(class_rows, "reuse_vs_dense.values_mean_cosine_fp32")
        ),
        "mean_pruned_values_cosine_fp32": _clamped_cosine(
            _path_mean(class_rows, "pruned_vs_dense.values_mean_cosine_fp32")
        ),
        "mean_reuse_keys_cosine_fp32_distance": _path_mean(
            class_rows, "reuse_vs_dense.keys_mean_cosine_fp32_distance"
        ),
        "mean_pruned_keys_cosine_fp32_distance": _path_mean(
            class_rows, "pruned_vs_dense.keys_mean_cosine_fp32_distance"
        ),
        "mean_reuse_values_cosine_fp32_distance": _path_mean(
            class_rows, "reuse_vs_dense.values_mean_cosine_fp32_distance"
        ),
        "mean_pruned_values_cosine_fp32_distance": _path_mean(
            class_rows, "pruned_vs_dense.values_mean_cosine_fp32_distance"
        ),
        "mean_reuse_keys_mean_abs": _path_mean(class_rows, "reuse_vs_dense.keys_mean_abs"),
        "mean_pruned_keys_mean_abs": _path_mean(class_rows, "pruned_vs_dense.keys_mean_abs"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_DIR)
    parser.add_argument(
        "--vision-tower-layer",
        type=int,
        default=2,
        help="Echoed into summary metadata; ignored otherwise.",
    )
    parser.add_argument(
        "--vision-tower-keep-rate",
        type=float,
        default=0.50,
        help="Echoed into summary metadata; ignored otherwise.",
    )
    args = parser.parse_args()

    row_path = args.output_dir / "kcache_distance_rows.jsonl"
    if not row_path.exists():
        raise SystemExit(f"missing rows file: {row_path}")
    output_rows = _read_jsonl(row_path)
    if not output_rows:
        raise SystemExit(f"zero rows in {row_path}")

    t0 = time.perf_counter_ns()

    # Reconstruct selection metadata from the rows.
    class_counts: dict[str, int] = {
        "shared_drift": 0,
        "reuse_only_drift": 0,
        "invalidated_only_drift": 0,
        "stable": 0,
    }
    for row in output_rows:
        class_counts[str(row["drift_class"])] = class_counts.get(str(row["drift_class"]), 0) + 1
    selection_metadata = {
        "available_by_drift_class": dict(class_counts),
        "selected_by_drift_class": dict(class_counts),
        "target_per_class": max(1, len(output_rows) // 4),
    }

    by_drift_class = {
        name: _class_summary([row for row in output_rows if row["drift_class"] == name], name)
        for name in ("shared_drift", "reuse_only_drift", "invalidated_only_drift", "stable")
    }

    keys_mean_abs_gap = _relative_gap(
        _path_mean(output_rows, "reuse_vs_dense.keys_mean_abs"),
        _path_mean(output_rows, "pruned_vs_dense.keys_mean_abs"),
    )
    values_mean_abs_gap = _relative_gap(
        _path_mean(output_rows, "reuse_vs_dense.values_mean_abs"),
        _path_mean(output_rows, "pruned_vs_dense.values_mean_abs"),
    )
    keys_cosine_distance_gap = _relative_gap(
        _path_mean(output_rows, "reuse_vs_dense.keys_mean_cosine_distance"),
        _path_mean(output_rows, "pruned_vs_dense.keys_mean_cosine_distance"),
    )
    values_cosine_distance_gap = _relative_gap(
        _path_mean(output_rows, "reuse_vs_dense.values_mean_cosine_distance"),
        _path_mean(output_rows, "pruned_vs_dense.values_mean_cosine_distance"),
    )
    keys_cosine_fp32_distance_gap = _relative_gap(
        _path_mean(output_rows, "reuse_vs_dense.keys_mean_cosine_fp32_distance"),
        _path_mean(output_rows, "pruned_vs_dense.keys_mean_cosine_fp32_distance"),
    )
    values_cosine_fp32_distance_gap = _relative_gap(
        _path_mean(output_rows, "reuse_vs_dense.values_mean_cosine_fp32_distance"),
        _path_mean(output_rows, "pruned_vs_dense.values_mean_cosine_fp32_distance"),
    )

    same_valid_lengths = bool(
        output_rows
        and all(row["reuse_vs_dense"]["keys_all_same_valid_token_length"] for row in output_rows)
        and all(row["reuse_vs_dense"]["values_all_same_valid_token_length"] for row in output_rows)
        and all(row["pruned_vs_dense"]["keys_all_same_valid_token_length"] for row in output_rows)
        and all(row["pruned_vs_dense"]["values_all_same_valid_token_length"] for row in output_rows)
    )
    n_token_length_mismatch_rows = sum(
        1
        for row in output_rows
        if not (
            row["reuse_vs_dense"]["keys_all_same_valid_token_length"]
            and row["reuse_vs_dense"]["values_all_same_valid_token_length"]
            and row["pruned_vs_dense"]["keys_all_same_valid_token_length"]
            and row["pruned_vs_dense"]["values_all_same_valid_token_length"]
        )
    )
    n_unique_followup_rows = len(
        {(str(row["video_id"]), int(row["q_index"])) for row in output_rows}
    )
    capture_row_floor = 20
    pass_h1_row_count = (
        len(output_rows) >= capture_row_floor and n_unique_followup_rows >= capture_row_floor
    )
    pass_h1_cache_states_captured = bool(
        output_rows
        and all(
            row["reuse_vs_dense"].get("keys_mean_cosine_fp32") is not None for row in output_rows
        )
        and all(
            row["reuse_vs_dense"].get("values_mean_cosine_fp32") is not None for row in output_rows
        )
        and all(
            row["pruned_vs_dense"].get("keys_mean_cosine_fp32") is not None for row in output_rows
        )
        and all(
            row["pruned_vs_dense"].get("values_mean_cosine_fp32") is not None for row in output_rows
        )
    )
    pass_h1_capture = pass_h1_row_count and pass_h1_cache_states_captured and same_valid_lengths
    pass_h2_distance_report = all(
        int(selection_metadata["selected_by_drift_class"].get(name, 0)) > 0
        for name in ("shared_drift", "reuse_only_drift", "invalidated_only_drift", "stable")
    )
    pass_h3_outcome_link = pass_h2_distance_report and all(
        by_drift_class[name].get("mean_reuse_keys_mean_abs") is not None
        for name in ("shared_drift", "reuse_only_drift", "invalidated_only_drift", "stable")
    )
    pass_h1_same_valid_lengths = same_valid_lengths
    pass_h4_saturation_test = (
        pass_h1_same_valid_lengths
        and keys_cosine_fp32_distance_gap is not None
        and values_cosine_fp32_distance_gap is not None
        and keys_cosine_fp32_distance_gap >= 0.5
        and values_cosine_fp32_distance_gap >= 0.5
    )

    layers0 = output_rows[0]["reuse_vs_dense"].get("layers", []) if output_rows else []
    cache_dtype_observed = layers0[0].get("keys_left_dtype", "?") if layers0 else "?"

    summary = {
        "phase": "1.30AG",
        "n_rows": len(output_rows),
        "n_unique_followup_rows": n_unique_followup_rows,
        "capture_row_floor": capture_row_floor,
        "max_pairs_requested": len(output_rows),
        "selection": selection_metadata,
        "vision_tower_layer": args.vision_tower_layer,
        "vision_tower_keep_rate": args.vision_tower_keep_rate,
        "cache_dtype_observed": cache_dtype_observed,
        "mean_reuse_keys_cosine": _path_mean(output_rows, "reuse_vs_dense.keys_mean_cosine"),
        "mean_pruned_keys_cosine": _path_mean(output_rows, "pruned_vs_dense.keys_mean_cosine"),
        "mean_reuse_values_cosine": _path_mean(output_rows, "reuse_vs_dense.values_mean_cosine"),
        "mean_pruned_values_cosine": _path_mean(output_rows, "pruned_vs_dense.values_mean_cosine"),
        "mean_reuse_keys_cosine_distance": _path_mean(
            output_rows, "reuse_vs_dense.keys_mean_cosine_distance"
        ),
        "mean_pruned_keys_cosine_distance": _path_mean(
            output_rows, "pruned_vs_dense.keys_mean_cosine_distance"
        ),
        "mean_reuse_values_cosine_distance": _path_mean(
            output_rows, "reuse_vs_dense.values_mean_cosine_distance"
        ),
        "mean_pruned_values_cosine_distance": _path_mean(
            output_rows, "pruned_vs_dense.values_mean_cosine_distance"
        ),
        "mean_reuse_keys_cosine_fp32": _clamped_cosine(
            _path_mean(output_rows, "reuse_vs_dense.keys_mean_cosine_fp32")
        ),
        "mean_pruned_keys_cosine_fp32": _clamped_cosine(
            _path_mean(output_rows, "pruned_vs_dense.keys_mean_cosine_fp32")
        ),
        "mean_reuse_values_cosine_fp32": _clamped_cosine(
            _path_mean(output_rows, "reuse_vs_dense.values_mean_cosine_fp32")
        ),
        "mean_pruned_values_cosine_fp32": _clamped_cosine(
            _path_mean(output_rows, "pruned_vs_dense.values_mean_cosine_fp32")
        ),
        "mean_reuse_keys_cosine_fp32_distance": _path_mean(
            output_rows, "reuse_vs_dense.keys_mean_cosine_fp32_distance"
        ),
        "mean_pruned_keys_cosine_fp32_distance": _path_mean(
            output_rows, "pruned_vs_dense.keys_mean_cosine_fp32_distance"
        ),
        "mean_reuse_values_cosine_fp32_distance": _path_mean(
            output_rows, "reuse_vs_dense.values_mean_cosine_fp32_distance"
        ),
        "mean_pruned_values_cosine_fp32_distance": _path_mean(
            output_rows, "pruned_vs_dense.values_mean_cosine_fp32_distance"
        ),
        "mean_reuse_keys_mean_abs": _path_mean(output_rows, "reuse_vs_dense.keys_mean_abs"),
        "mean_pruned_keys_mean_abs": _path_mean(output_rows, "pruned_vs_dense.keys_mean_abs"),
        "mean_reuse_values_mean_abs": _path_mean(output_rows, "reuse_vs_dense.values_mean_abs"),
        "mean_pruned_values_mean_abs": _path_mean(output_rows, "pruned_vs_dense.values_mean_abs"),
        "keys_cosine_distance_relative_gap": keys_cosine_distance_gap,
        "values_cosine_distance_relative_gap": values_cosine_distance_gap,
        "keys_cosine_fp32_distance_relative_gap": keys_cosine_fp32_distance_gap,
        "values_cosine_fp32_distance_relative_gap": values_cosine_fp32_distance_gap,
        "keys_mean_abs_relative_gap": keys_mean_abs_gap,
        "values_mean_abs_relative_gap": values_mean_abs_gap,
        "all_same_valid_token_lengths": same_valid_lengths,
        "n_token_length_mismatch_rows": n_token_length_mismatch_rows,
        "by_drift_class": by_drift_class,
        "pass_H1_row_count": pass_h1_row_count,
        "pass_H1_cache_states_captured": pass_h1_cache_states_captured,
        "pass_H1_capture": pass_h1_capture,
        "pass_H1_same_valid_lengths": pass_h1_same_valid_lengths,
        "pass_H2_distance_report": pass_h2_distance_report,
        "pass_H3_outcome_link": pass_h3_outcome_link,
        "pass_H4_saturation_test": pass_h4_saturation_test,
        "headline_pass": pass_h1_capture
        and pass_h2_distance_report
        and pass_h3_outcome_link
        and pass_h4_saturation_test,
        "row_jsonl": row_path.as_posix(),
        "wall_time_s": (time.perf_counter_ns() - t0) / 1e9,
        "reaggregated_by": "scripts/reaggregate_phase1_30AG.py",
    }
    summary_path = args.output_dir / "kcache_distance_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"[1.30AG-reaggregate] wrote {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
