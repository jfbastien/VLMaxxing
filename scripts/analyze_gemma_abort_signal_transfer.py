#!/usr/bin/env python3
"""Audit whether an output-format abort signal covers harmed rows.

This CPU-only screen uses one paired artifact. It does not simulate a mixed
policy because it has no safe fallback arm. It answers the transfer question:
would an intrinsic abort signal such as composed parse failure have fired on
rows that the composed/fast arm harmed?
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Literal

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.analyze_gemma_admission_policy_simulation import (  # noqa: E402
    _finite_float,
    _index_rows,
    _read_jsonl,
    _transition,
)

LETTERS = frozenset({"A", "B", "C", "D"})
SignalRule = Literal[
    "parse_failure",
    "non_letter",
    "vocab_margin_lt",
    "candidate_margin_lt",
    "parse_failure_or_vocab_margin_lt",
    "non_letter_or_vocab_margin_lt",
]


def _first_token_text(row: dict[str, Any]) -> str:
    value = row.get("composed_first_generated_token_text")
    if not isinstance(value, str):
        item = row.get("item_id", "<missing item_id>")
        raise ValueError(f"{item}: missing composed_first_generated_token_text")
    return value.strip()


def _is_letter(row: dict[str, Any]) -> bool:
    return _first_token_text(row).upper() in LETTERS


def _margin(row: dict[str, Any], field: str) -> float:
    value = _finite_float(row, field)
    if value < 0.0:
        item = row.get("item_id", "<missing item_id>")
        raise ValueError(f"{item}: {field} must be non-negative")
    return value


def _signal(row: dict[str, Any], *, signal_rule: SignalRule, margin_threshold: float) -> bool:
    parse_failure = bool(row["composed_parse_failure"])
    if signal_rule == "parse_failure":
        return parse_failure
    if signal_rule == "non_letter":
        return not _is_letter(row)
    if signal_rule == "vocab_margin_lt":
        return _margin(row, "composed_first_generated_top2_margin") < margin_threshold
    if signal_rule == "candidate_margin_lt":
        return _margin(row, "composed_first_generated_candidate_top2_margin") < margin_threshold
    if signal_rule == "parse_failure_or_vocab_margin_lt":
        return parse_failure or (
            _margin(row, "composed_first_generated_top2_margin") < margin_threshold
        )
    if signal_rule == "non_letter_or_vocab_margin_lt":
        return (not _is_letter(row)) or (
            _margin(row, "composed_first_generated_top2_margin") < margin_threshold
        )
    raise ValueError(f"unsupported signal rule: {signal_rule}")


def _summarize(
    rows: dict[str, dict[str, Any]],
    *,
    signal_rule: SignalRule,
    margin_threshold: float,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    items: list[dict[str, Any]] = []
    signal_by_group: dict[str, Counter[str]] = defaultdict(Counter)
    harm_by_group: dict[str, Counter[str]] = defaultdict(Counter)
    for key in sorted(rows):
        row = rows[key]
        dense_correct = bool(row["dense_correct"])
        composed_correct = bool(row["composed_correct"])
        transition = _transition(dense_correct, composed_correct)
        fired = _signal(row, signal_rule=signal_rule, margin_threshold=margin_threshold)
        group = str(row["group"])
        signal_by_group[group]["signal_fired" if fired else "signal_clear"] += 1
        if transition == "harmed":
            harm_by_group[group]["signal_fired" if fired else "signal_clear"] += 1
        items.append(
            {
                "item_id": key,
                "benchmark": row["benchmark"],
                "group": group,
                "signal_fired": fired,
                "dense_correct": dense_correct,
                "composed_correct": composed_correct,
                "correctness_transition": transition,
                "composed_parse_failure": bool(row["composed_parse_failure"]),
                "composed_first_generated_token_text": row.get(
                    "composed_first_generated_token_text"
                ),
                "composed_first_generated_top2_margin": row.get(
                    "composed_first_generated_top2_margin"
                ),
            }
        )
    harmed = [row for row in items if row["correctness_transition"] == "harmed"]
    signaled = [row for row in items if row["signal_fired"]]
    signaled_harmed = [
        row for row in items if row["signal_fired"] and row["correctness_transition"] == "harmed"
    ]
    summary = {
        "n": len(items),
        "signal_count": len(signaled),
        "signal_rate": len(signaled) / len(items),
        "harmed_count": len(harmed),
        "harmed_signaled_count": len(signaled_harmed),
        "harmed_recall": (len(signaled_harmed) / len(harmed)) if harmed else None,
        "signal_precision_for_harm": (len(signaled_harmed) / len(signaled)) if signaled else None,
        "signal_summary_by_group": {
            group: dict(sorted(counter.items()))
            for group, counter in sorted(signal_by_group.items())
        },
        "harm_coverage_by_group": {
            group: dict(sorted(counter.items())) for group, counter in sorted(harm_by_group.items())
        },
    }
    return summary, items


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paired-items", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--policy-label", default="abort_signal_transfer_screen")
    parser.add_argument(
        "--signal-rule",
        choices=[
            "parse_failure",
            "non_letter",
            "vocab_margin_lt",
            "candidate_margin_lt",
            "parse_failure_or_vocab_margin_lt",
            "non_letter_or_vocab_margin_lt",
        ],
        default="parse_failure",
    )
    parser.add_argument("--margin-threshold", type=float, default=0.5)
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    if args.margin_threshold < 0.0 or not math.isfinite(float(args.margin_threshold)):
        raise ValueError(
            f"--margin-threshold must be finite and non-negative, got {args.margin_threshold}"
        )
    rows = _index_rows(_read_jsonl(args.paired_items), label="paired-items")
    summary, items = _summarize(
        rows,
        signal_rule=args.signal_rule,
        margin_threshold=float(args.margin_threshold),
    )
    payload = {
        "schema": "gemma_abort_signal_transfer_v1",
        "analysis_role": "single_artifact_abort_signal_transfer_screen",
        "policy_label": args.policy_label,
        "signal_rule": args.signal_rule,
        "margin_threshold": float(args.margin_threshold),
        "source_path": str(args.paired_items),
        "summary": summary,
        "items": items,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
