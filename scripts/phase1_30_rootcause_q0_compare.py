#!/usr/bin/env python3
"""Compare 1.30 cold_pruned Q0 rows against 1.51V pruned rows on the same items.

Purpose: if 1.51V (which is mechanism-grade at kr_V=0.50) and 1.30's cold_pruned
arm land on the same choice/correctness per item, the Q0 degradation is real
for that regime; if they diverge materially, 1.30 has a first-query code-path
bug independent of the mechanism.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

CHOICE_LETTERS = ("A", "B", "C", "D")


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open() as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _phase130_choice(row: dict[str, Any]) -> Any:
    # 1.30 driver writes `choice` for the chosen index.
    return row.get("choice")


def _phase151V_choice(row: dict[str, Any]) -> Any:
    # 1.51V writes `choice_index` in its per-item jsonl.
    return row.get("choice_index", row.get("choice"))


def _normalize_choice(choice: Any) -> str | None:
    if choice is None:
        return None
    if isinstance(choice, bool):
        return None
    if isinstance(choice, int):
        if 0 <= choice < len(CHOICE_LETTERS):
            return CHOICE_LETTERS[choice]
        return None
    text = str(choice).strip().upper()
    if text in CHOICE_LETTERS:
        return text
    try:
        index = int(text)
    except ValueError:
        return None
    if 0 <= index < len(CHOICE_LETTERS):
        return CHOICE_LETTERS[index]
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase130_jsonl", type=Path)
    parser.add_argument("phase151v_jsonl", type=Path)
    args = parser.parse_args()

    phase130 = {
        row["item_id"]: row for row in _load_jsonl(args.phase130_jsonl) if int(row["q_index"]) == 0
    }
    phase151v = {row["item_id"]: row for row in _load_jsonl(args.phase151v_jsonl)}

    keys = sorted(set(phase130) & set(phase151v))
    if not keys:
        raise SystemExit("no overlapping item_ids between the two jsonls")

    agree_choice = 0
    agree_correct = 0
    for key in keys:
        a = phase130[key]
        b = phase151v[key]
        c130 = _phase130_choice(a)
        c51v = _phase151V_choice(b)
        norm130 = _normalize_choice(c130)
        norm51v = _normalize_choice(c51v)
        same_choice = norm130 == norm51v
        same_correct = bool(a["correct"]) == bool(b["correct"])
        agree_choice += int(same_choice)
        agree_correct += int(same_correct)
        print(
            f"{key}  "
            f"phase130 choice={c130}({norm130}) correct={a['correct']}  "
            f"phase151v choice_index={c51v}({norm51v}) correct={b['correct']}  "
            f"{'AGREE' if same_choice else 'DIFFER'}"
        )

    print()
    print(f"n={len(keys)}")
    print(f"choice agreement:  {agree_choice}/{len(keys)} = {agree_choice / len(keys):.3f}")
    print(f"correct agreement: {agree_correct}/{len(keys)} = {agree_correct / len(keys):.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
