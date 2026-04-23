#!/usr/bin/env python3
"""Build a Q0-only VideoMME manifest from a Phase 1.30 results jsonl.

Used to feed the same Q0 items to scripts/run_phase1_51V.py so we can compare
1.51V's first-query pruning path against 1.30's cold_pruned first-query path
(the parity check from Codex round-28).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase130_jsonl", type=Path)
    parser.add_argument("out_toml", type=Path)
    args = parser.parse_args()

    item_ids: list[str] = []
    with args.phase130_jsonl.open() as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if int(row["q_index"]) == 0:
                item_ids.append(str(row["item_id"]))
    item_ids = sorted(set(item_ids))
    if not item_ids:
        raise SystemExit("no q_index=0 rows in source jsonl")

    lines = [
        'benchmark = "videomme"',
        'description = "phase1_30 Q0 manifest for 1.51V parity check"',
        "item_ids = [",
    ]
    lines.extend(f'    "{iid}",' for iid in item_ids)
    lines.append("]")
    args.out_toml.write_text("\n".join(lines) + "\n")
    print(args.out_toml)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
