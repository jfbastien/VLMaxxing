#!/usr/bin/env python3
"""Validate that the 1.30AC smoke run really activates follow-up pruning."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open() as handle:
        for line_number, line in enumerate(handle, start=1):
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise SystemExit(f"{path}:{line_number}: invalid JSONL row: {exc}") from exc
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jsonl", type=Path, required=True)
    parser.add_argument(
        "--expected-follow-ups",
        type=int,
        default=2,
        help="Expected number of follow-up rows in the smoke session.",
    )
    args = parser.parse_args()

    rows = _load_jsonl(args.jsonl)
    if not rows:
        raise SystemExit(f"{args.jsonl}: no rows")

    follow_ups = [row for row in rows if int(row.get("q_index", -1)) > 0]
    if len(follow_ups) != args.expected_follow_ups:
        raise SystemExit(
            f"{args.jsonl}: expected {args.expected_follow_ups} follow-up rows, "
            f"got {len(follow_ups)}"
        )

    failures: list[str] = []
    for row in follow_ups:
        item_id = str(row.get("item_id", "<unknown>"))
        image_token_count = int(row.get("image_token_count") or 0)
        image_tokens_recomputed = int(row.get("image_tokens_recomputed") or 0)
        prefix_hit = int(row.get("prefix_hit") or 0)
        keep_rate = float(row.get("vision_tower_keep_rate") or 1.0)
        if row.get("reset_cache_between_queries") is not True:
            failures.append(f"{item_id}: reset_cache_between_queries is not true")
        if row.get("refresh_reason") != "per_query_reset":
            failures.append(f"{item_id}: refresh_reason={row.get('refresh_reason')!r}")
        if prefix_hit != 0:
            failures.append(f"{item_id}: prefix_hit={prefix_hit}, expected 0")
        if image_token_count <= 0:
            failures.append(f"{item_id}: image_token_count={image_token_count}, expected >0")
        if image_tokens_recomputed != image_token_count:
            failures.append(
                f"{item_id}: recomputed {image_tokens_recomputed}/{image_token_count} image tokens"
            )
        if keep_rate >= 1.0:
            failures.append(f"{item_id}: follow-up keep_rate={keep_rate}, expected <1.0")
        if row.get("vision_pruning_active") is not True:
            failures.append(f"{item_id}: vision_pruning_active is not true")

    if failures:
        raise SystemExit("\n".join(failures))

    print(
        f"[1.30AC smoke] validated {len(follow_ups)} follow-up rows with "
        "prefix_hit=0 and active vision pruning"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
