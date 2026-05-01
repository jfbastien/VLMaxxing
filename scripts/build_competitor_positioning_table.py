#!/usr/bin/env python3
"""Build the matched keep-rate random baseline paper table for Qwen C-VISION.

Reads Phase 1.51V/1.51VC Qwen 7B 8f VideoMME dev30 summaries:
- unpatched (dense reference)
- magnitude_norm L=2 kr=0.5 (the paper-headline scorer)
- uniform_random L=2 kr=0.5 seed=* (the trivial random-keep baseline)

and emits:
- ``paper/arxiv/generated/data/competitor_positioning_snapshot.json`` with
  the per-arm numbers and source paths.
- ``paper/arxiv/generated/tables/competitor_positioning.tex`` with a
  paper-ready three-row positioning table.

Why this is useful positioning evidence:

This is not a named peer-method comparison. It directly tests whether the
structured magnitude scorer earns its keep over a trivial baseline at the
same layer and keep-rate. Wall-clock is measured, not matched, because the
random row can have different planner and generation timing.

The delta-accuracy gap between magnitude_norm and uniform_random at matched keep-rate
is a sanity check the paper can surface alongside, but not instead of,
peer-method citations.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS = REPO_ROOT / "research" / "experiments" / "2026" / "artifacts"
GENERATED_DATA = REPO_ROOT / "paper" / "arxiv" / "generated" / "data"
GENERATED_TABLES = REPO_ROOT / "paper" / "arxiv" / "generated" / "tables"

DENSE_CELL = {
    "label": "Unpatched (dense reference)",
    "summary_path": (
        ARTIFACTS / "phase1_51V_qwen_cross_arch" / "videomme_dev30_8f_unpatched_summary.json"
    ),
    "kr_label": "1.00",
    "scorer_label": "(no pruning)",
}
MAGNITUDE_CELL = {
    "label": "magnitude\\_norm (structured scorer)",
    "summary_path": (
        ARTIFACTS / "phase1_51V_qwen_cross_arch" / "videomme_dev30_8f_L2_kr050_summary.json"
    ),
    "kr_label": "0.50",
    "scorer_label": "L2-norm of group mean hidden state",
}
RANDOM_GLOB = (
    ARTIFACTS
    / "phase1_51VC_random_keep_baseline"
    / "videomme_dev30_8f_L2_kr050_uniform_random_seed*_summary.json"
)


def _static_cells() -> list[dict[str, Any]]:
    return [
        {
            **DENSE_CELL,
            "row_kind": "dense",
        },
        {
            **MAGNITUDE_CELL,
            "row_kind": "structured",
        },
    ]


def _load(cell: dict[str, Any]) -> dict[str, Any] | None:
    path = cell["summary_path"]
    if not path.exists():
        return None
    return json.loads(path.read_text())


def _seed_from_path(path: Path) -> int:
    match = re.search(r"_seed(\d+)_summary\.json$", path.name)
    if not match:
        raise ValueError(f"could not parse uniform_random seed from {path}")
    return int(match.group(1))


def _summary_metric(summary: dict[str, Any], key: str) -> float:
    return float(summary[key])


def _row_from_summary(
    *,
    cell: dict[str, Any],
    summary: dict[str, Any],
    dense_acc: float,
) -> dict[str, Any]:
    accuracy = float(summary["dense_accuracy"])
    return {
        "label": cell["label"],
        "row_kind": cell["row_kind"],
        "scorer_label": cell["scorer_label"],
        "kr_label": cell["kr_label"],
        "n_items": int(summary["n_items"]),
        "n_items_label": str(int(summary["n_items"])),
        "frame_count": int(summary["frame_count"]),
        "accuracy": accuracy,
        "delta_vs_dense": accuracy - dense_acc,
        "parse_failures": int(summary["dense_parse_failures"]),
        "mean_kept_groups": float(summary["mean_kept_groups"]),
        "mean_total_groups": float(summary["mean_total_groups"]),
        "mean_effective_keep_rate": float(summary["mean_effective_keep_rate"]),
        "mean_vision_ms": float(summary["mean_dense_vision_ms"]),
        "mean_end_to_end_ms": float(summary["mean_dense_end_to_end_ms"]),
        "mean_decode_ms": float(summary["mean_decode_ms"]),
        "mean_peak_memory_gb": float(summary["mean_peak_memory_gb"]),
        "source": str(cell["summary_path"].relative_to(REPO_ROOT).as_posix()),
    }


def _random_row(dense_acc: float) -> dict[str, Any]:
    paths = sorted(RANDOM_GLOB.parent.glob(RANDOM_GLOB.name))
    if not paths:
        return {
            "label": "uniform\\_random (matched keep-rate)",
            "row_kind": "random",
            "scorer_label": "deterministic seeded random keep",
            "kr_label": "0.50",
            "missing": True,
        }
    summaries = [json.loads(path.read_text()) for path in paths]
    seeds = [_seed_from_path(path) for path in paths]
    accuracies = [_summary_metric(summary, "dense_accuracy") for summary in summaries]
    label = (
        "uniform\\_random (matched keep-rate)"
        if len(paths) == 1
        else f"uniform\\_random mean ({len(paths)} seeds)"
    )
    row = {
        "label": label,
        "row_kind": "random",
        "scorer_label": "deterministic seeded random keep",
        "kr_label": "0.50",
        "n_runs": len(paths),
        "seeds": seeds,
        "n_items": int(summaries[0]["n_items"]),
        "n_items_label": (
            str(int(summaries[0]["n_items"]))
            if len(paths) == 1
            else f"{int(summaries[0]['n_items'])}$\\times${len(paths)}"
        ),
        "frame_count": int(summaries[0]["frame_count"]),
        "accuracy": float(statistics.mean(accuracies)),
        "accuracy_min": float(min(accuracies)),
        "accuracy_max": float(max(accuracies)),
        "delta_vs_dense": float(statistics.mean(accuracies) - dense_acc),
        "parse_failures": float(
            statistics.mean(
                _summary_metric(summary, "dense_parse_failures") for summary in summaries
            )
        ),
        "mean_kept_groups": float(
            statistics.mean(_summary_metric(summary, "mean_kept_groups") for summary in summaries)
        ),
        "mean_total_groups": float(
            statistics.mean(_summary_metric(summary, "mean_total_groups") for summary in summaries)
        ),
        "mean_effective_keep_rate": float(
            statistics.mean(
                _summary_metric(summary, "mean_effective_keep_rate") for summary in summaries
            )
        ),
        "mean_vision_ms": float(
            statistics.mean(
                _summary_metric(summary, "mean_dense_vision_ms") for summary in summaries
            )
        ),
        "mean_end_to_end_ms": float(
            statistics.mean(
                _summary_metric(summary, "mean_dense_end_to_end_ms") for summary in summaries
            )
        ),
        "mean_decode_ms": float(
            statistics.mean(_summary_metric(summary, "mean_decode_ms") for summary in summaries)
        ),
        "mean_peak_memory_gb": float(
            statistics.mean(
                _summary_metric(summary, "mean_peak_memory_gb") for summary in summaries
            )
        ),
        "source_paths": [str(path.relative_to(REPO_ROOT).as_posix()) for path in paths],
    }
    return row


def _build_snapshot() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    dense_acc: float | None = None
    for cell in _static_cells():
        summary = _load(cell)
        if summary is None:
            rows.append(
                {
                    "label": cell["label"],
                    "scorer_label": cell["scorer_label"],
                    "kr_label": cell["kr_label"],
                    "missing": True,
                }
            )
            continue
        accuracy = float(summary["dense_accuracy"])
        if dense_acc is None:
            dense_acc = accuracy
        rows.append(_row_from_summary(cell=cell, summary=summary, dense_acc=dense_acc))
    if dense_acc is not None:
        rows.append(_random_row(dense_acc))
    structured = next((row for row in rows if row.get("row_kind") == "structured"), None)
    random = next((row for row in rows if row.get("row_kind") == "random"), None)
    structured_random_gap = None
    if structured and random and not random.get("missing"):
        structured_random_gap = float(structured["accuracy"] - random["accuracy"])
    snapshot = {
        "model": "Qwen 2.5-VL-7B-Instruct-4bit (MLX)",
        "manifest": "research/benchmark_manifests/videomme_dev_v1.toml",
        "n_items": 30,
        "frame_count": 8,
        "vision_tower_layer": 2,
        "model_note": (
            "matched keep-rate competitor positioning at (n=30 items, 8 frames, "
            "vision-tower layer L=2). Delta accuracy is reported relative to the unpatched "
            "dense reference row. uniform_random uses a deterministic per-call "
            "rng.default_rng(seed) to draw scores at the merged-group axis; the keep-rate "
            "selection then proceeds through the same window-aligned prune planner the "
            "magnitude_norm scorer feeds."
        ),
        "structured_minus_random_accuracy_gap": structured_random_gap,
        "rows": rows,
    }
    return snapshot


def _delta(value: float) -> str:
    sign = "-" if value < 0 else "+"
    return f"{sign}{abs(value) * 100:.1f}\\,pp"


def _emit_table(snapshot: dict[str, Any]) -> str:
    gap = snapshot.get("structured_minus_random_accuracy_gap")
    gap_sentence = (
        r"The structured-vs-random gap is "
        + f"{gap * 100:+.1f}"
        + r"\,pp over the random seed set present in the artifact directory. "
        if isinstance(gap, float)
        else ""
    )
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        (
            r"\caption{Random-keep sanity check at matched keep-rate. Same Qwen "
            r"2.5-VL-7B-Instruct-4bit, same VideoMME dev30 manifest, same "
            r"frame count, same vision-tower cut layer \(L=2\). The "
            r"\emph{magnitude\_norm} row is the structured Qwen scorer; the "
            r"\emph{uniform\_random} row is a trivial baseline at the same "
            r"keep-rate, not a matched-runtime peer method. The \(\Delta\)acc column is "
            r"relative to dense. "
            + gap_sentence
            + r"Wall-clock columns are measured and need not match.}"
        ),
        r"\label{tab:competitor-positioning}",
        r"\small",
        r"\begin{tabular}{@{}l c c r r r r@{}}",
        r"\toprule",
        (r"Arm & kr & N & Acc & $\Delta$acc vs dense & Vision ms & E2E ms \\"),
        r"\midrule",
    ]
    for row in snapshot["rows"]:
        if row.get("missing"):
            lines.append(f"{row['label']} & {row['kr_label']} & -- & -- & -- & -- & -- \\\\")
            continue
        lines.append(
            f"{row['label']} & "
            f"{row['kr_label']} & "
            f"{row['n_items_label']} & "
            f"{row['accuracy']:.3f} & "
            f"{_delta(row['delta_vs_dense'])} & "
            f"{row['mean_vision_ms']:.0f} & "
            f"{row['mean_end_to_end_ms']:.0f} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--snapshot-path",
        type=Path,
        default=GENERATED_DATA / "competitor_positioning_snapshot.json",
    )
    parser.add_argument(
        "--table-path",
        type=Path,
        default=GENERATED_TABLES / "competitor_positioning.tex",
    )
    args = parser.parse_args()

    snapshot = _build_snapshot()
    args.snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    args.table_path.parent.mkdir(parents=True, exist_ok=True)
    args.snapshot_path.write_text(
        json.dumps(snapshot, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
    args.table_path.write_text(_emit_table(snapshot))
    print(
        f"[competitor-positioning] {len(snapshot['rows'])} rows -> "
        f"{args.snapshot_path.relative_to(REPO_ROOT)}, "
        f"{args.table_path.relative_to(REPO_ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
