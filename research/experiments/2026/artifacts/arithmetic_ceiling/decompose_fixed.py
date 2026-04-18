"""Per-phase breakdown of the fixed cost (D+P+V) on Stage 2b n=30."""
from __future__ import annotations

import json
import statistics
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "phase1_51R_dev" / "stage2b_none_kr010_n30.jsonl"


def main() -> None:
    items = [json.loads(line) for line in SRC.read_text().splitlines() if line.strip()]

    groups: dict[str, list[dict]] = {"short": [], "medium": [], "long": [], "all": []}
    for it in items:
        d = it["dense_timing_ms"]
        row = {
            "D": d["decode"],
            "P": d["processor"],
            "V": d["vision"],
            "G": d["generate"],
            "e2e": d["end_to_end"],
        }
        row["fixed"] = row["D"] + row["P"] + row["V"]
        groups[it["group"]].append(row)
        groups["all"].append(row)

    print(f"{'bucket':>7}  {'n':>2}  {'D':>7}  {'P':>6}  {'V':>6}  {'G':>6}  {'e2e':>7}  |  {'D/e2e':>6}  {'V/e2e':>6}  {'V/fixed':>7}  {'G/e2e':>6}")
    for g, rs in groups.items():
        if not rs:
            continue
        n = len(rs)
        D = statistics.mean(r["D"] for r in rs)
        P = statistics.mean(r["P"] for r in rs)
        V = statistics.mean(r["V"] for r in rs)
        G = statistics.mean(r["G"] for r in rs)
        e2e = statistics.mean(r["e2e"] for r in rs)
        fixed = statistics.mean(r["fixed"] for r in rs)
        print(
            f"{g:>7}  {n:>2}  "
            f"{D/1000:>6.2f}s  {P/1000:>5.2f}s  {V/1000:>5.2f}s  {G/1000:>5.2f}s  {e2e/1000:>6.2f}s  |  "
            f"{D/e2e:>6.1%}  {V/e2e:>6.1%}  {V/fixed:>7.1%}  {G/e2e:>6.1%}"
        )


if __name__ == "__main__":
    main()
