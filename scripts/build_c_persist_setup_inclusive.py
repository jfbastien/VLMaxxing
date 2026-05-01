#!/usr/bin/env python3
"""Setup-inclusive C-PERSIST economics generator.

Reads existing phase 1.55A* summary.json artifacts that carry per-session
timing (session_first_query, session_follow_up, baseline) and emits:

- ``paper/arxiv/generated/data/c_persist_setup_inclusive_snapshot.json``
  with the per-cell numbers and source paths.
- ``paper/arxiv/generated/tables/c_persist_setup_inclusive.tex``
  with a paper-ready setup-inclusive speedup table.

Setup-inclusive speedup model
-----------------------------

Naive baseline (cold every query):
    naive_total(N)   = N * baseline_mean_ms

C-PERSIST session (cold first query, cheap follow-ups):
    persist_total(N) = first_query_mean_ms + (N - 1) * follow_up_mean_ms

    Speedup at N total session queries = naive_total / persist_total.

This is the honest replacement for the "follow-up speedup" headline
(``speedup_first_over_follow``) that absorbs the warm-up cost on the
denominator. The paper currently reports the warm-only multiplier; this
    generator surfaces the dependence on total session length so reviewers can read the
economics at any session length.

Note on baseline rows: many of the input summaries use stateless
question-cycle baselines (deterministic replicas), which is correct for
turn-matched paired drift but is valid as a *single-query* timing
denominator only because each baseline row is a fresh cold prefill.
This script uses ``baseline.mean_elapsed_ms`` as the cold-per-query
cost; the paper-side table caption flags this.
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

# Cells to surface in the paper table. Filename → (display label, model tag,
# frame count). Only landed C-PERSIST cells with full timing are included; we
# deliberately avoid using e.g. 1.55D selective re-prefill cells because the
# economics there fold in re-prefill cost which is conceptually different.
CELLS = [
    ("phase1_55A_16f_frame_scaling", "7B / 16f", "qwen2_5_vl_7b_4bit", 16),
    ("phase1_55A_18f_frame_scaling", "7B / 18f", "qwen2_5_vl_7b_4bit", 18),
    ("phase1_55A_20f_frame_scaling", "7B / 20f", "qwen2_5_vl_7b_4bit", 20),
    ("phase1_55A_24f_frame_scaling", "7B / 24f", "qwen2_5_vl_7b_4bit", 24),
    ("phase1_55A_32f_frame_scaling", "7B / 32f", "qwen2_5_vl_7b_4bit", 32),
    ("phase1_55A_3b_20f_crossarch", "3B / 20f", "qwen2_5_vl_3b_4bit", 20),
]
N_VALUES = [1, 2, 5, 10, 50]


def _setup_inclusive_speedup(
    *,
    first_ms: float,
    follow_ms: float,
    baseline_ms: float,
    n_total_queries: int,
) -> dict[str, float]:
    if n_total_queries < 1:
        raise ValueError(f"n_total_queries must be >= 1, got {n_total_queries}")
    naive_total = n_total_queries * baseline_ms
    persist_total = first_ms + (n_total_queries - 1) * follow_ms
    return {
        "n_total_queries": n_total_queries,
        "naive_total_ms": float(naive_total),
        "persist_total_ms": float(persist_total),
        "speedup": float(naive_total / max(persist_total, 1e-12)),
    }


def _load_cell(artifact_dir: str) -> dict[str, Any] | None:
    path = ARTIFACTS / artifact_dir / "summary.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def _build_snapshot() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for artifact_dir, display, model, frame_count in CELLS:
        summary = _load_cell(artifact_dir)
        if summary is None:
            continue
        first = float(summary["session_first_query"]["mean_elapsed_ms"])
        follow = float(summary["session_follow_up"]["mean_elapsed_ms"])
        baseline = float(summary["baseline"]["mean_elapsed_ms"])
        warm_speedup = float(
            summary.get("speedup_first_over_follow", baseline / max(follow, 1e-12))
        )
        delta_acc = float(summary.get("accuracy_delta_session_minus_baseline", 0.0))
        per_n = [
            _setup_inclusive_speedup(
                first_ms=first,
                follow_ms=follow,
                baseline_ms=baseline,
                n_total_queries=n,
            )
            for n in N_VALUES
        ]
        rows.append(
            {
                "artifact_dir": artifact_dir,
                "display": display,
                "model": model,
                "frame_count": frame_count,
                "first_query_mean_ms": first,
                "follow_up_mean_ms": follow,
                "baseline_mean_ms": baseline,
                "warm_speedup": warm_speedup,
                "accuracy_delta_session_minus_baseline": delta_acc,
                "setup_inclusive": per_n,
                "source": (f"research/experiments/2026/artifacts/{artifact_dir}/summary.json"),
            }
        )

    snapshot = {
        "n_total_queries_grid": N_VALUES,
        "model_note": (
            "warm_speedup is baseline_mean / follow_up_mean (per-follow-up only); "
            "setup_inclusive[i].speedup is N*baseline / (first_query + (N-1)*follow_up), "
            "the actual session-level multiplier at N total same-video queries."
        ),
        "cells": rows,
    }
    return snapshot


def _format_speedup(s: float) -> str:
    return f"{s:.2f}"


def _emit_table(snapshot: dict[str, Any]) -> str:
    n_grid = snapshot["n_total_queries_grid"]
    header_n = " & ".join(f"Q={n}" for n in n_grid)
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        (
            r"\caption{Setup-inclusive C-PERSIST session economics. "
            r"\emph{Warm} is the per-follow-up multiplier currently "
            r"reported elsewhere; \emph{Q=k} is the actual session-level "
            r"speedup when a session has \(k\) total queries on the "
            r"same video, computed as "
            r"\(Q \cdot \mathrm{baseline} / (\mathrm{first} + (Q-1) \cdot \mathrm{follow})\). "
            r"At \(Q=1\) the cold first-query cost dominates and the "
            r"speedup approaches~1; at large \(Q\) it asymptotes to the "
            r"per-follow-up multiplier. \(\Delta\)acc is the paired session-vs-baseline "
            r"accuracy delta.}"
        ),
        r"\label{tab:c-persist-setup-inclusive}",
        r"\small",
        r"\begin{tabular}{@{}l r r " + " r" * len(n_grid) + r"@{}}",
        r"\toprule",
        (r"Cell & $\Delta$acc & Warm & " + header_n + r" \\"),
        r"\midrule",
    ]
    for cell in snapshot["cells"]:
        n_speedups = " & ".join(
            _format_speedup(entry["speedup"]) for entry in cell["setup_inclusive"]
        )
        lines.append(
            f"{cell['display']} & {cell['accuracy_delta_session_minus_baseline']:+.2f} & "
            f"{_format_speedup(cell['warm_speedup'])}$\\times$ & {n_speedups} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate setup-inclusive C-PERSIST economics snapshot + paper table."
    )
    parser.add_argument(
        "--snapshot-path",
        type=Path,
        default=GENERATED_DATA / "c_persist_setup_inclusive_snapshot.json",
    )
    parser.add_argument(
        "--table-path",
        type=Path,
        default=GENERATED_TABLES / "c_persist_setup_inclusive.tex",
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
        f"[c-persist-setup-inclusive] {len(snapshot['cells'])} cells -> "
        f"{args.snapshot_path.relative_to(REPO_ROOT)}, "
        f"{args.table_path.relative_to(REPO_ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
