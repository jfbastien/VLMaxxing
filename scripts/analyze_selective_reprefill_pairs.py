#!/usr/bin/env python3
"""Summarize paired fidelity and latency for selective re-prefill runs."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any


def _is_pathological_like_response(text: str | None) -> bool:
    rendered = str(text or "")
    return "addCriterion" in rendered or "自动" in rendered


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open() as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _key(row: dict[str, Any]) -> tuple[str, int]:
    return (str(row["item_id"]), int(row["q_index"]))


def _median(values: list[float]) -> float | None:
    return float(statistics.median(values)) if values else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-jsonl", type=Path, required=True)
    parser.add_argument("--baseline-jsonl", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--label", default=None)
    args = parser.parse_args()

    session_rows = _load_jsonl(args.session_jsonl)
    baseline_rows = _load_jsonl(args.baseline_jsonl)
    session_by_key = {_key(row): row for row in session_rows}
    baseline_by_key = {_key(row): row for row in baseline_rows}
    if set(session_by_key) != set(baseline_by_key):
        raise SystemExit(
            "session/baseline keys differ: "
            f"{sorted(set(session_by_key) ^ set(baseline_by_key))[:5]}"
        )

    keys = sorted(session_by_key)
    correctness_diffs = 0
    choice_diffs = 0
    mismatches: list[dict[str, Any]] = []
    session_follow_up_ms: list[float] = []
    baseline_follow_up_ms: list[float] = []
    baseline_all_ms = [float(row["elapsed_ms"]) for row in baseline_rows]
    q_index_breakdown: dict[str, dict[str, Any]] = {}
    pathological_follow_up_hits = 0
    pathological_q3_hits = 0

    for key in keys:
        session = session_by_key[key]
        baseline = baseline_by_key[key]
        if bool(session["correct"]) != bool(baseline["correct"]):
            correctness_diffs += 1
        if session.get("choice") != baseline.get("choice"):
            choice_diffs += 1
        q_index = int(session["q_index"])
        q_label = f"q{q_index + 1}"
        if q_label not in q_index_breakdown:
            q_index_breakdown[q_label] = {
                "n": 0,
                "correctness_diffs": 0,
                "choice_diffs": 0,
                "pathological_hits": 0,
            }
        q_index_breakdown[q_label]["n"] += 1
        if bool(session["correct"]) != bool(baseline["correct"]):
            q_index_breakdown[q_label]["correctness_diffs"] += 1
        if session.get("choice") != baseline.get("choice"):
            q_index_breakdown[q_label]["choice_diffs"] += 1
        if _is_pathological_like_response(session.get("response")):
            q_index_breakdown[q_label]["pathological_hits"] += 1
            if q_index > 0:
                pathological_follow_up_hits += 1
            if q_index == 2:
                pathological_q3_hits += 1
        if q_index > 0:
            session_follow_up_ms.append(float(session["elapsed_ms"]))
            baseline_follow_up_ms.append(float(baseline["elapsed_ms"]))
        if bool(session["correct"]) != bool(baseline["correct"]) or session.get(
            "choice"
        ) != baseline.get("choice"):
            mismatches.append(
                {
                    "item_id": session["item_id"],
                    "q_index": q_index,
                    "session_choice": session.get("choice"),
                    "baseline_choice": baseline.get("choice"),
                    "session_correct": bool(session["correct"]),
                    "baseline_correct": bool(baseline["correct"]),
                }
            )

    session_follow_up_median_ms = _median(session_follow_up_ms)
    baseline_follow_up_median_ms = _median(baseline_follow_up_ms)
    baseline_all_query_median_ms = _median(baseline_all_ms)
    output = {
        "label": args.label or args.session_jsonl.stem,
        "n_pairs": len(keys),
        "n_follow_up_pairs": len(session_follow_up_ms),
        "paired_correctness_diffs": correctness_diffs,
        "paired_choice_diffs": choice_diffs,
        "pathological_follow_up_hits": pathological_follow_up_hits,
        "pathological_q3_hits": pathological_q3_hits,
        "session_follow_up_median_ms": session_follow_up_median_ms,
        "baseline_follow_up_median_ms": baseline_follow_up_median_ms,
        "baseline_all_query_median_ms": baseline_all_query_median_ms,
        "speedup_follow_up_median_cold_over_session": (
            baseline_follow_up_median_ms / session_follow_up_median_ms
            if baseline_follow_up_median_ms is not None
            and session_follow_up_median_ms is not None
            and session_follow_up_median_ms > 0
            else None
        ),
        "speedup_all_query_median_cold_over_session_follow_up": (
            baseline_all_query_median_ms / session_follow_up_median_ms
            if baseline_all_query_median_ms is not None
            and session_follow_up_median_ms is not None
            and session_follow_up_median_ms > 0
            else None
        ),
        "q_index_breakdown": q_index_breakdown,
        "mismatches": mismatches,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(f"[selective-reprefill] wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
