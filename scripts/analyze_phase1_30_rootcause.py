#!/usr/bin/env python3
"""Phase 1.30 root-cause 6-arm decomposition analyzer.

Reads the six <arm>_summary.json files produced by
scripts/run_phase1_30_rootcause_decompose.sh and prints:

 1. Raw per-arm accuracy (all_queries, first_queries, follow_ups), wall time,
    parse failures, degenerate count.
 2. Accuracy deltas vs cold_dense.
 3. V-only / K-only / combined decomposition and the interaction term.
 4. Hard-reset recovery for the dense and pruned streaming arms.

No pandas; pure stdlib so it runs in any venv.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ARMS = [
    "cold_dense",
    "cold_pruned",
    "streaming_dense_off",
    "streaming_pruned_off",
    "streaming_dense_reset",
    "streaming_pruned_reset",
]


def _load(path: Path) -> dict[str, Any]:
    with path.open() as handle:
        return json.load(handle)


def _acc(summary: dict[str, Any], key: str) -> float:
    return float(summary[key]["accuracy"])


def _wall_s(summary: dict[str, Any]) -> float:
    return float(summary["total_wall_ms"]) / 1000.0


def _int_field(summary: dict[str, Any], key: str) -> int:
    return int(summary.get(key, 0))


def _fmt(value: float) -> str:
    return f"{value:.3f}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "artifact_dir",
        type=Path,
        help="Directory holding <arm>_summary.json files.",
    )
    args = parser.parse_args()

    summaries: dict[str, dict[str, Any]] = {}
    for arm in ARMS:
        path = args.artifact_dir / f"{arm}_summary.json"
        if path.exists():
            summaries[arm] = _load(path)

    if "cold_dense" not in summaries:
        raise SystemExit(f"missing {args.artifact_dir}/cold_dense_summary.json")

    base = summaries["cold_dense"]

    print("\n== Raw summary ==")
    header = (
        f"{'arm':24s} {'all':>6s} {'q0':>6s} {'q23':>6s} "
        f"{'wall_s':>8s} {'parse':>6s} {'degen':>6s}"
    )
    print(header)
    print("-" * len(header))
    for arm in ARMS:
        summary = summaries.get(arm)
        if summary is None:
            continue
        print(
            f"{arm:24s} "
            f"{_fmt(_acc(summary, 'all_queries')):>6s} "
            f"{_fmt(_acc(summary, 'first_queries')):>6s} "
            f"{_fmt(_acc(summary, 'follow_ups')):>6s} "
            f"{_wall_s(summary):8.1f} "
            f"{_int_field(summary, 'parse_failures'):6d} "
            f"{_int_field(summary, 'degenerate_queries'):6d}"
        )

    print("\n== Accuracy deltas vs cold_dense ==")
    for arm in ARMS:
        summary = summaries.get(arm)
        if arm == "cold_dense" or summary is None:
            continue
        print(
            f"{arm:24s} "
            f"all {_acc(summary, 'all_queries') - _acc(base, 'all_queries'):+.3f}  "
            f"q0 {_acc(summary, 'first_queries') - _acc(base, 'first_queries'):+.3f}  "
            f"q23 {_acc(summary, 'follow_ups') - _acc(base, 'follow_ups'):+.3f}"
        )

    needed = {"cold_pruned", "streaming_dense_off", "streaming_pruned_off"}
    if needed.issubset(summaries):
        v_only = _acc(summaries["cold_pruned"], "all_queries") - _acc(base, "all_queries")
        k_only = (
            _acc(summaries["streaming_dense_off"], "all_queries")
            - _acc(base, "all_queries")
        )
        combined = (
            _acc(summaries["streaming_pruned_off"], "all_queries")
            - _acc(base, "all_queries")
        )
        interaction = combined - (v_only + k_only)

        print("\n== Composition decomposition (all_queries) ==")
        print(f"V-only (cold_pruned - cold_dense):            {v_only:+.3f}")
        print(f"K-only (streaming_dense_off - cold_dense):    {k_only:+.3f}")
        print(f"Combined (streaming_pruned_off - cold_dense): {combined:+.3f}")
        print(f"Interaction term (combined - V - K):          {interaction:+.3f}")

        if abs(interaction) > max(abs(v_only), abs(k_only)):
            print("-> interaction term dominates; combined is NON-ADDITIVE")
        elif abs(v_only) >= abs(k_only):
            print("-> V-only dominates the loss")
        else:
            print("-> K-only dominates the loss")

    if {"streaming_dense_off", "streaming_dense_reset"}.issubset(summaries):
        off = summaries["streaming_dense_off"]
        reset = summaries["streaming_dense_reset"]
        print("\n== Hard-reset recovery: dense streaming ==")
        print(
            f"q23 acc off={_acc(off, 'follow_ups'):.3f}  "
            f"reset={_acc(reset, 'follow_ups'):.3f}  "
            f"delta={_acc(reset, 'follow_ups') - _acc(off, 'follow_ups'):+.3f}"
        )
        print(
            f"q0  acc off={_acc(off, 'first_queries'):.3f}  "
            f"reset={_acc(reset, 'first_queries'):.3f}  "
            f"delta={_acc(reset, 'first_queries') - _acc(off, 'first_queries'):+.3f}"
        )

    if {"streaming_pruned_off", "streaming_pruned_reset"}.issubset(summaries):
        off = summaries["streaming_pruned_off"]
        reset = summaries["streaming_pruned_reset"]
        print("\n== Hard-reset recovery: pruned streaming ==")
        print(
            f"q23 acc off={_acc(off, 'follow_ups'):.3f}  "
            f"reset={_acc(reset, 'follow_ups'):.3f}  "
            f"delta={_acc(reset, 'follow_ups') - _acc(off, 'follow_ups'):+.3f}"
        )
        print(
            f"q0  acc off={_acc(off, 'first_queries'):.3f}  "
            f"reset={_acc(reset, 'first_queries'):.3f}  "
            f"delta={_acc(reset, 'first_queries') - _acc(off, 'first_queries'):+.3f}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
