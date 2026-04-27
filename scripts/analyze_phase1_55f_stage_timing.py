#!/usr/bin/env python3
"""Explain adaptive-vs-fixed C-PERSIST speedups from existing 1.55 artifacts."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open() as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def _median(values: list[float]) -> float | None:
    return float(statistics.median(values)) if values else None


def _row_key(row: dict[str, Any]) -> tuple[str, int]:
    return (str(row["item_id"]), int(row["q_index"]))


def _summarize_policy(label: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_q: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_q[int(row["q_index"])].append(row)
    q_summary: dict[str, dict[str, Any]] = {}
    for q_index, q_rows in sorted(by_q.items()):
        elapsed = [float(row["elapsed_ms"]) for row in q_rows]
        tail_tokens = [float(row.get("tail_prompt_tokens", 0)) for row in q_rows]
        prefix_coverage = [float(row.get("prefix_coverage", 0.0)) for row in q_rows]
        q_summary[f"q{q_index + 1}"] = {
            "n": len(q_rows),
            "median_elapsed_ms": _median(elapsed),
            "median_tail_prompt_tokens": _median(tail_tokens),
            "median_prefix_coverage": _median(prefix_coverage),
            "cache_sources": sorted({str(row.get("cache_source")) for row in q_rows}),
            "reprefill_k_values": sorted({int(row.get("reprefill_k", -1)) for row in q_rows}),
        }
    follow_rows = [row for row in rows if int(row["q_index"]) > 0]
    return {
        "label": label,
        "n_rows": len(rows),
        "q_index": q_summary,
        "follow_up_median_elapsed_ms": _median([float(row["elapsed_ms"]) for row in follow_rows]),
        "follow_up_median_tail_prompt_tokens": _median(
            [float(row.get("tail_prompt_tokens", 0)) for row in follow_rows]
        ),
    }


def _paired_q3_attribution(
    adaptive_rows: list[dict[str, Any]], fixed_rows: list[dict[str, Any]]
) -> dict[str, Any]:
    adaptive_by_key = {_row_key(row): row for row in adaptive_rows if int(row["q_index"]) == 2}
    fixed_by_key = {_row_key(row): row for row in fixed_rows if int(row["q_index"]) == 2}
    if set(adaptive_by_key) != set(fixed_by_key):
        raise SystemExit(
            f"adaptive/fixed Q3 keys differ: {sorted(set(adaptive_by_key) ^ set(fixed_by_key))[:5]}"
        )
    paired: list[dict[str, Any]] = []
    for key in sorted(adaptive_by_key):
        adaptive = adaptive_by_key[key]
        fixed = fixed_by_key[key]
        adaptive_ms = float(adaptive["elapsed_ms"])
        fixed_ms = float(fixed["elapsed_ms"])
        adaptive_tail = float(adaptive.get("tail_prompt_tokens", 0))
        fixed_tail = float(fixed.get("tail_prompt_tokens", 0))
        paired.append(
            {
                "item_id": key[0],
                "q_index": key[1],
                "adaptive_elapsed_ms": adaptive_ms,
                "fixed_k1_elapsed_ms": fixed_ms,
                "fixed_over_adaptive_speedup": fixed_ms / adaptive_ms if adaptive_ms else None,
                "adaptive_tail_prompt_tokens": adaptive_tail,
                "fixed_k1_tail_prompt_tokens": fixed_tail,
                "tail_token_reduction": (1.0 - adaptive_tail / fixed_tail if fixed_tail else None),
            }
        )
    return {
        "n": len(paired),
        "rows": paired,
        "median_fixed_over_adaptive_speedup": _median(
            [
                float(row["fixed_over_adaptive_speedup"])
                for row in paired
                if row["fixed_over_adaptive_speedup"] is not None
            ]
        ),
        "median_tail_token_reduction": _median(
            [
                float(row["tail_token_reduction"])
                for row in paired
                if row["tail_token_reduction"] is not None
            ]
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--adaptive-session-jsonl",
        type=Path,
        default=Path(
            "research/experiments/2026/artifacts/phase1_55F_q3_post_q2_state/session_k1_n7.jsonl"
        ),
    )
    parser.add_argument(
        "--fixed-k1-session-jsonl",
        type=Path,
        default=Path(
            "research/experiments/2026/artifacts/"
            "phase1_55D_selective_reprefill_v2/session_k1_n7.jsonl"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "research/experiments/2026/artifacts/phase1_55F_stage_timing/stage_timing_summary.json"
        ),
    )
    args = parser.parse_args()

    adaptive_rows = _load_jsonl(args.adaptive_session_jsonl)
    fixed_rows = _load_jsonl(args.fixed_k1_session_jsonl)
    adaptive = _summarize_policy("adaptive_q3_post_q2", adaptive_rows)
    fixed = _summarize_policy("fixed_k1", fixed_rows)
    paired_q3 = _paired_q3_attribution(adaptive_rows, fixed_rows)
    adaptive_q3 = adaptive["q_index"].get("q3", {})
    fixed_q3 = fixed["q_index"].get("q3", {})
    adaptive_q3_ms = adaptive_q3.get("median_elapsed_ms")
    fixed_q3_ms = fixed_q3.get("median_elapsed_ms")
    adaptive_q3_tail = adaptive_q3.get("median_tail_prompt_tokens")
    fixed_q3_tail = fixed_q3.get("median_tail_prompt_tokens")
    payload = {
        "phase": "1.55F-stage-timing",
        "adaptive_session_jsonl": args.adaptive_session_jsonl.as_posix(),
        "fixed_k1_session_jsonl": args.fixed_k1_session_jsonl.as_posix(),
        "adaptive": adaptive,
        "fixed_k1": fixed,
        "paired_q3": paired_q3,
        "q3_adaptive_over_fixed_elapsed_ratio": (
            adaptive_q3_ms / fixed_q3_ms
            if adaptive_q3_ms is not None and fixed_q3_ms not in (None, 0)
            else None
        ),
        "q3_fixed_over_adaptive_speedup": (
            fixed_q3_ms / adaptive_q3_ms
            if fixed_q3_ms is not None and adaptive_q3_ms not in (None, 0)
            else None
        ),
        "q3_tail_token_reduction": (
            1.0 - (adaptive_q3_tail / fixed_q3_tail)
            if adaptive_q3_tail is not None and fixed_q3_tail not in (None, 0)
            else None
        ),
        "pass_mechanism": bool(
            fixed_q3_ms is not None
            and adaptive_q3_ms not in (None, 0)
            and fixed_q3_ms / adaptive_q3_ms >= 3.0
        ),
        "pass_tail_work": bool(
            adaptive_q3_tail is not None
            and fixed_q3_tail is not None
            and adaptive_q3_tail < fixed_q3_tail
        ),
        "q3_speedup_threshold": 3.0,
        "mechanism_claim": (
            "Adaptive Q3 speedup is attributed to reusing the post-Q2 repaired "
            "cache and reducing Q3 tail prompt tokens relative to fixed K=1. "
            "This is a timing attribution from existing artifacts, not a new "
            "accuracy experiment."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"[1.55F-stage-timing] wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
