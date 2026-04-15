#!/usr/bin/env python3
"""Select dev-Pareto winners and project their holdout calibration to plan phase 1.12.

Reads:
- dev Pareto JSON (from pareto_analysis.py output)
- holdout calibration JSON (calibrated active reuse for the holdout slice)
- holdout dense frame-budget JSON (for headroom calc)

For each dev candidate (sorted by cached_accuracy at lowest fresh_frames),
looks up the same policy label in the holdout calibration, computes the
holdout-side effective_fresh_frames, and reports the matched dense-N
holdout point. Output is a curated launch list for phase 1.12.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _effective_fresh_frames(reuse: float, total_frames: int) -> float:
    if total_frames <= 1:
        return float(total_frames)
    return 1.0 + (total_frames - 1) * (1.0 - reuse)


def _dedupe_equivalents(
    candidates: list[dict[str, Any]], total_frames: int
) -> list[dict[str, Any]]:
    """Collapse Pareto candidates that represent the same operating point.

    With frame_count=N, max_age >= N-1 cannot bind on any cached decision
    (only N-1 reuse decisions exist). Two candidates that differ only in a
    non-binding max_age will produce bit-identical outputs; treat them as
    one policy.

    Fingerprint each row by (statistic, static_threshold, shifted_threshold,
    reuse_classes, empirical accuracy/reuse) and collapse by that key.
    Prefer the canonical max_age=None form when both are present.
    """
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    order: list[tuple[Any, ...]] = []
    for cand in candidates:
        key = (
            cand.get("statistic"),
            cand.get("static_threshold"),
            cand.get("shifted_threshold"),
            tuple(cand.get("reuse_classes") or ()),
            round(float(cand["cached_accuracy"]), 6),
            round(float(cand["effective_fresh_frames"]), 6),
            round(float(cand["mean_active_reuse"]), 6),
        )
        if key not in groups:
            order.append(key)
            groups[key] = []
        groups[key].append(cand)

    deduped: list[dict[str, Any]] = []
    for key in order:
        members = groups[key]
        if len(members) == 1:
            deduped.append(members[0])
            continue
        noage = [m for m in members if m.get("max_age") is None]
        if noage:
            deduped.append(noage[0])
        else:
            non_binding = [
                m
                for m in members
                if m.get("max_age") is not None
                and int(m["max_age"]) >= total_frames - 1
            ]
            if non_binding:
                deduped.append(min(non_binding, key=lambda m: int(m["max_age"])))
            else:
                deduped.append(min(members, key=lambda m: int(m.get("max_age") or 0)))
    return deduped


def _dense_at_budget(dense_runs: list[dict[str, Any]], budget: float) -> tuple[int, float]:
    eligible = [d for d in dense_runs if int(d["frame_count"]) <= budget]
    if not eligible:
        eligible = [min(dense_runs, key=lambda d: int(d["frame_count"]))]
    chosen = max(eligible, key=lambda d: int(d["frame_count"]))
    return (
        int(chosen["frame_count"]),
        float(chosen.get("dense_accuracy") or chosen.get("accuracy") or 0.0),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev-pareto", type=Path, required=True)
    parser.add_argument("--holdout-calibration", type=Path, required=True)
    parser.add_argument("--holdout-dense", type=Path, required=True)
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument("--total-frames", type=int, default=8)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    dev = json.loads(args.dev_pareto.read_text())
    holdout_cal = json.loads(args.holdout_calibration.read_text())
    holdout_dense = json.loads(args.holdout_dense.read_text())
    if "runs" in holdout_dense:
        dense_runs = holdout_dense["runs"]
    elif "dense_curve" in holdout_dense:
        dense_runs = holdout_dense["dense_curve"]
    else:
        raise ValueError(f"unrecognized dense schema in {args.holdout_dense}")

    cal_by_label = {p["candidate"]["label"]: p for p in holdout_cal["points"]}
    dev_candidates = dev.get("pareto_candidates") or []
    dev_candidates = sorted(
        dev_candidates, key=lambda c: (-c["cached_accuracy"], c["effective_fresh_frames"])
    )
    dev_candidates = _dedupe_equivalents(dev_candidates, args.total_frames)

    rows = []
    missing = []
    for cand in dev_candidates[: args.top_n]:
        label = cand["label"]
        cal_entry = cal_by_label.get(label)
        if cal_entry is None:
            missing.append(label)
            continue
        holdout_reuse = float(cal_entry["mean_active_reuse"])
        holdout_fresh = _effective_fresh_frames(holdout_reuse, args.total_frames)
        match_frames, match_dense = _dense_at_budget(dense_runs, holdout_fresh)
        rows.append(
            {
                "label": label,
                "dev_cached_accuracy": cand["cached_accuracy"],
                "dev_fresh_frames": cand["effective_fresh_frames"],
                "dev_reuse": cand["mean_active_reuse"],
                "holdout_calibrated_reuse": holdout_reuse,
                "holdout_fresh_frames": holdout_fresh,
                "holdout_match_dense_frames": match_frames,
                "holdout_match_dense_accuracy": match_dense,
                "candidate_payload": cand,
            }
        )

    payload = {
        "dev_pareto_source": str(args.dev_pareto),
        "holdout_calibration_source": str(args.holdout_calibration),
        "holdout_dense_source": str(args.holdout_dense),
        "total_frames": args.total_frames,
        "top_n_requested": args.top_n,
        "selected_count": len(rows),
        "missing_labels": missing,
        "selected": rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"Wrote {args.out} with {len(rows)} selected (missing {len(missing)})")
    for row in rows:
        label = row["label"]
        dev_acc = row["dev_cached_accuracy"]
        dev_fresh = row["dev_fresh_frames"]
        h_fresh = row["holdout_fresh_frames"]
        h_match = row["holdout_match_dense_frames"]
        h_dense = row["holdout_match_dense_accuracy"]
        print(
            f"  {label:<58} dev:{dev_acc:.3f}@{dev_fresh:.2f}  "
            f"h-fresh:{h_fresh:.2f}  vs d-{h_match}={h_dense:.3f}"
        )


if __name__ == "__main__":
    main()
