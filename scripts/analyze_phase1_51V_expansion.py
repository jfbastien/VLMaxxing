#!/usr/bin/env python3
"""Analyze the Phase 1.51V expansion queue results.

Reads paired (unpatched, patched) summary JSONs and emits thermal-normalized
V-reduction, E2E speedup, and decode_ms drift for each pair. Also flags
thermal-pairing validity per-pair (decode delta < 2%).

Usage:
  .venv/bin/python scripts/analyze_phase1_51V_expansion.py
  .venv/bin/python scripts/analyze_phase1_51V_expansion.py --artifacts PATH
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

# (label, unpatched_name, patched_name)
PAIRS = [
    ("VideoMME 8f kr=0.50", "exp01_videomme_8f_unpatched", "exp02_videomme_8f_L2_kr050"),
    ("VideoMME 8f kr=0.25", "exp01_videomme_8f_unpatched", "exp03_videomme_8f_L2_kr025"),
    ("VideoMME 8f kr=0.75", "exp01_videomme_8f_unpatched", "exp04_videomme_8f_L2_kr075"),
    ("MVBench 8f kr=0.50", "exp05_mvbench_8f_unpatched", "exp06_mvbench_8f_L2_kr050"),
    ("TOMATO 8f kr=0.50", "exp07_tomato_8f_unpatched", "exp08_tomato_8f_L2_kr050"),
    (
        "VideoMME 8f L=2 kr_V=0.50 × novelty kr=0.5 structural",
        "exp01_videomme_8f_unpatched",
        "exp09_videomme_8f_L2_kr050_novelty050_structural",
    ),
    (
        "VideoMME 8f L=2 kr_V=0.50 × novelty kr=0.3 none",
        "exp01_videomme_8f_unpatched",
        "exp10_videomme_8f_L2_kr050_novelty030_none",
    ),
    ("VideoMME 16f kr=0.50", "exp11_videomme_16f_unpatched", "exp12_videomme_16f_L2_kr050"),
]


def load_summary(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text())


def fmt_pct(x: float) -> str:
    return f"{x * 100:+.1f}%"


def analyze(artifacts: Path) -> int:
    print(f"{'Pair':<58s} {'V_red':>8s} {'E2E×':>6s} {'Dec Δ':>7s} {'Acc Δ':>7s} {'thermal':>9s}")
    print("-" * 105)

    v_share_rows = []

    for label, u_name, p_name in PAIRS:
        u = load_summary(artifacts / f"{u_name}_summary.json")
        p = load_summary(artifacts / f"{p_name}_summary.json")
        if not u or not p:
            status = ("-" if not u else "u") + ("-" if not p else "p")
            print(f"{label:<58s} {'pending':>8s} {'':>6s} {'':>7s} {'':>7s} {status:>9s}")
            continue

        u_v = u["mean_dense_vision_ms"]
        p_v = p["mean_dense_vision_ms"]
        u_decode = u["mean_decode_ms"]
        p_decode = p["mean_decode_ms"]
        u_e2e = u["mean_dense_end_to_end_ms"]
        p_e2e = p["mean_dense_end_to_end_ms"]
        u_acc = u["dense_accuracy"]
        p_acc = p["dense_accuracy"]

        v_red = 1.0 - (p_v / u_v)
        e2e_speedup = u_e2e / p_e2e
        decode_drift = (p_decode - u_decode) / u_decode
        acc_delta = p_acc - u_acc
        thermal_ok = "clean" if abs(decode_drift) < 0.02 else "DRIFT"

        print(
            f"{label:<58s} "
            f"{fmt_pct(v_red):>8s} "
            f"{e2e_speedup:>5.2f}× "
            f"{fmt_pct(decode_drift):>7s} "
            f"{acc_delta:+6.3f} "
            f"{thermal_ok:>9s}"
        )

        v_share_rows.append(
            {
                "label": label,
                "u_v_share": u_v / u_e2e,
                "p_v_share": p_v / p_e2e,
                "v_red": v_red,
                "e2e_speedup": e2e_speedup,
                "e2e_ceiling_at_100pct": 1.0 / (1.0 - (u_v / u_e2e)),
            }
        )

    if v_share_rows:
        print()
        print("V_share context (what fraction of E2E is vision tower):")
        print(f"{'Pair':<58s} {'V_share_u':>10s} {'V_share_p':>10s} {'ceil@100%':>10s}")
        print("-" * 90)
        for r in v_share_rows:
            print(
                f"{r['label']:<58s} "
                f"{fmt_pct(r['u_v_share']):>10s} "
                f"{fmt_pct(r['p_v_share']):>10s} "
                f"{r['e2e_ceiling_at_100pct']:>9.2f}×"
            )

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifacts",
        type=Path,
        default=Path("research/experiments/2026/artifacts/phase1_51V_expansion"),
    )
    args = parser.parse_args()
    return analyze(args.artifacts)


if __name__ == "__main__":
    raise SystemExit(main())
