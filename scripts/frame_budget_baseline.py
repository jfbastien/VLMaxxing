#!/usr/bin/env python3
"""Run dense frame-budget baselines on a frozen benchmark manifest."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import tomllib
from collections import defaultdict
from pathlib import Path
from typing import Any


def _manifest_benchmark(path: Path) -> str:
    payload = tomllib.loads(path.read_text())
    benchmark = payload.get("benchmark")
    if benchmark not in {"tomato", "mvbench", "videomme"}:
        raise ValueError(f"invalid benchmark in manifest {path}: {benchmark!r}")
    return str(benchmark)


def _run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def _wilson_interval(
    successes: int, total: int, *, z: float = 1.959963984540054
) -> tuple[float, float]:
    if total <= 0:
        raise ValueError("total must be positive")
    p_hat = successes / total
    denominator = 1.0 + (z**2) / total
    center = (p_hat + (z**2) / (2.0 * total)) / denominator
    margin = (
        z
        * math.sqrt((p_hat * (1.0 - p_hat) / total) + ((z**2) / (4.0 * total * total)))
        / denominator
    )
    return max(0.0, center - margin), min(1.0, center + margin)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open() as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def _per_group_dense_accuracy(rows: list[dict[str, Any]]) -> dict[str, dict[str, float | int]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["group"])].append(row)

    result: dict[str, dict[str, float | int]] = {}
    for group, group_rows in sorted(grouped.items()):
        dense_correct = sum(bool(row["dense"]["correct"]) for row in group_rows)
        result[group] = {
            "count": len(group_rows),
            "dense_accuracy": dense_correct / len(group_rows),
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--frame-counts", type=int, nargs="+", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--summary-path", type=Path, required=True)
    parser.add_argument(
        "--model-path", type=Path, default=Path.home() / "models" / "Qwen2.5-VL-7B-Instruct-4bit"
    )
    parser.add_argument("--max-tokens", type=int, default=32)
    parser.add_argument("--chunk-size", type=int, default=1)
    parser.add_argument(
        "--feature-cache-dir", type=Path, default=Path("research/cache/dense_features")
    )
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()

    benchmark = _manifest_benchmark(args.manifest)
    if args.summary_path.exists():
        raise FileExistsError(f"summary path already exists: {args.summary_path}")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    runs: list[dict[str, Any]] = []
    for frame_count in args.frame_counts:
        jsonl_path = args.output_dir / f"frame_{frame_count}.jsonl"
        run_summary_path = args.output_dir / f"frame_{frame_count}_summary.json"
        if jsonl_path.exists():
            raise FileExistsError(f"output path already exists: {jsonl_path}")
        if run_summary_path.exists():
            raise FileExistsError(f"summary path already exists: {run_summary_path}")

        command = [
            sys.executable,
            str(Path("scripts/run_benchmark_track_a.py")),
            "run",
            "--benchmark",
            benchmark,
            "--manifest",
            str(args.manifest),
            "--chunk-size",
            str(args.chunk_size),
            "--frame-count",
            str(frame_count),
            "--max-tokens",
            str(args.max_tokens),
            "--cache-mode",
            "identity",
            "--model-path",
            str(args.model_path),
            "--output-path",
            str(jsonl_path),
            "--summary-path",
            str(run_summary_path),
            "--feature-cache-dir",
            str(args.feature_cache_dir),
        ]
        if args.allow_dirty:
            command.append("--allow-dirty")
        _run(command)

        run_summary = json.loads(run_summary_path.read_text())
        rows = _load_jsonl(jsonl_path)
        dense_correct = sum(bool(row["dense"]["correct"]) for row in rows)
        ci_low, ci_high = _wilson_interval(dense_correct, len(rows))
        runs.append(
            {
                "frame_count": frame_count,
                "count": len(rows),
                "dense_accuracy": run_summary["dense_accuracy"],
                "dense_accuracy_ci95": [ci_low, ci_high],
                "agreement": run_summary["agreement"],
                "per_group_dense_accuracy": _per_group_dense_accuracy(rows),
                "output_path": str(jsonl_path),
                "summary_path": str(run_summary_path),
            }
        )

    payload = {
        "benchmark": benchmark,
        "manifest_path": str(args.manifest),
        "model_path": str(args.model_path),
        "max_tokens": args.max_tokens,
        "chunk_size": args.chunk_size,
        "frame_counts": args.frame_counts,
        "runs": runs,
    }
    args.summary_path.parent.mkdir(parents=True, exist_ok=True)
    args.summary_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
