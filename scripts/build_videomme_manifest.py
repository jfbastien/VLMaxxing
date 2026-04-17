#!/usr/bin/env python3
"""Generate duration-stratified VideoMME dev/holdout manifests.

VideoMME's 2700-question test split spans three durations (short/
medium/long, 900 each) and ten task types. For our N=30 lane we pick
10 items per duration, balanced by task type within a duration. The
dev and holdout splits are disjoint and sampled with a fixed seed so
the manifests are reproducible.

Outputs two TOML files compatible with scripts/run_benchmark_track_a.py.
"""

from __future__ import annotations

import argparse
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

DEFAULT_PARQUET_DIR = Path("data/benchmarks/videomme/hf")


def _collect_rows(parquet_dir: Path) -> list[dict[str, Any]]:
    files = list(parquet_dir.rglob("*.parquet"))
    if not files:
        raise SystemExit(f"no parquet found under {parquet_dir}; run fetch first")
    out: list[dict[str, Any]] = []
    for path in files:
        table = pq.read_table(path)
        out.extend(table.to_pylist())
    return out


def _item_id(row: dict[str, Any]) -> str:
    return f"videomme:{row['duration']}:{row['question_id']}"


def _sample_balanced(
    rows: list[dict[str, Any]],
    *,
    per_duration: int,
    seed: int,
) -> tuple[list[str], list[str]]:
    rng = random.Random(seed)

    by_duration_task: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_duration_task[(row["duration"], row["task_type"])].append(row)
    for group in by_duration_task.values():
        rng.shuffle(group)

    durations = ["short", "medium", "long"]
    dev_rows: list[dict[str, Any]] = []
    holdout_rows: list[dict[str, Any]] = []

    for duration in durations:
        task_types_for_duration = sorted(
            {key[1] for key in by_duration_task if key[0] == duration}
        )
        dev_pool: list[dict[str, Any]] = []
        holdout_pool: list[dict[str, Any]] = []
        # One dev + one holdout from each task type until we hit
        # per_duration. When a task type runs dry we round-robin
        # through the remaining types.
        type_queues: dict[str, list[dict[str, Any]]] = {
            task_type: list(by_duration_task[(duration, task_type)])
            for task_type in task_types_for_duration
        }
        # Round-robin fill
        while len(dev_pool) < per_duration or len(holdout_pool) < per_duration:
            progressed = False
            for task_type in task_types_for_duration:
                queue = type_queues[task_type]
                if not queue:
                    continue
                if len(dev_pool) < per_duration:
                    dev_pool.append(queue.pop())
                    progressed = True
                if not queue:
                    continue
                if len(holdout_pool) < per_duration:
                    holdout_pool.append(queue.pop())
                    progressed = True
            if not progressed:
                break
        if len(dev_pool) < per_duration or len(holdout_pool) < per_duration:
            raise SystemExit(
                f"could not fill {per_duration} items per split for duration={duration}"
            )
        dev_rows.extend(dev_pool)
        holdout_rows.extend(holdout_pool)

    dev_ids = sorted(_item_id(r) for r in dev_rows)
    holdout_ids = sorted(_item_id(r) for r in holdout_rows)
    # Sanity: disjoint
    overlap = set(dev_ids) & set(holdout_ids)
    if overlap:
        raise SystemExit(f"dev/holdout overlap: {overlap}")
    return dev_ids, holdout_ids


def _write_manifest(path: Path, *, item_ids: list[str], description: str) -> None:
    lines = ['benchmark = "videomme"', f'description = "{description}"']
    lines.append("item_ids = [")
    for item_id in item_ids:
        lines.append(f'    "{item_id}",')
    lines.append("]")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parquet-dir", type=Path, default=DEFAULT_PARQUET_DIR)
    parser.add_argument("--per-duration", type=int, default=10)
    parser.add_argument("--seed", type=int, default=20260417)
    parser.add_argument(
        "--dev-output",
        type=Path,
        default=Path("research/benchmark_manifests/videomme_dev_v1.toml"),
    )
    parser.add_argument(
        "--holdout-output",
        type=Path,
        default=Path("research/benchmark_manifests/videomme_holdout_v1.toml"),
    )
    args = parser.parse_args()

    rows = _collect_rows(args.parquet_dir)
    dev_ids, holdout_ids = _sample_balanced(
        rows, per_duration=args.per_duration, seed=args.seed
    )
    _write_manifest(
        args.dev_output,
        item_ids=dev_ids,
        description=(
            f"videomme dev v1 ({args.per_duration} items per duration, "
            f"task-type balanced, seed={args.seed})"
        ),
    )
    _write_manifest(
        args.holdout_output,
        item_ids=holdout_ids,
        description=(
            f"videomme holdout v1 ({args.per_duration} items per duration, "
            f"disjoint from dev, seed={args.seed})"
        ),
    )

    print(f"wrote dev manifest: {args.dev_output} ({len(dev_ids)} items)")
    print(f"wrote holdout manifest: {args.holdout_output} ({len(holdout_ids)} items)")
    print(f"total items needing videos: {len(set(dev_ids) | set(holdout_ids))}")

    # Emit the list of unique videoIDs so the user can fetch them manually.
    seen_video_ids: set[str] = set()
    videomme_rows = {_item_id(r): r for r in rows}
    for item_id in dev_ids + holdout_ids:
        seen_video_ids.add(videomme_rows[item_id]["videoID"])
    print(f"unique videoIDs needed: {len(seen_video_ids)}")
    print("  (first 10):", sorted(seen_video_ids)[:10])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
