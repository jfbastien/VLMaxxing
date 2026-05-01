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

This is the honest replacement for warm-only follow-up multipliers. The
generator surfaces the dependence on total session length so reviewers can
read the economics at any session length.

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
import statistics
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
QWEN_CELLS = [
    ("phase1_55A_16f_frame_scaling", "7B / 16f", "qwen2_5_vl_7b_4bit", 16),
    ("phase1_55A_18f_frame_scaling", "7B / 18f", "qwen2_5_vl_7b_4bit", 18),
    ("phase1_55A_20f_frame_scaling", "7B / 20f", "qwen2_5_vl_7b_4bit", 20),
    ("phase1_55A_24f_frame_scaling", "7B / 24f", "qwen2_5_vl_7b_4bit", 24),
    ("phase1_55A_32f_frame_scaling", "7B / 32f", "qwen2_5_vl_7b_4bit", 32),
    ("phase1_55A_3b_20f_crossarch", "3B / 20f", "qwen2_5_vl_3b_4bit", 20),
]
GEMMA_PREFIX_SNAPSHOT_CELLS = [
    (
        "sam_scaleout_m5_20260429/sam_m5_5b_swa_prefix_snapshot.jsonl",
        "Gemma 26B / 8f",
        "gemma_4_26b_a4b",
        8,
    ),
    (
        "sam_scaleout_m5_20260429/sam_m5_5b_swa_prefix_snapshot_32f.jsonl",
        "Gemma 26B / 32f",
        "gemma_4_26b_a4b",
        32,
    ),
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


def _prefix_snapshot_speedup(
    *,
    warm_ms: float,
    follow_ms: float,
    baseline_ms: float,
    n_total_queries: int,
) -> dict[str, float]:
    if n_total_queries < 1:
        raise ValueError(f"n_total_queries must be >= 1, got {n_total_queries}")
    naive_total = n_total_queries * baseline_ms
    persist_total = warm_ms + n_total_queries * follow_ms
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


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _build_snapshot() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for artifact_dir, display, model, frame_count in QWEN_CELLS:
        summary = _load_cell(artifact_dir)
        if summary is None:
            continue
        first = float(summary["session_first_query"]["mean_elapsed_ms"])
        follow = float(summary["session_follow_up"]["mean_elapsed_ms"])
        baseline = float(summary["baseline"]["mean_elapsed_ms"])
        warm_speedup = baseline / max(follow, 1e-12)
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
                "setup_model": "first_query_then_followups",
                "setup_model_note": "persist_total = first_query + (Q - 1) * follow_up",
                "first_query_mean_ms": first,
                "follow_up_mean_ms": follow,
                "baseline_mean_ms": baseline,
                "warm_speedup": warm_speedup,
                "accuracy_delta_session_minus_baseline": delta_acc,
                "setup_inclusive": per_n,
                "source": (f"research/experiments/2026/artifacts/{artifact_dir}/summary.json"),
            }
        )

    for rel_path, display, model, frame_count in GEMMA_PREFIX_SNAPSHOT_CELLS:
        source_path = ARTIFACTS / rel_path
        jsonl_rows = _load_jsonl(source_path)
        if not jsonl_rows:
            continue
        warm_values = [
            float(row["policy_params"]["warm_ms"])
            for row in jsonl_rows
            if row.get("policy_params") and row["policy_params"].get("warm_ms") is not None
        ]
        follow_values = [float(row["end_to_end_ms"]) for row in jsonl_rows]
        baseline_values = [float(row["baseline_end_to_end_ms"]) for row in jsonl_rows]
        if not warm_values or not follow_values or not baseline_values:
            raise ValueError(f"{source_path} is missing warm/follow/baseline timing fields")
        warm = float(statistics.mean(warm_values))
        follow = float(statistics.mean(follow_values))
        baseline = float(statistics.mean(baseline_values))
        per_n = [
            _prefix_snapshot_speedup(
                warm_ms=warm,
                follow_ms=follow,
                baseline_ms=baseline,
                n_total_queries=n,
            )
            for n in N_VALUES
        ]
        rows.append(
            {
                "artifact_dir": rel_path,
                "display": display,
                "model": model,
                "frame_count": frame_count,
                "setup_model": "prefix_snapshot_then_queries",
                "setup_model_note": "persist_total = prefix_warm + Q * follow_up",
                "prefix_warm_mean_ms": warm,
                "follow_up_mean_ms": follow,
                "baseline_mean_ms": baseline,
                "warm_speedup": baseline / max(follow, 1e-12),
                "median_per_row_warm_speedup": float(
                    statistics.median(
                        float(row["baseline_end_to_end_ms"]) / float(row["end_to_end_ms"])
                        for row in jsonl_rows
                    )
                ),
                "accuracy_delta_session_minus_baseline": 0.0,
                "setup_inclusive": per_n,
                "source": f"research/experiments/2026/artifacts/{rel_path}",
            }
        )

    snapshot = {
        "n_total_queries_grid": N_VALUES,
        "model_note": (
            "warm_speedup is baseline_mean / follow_up_mean (per-follow-up only, mean-timing "
            "denominator). setup_inclusive[i].speedup is the actual session-level multiplier "
            "at N total same-video queries using each row's setup_model_note."
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
            r"same video. Qwen rows use the measured cold first query plus "
            r"\(Q-1\) follow-ups; Gemma prefix-snapshot rows use the measured "
            r"prefix warm-up plus \(Q\) follow-up queries. "
            r"At \(Q=1\) the cold first-query cost dominates and the "
            r"speedup approaches~1; at large \(Q\) it asymptotes to the "
            r"mean per-follow-up multiplier. \(\Delta\)acc is the paired "
            r"session-vs-baseline accuracy delta when available; Gemma rows "
            r"report 0 because the prefix-snapshot artifacts have zero paired "
            r"correctness diffs against cold dense.}"
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
