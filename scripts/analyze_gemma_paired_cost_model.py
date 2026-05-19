#!/usr/bin/env python3
"""Summarize stage-level cost model metrics from paired Gemma artifacts.

This is a CPU-only audit. It reads paired rows emitted by the Gemma full
composition analyzer and reports ratio-of-sums speedups, stage shares, and
paired bootstrap CIs. It does not run a model and it does not decide fidelity
by itself; the accuracy and harm fields are reported so the cost table cannot
be mistaken for a quality win table.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.analyze_gemma_admission_policy_simulation import (  # noqa: E402
    _adjusted_composed_ms,
    _adjusted_dense_ms,
    _bootstrap_policy_ci,
    _composed_prefill_ms,
    _dense_prefill_ms,
    _finite_float,
    _index_rows,
    _read_jsonl,
    _row_key,
    _transition,
)


def _positive_stage(row: dict[str, Any], field: str) -> float:
    value = _finite_float(row, field)
    if value <= 0.0:
        item = row.get("item_id", "<missing item_id>")
        raise ValueError(f"{item}: {field} must be positive")
    return value


def _choice_changed(row: dict[str, Any]) -> bool:
    return row.get("dense_choice") != row.get("composed_choice")


def _policy_item(row: dict[str, Any]) -> dict[str, Any]:
    key = _row_key(row)
    dense_correct = bool(row["dense_correct"])
    composed_correct = bool(row["composed_correct"])
    dense_ms = _adjusted_dense_ms(row)
    composed_ms = _adjusted_composed_ms(row)
    dense_prefill_ms = _dense_prefill_ms(row)
    composed_prefill_ms = _composed_prefill_ms(row)
    dense_vision_ms = _positive_stage(row, "dense_vision_ms")
    composed_vision_ms = _positive_stage(row, "composed_vision_ms")
    if dense_prefill_ms + dense_vision_ms > dense_ms:
        raise ValueError(f"{key}: dense prefill+vision exceeds adjusted dense e2e")
    if composed_prefill_ms + composed_vision_ms > composed_ms:
        raise ValueError(f"{key}: composed prefill+vision exceeds adjusted composed e2e")
    return {
        "item_id": key,
        "benchmark": row.get("benchmark"),
        "group": row.get("group"),
        "dense_correct": dense_correct,
        "policy_correct": composed_correct,
        "dense_choice": row.get("dense_choice"),
        "policy_choice": row.get("composed_choice"),
        "correctness_transition": _transition(dense_correct, composed_correct),
        "choice_changed": _choice_changed(row),
        "dense_ms": dense_ms,
        "policy_ms": composed_ms,
        "dense_prefill_ms": dense_prefill_ms,
        "policy_prefill_ms": composed_prefill_ms,
        "dense_vision_ms": dense_vision_ms,
        "policy_vision_ms": composed_vision_ms,
    }


def _cost_model_bootstrap_ci(
    items: list[dict[str, Any]],
    *,
    n_bootstrap: int,
    seed: int,
) -> dict[str, Any]:
    ci = _bootstrap_policy_ci(items, n_bootstrap=n_bootstrap, seed=seed)
    ci["accuracy_delta_composed_minus_dense_ci95"] = ci.pop(
        "accuracy_delta_policy_minus_dense_ci95"
    )
    ci["e2e_speedup_dense_over_composed_ci95"] = ci.pop("e2e_speedup_dense_over_policy_ci95")
    ci["prefill_speedup_dense_over_composed_ci95"] = ci.pop(
        "prefill_speedup_dense_over_policy_ci95"
    )
    return ci


def _summarize(items: list[dict[str, Any]]) -> dict[str, Any]:
    if not items:
        raise ValueError("no paired items")
    n = len(items)
    dense_correct = sum(int(bool(row["dense_correct"])) for row in items)
    composed_correct = sum(int(bool(row["policy_correct"])) for row in items)
    dense_ms = sum(float(row["dense_ms"]) for row in items)
    composed_ms = sum(float(row["policy_ms"]) for row in items)
    dense_prefill_ms = sum(float(row["dense_prefill_ms"]) for row in items)
    composed_prefill_ms = sum(float(row["policy_prefill_ms"]) for row in items)
    dense_vision_ms = sum(float(row["dense_vision_ms"]) for row in items)
    composed_vision_ms = sum(float(row["policy_vision_ms"]) for row in items)
    dense_other_ms = dense_ms - dense_prefill_ms - dense_vision_ms
    composed_other_ms = composed_ms - composed_prefill_ms - composed_vision_ms
    if dense_other_ms < 0.0 or composed_other_ms < 0.0:
        raise ValueError("stage totals exceed e2e totals")
    transitions = Counter(str(row["correctness_transition"]) for row in items)
    groups = Counter(str(row["group"]) for row in items)
    return {
        "n": n,
        "groups": dict(sorted(groups.items())),
        "dense_accuracy": dense_correct / n,
        "composed_accuracy": composed_correct / n,
        "accuracy_delta_composed_minus_dense": (composed_correct - dense_correct) / n,
        "choice_agreement": 1.0 - (sum(int(bool(row["choice_changed"])) for row in items) / n),
        "choice_changed_count": sum(int(bool(row["choice_changed"])) for row in items),
        "failure_taxonomy": dict(sorted(transitions.items())),
        "harmed_count": int(transitions.get("harmed", 0)),
        "dense_total_ms": dense_ms,
        "composed_total_ms": composed_ms,
        "e2e_speedup_dense_over_composed": dense_ms / composed_ms,
        "dense_prefill_total_ms": dense_prefill_ms,
        "composed_prefill_total_ms": composed_prefill_ms,
        "prefill_speedup_dense_over_composed": dense_prefill_ms / composed_prefill_ms,
        "dense_vision_total_ms": dense_vision_ms,
        "composed_vision_total_ms": composed_vision_ms,
        "vision_speedup_dense_over_composed": dense_vision_ms / composed_vision_ms,
        "dense_other_total_ms": dense_other_ms,
        "composed_other_total_ms": composed_other_ms,
        "other_speedup_dense_over_composed": (
            dense_other_ms / composed_other_ms if composed_other_ms > 0.0 else None
        ),
        "dense_prefill_share_of_e2e": dense_prefill_ms / dense_ms,
        "dense_vision_share_of_e2e": dense_vision_ms / dense_ms,
        "dense_other_share_of_e2e": dense_other_ms / dense_ms,
        "composed_prefill_share_of_e2e": composed_prefill_ms / composed_ms,
        "composed_vision_share_of_e2e": composed_vision_ms / composed_ms,
        "composed_other_share_of_e2e": composed_other_ms / composed_ms,
        "prefill_only_e2e_ceiling_speedup": dense_ms
        / (dense_ms - dense_prefill_ms + composed_prefill_ms),
        "prefill_plus_vision_e2e_ceiling_speedup": dense_ms
        / (
            dense_ms - dense_prefill_ms - dense_vision_ms + composed_prefill_ms + composed_vision_ms
        ),
        "mean_dense_e2e_ms": dense_ms / n,
        "mean_composed_e2e_ms": composed_ms / n,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paired-items", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--label", required=True)
    parser.add_argument(
        "--n-bootstrap",
        type=int,
        default=2000,
        help="Paired item bootstrap resamples for accuracy and speed CIs.",
    )
    parser.add_argument("--bootstrap-seed", type=int, default=20260519)
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    rows = _index_rows(_read_jsonl(args.paired_items), label="paired-items")
    items: list[dict[str, Any]] = []
    for key in sorted(rows):
        items.append(_policy_item(rows[key]))
    payload = {
        "schema": "gemma_paired_cost_model_v1",
        "analysis_role": "stage_cost_model_audit",
        "label": args.label,
        "source_path": str(args.paired_items),
        "summary": _summarize(items),
        "bootstrap_ci": _cost_model_bootstrap_ci(
            items,
            n_bootstrap=args.n_bootstrap,
            seed=args.bootstrap_seed,
        ),
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
