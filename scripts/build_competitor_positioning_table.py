#!/usr/bin/env python3
"""Build the competitor-positioning paper table for 1.51V.

Reads three Phase 1.51V Qwen 7B 8f VideoMME dev30 summaries:
- unpatched (dense reference)
- magnitude_norm L=2 kr=0.5 (the paper-headline scorer)
- uniform_random L=2 kr=0.5 seed=42 (the 1.51VC trivial-baseline competitor)

and emits:
- ``paper/arxiv/generated/data/competitor_positioning_snapshot.json`` with
  the per-arm numbers and source paths.
- ``paper/arxiv/generated/tables/competitor_positioning.tex`` with a
  paper-ready three-row positioning table.

Why this is the right competitor positioning evidence:

The codex round-36 paper-defensibility critique asked for "one matched
runnable visual-token pruning baseline." A FasterVLM CLS-attention
reproduction is structurally different from Qwen 2.5-VL's spatial-merge
pruning point and would require new model surgery; running the existing
infrastructure with a *random keep* scorer at matched keep-rate is the
cleanest reviewer-defense move because it directly tests "does the
structured magnitude scorer earn its keep over a trivial baseline at the
same compute budget?" — the only honest reading of "head-to-head against
a simple baseline."

The Δacc gap between magnitude_norm and uniform_random at matched
keep-rate is the headline number the paper should surface alongside
peer-method citations (FastV / FasterVLM / HERMES / SparseVILA).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS = REPO_ROOT / "research" / "experiments" / "2026" / "artifacts"
GENERATED_DATA = REPO_ROOT / "paper" / "arxiv" / "generated" / "data"
GENERATED_TABLES = REPO_ROOT / "paper" / "arxiv" / "generated" / "tables"

CELLS = [
    {
        "label": "Unpatched (dense reference)",
        "summary_path": (
            ARTIFACTS / "phase1_51V_qwen_cross_arch" / "videomme_dev30_8f_unpatched_summary.json"
        ),
        "kr_label": "1.00",
        "scorer_label": "(no pruning)",
    },
    {
        "label": "magnitude_norm (paper headline)",
        "summary_path": (
            ARTIFACTS / "phase1_51V_qwen_cross_arch" / "videomme_dev30_8f_L2_kr050_summary.json"
        ),
        "kr_label": "0.50",
        "scorer_label": "L2-norm of group mean hidden state",
    },
    {
        "label": "uniform\\_random (1.51VC competitor)",
        "summary_path": (
            ARTIFACTS
            / "phase1_51VC_random_keep_baseline"
            / "videomme_dev30_8f_L2_kr050_uniform_random_seed42_summary.json"
        ),
        "kr_label": "0.50",
        "scorer_label": "deterministic seeded random keep",
    },
]


def _load(cell: dict[str, Any]) -> dict[str, Any] | None:
    path = cell["summary_path"]
    if not path.exists():
        return None
    return json.loads(path.read_text())


def _build_snapshot() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    dense_acc: float | None = None
    for cell in CELLS:
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
        rows.append(
            {
                "label": cell["label"],
                "scorer_label": cell["scorer_label"],
                "kr_label": cell["kr_label"],
                "n_items": int(summary["n_items"]),
                "frame_count": int(summary["frame_count"]),
                "accuracy": accuracy,
                "delta_vs_dense": (accuracy - dense_acc) if dense_acc is not None else 0.0,
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
        )
    snapshot = {
        "model": "Qwen 2.5-VL-7B-Instruct-4bit (MLX)",
        "manifest": "research/benchmark_manifests/videomme_dev_v1.toml",
        "n_items": 30,
        "frame_count": 8,
        "vision_tower_layer": 2,
        "model_note": (
            "matched keep-rate competitor positioning at (n=30 items, 8 frames, "
            "vision-tower layer L=2). Δacc reported relative to the unpatched "
            "dense reference row. uniform_random uses a deterministic per-call "
            "rng.default_rng(seed=42) to draw scores at the merged-group axis; "
            "the keep-rate selection then proceeds through the same window-aligned "
            "prune planner the magnitude_norm scorer feeds."
        ),
        "rows": rows,
    }
    return snapshot


def _delta(value: float) -> str:
    sign = "-" if value < 0 else "+"
    return f"{sign}{abs(value) * 100:.1f}\\,pp"


def _emit_table(snapshot: dict[str, Any]) -> str:
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        (
            r"\caption{Competitor positioning at matched keep-rate. Same Qwen "
            r"2.5-VL-7B-Instruct-4bit, same VideoMME dev30 manifest, same "
            r"frame count, same vision-tower cut layer \(L=2\). The "
            r"\emph{magnitude\_norm} row is the structured scorer the paper "
            r"reports as the C-VISION pruning headline; the "
            r"\emph{uniform\_random} row is a trivial-baseline competitor at "
            r"matched compute. The Δacc column quantifies how much the "
            r"structured anchor earns over random selection at the same "
            r"keep-rate. Speedup is per-stage \emph{vision-tower wall-clock} "
            r"reduction vs the unpatched reference.}"
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
            f"{row['n_items']} & "
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
