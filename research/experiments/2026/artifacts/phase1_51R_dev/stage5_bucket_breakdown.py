"""Per-bucket accuracy + speed breakdown for Stage 5 anchor arms."""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

DEV = Path(__file__).resolve().parent


def breakdown(path: Path) -> None:
    items = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    print(f"\n=== {path.name} (n={len(items)}) ===")
    buckets: dict[str, list[dict]] = {"short": [], "medium": [], "long": [], "all": []}
    for it in items:
        buckets[it["group"]].append(it)
        buckets["all"].append(it)
    print(f"{'bucket':>7}  n   dense_acc  pruned_acc   Δacc  agree  e2e    gen    per_tok")
    for g, rs in buckets.items():
        if not rs:
            continue
        da = statistics.mean(int(r["dense_correct"]) for r in rs)
        pa = statistics.mean(int(r["pruned_correct"]) for r in rs)
        ag = statistics.mean(int(r["agreement"]) for r in rs)
        e2e = statistics.mean(
            r["dense_timing_ms"]["end_to_end"] / r["pruned_timing_ms"]["end_to_end"]
            for r in rs if r["pruned_timing_ms"]["end_to_end"] > 0
        )
        gen = statistics.mean(
            r["dense_timing_ms"]["generate"] / r["pruned_timing_ms"]["generate"]
            for r in rs if r["pruned_timing_ms"]["generate"] > 0
        )
        per_tok = statistics.mean(
            (r["dense_timing_ms"]["generate"] / max(1, r["dense_generation_tokens"])) /
            (r["pruned_timing_ms"]["generate"] / max(1, r["pruned_generation_tokens"]))
            for r in rs if r["pruned_timing_ms"]["generate"] > 0
        )
        print(f"{g:>7}  {len(rs):>2}   {da:>6.3f}    {pa:>6.3f}    {pa-da:+.3f}  {ag:>.2f}   {e2e:>4.3f}  {gen:>4.3f}  {per_tok:>4.3f}")


def main() -> None:
    for arg in sys.argv[1:]:
        breakdown(DEV / arg)


if __name__ == "__main__":
    main()
