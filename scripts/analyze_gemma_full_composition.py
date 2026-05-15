#!/usr/bin/env python3
"""Analyze direct dense-vs-RLT composition artifacts.

This pairs a dense-reference ``run_novelty_pruning_gemma.py`` artifact
(``prune_placeholders=none``, no sparse vision) against a candidate artifact.
The candidate can be dense-equivalent, RLT prompt admission only, RLT
C-VISION only, or the full RLT admission + C-VISION composition. Q0b uses the
same pairing and ledger fields to separate prompt-side and encoder-side
failure modes before query-routing operators are allowed to run.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "gemma_full_composition_analysis_v2"
QUALITY_EPSILON = 1e-12
QUERY_CVISION_SCORE_MODES = {
    "rlt_topk",
    "rlt_topk_static_floor",
    "rlt_topk_endpoint_anchor",
    "fixed_uniform",
    "random_valid",
}
COMBINED_POLICY_INVARIANT_KEYS = (
    "anchor_arm",
    "arm_order",
    "frame_count",
    "group_keep_rates",
    "group_vision_tower_keep_rates",
    "keep_rate",
    "max_tokens",
    "model_path",
    "n_warmup",
    "prefill_step_size",
    "prune_placeholders",
    "rlt_config",
    "vision_tower_keep_rate",
    "vision_tower_layer",
    "vision_tower_score_mode",
)


def _safe_float(value: Any, default: float) -> float:
    if value is None:
        return default
    return float(value)


def _load_jsonl(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    schema: dict[str, Any] | None = None
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            payload = json.loads(stripped)
            kind = payload.get("kind")
            if kind == "schema":
                if schema is not None:
                    raise ValueError(f"{path}:{lineno} has a duplicate schema row")
                schema = payload
            elif kind in (None, "item"):
                rows.append(payload)
            else:
                raise ValueError(f"{path}:{lineno} has unexpected row kind {kind!r}")
    if schema is None:
        raise ValueError(f"{path} is missing a schema row")
    if not rows:
        raise ValueError(f"{path} has no item rows")
    return schema, rows


def _artifact_payload(schema: dict[str, Any]) -> dict[str, Any]:
    payload = schema.get("artifact_payload")
    if not isinstance(payload, dict):
        raise ValueError("schema row is missing artifact_payload")
    return payload


def _composed_arm_kind(composed: dict[str, Any]) -> str:
    prune_placeholders = composed.get("prune_placeholders")
    vision_keep_rate = _safe_float(composed.get("vision_tower_keep_rate"), 1.0)
    score_mode = composed.get("vision_tower_score_mode")
    uses_query_cvision = score_mode in QUERY_CVISION_SCORE_MODES

    if prune_placeholders == "none" and not uses_query_cvision:
        return "dense_equivalent"
    if prune_placeholders == "rlt" and not uses_query_cvision:
        return "rlt_admission_only"
    if prune_placeholders == "none" and uses_query_cvision:
        return "rlt_cvision_only" if score_mode == "rlt_topk" else f"{score_mode}_cvision_only"
    if prune_placeholders == "rlt" and score_mode in QUERY_CVISION_SCORE_MODES:
        if score_mode == "rlt_topk":
            return "rlt_admission_plus_rlt_cvision"
        return f"rlt_admission_plus_{score_mode}_cvision"
    raise ValueError(
        "unsupported composed arm contract: "
        f"prune_placeholders={prune_placeholders!r} "
        f"vision_tower_keep_rate={vision_keep_rate!r} "
        f"vision_tower_score_mode={score_mode!r}"
    )


def _require_contract(dense_schema: dict[str, Any], composed_schema: dict[str, Any]) -> str:
    dense = _artifact_payload(dense_schema)
    composed = _artifact_payload(composed_schema)
    if dense.get("prune_placeholders") != "none":
        raise ValueError("dense reference must use prune_placeholders=none")
    if _safe_float(dense.get("vision_tower_keep_rate"), 1.0) < 1.0:
        raise ValueError("dense reference must not use sparse vision")
    cell_type = _composed_arm_kind(composed)
    for key in ("manifest", "frame_count", "prefill_step_size"):
        if dense.get(key) != composed.get(key):
            raise ValueError(
                f"dense/composed schemas disagree on {key}: "
                f"{dense.get(key)!r} vs {composed.get(key)!r}"
            )
    return cell_type


def _combined_policy_signature(
    dense_schema: dict[str, Any], composed_schema: dict[str, Any], *, cell_type: str
) -> dict[str, dict[str, Any]]:
    def subset(payload: dict[str, Any]) -> dict[str, Any]:
        values: dict[str, Any] = {}
        for key in COMBINED_POLICY_INVARIANT_KEYS:
            if key in {"group_keep_rates", "group_vision_tower_keep_rates"}:
                value = payload.get(key)
                if value is None:
                    value = {}
            elif key not in payload:
                continue
            else:
                value = payload.get(key)
            if key in {"group_keep_rates", "group_vision_tower_keep_rates"} and value is None:
                value = {}
            values[key] = value
        return values

    return {
        "cell_type": {"value": cell_type},
        "dense": subset(_artifact_payload(dense_schema)),
        "composed": subset(_artifact_payload(composed_schema)),
    }


def _rows_by_item(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_item: dict[str, dict[str, Any]] = {}
    for row in rows:
        item_id = str(row["item_id"])
        if item_id in by_item:
            raise ValueError(f"duplicate item_id {item_id}")
        by_item[item_id] = row
    return by_item


def _timing(row: dict[str, Any], branch: str, key: str) -> float:
    timings = row.get(f"{branch}_timing_ms")
    if not isinstance(timings, dict):
        raise ValueError(f"{row.get('item_id')} missing {branch}_timing_ms")
    value = timings.get(key)
    if value is None:
        raise ValueError(f"{row.get('item_id')} missing {branch}_timing_ms.{key}")
    return float(value)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _accuracy(rows: list[dict[str, Any]], key: str) -> float:
    return sum(bool(row[key]) for row in rows) / len(rows) if rows else 0.0


def _bootstrap_ci(
    rows: list[dict[str, Any]],
    *,
    metric: Callable[[list[dict[str, Any]]], float],
    n_bootstrap: int,
    seed: int = 20260508,
) -> list[float] | None:
    if not rows or n_bootstrap <= 0:
        return None
    by_item: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_item[str(row["item_id"])].append(row)
    keys = sorted(by_item)
    rng = random.Random(seed)
    samples: list[float] = []
    for _ in range(n_bootstrap):
        sample_rows: list[dict[str, Any]] = []
        for key in rng.choices(keys, k=len(keys)):
            sample_rows.extend(by_item[key])
        samples.append(metric(sample_rows))
    samples.sort()
    return [
        float(samples[int(0.025 * (len(samples) - 1))]),
        float(samples[int(0.975 * (len(samples) - 1))]),
    ]


def _accuracy_delta(rows: list[dict[str, Any]]) -> float:
    return _accuracy(rows, "composed_correct") - _accuracy(rows, "dense_correct")


def _e2e_speedup(rows: list[dict[str, Any]]) -> float:
    dense = sum(float(row["dense_end_to_end_ms"]) for row in rows)
    composed = sum(float(row["composed_end_to_end_ms"]) for row in rows)
    return dense / composed if composed > 0.0 else 0.0


def _group_rows(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("group", "unknown"))].append(row)
    return dict(grouped)


def _count_by_key(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        counts[str(row.get(key, "unknown"))] += 1
    return dict(sorted(counts.items()))


def _choice_agreement(rows: list[dict[str, Any]]) -> float:
    if not rows:
        return 0.0
    return sum(not bool(row["choice_changed"]) for row in rows) / len(rows)


def _summarize(
    rows: list[dict[str, Any]],
    *,
    cell_type: str,
    quality_delta_floor: float,
    bucket_min_n: int,
    n_bootstrap: int,
) -> dict[str, Any]:
    dense_acc = _accuracy(rows, "dense_correct")
    composed_acc = _accuracy(rows, "composed_correct")
    accuracy_delta = composed_acc - dense_acc
    dense_e2e = sum(float(row["dense_end_to_end_ms"]) for row in rows)
    composed_e2e = sum(float(row["composed_end_to_end_ms"]) for row in rows)
    parse_delta = sum(bool(row["composed_parse_failure"]) for row in rows) - sum(
        bool(row["dense_parse_failure"]) for row in rows
    )
    by_group: dict[str, Any] = {}
    bucket_failures: list[str] = []
    bucket_underpowered: list[str] = []
    for group, group_rows in sorted(_group_rows(rows).items()):
        group_delta = _accuracy_delta(group_rows)
        group_speedup = _e2e_speedup(group_rows)
        evaluated = len(group_rows) >= bucket_min_n
        pass_quality = group_delta + QUALITY_EPSILON >= quality_delta_floor if evaluated else None
        pass_e2e = group_speedup > 1.0 if evaluated else None
        if evaluated and not (pass_quality and pass_e2e):
            bucket_failures.append(group)
        if not evaluated:
            bucket_underpowered.append(group)
        by_group[group] = {
            "n": len(group_rows),
            "dense_accuracy": _accuracy(group_rows, "dense_correct"),
            "composed_accuracy": _accuracy(group_rows, "composed_correct"),
            "accuracy_delta_composed_minus_dense": group_delta,
            "e2e_speedup_dense_over_composed": group_speedup,
            "failure_taxonomy": _count_by_key(group_rows, "correctness_transition"),
            "parse_taxonomy": _count_by_key(group_rows, "parse_transition"),
            "choice_agreement": _choice_agreement(group_rows),
            "gate_evaluated": evaluated,
            "quality_gate_pass": pass_quality,
            "e2e_gate_pass": pass_e2e,
        }
    choice_changes = sum(bool(row["choice_changed"]) for row in rows)
    dense_equivalence = (
        cell_type == "dense_equivalent"
        and accuracy_delta == 0.0
        and parse_delta == 0
        and choice_changes == 0
    )
    return {
        "cell_type": cell_type,
        "n_items": len(rows),
        "dense_accuracy": dense_acc,
        "composed_accuracy": composed_acc,
        "accuracy_delta_composed_minus_dense": accuracy_delta,
        "accuracy_delta_ci95": _bootstrap_ci(rows, metric=_accuracy_delta, n_bootstrap=n_bootstrap),
        "e2e_speedup_dense_over_composed": dense_e2e / composed_e2e if composed_e2e > 0.0 else 0.0,
        "e2e_speedup_ci95": _bootstrap_ci(rows, metric=_e2e_speedup, n_bootstrap=n_bootstrap),
        "dense_total_e2e_ms": dense_e2e,
        "composed_total_e2e_ms": composed_e2e,
        "mean_dense_end_to_end_ms": dense_e2e / len(rows),
        "mean_composed_end_to_end_ms": composed_e2e / len(rows),
        "mean_dense_vision_ms": _mean([float(row["dense_vision_ms"]) for row in rows]),
        "mean_composed_vision_ms": _mean([float(row["composed_vision_ms"]) for row in rows]),
        "mean_dense_prefill_ms": _mean([float(row["dense_prefill_ms"]) for row in rows]),
        "mean_composed_prefill_ms": _mean([float(row["composed_prefill_ms"]) for row in rows]),
        "parse_failure_delta_composed_minus_dense": parse_delta,
        "choice_changed_count": choice_changes,
        "choice_agreement": _choice_agreement(rows),
        "failure_taxonomy": _count_by_key(rows, "correctness_transition"),
        "parse_taxonomy": _count_by_key(rows, "parse_transition"),
        "pass_complete_pairing": True,
        "pass_dense_equivalence": dense_equivalence if cell_type == "dense_equivalent" else None,
        "pass_fidelity": accuracy_delta + QUALITY_EPSILON >= quality_delta_floor,
        "pass_e2e_positive": dense_e2e > composed_e2e,
        "pass_parse_failure_delta": parse_delta <= 2,
        "pass_bucket_quality_and_e2e": not bucket_failures,
        "bucket_failures": bucket_failures,
        "bucket_underpowered": bucket_underpowered,
        "by_group": by_group,
    }


def _paired_rows(
    dense_rows: list[dict[str, Any]],
    composed_rows: list[dict[str, Any]],
    *,
    expected_items: int | None,
    cell_type: str,
) -> list[dict[str, Any]]:
    dense_by_item = _rows_by_item(dense_rows)
    composed_by_item = _rows_by_item(composed_rows)
    paired_ids = sorted(set(dense_by_item) & set(composed_by_item))
    if expected_items is not None and len(paired_ids) != expected_items:
        raise ValueError(
            f"expected {expected_items} paired items, found {len(paired_ids)} "
            f"(dense={len(dense_by_item)}, composed={len(composed_by_item)})"
        )
    rows: list[dict[str, Any]] = []
    for item_id in paired_ids:
        dense = dense_by_item[item_id]
        composed = composed_by_item[item_id]
        if dense.get("answer_index") != composed.get("answer_index"):
            raise ValueError(f"answer mismatch for {item_id}")
        dense_metadata = dense.get("metadata", {})
        composed_metadata = composed.get("metadata", {})
        if not isinstance(dense_metadata, dict):
            dense_metadata = {}
        if not isinstance(composed_metadata, dict):
            composed_metadata = {}
        placeholder_total = composed_metadata.get("dense_placeholder_count")
        placeholder_kept = composed_metadata.get("pruned_placeholder_count")
        placeholder_bypassed = composed_metadata.get("placeholder_prune_bypassed")
        if placeholder_total is None or placeholder_kept is None or placeholder_bypassed is None:
            raise ValueError(f"{item_id} missing placeholder ledger fields")
        placeholder_total_i = int(placeholder_total)
        placeholder_kept_i = int(placeholder_kept)
        if placeholder_total_i <= 0:
            raise ValueError(f"{item_id} has nonpositive dense_placeholder_count")
        if cell_type == "dense_equivalent" or cell_type.endswith("_cvision_only"):
            if not bool(placeholder_bypassed):
                raise ValueError(f"{item_id} expected placeholder_prune_bypassed=true")
            if placeholder_total_i != placeholder_kept_i:
                raise ValueError(
                    f"{item_id} expected dense placeholder count, got "
                    f"{placeholder_kept_i}/{placeholder_total_i}"
                )
        encoder_valid = composed_metadata.get("gemma_encoder_valid_positions_per_frame")
        encoder_kept = composed_metadata.get("gemma_encoder_kept_per_frame")
        require_encoder = cell_type.endswith("_cvision_only") or "_cvision" in cell_type
        if require_encoder and (encoder_valid is None or encoder_kept is None):
            raise ValueError(f"{item_id} missing Gemma encoder kept/valid ledger fields")
        vision_reduction = None
        if encoder_valid is not None and encoder_kept is not None:
            valid_values = [int(value) for value in encoder_valid]
            kept_values = [int(value) for value in encoder_kept]
            if len(valid_values) != len(kept_values):
                raise ValueError(f"{item_id} encoder kept/valid length mismatch")
            reductions = [
                1.0 - (kept / valid)
                for kept, valid in zip(kept_values, valid_values, strict=True)
                if valid > 0
            ]
            vision_reduction = _mean(reductions)
        dense_correct = bool(dense.get("dense_correct"))
        composed_correct = bool(composed.get("pruned_correct"))
        if dense_correct and composed_correct:
            correctness_transition = "preserved_correct"
        elif dense_correct and not composed_correct:
            correctness_transition = "harmed"
        elif not dense_correct and composed_correct:
            correctness_transition = "recovered"
        else:
            correctness_transition = "unchanged_wrong"
        dense_parse_failure = bool(dense.get("dense_parse_failure"))
        composed_parse_failure = bool(composed.get("pruned_parse_failure"))
        if dense_parse_failure == composed_parse_failure:
            parse_transition = "parse_same"
        elif dense_parse_failure:
            parse_transition = "parse_recovered"
        else:
            parse_transition = "parse_harmed"
        rows.append(
            {
                "paired_row_key": item_id,
                "cell_type": cell_type,
                "item_id": item_id,
                "benchmark": dense.get("benchmark"),
                "group": dense.get("group"),
                "answer_index": dense.get("answer_index"),
                "dense_correct": dense_correct,
                "composed_correct": composed_correct,
                "correctness_transition": correctness_transition,
                "dense_parse_failure": dense_parse_failure,
                "composed_parse_failure": composed_parse_failure,
                "parse_transition": parse_transition,
                "dense_choice": dense.get("dense_choice"),
                "composed_choice": composed.get("pruned_choice"),
                "choice_changed": dense.get("dense_choice") != composed.get("pruned_choice"),
                "dense_end_to_end_ms": _timing(dense, "dense", "end_to_end"),
                "composed_end_to_end_ms": _timing(composed, "pruned", "end_to_end"),
                "dense_vision_ms": _timing(dense, "dense", "vision"),
                "composed_vision_ms": _timing(composed, "pruned", "vision"),
                "dense_prefill_ms": _timing(dense, "dense", "multimodal_prefill_ms"),
                "composed_prefill_ms": _timing(composed, "pruned", "multimodal_prefill_ms"),
                "dense_prompt_tokens": dense.get("dense_prompt_tokens"),
                "composed_prompt_tokens": composed.get("pruned_prompt_tokens"),
                "dense_metadata": dense_metadata,
                "composed_metadata": composed_metadata,
                "dense_placeholder_count": placeholder_total_i,
                "composed_placeholder_count": placeholder_kept_i,
                "placeholder_prune_bypassed": bool(placeholder_bypassed),
                "placeholder_reduction": 1.0 - (placeholder_kept_i / placeholder_total_i),
                "gemma_encoder_valid_positions_per_frame": encoder_valid,
                "gemma_encoder_kept_per_frame": encoder_kept,
                "vision_reduction": vision_reduction,
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dense-jsonl", type=Path, required=True, action="append")
    parser.add_argument("--composed-jsonl", type=Path, required=True, action="append")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--paired-items", type=Path, required=True)
    parser.add_argument("--expected-items", type=int, required=True)
    parser.add_argument("--quality-delta-floor", type=float, default=-0.05)
    parser.add_argument("--bucket-min-n", type=int, default=5)
    parser.add_argument("--n-bootstrap", type=int, default=1000)
    args = parser.parse_args()

    dense_paths: list[Path] = args.dense_jsonl
    composed_paths: list[Path] = args.composed_jsonl
    if len(dense_paths) != len(composed_paths):
        raise ValueError(
            f"got {len(dense_paths)} dense JSONLs but {len(composed_paths)} composed JSONLs"
        )
    paired: list[dict[str, Any]] = []
    source_pairs: list[dict[str, Any]] = []
    policy_signature: dict[str, dict[str, Any]] | None = None
    for dense_path, composed_path in zip(dense_paths, composed_paths, strict=True):
        dense_schema, dense_rows = _load_jsonl(dense_path)
        composed_schema, composed_rows = _load_jsonl(composed_path)
        cell_type = _require_contract(dense_schema, composed_schema)
        source_signature = _combined_policy_signature(
            dense_schema, composed_schema, cell_type=cell_type
        )
        if policy_signature is None:
            policy_signature = source_signature
        elif source_signature != policy_signature:
            raise ValueError("combined analysis source pairs disagree on policy/config invariants")
        source_paired = _paired_rows(
            dense_rows,
            composed_rows,
            expected_items=None,
            cell_type=cell_type,
        )
        source_pairs.append(
            {
                "dense_jsonl": str(dense_path),
                "composed_jsonl": str(composed_path),
                "n_items": len(source_paired),
            }
        )
        paired.extend(source_paired)
    seen_item_ids: set[str] = set()
    duplicate_item_ids: list[str] = []
    for row in paired:
        item_id = str(row["item_id"])
        if item_id in seen_item_ids:
            duplicate_item_ids.append(item_id)
        seen_item_ids.add(item_id)
    if duplicate_item_ids:
        raise ValueError(
            "combined analysis has duplicate item_ids across sources: "
            + ", ".join(sorted(duplicate_item_ids)[:5])
        )
    if len(paired) != args.expected_items:
        raise ValueError(
            f"expected {args.expected_items} paired items, found {len(paired)} "
            f"across {len(source_pairs)} source pair(s)"
        )
    summary_cell_type = (
        next(iter(policy_signature["cell_type"].values())) if policy_signature else "unknown"
    )
    summary = _summarize(
        paired,
        cell_type=summary_cell_type,
        quality_delta_floor=args.quality_delta_floor,
        bucket_min_n=args.bucket_min_n,
        n_bootstrap=args.n_bootstrap,
    )
    decisions: list[dict[str, Any]] = []
    direct_gate_keys = (
        "pass_fidelity",
        "pass_e2e_positive",
        "pass_parse_failure_delta",
        "pass_bucket_quality_and_e2e",
    )
    dense_equivalence_gate = summary.get("cell_type") == "dense_equivalent"
    if dense_equivalence_gate:
        gate_passed = bool(summary.get("pass_dense_equivalence"))
        failed = ["pass_dense_equivalence"] if not gate_passed else []
    else:
        gate_passed = all(bool(summary[key]) for key in direct_gate_keys)
        failed = [key for key in direct_gate_keys if not summary[key]]

    if not gate_passed:
        decisions.append(
            {
                "decision": "stop",
                "reason": "direct_pair_gate_failed",
                "failed": failed,
            }
        )
    else:
        decisions.append({"decision": "continue", "reason": "direct_pair_gate_passed"})

    output = {
        "schema_version": SCHEMA_VERSION,
        "dense_jsonl": (
            str(dense_paths[0]) if len(dense_paths) == 1 else [str(p) for p in dense_paths]
        ),
        "composed_jsonl": (
            str(composed_paths[0]) if len(composed_paths) == 1 else [str(p) for p in composed_paths]
        ),
        "source_pairs": source_pairs,
        "expected_items": args.expected_items,
        "cell_type": summary["cell_type"],
        "summary": summary,
        "decisions": decisions,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    args.paired_items.parent.mkdir(parents=True, exist_ok=True)
    with args.paired_items.open("w", encoding="utf-8") as handle:
        for row in paired:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    print(json.dumps({"output": str(args.output), "decision": decisions[0]["decision"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
