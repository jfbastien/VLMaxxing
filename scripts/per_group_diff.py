#!/usr/bin/env python3
"""Compare two benchmark jsonl outputs per-group to surface which items each
path got right/wrong. Useful for understanding whether a "Pareto-matching"
cached policy is genuinely doing better on specific tasks or merely
reproducing the dense baseline's per-group hit/miss pattern.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open() as fh:
        for line in fh:
            s = line.strip()
            if s:
                rows.append(json.loads(s))
    return rows


def _extract_item_result(item: dict[str, Any], which: str) -> tuple[str | None, bool]:
    block = item.get(which, {})
    return (block.get("text"), bool(block.get("correct", False)))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cached", type=Path, required=True)
    parser.add_argument(
        "--dense", type=Path, required=True,
        help="Dense frame-budget jsonl (e.g. frame_4.jsonl from phase 1.9)",
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    cached_rows = _load_jsonl(args.cached)
    dense_rows = _load_jsonl(args.dense)

    by_id: dict[str, dict[str, Any]] = {}
    for row in dense_rows:
        item_id = row["item_id"]
        by_id[item_id] = {"group": row.get("group"), "dense": row.get("dense")}
    for row in cached_rows:
        item_id = row["item_id"]
        if item_id not in by_id:
            by_id[item_id] = {"group": row.get("group")}
        by_id[item_id]["cached"] = row.get("cached")
        by_id[item_id]["dense_this_run"] = row.get("dense")

    group_stats: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "n": 0,
            "both_right": 0,
            "both_wrong": 0,
            "cached_only_right": 0,
            "dense_only_right": 0,
        }
    )
    disagreements = []
    for item_id, payload in by_id.items():
        group = payload.get("group") or "unknown"
        dense = payload.get("dense") or payload.get("dense_this_run") or {}
        cached = payload.get("cached") or {}
        if not dense or not cached:
            continue
        dense_ok = bool(dense.get("correct", False))
        cached_ok = bool(cached.get("correct", False))
        stats = group_stats[group]
        stats["n"] += 1
        if dense_ok and cached_ok:
            stats["both_right"] += 1
        elif not dense_ok and not cached_ok:
            stats["both_wrong"] += 1
        elif cached_ok and not dense_ok:
            stats["cached_only_right"] += 1
        elif dense_ok and not cached_ok:
            stats["dense_only_right"] += 1
        if dense.get("text") != cached.get("text"):
            disagreements.append(
                {
                    "item_id": item_id,
                    "group": group,
                    "dense_text": dense.get("text"),
                    "dense_correct": dense_ok,
                    "cached_text": cached.get("text"),
                    "cached_correct": cached_ok,
                }
            )

    payload = {
        "cached_source": str(args.cached),
        "dense_source": str(args.dense),
        "per_group": dict(group_stats),
        "disagreements": disagreements,
        "n_disagreements": len(disagreements),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    print(f"Wrote {args.out}")
    print("Per-group stats:")
    for group in sorted(group_stats):
        s = group_stats[group]
        print(
            f"  {group:<24} n={s['n']:>2} both_right={s['both_right']} "
            f"both_wrong={s['both_wrong']} "
            f"cached_only={s['cached_only_right']} dense_only={s['dense_only_right']}"
        )
    print(f"\nTotal disagreements: {len(disagreements)}")


if __name__ == "__main__":
    main()
