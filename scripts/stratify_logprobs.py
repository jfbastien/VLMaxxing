#!/usr/bin/env python3
"""Stratify benchmark items by dense-path answer-margin to separate
confidence-limited from staleness-limited disagreements.

Reads a benchmark JSONL produced with `--log-option-logprobs` and writes a
summary that bins items into:

- confidence-limited: dense top_margin < CONF_LOW (dense itself uncertain)
- staleness-agnostic: both dense and cached top_margin >= CONF_HIGH
- staleness-limited: dense top_margin >= CONF_HIGH but cached < CONF_LOW
- ambiguous: everything else

Within each bin the script reports cached vs dense agreement, accuracy,
and Wilson 95% CIs. Pareto and policy comparisons should be conditioned on
this stratification so high-confidence disagreements are not diluted by
items where dense itself was guessing.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any


def _wilson_interval(k: int, n: int, *, z: float = 1.959963984540054) -> tuple[float, float]:
    if n <= 0:
        return 0.0, 0.0
    p = k / n
    denom = 1.0 + (z**2) / n
    center = (p + (z**2) / (2.0 * n)) / denom
    margin = z * math.sqrt((p * (1.0 - p) / n) + ((z**2) / (4.0 * n * n))) / denom
    return (center - margin, center + margin)


def _stratify_item(item: dict[str, Any], *, conf_low: float, conf_high: float) -> str:
    dense = item.get("dense", {})
    cached = item.get("cached", {})
    dense_lp = dense.get("option_logprobs") or {}
    cached_lp = cached.get("option_logprobs") or {}
    dense_margin = dense_lp.get("top_margin")
    cached_margin = cached_lp.get("top_margin")
    if dense_margin is None or cached_margin is None:
        return "missing_logprobs"
    if dense_margin < conf_low:
        return "confidence_limited"
    if dense_margin >= conf_high and cached_margin >= conf_high:
        return "staleness_agnostic"
    if dense_margin >= conf_high and cached_margin < conf_low:
        return "staleness_limited"
    return "ambiguous"


def _summarize_bin(items: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(items)
    if n == 0:
        return {"n": 0}
    dense_correct = sum(int(it.get("dense", {}).get("correct", False)) for it in items)
    cached_correct = sum(int(it.get("cached", {}).get("correct", False)) for it in items)
    agreement = sum(int(it.get("match", False)) for it in items)
    return {
        "n": n,
        "dense_accuracy": dense_correct / n,
        "dense_accuracy_ci95": list(_wilson_interval(dense_correct, n)),
        "cached_accuracy": cached_correct / n,
        "cached_accuracy_ci95": list(_wilson_interval(cached_correct, n)),
        "agreement": agreement / n,
        "agreement_ci95": list(_wilson_interval(agreement, n)),
        "item_ids": [it.get("item_id") for it in items],
    }


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open() as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _cmd_stratify(args: argparse.Namespace) -> None:
    items = _load_jsonl(args.jsonl)
    bins: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        label = _stratify_item(item, conf_low=args.conf_low, conf_high=args.conf_high)
        bins[label].append(item)
    payload = {
        "source": str(args.jsonl),
        "conf_low": args.conf_low,
        "conf_high": args.conf_high,
        "n_total": len(items),
        "bin_counts": {label: len(b) for label, b in bins.items()},
        "bin_metrics": {label: _summarize_bin(b) for label, b in bins.items()},
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"Wrote {args.out}")
    print(f"Total items: {len(items)}")
    for label, bin_items in bins.items():
        metrics = payload["bin_metrics"][label]
        if "n" in metrics and metrics["n"] > 0 and label != "missing_logprobs":
            print(
                f"  {label:<22} n={metrics['n']:>3}  "
                f"dense={metrics.get('dense_accuracy', 0):.3f}  "
                f"cached={metrics.get('cached_accuracy', 0):.3f}  "
                f"agreement={metrics.get('agreement', 0):.3f}"
            )
        else:
            print(f"  {label:<22} n={len(bin_items):>3}  (no logprob data)")


def main() -> None:
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers(dest="command", required=True)
    p = subs.add_parser("stratify")
    p.add_argument("--jsonl", type=Path, required=True)
    p.add_argument(
        "--conf-low",
        type=float,
        default=0.5,
        help="Top-margin threshold below which a path is treated as uncertain.",
    )
    p.add_argument(
        "--conf-high",
        type=float,
        default=1.0,
        help="Top-margin threshold above which a path is treated as confident.",
    )
    p.add_argument("--out", type=Path, required=True)
    p.set_defaults(handler=_cmd_stratify)
    args = parser.parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
