#!/usr/bin/env python3
"""Compare one or more phase-1.57 feature-drift summaries.

This is the paper-hygiene companion to ``measure_feature_drift.py``.
The experiment runner already emits per-class cosine aggregates for a
single manifest / split; this script aligns multiple summaries and
reports how the STATIC / SHIFTED / NOVEL distributions moved across
splits or frame counts.

Typical use:

    uv run python scripts/compare_feature_drift.py \
        --summary research/experiments/2026/artifacts/phase1_57/qwen_16f_dev.json \
        --summary research/experiments/2026/artifacts/phase1_57/qwen_16f_holdout.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

CLASS_KEYS = ("static", "shifted", "novel")
METRIC_KEYS = ("mean_cos", "median_cos", "p05_cos", "p95_cos")


def _load_summary(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    if "aggregate" not in payload:
        raise ValueError(f"{path} is missing aggregate data")
    return payload


def _label(summary: dict[str, Any], fallback: str) -> str:
    manifests = summary.get("manifest", [])
    manifest_suffix = ",".join(Path(m).stem for m in manifests) if manifests else fallback
    group = summary.get("group_filter")
    frame_count = summary.get("frame_count")
    model = summary.get("model", fallback)
    parts = [model, manifest_suffix]
    if group is not None:
        parts.append(group)
    if frame_count is not None:
        parts.append(f"{frame_count}f")
    return " / ".join(str(part) for part in parts)


def _fmt_float(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:+.4f}"


def _row_value(summary: dict[str, Any], class_key: str, metric_key: str) -> float | None:
    row = summary.get("aggregate", {}).get(class_key, {})
    if not row:
        return None
    value = row.get(metric_key)
    return float(value) if value is not None else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--summary",
        type=Path,
        action="append",
        required=True,
        help="Path to a phase-1.57 summary JSON (repeat to compare multiple runs)",
    )
    args = parser.parse_args()

    loaded = [
        (_label(summary, path.stem), summary)
        for path in args.summary
        for summary in [_load_summary(path)]
    ]
    if len(loaded) < 2:
        raise SystemExit("need at least two --summary inputs to compare")

    print(f"Compared {len(loaded)} summaries")
    print()
    for class_key in CLASS_KEYS:
        print(class_key.upper())
        header = ["metric", *(label for label, _ in loaded), "max_span"]
        widths = [max(len(col), 12) for col in header]
        fmt = "  ".join(f"{{:{width}s}}" for width in widths)
        print(fmt.format(*header))
        for metric_key in METRIC_KEYS:
            values = [_row_value(summary, class_key, metric_key) for _, summary in loaded]
            numeric = [value for value in values if value is not None]
            span = (max(numeric) - min(numeric)) if numeric else None
            row = [metric_key, *(_fmt_float(value) for value in values), _fmt_float(span)]
            print(fmt.format(*row))
        print()

    baseline_label, baseline_summary = loaded[0]
    for label, summary in loaded[1:]:
        print(f"Delta vs baseline: {baseline_label} -> {label}")
        for class_key in CLASS_KEYS:
            base = _row_value(baseline_summary, class_key, "mean_cos")
            current = _row_value(summary, class_key, "mean_cos")
            delta = None if base is None or current is None else current - base
            print(f"  {class_key:<8s} mean_cos Δ={_fmt_float(delta)}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
