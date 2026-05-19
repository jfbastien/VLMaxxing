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
import math
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
    _optional_finite_float,
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


def _optional_nonnegative_int(row: dict[str, Any], *fields: str) -> int | None:
    for field in fields:
        value = row.get(field)
        if value is None:
            continue
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            item = row.get("item_id", "<missing item_id>")
            raise ValueError(f"{item}: {field} must be a non-negative integer")
        return value
    return None


def _optional_positive_float(row: dict[str, Any], *fields: str) -> float | None:
    for field in fields:
        value = row.get(field)
        if value is None:
            continue
        if not isinstance(value, int | float):
            item = row.get("item_id", "<missing item_id>")
            raise ValueError(f"{item}: {field} must be numeric")
        result = float(value)
        if not math.isfinite(result) or result <= 0.0:
            item = row.get("item_id", "<missing item_id>")
            raise ValueError(f"{item}: {field} must be finite and positive")
        return result
    return None


def _optional_adjusted_text_generation_ms(
    row: dict[str, Any],
    *,
    capture_field: str,
    timing_fields: tuple[str, ...],
) -> float | None:
    raw_ms = _optional_positive_float(row, *timing_fields)
    if raw_ms is None:
        return None
    adjusted_ms = raw_ms - _optional_finite_float(row, capture_field)
    if adjusted_ms <= 0.0:
        item = row.get("item_id", "<missing item_id>")
        raise ValueError(f"{item}: adjusted {timing_fields[0]} must be positive")
    return adjusted_ms


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
    dense_video_decode_ms = _optional_positive_float(row, "dense_video_decode_ms")
    policy_video_decode_ms = _optional_positive_float(
        row,
        "composed_video_decode_ms",
        "pruned_video_decode_ms",
    )
    dense_text_generation_ms = _optional_adjusted_text_generation_ms(
        row,
        capture_field="dense_first_generated_confidence_capture_ms",
        timing_fields=("dense_text_generation_ms",),
    )
    policy_text_generation_ms = _optional_adjusted_text_generation_ms(
        row,
        capture_field="composed_first_generated_confidence_capture_ms",
        timing_fields=("composed_text_generation_ms", "pruned_text_generation_ms"),
    )
    if (dense_video_decode_ms is None) != (policy_video_decode_ms is None):
        raise ValueError(f"{key}: dense/policy video decode fields must both be present or absent")
    if (dense_text_generation_ms is None) != (policy_text_generation_ms is None):
        raise ValueError(
            f"{key}: dense/policy text generation fields must both be present or absent"
        )
    dense_generation_tokens = _optional_nonnegative_int(row, "dense_generation_tokens")
    policy_generation_tokens = _optional_nonnegative_int(
        row,
        "composed_generation_tokens",
        "pruned_generation_tokens",
    )
    if (dense_generation_tokens is None) != (policy_generation_tokens is None):
        raise ValueError(
            f"{key}: dense/policy generation token fields must both be present or absent"
        )
    if dense_prefill_ms + dense_vision_ms > dense_ms:
        raise ValueError(f"{key}: dense prefill+vision exceeds adjusted dense e2e")
    if composed_prefill_ms + composed_vision_ms > composed_ms:
        raise ValueError(f"{key}: composed prefill+vision exceeds adjusted composed e2e")
    dense_tail_ms = dense_ms - dense_prefill_ms - dense_vision_ms
    policy_tail_ms = composed_ms - composed_prefill_ms - composed_vision_ms
    if (
        dense_video_decode_ms is not None
        and dense_prefill_ms + dense_vision_ms + dense_video_decode_ms > dense_ms
    ):
        raise ValueError(f"{key}: dense prefill+vision+video_decode exceeds adjusted dense e2e")
    if (
        policy_video_decode_ms is not None
        and composed_prefill_ms + composed_vision_ms + policy_video_decode_ms > composed_ms
    ):
        raise ValueError(
            f"{key}: composed prefill+vision+video_decode exceeds adjusted composed e2e"
        )
    if (
        dense_text_generation_ms is not None
        and dense_prefill_ms + dense_vision_ms + dense_text_generation_ms > dense_ms
    ):
        raise ValueError(f"{key}: dense prefill+vision+text_generation exceeds adjusted dense e2e")
    if (
        policy_text_generation_ms is not None
        and composed_prefill_ms + composed_vision_ms + policy_text_generation_ms > composed_ms
    ):
        raise ValueError(
            f"{key}: composed prefill+vision+text_generation exceeds adjusted composed e2e"
        )
    if (
        dense_video_decode_ms is not None
        and dense_text_generation_ms is not None
        and dense_video_decode_ms + dense_text_generation_ms > dense_tail_ms
    ):
        raise ValueError(f"{key}: dense video_decode+text_generation exceeds adjusted dense tail")
    if (
        policy_video_decode_ms is not None
        and policy_text_generation_ms is not None
        and policy_video_decode_ms + policy_text_generation_ms > policy_tail_ms
    ):
        raise ValueError(
            f"{key}: composed video_decode+text_generation exceeds adjusted composed tail"
        )
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
        "dense_tail_ms": dense_tail_ms,
        "policy_tail_ms": policy_tail_ms,
        "dense_video_decode_ms": dense_video_decode_ms,
        "policy_video_decode_ms": policy_video_decode_ms,
        "dense_text_generation_ms": dense_text_generation_ms,
        "policy_text_generation_ms": policy_text_generation_ms,
        "dense_generation_tokens": dense_generation_tokens,
        "policy_generation_tokens": policy_generation_tokens,
    }


def _mean(values: list[float]) -> float | None:
    return (sum(values) / len(values)) if values else None


def _ratio(num: float | None, denom: float | None) -> float | None:
    if num is None or denom is None or denom == 0.0:
        return None
    return num / denom


def _sum_present(items: list[dict[str, Any]], field: str) -> float | None:
    values = [float(item[field]) for item in items if item[field] is not None]
    if len(values) != len(items):
        return None
    return sum(values)


def _transition_stage_costs(items: list[dict[str, Any]]) -> dict[str, Any]:
    by_transition: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        by_transition.setdefault(str(item["correctness_transition"]), []).append(item)

    summaries: dict[str, dict[str, Any]] = {}
    for transition, rows in sorted(by_transition.items()):
        generation_token_pairs = [
            (int(row["dense_generation_tokens"]), int(row["policy_generation_tokens"]))
            for row in rows
            if row["dense_generation_tokens"] is not None
            and row["policy_generation_tokens"] is not None
        ]
        dense_video_decode = [
            float(row["dense_video_decode_ms"])
            for row in rows
            if row["dense_video_decode_ms"] is not None
        ]
        policy_video_decode = [
            float(row["policy_video_decode_ms"])
            for row in rows
            if row["policy_video_decode_ms"] is not None
        ]
        dense_text_generation = [
            float(row["dense_text_generation_ms"])
            for row in rows
            if row["dense_text_generation_ms"] is not None
        ]
        policy_text_generation = [
            float(row["policy_text_generation_ms"])
            for row in rows
            if row["policy_text_generation_ms"] is not None
        ]
        summaries[transition] = {
            "n": len(rows),
            "mean_dense_e2e_ms": _mean([float(row["dense_ms"]) for row in rows]),
            "mean_policy_e2e_ms": _mean([float(row["policy_ms"]) for row in rows]),
            "mean_dense_prefill_ms": _mean([float(row["dense_prefill_ms"]) for row in rows]),
            "mean_policy_prefill_ms": _mean([float(row["policy_prefill_ms"]) for row in rows]),
            "mean_dense_vision_ms": _mean([float(row["dense_vision_ms"]) for row in rows]),
            "mean_policy_vision_ms": _mean([float(row["policy_vision_ms"]) for row in rows]),
            "mean_dense_tail_ms": _mean([float(row["dense_tail_ms"]) for row in rows]),
            "mean_policy_tail_ms": _mean([float(row["policy_tail_ms"]) for row in rows]),
            "mean_dense_video_decode_ms": _mean(dense_video_decode),
            "mean_policy_video_decode_ms": _mean(policy_video_decode),
            "mean_dense_text_generation_ms": _mean(dense_text_generation),
            "mean_policy_text_generation_ms": _mean(policy_text_generation),
            "mean_dense_generation_tokens": _mean(
                [float(dense_tokens) for dense_tokens, _ in generation_token_pairs]
            ),
            "mean_policy_generation_tokens": _mean(
                [float(policy_tokens) for _, policy_tokens in generation_token_pairs]
            ),
            "generation_tokens_available_count": len(generation_token_pairs),
        }

    harmed = summaries.get("harmed")
    preserved = summaries.get("preserved_correct")
    comparison: dict[str, Any] | None = None
    if harmed and preserved:
        comparison = {
            "harmed_n": harmed["n"],
            "preserved_correct_n": preserved["n"],
            "policy_e2e_ratio_harmed_over_preserved_correct": _ratio(
                harmed["mean_policy_e2e_ms"],
                preserved["mean_policy_e2e_ms"],
            ),
            "policy_tail_ratio_harmed_over_preserved_correct": _ratio(
                harmed["mean_policy_tail_ms"],
                preserved["mean_policy_tail_ms"],
            ),
            "policy_text_generation_ratio_harmed_over_preserved_correct": _ratio(
                harmed["mean_policy_text_generation_ms"],
                preserved["mean_policy_text_generation_ms"],
            ),
            "policy_generation_tokens_ratio_harmed_over_preserved_correct": _ratio(
                harmed["mean_policy_generation_tokens"],
                preserved["mean_policy_generation_tokens"],
            ),
        }
    return {
        "by_transition": summaries,
        "harm_vs_preserved_correct": comparison,
    }


def _optional_tail_audit(
    *,
    items: list[dict[str, Any]],
    dense_ms: float,
    dense_prefill_ms: float,
    composed_prefill_ms: float,
    dense_vision_ms: float,
    composed_vision_ms: float,
) -> dict[str, Any] | None:
    dense_video_decode_ms = _sum_present(items, "dense_video_decode_ms")
    composed_video_decode_ms = _sum_present(items, "policy_video_decode_ms")
    dense_text_generation_ms = _sum_present(items, "dense_text_generation_ms")
    composed_text_generation_ms = _sum_present(items, "policy_text_generation_ms")
    if (
        dense_video_decode_ms is None
        or composed_video_decode_ms is None
        or dense_text_generation_ms is None
        or composed_text_generation_ms is None
    ):
        return None
    prefill_vision_ceiling_denominator = (
        dense_ms - dense_prefill_ms - dense_vision_ms + composed_prefill_ms + composed_vision_ms
    )
    prefill_vision_text_denominator = (
        dense_ms
        - dense_prefill_ms
        - dense_vision_ms
        - dense_text_generation_ms
        + composed_prefill_ms
        + composed_vision_ms
        + composed_text_generation_ms
    )
    if prefill_vision_ceiling_denominator <= 0.0 or prefill_vision_text_denominator <= 0.0:
        raise ValueError("tail audit ceiling denominator must be positive")
    return {
        "dense_video_decode_total_ms": dense_video_decode_ms,
        "composed_video_decode_total_ms": composed_video_decode_ms,
        "video_decode_inflation_composed_over_dense": (
            composed_video_decode_ms / dense_video_decode_ms
        ),
        "video_decode_delta_share_of_dense_e2e": (
            (composed_video_decode_ms - dense_video_decode_ms) / dense_ms
        ),
        "dense_text_generation_total_ms": dense_text_generation_ms,
        "composed_text_generation_total_ms": composed_text_generation_ms,
        "text_generation_inflation_composed_over_dense": (
            composed_text_generation_ms / dense_text_generation_ms
        ),
        "text_generation_delta_share_of_dense_e2e": (
            (composed_text_generation_ms - dense_text_generation_ms) / dense_ms
        ),
        "prefill_plus_vision_plus_text_generation_e2e_ceiling_speedup": (
            dense_ms / prefill_vision_text_denominator
        ),
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
    prefill_vision_ceiling = dense_ms / (
        dense_ms - dense_prefill_ms - dense_vision_ms + composed_prefill_ms + composed_vision_ms
    )
    tail_audit = _optional_tail_audit(
        items=items,
        dense_ms=dense_ms,
        dense_prefill_ms=dense_prefill_ms,
        composed_prefill_ms=composed_prefill_ms,
        dense_vision_ms=dense_vision_ms,
        composed_vision_ms=composed_vision_ms,
    )
    if tail_audit is not None:
        tail_audit["prefill_plus_vision_relative_error"] = (
            (dense_ms / composed_ms) - prefill_vision_ceiling
        ) / prefill_vision_ceiling
        text_ceiling = float(
            tail_audit["prefill_plus_vision_plus_text_generation_e2e_ceiling_speedup"]
        )
        tail_audit["prefill_plus_vision_plus_text_generation_relative_error"] = (
            (dense_ms / composed_ms) - text_ceiling
        ) / text_ceiling
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
        "prefill_plus_vision_e2e_ceiling_speedup": prefill_vision_ceiling,
        "tail_audit": tail_audit,
        "transition_stage_costs": _transition_stage_costs(items),
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
