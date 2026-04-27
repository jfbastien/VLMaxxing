#!/usr/bin/env python3
"""Compare 1.30 cache-reuse and cache-invalidated boundary failures.

This is a post-hoc mechanism attribution over landed 1.30AD/1.30AC artifacts.
It does not claim direct tensor-level KV distance. Instead it quantifies whether
the two policies produce the same aggregate loss through the same or different
row-level flips, and ties those flips to measured cache/prefix mechanics.
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
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


def _row_key(row: dict[str, Any]) -> tuple[str, int]:
    return (str(row["item_id"]), int(row["q_index"]))


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _median(values: list[float]) -> float | None:
    return float(statistics.median(values)) if values else None


def _pair_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_q = Counter(int(row["q_index"]) for row in rows)
    choice_drift = {
        _row_key(row)
        for row in rows
        if row.get("cold_choice") is not None
        and row.get("streaming_choice") is not None
        and row["cold_choice"] != row["streaming_choice"]
    }
    correctness_drift = {
        _row_key(row)
        for row in rows
        if bool(row.get("cold_correct")) != bool(row.get("streaming_correct"))
    }
    cold_correct = sum(bool(row.get("cold_correct")) for row in rows)
    streaming_correct = sum(bool(row.get("streaming_correct")) for row in rows)
    follow_rows = [row for row in rows if int(row["q_index"]) > 0]
    return {
        "n": len(rows),
        "n_follow_up": len(follow_rows),
        "q_index_counts": {str(key): value for key, value in sorted(by_q.items())},
        "cold_accuracy": cold_correct / len(rows) if rows else None,
        "streaming_accuracy": streaming_correct / len(rows) if rows else None,
        "accuracy_delta": ((streaming_correct - cold_correct) / len(rows) if rows else None),
        "choice_drift_count": len(choice_drift),
        "correctness_drift_count": len(correctness_drift),
        "any_drift_count": len(choice_drift | correctness_drift),
        "choice_drift_keys": sorted([f"{item_id}#q{q}" for item_id, q in choice_drift]),
        "correctness_drift_keys": sorted([f"{item_id}#q{q}" for item_id, q in correctness_drift]),
        "any_drift_keys": sorted(
            [f"{item_id}#q{q}" for item_id, q in (choice_drift | correctness_drift)]
        ),
        "follow_up_accuracy_delta": (
            (
                sum(bool(row.get("streaming_correct")) for row in follow_rows)
                - sum(bool(row.get("cold_correct")) for row in follow_rows)
            )
            / len(follow_rows)
            if follow_rows
            else None
        ),
    }


def _streaming_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    follow_rows = [row for row in rows if int(row["q_index"]) > 0]
    active = [bool(row.get("vision_pruning_active", False)) for row in follow_rows]
    prefix_coverage = [float(row["prefix_coverage"]) for row in follow_rows]
    image_recomputed = [float(row["image_tokens_recomputed"]) for row in follow_rows]
    image_count = [float(row["image_token_count"]) for row in follow_rows]
    recomputed_fraction = [
        recomputed / count
        for recomputed, count in zip(image_recomputed, image_count, strict=True)
        if count
    ]
    return {
        "n": len(rows),
        "n_follow_up": len(follow_rows),
        "follow_up_vision_pruning_active_fraction": (sum(active) / len(active) if active else None),
        "follow_up_mean_prefix_coverage": _mean(prefix_coverage),
        "follow_up_median_prefix_coverage": _median(prefix_coverage),
        "follow_up_mean_image_recomputed_fraction": _mean(recomputed_fraction),
        "follow_up_median_image_recomputed_fraction": _median(recomputed_fraction),
        "follow_up_refresh_reasons": dict(
            Counter(str(row.get("refresh_reason")) for row in follow_rows)
        ),
    }


def _set_stats(left: set[str], right: set[str]) -> dict[str, Any]:
    union = left | right
    intersection = left & right
    return {
        "left_count": len(left),
        "right_count": len(right),
        "intersection_count": len(intersection),
        "left_only_count": len(left - right),
        "right_only_count": len(right - left),
        "jaccard": len(intersection) / len(union) if union else 1.0,
        "left_only": sorted(left - right),
        "right_only": sorted(right - left),
        "intersection": sorted(intersection),
    }


def _key_text(row: dict[str, Any]) -> str:
    item_id, q_index = _row_key(row)
    return f"{item_id}#q{q_index}"


def _load_margin_by_key(path: Path | None) -> dict[str, float]:
    if path is None or not path.exists():
        return {}
    margins: dict[str, float] = {}
    for row in _load_jsonl(path):
        key = _key_text(row)
        margins.setdefault(key, float(row["dense_answer_margin"]))
    return margins


def _feature_groups(row: dict[str, Any]) -> dict[str, str]:
    return {
        "duration": str(row.get("duration")),
        "split": str(row.get("split")),
        "q_index": f"q{int(row['q_index'])}",
        "cold_correct": str(bool(row.get("cold_correct"))).lower(),
        "duration_x_q_index": f"{row.get('duration')}/q{int(row['q_index'])}",
    }


def _summarize_group(rows: list[dict[str, Any]], margins: dict[str, float]) -> dict[str, Any]:
    n = len(rows)
    if n == 0:
        return {"n": 0}
    any_drift_rows = [
        row
        for row in rows
        if (
            row.get("cold_choice") is not None
            and row.get("streaming_choice") is not None
            and row["cold_choice"] != row["streaming_choice"]
        )
        or bool(row.get("cold_correct")) != bool(row.get("streaming_correct"))
    ]
    choice_drift_rows = [
        row
        for row in rows
        if row.get("cold_choice") is not None
        and row.get("streaming_choice") is not None
        and row["cold_choice"] != row["streaming_choice"]
    ]
    correctness_drift_rows = [
        row for row in rows if bool(row.get("cold_correct")) != bool(row.get("streaming_correct"))
    ]
    cold_correct = sum(bool(row.get("cold_correct")) for row in rows)
    streaming_correct = sum(bool(row.get("streaming_correct")) for row in rows)
    margin_values = [margins[_key_text(row)] for row in rows if _key_text(row) in margins]
    drift_margin_values = [
        margins[_key_text(row)] for row in any_drift_rows if _key_text(row) in margins
    ]
    any_drift_keys = {_key_text(row) for row in any_drift_rows}
    stable_margin_values = [
        margins[_key_text(row)]
        for row in rows
        if _key_text(row) not in any_drift_keys and _key_text(row) in margins
    ]
    return {
        "n": n,
        "any_drift_count": len(any_drift_rows),
        "choice_drift_count": len(choice_drift_rows),
        "correctness_drift_count": len(correctness_drift_rows),
        "any_drift_fraction": len(any_drift_rows) / n,
        "accuracy_delta": (streaming_correct - cold_correct) / n,
        "n_with_margin": len(margin_values),
        "mean_margin_all": _mean(margin_values),
        "mean_margin_drift": _mean(drift_margin_values),
        "mean_margin_stable": _mean(stable_margin_values),
        "median_margin_all": _median(margin_values),
        "median_margin_drift": _median(drift_margin_values),
        "median_margin_stable": _median(stable_margin_values),
    }


def _feature_correlation_summary(
    rows: list[dict[str, Any]], margins: dict[str, float]
) -> dict[str, Any]:
    by_feature: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for row in rows:
        for feature, value in _feature_groups(row).items():
            by_feature.setdefault(feature, {}).setdefault(value, []).append(row)
    summary = {
        feature: {
            value: _summarize_group(group_rows, margins)
            for value, group_rows in sorted(groups.items())
        }
        for feature, groups in sorted(by_feature.items())
    }
    concentrated_groups: list[dict[str, Any]] = []
    for feature, groups in summary.items():
        for value, group in groups.items():
            if int(group["n"]) < 5:
                continue
            concentrated_groups.append(
                {
                    "feature": feature,
                    "value": value,
                    "n": group["n"],
                    "any_drift_fraction": group["any_drift_fraction"],
                    "accuracy_delta": group["accuracy_delta"],
                    "mean_margin_drift": group["mean_margin_drift"],
                    "mean_margin_stable": group["mean_margin_stable"],
                }
            )
    concentrated_groups.sort(
        key=lambda group: (float(group["any_drift_fraction"]), int(group["n"])),
        reverse=True,
    )
    return {
        "groups": summary,
        "top_drift_concentrations_n_ge_5": concentrated_groups[:10],
        "margin_available": bool(margins),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cache-reuse-pairs",
        type=Path,
        default=Path(
            "research/experiments/2026/artifacts/"
            "phase1_30AD_instrumented_w_rerun/paired_queries.jsonl"
        ),
    )
    parser.add_argument(
        "--cache-reuse-streaming",
        type=Path,
        default=Path(
            "research/experiments/2026/artifacts/phase1_30AD_instrumented_w_rerun/"
            "streaming_q0_dense_cache_reuse_followups.jsonl"
        ),
    )
    parser.add_argument(
        "--cache-invalidated-pairs",
        type=Path,
        default=Path(
            "research/experiments/2026/artifacts/"
            "phase1_30AC_cache_invalidated_followups/paired_queries.jsonl"
        ),
    )
    parser.add_argument(
        "--cache-invalidated-streaming",
        type=Path,
        default=Path(
            "research/experiments/2026/artifacts/phase1_30AC_cache_invalidated_followups/"
            "streaming_cache_invalidated_followups.jsonl"
        ),
    )
    parser.add_argument(
        "--logit-margin-jsonl",
        type=Path,
        default=Path(
            "research/experiments/2026/artifacts/"
            "phase1_65_logit_margin_failure_predictor/scored_rows.jsonl"
        ),
        help="Optional 1.65 scored_rows.jsonl for margin-stratified attribution.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "research/experiments/2026/artifacts/"
            "phase1_30AF_cache_boundary_attribution/attribution_summary.json"
        ),
    )
    args = parser.parse_args()

    reuse_pairs = _load_jsonl(args.cache_reuse_pairs)
    invalidated_pairs = _load_jsonl(args.cache_invalidated_pairs)
    margin_by_key = _load_margin_by_key(args.logit_margin_jsonl)
    reuse_pair_summary = _pair_summary(reuse_pairs)
    invalidated_pair_summary = _pair_summary(invalidated_pairs)
    reuse_keys = set(reuse_pair_summary["any_drift_keys"])
    invalidated_keys = set(invalidated_pair_summary["any_drift_keys"])
    common_pair_keys = {_row_key(row) for row in reuse_pairs} & {
        _row_key(row) for row in invalidated_pairs
    }
    accuracy_delta_gap = (
        abs(
            float(reuse_pair_summary["accuracy_delta"])
            - float(invalidated_pair_summary["accuracy_delta"])
        )
        if reuse_pair_summary["accuracy_delta"] is not None
        and invalidated_pair_summary["accuracy_delta"] is not None
        else None
    )
    payload = {
        "phase": "1.30AF",
        "scope_note": (
            "Post-hoc attribution over 1.30AD/1.30AC artifacts. This is not "
            "direct KV tensor-distance measurement; it tests whether equal "
            "aggregate loss comes from identical row-level failures or from "
            "different policy-specific flip sets."
        ),
        "cache_reuse": {
            "pairs": args.cache_reuse_pairs.as_posix(),
            "streaming": args.cache_reuse_streaming.as_posix(),
            "pair_summary": reuse_pair_summary,
            "feature_correlations": _feature_correlation_summary(reuse_pairs, margin_by_key),
            "streaming_summary": _streaming_summary(_load_jsonl(args.cache_reuse_streaming)),
        },
        "cache_invalidated": {
            "pairs": args.cache_invalidated_pairs.as_posix(),
            "streaming": args.cache_invalidated_streaming.as_posix(),
            "pair_summary": invalidated_pair_summary,
            "feature_correlations": _feature_correlation_summary(invalidated_pairs, margin_by_key),
            "streaming_summary": _streaming_summary(_load_jsonl(args.cache_invalidated_streaming)),
        },
        "logit_margin_jsonl": (
            args.logit_margin_jsonl.as_posix() if args.logit_margin_jsonl.exists() else None
        ),
        "logit_margin_available": bool(margin_by_key),
        "common_pair_rows": len(common_pair_keys),
        "accuracy_delta_gap": accuracy_delta_gap,
        "any_drift_set_overlap": _set_stats(reuse_keys, invalidated_keys),
        "pass_complete_overlap": len(common_pair_keys) >= 171,
        "pass_same_net_delta": bool(accuracy_delta_gap is not None and accuracy_delta_gap <= 0.005),
        "pass_mechanism_contrast": False,
        "pass_row_set_nonidentity": bool(reuse_keys != invalidated_keys),
        "pass_feature_attribution_report": True,
    }
    reuse_active = payload["cache_reuse"]["streaming_summary"][
        "follow_up_vision_pruning_active_fraction"
    ]
    invalidated_active = payload["cache_invalidated"]["streaming_summary"][
        "follow_up_vision_pruning_active_fraction"
    ]
    payload["pass_mechanism_contrast"] = bool(
        reuse_active is not None
        and invalidated_active is not None
        and reuse_active < 0.10
        and invalidated_active > 0.90
    )
    payload["interpretation"] = (
        "If pass_same_net_delta and pass_row_set_nonidentity both hold, the "
        "paper should describe 1.30AC/AD as same aggregate boundary loss, not "
        "byte-equivalent behavior. The policies perturb different rows through "
        "different cache mechanisms."
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"[1.30AF] wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
