#!/usr/bin/env python3
"""Predict which calibrated policies are most likely to land on the Pareto
frontier given a dense frame-budget curve. CPU-only; no GPU usage.

For each calibrated policy:

- compute effective_fresh_frames = 1 + (N-1) * (1 - mean_active_reuse)
- look up the dense accuracy at the closest dense frame budget that is
  < effective_fresh_frames
- the policy is "potentially Pareto-relevant" if its calibrated reuse
  produces a fresh-frame budget where the dense baseline is materially
  weaker than the highest dense accuracy

This is a calibration-based heuristic, not a real Pareto check (which
requires knowing the cached accuracy that only the LLM can measure). It
helps prioritize sweep ordering and sanity-check whether a slice has any
chance of producing Pareto candidates at all.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class DensePoint:
    frames: int
    accuracy: float


def _load_dense(path: Path) -> list[DensePoint]:
    """Load a dense frame-budget curve from either the v1 phase-1.8 nested
    schema (`{dev: {dense_curve: [...]}}`) or the v2 phase-1.9 flat
    summary (`{runs: [...]}`)."""
    data = json.loads(path.read_text())
    if "runs" in data:
        return [
            DensePoint(frames=int(r["frame_count"]), accuracy=float(r["dense_accuracy"]))
            for r in data["runs"]
        ]
    if "dev" in data and "dense_curve" in data["dev"]:
        return [
            DensePoint(
                frames=int(r["frame_count"]),
                accuracy=float(r.get("dense_accuracy") or r.get("accuracy") or 0.0),
            )
            for r in data["dev"]["dense_curve"]
        ]
    if "dense_curve" in data:
        return [
            DensePoint(
                frames=int(r["frame_count"]),
                accuracy=float(r.get("dense_accuracy") or r.get("accuracy") or 0.0),
            )
            for r in data["dense_curve"]
        ]
    raise ValueError(f"unrecognized dense-curve schema in {path}")


def _effective_fresh_frames(reuse: float, total_frames: int) -> float:
    if total_frames <= 1:
        return float(total_frames)
    return 1.0 + (total_frames - 1) * (1.0 - reuse)


def _dense_at_budget(dense: list[DensePoint], budget: float) -> tuple[int, float]:
    """Return (frame_count, dense_accuracy) for the dense point with the
    largest frame_count <= budget. If budget < smallest dense frame, returns
    that smallest point."""
    eligible = [d for d in dense if d.frames <= budget]
    if not eligible:
        eligible = [min(dense, key=lambda d: d.frames)]
    chosen = max(eligible, key=lambda d: d.frames)
    return chosen.frames, chosen.accuracy


def _cmd_predict(args: argparse.Namespace) -> None:
    calibration = json.loads(Path(args.calibration).read_text())
    dense = _load_dense(Path(args.dense))
    best_dense_acc = max(d.accuracy for d in dense)
    print(f"Dense curve max accuracy: {best_dense_acc:.3f}")
    print(f"Dense points: {[(d.frames, round(d.accuracy, 3)) for d in dense]}")
    rows = []
    for point in calibration["points"]:
        reuse = float(point["mean_active_reuse"])
        fresh = _effective_fresh_frames(reuse, args.total_frames)
        match_frames, match_dense = _dense_at_budget(dense, fresh)
        # heuristic: "headroom" is the gap between best_dense_acc and
        # match_dense. If headroom > 0, a cached policy at this budget
        # COULD beat dense at the matched budget if its accuracy is between
        # match_dense and best_dense_acc.
        headroom = best_dense_acc - match_dense
        rows.append(
            {
                "label": point["candidate"]["label"],
                "calibrated_reuse": reuse,
                "effective_fresh_frames": fresh,
                "match_dense_frames": match_frames,
                "match_dense_accuracy": match_dense,
                "headroom": headroom,
                "statistic": point["candidate"]["statistic"],
                "max_age": point["candidate"]["max_age"],
                "reuse_classes": point["candidate"]["reuse_classes"],
            }
        )
    rows.sort(key=lambda r: (-r["headroom"], r["effective_fresh_frames"]))

    payload = {
        "calibration_path": str(args.calibration),
        "dense_path": str(args.dense),
        "total_frames": args.total_frames,
        "best_dense_accuracy": best_dense_acc,
        "predicted": rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"\nWrote {args.out}")
    print(f"\nTop {args.top} highest-headroom predictions:")
    for r in rows[: args.top]:
        print(
            f"  {r['label']:<58} reuse={r['calibrated_reuse']:.3f}  "
            f"fresh={r['effective_fresh_frames']:.2f}  "
            f"vs_dense_at_{r['match_dense_frames']}={r['match_dense_accuracy']:.3f}  "
            f"headroom={r['headroom']:+.3f}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers(dest="command", required=True)
    p = subs.add_parser("predict")
    p.add_argument("--calibration", type=Path, required=True)
    p.add_argument("--dense", type=Path, required=True)
    p.add_argument("--total-frames", type=int, default=8)
    p.add_argument("--top", type=int, default=20)
    p.add_argument("--out", type=Path, required=True)
    p.set_defaults(handler=_cmd_predict)
    args = parser.parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
