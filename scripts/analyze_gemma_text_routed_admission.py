#!/usr/bin/env python3
"""Simulate text-only admission routing from already-paired Gemma artifacts.

This is a CPU-only policy audit. It does not run a model. The policy routes
items whose raw question text matches ``--safe-question-regex`` to a safe
paired row, typically no-admission, and routes all other items to a fast paired
row, typically admission-on. Timing uses the safe paired row's dense branch as
the fixed denominator for every item, matching
``analyze_gemma_admission_policy_simulation.py``.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.analyze_gemma_admission_policy_simulation import (  # noqa: E402
    _adjusted_composed_ms,
    _adjusted_dense_ms,
    _empty_group_summary,
    _finalize_summary,
    _index_rows,
    _read_jsonl,
    _source_summary,
    _transition,
    _validate_pairing,
)

DEFAULT_SAFE_QUESTION_REGEX = (
    r"\bwhat\s+(?:(?:color|shape|material)\b|is\s+the\s+(?:color|shape|material)\b)"
)
MVBENCH_JSON_DIR = Path("data/benchmarks/mvbench/hf/json")


def _load_manifest_item_ids(path: Path) -> list[str]:
    payload = tomllib.loads(path.read_text(encoding="utf-8"))
    item_ids = payload.get("item_ids")
    if not isinstance(item_ids, list) or not item_ids:
        raise ValueError(f"{path}: missing non-empty item_ids")
    result: list[str] = []
    seen: set[str] = set()
    for raw in item_ids:
        if not isinstance(raw, str) or not raw:
            raise ValueError(f"{path}: item_ids must be non-empty strings")
        if raw in seen:
            raise ValueError(f"{path}: duplicate item_id {raw!r}")
        seen.add(raw)
        result.append(raw)
    return result


def _parse_mvbench_item_id(item_id: str) -> tuple[str, int]:
    parts = item_id.split(":", maxsplit=2)
    if len(parts) != 3 or parts[0] != "mvbench" or not parts[1] or not parts[2]:
        raise ValueError(f"only MVBench item ids are supported by this analyzer; got {item_id!r}")
    return parts[1], int(parts[2])


def _load_mvbench_questions(item_ids: list[str], *, json_dir: Path) -> dict[str, str]:
    payload_by_task: dict[str, list[dict[str, Any]]] = {}
    questions: dict[str, str] = {}
    for item_id in item_ids:
        task, index = _parse_mvbench_item_id(item_id)
        if task not in payload_by_task:
            path = json_dir / f"{task}.json"
            if not path.exists():
                raise FileNotFoundError(f"missing MVBench task JSON: {path}")
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, list):
                raise ValueError(f"{path}: expected list payload")
            payload_by_task[task] = payload
        task_rows = payload_by_task[task]
        if index < 0 or index >= len(task_rows):
            raise IndexError(
                f"{item_id}: index {index} out of range for task {task!r} "
                f"with {len(task_rows)} rows"
            )
        question = task_rows[index].get("question")
        if not isinstance(question, str) or not question:
            raise ValueError(f"{item_id}: missing raw question text")
        questions[item_id] = question
    return questions


def _compile_regex(pattern: str) -> re.Pattern[str]:
    try:
        return re.compile(pattern, re.IGNORECASE)
    except re.error as exc:
        raise ValueError(f"invalid --safe-question-regex {pattern!r}: {exc}") from exc


def _simulate_text_policy(
    safe_rows: dict[str, dict[str, Any]],
    fast_rows: dict[str, dict[str, Any]],
    *,
    questions: dict[str, str],
    safe_regex: re.Pattern[str],
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    overall = _empty_group_summary()
    by_group = defaultdict(_empty_group_summary)
    item_rows: list[dict[str, Any]] = []
    route_confusion: dict[str, Counter[str]] = defaultdict(Counter)

    missing_questions = sorted(set(safe_rows) - set(questions))
    if missing_questions:
        raise ValueError(f"missing question text for item ids: {missing_questions[:5]}")

    for key in sorted(safe_rows):
        safe = safe_rows[key]
        fast = fast_rows[key]
        question = questions[key]
        group = str(safe["group"])
        match = safe_regex.search(question)
        use_safe = match is not None
        source = "safe" if use_safe else "fast"
        chosen = safe if use_safe else fast
        dense_correct = bool(safe["dense_correct"])
        policy_correct = bool(chosen["composed_correct"])
        dense_choice = safe.get("dense_choice")
        policy_choice = chosen.get("composed_choice")
        transition = _transition(dense_correct, policy_correct)
        dense_ms = _adjusted_dense_ms(safe)
        policy_ms = _adjusted_composed_ms(chosen)
        if dense_ms <= 0.0 or policy_ms <= 0.0:
            raise ValueError(f"{key}: adjusted timing must be positive")

        route_confusion[group][source] += 1
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
                "question": question,
                "matched_safe_regex": use_safe,
                "matched_text": match.group(0) if match is not None else None,
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

    route_summary = {
        group: dict(sorted(counter.items())) for group, counter in sorted(route_confusion.items())
    }
    source_counts = Counter(row["source"] for row in item_rows)
    if source_counts.get("safe", 0) == 0 or source_counts.get("fast", 0) == 0:
        raise ValueError(
            "text routing is degenerate; expected at least one safe-routed item "
            f"and at least one fast-routed item, got {dict(sorted(source_counts.items()))}"
        )
    return (
        _finalize_summary(overall),
        item_rows,
        {group: _finalize_summary(summary) for group, summary in sorted(by_group.items())},
        route_summary,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--safe-paired-items", required=True, type=Path)
    parser.add_argument("--fast-paired-items", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--safe-question-regex",
        default=DEFAULT_SAFE_QUESTION_REGEX,
        help=(
            "Case-insensitive raw-question regex. Matching items route to the safe "
            "paired rows; non-matching items route to the fast paired rows."
        ),
    )
    parser.add_argument("--policy-label", default="text_regex_safe_fallback")
    parser.add_argument("--mvbench-json-dir", type=Path, default=MVBENCH_JSON_DIR)
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
    item_ids = _load_manifest_item_ids(args.manifest)
    questions = _load_mvbench_questions(item_ids, json_dir=args.mvbench_json_dir)
    safe_regex = _compile_regex(str(args.safe_question_regex))
    safe_rows = _index_rows(
        _read_jsonl(args.safe_paired_items),
        label="safe-paired-items",
    )
    fast_rows = _index_rows(
        _read_jsonl(args.fast_paired_items),
        label="fast-paired-items",
    )
    manifest_keys = set(item_ids)
    artifact_keys = set(safe_rows)
    if manifest_keys != artifact_keys:
        missing_from_manifest = sorted(artifact_keys - manifest_keys)
        missing_from_artifacts = sorted(manifest_keys - artifact_keys)
        raise ValueError(
            "manifest and paired artifacts do not describe the same item set: "
            f"missing_from_manifest={missing_from_manifest[:5]}, "
            f"missing_from_artifacts={missing_from_artifacts[:5]}"
        )
    audit = _validate_pairing(
        safe_rows,
        fast_rows,
        allow_dense_label_drift=args.allow_dense_label_drift,
    )
    summary, item_rows, by_group, route_summary = _simulate_text_policy(
        safe_rows,
        fast_rows,
        questions=questions,
        safe_regex=safe_regex,
    )
    payload = {
        "schema": "gemma_text_routed_admission_v1",
        "analysis_role": "exploratory_offline_text_policy_simulation",
        "dense_reference_source": "safe_paired_items",
        "policy_label": args.policy_label,
        "safe_question_regex": str(args.safe_question_regex),
        "safe_source_path": str(args.safe_paired_items),
        "fast_source_path": str(args.fast_paired_items),
        "manifest_path": str(args.manifest),
        "question_source": "mvbench_raw_question_json",
        "pairing_audit": audit,
        "route_summary_by_group": route_summary,
        "summary": summary,
        "by_group": by_group,
        "source_baselines": {
            "safe_all_items": _source_summary(safe_rows),
            "fast_all_items": _source_summary(fast_rows),
        },
        "items": item_rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
