#!/usr/bin/env python3
"""Analyze Track B compact vision execution against a dense Qwen arm."""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open() as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def _index(rows: list[dict[str, Any]], *, label: str) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        item_id = str(row["item_id"])
        if item_id in indexed:
            raise ValueError(f"duplicate {label} item_id: {item_id}")
        indexed[item_id] = row
    return indexed


def _timing(row: dict[str, Any], key: str) -> float:
    timings = row.get("timing_ms")
    if not isinstance(timings, dict):
        raise ValueError(f"missing timing_ms in {row.get('item_id')}")
    value = timings.get(key)
    if value is None:
        raise ValueError(f"missing timing_ms.{key} in {row.get('item_id')}")
    return float(value)


def _paired_rows(
    dense_rows: list[dict[str, Any]], sparse_rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    dense = _index(dense_rows, label="dense")
    sparse = _index(sparse_rows, label="sparse")
    if set(dense) != set(sparse):
        raise ValueError(
            "dense/sparse item mismatch: "
            f"missing_sparse={sorted(set(dense) - set(sparse))[:5]}, "
            f"missing_dense={sorted(set(sparse) - set(dense))[:5]}"
        )
    paired: list[dict[str, Any]] = []
    for item_id in sorted(dense):
        dense_row = dense[item_id]
        sparse_row = sparse[item_id]
        dense_correct = bool(dense_row.get("correct", False))
        sparse_correct = bool(sparse_row.get("correct", False))
        paired.append(
            {
                "item_id": item_id,
                "group": dense_row.get("group"),
                "dense_correct": dense_correct,
                "sparse_correct": sparse_correct,
                "dense_choice_index": dense_row.get("choice_index"),
                "sparse_choice_index": sparse_row.get("choice_index"),
                "dense_parse_failure": bool(dense_row.get("parse_failure", False)),
                "sparse_parse_failure": bool(sparse_row.get("parse_failure", False)),
                "dense_decode_ms": _timing(dense_row, "decode"),
                "sparse_decode_ms": _timing(sparse_row, "decode"),
                "dense_processor_ms": _timing(dense_row, "processor"),
                "sparse_processor_ms": _timing(sparse_row, "processor"),
                "dense_vision_ms": _timing(dense_row, "vision"),
                "sparse_vision_ms": _timing(sparse_row, "vision"),
                "dense_generate_ms": _timing(dense_row, "generate"),
                "sparse_generate_ms": _timing(sparse_row, "generate"),
                "dense_end_to_end_ms": _timing(dense_row, "end_to_end"),
                "sparse_end_to_end_ms": _timing(sparse_row, "end_to_end"),
                "sparse_kept_groups": sparse_row.get("kept_groups"),
                "sparse_total_groups": sparse_row.get("total_groups"),
            }
        )
    return paired


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _accuracy(rows: list[dict[str, Any]], key: str) -> float:
    return sum(bool(row[key]) for row in rows) / len(rows) if rows else 0.0


def _bootstrap_ci(
    rows: list[dict[str, Any]],
    *,
    metric: Callable[[list[dict[str, Any]]], float],
    n_bootstrap: int = 10_000,
    seed: int = 20260427,
) -> list[float]:
    if not rows:
        return [0.0, 0.0]
    by_group: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_group[str(row["item_id"])].append(row)
    keys = sorted(by_group)
    rng = random.Random(seed)
    samples: list[float] = []
    for _ in range(n_bootstrap):
        sample_rows: list[dict[str, Any]] = []
        for key in rng.choices(keys, k=len(keys)):
            sample_rows.extend(by_group[key])
        samples.append(metric(sample_rows))
    samples.sort()
    return [
        samples[int(0.025 * (len(samples) - 1))],
        samples[int(0.975 * (len(samples) - 1))],
    ]


def _accuracy_delta(rows: list[dict[str, Any]]) -> float:
    return _accuracy(rows, "sparse_correct") - _accuracy(rows, "dense_correct")


def _ratio(rows: list[dict[str, Any]], numerator_key: str, denominator_key: str) -> float:
    numerator = sum(float(row[numerator_key]) for row in rows)
    denominator = sum(float(row[denominator_key]) for row in rows)
    return numerator / denominator if denominator > 0 else 0.0


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    dense_vision = sum(float(row["dense_vision_ms"]) for row in rows)
    sparse_vision = sum(float(row["sparse_vision_ms"]) for row in rows)
    dense_e2e = sum(float(row["dense_end_to_end_ms"]) for row in rows)
    sparse_e2e = sum(float(row["sparse_end_to_end_ms"]) for row in rows)
    vision_share_dense = dense_vision / dense_e2e if dense_e2e > 0 else 0.0
    vision_reduction = 1.0 - (sparse_vision / dense_vision) if dense_vision > 0 else 0.0
    predicted_e2e_speedup = (
        1.0 / (1.0 - vision_share_dense * vision_reduction)
        if vision_share_dense * vision_reduction < 1.0
        else None
    )
    actual_e2e_speedup = dense_e2e / sparse_e2e if sparse_e2e > 0 else None
    keep_rates = [
        float(row["sparse_kept_groups"]) / float(row["sparse_total_groups"])
        for row in rows
        if row.get("sparse_kept_groups") is not None
        and row.get("sparse_total_groups") is not None
        and float(row["sparse_total_groups"]) > 0
    ]
    return {
        "n": len(rows),
        "dense_accuracy": _accuracy(rows, "dense_correct"),
        "sparse_accuracy": _accuracy(rows, "sparse_correct"),
        "accuracy_delta_sparse_minus_dense": _accuracy_delta(rows),
        "accuracy_delta_sparse_minus_dense_ci95": _bootstrap_ci(rows, metric=_accuracy_delta),
        "choice_agreement": sum(
            row["dense_choice_index"] == row["sparse_choice_index"] for row in rows
        )
        / len(rows),
        "dense_parse_failures": sum(row["dense_parse_failure"] for row in rows),
        "sparse_parse_failures": sum(row["sparse_parse_failure"] for row in rows),
        "mean_keep_rate": _mean(keep_rates),
        "vision_share_dense": vision_share_dense,
        "vision_reduction": vision_reduction,
        "vision_speedup_dense_over_sparse": dense_vision / sparse_vision
        if sparse_vision > 0
        else None,
        "actual_e2e_speedup_dense_over_sparse": actual_e2e_speedup,
        "predicted_e2e_speedup_from_vision_only": predicted_e2e_speedup,
        "actual_minus_predicted_e2e_speedup": (
            actual_e2e_speedup - predicted_e2e_speedup
            if actual_e2e_speedup is not None and predicted_e2e_speedup is not None
            else None
        ),
        "mean_dense_decode_ms": _mean([float(row["dense_decode_ms"]) for row in rows]),
        "mean_sparse_decode_ms": _mean([float(row["sparse_decode_ms"]) for row in rows]),
        "mean_dense_processor_ms": _mean([float(row["dense_processor_ms"]) for row in rows]),
        "mean_sparse_processor_ms": _mean([float(row["sparse_processor_ms"]) for row in rows]),
        "mean_dense_vision_ms": _mean([float(row["dense_vision_ms"]) for row in rows]),
        "mean_sparse_vision_ms": _mean([float(row["sparse_vision_ms"]) for row in rows]),
        "mean_dense_generate_ms": _mean([float(row["dense_generate_ms"]) for row in rows]),
        "mean_sparse_generate_ms": _mean([float(row["sparse_generate_ms"]) for row in rows]),
        "mean_dense_end_to_end_ms": _mean([float(row["dense_end_to_end_ms"]) for row in rows]),
        "mean_sparse_end_to_end_ms": _mean([float(row["sparse_end_to_end_ms"]) for row in rows]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dense-jsonl", type=Path, required=True)
    parser.add_argument("--sparse-jsonl", type=Path, required=True)
    parser.add_argument("--dense-summary", type=Path, required=True)
    parser.add_argument("--sparse-summary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--paired-items", type=Path, default=None)
    parser.add_argument("--expected-items", type=int, default=60)
    args = parser.parse_args()

    dense_rows = _load_jsonl(args.dense_jsonl)
    sparse_rows = _load_jsonl(args.sparse_jsonl)
    dense_summary = json.loads(args.dense_summary.read_text())
    sparse_summary = json.loads(args.sparse_summary.read_text())
    rows = _paired_rows(dense_rows, sparse_rows)
    summary = _summarize(rows)

    payload = {
        "dense_jsonl": args.dense_jsonl.as_posix(),
        "sparse_jsonl": args.sparse_jsonl.as_posix(),
        "dense_summary": args.dense_summary.as_posix(),
        "sparse_summary": args.sparse_summary.as_posix(),
        "sparse_execution_scope": (
            "Qwen compact post-layer vision execution: dense patch embed and early "
            "vision blocks through L, compact execution for remaining vision blocks, "
            "scatter before merger so LLM prompt geometry is unchanged."
        ),
        "dense_manifest": dense_summary.get("manifest"),
        "sparse_manifest": sparse_summary.get("manifest"),
        "frame_count": sparse_summary.get("frame_count"),
        "vision_tower_layer": sparse_summary.get("vision_tower_layer"),
        "vision_tower_keep_rate": sparse_summary.get("vision_tower_keep_rate"),
        "n_paired_items": len(rows),
        "all": summary,
        "by_group": {
            group: _summarize([row for row in rows if str(row.get("group")) == group])
            for group in sorted({str(row.get("group")) for row in rows})
        },
        "pass_complete_pairing": len(rows) == args.expected_items,
        "pass_format": summary["dense_parse_failures"] == 0
        and summary["sparse_parse_failures"] == 0,
        "pass_fidelity": summary["accuracy_delta_sparse_minus_dense"] >= -0.05,
        "pass_sparse_vision": summary["vision_reduction"] >= 0.25,
        "pass_e2e_positive": summary["actual_e2e_speedup_dense_over_sparse"] is not None
        and summary["actual_e2e_speedup_dense_over_sparse"] >= 1.03,
        "pass_ceiling_explained": (
            summary["actual_minus_predicted_e2e_speedup"] is not None
            and abs(float(summary["actual_minus_predicted_e2e_speedup"])) <= 0.05
        ),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    if args.paired_items is not None:
        with args.paired_items.open("w") as handle:
            for row in rows:
                handle.write(json.dumps(row, sort_keys=True) + "\n")
    print(f"[1.63] wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
