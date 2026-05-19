from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

INTRINSIC_FIELDS = ("benchmark", "group", "answer_index")
DENSE_LABEL_FIELDS = ("dense_choice", "dense_correct", "dense_parse_failure")
COMPOSED_LABEL_FIELDS = ("composed_choice", "composed_correct", "composed_parse_failure")
TIMING_FIELDS = ("dense_end_to_end_ms", "composed_end_to_end_ms")
TRANSITIONS = ("preserved_correct", "recovered", "harmed", "unchanged_wrong")


def _finite_float(row: dict[str, Any], field: str) -> float:
    value = row.get(field)
    if not isinstance(value, int | float) or not math.isfinite(float(value)):
        item = row.get("item_id", "<missing item_id>")
        raise ValueError(f"{item}: missing or non-finite {field}")
    return float(value)


def _optional_finite_float(row: dict[str, Any], field: str) -> float:
    value = row.get(field, 0.0)
    if value is None:
        return 0.0
    if not isinstance(value, int | float) or not math.isfinite(float(value)):
        item = row.get("item_id", "<missing item_id>")
        raise ValueError(f"{item}: non-finite {field}")
    result = float(value)
    if result < 0.0:
        item = row.get("item_id", "<missing item_id>")
        raise ValueError(f"{item}: negative {field}")
    return result


def _row_key(row: dict[str, Any]) -> str:
    item_id = row.get("item_id") or row.get("paired_row_key")
    if not isinstance(item_id, str) or not item_id:
        raise ValueError("paired row missing item_id/paired_row_key")
    return item_id


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSONL") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_no}: expected object row")
            rows.append(row)
    if not rows:
        raise ValueError(f"{path}: no rows")
    return rows


def _index_rows(rows: list[dict[str, Any]], *, label: str) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = _row_key(row)
        if key in indexed:
            raise ValueError(f"{label}: duplicate item_id {key!r}")
        for field in (
            *INTRINSIC_FIELDS,
            *DENSE_LABEL_FIELDS,
            *COMPOSED_LABEL_FIELDS,
            *TIMING_FIELDS,
        ):
            if field not in row:
                raise ValueError(f"{label}: {key}: missing {field}")
        for field in (
            "dense_correct",
            "dense_parse_failure",
            "composed_correct",
            "composed_parse_failure",
        ):
            if not isinstance(row[field], bool):
                raise ValueError(f"{label}: {key}: {field} must be boolean")
        for field in ("dense_choice", "composed_choice"):
            if row[field] is not None and not isinstance(row[field], int):
                raise ValueError(f"{label}: {key}: {field} must be int or null")
        for field in TIMING_FIELDS:
            if _finite_float(row, field) <= 0.0:
                raise ValueError(f"{label}: {key}: {field} must be positive")
        indexed[key] = row
    return indexed


def _validate_pairing(
    safe_rows: dict[str, dict[str, Any]],
    fast_rows: dict[str, dict[str, Any]],
    *,
    allow_dense_label_drift: bool,
) -> dict[str, Any]:
    safe_keys = set(safe_rows)
    fast_keys = set(fast_rows)
    if safe_keys != fast_keys:
        missing_from_safe = sorted(fast_keys - safe_keys)
        missing_from_fast = sorted(safe_keys - fast_keys)
        raise ValueError(
            "safe and fast paired rows do not have the same item set: "
            f"missing_from_safe={missing_from_safe[:5]}, "
            f"missing_from_fast={missing_from_fast[:5]}"
        )

    dense_label_mismatches: list[dict[str, Any]] = []
    intrinsic_mismatches: list[dict[str, Any]] = []
    for key in sorted(safe_keys):
        safe = safe_rows[key]
        fast = fast_rows[key]
        intrinsic_diff = {
            field: {"safe": safe.get(field), "fast": fast.get(field)}
            for field in INTRINSIC_FIELDS
            if safe.get(field) != fast.get(field)
        }
        if intrinsic_diff:
            intrinsic_mismatches.append({"item_id": key, "diff": intrinsic_diff})
        dense_diff = {
            field: {"safe": safe.get(field), "fast": fast.get(field)}
            for field in DENSE_LABEL_FIELDS
            if safe.get(field) != fast.get(field)
        }
        if dense_diff:
            dense_label_mismatches.append({"item_id": key, "diff": dense_diff})

    if intrinsic_mismatches:
        raise ValueError(
            "safe and fast paired rows disagree on item-intrinsic fields: "
            f"{intrinsic_mismatches[:5]}"
        )
    if dense_label_mismatches and not allow_dense_label_drift:
        raise ValueError(
            "safe and fast paired rows disagree on dense labels; rerun with "
            "--allow-dense-label-drift only for explicitly exploratory analyses: "
            f"{dense_label_mismatches[:5]}"
        )
    return {
        "dense_label_mismatch_count": len(dense_label_mismatches),
        "dense_label_mismatches": dense_label_mismatches[:20],
        "observed_groups": sorted({str(row["group"]) for row in safe_rows.values()}),
    }


def _adjusted_dense_ms(row: dict[str, Any]) -> float:
    adjusted = _finite_float(row, "dense_end_to_end_ms") - _optional_finite_float(
        row, "dense_first_generated_confidence_capture_ms"
    )
    if adjusted <= 0.0:
        item = row.get("item_id", "<missing item_id>")
        raise ValueError(f"{item}: adjusted dense timing must be positive")
    return adjusted


def _adjusted_composed_ms(row: dict[str, Any]) -> float:
    adjusted = _finite_float(row, "composed_end_to_end_ms") - _optional_finite_float(
        row, "composed_first_generated_confidence_capture_ms"
    )
    if adjusted <= 0.0:
        item = row.get("item_id", "<missing item_id>")
        raise ValueError(f"{item}: adjusted composed timing must be positive")
    return adjusted


def _transition(dense_correct: bool, composed_correct: bool) -> str:
    if dense_correct and composed_correct:
        return "preserved_correct"
    if not dense_correct and composed_correct:
        return "recovered"
    if dense_correct and not composed_correct:
        return "harmed"
    return "unchanged_wrong"


def _empty_group_summary() -> dict[str, Any]:
    return {
        "n": 0,
        "dense_correct": 0,
        "policy_correct": 0,
        "choice_changed_count": 0,
        "dense_total_ms": 0.0,
        "policy_total_ms": 0.0,
        "source_counts": Counter(),
        "failure_taxonomy": Counter(),
    }


def _finalize_summary(summary: dict[str, Any]) -> dict[str, Any]:
    n = int(summary["n"])
    dense_correct = int(summary["dense_correct"])
    policy_correct = int(summary["policy_correct"])
    dense_total_ms = float(summary["dense_total_ms"])
    policy_total_ms = float(summary["policy_total_ms"])
    source_counts = dict(sorted(summary["source_counts"].items()))
    failure_taxonomy = {
        transition: int(summary["failure_taxonomy"].get(transition, 0))
        for transition in TRANSITIONS
    }
    return {
        "n": n,
        "dense_accuracy": dense_correct / n if n else None,
        "policy_accuracy": policy_correct / n if n else None,
        "accuracy_delta_policy_minus_dense": (policy_correct - dense_correct) / n if n else None,
        "choice_agreement": 1.0 - (int(summary["choice_changed_count"]) / n) if n else None,
        "choice_changed_count": int(summary["choice_changed_count"]),
        "dense_total_ms": dense_total_ms,
        "policy_total_ms": policy_total_ms,
        "e2e_speedup_dense_over_policy": dense_total_ms / policy_total_ms,
        "source_counts": source_counts,
        "failure_taxonomy": failure_taxonomy,
    }


def _simulate_policy(
    safe_rows: dict[str, dict[str, Any]],
    fast_rows: dict[str, dict[str, Any]],
    *,
    fallback_groups: set[str],
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    overall = _empty_group_summary()
    by_group = defaultdict(_empty_group_summary)
    item_rows: list[dict[str, Any]] = []

    for key in sorted(safe_rows):
        safe = safe_rows[key]
        fast = fast_rows[key]
        group = str(safe["group"])
        use_safe = group in fallback_groups
        chosen = safe if use_safe else fast
        source = "safe" if use_safe else "fast"
        dense_correct = bool(safe["dense_correct"])
        policy_correct = bool(chosen["composed_correct"])
        dense_choice = safe.get("dense_choice")
        policy_choice = chosen.get("composed_choice")
        transition = _transition(dense_correct, policy_correct)
        dense_ms = _adjusted_dense_ms(safe)
        policy_ms = _adjusted_composed_ms(chosen)
        if dense_ms <= 0.0 or policy_ms <= 0.0:
            raise ValueError(f"{key}: adjusted timing must be positive")

        for summary in (overall, by_group[group]):
            summary["n"] += 1
            summary["dense_correct"] += int(dense_correct)
            summary["policy_correct"] += int(policy_correct)
            summary["choice_changed_count"] += int(dense_choice != policy_choice)
            summary["dense_total_ms"] += dense_ms
            summary["policy_total_ms"] += policy_ms
            summary["source_counts"][source] += 1
            summary["failure_taxonomy"][transition] += 1

        item_rows.append(
            {
                "item_id": key,
                "group": group,
                "source": source,
                "dense_correct": dense_correct,
                "policy_correct": policy_correct,
                "dense_choice": dense_choice,
                "policy_choice": policy_choice,
                "correctness_transition": transition,
                "dense_ms": dense_ms,
                "policy_ms": policy_ms,
            }
        )

    return (
        _finalize_summary(overall),
        item_rows,
        {group: _finalize_summary(summary) for group, summary in sorted(by_group.items())},
    )


def _source_summary(rows: dict[str, dict[str, Any]]) -> dict[str, Any]:
    summary = _empty_group_summary()
    for row in rows.values():
        dense_correct = bool(row["dense_correct"])
        composed_correct = bool(row["composed_correct"])
        dense_choice = row.get("dense_choice")
        composed_choice = row.get("composed_choice")
        transition = _transition(dense_correct, composed_correct)
        summary["n"] += 1
        summary["dense_correct"] += int(dense_correct)
        summary["policy_correct"] += int(composed_correct)
        summary["choice_changed_count"] += int(dense_choice != composed_choice)
        summary["dense_total_ms"] += _adjusted_dense_ms(row)
        summary["policy_total_ms"] += _adjusted_composed_ms(row)
        summary["source_counts"]["all"] += 1
        summary["failure_taxonomy"][transition] += 1
    return _finalize_summary(summary)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Simulate class-conditional admission routing from already-paired Gemma "
            "composition artifacts. This is an offline policy audit, not a new MLX run."
        )
    )
    parser.add_argument("--safe-paired-items", required=True, type=Path)
    parser.add_argument("--fast-paired-items", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--fallback-group",
        action="append",
        default=[],
        help="Route this group to the safe/no-admission paired rows.",
    )
    parser.add_argument(
        "--policy-label",
        default="group_conditional_safe_fallback",
    )
    parser.add_argument(
        "--allow-dense-label-drift",
        action="store_true",
        help=(
            "Allow safe/fast dense-label disagreement and record it. Default hard-fails "
            "because mixed-policy accuracy otherwise has an ambiguous reference."
        ),
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    fallback_groups = set(args.fallback_group)
    if not fallback_groups:
        raise ValueError("at least one --fallback-group is required")

    safe_rows = _index_rows(
        _read_jsonl(args.safe_paired_items),
        label="safe-paired-items",
    )
    fast_rows = _index_rows(
        _read_jsonl(args.fast_paired_items),
        label="fast-paired-items",
    )
    audit = _validate_pairing(
        safe_rows,
        fast_rows,
        allow_dense_label_drift=args.allow_dense_label_drift,
    )
    unknown_fallback_groups = sorted(fallback_groups - set(audit["observed_groups"]))
    if unknown_fallback_groups:
        raise ValueError(
            "requested fallback groups are absent from paired rows: "
            f"{unknown_fallback_groups}; observed_groups={audit['observed_groups']}"
        )
    audit["requested_fallback_groups"] = sorted(fallback_groups)
    summary, item_rows, by_group = _simulate_policy(
        safe_rows,
        fast_rows,
        fallback_groups=fallback_groups,
    )
    payload = {
        "schema": "gemma_admission_policy_simulation_v1",
        "analysis_role": "exploratory_offline_policy_simulation",
        "dense_reference_source": "safe_paired_items",
        "policy_label": args.policy_label,
        "fallback_groups": sorted(fallback_groups),
        "safe_source_path": str(args.safe_paired_items),
        "fast_source_path": str(args.fast_paired_items),
        "pairing_audit": audit,
        "summary": summary,
        "by_group": by_group,
        "source_baselines": {
            "safe_all_items": _source_summary(safe_rows),
            "fast_all_items": _source_summary(fast_rows),
        },
        "items": item_rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
