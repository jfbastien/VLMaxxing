#!/usr/bin/env python3
"""Validate Sam scale-out JSONL artifacts before importing them as evidence.

This intentionally implements only the JSON-Schema subset used by
``research/schemas/sam_scaleout_artifact_v1.schema.json`` plus explicit
protocol gates for B0/B3/B5. The goal is hard-fail artifact hygiene, not a
general-purpose schema validator.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = ROOT / "research/schemas/sam_scaleout_artifact_v1.schema.json"


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        obj = json.load(handle)
    if not isinstance(obj, dict):
        raise SystemExit(f"{path} did not contain a JSON object")
    return obj


def _load_jsonl(path: Path) -> list[tuple[int, dict[str, Any]]]:
    rows: list[tuple[int, dict[str, Any]]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            obj = json.loads(line)
            if not isinstance(obj, dict):
                raise SystemExit(f"{path}:{line_no} did not contain a JSON object")
            rows.append((line_no, obj))
    return rows


def _type_ok(value: Any, expected: str) -> bool:
    if expected == "null":
        return value is None
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "array":
        return isinstance(value, list)
    if expected == "object":
        return isinstance(value, dict)
    raise ValueError(f"unsupported schema type: {expected}")


def _allowed_types(spec: dict[str, Any]) -> list[str]:
    expected = spec.get("type")
    if isinstance(expected, str):
        return [expected]
    if isinstance(expected, list) and all(isinstance(item, str) for item in expected):
        return expected
    raise ValueError(f"unsupported type declaration: {expected!r}")


def _validate_value(value: Any, spec: dict[str, Any], path: str) -> list[str]:
    errors: list[str] = []
    if "const" in spec and value != spec["const"]:
        errors.append(f"{path}: expected const {spec['const']!r}, got {value!r}")
        return errors

    allowed = _allowed_types(spec)
    if not any(_type_ok(value, expected) for expected in allowed):
        errors.append(f"{path}: expected {allowed}, got {type(value).__name__}")
        return errors

    if value is None:
        return errors

    if isinstance(value, str) and "minLength" in spec and len(value) < int(spec["minLength"]):
        errors.append(f"{path}: shorter than minLength={spec['minLength']}")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in spec and value < spec["minimum"]:
            errors.append(f"{path}: below minimum={spec['minimum']}")
        if "maximum" in spec and value > spec["maximum"]:
            errors.append(f"{path}: above maximum={spec['maximum']}")
    if isinstance(value, list):
        if "minItems" in spec and len(value) < int(spec["minItems"]):
            errors.append(f"{path}: fewer than minItems={spec['minItems']}")
        if "maxItems" in spec and len(value) > int(spec["maxItems"]):
            errors.append(f"{path}: more than maxItems={spec['maxItems']}")
        item_spec = spec.get("items")
        if isinstance(item_spec, dict):
            for idx, item in enumerate(value):
                errors.extend(_validate_value(item, item_spec, f"{path}[{idx}]"))
    return errors


def _validate_schema(rows: list[tuple[int, dict[str, Any]]], schema: dict[str, Any]) -> list[str]:
    required = set(schema.get("required", []))
    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        raise SystemExit("schema properties must be an object")

    errors: list[str] = []
    allow_extra = bool(schema.get("additionalProperties", True))
    for line_no, row in rows:
        missing = sorted(required.difference(row))
        for key in missing:
            errors.append(f"line {line_no}: missing required field {key!r}")
        if not allow_extra:
            for key in sorted(set(row).difference(properties)):
                errors.append(f"line {line_no}: unknown field {key!r}")
        for key, value in row.items():
            spec = properties.get(key)
            if spec is None:
                continue
            errors.extend(f"line {line_no}: {error}" for error in _validate_value(value, spec, key))
    return errors


def _is_followup(row: dict[str, Any]) -> bool:
    return int(row.get("q_index") or 0) > 0 or int(row.get("turn_index") or 0) > 0


def _count_true(rows: list[dict[str, Any]], key: str) -> int:
    return sum(1 for row in rows if bool(row.get(key)))


def _mismatch_count(rows: list[dict[str, Any]], left_key: str, right_key: str) -> int:
    return sum(1 for row in rows if row.get(left_key) != row.get(right_key))


def _non_null_count(rows: list[dict[str, Any]], key: str) -> int:
    return sum(1 for row in rows if row.get(key) is not None)


def _derived_choice_diff(row: dict[str, Any]) -> bool:
    return row.get("session_choice") != row.get("baseline_choice")


def _derived_correctness_diff(row: dict[str, Any]) -> bool:
    return bool(row.get("session_correct")) != bool(row.get("baseline_correct"))


def _derived_text_identical(row: dict[str, Any]) -> bool:
    return row.get("raw_response") == row.get("baseline_raw_response")


def _derived_parse_failure(row: dict[str, Any]) -> bool:
    return bool(row.get("session_parse_failure")) or bool(row.get("baseline_parse_failure"))


def _derived_consistency_errors(
    numbered_rows: list[tuple[int, dict[str, Any]]],
) -> list[str]:
    errors: list[str] = []
    for line_no, row in numbered_rows:
        if row.get("choice_diff") != _derived_choice_diff(row):
            errors.append(f"line {line_no}: choice_diff disagrees with paired choices")
        if row.get("correctness_diff") != _derived_correctness_diff(row):
            errors.append(f"line {line_no}: correctness_diff disagrees with paired correctness")
        if row.get("text_identical") != _derived_text_identical(row):
            errors.append(f"line {line_no}: text_identical disagrees with raw responses")
        if row.get("parse_failure") != _derived_parse_failure(row):
            errors.append(f"line {line_no}: parse_failure must equal per-arm parse failure OR")
    return errors


def _require_b0b_protocol(rows: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    cross_turn_rows = [row for row in rows if row.get("arm") == "cross_turn_warm"]
    within_turn_rows = [row for row in rows if row.get("arm") == "within_turn_cache_replay"]
    baseline_rows = [row for row in rows if row.get("baseline_arm") == "cold_dense"]

    if len(cross_turn_rows) < 21:
        errors.append(f"B0b requires at least 21 cross_turn_warm rows, saw {len(cross_turn_rows)}")
    if len(within_turn_rows) < 21:
        errors.append(
            f"B0b requires at least 21 within_turn_cache_replay rows, saw {len(within_turn_rows)}"
        )
    if not baseline_rows:
        errors.append("B0b requires baseline_arm='cold_dense' rows")

    cross_by_video: dict[Any, set[int]] = defaultdict(set)
    for row in cross_turn_rows:
        cross_by_video[row.get("video_id")].add(int(row.get("q_index") or 0))
    within_by_video: dict[Any, set[int]] = defaultdict(set)
    for row in within_turn_rows:
        within_by_video[row.get("video_id")].add(int(row.get("q_index") or 0))
    if len(cross_by_video) < 7:
        errors.append(f"B0b requires at least 7 videos, saw {len(cross_by_video)}")
    underspecified = sorted(
        str(video_id) for video_id, q_indices in cross_by_video.items() if len(q_indices) < 3
    )
    if underspecified:
        errors.append(
            "B0b requires at least 3 cross-turn questions per video; "
            f"underspecified videos: {underspecified[:10]}"
        )
    within_underspecified = sorted(
        str(video_id) for video_id, q_indices in within_by_video.items() if len(q_indices) < 3
    )
    if len(within_by_video) < 7:
        errors.append(
            f"B0b requires within-turn replay across at least 7 videos, saw {len(within_by_video)}"
        )
    if within_underspecified:
        errors.append(
            "B0b requires at least 3 within-turn replay questions per video; "
            f"underspecified videos: {within_underspecified[:10]}"
        )
    if not any(_is_followup(row) for row in cross_turn_rows):
        errors.append("B0b requires at least one cross-turn follow-up row")
    return errors


def _json_key(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _require_b3_matched_events(rows: list[dict[str, Any]], args: argparse.Namespace) -> list[str]:
    errors: list[str] = []
    required_arms = {arm.strip() for arm in (args.require_arms or "").split(",") if arm.strip()}
    by_pair_key: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_pair_key[row.get("pair_key")].append(row)

    matched_fields = (
        "video_id",
        "event_id",
        "item_id",
        "q_index",
        "turn_index",
        "raw_prompt",
        "baseline_raw_prompt",
        "baseline_choice",
        "baseline_correct",
        "event_time_s",
        "observation_window_s",
        "changed_answer_expected",
        "evidence_budget",
    )
    for pair_key, group in by_pair_key.items():
        observed_arms = {str(row.get("arm")) for row in group}
        if required_arms:
            missing = sorted(required_arms.difference(observed_arms))
            if missing:
                errors.append(f"B3 pair_key={pair_key!r} missing arms: {missing}")
        for field in matched_fields:
            values = {_json_key(row.get(field)) for row in group}
            if len(values) > 1:
                errors.append(f"B3 pair_key={pair_key!r} has mismatched {field}")
    return errors


def _phase_errors(rows: list[dict[str, Any]], args: argparse.Namespace) -> list[str]:
    errors: list[str] = []

    if args.phase:
        phases = {row.get("phase") for row in rows}
        if phases != {args.phase}:
            observed = sorted(str(phase) for phase in phases)
            errors.append(f"expected phase {args.phase!r}, saw {observed!r}")

    if len(rows) < args.min_rows:
        errors.append(f"expected at least {args.min_rows} rows, saw {len(rows)}")

    if args.expected_row_count is not None and len(rows) != args.expected_row_count:
        errors.append(f"expected exactly {args.expected_row_count} rows, saw {len(rows)}")

    if args.min_pair_keys is not None:
        pair_key_count = len({row.get("pair_key") for row in rows})
        if pair_key_count < args.min_pair_keys:
            errors.append(f"expected at least {args.min_pair_keys} pair_keys, saw {pair_key_count}")

    if args.min_videos is not None:
        video_count = len({row.get("video_id") for row in rows})
        if video_count < args.min_videos:
            errors.append(f"expected at least {args.min_videos} videos, saw {video_count}")

    if args.require_arms:
        required_arms = {arm.strip() for arm in args.require_arms.split(",") if arm.strip()}
        observed_arms = {str(row.get("arm")) for row in rows}
        missing = sorted(required_arms.difference(observed_arms))
        if missing:
            errors.append(f"missing required arms: {missing}")

    if args.require_zero_choice_diffs and any(_derived_choice_diff(row) for row in rows):
        errors.append("paired choices must match for every row")
    if args.require_zero_correctness_diffs and any(_derived_correctness_diff(row) for row in rows):
        errors.append("paired correctness must match for every row")
    if args.require_zero_text_diffs and any(not _derived_text_identical(row) for row in rows):
        errors.append("raw paired responses must be identical for every row")
    if args.require_zero_parse_failures and any(_derived_parse_failure(row) for row in rows):
        errors.append("per-arm parse failures must be false for every row")

    if args.require_matching_input_hash:
        mismatches = _mismatch_count(rows, "input_ids_hash", "baseline_input_ids_hash")
        if mismatches:
            errors.append(f"input_ids_hash mismatches: {mismatches}")
    if args.require_matching_prompt_hash:
        mismatches = _mismatch_count(rows, "prompt_hash", "baseline_prompt_hash")
        if mismatches:
            errors.append(f"prompt_hash mismatches: {mismatches}")
    if args.require_matching_frame_hashes:
        mismatches = _mismatch_count(rows, "frame_hashes", "baseline_frame_hashes")
        if mismatches:
            errors.append(f"frame_hashes mismatches: {mismatches}")

    if args.require_positive_prefix_on_followups:
        bad = [
            row.get("pair_key")
            for row in rows
            if _is_followup(row)
            and (
                row.get("prefix_hit") is None
                or row.get("prefix_hit") <= 0
                or row.get("prefix_coverage") is None
                or row.get("prefix_coverage") <= 0
            )
        ]
        if bad:
            errors.append(f"follow-up rows without positive prefix metadata: {bad[:10]}")

    if args.require_b0b_protocol:
        errors.extend(_require_b0b_protocol(rows))

    if args.require_b3_matched_events:
        missing_budget = _non_null_count(rows, "evidence_budget") != len(rows)
        missing_event = _non_null_count(rows, "event_id") != len(rows)
        missing_frames = _non_null_count(rows, "selected_frame_indices") != len(rows)
        if missing_budget:
            errors.append("B3 requires evidence_budget on every row")
        if missing_event:
            errors.append("B3 requires event_id on every row")
        if missing_frames:
            errors.append("B3 requires selected_frame_indices on every row")
        stale_rows = [
            row
            for row in rows
            if row.get("stale_cache_case_id") and row.get("changed_answer_expected") is True
        ]
        if not stale_rows:
            errors.append("B3 requires at least one changed-answer stale-cache case")
        errors.extend(_require_b3_matched_events(rows, args))

    if args.require_b5_provenance:
        for key in (
            "claim_id",
            "source_artifact_path",
            "source_artifact_sha256",
            "export_row_count",
            "expected_row_count",
            "ci_method",
            "ci95",
            "provenance_note",
        ):
            if _non_null_count(rows, key) != len(rows):
                errors.append(f"B5 requires {key} on every row")
        export_counts = {row.get("export_row_count") for row in rows}
        expected_counts = {row.get("expected_row_count") for row in rows}
        if len(export_counts) != 1:
            observed = sorted(str(count) for count in export_counts)
            errors.append(f"B5 export_row_count is not constant: {observed!r}")
        if len(expected_counts) != 1:
            observed = sorted(str(count) for count in expected_counts)
            errors.append(f"B5 expected_row_count is not constant: {observed!r}")
        if export_counts and len(export_counts) == 1 and next(iter(export_counts)) != len(rows):
            errors.append(
                f"B5 export_row_count={next(iter(export_counts))} does not match rows={len(rows)}"
            )
        if (
            args.expected_row_count is not None
            and expected_counts
            and len(expected_counts) == 1
            and next(iter(expected_counts)) != args.expected_row_count
        ):
            errors.append(
                "B5 row metadata expected_row_count="
                f"{next(iter(expected_counts))} does not match CLI expected "
                f"{args.expected_row_count}"
            )

    return errors


def _summary(rows: list[dict[str, Any]], errors: list[str]) -> dict[str, Any]:
    return {
        "n_rows": len(rows),
        "phases": dict(Counter(str(row.get("phase")) for row in rows)),
        "arms": dict(Counter(str(row.get("arm")) for row in rows)),
        "policies": dict(Counter(str(row.get("policy")) for row in rows)),
        "choice_diffs": sum(1 for row in rows if _derived_choice_diff(row)),
        "correctness_diffs": sum(1 for row in rows if _derived_correctness_diff(row)),
        "text_diffs": sum(1 for row in rows if not _derived_text_identical(row)),
        "parse_failures": sum(1 for row in rows if _derived_parse_failure(row)),
        "session_parse_failures": _count_true(rows, "session_parse_failure"),
        "baseline_parse_failures": _count_true(rows, "baseline_parse_failure"),
        "input_hash_mismatches": _mismatch_count(rows, "input_ids_hash", "baseline_input_ids_hash"),
        "prompt_hash_mismatches": _mismatch_count(rows, "prompt_hash", "baseline_prompt_hash"),
        "frame_hash_mismatches": _mismatch_count(rows, "frame_hashes", "baseline_frame_hashes"),
        "schema_or_gate_errors": len(errors),
        "first_errors": errors[:25],
        "pass": not errors,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jsonl", type=Path, required=True, help="Sam artifact JSONL")
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--summary-output", type=Path)
    parser.add_argument("--phase")
    parser.add_argument("--min-rows", type=int, default=1)
    parser.add_argument("--expected-row-count", type=int)
    parser.add_argument("--min-pair-keys", type=int)
    parser.add_argument("--min-videos", type=int)
    parser.add_argument("--require-arms")
    parser.add_argument("--require-zero-choice-diffs", action="store_true")
    parser.add_argument("--require-zero-correctness-diffs", action="store_true")
    parser.add_argument("--require-zero-text-diffs", action="store_true")
    parser.add_argument("--require-zero-parse-failures", action="store_true")
    parser.add_argument("--require-matching-input-hash", action="store_true")
    parser.add_argument("--require-matching-prompt-hash", action="store_true")
    parser.add_argument("--require-matching-frame-hashes", action="store_true")
    parser.add_argument("--require-positive-prefix-on-followups", action="store_true")
    parser.add_argument("--require-b0b-protocol", action="store_true")
    parser.add_argument("--require-b3-matched-events", action="store_true")
    parser.add_argument("--require-b5-provenance", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    schema = _load_json(args.schema)
    numbered_rows = _load_jsonl(args.jsonl)
    rows = [row for _, row in numbered_rows]
    errors = _validate_schema(numbered_rows, schema)
    errors.extend(_derived_consistency_errors(numbered_rows))
    errors.extend(_phase_errors(rows, args))

    summary = _summary(rows, errors)
    if args.summary_output:
        args.summary_output.parent.mkdir(parents=True, exist_ok=True)
        args.summary_output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    else:
        print(json.dumps(summary, indent=2))

    if errors:
        for error in errors[:25]:
            print(f"ERROR: {error}", file=sys.stderr)
        if len(errors) > 25:
            print(f"ERROR: ... {len(errors) - 25} more", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
