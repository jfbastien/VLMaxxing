#!/usr/bin/env python3
"""Simulate speculative admission from already-paired Gemma artifacts.

This is a CPU-only policy audit. It does not run a model. The simulated policy
first tries the fast admission-on row. If the configured abort predicate fires
on that fast row, the policy rolls back to the safe/no-admission row.

Two cost assumptions are reported:

* with_vision_cache: the rollback reuses encoder features and pays only the
  safe LM prefill plus safe decode/parse tail.
* without_vision_cache: the rollback pays the safe vision stage again.

First-token predicates such as non-letter and first-token margin are charged
only through the fast vision + LM prefill before rollback. Final-output
predicates such as parse failure are charged through the full fast path before
rollback.
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
    _adjusted_composed_ms,
    _adjusted_dense_ms,
    _bootstrap_policy_ci,
    _composed_prefill_ms,
    _dense_prefill_ms,
    _empty_group_summary,
    _finalize_summary,
    _finite_float,
    _index_rows,
    _read_jsonl,
    _source_summary,
    _transition,
    _validate_pairing,
)

LETTERS = frozenset({"A", "B", "C", "D"})
AbortRule = Literal[
    "parse_failure",
    "non_letter",
    "vocab_margin_lt",
    "candidate_margin_lt",
    "parse_failure_or_vocab_margin_lt",
    "non_letter_or_vocab_margin_lt",
]
AbortStage = Literal["first_token", "post_generation"]


def _positive_stage(row: dict[str, Any], field: str) -> float:
    value = _finite_float(row, field)
    if value <= 0.0:
        item = row.get("item_id", "<missing item_id>")
        raise ValueError(f"{item}: {field} must be positive")
    return value


def _stage_tail_ms(row: dict[str, Any], *, prefix: str, total_ms: float) -> float:
    vision_ms = _positive_stage(row, f"{prefix}_vision_ms")
    if prefix == "dense":
        prefill_ms = _dense_prefill_ms(row)
    elif prefix == "composed":
        prefill_ms = _composed_prefill_ms(row)
    else:
        raise ValueError(f"unsupported timing prefix: {prefix}")
    tail_ms = total_ms - vision_ms - prefill_ms
    if tail_ms < 0.0:
        item = row.get("item_id", "<missing item_id>")
        raise ValueError(f"{item}: {prefix} vision+prefill exceeds adjusted e2e")
    return tail_ms


def _first_token_text(row: dict[str, Any]) -> str:
    value = row.get("composed_first_generated_token_text")
    if not isinstance(value, str):
        item = row.get("item_id", "<missing item_id>")
        raise ValueError(f"{item}: missing composed_first_generated_token_text")
    return value.strip()


def _is_letter_token(row: dict[str, Any]) -> bool:
    return _first_token_text(row).upper() in LETTERS


def _margin(row: dict[str, Any], field: str) -> float:
    value = _finite_float(row, field)
    if value < 0.0:
        item = row.get("item_id", "<missing item_id>")
        raise ValueError(f"{item}: {field} must be non-negative")
    return value


def _confidence_capture_ms(row: dict[str, Any]) -> float:
    value = _finite_float(row, "composed_first_generated_confidence_capture_ms")
    if value < 0.0:
        item = row.get("item_id", "<missing item_id>")
        raise ValueError(
            f"{item}: composed_first_generated_confidence_capture_ms must be non-negative"
        )
    return value


def _rule_needs_margin(abort_rule: AbortRule) -> bool:
    return "margin" in abort_rule


def _abort_decision(
    row: dict[str, Any],
    *,
    abort_rule: AbortRule,
    margin_threshold: float,
) -> tuple[bool, AbortStage | None]:
    parse_failure = bool(row["composed_parse_failure"])
    if abort_rule == "parse_failure":
        return parse_failure, "post_generation" if parse_failure else None
    if abort_rule == "non_letter":
        aborted = not _is_letter_token(row)
        return aborted, "first_token" if aborted else None
    if abort_rule == "vocab_margin_lt":
        aborted = _margin(row, "composed_first_generated_top2_margin") < margin_threshold
        return aborted, "first_token" if aborted else None
    if abort_rule == "candidate_margin_lt":
        aborted = _margin(row, "composed_first_generated_candidate_top2_margin") < margin_threshold
        return aborted, "first_token" if aborted else None
    if abort_rule == "parse_failure_or_vocab_margin_lt":
        margin_abort = _margin(row, "composed_first_generated_top2_margin") < margin_threshold
        if margin_abort:
            return True, "first_token"
        return parse_failure, "post_generation" if parse_failure else None
    if abort_rule == "non_letter_or_vocab_margin_lt":
        aborted = (not _is_letter_token(row)) or (
            _margin(row, "composed_first_generated_top2_margin") < margin_threshold
        )
        return aborted, "first_token" if aborted else None
    raise ValueError(f"unsupported abort rule: {abort_rule}")


def _add_to_summary(summary: dict[str, Any], *, item: dict[str, Any], cost_mode: str) -> None:
    source = str(item["source"])
    transition = str(item["correctness_transition"])
    summary["n"] += 1
    summary["dense_correct"] += int(bool(item["dense_correct"]))
    summary["policy_correct"] += int(bool(item["policy_correct"]))
    summary["choice_changed_count"] += int(item["dense_choice"] != item["policy_choice"])
    summary["dense_total_ms"] += float(item["dense_ms"])
    summary["policy_total_ms"] += float(item[f"policy_ms_{cost_mode}"])
    summary["dense_prefill_total_ms"] += float(item["dense_prefill_ms"])
    summary["policy_prefill_total_ms"] += float(item[f"policy_prefill_ms_{cost_mode}"])
    summary["source_counts"][source] += 1
    summary["failure_taxonomy"][transition] += 1


def _finalize_spec_summary(summary: dict[str, Any], *, abort_count: int) -> dict[str, Any]:
    finalized = _finalize_summary(summary)
    n = int(finalized["n"])
    finalized["abort_count"] = abort_count
    finalized["abort_rate"] = abort_count / n if n else None
    return finalized


def _ci_for_mode(
    items: list[dict[str, Any]],
    *,
    cost_mode: str,
    n_bootstrap: int,
    seed: int,
) -> dict[str, Any]:
    bootstrap_rows = []
    for item in items:
        bootstrap_rows.append(
            {
                "dense_correct": item["dense_correct"],
                "policy_correct": item["policy_correct"],
                "dense_ms": item["dense_ms"],
                "policy_ms": item[f"policy_ms_{cost_mode}"],
                "dense_prefill_ms": item["dense_prefill_ms"],
                "policy_prefill_ms": item[f"policy_prefill_ms_{cost_mode}"],
            }
        )
    return _bootstrap_policy_ci(bootstrap_rows, n_bootstrap=n_bootstrap, seed=seed)


def _summarize_by_mode(
    items: list[dict[str, Any]],
    *,
    cost_mode: str,
    n_bootstrap: int,
    seed: int,
) -> dict[str, Any]:
    overall = _empty_group_summary()
    by_group = defaultdict(_empty_group_summary)
    abort_count = 0
    abort_by_group: Counter[str] = Counter()
    abort_stage_counts: Counter[str] = Counter()
    fast_transition_by_abort: dict[str, Counter[str]] = defaultdict(Counter)
    for item in items:
        group = str(item["group"])
        aborted = bool(item["aborted"])
        abort_count += int(aborted)
        abort_by_group[group] += int(aborted)
        if aborted:
            abort_stage_counts[str(item["abort_stage"])] += 1
        fast_transition_by_abort["aborted" if aborted else "kept"][
            str(item["fast_correctness_transition"])
        ] += 1
        _add_to_summary(overall, item=item, cost_mode=cost_mode)
        _add_to_summary(by_group[group], item=item, cost_mode=cost_mode)

    fast_harmed = [item for item in items if item["fast_correctness_transition"] == "harmed"]
    aborted_harmed = [item for item in fast_harmed if item["aborted"]]
    aborted_items = [item for item in items if item["aborted"]]
    return {
        "summary": _finalize_spec_summary(overall, abort_count=abort_count),
        "bootstrap_ci": _ci_for_mode(
            items,
            cost_mode=cost_mode,
            n_bootstrap=n_bootstrap,
            seed=seed,
        ),
        "by_group": {
            group: _finalize_spec_summary(summary, abort_count=abort_by_group[group])
            for group, summary in sorted(by_group.items())
        },
        "abort_audit": {
            "fast_harmed_count": len(fast_harmed),
            "aborted_harmed_count": len(aborted_harmed),
            "abort_count": len(aborted_items),
            "abort_stage_counts": dict(sorted(abort_stage_counts.items())),
            "harm_recall": (len(aborted_harmed) / len(fast_harmed)) if fast_harmed else None,
            "abort_precision_for_harm": (
                len(aborted_harmed) / len(aborted_items) if aborted_items else None
            ),
            "fast_transition_by_abort": {
                key: dict(sorted(counter.items()))
                for key, counter in sorted(fast_transition_by_abort.items())
            },
        },
    }


def _simulate_speculative(
    safe_rows: dict[str, dict[str, Any]],
    fast_rows: dict[str, dict[str, Any]],
    *,
    abort_rule: AbortRule,
    margin_threshold: float,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for key in sorted(safe_rows):
        safe = safe_rows[key]
        fast = fast_rows[key]
        aborted, abort_stage = _abort_decision(
            fast,
            abort_rule=abort_rule,
            margin_threshold=margin_threshold,
        )
        chosen = safe if aborted else fast
        source = "safe_rollback" if aborted else "fast_kept"

        dense_correct = bool(safe["dense_correct"])
        policy_correct = bool(chosen["composed_correct"])
        dense_choice = safe.get("dense_choice")
        policy_choice = chosen.get("composed_choice")
        fast_correct = bool(fast["composed_correct"])
        dense_ms = _adjusted_dense_ms(safe)
        dense_prefill_ms = _dense_prefill_ms(safe)
        fast_ms = _adjusted_composed_ms(fast)
        fast_vision_ms = _positive_stage(fast, "composed_vision_ms")
        fast_prefill_ms = _composed_prefill_ms(fast)
        fast_decision_ms = _confidence_capture_ms(fast) if _rule_needs_margin(abort_rule) else 0.0
        _stage_tail_ms(fast, prefix="composed", total_ms=fast_ms)

        safe_ms = _adjusted_composed_ms(safe)
        safe_vision_ms = _positive_stage(safe, "composed_vision_ms")
        safe_prefill_ms = _composed_prefill_ms(safe)
        safe_tail_ms = _stage_tail_ms(safe, prefix="composed", total_ms=safe_ms)

        if aborted and abort_stage == "first_token":
            policy_ms_with_vision_cache = (
                fast_vision_ms + fast_prefill_ms + fast_decision_ms + safe_prefill_ms + safe_tail_ms
            )
            policy_ms_without_vision_cache = (
                fast_vision_ms
                + fast_prefill_ms
                + fast_decision_ms
                + safe_vision_ms
                + safe_prefill_ms
                + safe_tail_ms
            )
            policy_prefill_ms = fast_prefill_ms + safe_prefill_ms
            policy_vision_ms_with_cache = fast_vision_ms
            policy_vision_ms_without_cache = fast_vision_ms + safe_vision_ms
        elif aborted and abort_stage == "post_generation":
            policy_ms_with_vision_cache = (
                fast_ms + fast_decision_ms + safe_prefill_ms + safe_tail_ms
            )
            policy_ms_without_vision_cache = (
                fast_ms + fast_decision_ms + safe_vision_ms + safe_prefill_ms + safe_tail_ms
            )
            policy_prefill_ms = fast_prefill_ms + safe_prefill_ms
            policy_vision_ms_with_cache = fast_vision_ms
            policy_vision_ms_without_cache = fast_vision_ms + safe_vision_ms
        else:
            policy_ms_with_vision_cache = fast_ms + fast_decision_ms
            policy_ms_without_vision_cache = fast_ms + fast_decision_ms
            policy_prefill_ms = fast_prefill_ms
            policy_vision_ms_with_cache = fast_vision_ms
            policy_vision_ms_without_cache = fast_vision_ms

        items.append(
            {
                "item_id": key,
                "benchmark": safe["benchmark"],
                "group": str(safe["group"]),
                "source": source,
                "aborted": aborted,
                "abort_stage": abort_stage,
                "abort_rule": abort_rule,
                "dense_correct": dense_correct,
                "policy_correct": policy_correct,
                "fast_correct": fast_correct,
                "dense_choice": dense_choice,
                "policy_choice": policy_choice,
                "fast_choice": fast.get("composed_choice"),
                "correctness_transition": _transition(dense_correct, policy_correct),
                "fast_correctness_transition": _transition(dense_correct, fast_correct),
                "dense_ms": dense_ms,
                "policy_ms_with_vision_cache": policy_ms_with_vision_cache,
                "policy_ms_without_vision_cache": policy_ms_without_vision_cache,
                "dense_prefill_ms": dense_prefill_ms,
                "policy_prefill_ms_with_vision_cache": policy_prefill_ms,
                "policy_prefill_ms_without_vision_cache": policy_prefill_ms,
                "fast_prefill_ms": fast_prefill_ms,
                "fast_decision_ms": fast_decision_ms,
                "safe_prefill_ms": safe_prefill_ms,
                "fast_vision_ms": fast_vision_ms,
                "safe_vision_ms": safe_vision_ms,
                "policy_vision_ms_with_vision_cache": policy_vision_ms_with_cache,
                "policy_vision_ms_without_vision_cache": policy_vision_ms_without_cache,
                "fast_composed_parse_failure": bool(fast["composed_parse_failure"]),
                "fast_composed_first_generated_token_text": fast.get(
                    "composed_first_generated_token_text"
                ),
                "fast_composed_first_generated_top2_margin": fast.get(
                    "composed_first_generated_top2_margin"
                ),
                "fast_composed_first_generated_candidate_top2_margin": fast.get(
                    "composed_first_generated_candidate_top2_margin"
                ),
            }
        )
    return items


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--safe-paired-items", required=True, type=Path)
    parser.add_argument("--fast-paired-items", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--policy-label", default="speculative_admission")
    parser.add_argument(
        "--abort-rule",
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
    parser.add_argument(
        "--margin-threshold",
        type=float,
        default=0.5,
        help="Margin threshold for *_margin_lt abort rules.",
    )
    parser.add_argument(
        "--allow-dense-label-drift",
        action="store_true",
        help="Allow safe/fast dense-label disagreement and record it.",
    )
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
    if args.margin_threshold < 0.0 or not math.isfinite(float(args.margin_threshold)):
        raise ValueError(
            f"--margin-threshold must be finite and non-negative, got {args.margin_threshold}"
        )

    safe_rows = _index_rows(_read_jsonl(args.safe_paired_items), label="safe-paired-items")
    fast_rows = _index_rows(_read_jsonl(args.fast_paired_items), label="fast-paired-items")
    audit = _validate_pairing(
        safe_rows,
        fast_rows,
        allow_dense_label_drift=args.allow_dense_label_drift,
    )
    dense_label_mismatch_count = int(audit["dense_label_mismatch_count"])
    accuracy_reference = {
        "dense_reference_source": "safe_paired_items",
        "dense_label_mismatch_count": dense_label_mismatch_count,
        "accuracy_delta_interpretation": (
            "exploratory_only_dense_label_drift"
            if dense_label_mismatch_count
            else "paired_same_dense_reference"
        ),
    }
    items = _simulate_speculative(
        safe_rows,
        fast_rows,
        abort_rule=args.abort_rule,
        margin_threshold=float(args.margin_threshold),
    )
    payload = {
        "schema": "gemma_speculative_admission_v1",
        "analysis_role": "exploratory_offline_speculative_admission_simulation",
        "assumptions": {
            "model_not_run": True,
            "abort_stage_model": (
                "first-token predicates abort after fast vision+prefill; final-output "
                "parse_failure aborts after the full fast path"
            ),
            "with_vision_cache": (
                "rollback reuses encoder features and pays safe LM prefill plus safe decode tail"
            ),
            "without_vision_cache": "rollback pays safe vision stage again",
        },
        "dense_reference_source": "safe_paired_items",
        "accuracy_reference": accuracy_reference,
        "policy_label": args.policy_label,
        "abort_rule": args.abort_rule,
        "margin_threshold": float(args.margin_threshold),
        "safe_source_path": str(args.safe_paired_items),
        "fast_source_path": str(args.fast_paired_items),
        "pairing_audit": audit,
        "with_vision_cache": _summarize_by_mode(
            items,
            cost_mode="with_vision_cache",
            n_bootstrap=args.n_bootstrap,
            seed=args.bootstrap_seed,
        ),
        "without_vision_cache": _summarize_by_mode(
            items,
            cost_mode="without_vision_cache",
            n_bootstrap=args.n_bootstrap,
            seed=args.bootstrap_seed,
        ),
        "source_baselines": {
            "safe_all_items": _source_summary(safe_rows),
            "fast_all_items": _source_summary(fast_rows),
        },
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
