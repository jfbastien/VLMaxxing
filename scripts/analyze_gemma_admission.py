#!/usr/bin/env python3
"""Analyze Gemma visual-admission JSONL artifacts.

The Gemma admission runner writes paired dense/pruned results in each item row.
This analyzer turns those rows into gate decisions so the autonomous RLT queue
can stop before H3 cells when RLT-style admission is already quality- or
overhead-dominated.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "gemma_admission_analysis_v2"


def _load_jsonl(path: Path) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    schema: dict[str, Any] | None = None
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            payload = json.loads(stripped)
            kind = payload.get("kind")
            if kind == "schema":
                schema = payload
            elif kind in (None, "item"):
                rows.append(payload)
            else:
                raise ValueError(f"unexpected row kind in {path}: {kind!r}")
    if schema is None:
        raise ValueError(f"{path} is missing row-0 schema metadata")
    if not rows:
        raise ValueError(f"{path} has no item rows")
    return schema, rows


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _timing(row: dict[str, Any], branch: str, key: str) -> float:
    timings = row.get(f"{branch}_timing_ms")
    if not isinstance(timings, dict):
        raise ValueError(f"missing {branch}_timing_ms in {row.get('item_id')}")
    value = timings.get(key)
    if value is None:
        raise ValueError(f"missing {branch}_timing_ms.{key} in {row.get('item_id')}")
    return float(value)


def _optional_timing(row: dict[str, Any], branch: str, *keys: str) -> float:
    timings = row.get(f"{branch}_timing_ms")
    if not isinstance(timings, dict):
        raise ValueError(f"missing {branch}_timing_ms in {row.get('item_id')}")
    for key in keys:
        value = timings.get(key)
        if value is not None:
            return float(value)
    raise ValueError(f"missing any of {branch}_timing_ms.{list(keys)} in {row.get('item_id')}")


def _stage_ms_from_tps(row: dict[str, Any], *, branch: str, stage: str) -> float:
    tokens_key = f"{branch}_{stage}_tokens"
    tps_key = f"{branch}_{stage}_tps"
    tokens = int(row.get(tokens_key, 0))
    if tokens == 0:
        return 0.0
    tps = float(row.get(tps_key, 0.0))
    if tps <= 0.0:
        raise ValueError(
            f"cannot derive {branch} {stage} time for {row.get('item_id')}: "
            f"{tokens_key}={tokens}, {tps_key}={tps}"
        )
    return float(tokens / tps * 1000.0)


def _prefill_ms(row: dict[str, Any], *, branch: str) -> float:
    timings = row.get(f"{branch}_timing_ms")
    if isinstance(timings, dict):
        direct = timings.get("multimodal_prefill_ms", timings.get("multimodal_prefill"))
        if direct is not None:
            return float(direct)
    return _stage_ms_from_tps(row, branch=branch, stage="prompt")


def _accuracy(rows: list[dict[str, Any]], key: str) -> float:
    return sum(bool(row.get(key, False)) for row in rows) / len(rows) if rows else 0.0


def _group_rows(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("group", "unknown"))].append(row)
    return dict(grouped)


def _quality_summary(
    rows: list[dict[str, Any]],
    *,
    quality_delta_floor: float,
    bucket_min_n: int,
) -> dict[str, Any]:
    dense_acc = _accuracy(rows, "dense_correct")
    pruned_acc = _accuracy(rows, "pruned_correct")
    aggregate_delta = pruned_acc - dense_acc
    by_bucket: dict[str, dict[str, Any]] = {}
    bucket_failures: list[str] = []
    for bucket, bucket_rows in sorted(_group_rows(rows).items()):
        dense_bucket = _accuracy(bucket_rows, "dense_correct")
        pruned_bucket = _accuracy(bucket_rows, "pruned_correct")
        delta = pruned_bucket - dense_bucket
        evaluated = len(bucket_rows) >= bucket_min_n
        passed = delta >= quality_delta_floor if evaluated else None
        if evaluated and not passed:
            bucket_failures.append(bucket)
        by_bucket[bucket] = {
            "n": len(bucket_rows),
            "dense_accuracy": dense_bucket,
            "pruned_accuracy": pruned_bucket,
            "accuracy_delta_pruned_minus_dense": delta,
            "quality_gate_evaluated": evaluated,
            "quality_gate_pass": passed,
        }
    return {
        "dense_accuracy": dense_acc,
        "pruned_accuracy": pruned_acc,
        "accuracy_delta_pruned_minus_dense": aggregate_delta,
        "aggregate_quality_gate_pass": aggregate_delta >= quality_delta_floor,
        "bucket_quality_gate_pass": not bucket_failures,
        "bucket_failures": bucket_failures,
        "buckets": by_bucket,
    }


def _bootstrap_ci(
    rows: list[dict[str, Any]],
    *,
    metric: Callable[[list[dict[str, Any]]], float],
    n_bootstrap: int,
    seed: int = 20260507,
) -> list[float] | None:
    if not rows or n_bootstrap <= 0:
        return None
    by_item: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_item[str(row["item_id"])].append(row)
    keys = sorted(by_item)
    rng = random.Random(seed)
    samples: list[float] = []
    for _ in range(n_bootstrap):
        sample_rows: list[dict[str, Any]] = []
        for key in rng.choices(keys, k=len(keys)):
            sample_rows.extend(by_item[key])
        samples.append(metric(sample_rows))
    samples.sort()
    return [
        float(samples[int(0.025 * (len(samples) - 1))]),
        float(samples[int(0.975 * (len(samples) - 1))]),
    ]


def _accuracy_delta_metric(rows: list[dict[str, Any]]) -> float:
    return _accuracy(rows, "pruned_correct") - _accuracy(rows, "dense_correct")


def _e2e_speedup_metric(rows: list[dict[str, Any]]) -> float:
    dense = sum(_timing(row, "dense", "end_to_end") for row in rows)
    pruned = sum(_timing(row, "pruned", "end_to_end") for row in rows)
    return dense / pruned if pruned > 0.0 else 0.0


def _overhead_budget_metric(rows: list[dict[str, Any]]) -> float:
    dense_prefill = sum(_prefill_ms(row, branch="dense") for row in rows)
    pruned_prefill = sum(_prefill_ms(row, branch="pruned") for row in rows)
    dense_vision = sum(_timing(row, "dense", "vision") for row in rows)
    pruned_vision = sum(_timing(row, "pruned", "vision") for row in rows)
    overhead = sum(
        _optional_timing(row, "pruned", "mask_compute", "mask")
        + _optional_timing(row, "pruned", "placeholder_prune", "prune")
        for row in rows
    )
    return (dense_prefill - pruned_prefill) + (dense_vision - pruned_vision) - overhead


def analyze(
    rows: list[dict[str, Any]],
    *,
    quality_delta_floor: float,
    bucket_min_n: int,
    require_overhead_gate: bool,
    timing_min_n: int,
    n_bootstrap: int,
) -> dict[str, Any]:
    quality = _quality_summary(
        rows,
        quality_delta_floor=quality_delta_floor,
        bucket_min_n=bucket_min_n,
    )
    choice_agreement = _mean(
        [1.0 if row.get("dense_choice") == row.get("pruned_choice") else 0.0 for row in rows]
    )
    dense_prefill_ms = [_prefill_ms(row, branch="dense") for row in rows]
    pruned_prefill_ms = [_prefill_ms(row, branch="pruned") for row in rows]
    overhead_ms = [
        _optional_timing(row, "pruned", "mask_compute", "mask")
        + _optional_timing(row, "pruned", "placeholder_prune", "prune")
        for row in rows
    ]
    dense_vision_ms = [_timing(row, "dense", "vision") for row in rows]
    pruned_vision_ms = [_timing(row, "pruned", "vision") for row in rows]
    dense_e2e = [_timing(row, "dense", "end_to_end") for row in rows]
    pruned_e2e = [_timing(row, "pruned", "end_to_end") for row in rows]
    prompt_reduction_ms = sum(dense_prefill_ms) - sum(pruned_prefill_ms)
    vision_reduction_ms = sum(dense_vision_ms) - sum(pruned_vision_ms)
    overhead_budget_ms = prompt_reduction_ms + vision_reduction_ms
    total_overhead_ms = sum(overhead_ms)
    overhead_gate_evaluated = require_overhead_gate and len(rows) >= timing_min_n
    overhead_gate_pass = (
        total_overhead_ms < max(0.0, overhead_budget_ms) if overhead_gate_evaluated else None
    )
    dense_e2e_total = sum(dense_e2e)
    pruned_e2e_total = sum(pruned_e2e)
    decisions: list[dict[str, Any]] = []
    skip_phases: list[str] = []
    if not quality["aggregate_quality_gate_pass"] or not quality["bucket_quality_gate_pass"]:
        decisions.append(
            {
                "decision": "stop",
                "reason": "gemma_admission_quality_gate_failed",
                "details": {
                    "accuracy_delta_pruned_minus_dense": quality[
                        "accuracy_delta_pruned_minus_dense"
                    ],
                    "bucket_failures": quality["bucket_failures"],
                    "gate": quality_delta_floor,
                },
            }
        )
        skip_phases.extend(["RLT-3G-A", "RLT-3G-B", "RLT-4Q", "RLT-5G", "RLT-5Q"])
    if overhead_gate_evaluated and overhead_gate_pass is False:
        decisions.append(
            {
                "decision": "contract",
                "reason": "gemma_admission_overhead_dominated",
                "details": {
                    "prompt_reduction_ms": prompt_reduction_ms,
                    "vision_reduction_ms": vision_reduction_ms,
                    "overhead_budget_ms": overhead_budget_ms,
                    "overhead_ms": total_overhead_ms,
                    "timing_min_n": timing_min_n,
                },
            }
        )
        skip_phases.extend(["RLT-3G-A", "RLT-3G-B"])
    if not decisions:
        decisions.append({"decision": "continue", "reason": "gemma_admission_gates_survived"})
    return {
        "n_items": len(rows),
        **quality,
        "choice_agreement": choice_agreement,
        "dense_parse_failures": sum(bool(row.get("dense_parse_failure", False)) for row in rows),
        "pruned_parse_failures": sum(bool(row.get("pruned_parse_failure", False)) for row in rows),
        "mean_dense_prefill_ms": _mean(dense_prefill_ms),
        "mean_pruned_prefill_ms": _mean(pruned_prefill_ms),
        "total_prefill_reduction_ms": prompt_reduction_ms,
        "mean_dense_vision_ms": _mean(dense_vision_ms),
        "mean_pruned_vision_ms": _mean(pruned_vision_ms),
        "total_vision_reduction_ms": vision_reduction_ms,
        "total_overhead_budget_ms": overhead_budget_ms,
        "mean_overhead_ms": _mean(overhead_ms),
        "total_overhead_ms": total_overhead_ms,
        "overhead_gate_evaluated": overhead_gate_evaluated,
        "overhead_gate_pass": overhead_gate_pass,
        "timing_min_n": timing_min_n,
        "dense_e2e_total_ms": dense_e2e_total,
        "pruned_e2e_total_ms": pruned_e2e_total,
        "e2e_speedup_dense_over_pruned": (
            dense_e2e_total / pruned_e2e_total if pruned_e2e_total > 0.0 else None
        ),
        "bootstrap": {
            "n_bootstrap": n_bootstrap,
            "accuracy_delta_pruned_minus_dense_ci95": _bootstrap_ci(
                rows,
                metric=_accuracy_delta_metric,
                n_bootstrap=n_bootstrap,
            ),
            "e2e_speedup_dense_over_pruned_ci95": _bootstrap_ci(
                rows,
                metric=_e2e_speedup_metric,
                n_bootstrap=n_bootstrap,
            ),
            "overhead_budget_minus_overhead_ms_ci95": _bootstrap_ci(
                rows,
                metric=_overhead_budget_metric,
                n_bootstrap=n_bootstrap,
            ),
        },
        "decisions": decisions,
        "skip_phases": sorted(set(skip_phases)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jsonl", type=Path, required=True)
    parser.add_argument("--summary-json", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--quality-delta-floor", type=float, default=-0.05)
    parser.add_argument("--bucket-min-n", type=int, default=20)
    parser.add_argument("--timing-min-n", type=int, default=20)
    parser.add_argument("--n-bootstrap", type=int, default=2000)
    parser.add_argument("--no-overhead-gate", action="store_true")
    args = parser.parse_args()
    if args.timing_min_n < 1:
        raise SystemExit("--timing-min-n must be at least 1")
    if args.n_bootstrap < 0:
        raise SystemExit("--n-bootstrap must be nonnegative")

    schema, rows = _load_jsonl(args.jsonl)
    runner_summary = json.loads(args.summary_json.read_text(encoding="utf-8"))
    analysis = analyze(
        rows,
        quality_delta_floor=args.quality_delta_floor,
        bucket_min_n=args.bucket_min_n,
        require_overhead_gate=not args.no_overhead_gate,
        timing_min_n=args.timing_min_n,
        n_bootstrap=args.n_bootstrap,
    )
    payload = {
        "schema_version": SCHEMA_VERSION,
        "jsonl": str(args.jsonl),
        "summary_json": str(args.summary_json),
        "runner_schema": schema,
        "runner_summary_schema_version": runner_summary.get("schema_version"),
        "gates": {
            "quality_delta_floor": args.quality_delta_floor,
            "bucket_min_n": args.bucket_min_n,
            "timing_min_n": args.timing_min_n,
            "n_bootstrap": args.n_bootstrap,
            "overhead_gate_required": not args.no_overhead_gate,
        },
        **analysis,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "decisions": payload["decisions"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
