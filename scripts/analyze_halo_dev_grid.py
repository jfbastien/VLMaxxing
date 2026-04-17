#!/usr/bin/env python3
"""Pick the phase 1.37B halo-veto dev-tranche winner.

Selection rule from the 2026-04-17 prereg:
  primary: cached_accuracy (higher better)
  tiebreaker 1: effective_fresh_frames (lower better)
  tiebreaker 2: agreement (higher better)

Reads every `*_summary.json` in the dev artifact directory, tabulates
the cells, and emits a JSON pick + markdown table to stdout.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _cell_row(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text())
    planner = data.get("planner", {})
    halo = planner.get("neighbor_halo_veto")
    return {
        "label": path.stem.removesuffix("_summary"),
        "cached_accuracy": data.get("cached_accuracy"),
        "dense_accuracy": data.get("dense_accuracy"),
        "agreement": data.get("agreement"),
        "reuse_ratio_mean_active": data.get("reuse_ratio_mean_active"),
        "completed_n": len(data.get("completed_item_ids") or []),
        "requested_n": len(data.get("requested_item_ids") or []),
        "halo": halo,
        "path": str(path),
    }


def _approx_effective_fresh_frames(row: dict[str, Any], frame_count: int = 8) -> float:
    reuse = row.get("reuse_ratio_mean_active")
    if reuse is None:
        return float(frame_count)
    reused_pairs = float(reuse) * (frame_count - 1)
    return frame_count - reused_pairs


def rank(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def key(r: dict[str, Any]) -> tuple[float, float, float]:
        acc = r.get("cached_accuracy") or 0.0
        ef = _approx_effective_fresh_frames(r)
        ag = r.get("agreement") or 0.0
        return (-acc, ef, -ag)

    return sorted(rows, key=key)


def format_markdown(rows: list[dict[str, Any]]) -> str:
    header = (
        "| label | halo | cached_acc | dense_acc | agreement | "
        "reuse_active | eff_fresh | completed |"
    )
    sep = "|---|---|---:|---:|---:|---:|---:|---:|"
    lines = [header, sep]
    for r in rows:
        halo = r.get("halo")
        halo_str = f"p={halo['percentile']}/n={halo['neighborhood']}" if halo else "(none)"
        lines.append(
            "| {label} | {halo} | {cached:.3f} | {dense:.3f} | {ag:.3f} | "
            "{reuse:.3f} | {ef:.2f} | {done}/{req} |".format(
                label=r["label"],
                halo=halo_str,
                cached=r.get("cached_accuracy") or 0.0,
                dense=r.get("dense_accuracy") or 0.0,
                ag=r.get("agreement") or 0.0,
                reuse=r.get("reuse_ratio_mean_active") or 0.0,
                ef=_approx_effective_fresh_frames(r),
                done=r.get("completed_n") or 0,
                req=r.get("requested_n") or 0,
            )
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact_dir", type=Path)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    rows = [_cell_row(p) for p in sorted(args.artifact_dir.glob("*_summary.json"))]
    if not rows:
        raise SystemExit(f"no summaries under {args.artifact_dir}")

    ranked = rank(rows)
    winner = ranked[0]
    top_k = ranked[:3]
    result = {
        "artifact_dir": str(args.artifact_dir),
        "cells_found": len(rows),
        "winner": winner,
        "top_k": top_k,
        "table_markdown": format_markdown(ranked),
    }
    text = json.dumps(result, indent=2, default=str)
    if args.out is not None:
        args.out.write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
