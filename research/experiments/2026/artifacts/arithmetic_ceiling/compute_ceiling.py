"""Empirical arithmetic-ceiling analysis for 1.51R — Task #88.

Uses Stage 2b n=30 JSONL (kr=0.10 anchor=none, Gemma 4-E4B-4bit, VideoMME).

Decomposition per item: end_to_end = decode + processor + vision + generate
Only `generate` is touched by 1.51R's prefill-shortening. The ceiling:

    e2e_speedup ≤ (D + P + V + G) / (D + P + V + G/s)

where s is the per-phase speedup on generate. As s → ∞, the ceiling
collapses to (D + P + V + G) / (D + P + V).

Outputs:
- ceiling_summary.json: per-bucket ceiling statistics
- ceiling_data.csv: per-item decomposition for inspection / plotting
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

ARTIFACT = Path(__file__).resolve().parent
SRC = ARTIFACT.parent / "phase1_51R_dev" / "stage2b_none_kr010_n30.jsonl"
assert SRC.exists(), f"missing source: {SRC}"


def main() -> None:
    items = [json.loads(line) for line in SRC.read_text().splitlines() if line.strip()]
    assert len(items) == 30, f"expected 30 items, got {len(items)}"

    rows = []
    for it in items:
        d = it["dense_timing_ms"]
        p = it["pruned_timing_ms"]
        D = d["decode"]
        P = d["processor"]
        V = d["vision"]
        G_dense = d["generate"]
        G_pruned = p["generate"]
        e2e_dense = d["end_to_end"]
        e2e_pruned = p["end_to_end"]
        fixed = D + P + V  # cost invariant under 1.51R
        # Observed per-phase speedup on generate
        s_obs = G_dense / G_pruned if G_pruned > 0 else float("nan")
        # Observed e2e speedup
        e2e_speedup_obs = e2e_dense / e2e_pruned if e2e_pruned > 0 else float("nan")
        # Per-token normalized speedup (our headline Stage 2b number)
        dense_toks = it["dense_generation_tokens"] or 1
        pruned_toks = it["pruned_generation_tokens"] or 1
        per_tok_dense_ms = G_dense / dense_toks
        per_tok_pruned_ms = G_pruned / pruned_toks
        per_tok_speedup = (
            per_tok_dense_ms / per_tok_pruned_ms if per_tok_pruned_ms > 0 else float("nan")
        )
        # Arithmetic ceiling for this item, at s = per_tok_speedup (the
        # "true" per-phase G speedup after controlling for token-count drift):
        ceiling = (
            (fixed + G_dense) / (fixed + G_dense / per_tok_speedup)
            if per_tok_speedup > 0
            else float("nan")
        )
        # Infinite-s ceiling: what if we pruned G to zero?
        ceiling_inf = (fixed + G_dense) / fixed if fixed > 0 else float("nan")
        rows.append(
            {
                "item_id": it["item_id"],
                "group": it["group"],
                "D_ms": round(D, 1),
                "P_ms": round(P, 1),
                "V_ms": round(V, 1),
                "G_dense_ms": round(G_dense, 1),
                "G_pruned_ms": round(G_pruned, 1),
                "fixed_frac": round(fixed / (fixed + G_dense), 3),
                "s_obs": round(s_obs, 3),
                "per_tok_speedup": round(per_tok_speedup, 3),
                "e2e_speedup_obs": round(e2e_speedup_obs, 3),
                "ceiling_per_tok_s": round(ceiling, 3),
                "ceiling_inf_s": round(ceiling_inf, 3),
            }
        )

    # CSV
    csv_path = ARTIFACT / "ceiling_data.csv"
    header = list(rows[0].keys())
    lines = [",".join(header)]
    for r in rows:
        lines.append(",".join(str(r[k]) for k in header))
    csv_path.write_text("\n".join(lines) + "\n")

    # Summary per group + aggregate
    groups: dict[str, list[dict]] = {"short": [], "medium": [], "long": [], "all": []}
    for r in rows:
        groups[r["group"]].append(r)
        groups["all"].append(r)

    summary: dict[str, dict] = {}
    for g, rs in groups.items():
        if not rs:
            continue
        fixed_fracs = [r["fixed_frac"] for r in rs]
        per_tok = [r["per_tok_speedup"] for r in rs if r["per_tok_speedup"] > 0]
        e2e_obs = [r["e2e_speedup_obs"] for r in rs if r["e2e_speedup_obs"] > 0]
        ceilings = [r["ceiling_per_tok_s"] for r in rs if r["ceiling_per_tok_s"] > 0]
        ceilings_inf = [r["ceiling_inf_s"] for r in rs if r["ceiling_inf_s"] > 0]
        summary[g] = {
            "n": len(rs),
            "fixed_frac_mean": round(statistics.mean(fixed_fracs), 3),
            "per_tok_speedup_mean": round(statistics.mean(per_tok), 3),
            "e2e_speedup_obs_mean": round(statistics.mean(e2e_obs), 3),
            "ceiling_at_observed_s_mean": round(statistics.mean(ceilings), 3),
            "ceiling_at_infinite_s_mean": round(statistics.mean(ceilings_inf), 3),
            "headroom_remaining": round(
                statistics.mean(ceilings_inf) - statistics.mean(e2e_obs), 3
            ),
        }

    summary_path = ARTIFACT / "ceiling_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")

    print("=== arithmetic-ceiling summary (Stage 2b kr=0.10 n=30) ===")
    for g in ("short", "medium", "long", "all"):
        if g in summary:
            s = summary[g]
            print(
                f"{g:>7}: n={s['n']:>2}  "
                f"fixed_frac={s['fixed_frac_mean']:.3f}  "
                f"s_per_tok={s['per_tok_speedup_mean']:.3f}×  "
                f"e2e_obs={s['e2e_speedup_obs_mean']:.3f}×  "
                f"ceiling@s={s['ceiling_at_observed_s_mean']:.3f}×  "
                f"ceiling@∞={s['ceiling_at_infinite_s_mean']:.3f}×  "
                f"headroom={s['headroom_remaining']:.3f}"
            )
    print(f"\nwrote: {csv_path}")
    print(f"wrote: {summary_path}")


if __name__ == "__main__":
    main()
